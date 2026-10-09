import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Section, TopicQuiz, QuizQuestion, QuizChoice, QuizAttempt, Contest, ContestAccount, ContestTask, TaskTest


class ReactPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='react-student', password='test-password-123')
        self.first = Section.objects.create(slug='first', title='First', title_kk='Бірінші', content='<p>Visible lesson</p>', order=1)
        self.second = Section.objects.create(slug='second', title='Second', content='PRIVATE_LOCKED_LESSON', order=2)
        self.quiz = TopicQuiz.objects.create(topic=self.first)
        self.question = QuizQuestion.objects.create(quiz=self.quiz, text='Choose', text_kk='Таңдаңыз')
        self.correct = QuizChoice.objects.create(question=self.question, text='Yes', text_kk='Иә', is_correct=True)
        self.wrong = QuizChoice.objects.create(question=self.question, text='No', is_correct=False)

    def get_props(self, url):
        return self.client.get(url, HTTP_ACCEPT='application/json').json()

    def test_public_shell_and_assets(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'react.html')
        self.assertContains(response, 'id="root"')
        self.assertContains(response, 'type="module"')
        self.assertNotContains(response, 'js/main.js')
        self.assertTrue(response.context['react_js'].startswith('/static/react/assets/'))

    def test_authenticated_routes_enforce_login(self):
        for name in ('dashboard','analytics','contest','contest_login'):
            self.assertEqual(self.client.get(reverse(name)).status_code,302)
        self.assertEqual(self.client.get(reverse('section',args=['first'])).status_code,302)

    def test_materials_omit_locked_content_and_keep_localization(self):
        self.client.force_login(self.user)
        data = self.get_props(reverse('dashboard'))
        self.assertNotIn('PRIVATE_LOCKED_LESSON',json.dumps(data))
        self.assertTrue(data['props']['roots'][1]['locked'])
        self.assertEqual(self.client.get(reverse('section',args=['second'])).status_code,302)
        self.client.post(reverse('set_language'), {'language':'kk','next':'/app/'})
        data=self.get_props(reverse('section',args=['first']))
        self.assertEqual(data['props']['current']['title'],'Бірінші')
        self.assertEqual(data['props']['current']['content'],'<p>Visible lesson</p>')
        self.assertNotIn('PRIVATE_LOCKED_LESSON',json.dumps(data))

    def test_quiz_has_no_correctness_flags_before_submit(self):
        self.client.force_login(self.user)
        data=self.get_props(reverse('topic_quiz',args=['first']))
        self.assertIsNone(data['props']['result'])
        self.assertNotIn('is_correct',json.dumps(data['props']['questions']))
        self.assertNotIn('correct_choice',json.dumps(data))
        response=self.client.post(reverse('topic_quiz',args=['first']),{f'q_{self.question.pk}':str(self.correct.pk)})
        result=response.context['bootstrap']['props']['result']
        self.assertTrue(result['passed'])
        self.assertEqual(result['next']['id'],self.second.pk)
        self.assertTrue(QuizAttempt.objects.get(user=self.user).passed)
        self.assertEqual(self.client.get(reverse('section',args=['second'])).status_code,200)

    def test_wrong_quiz_does_not_unlock_next(self):
        self.client.force_login(self.user)
        response=self.client.post(reverse('topic_quiz',args=['first']),{f'q_{self.question.pk}':str(self.wrong.pk)})
        self.assertFalse(response.context['bootstrap']['props']['result']['passed'])
        self.assertEqual(self.client.get(reverse('section',args=['second'])).status_code,302)

    def test_login_keeps_next_errors_and_does_not_serialize_password(self):
        response=self.client.post(reverse('login'),{'username':'react-student','password':'WRONG_SECRET','next':'/app/analytics/'})
        self.assertTrue(response.context['bootstrap']['props']['error'])
        self.assertNotContains(response,'WRONG_SECRET')
        response=self.client.post(reverse('login'),{'username':'react-student','password':'test-password-123','next':'/app/analytics/'})
        self.assertRedirects(response,'/app/analytics/',fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('logout')).status_code,405)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('dashboard')).status_code,302)

    def test_csrf_still_required_for_login_and_quiz(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('login'),{'username':'react-student','password':'test-password-123'}).status_code,403)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('topic_quiz',args=['first']),{}).status_code,403)
        response=client.get(reverse('topic_quiz',args=['first']))
        token=response.context['bootstrap']['csrf']
        response=client.post(reverse('topic_quiz',args=['first']),{'csrfmiddlewaretoken':token,f'q_{self.question.pk}':self.correct.pk})
        self.assertEqual(response.status_code,200)

    def test_json_escapes_script_in_authored_titles(self):
        self.first.title='</script><script>alert(1)</script>'
        self.first.save()
        self.client.force_login(self.user)
        response=self.client.get(reverse('dashboard'))
        self.assertNotContains(response,'</script><script>alert(1)</script>')
        self.assertContains(response,'\\u003C/script\\u003E')
        self.assertIn('no-store',response['Cache-Control'])

    def test_contest_payload_does_not_expose_judge_tests_or_credentials(self):
        contest=Contest.objects.create(title='Contest',starts_at=timezone.now()-timedelta(minutes=1))
        account=ContestAccount.objects.create(contest=contest,login='contest-user')
        account.set_password('contest-secret');account.save()
        task=ContestTask.objects.create(contest=contest,title='Task',statement='<p>Print a number</p>')
        TaskTest.objects.create(task=task,input_data='SECRET_INPUT',expected_output='SECRET_OUTPUT')
        self.client.force_login(self.user)
        self.client.post(reverse('contest_login'),{'login':account.login,'password':'contest-secret'})
        data=self.get_props(reverse('contest'))
        self.assertEqual(data['props']['tasks'][0]['title'],'Task')
        for secret in ('SECRET_INPUT','SECRET_OUTPUT','password_hash','contest-secret'):
            self.assertNotIn(secret,json.dumps(data))
        contest.starts_at=timezone.now()+timedelta(days=1);contest.save()
        data=self.get_props(reverse('contest'))
        self.assertEqual(data['props']['state'],'upcoming')
        self.assertEqual(data['props']['tasks'],[])

    @override_settings(REACT_FRONTEND_ENABLED=False)
    def test_legacy_fallback(self):
        self.client.force_login(self.user)
        self.assertTemplateUsed(self.client.get(reverse('dashboard')),'dashboard.html')
        self.assertTemplateUsed(self.client.get(reverse('analytics')),'analytics.html')

    @patch('core.views.ai_module.ask',return_value='Ответ BYTE AI')
    @patch('core.views.ai_module.is_configured',return_value=True)
    def test_ai_endpoint_preserved(self,configured,ask):
        self.client.force_login(self.user)
        response=self.client.post(reverse('ai_ask_home'),json.dumps({'message':'Explain Python','history':[]}),content_type='application/json')
        self.assertEqual(response.json()['content'],'Ответ BYTE AI')
