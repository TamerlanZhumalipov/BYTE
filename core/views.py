import json
import logging
import math
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import Http404, JsonResponse
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LeadForm
from .judge import LANGUAGES, MAX_CODE_BYTES, run_submission
from .localization import get_request_language, tr
from .models import (
    AIMessage, Contest, ContestAccount, ContestTask, QuizAttempt, Section, Submission, TopicQuiz,
)
from . import ai as ai_module

logger = logging.getLogger(__name__)

CONTEST_SESSION_KEY = "contest_account_id"
SUBMIT_COOLDOWN_SEC = 10


# ---------------------------------------------------------------------------
# Лендинг и заявки
# ---------------------------------------------------------------------------

def index(request):
    return render(request, "index.html")


@require_POST
def set_language(request):
    language = request.POST.get("language", "ru")
    request.session["site_language"] = language if language in {"ru", "kk"} else "ru"

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/"
    return redirect(next_url)


@require_POST
def lead_create(request):
    # Принимаем как актуальное поле phone, так и старое contact,
    # чтобы форма не ломалась при кэше старого HTML/JS в браузере.
    data = request.POST.copy()
    if not data.get("phone") and data.get("contact"):
        data["phone"] = data.get("contact", "")

    form = LeadForm(data)
    if not form.is_valid():
        errors = {
            field: [str(message) for message in messages]
            for field, messages in form.errors.items()
        }
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    try:
        lead = form.save()
    except IntegrityError:
        logger.exception("Не удалось сохранить заявку")
        return JsonResponse(
            {"ok": False, "error": "Не удалось сохранить заявку. Попробуйте ещё раз."},
            status=500,
        )

    return JsonResponse({
        "ok": True,
        "lead_id": lead.pk,
        "message": "Заявка принята. Мы свяжемся с вами в течение дня.",
    })


# ---------------------------------------------------------------------------
# Кабинет: материалы
# ---------------------------------------------------------------------------

def _localize_section(section, lang):
    """Добавляет display_* поля с fallback на русский."""
    use_kk = lang == "kk"
    section.display_title = (section.title_kk or section.title) if use_kk else section.title
    section.display_summary = (section.summary_kk or section.summary) if use_kk else section.summary
    section.display_content = (section.content_kk or section.content) if use_kk else section.content
    section.display_video_url = (section.video_url_kk or section.video_url) if use_kk else section.video_url
    section.display_video_embed_url = section.make_video_embed_url(section.display_video_url)
    return section


def _build_tree(lang="ru"):
    """Все опубликованные разделы одним запросом, собранные в дерево."""
    sections = list(Section.objects.filter(is_published=True))
    by_parent = {}
    for section in sections:
        _localize_section(section, lang)
        by_parent.setdefault(section.parent_id, []).append(section)
    for section in sections:
        section.kids = by_parent.get(section.id, [])
    return by_parent.get(None, []), {s.id: s for s in sections}


def _flatten(nodes):
    result = []
    for node in nodes:
        result.append(node)
        result.extend(_flatten(getattr(node, "kids", [])))
    return result


def _upcoming_contest():
    """Ближайший контест, который ещё не закончился."""
    now = timezone.now()
    for contest in Contest.objects.filter(starts_at__gte=now - timedelta(days=1)).order_by("starts_at"):
        if contest.ends_at >= now:
            return contest
    return None


def _root_topic(section, by_id=None):
    """Возвращает корневую тему.

    Если передан by_id из _build_tree(), используем те же экземпляры Section,
    на которых уже есть динамический атрибут .kids. Это важно для навигации
    по урокам и определения последней подтемы.
    """
    node = section
    while node and node.parent_id:
        if by_id and node.parent_id in by_id:
            node = by_id[node.parent_id]
        else:
            node = node.parent
    return node


def _mark_topic_lock(node, locked):
    node.is_locked = locked
    for child in getattr(node, "kids", []):
        _mark_topic_lock(child, locked)


