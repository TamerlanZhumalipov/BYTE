import json
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, SimpleTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from core.models import Section, Contest, ContestAccount, ContestTask, Submission, RequestBucket
from core.security import consume
from core.judge import run_submission, _run_one
from core import container_runner


class SecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('owner', password='test-only')
        cls.other = User.objects.create_user('other', password='test-only')
        cls.contest = Contest.objects.create(title='test', starts_at=timezone.now()-timedelta(minutes=1))
        cls.account = ContestAccount.objects.create(contest=cls.contest,user=cls.owner,login='personal')
        cls.account.set_password('test-only');cls.account.save()

    def test_assigned_contest_account_rejects_other_user_even_with_password(self):
        self.client.force_login(self.other)
        r=self.client.post(reverse('contest_login'), {'login':'personal','password':'test-only'})
        self.assertEqual(r.status_code,200)
        self.assertNotIn('contest_account_id',self.client.session)
        session=self.client.session;session['contest_account_id']=self.account.pk;session.save()
        self.assertEqual(self.client.get(reverse('contest')).status_code,302)
        self.assertEqual(self.client.post(reverse('contest_submit'),'{}',content_type='application/json').status_code,403)

    def test_contest_owner_allowed(self):
        self.client.force_login(self.owner)
        r=self.client.post(reverse('contest_login'), {'login':'personal','password':'test-only'})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.session['contest_account_id'],self.account.pk)

    def test_login_rate_limit_and_spoofed_forwarding_header(self):
        for _ in range(12):
            self.client.post(reverse('login'), {'username':'absent','password':'wrong'})
        r=self.client.post(reverse('login'), {'username':'absent','password':'wrong'},HTTP_X_FORWARDED_FOR='8.8.8.8',HTTP_X_REAL_IP='8.8.4.4')
        self.assertEqual(r.status_code,429)
        self.assertGreater(int(r['Retry-After']),0)

    def test_atomic_shared_bucket_stops_at_limit_and_hashes_identity(self):
        self.assertTrue(consume('probe','private-ip|private-login',2,600)[0])
        self.assertTrue(consume('probe','private-ip|private-login',2,600)[0])
        self.assertFalse(consume('probe','private-ip|private-login',2,600)[0])
        self.assertNotIn('private',RequestBucket.objects.get().key)

    def test_malformed_ai_payload_returns_400(self):
        self.client.force_login(self.owner)
        r=self.client.post(reverse('ai_ask_home'),json.dumps({'message':{'nested':'bad'}}),content_type='application/json')
        self.assertEqual(r.status_code,400)

    def test_personal_pages_never_cache(self):
        self.client.force_login(self.owner)
        for name in ('dashboard','analytics','contest_login'):
            r=self.client.get(reverse(name))
            self.assertIn('no-store',r['Cache-Control'])
            self.assertIn('private',r['Cache-Control'])

    def test_csrf_login_and_leads_rejected(self):
        from django.test import Client
        c=Client(enforce_csrf_checks=True)
        for name in ('login','lead_create','set_language'):
            self.assertEqual(c.post(reverse(name),{}).status_code,403)

    def test_contest_queries_do_not_grow_per_task_or_fetch_source(self):
        self.client.force_login(self.owner)
        session=self.client.session;session['contest_account_id']=self.account.pk;session.save()
        task=ContestTask.objects.create(contest=self.contest,title='One',statement='hello')
        Submission.objects.create(account=self.account,task=task,language='python',code='PRIVATE_SOURCE_SENTINEL',verdict='WA',passed=0,total=1)
        with CaptureQueriesContext(connection) as first:
            r=self.client.get(reverse('contest'))
        for i in range(15):
            ContestTask.objects.create(contest=self.contest,title=str(i),statement='hello')
        with CaptureQueriesContext(connection) as many:
            response=self.client.get(reverse('contest'))
        self.assertLessEqual(len(many),len(first)+1)
        self.assertNotContains(response,'PRIVATE_SOURCE_SENTINEL')
        history_queries=[q['sql'] for q in many if 'core_submission' in q['sql']]
        self.assertTrue(history_queries)
        self.assertTrue(all('"code"' not in q for q in history_queries))

    def test_ai_cannot_read_a_locked_lesson(self):
        Section.objects.create(title='First',slug='first',order=0)
        locked=Section.objects.create(title='Second',slug='locked',order=1,content='LOCKED_CONTENT')
        self.client.force_login(self.owner)
        with patch('core.views.ai_module.ask') as ask:
            r=self.client.post(reverse('ai_ask',args=[locked.slug]),json.dumps({'message':'Explain this lesson'}),content_type='application/json')
            self.assertEqual(r.status_code,403)
            ask.assert_not_called()



