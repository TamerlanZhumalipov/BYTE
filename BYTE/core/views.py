import json
import logging
import math
from datetime import timedelta


from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.db.models import Avg, Max
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LeadForm
from .ai import ai_chat
from .judge import LANGUAGES, MAX_CODE_BYTES, run_submission
from .models import Contest, ContestAccount, ContestTask, Section, Submission, LessonProgress, QuizAttempt

logger = logging.getLogger(__name__)

CONTEST_SESSION_KEY = "contest_account_id"
SUBMIT_COOLDOWN_SEC = 10

# ---------------------------------------------------------------------------
# Лендинг и заявки
# ---------------------------------------------------------------------------

def index(request):
    return render(request, "index.html")


@require_POST
def lead_create(request):
    form = LeadForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


# ---------------------------------------------------------------------------
# Кабинет: материалы
# ---------------------------------------------------------------------------

def _build_tree():
    sections = list(Section.objects.filter(is_published=True))
    by_parent = {}
    for section in sections:
        by_parent.setdefault(section.parent_id, []).append(section)
    for section in sections:
        section.kids = by_parent.get(section.id, [])
    return by_parent.get(None, []), {s.id: s for s in sections}


def _flatten(nodes):
    result = []
    for node in nodes:
        result.append(node)
        result.extend(_flatten(node.kids))
    return result


def _upcoming_contest():
    now = timezone.now()
    for contest in Contest.objects.filter(starts_at__gte=now - timedelta(days=1)).order_by("starts_at"):
        if contest.ends_at >= now:
            return contest
    return None


@login_required
def dashboard(request, slug=None):
    roots, by_id = _build_tree()
    flat = _flatten(roots)
    current = None
    breadcrumbs = []
    prev_section = next_section = None
    open_ids = set()
    if slug:
        current = next((s for s in flat if s.slug == slug), None)
        if current is None:
            raise Http404("Раздел не найден")
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

    lessons = [s for s in flat if s.content.strip()]
    completed_ids = set(LessonProgress.objects.filter(user=request.user, completed=True, section_id__in=[s.pk for s in lessons]).values_list('section_id', flat=True))
    for root in roots:
        children = [s for s in _flatten([root]) if s.content.strip()]
        root.lesson_count = len(children)
        root.completed_count = sum(s.pk in completed_ids for s in children)
        root.percent = round(100 * root.completed_count / len(children)) if children else 0
    if current:
        LessonProgress.objects.get_or_create(user=request.user, section=current)
        LessonProgress.objects.filter(user=request.user, section=current).update(updated_at=timezone.now())
    resume = next((s for s in lessons if s.pk not in completed_ids), None)
    latest = LessonProgress.objects.filter(user=request.user, completed=False, section_id__in=[s.pk for s in lessons]).order_by('-updated_at').first()
    if latest:
        resume = by_id.get(latest.section_id, resume)
    attempts = QuizAttempt.objects.filter(user=request.user)
    average = attempts.aggregate(value=Avg('percent'))['value']
    from .learning import available_quizzes
    section_quizzes = available_quizzes().filter(section=current).filter(questions__isnull=False).distinct() if current else []
    next_contest = _upcoming_contest()
    contest_tasks = list(next_contest.tasks.all()[:4]) if next_contest else []
    return render(request, "dashboard.html", {
        "lesson_count": len(lessons), "completed_count": len(completed_ids),
        "progress_percent": round(100 * len(completed_ids) / len(lessons)) if lessons else 0,
        "is_completed": current and current.pk in completed_ids, "resume_section": resume,
        "attempt_count": attempts.count(), "average_score": round(average) if average is not None else None,
        "recent_attempts": attempts[:3], "section_quizzes": section_quizzes, "active_tab": "materials",
        "roots": roots, "current": current, "breadcrumbs": breadcrumbs, "prev_section": prev_section,
        "next_section": next_section, "open_ids": open_ids, "next_contest": next_contest,
        "contest_tasks": contest_tasks,
    })


# ---------------------------------------------------------------------------
# Контест
# ---------------------------------------------------------------------------

def _current_account(request):
    account_id = request.session.get(CONTEST_SESSION_KEY)
    if not account_id:
        return None
    return ContestAccount.objects.select_related("contest").filter(pk=account_id, is_active=True).first()


def _submission_json(sub):
    return {
        "id": sub.id, "verdict": sub.verdict, "label": sub.get_verdict_display(),
        "passed": sub.passed, "total": sub.total, "marks": sub.marks,
        "message": sub.message, "language": sub.language,
        "time": timezone.localtime(sub.created_at).strftime("%H:%M:%S"),
        "created_at": timezone.localtime(sub.created_at).strftime("%H:%M:%S"),
    }