def _decorate_learning_path(user, roots):
    """Добавляет темам состояние прогресса и последовательно открывает программу."""
    quizzes = {
        quiz.topic_id: quiz
        for quiz in TopicQuiz.objects.filter(topic__in=roots).select_related("topic")
    }
    attempts = list(
        QuizAttempt.objects.filter(user=user, quiz__topic__in=roots)
        .select_related("quiz", "quiz__topic")
        .order_by("-created_at")
    )

    best_by_topic = {}
    latest_by_topic = {}
    passed_topics = set()
    attempts_count = {}
    for attempt in attempts:
        topic_id = attempt.quiz.topic_id
        attempts_count[topic_id] = attempts_count.get(topic_id, 0) + 1
        best_by_topic[topic_id] = max(best_by_topic.get(topic_id, 0), attempt.score_percent)
        latest_by_topic.setdefault(topic_id, attempt)
        if attempt.passed:
            passed_topics.add(topic_id)

    unlocked = True
    for root in roots:
        root.quiz_obj = quizzes.get(root.id)
        root.best_score = best_by_topic.get(root.id)
        root.latest_attempt = latest_by_topic.get(root.id)
        root.attempts_count = attempts_count.get(root.id, 0)
        root.is_completed = root.id in passed_topics
        root.is_locked = not unlocked
        _mark_topic_lock(root, root.is_locked)

        # Следующая основная тема открывается только после успешного теста текущей.
        if not root.is_completed:
            unlocked = False

    return {
        "quizzes": quizzes,
        "best_by_topic": best_by_topic,
        "latest_by_topic": latest_by_topic,
        "passed_topics": passed_topics,
        "attempts": attempts,
    }


@login_required
def dashboard(request, slug=None):
    lang = get_request_language(request)
    roots, by_id = _build_tree(lang)
    flat = _flatten(roots)
    learning = _decorate_learning_path(request.user, roots)

    current = None
    breadcrumbs = []
    prev_section = next_section = None
    open_ids = set()

    if slug:
        current = next((s for s in flat if s.slug == slug), None)
        if current is None:
            raise Http404("Раздел не найден")
        if getattr(current, "is_locked", False):
            messages.warning(
                request,
                tr("Эта тема пока закрыта. Сначала пройдите тест предыдущей основной темы.", lang),
            )
            return redirect("dashboard")

        parent_id = current.parent_id
        while parent_id in by_id:
            ancestor = by_id[parent_id]
            breadcrumbs.insert(0, ancestor)
            open_ids.add(ancestor.id)
            parent_id = ancestor.parent_id
        open_ids.add(current.id)

        index = flat.index(current)
        prev_section = flat[index - 1] if index > 0 else None
        next_section = flat[index + 1] if index < len(flat) - 1 else None
        if next_section is not None and getattr(next_section, "is_locked", False):
            next_section = None

    current_root = _root_topic(current, by_id) if current else None
    current_quiz = learning["quizzes"].get(current_root.id) if current_root else None
    current_best_score = learning["best_by_topic"].get(current_root.id) if current_root else None
    current_topic_completed = bool(current_root and current_root.id in learning["passed_topics"])

    next_root = None
    if current_root and current_root in roots:
        root_index = roots.index(current_root)
        if root_index < len(roots) - 1:
            next_root = roots[root_index + 1]

    # После последнего урока внутри основной темы следующий шаг — проверочный тест,
    # а не следующая основная тема.
    next_is_quiz = False
    if current and current_root and current_quiz:
        topic_sections = _flatten([current_root])
        if topic_sections and current.id == topic_sections[-1].id:
            next_section = None
            next_is_quiz = True

    # История BYTE AI хранится только в sessionStorage браузера.
    # После закрытия вкладки/браузера новый чат начинается с нуля.
    ai_history = []

    return render(request, "dashboard.html", {
        "active_tab": "materials",
        "roots": roots,
        "current": current,
        "breadcrumbs": breadcrumbs,
        "prev_section": prev_section,
        "next_section": next_section,
        "open_ids": open_ids,
        "next_contest": _upcoming_contest(),
        "current_root": current_root,
        "current_quiz": current_quiz,
        "current_best_score": current_best_score,
        "current_topic_completed": current_topic_completed,
        "next_root": next_root,
        "next_is_quiz": next_is_quiz,
        "ai_enabled": ai_module.is_configured(),
        "ai_history": ai_history,
    })


