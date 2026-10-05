import json
import logging
import math
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import Http404, JsonResponse
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LeadForm
from .judge import LANGUAGES, MAX_CODE_BYTES, run_submission
from .models import AIMessage, Contest, ContestAccount, ContestTask, Section, Submission
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

def _build_tree():
    """Все опубликованные разделы одним запросом, собранные в дерево.

    Каждому разделу добавляется атрибут .kids — список его подразделов.
    """
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
    """Ближайший контест, который ещё не закончился."""
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

    ai_history = []
    if current:
        ai_history = [
            {"role": m.role, "content": m.content}
            for m in AIMessage.objects.filter(user=request.user, section=current, archived=False)
        ]

    return render(request, "dashboard.html", {
        "active_tab": "materials",
        "roots": roots,
        "current": current,
        "breadcrumbs": breadcrumbs,
        "prev_section": prev_section,
        "next_section": next_section,
        "open_ids": open_ids,
        "next_contest": _upcoming_contest(),
        "ai_enabled": ai_module.is_configured(),
        "ai_history": ai_history,
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
        error = "Неверный логин или пароль контеста."

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


@login_required
@require_POST
def ai_ask(request, slug):
    if not ai_module.is_configured():
        return JsonResponse({"error": "Помощник сейчас недоступен. Сообщите куратору."}, status=503)

    section = Section.objects.filter(slug=slug, is_published=True).first()
    if section is None:
        raise Http404("Раздел не найден")

    try:
        data = json.loads(request.body)
        message = (data.get("message") or "").strip()
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"error": "Некорректный запрос."}, status=400)

    if not message:
        return JsonResponse({"error": "Введите вопрос."}, status=400)
    if len(message) > 2000:
        return JsonResponse({"error": "Слишком длинное сообщение (максимум 2000 символов)."}, status=400)

    now = timezone.now()
    last = AIMessage.objects.filter(user=request.user, role="user").order_by("-created_at").first()
    if last and (now - last.created_at).total_seconds() < settings.AI_COOLDOWN_SECONDS:
        return JsonResponse({"error": "Слишком часто — подождите пару секунд."}, status=429)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = AIMessage.objects.filter(user=request.user, role="user", created_at__gte=today_start).count()
    if used_today >= settings.AI_DAILY_LIMIT:
        return JsonResponse({"error": "Дневной лимит вопросов помощнику исчерпан. Попробуйте завтра."}, status=429)

    history_qs = (
        AIMessage.objects.filter(user=request.user, section=section, archived=False)
        .order_by("-created_at")[: settings.AI_HISTORY_MESSAGES]
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(history_qs)]

    AIMessage.objects.create(user=request.user, section=section, role="user", content=message)

    try:
        answer = ai_module.ask(section, _section_path_titles(section), history, message)
    except Exception:  # noqa: BLE001 — не показываем ученику внутреннюю ошибку/трассировку
        logger.exception("Ошибка ИИ-помощника")
        return JsonResponse({"error": "Не получилось получить ответ. Попробуйте ещё раз чуть позже."}, status=502)

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
