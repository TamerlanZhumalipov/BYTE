"""Student learning: all grading and ownership checks happen server-side."""
import uuid
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import LessonProgress, Quiz, QuizAttempt


def visible_sections():
    # Reuse the navigation tree: a child of an unpublished ancestor stays private.
    from .views import _build_tree, _flatten
    roots, _ = _build_tree()
    return _flatten(roots)


def available_quizzes():
    ids = [s.pk for s in visible_sections()]
    return Quiz.objects.filter(is_published=True).filter(Q(section_id__in=ids) | Q(section__isnull=True))


@login_required
@require_POST
def lesson_complete(request, slug):
    section = next((s for s in visible_sections() if s.slug == slug and s.content.strip()), None)
    if section is None:
        raise Http404('Урок не найден')
    LessonProgress.objects.update_or_create(user=request.user, section=section, defaults={'completed': request.POST.get('completed') == '1'})
    return redirect('section', slug=slug)


@login_required
def quizzes(request):
    items = list(available_quizzes().annotate(question_count=Count('questions')).filter(question_count__gt=0))
    best = dict(QuizAttempt.objects.filter(user=request.user).values('quiz_id').annotate(best=Max('percent')).values_list('quiz_id', 'best'))
    for item in items:
        item.best = best.get(item.pk)
    return render(request, 'quizzes.html', {'active_tab': 'quizzes', 'quizzes': items})


@login_required
def quiz_detail(request, pk):
    quiz = get_object_or_404(available_quizzes(), pk=pk)
    questions = list(quiz.questions.all())
    if not questions:
        raise Http404('Тест пока не готов')
    error = ''
    selected = {}
    token = request.POST.get('submission_token', '')
    if request.method == 'POST':
        try:
            payload = signing.loads(token, salt='quiz-attempt', max_age=86400)
            if payload['user'] != request.user.pk or payload['quiz'] != quiz.pk:
                raise signing.BadSignature()
            key = uuid.UUID(payload['key'])
        except (signing.BadSignature, KeyError, ValueError, TypeError):
            error = 'Сессия теста истекла. Ответьте на вопросы ещё раз.'
        else:
            previous = QuizAttempt.objects.filter(submission_key=key, user=request.user).first()
            if previous:
                return redirect('quiz_result', pk=previous.pk)
            selected = {str(q.pk): request.POST.get(f'question_{q.pk}', '') for q in questions}
            if any(answer not in ('A', 'B', 'C', 'D') for answer in selected.values()):
                error = 'Ответьте на все вопросы, затем завершите тест.'
            else:
                review = [{'text': q.text, 'options': q.options, 'selected': selected[str(q.pk)], 'correct': q.correct, 'explanation': q.explanation, 'is_correct': selected[str(q.pk)] == q.correct} for q in questions]
                score = sum(row['is_correct'] for row in review)
                percent = round(100 * score / len(questions))
                attempt, _ = QuizAttempt.objects.get_or_create(submission_key=key, defaults={'user': request.user, 'quiz': quiz, 'quiz_title': quiz.title, 'score': score, 'total': len(questions), 'percent': percent, 'passed': score * 100 >= quiz.passing_percent * len(questions), 'review': review})
                return redirect('quiz_result', pk=attempt.pk)
    if not token or error.startswith('Сессия'):
        token = signing.dumps({'user': request.user.pk, 'quiz': quiz.pk, 'key': str(uuid.uuid4())}, salt='quiz-attempt')
    for q in questions:
        q.selected = selected.get(str(q.pk))
    return render(request, 'quiz_detail.html', {'active_tab': 'quizzes', 'quiz': quiz, 'questions': questions, 'submission_token': token, 'error': error})


@login_required
def quiz_result(request, pk):
    attempt = get_object_or_404(QuizAttempt, pk=pk, user=request.user)
    can_retry = attempt.quiz_id and available_quizzes().filter(pk=attempt.quiz_id).exists()
    return render(request, 'quiz_result.html', {'active_tab': 'results', 'attempt': attempt, 'can_retry': can_retry})


@login_required
def results(request):
    attempts = QuizAttempt.objects.filter(user=request.user)
    page = Paginator(attempts, 12).get_page(request.GET.get('page'))
    return render(request, 'results.html', {'active_tab': 'results', 'page_obj': page})
