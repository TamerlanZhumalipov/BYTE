"""Bounded subprocess interface for public SQL runs and hidden grading."""
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .judge import JudgeResult, MAX_CODE_BYTES
from .sql_engine import validate_fixture, schema_signature

WORKER = Path(__file__).with_name('sql_engine.py').resolve()
MAX_TESTS = 10
TOTAL_SECONDS = 20


def run_query(query, fixture, time_limit=2, *, reference=None, ordered=False):
    validate_fixture(fixture)
    if not math.isfinite(time_limit) or not 0 < time_limit <= 3:
        raise ValueError('SQL time limit must be between 0 and 3 seconds.')
    if not isinstance(query, str) or len(query.encode()) > MAX_CODE_BYTES:
        return {'status': 'RE', 'message': 'Запрос превышает 64 КБ.'}
    payload = {'fixture': fixture, 'query': query, 'seconds': time_limit, 'reference': reference, 'ordered': ordered}
    with tempfile.TemporaryDirectory(prefix='byte-sql-') as directory:
        try:
            process = subprocess.run(
                [sys.executable, '-I', str(WORKER)], input=json.dumps(payload).encode(),
                capture_output=True, cwd=directory, timeout=2 * time_limit + 1,
                env={'PATH': os.defpath, 'LANG': 'C.UTF-8'},
            )
        except subprocess.TimeoutExpired:
            return {'status': 'TLE', 'message': 'Превышено время выполнения запроса.'}
    if process.returncode:
        return {'status': 'RE', 'message': 'Запрос остановлен: превышен лимит ресурсов или ошибка SQLite.'}
    if len(process.stdout) > 1_000_000:
        return {'status': 'RE', 'message': 'Слишком большой результат.'}
    try:
        return json.loads(process.stdout)
    except (ValueError, UnicodeError):
        return {'status': 'RE', 'message': 'Ошибка SQL-проверки. Сообщите куратору.'}


def run_sql_submission(query, task, fixtures):
    if not 1 <= len(fixtures) <= MAX_TESTS or not task.sql_reference.strip():
        raise ValueError('Нужен эталон и от 1 до 10 скрытых наборов.')
    schema = schema_signature(task.sql_sample)
    for fixture in fixtures:
        if schema_signature(fixture) != schema:
            raise ValueError('Схема скрытого набора отличается от открытой.')
    deadline = time.monotonic() + TOTAL_SECONDS
    marks = []
    message = ''
    for fixture in fixtures:
        if time.monotonic() + 2 * task.time_limit + 1 > deadline:
            marks.append('T')
            continue
        result = run_query(query, fixture, task.time_limit, reference=task.sql_reference, ordered=task.sql_ordered)
        if result['status'] == 'CONFIG':
            raise ValueError('Ошибка эталона SQL.')
        marks.append({'OK': 'P', 'WA': 'F', 'TLE': 'T'}.get(result['status'], 'E'))
        # Never disclose hidden values, reference output or data-dependent errors.
        if result['status'] == 'RE':
            message = 'Запрос не выполнен на скрытом наборе. Проверьте синтаксис, типы и ограничения на открытых данных.'
    passed = marks.count('P')
    bad = next((m for m in marks if m != 'P'), None)
    verdict = {'F': 'WA', 'T': 'TLE', 'E': 'RE', None: 'OK'}[bad]
    return JudgeResult(verdict, passed, len(fixtures), ''.join(marks), message)
