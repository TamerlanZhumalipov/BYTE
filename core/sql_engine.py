"""Standalone SQLite worker: no Django imports, credentials or application DB.

Only this program is executed in the subprocess, never student Python/code.
Keep SQLite patched; this is a constrained SQL worker, not an OS sandbox.
"""
import json
import math
import re
import sqlite3
import sys
import time

MAX_FIXTURE_BYTES = 512_000
MAX_ROWS = 2000
MAX_RESULT_BYTES = 512_000
MAX_QUERY_BYTES = 65536
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
TYPES = {"INTEGER", "REAL", "TEXT", "NUMERIC"}
FUNCTIONS = set("abs avg char coalesce count dense_rank first_value glob group_concat ifnull instr lag last_value lead length like lower ltrim max min nth_value ntile nullif rank replace round row_number rtrim substr substring sum total trim typeof unicode upper percent_rank cume_dist".split())


def validate_fixture(fixture):
    if not isinstance(fixture, dict) or set(fixture) != {"tables"}:
        raise ValueError('Набор должен содержать только ключ tables.')
    if len(json.dumps(fixture, allow_nan=False).encode()) > MAX_FIXTURE_BYTES:
        raise ValueError('Учебный набор превышает 512 КБ.')
    tables = fixture['tables']
    if not isinstance(tables, list) or not 1 <= len(tables) <= 8:
        raise ValueError('Нужно от 1 до 8 таблиц.')
    names = set()
    for table in tables:
        if not isinstance(table, dict) or set(table) != {'name', 'columns', 'rows'}:
            raise ValueError('У таблицы нужны name, columns, rows.')
        name = table['name']
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or name.lower().startswith(('sqlite_', 'pragma_')) or name.lower() in names:
            raise ValueError('Неверное или повторяющееся имя таблицы.')
        names.add(name.lower())
        columns = table['columns']
        if not isinstance(columns, list) or not 1 <= len(columns) <= 32:
            raise ValueError('Нужно от 1 до 32 столбцов.')
        column_names = set()
        for column in columns:
            if not isinstance(column, list) or len(column) != 2:
                raise ValueError('Столбец задаётся парой [имя, тип].')
            col, kind = column
            if not isinstance(col, str) or not IDENTIFIER.fullmatch(col) or col.lower() in column_names or kind not in TYPES:
                raise ValueError('Неверное имя или тип столбца.')
            column_names.add(col.lower())
        rows = table['rows']
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError('Не больше 1000 строк в таблице.')
        for row in rows:
            if not isinstance(row, list) or len(row) != len(columns):
                raise ValueError('Число значений должно совпадать с числом столбцов.')
            for value in row:
                if value is None:
                    continue
                if type(value) not in (str, int, float):
                    raise ValueError('Допустимы строка, число или null.')
                if isinstance(value, str) and len(value) > 4000:
                    raise ValueError('Слишком длинная строка.')
                if type(value) is int and not -(2**63) <= value < 2**63:
                    raise ValueError('Целое число вне диапазона SQLite.')
                if type(value) is float and not math.isfinite(value):
                    raise ValueError('Число должно быть конечным.')
    return fixture


def schema_signature(fixture):
    validate_fixture(fixture)
    return sorted((t['name'].lower(), tuple((c.lower(), k) for c, k in t['columns'])) for t in fixture['tables'])


