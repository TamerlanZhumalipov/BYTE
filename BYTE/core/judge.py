"""Проверка решений: запускает код ученика на тестах и сравнивает вывод.

ВАЖНО. Этот модуль исполняет ЧУЖИЕ программы на той же машине, где работает сайт.
Здесь есть лимиты по времени, памяти и размеру вывода, но это НЕ полноценная
песочница: программа ученика всё ещё может читать файлы сервера. Для учебного
курса с известными учениками этого достаточно на старте, а перед реальным
запуском лучше вынести проверку в изолированную среду (Docker / Judge0) —
достаточно заменить одну функцию: run_submission().
"""
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

LANGUAGES = ("python", "cpp")

MAX_CODE_BYTES = 64 * 1024          # максимальный размер исходника
MAX_OUTPUT_BYTES = 1_000_000        # сколько вывода читаем у программы
TOTAL_BUDGET_SEC = 25.0             # общий бюджет времени на одну отправку (тесты сверх бюджета не запускаются)
COMPILE_TIMEOUT_SEC = 30
LAUNCH_OVERHEAD_SEC = 0.5           # запас на запуск интерпретатора
MEMORY_LIMIT_MB = 512
FILE_LIMIT_MB = 16
MESSAGE_LIMIT = 1500

# Минимальное окружение: наши секреты из переменных окружения программе не попадают.
_ENV = {
    "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    "LANG": "C.UTF-8",
}

# Маленький «запускатель»: ставит лимиты памяти и размера файлов и подменяет себя
# программой ученика. Так лимиты не зависят от потоков веб-сервера.
_LAUNCHER = r'''
import os, sys
try:
    import resource
    mem = int(sys.argv[1]) * 1024 * 1024
    fsz = int(sys.argv[2]) * 1024 * 1024
    limits = [(resource.RLIMIT_FSIZE, fsz)]
    if sys.platform != "darwin":
        limits.append((resource.RLIMIT_AS, mem))
    for res, val in limits:
        try:
            resource.setrlimit(res, (val, val))
        except (ValueError, OSError):
            pass
except ImportError:
    pass
os.execvp(sys.argv[3], sys.argv[3:])
'''


@dataclass
class JudgeResult:
    verdict: str        # OK / WA / TLE / RE / CE
    passed: int
    total: int
    marks: str          # по символу на тест: P — верно, F — неверно, T — время, E — ошибка, - — не запускался
    message: str = ""   # текст ошибки компиляции / выполнения (обрезан)


def _clip(text, tail=False):
    text = (text or "").strip()
    if len(text) <= MESSAGE_LIMIT:
        return text
    return ("…" + text[-MESSAGE_LIMIT:]) if tail else (text[:MESSAGE_LIMIT] + "…")


def _normalize(text):
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _wrap(cmd):
    return [sys.executable, "-I", "-c", _LAUNCHER, str(MEMORY_LIMIT_MB), str(FILE_LIMIT_MB), *cmd]


def _read_head(path, limit):
    try:
        with open(path, "rb") as f:
            return f.read(limit).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _prepare(code, language, workdir):
    """Готовит программу к запуску. Возвращает (команда, текст_ошибки)."""
    if language == "python":
        with open(os.path.join(workdir, "main.py"), "w", encoding="utf-8") as f:
            f.write(code)
        check = subprocess.run(
            [sys.executable, "-I", "-m", "py_compile", "main.py"],
            cwd=workdir, capture_output=True, timeout=COMPILE_TIMEOUT_SEC, env=_ENV,
        )
        if check.returncode != 0:
            return None, _clip(check.stderr.decode("utf-8", errors="replace").replace(workdir, "."))
        return [sys.executable, "-I", "-X", "utf8", "main.py"], ""

    with open(os.path.join(workdir, "main.cpp"), "w", encoding="utf-8") as f:
        f.write(code)
    try:
        build = subprocess.run(
            ["g++", "-O2", "-std=c++17", "-o", "main", "main.cpp"],
            cwd=workdir, capture_output=True, timeout=COMPILE_TIMEOUT_SEC, env=_ENV,
        )
    except FileNotFoundError:
        return None, "На сервере не найден компилятор g++."
    except subprocess.TimeoutExpired:
        return None, "Компиляция заняла слишком много времени."
    if build.returncode != 0:
        return None, _clip(build.stderr.decode("utf-8", errors="replace").replace(workdir, "."))
    return ["./main"], ""


def _run_one(cmd, workdir, stdin_text, timeout):
    """Один запуск. Возвращает (статус, вывод, stderr): статус OK / T / E."""
    out_path = os.path.join(workdir, "_out.txt")
    err_path = os.path.join(workdir, "_err.txt")
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            proc = subprocess.run(
                _wrap(cmd), cwd=workdir, input=stdin_text.encode("utf-8"),
                stdout=out, stderr=err, timeout=timeout + LAUNCH_OVERHEAD_SEC, env=_ENV,
            )
    except subprocess.TimeoutExpired:
        return "T", "", ""
    output = _read_head(out_path, MAX_OUTPUT_BYTES)
    errors = _read_head(err_path, 4000).replace(workdir, ".")
    if proc.returncode != 0:
        return "E", output, errors
    return "OK", output, errors


def run_submission(code, language, tests, time_limit=2.0):
    """Проверяет решение. tests — список пар (входные_данные, ожидаемый_вывод)."""
    total = len(tests)
    blank = "-" * total

    if language not in LANGUAGES:
        return JudgeResult("CE", 0, total, blank, "Неизвестный язык программирования.")
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return JudgeResult("CE", 0, total, blank, "Решение слишком большое (максимум 64 КБ).")

    with tempfile.TemporaryDirectory(prefix="byte-judge-") as workdir:
        cmd, error = _prepare(code, language, workdir)
        if cmd is None:
            return JudgeResult("CE", 0, total, blank, error)

        marks = []
        message = ""
        deadline = time.monotonic() + TOTAL_BUDGET_SEC
        for stdin_text, expected in tests:
            if time.monotonic() > deadline:
                marks.append("-")
                continue
            status, output, errors = _run_one(cmd, workdir, stdin_text, time_limit)
            if status == "T":
                marks.append("T")
            elif status == "E":
                marks.append("E")
                if not message:
                    message = _clip(errors, tail=True)
            elif _normalize(output) == _normalize(expected):
                marks.append("P")
            else:
                marks.append("F")

    passed = marks.count("P")
    if total and passed == total:
        verdict = "OK"
    else:
        first_bad = next((m for m in marks if m != "P"), "F")
        verdict = {"F": "WA", "T": "TLE", "E": "RE", "-": "TLE"}[first_bad]
    return JudgeResult(verdict, passed, total, "".join(marks), message)
