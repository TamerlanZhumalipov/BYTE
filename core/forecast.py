"""BYTE Forecast v1: deterministic, uncalibrated assessment-based estimate.

No LLM or network call participates in scoring. See docs/forecast.md for the
assumptions, missing-data policy, evidence caps and historical semantics.
"""
from collections import defaultdict
from datetime import timedelta
from math import ceil, floor

from django.db.models import Prefetch
from django.utils import timezone

from .models import ENTSpecification, ENTTopic, ENTPracticeResult, QuizAttempt, Section, Submission

VERSION = "byte-forecast-v1"


def _decay(date, now):
    return 0.5 ** (max(0, (now - date).total_seconds() / 86400) / 60)


def _title(obj, language):
    return (obj.title_kk or obj.title) if language == "kk" else obj.title


def _calculate(topics, quizzes, submissions, mocks, maximum, now):
    start = now - timedelta(days=180)
    # Repeating the same quiz does not create independent evidence.
    by_root = defaultdict(list)
    for attempt in quizzes:
        if start <= attempt.created_at <= now and attempt.total_questions > 0 and 0 <= attempt.correct_count <= attempt.total_questions:
            if len(by_root[attempt.quiz.topic_id]) < 3:
                by_root[attempt.quiz.topic_id].append(attempt)
    root_evidence = {}
    for root_id, attempts in by_root.items():
        weights = [_decay(a.created_at, now) * (0.5 ** i) for i, a in enumerate(attempts)]
        score = sum(a.correct_count / a.total_questions * w for a, w in zip(attempts, weights)) / sum(weights)
        # Latest test length caps evidence; retries cannot inflate the sample size.
        mass = min(attempts[0].total_questions, 12) * _decay(attempts[0].created_at, now)
        root_evidence[root_id] = (score, mass)

    root_links = defaultdict(int)
    for topic in topics:
        for section in topic.sections.all():
            root_links[section.pk] += 1
    latest_tasks = {}
    for sub in submissions:
        if start <= sub.created_at <= now and sub.verdict in {"OK", "WA", "TLE", "RE", "CE"} and sub.total > 0 and 0 <= sub.passed <= sub.total:
            latest_tasks.setdefault(sub.task_id, sub)
    topic_ids = {t.pk for t in topics}
    task_evidence = defaultdict(list)
    for sub in latest_tasks.values():
        linked = [t.pk for t in sub.task.ent_topics.all() if t.pk in topic_ids]
        for topic_id in linked:
            task_evidence[topic_id].append((sub.passed / sub.total, 2 * _decay(sub.created_at, now) / len(linked)))

    rows = []
    evidence_ids = set()
    total_weight = sum(float(t.forecast_weight) for t in topics)
    total_mass = 0
    for topic in topics:
        roots = list(topic.sections.all())
        parts = [(root_evidence[s.pk][0], root_evidence[s.pk][1] / root_links[s.pk]) for s in roots if s.pk in root_evidence]
        for section in roots:
            if section.pk in root_evidence:
                evidence_ids.add(("quiz", section.pk))
        contest_parts = task_evidence[topic.pk]
        # Contests are a weaker proxy; cap total contest evidence per topic.
        contest_mass = sum(m for _, m in contest_parts)
        contest_factor = min(1, 4 / contest_mass) if contest_mass else 0
        parts += [(p, m * contest_factor) for p, m in contest_parts]
        mass = sum(m for _, m in parts)
        total_mass += mass
        observed = sum(p * m for p, m in parts) / mass if mass else None
        # Broad root mappings may cover only part of an ENT topic.
        root_coverage = sum(s.pk in root_evidence for s in roots) / len(roots) if roots else 0
        reliability = min(0.8, mass / (mass + 4)) * max(root_coverage, 0.35 if contest_parts else 0)
        estimate = 0.5 + reliability * (observed - 0.5) if observed is not None else 0.5
        radius = 0.12 + 0.38 * (1 - reliability)
        share = float(topic.forecast_weight) / total_weight if total_weight else 0
        rows.append({
            "id": topic.pk, "code": topic.code, "mastery": round(estimate * 100) if mass else None,
            "coverage": round(reliability * 100), "has_evidence": bool(mass),
            "quiz_roots": sum(s.pk in root_evidence for s in roots), "contest_tasks": len(contest_parts),
            "model_points": round(estimate * share * maximum, 1) if mass else None,
            "model_max": round(share * maximum, 1), "weight": share,
            "estimate": estimate, "radius": radius,
        })
    for task_id, sub in latest_tasks.items():
        if any(t.pk in topic_ids for t in sub.task.ent_topics.all()):
            evidence_ids.add(("contest", task_id))
    coverage = sum(r["weight"] * r["coverage"] / 100 for r in rows)
    score = sum(r["weight"] * r["estimate"] for r in rows)
    radius = sum(r["weight"] * r["radius"] for r in rows)
    # Full, verified mocks provide direct exam evidence, never per-topic mastery.
    recent_mocks = [m for m in mocks if now - timedelta(days=90) <= m.taken_at <= now and m.max_score == maximum and 0 <= m.score <= m.max_score][:3]
    if recent_mocks:
        weights = [_decay(m.taken_at, now) * 0.7 ** i for i, m in enumerate(recent_mocks)]
        mock_score = sum(m.score / m.max_score * w for m, w in zip(recent_mocks, weights)) / sum(weights)
        blend = 0.75 if coverage >= 0.2 else 1.0
        score = (1 - blend) * score + blend * mock_score
        spread = max(abs(m.score / m.max_score - mock_score) for m in recent_mocks)
        mock_radius = max(0.12, spread + 0.08, 0.22 - 0.03 * len(recent_mocks))
        radius = (1 - blend) * radius + blend * mock_radius
    available = bool(recent_mocks) or (len(evidence_ids) >= 3 and total_mass >= 10 and coverage >= 0.2)
    return {
        "status": "ready" if available else "insufficient_data",
        "score": round(score * maximum) if available else None,
        "low": max(0, floor((score - radius) * maximum)) if available else None,
        "high": min(maximum, ceil((score + radius) * maximum)) if available else None,
        "confidence": "medium" if available and sum(m.taken_at >= now - timedelta(days=30) for m in recent_mocks) >= 2 else "low",
        "coverage_percent": round(coverage * 100), "assessed_topics": sum(r["has_evidence"] for r in rows),
        "quiz_count": sum(key[0] == "quiz" for key in evidence_ids),
        "contest_count": sum(key[0] == "contest" for key in evidence_ids),
        "mock_count": len(recent_mocks), "topics": rows,
    }


