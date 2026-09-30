from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import ContestTask, TaskTest


class Command(BaseCommand):
    help = (
        "Загружает тесты к задаче из папки с парами файлов 01.in / 01.out, 02.in / 02.out ... "
        "Пример: python3 manage.py import_tests 3 ./tests/task3 --replace"
    )

    def add_arguments(self, parser):
        parser.add_argument("task_id", type=int, help="ID задачи (ContestTask)")
        parser.add_argument("folder", help="Папка с файлами .in и .out")
        parser.add_argument("--replace", action="store_true", help="Сначала удалить существующие тесты задачи")

    def handle(self, *args, **options):
        task = ContestTask.objects.filter(pk=options["task_id"]).first()
        if task is None:
            raise CommandError(f"Задача с id={options['task_id']} не найдена.")

        folder = Path(options["folder"])
        if not folder.is_dir():
            raise CommandError(f"Папка не найдена: {folder}")

        inputs = sorted(folder.glob("*.in"))
        if not inputs:
            raise CommandError("В папке нет файлов *.in")

        tests = []
        for order, in_file in enumerate(inputs, start=1):
            out_file = in_file.with_suffix(".out")
            if not out_file.exists():
                raise CommandError(f"Нет файла с ответом для {in_file.name}: ожидается {out_file.name}")
            tests.append(TaskTest(
                task=task, order=order,
                input_data=in_file.read_text(encoding="utf-8"),
                expected_output=out_file.read_text(encoding="utf-8"),
            ))

        if options["replace"]:
            task.tests.all().delete()
        TaskTest.objects.bulk_create(tests)
        self.stdout.write(self.style.SUCCESS(f"Загружено тестов: {len(tests)} → «{task.title}»"))
