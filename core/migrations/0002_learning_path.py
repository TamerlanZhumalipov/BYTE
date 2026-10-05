# Generated for BYTE learning path architecture

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="video_url",
            field=models.URLField(
                blank=True,
                help_text="Ссылка на YouTube/Vimeo или другой источник видео. Для YouTube ссылка автоматически превращается во встраиваемую.",
                verbose_name="Видео урока",
            ),
        ),
        migrations.CreateModel(
            name="TopicQuiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "pass_percent",
                    models.PositiveSmallIntegerField(
                        default=70,
                        help_text="Минимальный процент правильных ответов, чтобы открыть следующую тему.",
                        verbose_name="Проходной процент",
                    ),
                ),
                (
                    "topic",
                    models.OneToOneField(
                        limit_choices_to={"parent__isnull": True},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_quiz",
                        to="core.section",
                        verbose_name="Основная тема",
                    ),
                ),
            ],
            options={
                "verbose_name": "тест по теме",
                "verbose_name_plural": "тесты по темам",
            },
        ),
        migrations.CreateModel(
            name="QuizQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveSmallIntegerField(default=1, verbose_name="Порядок")),
                ("text", models.TextField(verbose_name="Вопрос")),
                (
                    "quiz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="core.topicquiz",
                        verbose_name="Тест",
                    ),
                ),
            ],
            options={
                "verbose_name": "вопрос теста",
                "verbose_name_plural": "вопросы теста",
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="QuizChoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=500, verbose_name="Вариант ответа")),
                ("is_correct", models.BooleanField(default=False, verbose_name="Правильный ответ")),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="core.quizquestion",
                        verbose_name="Вопрос",
                    ),
                ),
            ],
            options={
                "verbose_name": "вариант ответа",
                "verbose_name_plural": "варианты ответа",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score_percent", models.PositiveSmallIntegerField(verbose_name="Результат, %")),
                ("correct_count", models.PositiveSmallIntegerField(verbose_name="Правильных ответов")),
                ("total_questions", models.PositiveSmallIntegerField(verbose_name="Всего вопросов")),
                ("passed", models.BooleanField(default=False, verbose_name="Тест пройден")),
                ("answers", models.JSONField(blank=True, default=dict, verbose_name="Ответы")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Попытка")),
                (
                    "quiz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="core.topicquiz",
                        verbose_name="Тест",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="topic_quiz_attempts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Ученик",
                    ),
                ),
            ],
            options={
                "verbose_name": "попытка теста",
                "verbose_name_plural": "результаты тестов",
                "ordering": ["-created_at"],
            },
        ),
    ]
