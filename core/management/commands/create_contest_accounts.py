import random
import string

from django.core.management.base import BaseCommand, CommandError

from core.models import Contest, ContestAccount

# Без похожих символов (0/O, 1/l/I), чтобы пароль было легко переписать
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


class Command(BaseCommand):
    help = (
        "Создаёт участников контеста: для каждого имени — случайные логин и пароль. "
        "Пример: python3 manage.py create_contest_accounts 1 \"Иван Петров\" \"Айгерим С.\""
    )

    def add_arguments(self, parser):
        parser.add_argument("contest_id", type=int, help="ID контеста (виден в адресе в админке)")
        parser.add_argument("names", nargs="+", help="Имена участников")

    def handle(self, *args, **options):
        contest = Contest.objects.filter(pk=options["contest_id"]).first()
        if contest is None:
            raise CommandError(f"Контест с id={options['contest_id']} не найден.")

        rng = random.SystemRandom()
        rows = []
        for name in options["names"]:
            login = self._unique_login(rng)
            password = "".join(rng.choices(PASSWORD_ALPHABET, k=8))
            account = ContestAccount(contest=contest, login=login, full_name=name)
            account.set_password(password)
            account.save()
            rows.append((name, login, password))

        self.stdout.write(self.style.SUCCESS(f"Создано участников: {len(rows)} (контест «{contest.title}»)"))
        self.stdout.write("")
        self.stdout.write(f"{'Имя':<28}{'Логин':<12}Пароль")
        self.stdout.write("-" * 56)
        for name, login, password in rows:
            self.stdout.write(f"{name:<28}{login:<12}{password}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Сохраните пароли сейчас — потом они не показываются."))

    @staticmethod
    def _unique_login(rng):
        while True:
            login = "byte" + "".join(rng.choices(string.digits, k=4))
            if not ContestAccount.objects.filter(login=login).exists():
                return login
