import random
import string
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Contest, ContestAccount, ContestTask, TaskTest

TESTS_PER_TASK = 100


def sieve_count(n):
    """Сколько простых чисел не больше n."""
    if n < 2:
        return 0
    flags = bytearray([1]) * (n + 1)
    flags[0] = flags[1] = 0
    for i in range(2, int(n ** 0.5) + 1):
        if flags[i]:
            flags[i * i::i] = bytearray(len(range(i * i, n + 1, i)))
    return sum(flags)


def tests_sum(rng):
    cases = [(0, 0), (1, 2), (-5, 5), (10 ** 9, 10 ** 9), (-10 ** 9, -10 ** 9), (-7, -8), (123456789, -987654321)]
    while len(cases) < TESTS_PER_TASK:
        limit = rng.choice([10, 1000, 10 ** 6, 10 ** 9])
        cases.append((rng.randint(-limit, limit), rng.randint(-limit, limit)))
    return [(f"{a} {b}\n", f"{a + b}\n") for a, b in cases]


def tests_max(rng):
    arrays = [[5], [-3, -1, -7], [4, 4, 4, 4], [9, 1, 2, 3], [1, 2, 3, 9]]
    while len(arrays) < TESTS_PER_TASK:
        n = rng.choice([2, 3, 5, 10, 50, 200, 1000])
        arrays.append([rng.randint(-10 ** 6, 10 ** 6) for _ in range(n)])
    return [(f"{len(a)}\n{' '.join(map(str, a))}\n", f"{max(a)}\n") for a in arrays]


def tests_primes(rng):
    values = [1, 2, 3, 4, 10, 100, 1000, 100000, 199999, 200000]
    while len(values) < TESTS_PER_TASK:
        values.append(rng.choice([rng.randint(1, 1000), rng.randint(100000, 200000)]))
    return [(f"{n}\n", f"{sieve_count(n)}\n") for n in values]


STATEMENTS = {
    "sum": """
<p>Даны два целых числа <code>a</code> и <code>b</code>. Выведите их сумму.</p>
<h3>Формат ввода</h3>
<p>В единственной строке через пробел записаны два целых числа, каждое по модулю не больше 10<sup>9</sup>.</p>
<h3>Формат вывода</h3>
<p>Одно целое число — значение <code>a + b</code>. В C++ используйте тип <code>long long</code>.</p>
<h3>Пример</h3>
<div class="ex"><div><strong>Ввод</strong><pre>3 4</pre></div><div><strong>Вывод</strong><pre>7</pre></div></div>
""",
    "max": """
<p>Дан массив целых чисел. Найдите в нём наибольшее число.</p>
<h3>Формат ввода</h3>
<p>В первой строке записано число <code>n</code> (1 ≤ n ≤ 1000). Во второй строке через пробел записаны <code>n</code> целых чисел, каждое по модулю не больше 10<sup>6</sup>.</p>
<h3>Формат вывода</h3>
<p>Одно число — максимальный элемент массива.</p>
<h3>Пример</h3>
<div class="ex"><div><strong>Ввод</strong><pre>5
3 -1 9 4 9</pre></div><div><strong>Вывод</strong><pre>9</pre></div></div>
""",
    "primes": """
<p>Посчитайте, сколько существует простых чисел, не превосходящих <code>n</code>.</p>
<h3>Формат ввода</h3>
<p>В единственной строке записано целое число <code>n</code> (1 ≤ n ≤ 200 000).</p>
<h3>Формат вывода</h3>
<p>Одно число — количество простых чисел от 1 до <code>n</code> включительно.</p>
<div class="note">Проверять каждое число делением «в лоб» может оказаться слишком медленно. Подумайте о решете Эратосфена.</div>
<h3>Пример</h3>
<div class="ex"><div><strong>Ввод</strong><pre>10</pre></div><div><strong>Вывод</strong><pre>4</pre></div></div>
<p>Простые числа до 10: 2, 3, 5, 7.</p>
""",
}


class Command(BaseCommand):
    help = "Создаёт демо-контест: 3 задачи по 100 тестов и одного демо-участника."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=90, help="Длительность контеста (по умолчанию 90)")
        parser.add_argument("--starts-in", type=int, default=0, help="Через сколько минут начало (по умолчанию — сразу)")

    def handle(self, *args, **options):
        rng = random.Random(2026)
        contest = Contest.objects.create(
            title="Демо-контест BYTE",
            starts_at=timezone.now() + timedelta(minutes=options["starts_in"]),
            duration_minutes=options["minutes"],
        )

        specs = [
            (1, "Сумма двух чисел", "sum", 2.0, tests_sum),
            (2, "Максимум в массиве", "max", 2.0, tests_max),
            (3, "Простые числа", "primes", 2.0, tests_primes),
        ]
        for order, title, key, time_limit, generator in specs:
            task = ContestTask.objects.create(
                contest=contest, order=order, title=title,
                statement=STATEMENTS[key], time_limit=time_limit,
            )
            TaskTest.objects.bulk_create([
                TaskTest(task=task, order=i, input_data=inp, expected_output=out)
                for i, (inp, out) in enumerate(generator(rng), start=1)
            ])

        login = f"demo{contest.id}"
        password = "".join(rng.choices(string.ascii_lowercase + string.digits, k=8))
        account = ContestAccount(contest=contest, login=login, full_name="Демо-участник")
        account.set_password(password)
        account.save()

        self.stdout.write(self.style.SUCCESS(f"Контест «{contest.title}» создан (id={contest.id})."))
        self.stdout.write(f"  начало:   {timezone.localtime(contest.starts_at):%d.%m.%Y %H:%M}")
        self.stdout.write(f"  идёт:     {contest.duration_minutes} мин, 3 задачи × {TESTS_PER_TASK} тестов")
        self.stdout.write("Вход в контест:")
        self.stdout.write(f"  логин:  {login}")
        self.stdout.write(f"  пароль: {password}")
