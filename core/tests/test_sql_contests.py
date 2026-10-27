import copy
import json
from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, Client
from django.urls import reverse
from django.utils import timezone

from core.models import Contest, ContestAccount, ContestTask, TaskTest, Submission
from core.sql_demo import SPECS, students
from core.sql_engine import same_result, validate_fixture
from core.sql_judge import run_query, run_sql_submission


class SQLEngineTests(SimpleTestCase):
    fixture = students([[1, 'A', 35], [2, 'B', None], [3, 'A', 35]])

    def test_select_count_cte_join_and_aggregate(self):
        for query in ['SELECT * FROM students', 'SELECT count(*) FROM students',
                      'WITH s AS (SELECT * FROM students) SELECT name FROM s',
                      'SELECT a.id FROM students a JOIN students b ON a.id=b.id',
                      'SELECT name, ROUND(AVG(score), 1) FROM students GROUP BY name']:
            with self.subTest(query=query):
                self.assertEqual(run_query(query, self.fixture)['status'], 'OK')

    def test_mutations_files_extensions_system_tables_and_multiple_statements_denied(self):
        queries = ['DELETE FROM students', 'DROP TABLE students', 'UPDATE students SET score=50',
                   'CREATE TABLE bad(x)', "ATTACH DATABASE '/tmp/byte-must-not-open.db' AS other",
                   "VACUUM INTO '/tmp/byte-must-not-create.db'", 'PRAGMA database_list',
                   "SELECT load_extension('missing')", "SELECT readfile('/etc/passwd')",
                   'SELECT * FROM sqlite_master', 'SELECT * FROM pragma_table_info(\'students\')',
                   'SELECT 1; SELECT 2', 'BEGIN', 'SELECT randomblob(1000000000)']
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(run_query(query, self.fixture)['status'], 'RE')
        self.assertEqual(len(run_query('SELECT * FROM students', self.fixture)['rows']), 3)

    def test_recursive_query_time_limit(self):
        result = run_query('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n', self.fixture, .05)
        self.assertEqual(result['status'], 'TLE')

    def test_output_and_query_limits(self):
        self.assertEqual(run_query('SELECT * FROM students a, students b, students c, students d, students e, students f, students g', self.fixture)['status'], 'RE')
        self.assertEqual(run_query('SELECT 1 --' + 'a' * 65536, self.fixture)['status'], 'RE')

    def test_result_comparison_order_duplicates_null_columns_types(self):
        expected = {'columns': ['x'], 'rows': [[1], [1], [None]]}
        self.assertTrue(same_result({'columns':['alias'], 'rows':[[None],[1],[1]]}, expected, False))
        self.assertFalse(same_result({'columns':['x'], 'rows':[[None],[1],[1]]}, expected, True))
        self.assertFalse(same_result({'columns':['x'], 'rows':[[None],[1]]}, expected, False))
        self.assertFalse(same_result({'columns':['x'], 'rows':[[None],['1'],['1']]}, expected, False))
        self.assertFalse(same_result({'columns':['x','y'], 'rows':[]}, {'columns':['x'], 'rows':[]}, False))

    def test_seed_answers_pass_every_hidden_fixture(self):
        for spec in SPECS:
            task = SimpleNamespace(sql_sample=spec['sql_sample'], sql_reference=spec['sql_reference'], sql_ordered=spec['sql_ordered'], time_limit=2)
            result = run_sql_submission(spec['sql_reference'], task, spec['fixtures'])
            self.assertEqual((result.verdict, result.passed, result.total), ('OK', 6, 6))

    def test_hidden_errors_are_generic_and_bad_reference_is_configuration_error(self):
        spec = SPECS[0]
        task = SimpleNamespace(sql_sample=spec['sql_sample'], sql_reference=spec['sql_reference'], sql_ordered=True, time_limit=2)
        result = run_sql_submission('SELECT abs(-9223372036854775808)', task, spec['fixtures'])
        self.assertEqual(result.verdict, 'RE')
        self.assertNotIn('922337', result.message)
        task.sql_reference = 'SELECT broken FROM missing'
        with self.assertRaises(ValueError):
            run_sql_submission('SELECT 1', task, spec['fixtures'])

    def test_invalid_fixture_and_mismatched_schema(self):
        for fixture in ({}, {'tables':[]}, {'tables':[{'name':'sqlite_secret','columns':[['x','TEXT']], 'rows':[]}]},
                        students([[1, {'bad': 'cell'}, 3]])):
            with self.assertRaises((ValueError, TypeError)):
                validate_fixture(fixture)
        task = SimpleNamespace(sql_sample=students([]), sql_reference='SELECT 1', sql_ordered=False, time_limit=2)
        wrong = copy.deepcopy(students([])); wrong['tables'][0]['name'] = 'other'
        with self.assertRaises(ValueError):
            run_sql_submission('SELECT 1', task, [wrong])


class SQLContestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('sql-student', password='test-password')
        cls.contest = Contest.objects.create(title='SQL test', kind='sql', starts_at=timezone.now()-timedelta(minutes=1), duration_minutes=40)
        cls.tasks = []
        for i, spec in enumerate(SPECS, 1):
            task = ContestTask.objects.create(contest=cls.contest, order=i, **{k:v for k,v in spec.items() if k != 'fixtures'})
            cls.tasks.append(task)
            for j, fixture in enumerate(spec['fixtures']):
                TaskTest.objects.create(task=task, order=j, sql_fixture=fixture)
        cls.account = ContestAccount.objects.create(contest=cls.contest, user=cls.user, login='sql-test')
        cls.account.set_password('sql-password'); cls.account.save()
        cls.programming = Contest.objects.create(title='Python test', starts_at=timezone.now()-timedelta(minutes=1), duration_minutes=40)
        cls.programming_task = ContestTask.objects.create(contest=cls.programming, title='Sum', statement='sum')
        TaskTest.objects.create(task=cls.programming_task, input_data='1 2', expected_output='3')
        cls.programming_account = ContestAccount.objects.create(contest=cls.programming, login='python-test')

    def setUp(self):
        self.client.force_login(self.user)
        self.enter(self.account)

    def enter(self, account):
        session = self.client.session;session['contest_account_id'] = account.pk;session.save()

    def post(self, url='contest_sql_run', **changes):
        data = {'task_id':self.tasks[0].pk, 'language':'sql', 'code':SPECS[0]['sql_reference']}
        data.update(changes)
        return self.client.post(reverse(url), json.dumps(data), content_type='application/json')

    def test_preview_returns_table_without_submission_or_points(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['rows'][0], [3,'Дана',42])
        self.assertFalse(Submission.objects.exists())
        self.assertNotIn('reference', response.json())

    def test_submit_persists_score_and_history(self):
        response = self.post('contest_submit')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['submission']['verdict'], 'OK')
        self.assertEqual(response.json()['best'], 1)
        self.assertEqual(response.json()['submission']['passed'], 1)
        self.assertEqual(response.json()['submission']['total'], 1)
        self.assertEqual(response.json()['submission']['marks'], '')
        self.assertEqual(Submission.objects.get().language, 'sql')

    def test_wrong_answer(self):
        response = self.post('contest_submit', code='SELECT 1')
        self.assertEqual(response.json()['submission']['verdict'], 'WA')

    def test_partial_sql_scores_are_binary_and_solved_status_survives_failed_retry(self):
        from core.judge import JudgeResult
        with patch('core.views.run_sql_submission', return_value=JudgeResult('WA',5,6,'PPPPPF')):
            response = self.post('contest_submit').json()
        self.assertEqual((response['best'], response['submission']['passed'], response['submission']['total']), (0,0,1))
        self.assertEqual(Submission.objects.get().passed, 5)  # Internal diagnostics remain available.
        page = self.client.get(reverse('contest'))
        self.assertNotContains(page, 'id="cx-grid"')
        self.assertNotContains(page, 'cx-legend')
        task = page.context['contest_data']['tasks'][0]
        self.assertEqual((task['best'],task['total'],task['history'][0]['passed']), (0,1,0))
        Submission.objects.create(account=self.account,task=self.tasks[0],language='sql',code='',verdict='OK',passed=6,total=6,marks='PPPPPP')
        Submission.objects.create(account=self.account,task=self.tasks[0],language='sql',code='',verdict='WA',passed=5,total=6,marks='PPPPPF')
        task = self.client.get(reverse('contest')).context['contest_data']['tasks'][0]
        self.assertEqual(task['best'], 1)
        self.assertEqual(task['history'][0]['passed'], 0)
        self.assertTrue(all(h['total']==1 and h['marks']=='' for h in task['history']))

    def test_no_cross_contest_task_or_language(self):
        self.assertEqual(self.post(task_id=self.programming_task.pk).status_code, 404)
        self.assertEqual(self.post('contest_submit', language='python', code='print(1)').status_code, 400)
        self.enter(self.programming_account)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.post('contest_submit', task_id=self.programming_task.pk).status_code, 400)

    def test_programming_judge_still_used(self):
        from core.judge import JudgeResult
        self.enter(self.programming_account)
        with patch('core.views.run_submission', return_value=JudgeResult('OK',1,1,'P')) as judge:
            response = self.post('contest_submit', task_id=self.programming_task.pk, language='python', code='print(3)')
        self.assertEqual(response.status_code, 200);judge.assert_called_once()

    def test_running_window_and_three_task_requirement(self):
        for start in (timezone.now()+timedelta(hours=1), timezone.now()-timedelta(hours=2)):
            Contest.objects.filter(pk=self.contest.pk).update(starts_at=start)
            self.assertEqual(self.post().status_code, 403)
            self.assertEqual(self.post('contest_submit').status_code, 403)
        Contest.objects.filter(pk=self.contest.pk).update(starts_at=timezone.now()-timedelta(minutes=1))
        self.tasks[2].delete()
        self.assertEqual(self.post().status_code, 409)
        self.assertEqual(self.post('contest_submit').status_code, 409)

    def test_rate_limit_shared_by_preview_and_submit(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 429)
        self.assertEqual(self.post('contest_submit').status_code, 429)

    def test_auth_csrf_and_invalid_payload(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('contest_sql_run'), '{}', content_type='application/json').status_code, 403)
        for payload in ('{}','[]','null','not json'):
            self.assertEqual(self.client.post(reverse('contest_sql_run'),payload,content_type='application/json').status_code, 400)
        self.client.logout()
        self.assertEqual(self.post().status_code, 302)

    def test_public_page_does_not_leak_hidden_values_or_answer(self):
        fixture = students([[99,'HIDDEN_SENTINEL',49]])
        TaskTest.objects.filter(task=self.tasks[0]).update(sql_fixture=fixture)
        for lang in ('ru','kk'):
            session = self.client.session;session['site_language']=lang;session.save()
            response = self.client.get(reverse('contest'))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response,'HIDDEN_SENTINEL')
            self.assertNotContains(response,SPECS[0]['sql_reference'])
            self.assertContains(response,'id="cx-run"')
            self.assertNotContains(response,'<option value="python">')
        self.enter(self.programming_account)
        response = self.client.get(reverse('contest'))
        self.assertNotContains(response,'id="cx-run"')
        self.assertContains(response,'<option value="python">')

    def test_mode_selection_login(self):
        session=self.client.session;session.pop('contest_account_id');session.save()
        response=self.client.post(reverse('contest_login'),{'kind':'programming','login':'sql-test','password':'sql-password'})
        self.assertEqual(response.status_code,200)
        self.assertNotIn('contest_account_id',self.client.session)
        response=self.client.post(reverse('contest_login'),{'kind':'sql','login':'sql-test','password':'sql-password'})
        self.assertEqual(response.status_code,302)

    def test_model_validation(self):
        self.contest.kind='programming'
        with self.assertRaises(ValidationError): self.contest.full_clean()
        self.programming_task.sql_sample=students([])
        with self.assertRaises(ValidationError): self.programming_task.full_clean()
        bad=TaskTest(task=self.tasks[0],input_data='stdin',sql_fixture=students([]))
        with self.assertRaises(ValidationError): bad.full_clean()

    def test_seed_command_builds_three_tasks_without_changing_existing_contests(self):
        output=StringIO();call_command('seed_sql_contest',stdout=output)
        new=Contest.objects.exclude(pk__in=[self.contest.pk,self.programming.pk]).get()
        self.assertEqual(new.kind,'sql');self.assertEqual(new.tasks.count(),3)
        self.assertTrue(all(t.tests.count()==6 for t in new.tasks.all()))
        self.assertEqual(self.contest.tasks.count(),3)