def execute_query(fixture, query, seconds):
    validate_fixture(fixture)
    if not isinstance(query, str) or not query.strip() or len(query.encode()) > MAX_QUERY_BYTES:
        raise ValueError('Нужен один SQL-запрос размером до 64 КБ.')
    connection = sqlite3.connect(':memory:')
    deadline = time.monotonic() + seconds
    try:
        connection.execute('PRAGMA temp_store=MEMORY')
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.execute('PRAGMA hard_heap_limit=67108864')
        connection.execute('PRAGMA max_page_count=4096')
        if hasattr(connection, 'enable_load_extension'):
            connection.enable_load_extension(False)
        if hasattr(connection, 'setlimit'):
            limits = {'SQLITE_LIMIT_LENGTH': 1_000_000, 'SQLITE_LIMIT_SQL_LENGTH': MAX_QUERY_BYTES,
                      'SQLITE_LIMIT_COLUMN': 64, 'SQLITE_LIMIT_EXPR_DEPTH': 50,
                      'SQLITE_LIMIT_COMPOUND_SELECT': 10, 'SQLITE_LIMIT_ATTACHED': 0,
                      'SQLITE_LIMIT_LIKE_PATTERN_LENGTH': 500, 'SQLITE_LIMIT_VDBE_OP': 100000}
            for name, limit in limits.items():
                connection.setlimit(getattr(sqlite3, name), limit)
        for table in fixture['tables']:
            columns = ', '.join(f'"{name}" {kind}' for name, kind in table['columns'])
            connection.execute(f'CREATE TABLE "{table["name"]}" ({columns})')
            placeholders = ','.join('?' for _ in table['columns'])
            connection.executemany(f'INSERT INTO "{table["name"]}" VALUES ({placeholders})', table['rows'])
        connection.commit()
        connection.execute('PRAGMA query_only=ON')
        names = {t['name'].lower() for t in fixture['tables']}

        def authorize(action, first, second, database, source):
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and database in ('main', None) and (first or '').lower() in names:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and (second or '').lower() in FUNCTIONS:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        cursor = connection.execute(query)  # execute, never executescript: one statement only
        if cursor.description is None or len(cursor.description) > 64:
            raise ValueError('Запрос должен вернуть таблицу не больше 64 столбцов.')
        rows = []
        size = 0
        for row in cursor:
            if len(rows) >= MAX_ROWS:
                raise ValueError('Результат превышает 2000 строк.')
            if any(isinstance(value, bytes) for value in row):
                raise ValueError('Двоичные значения BLOB не поддерживаются.')
            size += len(json.dumps(row, ensure_ascii=False, allow_nan=False).encode('utf-8'))
            if size > MAX_RESULT_BYTES:
                raise ValueError('Результат превышает 512 КБ.')
            rows.append(row)
        return {'columns': [column[0][:120] for column in cursor.description], 'rows': rows}
    finally:
        connection.close()


def same_result(actual, expected, ordered):
    from collections import Counter
    if len(actual['columns']) != len(expected['columns']):
        return False
    a = [tuple(row) for row in actual['rows']]
    b = [tuple(row) for row in expected['rows']]
    return a == b if ordered else Counter(a) == Counter(b)


def main():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        if sys.platform != 'darwin':
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
    except (ImportError, ValueError, OSError):
        pass
    try:
        data = json.loads(sys.stdin.buffer.read(MAX_FIXTURE_BYTES + 2 * MAX_QUERY_BYTES + 4096))
        seconds = min(3.0, max(0.05, float(data.get('seconds', 2))))
        expected = None
        if data.get('reference') is not None:
            try:
                expected = execute_query(data['fixture'], data['reference'], seconds)
            except Exception:
                print(json.dumps({'status': 'CONFIG', 'message': 'Ошибка настройки эталона или набора. Сообщите куратору.'}))
                return
        actual = execute_query(data['fixture'], data['query'], seconds)
        if expected is None:
            result = {'status': 'OK', **actual}
        else:
            result = {'status': 'OK' if same_result(actual, expected, data.get('ordered', False)) else 'WA'}
    except sqlite3.OperationalError as exc:
        result = {'status': 'TLE' if 'interrupted' in str(exc) else 'RE', 'message': str(exc)[:300]}
    except (ValueError, sqlite3.Error, MemoryError, OverflowError) as exc:
        result = {'status': 'RE', 'message': str(exc)[:300] or 'Превышен лимит памяти.'}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
