import random
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Создаёт аккаунт ученика со случайным паролём и печатает "
        "логин/пароль в терминал, чтобы сразу передать ученику."
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Логин ученика, например ivan_petrov")
        parser.add_argument("--email", default="", help="Email ученика (необязательно)")
        parser.add_argument(
            "--password",
            default="",
            help="Задать пароль вручную вместо случайного",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]

        if User.objects.filter(username=username).exists():
            raise CommandError(f"Пользователь «{username}» уже существует.")

        password = options["password"] or self._generate_password()
        User.objects.create_user(username=username, email=email, password=password)

        self.stdout.write(self.style.SUCCESS("Аккаунт создан:"))
        self.stdout.write(f"  логин:  {username}")
        self.stdout.write(f"  пароль: {password}")
        self.stdout.write(self.style.WARNING("Сохраните пароль сейчас — второй раз он не выводится."))

    @staticmethod
    def _generate_password(length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(random.choices(alphabet, k=length))
