from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.urls import reverse
from django.utils import timezone


# ---------------------------------------------------------------------------
# Заявки с лендинга
# ---------------------------------------------------------------------------

class Lead(models.Model):
    PLAN_CHOICES = [
        ("start", "Старт"),
        ("mentor", "Ментор"),
    ]
    name = models.CharField("Имя", max_length=120)
    phone = models.CharField("Телефон", max_length=32)
    plan = models.CharField("Пакет", max_length=10, choices=PLAN_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "заявка"
        verbose_name_plural = "заявки"

    def __str__(self):
        return f"{self.name} ({self.phone})"


# ---------------------------------------------------------------------------
# Материалы: разделы (темы ЕНТ) и подразделы любой вложенности
# ---------------------------------------------------------------------------

class Section(models.Model):
    """Раздел материалов.

    Раздел без родителя — это тема ЕНТ (их около 16).
    Раздел с родителем — подраздел; вложенность может быть любой глубины.
    """
    title = models.CharField("Название", max_length=200)
    slug = models.SlugField("Адрес (латиницей)", max_length=120, unique=True)
    parent = models.ForeignKey(
        "self", verbose_name="Родительский раздел", null=True, blank=True,
        related_name="children", on_delete=models.CASCADE,
        help_text="Оставьте пустым, если это самостоятельная тема.",
    )
    order = models.PositiveIntegerField("Порядок", default=0)
    summary = models.CharField("Краткое описание", max_length=255, blank=True)
    content = models.TextField(
        "Содержимое (HTML)", blank=True,
        help_text="Можно использовать теги: h2, h3, p, ul, ol, table, pre, code, div class=\"note\".",
    )
    is_published = models.BooleanField("Показывать ученикам", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "раздел материалов"
        verbose_name_plural = "материалы"

    def __str__(self):
        return f"{self.parent} → {self.title}" if self.parent_id else self.title

    def get_absolute_url(self):
        return reverse("section", args=[self.slug])


# ---------------------------------------------------------------------------
# Лайв-контест
# ---------------------------------------------------------------------------

class Contest(models.Model):
    title = models.CharField("Название", max_length=200)
    starts_at = models.DateTimeField("Начало")
    duration_minutes = models.PositiveIntegerField("Длительность, минут", default=90)

    class Meta:
        ordering = ["-starts_at"]
        verbose_name = "контест"
        verbose_name_plural = "контесты"

    def __str__(self):
        return self.title

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.duration_minutes)

    def state(self, now=None):
        """upcoming — ещё не начался, running — идёт, finished — закончился."""
        now = now or timezone.now()
        if now < self.starts_at:
            return "upcoming"
        if now >= self.ends_at:
            return "finished"
        return "running"


class ContestTask(models.Model):
    contest = models.ForeignKey(Contest, verbose_name="Контест", related_name="tasks", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField("Номер", default=1)
    title = models.CharField("Название", max_length=200)
    statement = models.TextField("Условие (HTML)")
    time_limit = models.FloatField("Лимит времени на один тест, сек", default=2.0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "задача контеста"
        verbose_name_plural = "задачи контеста"

    def __str__(self):
        return f"{self.contest.title}: {self.order}. {self.title}"


class TaskTest(models.Model):
    """Один тест к задаче: входные данные и правильный ответ."""
    task = models.ForeignKey(ContestTask, verbose_name="Задача", related_name="tests", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField("Номер", default=0)
    input_data = models.TextField("Входные данные", blank=True)
    expected_output = models.TextField("Правильный ответ")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "тест"
        verbose_name_plural = "тесты"

    def __str__(self):
        return f"Тест {self.order} — {self.task.title}"


class ContestAccount(models.Model):
    """Отдельный логин и пароль участника для входа в контест.

    Не связан с логином на сайте: куратор выдаёт его каждому участнику вручную.
    """
    contest = models.ForeignKey(Contest, verbose_name="Контест", related_name="accounts", on_delete=models.CASCADE)
    full_name = models.CharField("Имя участника", max_length=150, blank=True)
    login = models.CharField("Логин контеста", max_length=50, unique=True)
    password_hash = models.CharField(max_length=256, editable=False)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        ordering = ["contest", "login"]
        verbose_name = "участник контеста"
        verbose_name_plural = "участники контеста"

    def __str__(self):
        return f"{self.login} ({self.full_name or 'без имени'})"

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)


class Submission(models.Model):
    VERDICTS = [
        ("PENDING", "Проверяется"),
        ("OK", "Принято"),
        ("WA", "Неверный ответ"),
        ("TLE", "Превышено время"),
        ("RE", "Ошибка выполнения"),
        ("CE", "Ошибка компиляции"),
    ]
    LANGUAGES = [("python", "Python"), ("cpp", "C++")]

    account = models.ForeignKey(ContestAccount, verbose_name="Участник", related_name="submissions", on_delete=models.CASCADE)
    task = models.ForeignKey(ContestTask, verbose_name="Задача", related_name="submissions", on_delete=models.CASCADE)
    language = models.CharField("Язык", max_length=10, choices=LANGUAGES)
    code = models.TextField("Код")
    verdict = models.CharField("Вердикт", max_length=8, choices=VERDICTS, default="PENDING")
    passed = models.PositiveSmallIntegerField("Пройдено тестов", default=0)
    total = models.PositiveSmallIntegerField("Всего тестов", default=0)
    marks = models.CharField("Результат по тестам", max_length=500, blank=True)
    message = models.TextField("Сообщение проверки", blank=True)
    created_at = models.DateTimeField("Отправлено", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "отправка"
        verbose_name_plural = "отправки"

    def __str__(self):
        return f"{self.account.login} · {self.task.title} · {self.passed}/{self.total}"
