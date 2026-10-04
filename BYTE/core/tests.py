import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Section, LessonProgress, Quiz, Question, QuizAttempt


class LearningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='student', password='test-password')
        self.other = get_user_model().objects.create_user(username='other')
        self.section = Section.objects.create(title='Python', slug='python', content='<p>Learn Python</p>')
        self.quiz = Quiz.objects.create(title='Python quiz', section=self.section, is_published=True)
        self.question = Question.objects.create(quiz=self.quiz, text='2 + 2?', option_a='4', option_b='5', option_c='6', option_d='7', correct='A', explanation='Two plus two is four.')
        self.client.force_login(self.user)

    def submit(self, answer='A', token=None):
        url = reverse('quiz_detail', args=[self.quiz.pk])
        if token is None:
            token = self.client.get(url).context['submission_token']
        return self.client.post(url, {'submission_token': token, f'question_{self.question.pk}': answer})

    def test_pages_and_anonymous_redirect(self):
        for url in ['/app/', '/app/quizzes/', '/app/results/', '/contest/login/', self.section.get_absolute_url()]:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get('/app/').status_code, 302)

    def test_progress_is_personal_idempotent_and_reversible(self):
        url = reverse('lesson_complete', args=[self.section.slug])
        self.assertEqual(self.client.get(url).status_code, 405)
        for _ in range(2):
            self.client.post(url, {'completed': '1'})
        self.assertEqual(LessonProgress.objects.count(), 1)
        self.assertEqual(self.client.get('/app/').context['progress_percent'], 100)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/app/').context['progress_percent'], 0)
        self.client.force_login(self.user)
        self.client.post(url, {'completed': '0'})
        self.assertEqual(self.client.get('/app/').context['progress_percent'], 0)

    def test_visit_does_not_complete_lesson(self):
        self.client.get(self.section.get_absolute_url())
        self.assertFalse(LessonProgress.objects.get().completed)
        self.assertEqual(self.client.get('/app/').context['resume_section'], self.section)

    def test_unpublished_ancestor_blocks_content_progress_and_quiz(self):
        parent = Section.objects.create(title='Private', slug='private', is_published=False)
        self.section.parent = parent
        self.section.save()
        self.assertEqual(self.client.get(self.section.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.post(reverse('lesson_complete', args=[self.section.slug]), {'completed': '1'}).status_code, 404)
        self.assertEqual(self.client.get(reverse('quiz_detail', args=[self.quiz.pk])).status_code, 404)
        self.assertEqual(self.client.get('/app/').context['lesson_count'], 0)

    def test_empty_sections_are_not_counted_or_completable(self):
        empty = Section.objects.create(title='Soon', slug='soon')
        self.assertEqual(self.client.get('/app/').context['lesson_count'], 1)
        self.assertEqual(self.client.post(reverse('lesson_complete', args=[empty.slug]), {'completed': '1'}).status_code, 404)

    def test_grades_are_computed_on_server(self):
        response = self.submit('B')
        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get()
        self.assertEqual(attempt.score, 0)
        self.assertFalse(attempt.passed)
        self.assertContains(self.client.get(response.url), 'Правильный ответ')

    def test_submission_replay_does_not_duplicate(self):
        token = self.client.get(reverse('quiz_detail', args=[self.quiz.pk])).context['submission_token']
        self.submit(token=token)
        self.submit(token=token)
        self.assertEqual(QuizAttempt.objects.count(), 1)
        self.assertEqual(QuizAttempt.objects.get().percent, 100)

    def test_invalid_or_missing_answers_are_not_saved(self):
        for answer in ['', 'INVALID']:
            self.assertEqual(self.submit(answer).status_code, 200)
        self.assertEqual(QuizAttempt.objects.count(), 0)

    def test_tampered_and_other_users_tokens_are_rejected(self):
        token = self.client.get(reverse('quiz_detail', args=[self.quiz.pk])).context['submission_token']
        self.submit(token='invalid')
        self.client.force_login(self.other)
        self.submit(token=token)
        self.assertEqual(QuizAttempt.objects.count(), 0)

    def test_results_private_and_snapshot_survives_edit_and_delete(self):
        response = self.submit()
        self.question.text = 'New question'
        self.question.save()
        self.quiz.delete()
        self.assertContains(self.client.get(response.url), '2 + 2?')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(response.url).status_code, 404)
        self.assertNotContains(self.client.get('/app/results/'), 'Python quiz')

    def test_unpublished_and_empty_quizzes_are_not_offered(self):
        self.quiz.is_published = False
        self.quiz.save()
        self.assertNotContains(self.client.get('/app/quizzes/'), 'Python quiz')
        self.assertEqual(self.client.get(reverse('quiz_detail', args=[self.quiz.pk])).status_code, 404)
        self.quiz.is_published = True
        self.quiz.save()
        self.question.delete()
        self.assertNotContains(self.client.get('/app/quizzes/'), 'Python quiz')

    def test_csrf_required(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('lesson_complete', args=[self.section.slug]), {'completed': '1'}).status_code, 403)


class AITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username='student')
        self.client.force_login(self.user)

    def post(self, data):
        return self.client.post('/api/ai/', json.dumps(data), content_type='application/json')

    def test_anonymous_returns_json(self):
        self.client.logout()
        response = self.post({'question': 'Hello'})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()['ok'])

    @override_settings(GEMINI_API_KEY='')
    def test_missing_key_does_not_break_site(self):
        self.assertEqual(self.client.get('/app/').status_code, 200)
        self.assertFalse(self.client.get('/api/ai/').json()['configured'])
        self.assertEqual(self.post({'question': 'Hello'}).status_code, 503)

    def test_invalid_payloads(self):
        for data in [[], None, {'question': 1}, {'question': ''}, {'question': 'a' * 4001}]:
            self.assertEqual(self.post(data).status_code, 400)
        self.assertEqual(self.client.post('/api/ai/', '{bad', content_type='application/json').status_code, 400)

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('core.ai.generate_answer', return_value='Use a loop.')
    def test_context_history_and_clear(self, generate):
        section = Section.objects.create(title='Loops', slug='loops', content='<p>Range</p>')
        response = self.post({'question': 'Explain', 'section': section.slug})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Range', generate.call_args.args[2])
        self.assertNotIn('<p>', generate.call_args.args[2])
        self.assertEqual(len(self.client.get('/api/ai/').json()['history']), 2)
        cache.clear()
        self.post({'question': 'More'})
        self.assertEqual(len(generate.call_args.args[1]), 2)
        self.assertEqual(self.post({'action': 'clear'}).status_code, 200)
        self.assertEqual(self.client.get('/api/ai/').json()['history'], [])

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('core.ai.generate_answer', return_value='Answer')
    def test_private_lesson_not_sent_to_provider(self, generate):
        Section.objects.create(title='Secret', slug='secret', content='SECRET DATA', is_published=False)
        self.post({'question': 'Explain', 'section': 'secret'})
        self.assertEqual(generate.call_args.args[2], '')

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('core.ai.generate_answer', side_effect=RuntimeError('provider secret'))
    def test_provider_error_is_safe_and_lock_released(self, generate):
        response = self.post({'question': 'Hello'})
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, 'provider secret', status_code=503)
        self.assertFalse(cache.get(f'byte-ai-busy:{self.user.pk}'))
        self.assertEqual(self.client.get('/api/ai/').json()['history'], [])

    @override_settings(GEMINI_API_KEY='test-key')
    @patch('core.ai.generate_answer', return_value='Answer')
    def test_rate_limit(self, generate):
        self.assertEqual(self.post({'question': 'Hello'}).status_code, 200)
        self.assertEqual(self.post({'question': 'Again'}).status_code, 429)
        self.assertEqual(generate.call_count, 1)

    @override_settings(GEMINI_API_KEY='test-key')
    def test_busy_chat_cannot_be_cleared(self):
        cache.set(f'byte-ai-busy:{self.user.pk}', True, 30)
        self.assertEqual(self.post({'action': 'clear'}).status_code, 409)
