from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_learning_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="section",
            name="title_kk",
            field=models.CharField(blank=True, max_length=200, verbose_name="Название (қазақша)"),
        ),
        migrations.AddField(
            model_name="section",
            name="summary_kk",
            field=models.CharField(blank=True, max_length=255, verbose_name="Қысқаша сипаттама (қазақша)"),
        ),
        migrations.AddField(
            model_name="section",
            name="content_kk",
            field=models.TextField(
                blank=True,
                help_text="Қазақ тіліндегі материал. Егер бос болса, орысша нұсқа көрсетіледі.",
                verbose_name="Содержимое (қазақша, HTML)",
            ),
        ),
        migrations.AddField(
            model_name="section",
            name="video_url_kk",
            field=models.URLField(
                blank=True,
                help_text="Қазақша видео сілтемесі. Егер бос болса, негізгі видео қолданылады.",
                verbose_name="Видео урока (қазақша)",
            ),
        ),
        migrations.AddField(
            model_name="quizquestion",
            name="text_kk",
            field=models.TextField(blank=True, verbose_name="Сұрақ (қазақша)"),
        ),
        migrations.AddField(
            model_name="quizchoice",
            name="text_kk",
            field=models.CharField(blank=True, max_length=500, verbose_name="Жауап нұсқасы (қазақша)"),
        ),
    ]
