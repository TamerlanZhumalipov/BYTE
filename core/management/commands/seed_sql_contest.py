import secrets
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Contest, ContestTask, TaskTest, ContestAccount
from core.sql_demo import SPECS
from core.sql_judge import run_query


class Command(BaseCommand):
    help = 'Создаёт отдельный SQL-контест: 3 задачи, по 6 скрытых наборов, вход участника.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=40)
        parser.add_argument('--starts-in', type=int, default=10)

    @transaction.atomic
    def handle(self, *args, **options):
        if not 1 <= options['minutes'] <= 240 or options['starts_in'] < 0:
            raise CommandError('Длительность: 1–240 минут; начало — не раньше текущего времени.')
        contest = Contest.objects.create(title='BYTE SQL · Фильтрация, группы и JOIN', kind='sql',
            starts_at=timezone.now() + timedelta(minutes=options['starts_in']), duration_minutes=options['minutes'])
        for order, spec in enumerate(SPECS, 1):
            fields = {key: value for key, value in spec.items() if key != 'fixtures'}
            task = ContestTask(contest=contest, order=order, time_limit=2, **fields)
            task.full_clean()
            task.save()
            for i, fixture in enumerate(spec['fixtures'], 1):
                result = run_query(task.sql_reference, fixture)
                if result['status'] != 'OK':
                    raise CommandError('Эталон не проходит проверку: ' + str(result))
                case = TaskTest(task=task, order=i, sql_fixture=fixture)
                case.full_clean()
                case.save()
        password = secrets.token_urlsafe(12)
        account = ContestAccount(contest=contest, login=f'sql{contest.pk}', full_name='Демо SQL')
        account.set_password(password)
        account.save()
        self.stdout.write(self.style.SUCCESS(f'SQL-контест создан: id={contest.pk}, 3 задачи × 6 скрытых наборов.'))
        self.stdout.write(f'Начало: {timezone.localtime(contest.starts_at):%d.%m.%Y %H:%M}; длительность: {contest.duration_minutes} мин.')
        self.stdout.write(f'Выберите SQL на странице входа. Логин: {account.login}; пароль: {password}')
        self.stdout.write('Для учеников создайте отдельные аккаунты через админку или create_contest_accounts.')