# ---------------------------------------------------------------------------
# Проверочные тесты и аналитика
# ---------------------------------------------------------------------------

@login_required
def topic_quiz(request, slug):
    lang = get_request_language(request)
    roots, _ = _build_tree(lang)
    learning = _decorate_learning_path(request.user, roots)
    topic = next((root for root in roots if root.slug == slug), None)
    if topic is None:
        raise Http404("Основная тема не найдена")
    if topic.is_locked:
        messages.warning(request, tr("Сначала завершите предыдущую основную тему.", lang))
        return redirect("dashboard")

    quiz = learning["quizzes"].get(topic.id)
    if quiz is None:
        messages.info(request, tr("Проверочный тест для этой темы пока не добавлен.", lang))
        return redirect(topic.get_absolute_url())

    questions = list(quiz.questions.prefetch_related("choices").all())
    for question in questions:
        question.display_text = (question.text_kk or question.text) if lang == "kk" else question.text
        for choice in question.choices.all():
            choice.display_text = (choice.text_kk or choice.text) if lang == "kk" else choice.text
    result = None

    if request.method == "POST":
        if not questions:
            messages.info(request, tr("В тесте пока нет вопросов.", lang))
            return redirect(topic.get_absolute_url())

        correct_count = 0
        answers = {}
        review = []
        for question in questions:
            selected_raw = request.POST.get(f"q_{question.id}", "")
            try:
                selected_id = int(selected_raw)
            except (TypeError, ValueError):
                selected_id = None

            choices = list(question.choices.all())
            selected = next((choice for choice in choices if choice.id == selected_id), None)
            correct_choice = next((choice for choice in choices if choice.is_correct), None)
            is_correct = bool(selected and selected.is_correct)
            if is_correct:
                correct_count += 1
            answers[str(question.id)] = selected_id
            review.append({
                "question": question,
                "selected": selected,
                "correct_choice": correct_choice,
                "is_correct": is_correct,
            })

        total = len(questions)
        score = round(correct_count * 100 / total)
        passed = score >= quiz.pass_percent
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score_percent=score,
            correct_count=correct_count,
            total_questions=total,
            passed=passed,
            answers=answers,
        )

        # После успешной попытки пересчитываем путь, чтобы сразу показать открытую тему.
        refreshed = _decorate_learning_path(request.user, roots)
        topic_index = roots.index(topic)
        unlocked_next = roots[topic_index + 1] if passed and topic_index < len(roots) - 1 else None

        result = {
            "attempt": attempt,
            "score": score,
            "passed": passed,
            "correct_count": correct_count,
            "total": total,
            "review": review,
            "unlocked_next": unlocked_next,
        }

    best_score = (
        QuizAttempt.objects.filter(user=request.user, quiz=quiz)
        .order_by("-score_percent")
        .values_list("score_percent", flat=True)
        .first()
    )

    return render(request, "topic_quiz.html", {
        "active_tab": "materials",
        "topic": topic,
        "quiz": quiz,
        "questions": questions,
        "result": result,
        "best_score": best_score,
    })


def _analytics_forecast(roots):
    points = [
        (index + 1, root.best_score)
        for index, root in enumerate(roots)
        if root.best_score is not None
    ]
    if not points:
        return None, "Недостаточно данных"

    if len(points) == 1:
        return int(points[0][1]), "Первичный прогноз"

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    slope = (
        sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
        if denominator else 0
    )
    intercept = y_mean - slope * x_mean

    projected = []
    known = {x: y for x, y in points}
    for index in range(1, len(roots) + 1):
        value = known.get(index, intercept + slope * index)
        projected.append(max(0, min(100, value)))

    forecast = round(sum(projected) / len(projected))
    if slope > 2:
        trend = "Результаты растут"
    elif slope < -2:
        trend = "Есть нисходящий тренд"
    else:
        trend = "Результаты стабильны"
    return forecast, trend


