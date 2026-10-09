from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from core.models import Textbook, TextbookReference, ENTTopic
from core.textbooks import book_reply, for_topics
from core.forecast import get_forecast


class TextbookTests(TestCase):
    def setUp(self):
        self.book = Textbook.objects.get(isbn='978-601-331-945-2')
        self.user = get_user_model().objects.create_user('reader', password='test')

    def test_seed_and_exact_pages(self):
        self.assertEqual(self.book.references.count(), 18)
        answer = book_reply('Какой учебник почитать про while?')
        self.assertIn('страницы 98', answer)
        self.assertIn('2021', answer)
        self.assertIn('қазақша', answer)
        self.assertNotIn('страницы 104', answer)
        self.assertIsNone(book_reply('Объясни while'))

    def test_unverified_and_inactive_not_recommended(self):
        self.book.references.update(verified=False)
        self.assertIn('нет проверенной ссылки', book_reply('книга про while'))
        self.book.references.update(verified=True)
        self.book.is_active = False
        self.book.save()
        self.assertIn('нет проверенной ссылки', book_reply('книга про while'))

    def test_no_fabrication_and_language(self):
        self.assertIn('нет проверенной ссылки', book_reply('учебник про рекурсию'))
        self.assertIn('98-беттен', book_reply('while туралы қай кітап оқу керек?'))
        self.assertIn('нет проверенной ссылки', book_reply('учебник information'))

    def test_admin_validation(self):
        ref = self.book.references.first()
        ref.page_start = 999
        with self.assertRaises(ValidationError):
            ref.full_clean()
        ref.page_start = 7
        ref.verification_note = ''
        with self.assertRaises(ValidationError):
            ref.full_clean()

    def test_topic_catalog_and_forecast(self):
        topic = ENTTopic.objects.get(code='01', specification__year=2026)
        self.assertEqual(for_topics([topic.pk])[topic.pk][0]['page_start'], 13)
        forecast = get_forecast(self.user)
        self.assertTrue(any(r['reading'] for r in forecast['recommendations']))
        self.assertIsNone(forecast['score'])

    def test_chat_without_gemini_and_auth(self):
        url = reverse('ai_ask_home')
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.post(url, data={'message': 'учебник про while', 'history': []}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('страницы 98', response.json()['content'])

    def test_analytics_renders_both_languages(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('analytics')), 'Что почитать')
        session = self.client.session
        session['site_language'] = 'kk'
        session.save()
        self.assertContains(self.client.get(reverse('analytics')), 'Не оқу керек')