def contest(request):
    account = _current_account(request)
    if not account:
        return render(request, "contest_login.html", {"active_tab": "contest"})

    contest_obj = account.contest
    tasks = list(contest_obj.tasks.prefetch_related("tests").all())
    now = timezone.now()
    state = contest_obj.state(now)

    items = []
    data_tasks = []
    for task in tasks:
        total = task.tests.count()
        submissions = list(Submission.objects.filter(account=account, task=task).order_by("-created_at")[:8])
        best = max((sub.passed for sub in submissions), default=0)
        items.append({"task": task, "total": total, "best": best})
        data_tasks.append({
            "id": task.id,
            "title": task.title,
            "total": total,
            "best": best,
            "history": [_submission_json(sub) for sub in submissions],
        })

    seconds_to_start = max(0, math.ceil((contest_obj.starts_at - now).total_seconds()))
    remaining = max(0, math.ceil((contest_obj.ends_at - now).total_seconds())) if state == "running" else 0
    contest_data = {
        "contestId": contest_obj.id,
        "accountId": account.id,
        "state": state,
        "duration": contest_obj.duration_minutes * 60,
        "remaining": remaining,
        "submitUrl": reverse("contest_submit"),
        "tasks": data_tasks,
    }
    return render(request, "contest.html", {
        "account": account, "contest": contest_obj, "tasks": tasks, "items": items,
        "state": state, "now": now, "seconds_to_start": seconds_to_start,
        "contest_data": contest_data, "active_tab": "contest",
    })


@require_POST
def contest_login(request):
    login = request.POST.get("login", "").strip()
    password = request.POST.get("password", "")
    account = ContestAccount.objects.select_related("contest").filter(login=login, is_active=True).first()
    if not account or not account.check_password(password):
        return render(request, "contest_login.html", {"error":"Неверный логин или пароль.", "active_tab":"contest"}, status=400)
    request.session[CONTEST_SESSION_KEY] = account.pk
    return redirect("contest")


@require_POST
def contest_logout(request):
    request.session.pop(CONTEST_SESSION_KEY, None)
    return redirect("contest")


@require_POST
def contest_submit(request):
    account = _current_account(request)
    if not account:
        return JsonResponse({"ok":False,"error":"Сначала войдите в контест."}, status=401)
    contest_obj = account.contest
    state = contest_obj.state()
    if state != "running":
        return JsonResponse({"ok":False,"error":"Отправлять решения можно только во время контеста.", "state":state}, status=403)
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id", data.get("task"))
        task = ContestTask.objects.get(pk=task_id, contest=contest_obj)
    except (json.JSONDecodeError, ContestTask.DoesNotExist):
        return JsonResponse({"ok":False,"error":"Задача не найдена."}, status=400)
    language = data.get("language")
    code = data.get("code", "")
    if language not in LANGUAGES:
        return JsonResponse({"ok":False,"error":"Выберите язык."}, status=400)
    if not code.strip():
        return JsonResponse({"ok":False,"error":"Введите код решения."}, status=400)
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return JsonResponse({"ok":False,"error":"Код слишком большой."}, status=400)
    recent = Submission.objects.filter(account=account, created_at__gte=timezone.now()-timedelta(seconds=SUBMIT_COOLDOWN_SEC)).exists()
    if recent:
        return JsonResponse({"ok":False,"error":f"Подождите {SUBMIT_COOLDOWN_SEC} секунд перед следующей отправкой."}, status=429)
    submission = Submission.objects.create(account=account, task=task, language=language, code=code)
    try:
        run_submission(submission)
    except Exception:
        logger.exception("Judge crashed for submission %s", submission.pk)
        submission.verdict="RE"; submission.message="Ошибка системы проверки."; submission.save(update_fields=["verdict","message"])

    best = Submission.objects.filter(account=account, task=task).aggregate(value=Max("passed"))["value"] or 0
    remaining = max(0, math.ceil((contest_obj.ends_at - timezone.now()).total_seconds()))
    return JsonResponse({"ok":True,"submission":_submission_json(submission), "best":best, "remaining":remaining})


@login_required
@require_POST
def lesson_complete(request, slug):
    section = Section.objects.filter(slug=slug, is_published=True).first()
    if not section: raise Http404("Раздел не найден")
    completed = request.POST.get('completed') == '1'
    LessonProgress.objects.update_or_create(user=request.user, section=section, defaults={'completed':completed})
    return redirect(section.get_absolute_url())


def handler404(request, exception):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)