@login_required
def analytics(request):
    lang = get_request_language(request)
    roots, _ = _build_tree(lang)
    learning = _decorate_learning_path(request.user, roots)

    rows = []
    for index, root in enumerate(roots, start=1):
        quiz = learning["quizzes"].get(root.id)
        latest = learning["latest_by_topic"].get(root.id)
        rows.append({
            "index": index,
            "topic": root,
            "quiz": quiz,
            "best_score": root.best_score,
            "latest": latest,
            "attempts_count": root.attempts_count,
            "completed": root.is_completed,
            "locked": root.is_locked,
        })

    total_topics = len(roots)
    completed_topics = sum(1 for root in roots if root.is_completed)
    progress_percent = round(completed_topics * 100 / total_topics) if total_topics else 0
    scored = [root.best_score for root in roots if root.best_score is not None]
    average_score = round(sum(scored) / len(scored)) if scored else None
    forecast_score, trend = _analytics_forecast(roots)
    trend = tr(trend, lang)

    recent_attempts = learning["attempts"][:6]
    for attempt in recent_attempts:
        _localize_section(attempt.quiz.topic, lang)

    return render(request, "analytics.html", {
        "active_tab": "analytics",
        "rows": rows,
        "total_topics": total_topics,
        "completed_topics": completed_topics,
        "progress_percent": progress_percent,
        "average_score": average_score,
        "forecast_score": forecast_score,
        "trend": trend,
        "recent_attempts": recent_attempts,
    })


# ---------------------------------------------------------------------------
# Контест: отдельный вход по логину/паролю, выданному куратором
# ---------------------------------------------------------------------------

def _current_account(request):
    account_id = request.session.get(CONTEST_SESSION_KEY)
    if not account_id:
        return None
    return (
        ContestAccount.objects.select_related("contest")
        .filter(pk=account_id, is_active=True)
        .first()
    )


def _submission_json(sub):
    return {
        "id": sub.id,
        "verdict": sub.verdict,
        "label": sub.get_verdict_display(),
        "passed": sub.passed,
        "total": sub.total,
        "marks": sub.marks,
        "language": sub.language,
        "time": timezone.localtime(sub.created_at).strftime("%H:%M:%S"),
        "message": sub.message,
    }


def _seconds(delta):
    return max(0, int(math.ceil(delta.total_seconds())))


@login_required
def contest_login(request):
    if _current_account(request):
        return redirect("contest")

    error = ""
    if request.method == "POST":
        login = request.POST.get("login", "").strip().lower()
        password = request.POST.get("password", "")
        account = ContestAccount.objects.filter(login=login, is_active=True).first()
        if account and account.check_password(password):
            request.session[CONTEST_SESSION_KEY] = account.pk
            return redirect("contest")
        error = tr("Неверный логин или пароль контеста.", get_request_language(request))

    return render(request, "contest_login.html", {
        "active_tab": "contest",
        "error": error,
        "next_contest": _upcoming_contest(),
    })


@login_required
@require_POST
def contest_logout(request):
    request.session.pop(CONTEST_SESSION_KEY, None)
    return redirect("dashboard")


@login_required
def contest(request):
    account = _current_account(request)
    if account is None:
        return redirect("contest_login")

    contest_obj = account.contest
    now = timezone.now()
    state = contest_obj.state(now)

    context = {
        "active_tab": "contest",
        "account": account,
        "contest": contest_obj,
        "state": state,
    }

    if state == "upcoming":
        context["seconds_to_start"] = _seconds(contest_obj.starts_at - now)
        return render(request, "contest.html", context)

    items = []
    payload_tasks = []
    for task in contest_obj.tasks.all():
        total = task.tests.count()
        finished = account.submissions.filter(task=task).exclude(verdict="PENDING")
        best = finished.order_by("-passed", "created_at").first()
        history = [_submission_json(s) for s in finished.order_by("-created_at")[:8]]
        best_passed = best.passed if best else 0
        items.append({"task": task, "total": total, "best": best_passed})
        payload_tasks.append({
            "id": task.id,
            "total": total,
            "best": best_passed,
            "history": history,
        })

    context["items"] = items
    context["contest_data"] = {
        "contestId": contest_obj.id,
        "accountId": account.id,
        "state": state,
        "remaining": _seconds(contest_obj.ends_at - now) if state == "running" else 0,
        "duration": contest_obj.duration_minutes * 60,
        "submitUrl": reverse("contest_submit"),
        "tasks": payload_tasks,
    }
    return render(request, "contest.html", context)