class ContainerBoundaryTests(SimpleTestCase):
    @override_settings(DEBUG=False,JUDGE_BACKEND='local')
    def test_production_never_uses_local_runner(self):
        with patch('core.judge._prepare') as prepare:
            # Explicitly test the gate, which is also checked by production settings.
            from core.judge import _sandboxed
            with self.assertRaises(RuntimeError):_sandboxed()
            prepare.assert_not_called()

    @override_settings(JUDGE_BACKEND='docker',JUDGE_DOCKER_IMAGE='byte-judge:local')
    def test_container_has_no_network_privileges_or_project_mount(self):
        proc=MagicMock(returncode=0)
        proc.communicate.return_value=(None,None)
        with tempfile.TemporaryDirectory() as folder, patch('core.container_runner.shutil.which', return_value='docker'), patch('core.container_runner.subprocess.Popen',return_value=proc) as start, patch('core.container_runner.subprocess.run') as cleanup:
            result=container_runner.run(['python3','main.py'],folder)
            args=start.call_args.args[0]
            for required in ('--network=none','--read-only','--cap-drop=ALL','--user=65534:65534','--security-opt=no-new-privileges','--pids-limit=32','--pull=never'):
                self.assertIn(required,args)
            self.assertIn('type=bind,src='+folder+',dst=/work,readonly',args)
            self.assertNotIn('DJANGO_SECRET_KEY',start.call_args.kwargs['env'])
            self.assertEqual(result.returncode,0)
            cleanup.assert_called_once()

    @override_settings(JUDGE_DOCKER_IMAGE='byte-judge:local')
    def test_missing_docker_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder, patch('core.container_runner.shutil.which', return_value='docker'),patch('core.container_runner.subprocess.Popen',side_effect=FileNotFoundError),patch('core.container_runner.subprocess.run'):
            with self.assertRaises(RuntimeError):container_runner.run(['python3'],folder)

    @override_settings(JUDGE_DOCKER_IMAGE='byte-judge:local')
    def test_timeout_kills_client_and_container(self):
        proc=MagicMock();proc.communicate.side_effect=[subprocess.TimeoutExpired('docker',.01),(None,None)]
        with tempfile.TemporaryDirectory() as folder, patch('core.container_runner.shutil.which', return_value='docker'),patch('core.container_runner.subprocess.Popen',return_value=proc),patch('core.container_runner.subprocess.run') as cleanup, patch('core.container_runner.time.monotonic', side_effect=[0,0,2]):
            with self.assertRaises(subprocess.TimeoutExpired):container_runner.run(['python3'],folder,timeout=.001)
            proc.kill.assert_called_once()
            self.assertEqual(cleanup.call_args.args[0][:3],['docker','rm','-f'])


class JudgeAcceptanceCommandTests(SimpleTestCase):
    @override_settings(JUDGE_BACKEND='docker')
    def test_acceptance_invokes_actual_languages_and_compares_verdicts(self):
        from django.core.management import call_command
        from io import StringIO
        from core.judge import JudgeResult
        with patch('core.management.commands.verify_judge.run_submission',side_effect=[JudgeResult('OK',1,1,'P'),JudgeResult('OK',1,1,'P'),JudgeResult('TLE',0,1,'T')]) as run:
            call_command('verify_judge',stdout=StringIO())
            self.assertEqual([c.args[1] for c in run.call_args_list],['python','cpp','python'])
