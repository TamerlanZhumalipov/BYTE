# BYTE

Платформа подготовки к ЕНТ по информатике: материалы RU/KZ, тесты, аналитика и отдельные контесты Programming/SQL.

## Локальная разработка

Требуется Python 3.12. Не используйте прежнее окружение Python 3.9.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade 'pip>=26.2.2'
python -m pip install -r requirements.lock.txt
cp .env.example .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

Укажите параметры AI в локальном `.env`, если помощник нужен. Секреты, базу и бэкапы не коммитить.

Python/C++ по умолчанию выполняются только через Docker. Подготовка и проверка:

```bash
docker build --pull -t byte-judge:local -f deploy/judge.Dockerfile .
python manage.py verify_judge
```

`BYTE_JUDGE_BACKEND=local` разрешён исключительно при `DJANGO_DEBUG=1` для собственного доверенного кода. Публичный запуск с ним запрещён.

## Проверки и выпуск

```bash
python manage.py test core.tests
```

- [Инструкция выпуска](docs/release.md)
- [Проверка безопасности и производительности](docs/security-audit-2026-10-28.md)
- [SQL-контесты](docs/sql-contests.md)

GitHub workflow проверяет зависимости, миграции, серверные тесты и реальные Linux-контейнеры. До успешного выполнения и проверки целевого сервера публичный запуск не считается готовым.