def get_forecast(user, *, language="ru", year=None, now=None):
    if not user.is_authenticated:
        raise ValueError("Forecast requires an authenticated user")
    now = now or timezone.now()
    language = "kk" if language in {"kk", "kz"} else "ru"
    specs = ENTSpecification.objects.filter(subject="informatics", year__lte=now.year)
    if year is not None:
        specs = specs.filter(year=year)
    spec = specs.prefetch_related(Prefetch("topics", queryset=ENTTopic.objects.prefetch_related(
        Prefetch("sections", queryset=Section.objects.filter(parent__isnull=True, is_published=True).only("id", "title", "title_kk")),
    ))).first()
    base = {"version": VERSION, "generated_at": now.isoformat(), "language": language,
            "status": "unavailable", "score": None, "topics": [], "history": [], "recommendations": []}
    if not spec or spec.max_score <= 0:
        return base
    topics = list(spec.topics.all())
    if not topics or any(t.forecast_weight <= 0 for t in topics):
        return base
    root_ids = {s.pk for t in topics for s in t.sections.all()}
    earliest = now - timedelta(days=210)
    quizzes = list(QuizAttempt.objects.filter(user=user, quiz__topic_id__in=root_ids, created_at__range=(earliest, now)).select_related("quiz").defer("answers").order_by("-created_at", "-pk"))
    submissions = list(Submission.objects.filter(account__user=user, task__ent_topics__specification=spec, created_at__range=(earliest, now)).select_related("task").defer("code", "marks", "message", "task__statement").prefetch_related("task__ent_topics").distinct().order_by("-created_at", "-pk"))
    mocks = list(ENTPracticeResult.objects.filter(user=user, specification=spec, verified=True, taken_at__range=(earliest, now)).order_by("-taken_at", "-pk"))
    data = _calculate(topics, quizzes, submissions, mocks, spec.max_score, now)
    for row, topic in zip(data["topics"], topics):
        row["title"] = _title(topic, language)
        row["mapped"] = bool(list(topic.sections.all()))
        # Internal floats are only needed while calculating the aggregate.
        for key in ("weight", "estimate", "radius"):
            row.pop(key)
    history = []
    for days in (30, 21, 14, 7):
        date = now - timedelta(days=days)
        old = _calculate(topics, quizzes, submissions, mocks, spec.max_score, date)
        history.append({"date": date.date().isoformat(), "score": old["score"]})
    previous = history[0]["score"]
    delta = data["score"] - previous if previous is not None and data["score"] is not None else None
    history.append({"date": now.date().isoformat(), "score": data["score"]})
    recommendations = sorted(data["topics"], key=lambda r: (r["mastery"] is not None, r["mastery"] or 0, r["code"]))[:3]
    from .textbooks import for_topics
    reading = for_topics([r["id"] for r in recommendations], language)
    for row in recommendations:
        row["reading"] = reading[row["id"]]
    note = (spec.forecast_weight_note_kk or spec.forecast_weight_note) if language == "kk" else spec.forecast_weight_note
    return {**base, **data, "specification_id": spec.pk, "year": spec.year,
            "max_score": spec.max_score, "topic_count": len(topics), "delta": delta,
            "history": history, "recommendations": recommendations,
            "weight_note": note, "equal_weights": len({t.forecast_weight for t in topics}) == 1}
