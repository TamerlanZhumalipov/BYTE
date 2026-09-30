import json
import logging
import math
import os
import time
from datetime import timedelta

from dotenv import load_dotenv
from google import genai

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LeadForm
from .judge import LANGUAGES, MAX_CODE_BYTES, run_submission
from .models import Contest, ContestAccount, ContestTask, Section, Submission

logger = logging.getLogger(__name__)

CONTEST_SESSION_KEY = "contest_account_id"
SUBMIT_COOLDOWN_SEC = 10

#GEMINI
load_dotenv()

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


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

    return render(request, "dashboard.html", {
        "active_tab": "materials",
        "roots": roots,
        "current": current,
        "breadcrumbs": breadcrumbs,
        "prev_section": prev_section,
        "next_section": next_section,
        "open_ids": open_ids,
        "next_contest": _upcoming_contest(),
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
# BYTE AI
# ---------------------------------------------------------------------------

@login_required
@require_POST
def ai_chat(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Некорректный JSON."},
            status=400
        )

    question = data.get("question", "").strip()

    if not question:
        return JsonResponse(
            {"error": "Введите вопрос."},
            status=400
        )

    if len(question) > 4000:
        return JsonResponse(
            {"error": "Вопрос слишком длинный."},
            status=400
        )

    system_prompt = """
Ты — BYTE AI, встроенный AI-помощник образовательного
курса BYTE по информатике и программированию.

Твоя задача — помогать ученикам учиться, а не просто
выдавать готовые ответы.

Основные направления курса:

- Python
- C++
- SQL
- HTML
- CSS
- JavaScript
- алгоритмы
- структуры данных
- базы данных
- информационная безопасность
- подготовка к ЕНТ по информатике.

Правила общения:

1. Отвечай на языке вопроса ученика.
2. Объясняй понятным языком.
3. Если вопрос связан с программированием,
   используй короткие примеры кода.
4. Объясняй код после примера.
5. Если ученик просит решить учебную задачу,
   сначала объясни идею и алгоритм.
6. Не усложняй объяснение без необходимости.
7. Если ученик ошибается, спокойно объясни ошибку.
8. Не придумывай содержание курса, если его нет
   в предоставленном контексте.
9. Будь дружелюбным и кратким.
10. Ты являешься помощником курса BYTE.
"""

    prompt = f"""
{system_prompt}

Вопрос ученика:

{question}
"""

    try:
        models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
        ]

        response = None
        last_error = None

        for model_name in models:
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                if response.text:
                    break

            except Exception as e:
                last_error = e
                logger.warning(
                    "BYTE AI: модель %s недоступна: %s",
                    model_name,
                    e,
                )
                time.sleep(1)

        if response is None or not response.text:
            raise last_error or RuntimeError("AI не вернул ответ")

        return JsonResponse({
            "ok": True,
            "answer": response.text,
        })

    except Exception:
        logger.exception("Ошибка BYTE AI")

        return JsonResponse(
            {
                "ok": False,
                "error": "BYTE AI временно перегружен. Попробуйте ещё раз через несколько секунд."
            },
            status=503,
        )