@login_required
@require_POST
def contest_submit(request):
    account = _current_account(request)
    if account is None:
        return JsonResponse({"error": "Сначала войдите в контест."}, status=403)

    try:
        data = json.loads(request.body)
        task_id = int(data.get("task_id"))
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"error": "Некорректный запрос."}, status=400)

    contest_obj = account.contest
    now = timezone.now()
    if contest_obj.state(now) != "running":
        return JsonResponse({
            "error": "Контест сейчас не идёт — отправка закрыта.",
            "state": contest_obj.state(now),
        }, status=403)

    task = ContestTask.objects.filter(pk=task_id, contest=contest_obj).first()
    if task is None:
        return JsonResponse({"error": "Такой задачи нет в этом контесте."}, status=404)

    language = data.get("language")
    code = data.get("code")
    if language not in LANGUAGES or not isinstance(code, str) or not code.strip():
        return JsonResponse({"error": "Выберите язык и напишите решение."}, status=400)
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return JsonResponse({"error": "Решение слишком большое (максимум 64 КБ)."}, status=400)

    if account.submissions.filter(verdict="PENDING", created_at__gte=now - timedelta(minutes=2)).exists():
        return JsonResponse({"error": "Предыдущее решение ещё проверяется — подождите."}, status=429)
    last = account.submissions.order_by("-created_at").first()
    if last:
        elapsed = (now - last.created_at).total_seconds()
        if elapsed < SUBMIT_COOLDOWN_SEC:
            wait = int(math.ceil(SUBMIT_COOLDOWN_SEC - elapsed))
            return JsonResponse({"error": f"Слишком часто. Подождите {wait} с."}, status=429)

    tests = list(task.tests.values_list("input_data", "expected_output"))
    if not tests:
        return JsonResponse({"error": "У этой задачи пока нет тестов. Сообщите куратору."}, status=409)

    submission = Submission.objects.create(
        account=account, task=task, language=language, code=code, total=len(tests),
    )
    try:
        result = run_submission(code, language, tests, task.time_limit)
    except Exception:  # noqa: BLE001 — не оставляем отправку в статусе «проверяется»
        logger.exception("Ошибка проверяющей системы")
        submission.verdict = "RE"
        submission.message = "Внутренняя ошибка проверки. Сообщите куратору."
        submission.save(update_fields=["verdict", "message"])
        return JsonResponse({"error": "Внутренняя ошибка проверки. Сообщите куратору."}, status=500)

    submission.verdict = result.verdict
    submission.passed = result.passed
    submission.total = result.total
    submission.marks = result.marks
    submission.message = result.message
    submission.save()

    best = (
        account.submissions.filter(task=task).exclude(verdict="PENDING")
        .order_by("-passed").values_list("passed", flat=True).first() or 0
    )
    return JsonResponse({
        "submission": _submission_json(submission),
        "best": best,
        "remaining": _seconds(contest_obj.ends_at - timezone.now()),
    })


# ---------------------------------------------------------------------------
# ИИ-помощник по материалам
# ---------------------------------------------------------------------------

def _section_path_titles(section):
    titles = [section.title]
    parent = section.parent
    while parent is not None:
        titles.insert(0, parent.title)
        parent = parent.parent
    return titles


