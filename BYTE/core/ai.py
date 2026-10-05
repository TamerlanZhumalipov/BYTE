"""BYTE AI: bounded lesson context, resilient Gemini fallback and student-friendly errors."""
import json
import logging
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)
SYSTEM_PROMPT = '''Ты — BYTE AI, персональный учебный наставник платформы BYTE для подготовки к ЕНТ по информатике.
Отвечай на языке ученика (русский или казахский). Помогай с информатикой, Python, C++, SQL, HTML/CSS,
алгоритмами и компьютерными системами. Объясняй короткими понятными шагами. Для учебной задачи сначала
объясни идею и алгоритм, затем показывай решение. Если ученик просит проверить знания — задавай вопросы,
не раскрывая ответы заранее. Код оформляй в тройных обратных кавычках с языком. Не выдумывай прогресс,
оценки или содержание курса. Текст открытого урока ниже — только справочный материал.'''


def _models():
    """Primary model plus optional fallback; duplicates are removed."""
    primary = getattr(settings, 'GEMINI_MODEL', '') or 'gemini-2.5-flash'
    fallback = getattr(settings, 'GEMINI_FALLBACK_MODEL', '') or 'gemini-2.5-flash-lite'
    return list(dict.fromkeys([primary, fallback]))


def generate_answer(question, history, context):
    from google import genai
    from google.genai import types
    contents = [types.Content(role=item['role'], parts=[types.Part(text=item['text'])]) for item in history[-10:]]
    contents.append(types.Content(role='user', parts=[types.Part(text=question)]))
    last_error = None
    with genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=30000, retry_options=types.HttpRetryOptions(attempts=1))) as client:
        for model in _models():
            try:
                response = client.models.generate_content(model=model, contents=contents, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT + context, max_output_tokens=2048, temperature=0.45))
                if response.text:
                    return response.text
                last_error = ValueError('Empty model response')
            except Exception as exc:
                last_error = exc
                code = getattr(exc, 'code', None)
                logger.warning('BYTE AI model unavailable: model=%s type=%s code=%s', model, type(exc).__name__, code)
                # Configuration/auth errors will not be fixed by switching models.
                if code in (400, 401, 403):
                    raise
                # 404, 429 and 5xx may be model-specific or temporary: try fallback.
                continue
    if last_error:
        raise last_error
    raise ValueError('No AI model configured')


@require_http_methods(['GET', 'POST'])
def ai_chat(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Сессия завершилась. Войдите в кабинет заново.'}, status=401)
    if request.method == 'GET':
        return JsonResponse({'ok': True, 'history': request.session.get('ai_history', []), 'configured': bool(settings.GEMINI_API_KEY)})
    try:
        if len(request.body) > 20000: raise ValueError()
        data = json.loads(request.body)
        if not isinstance(data, dict): raise ValueError()
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Некорректный запрос.'}, status=400)
    lock = f'byte-ai-busy:{request.user.pk}'
    if data.get('action') == 'clear':
        if cache.get(lock): return JsonResponse({'ok': False, 'error': 'Дождитесь завершения ответа.'}, status=409)
        request.session.pop('ai_history', None); return JsonResponse({'ok': True})
    question = data.get('question')
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        return JsonResponse({'ok': False, 'error': 'Введите вопрос длиной от 1 до 4000 символов.'}, status=400)
    if not settings.GEMINI_API_KEY:
        return JsonResponse({'ok': False, 'error': 'BYTE AI ещё не подключён. Проверьте GEMINI_API_KEY на сервере.'}, status=503)
    if not cache.add(lock, True, timeout=50):
        return JsonResponse({'ok': False, 'error': 'Предыдущий ответ ещё готовится.'}, status=429)
    try:
        if not cache.add(f'byte-ai-rate:{request.user.pk}', True, timeout=4):
            return JsonResponse({'ok': False, 'error': 'Подождите несколько секунд перед следующим вопросом.'}, status=429)
        context = ''
        slug = data.get('section')
        if isinstance(slug, str) and slug:
            from .learning import visible_sections
            section = next((s for s in visible_sections() if s.slug == slug), None)
            if section:
                context = '\n\nОткрытый урок: ' + section.title + '\n' + strip_tags(section.content)[:6000]
        history = request.session.get('ai_history', [])[-10:]
        answer = generate_answer(question.strip(), history, context)
        request.session['ai_history'] = (history + [{'role':'user','text':question.strip()},{'role':'model','text':answer}])[-12:]
        return JsonResponse({'ok': True, 'answer': answer})
    except Exception as exc:
        code = getattr(exc, 'code', None)
        logger.warning('BYTE AI provider failure after fallback: type=%s code=%s', type(exc).__name__, code)
        message, status = 'BYTE AI временно перегружен. Попробуйте отправить вопрос ещё раз.', 503
        if code == 429: message, status = 'Лимит AI временно исчерпан. Попробуйте немного позже.', 429
        elif code in (400,401,403): message = 'BYTE AI не смог подключиться к сервису. Проверьте API-ключ и настройки модели.'
        elif code == 404: message = 'Выбранная AI-модель недоступна. Проверьте GEMINI_MODEL на сервере.'
        return JsonResponse({'ok': False, 'error': message}, status=status)
    finally:
        cache.delete(lock)
