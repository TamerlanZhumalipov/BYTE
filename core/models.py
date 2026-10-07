from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.conf import settings
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
    title_kk = models.CharField("Название (қазақша)", max_length=200, blank=True)
    slug = models.SlugField("Адрес (латиницей)", max_length=120, unique=True)
    parent = models.ForeignKey(
        "self", verbose_name="Родительский раздел", null=True, blank=True,
        related_name="children", on_delete=models.CASCADE,
        help_text="Оставьте пустым, если это самостоятельная тема.",
    )
    order = models.PositiveIntegerField("Порядок", default=0)
    summary = models.CharField("Краткое описание", max_length=255, blank=True)
    summary_kk = models.CharField("Қысқаша сипаттама (қазақша)", max_length=255, blank=True)
    content = models.TextField(
        "Содержимое (HTML)", blank=True,
        help_text="Можно использовать теги: h2, h3, p, ul, ol, table, pre, code, div class=\"note\".",
    )
    content_kk = models.TextField(
        "Содержимое (қазақша, HTML)", blank=True,
        help_text="Қазақ тіліндегі материал. Егер бос болса, орысша нұсқа көрсетіледі.",
    )
    video_url = models.URLField(
        "Видео урока",
        blank=True,
        help_text="Ссылка на YouTube/Vimeo или другой источник видео. Для YouTube ссылка автоматически превращается во встраиваемую.",
    )
    video_url_kk = models.URLField(
        "Видео урока (қазақша)",
        blank=True,
        help_text="Қазақша видео сілтемесі. Егер бос болса, негізгі видео қолданылады.",
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

    @staticmethod
    def make_video_embed_url(url):
        """Возвращает ссылку, подходящую для iframe. YouTube нормализуется автоматически."""
        url = (url or "").strip()
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if host in {"youtu.be", "www.youtu.be"}:
                video_id = parsed.path.strip("/")
                return f"https://www.youtube.com/embed/{video_id}" if video_id else url
            if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
                if parsed.path.startswith("/embed/"):
                    return url
                video_id = parse_qs(parsed.query).get("v", [""])[0]
                return f"https://www.youtube.com/embed/{video_id}" if video_id else url
        except ValueError:
            return url
        return url

    @property
    def video_embed_url(self):
        return self.make_video_embed_url(self.video_url)


# ---------------------------------------------------------------------------
# Проверочные тесты по основным темам
# ---------------------------------------------------------------------------

class TopicQuiz(models.Model):
    topic = models.OneToOneField(
        Section,
        verbose_name="Основная тема",
        related_name="topic_quiz",
        on_delete=models.CASCADE,
        limit_choices_to={"parent__isnull": True},
    )
    pass_percent = models.PositiveSmallIntegerField(
        "Проходной процент",
        default=70,
        help_text="Минимальный процент правильных ответов, чтобы открыть следующую тему.",
    )

    class Meta:
        verbose_name = "тест по теме"
        verbose_name_plural = "тесты по темам"

    def __str__(self):
        return f"Тест: {self.topic.title}"


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(
        TopicQuiz,
        verbose_name="Тест",
        related_name="questions",
        on_delete=models.CASCADE,
    )
    order = models.PositiveSmallIntegerField("Порядок", default=1)
    text = models.TextField("Вопрос")
    text_kk = models.TextField("Сұрақ (қазақша)", blank=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "вопрос теста"
        verbose_name_plural = "вопросы теста"

    def __str__(self):
        return f"{self.quiz.topic.title}: {self.order}. {self.text[:60]}"


class QuizChoice(models.Model):
    question = models.ForeignKey(
        QuizQuestion,
        verbose_name="Вопрос",
        related_name="choices",
        on_delete=models.CASCADE,
    )
    text = models.CharField("Вариант ответа", max_length=500)
    text_kk = models.CharField("Жауап нұсқасы (қазақша)", max_length=500, blank=True)
    is_correct = models.BooleanField("Правильный ответ", default=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "вариант ответа"
        verbose_name_plural = "варианты ответа"

    def __str__(self):
        return self.text[:80]


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Ученик",
        related_name="topic_quiz_attempts",
        on_delete=models.CASCADE,
    )
    quiz = models.ForeignKey(
        TopicQuiz,
        verbose_name="Тест",
        related_name="attempts",
        on_delete=models.CASCADE,
    )
    score_percent = models.PositiveSmallIntegerField("Результат, %")
    correct_count = models.PositiveSmallIntegerField("Правильных ответов")
    total_questions = models.PositiveSmallIntegerField("Всего вопросов")
    passed = models.BooleanField("Тест пройден", default=False)
    answers = models.JSONField("Ответы", default=dict, blank=True)
    created_at = models.DateTimeField("Попытка", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "попытка теста"
        verbose_name_plural = "результаты тестов"

    def __str__(self):
        return f"{self.user} · {self.quiz.topic.title} · {self.score_percent}%"


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


# ---------------------------------------------------------------------------
# ИИ-помощник: история вопросов учеников
# ---------------------------------------------------------------------------

class AIMessage(models.Model):
    """Одна реплика в диалоге ученика с помощником по конкретному разделу."""
    ROLES = [("user", "Ученик"), ("assistant", "Помощник")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Ученик",
        related_name="ai_messages", on_delete=models.CASCADE,
    )
    section = models.ForeignKey(
        Section, verbose_name="Раздел", related_name="ai_messages",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    role = models.CharField("Кто", max_length=10, choices=ROLES)
    content = models.TextField("Текст")
    archived = models.BooleanField(
        "Диалог завершён", default=False,
        help_text="Ученик нажал «Новый диалог»: помощник эту переписку уже не учитывает, но куратор её видит.",
    )
    created_at = models.DateTimeField("Когда", auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "сообщение помощника"
        verbose_name_plural = "диалоги с помощником"

    def __str__(self):
        return f"{self.user} · {self.get_role_display()} · {self.content[:40]}"


class ENTSpecification(models.Model):
    year = models.PositiveSmallIntegerField("Год")
    subject = models.SlugField("Предмет", default="informatics")
    title = models.CharField("Название (RU)", max_length=200)
    title_kk = models.CharField("Название (KZ)", max_length=200, blank=True)
    source_url = models.URLField("Спецификация RU", blank=True)
    source_url_kk = models.URLField("Спецификация KZ", blank=True)
    question_count = models.PositiveSmallIntegerField(default=40)
    max_score = models.PositiveSmallIntegerField(default=50)

    class Meta:
        ordering = ["-year", "subject"]
        constraints = [models.UniqueConstraint(fields=["year", "subject"], name="ent_spec_year_subject_unique")]
        verbose_name = "спецификация ЕНТ"
        verbose_name_plural = "спецификации ЕНТ"

    def __str__(self):
        return f"{self.title} · {self.year}"


class ENTTopic(models.Model):
    specification = models.ForeignKey(ENTSpecification, on_delete=models.CASCADE, related_name="topics")
    code = models.CharField("Код темы", max_length=2)
    title = models.CharField("Название (RU)", max_length=300)
    title_kk = models.CharField("Название (KZ)", max_length=300, blank=True)
    sections = models.ManyToManyField(
        Section, related_name="ent_topics", blank=True,
        limit_choices_to={"parent__isnull": True}, verbose_name="Корневые темы BYTE",
        help_text="Начальное сопоставление может покрывать только часть официальной темы.",
    )
    mapping_notes = models.TextField("Примечания к покрытию", blank=True)

    class Meta:
        ordering = ["specification", "code"]
        constraints = [models.UniqueConstraint(fields=["specification", "code"], name="ent_topic_spec_code_unique")]
        verbose_name = "тема ЕНТ"
        verbose_name_plural = "темы ЕНТ"

    def __str__(self):
        return f"{self.code} · {self.title}"