def _ai_request_payload(request):
    try:
        data = json.loads(request.body)
        message = (data.get("message") or "").strip()
        raw_history = data.get("history") or []
    except (ValueError, TypeError, AttributeError):
        return None, None, JsonResponse({"error": "Некорректный запрос."}, status=400)

    if not message:
        return None, None, JsonResponse({"error": "Введите вопрос."}, status=400)
    if len(message) > 2000:
        return None, None, JsonResponse(
            {"error": "Слишком длинное сообщение (максимум 2000 символов)."},
            status=400,
        )

    # История приходит из sessionStorage текущей вкладки и не хранится
    # сервером как контекст чата между посещениями.
    history = []
    if isinstance(raw_history, list):
        for item in raw_history[-settings.AI_HISTORY_MESSAGES:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            history.append({"role": role, "content": content[:4000]})

    return message, history, None


def _ai_rate_limit(request):
    now = timezone.now()
    last = AIMessage.objects.filter(user=request.user, role="user").order_by("-created_at").first()
    if last and (now - last.created_at).total_seconds() < settings.AI_COOLDOWN_SECONDS:
        return JsonResponse({"error": "Слишком часто — подождите пару секунд."}, status=429)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = AIMessage.objects.filter(
        user=request.user, role="user", created_at__gte=today_start
    ).count()
    if used_today >= settings.AI_DAILY_LIMIT:
        return JsonResponse({"error": "Дневной лимит вопросов помощнику исчерпан. Попробуйте завтра."}, status=429)
    return None


@login_required
@require_POST
def ai_ask_home(request):
    if not ai_module.is_configured():
        return JsonResponse({"error": "BYTE AI сейчас недоступен. Проверьте GEMINI_API_KEY."}, status=503)

    message, history, error = _ai_request_payload(request)
    if error:
        return error
    limited = _ai_rate_limit(request)
    if limited:
        return limited

    # Сообщения можно оставлять в БД для лимитов/админки, но они больше
    # не восстанавливаются в чат и не используются как история новой сессии.
    AIMessage.objects.create(user=request.user, section=None, role="user", content=message)

    try:
        answer = ai_module.ask(None, [], history, message)
    except ai_module.AIServiceError as exc:
        logger.exception("Ошибка BYTE AI на главной кабинета")
        return JsonResponse({"error": exc.public_message, "code": exc.code}, status=502)
    except Exception:
        logger.exception("Неожиданная ошибка BYTE AI на главной кабинета")
        return JsonResponse({"error": "Внутренняя ошибка BYTE AI. Проверьте терминал Django."}, status=502)

    reply = AIMessage.objects.create(
        user=request.user, section=None, role="assistant", content=answer
    )
    return JsonResponse({"content": reply.content})


@login_required
@require_POST
def ai_reset_home(request):
    AIMessage.objects.filter(
        user=request.user, section=None, archived=False
    ).update(archived=True)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def ai_ask(request, slug):
    if not ai_module.is_configured():
        return JsonResponse({"error": "Помощник сейчас недоступен. Сообщите куратору."}, status=503)

    section = Section.objects.filter(slug=slug, is_published=True).first()
    if section is None:
        raise Http404("Раздел не найден")

    message, history, error = _ai_request_payload(request)
    if error:
        return error
    limited = _ai_rate_limit(request)
    if limited:
        return limited

    AIMessage.objects.create(user=request.user, section=section, role="user", content=message)

    try:
        answer = ai_module.ask(section, _section_path_titles(section), history, message)
    except ai_module.AIServiceError as exc:
        logger.exception("Ошибка ИИ-помощника")
        return JsonResponse({"error": exc.public_message, "code": exc.code}, status=502)
    except Exception:
        logger.exception("Неожиданная ошибка ИИ-помощника")
        return JsonResponse({"error": "Внутренняя ошибка BYTE AI. Проверьте терминал Django."}, status=502)

    reply = AIMessage.objects.create(user=request.user, section=section, role="assistant", content=answer)
    return JsonResponse({"content": reply.content})


@login_required
@require_POST
def ai_reset(request, slug):
    section = Section.objects.filter(slug=slug).first()
    if section is None:
        raise Http404("Раздел не найден")
    AIMessage.objects.filter(user=request.user, section=section, archived=False).update(archived=True)
    return JsonResponse({"ok": True})
