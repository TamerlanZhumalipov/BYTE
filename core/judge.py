"""Programming judge: production execution is restricted to Docker containers.

Local execution is available only with DEBUG and explicit BYTE_JUDGE_BACKEND=local.
Do not use the local backend for untrusted students.
"""
import os
import subprocess
import sys
import tempfile
import time
import math
from django.conf import settings
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


def _sandboxed():
    if settings.JUDGE_BACKEND == "local" and not settings.DEBUG:
        raise RuntimeError("Local judge is forbidden in production.")
    if settings.JUDGE_BACKEND not in {"docker", "local"}:
        raise RuntimeError("Unknown judge backend.")
    return settings.JUDGE_BACKEND == "docker"


def _prepare(code, language, workdir):
    """Готовит программу к запуску. Возвращает (команда, текст_ошибки)."""
    if _sandboxed():
        return _prepare_container(code, language, workdir)
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
    if _sandboxed():
        from .container_runner import run
        try:
            result = run(cmd, workdir, stdin=stdin_text.encode(), timeout=timeout+LAUNCH_OVERHEAD_SEC)
        except subprocess.TimeoutExpired:
            return "T", "", ""
        return ("OK" if result.returncode == 0 else "E", result.stdout.decode("utf-8",errors="replace"), result.stderr.decode("utf-8",errors="replace"))
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
    if not math.isfinite(time_limit) or not 0 < time_limit <= 10:
        raise ValueError("Invalid time limit.")
    if not 1 <= len(tests) <= 50:
        raise ValueError("Expected 1 to 50 tests.")
    total = len(tests)
    blank = "-" * total

    if language not in LANGUAGES:
        return JudgeResult("CE", 0, total, blank, "Неизвестный язык программирования.")
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return JudgeResult("CE", 0, total, blank, "Решение слишком большое (максимум 64 КБ).")

    with tempfile.TemporaryDirectory(prefix="byte-judge-") as workdir:
        if _sandboxed():
            os.chmod(workdir, 0o777)  # Only this disposable source directory is mounted.
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
            status, output, errors = _run_one(cmd, workdir, stdin_text, min(time_limit, max(.01, deadline-time.monotonic())))
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


def _prepare_container(code, language, workdir):
    from .container_runner import run
    filename = "main.py" if language == "python" else "main.cpp"
    with open(os.path.join(workdir, filename), "w", encoding="utf-8") as source:
        source.write(code)
    command = (["python3", "-I", "-B", "-c", "from pathlib import Path; compile(Path('main.py').read_bytes(), 'main.py', 'exec')"] if language == "python"
               else ["g++", "-O2", "-std=c++17", "-o", "main", "main.cpp"])
    try:
        result = run(command, workdir, timeout=COMPILE_TIMEOUT_SEC, writable=(language == "cpp"))
    except subprocess.TimeoutExpired:
        return None, "Компиляция заняла слишком много времени."
    if result.returncode:
        return None, _clip(result.stderr.decode("utf-8", errors="replace"))
    return (["python3", "-I", "-B", "main.py"] if language == "python" else ["./main"]), ""
