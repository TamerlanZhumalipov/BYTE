#!/usr/bin/env bash
# Первичная установка проекта BYTE (macOS / Linux). Запускать из папки проекта:  bash setup.sh
set -e

if [ ! -f manage.py ]; then
  echo "Запустите скрипт из папки проекта (где лежит manage.py)."; exit 1
fi

echo "==> 1/4 Создаю виртуальное окружение (venv)"
python3 -m venv venv
source venv/bin/activate

echo "==> 2/4 Устанавливаю Django"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 3/4 Создаю таблицы в базе данных"
python manage.py makemigrations core
python manage.py migrate

echo "==> 4/4 Загружаю 16 тем материалов"
python manage.py seed_materials

cat << 'MSG'

Готово! Дальше:

  source venv/bin/activate              # включить окружение (в каждом новом окне терминала)
  python manage.py createsuperuser      # создать администратора для /admin/
  python manage.py seed_demo_contest    # демо-контест (напечатает логин и пароль участника)
  python manage.py runserver            # запустить сайт: http://127.0.0.1:8000/

MSG
