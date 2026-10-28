"""Настройки проекта BYTE (совместимы с Django 4.2 – 5.x)."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

def _load_dotenv():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


# ВАЖНО для продакшена: задайте свои значения через переменные окружения.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-key-change-me-before-deploy")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.security.RequestProtectionMiddleware",
]

ROOT_URLCONF = "byte_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_language",
                "core.legal.legal_context",
            ],
        },
    },
]

WSGI_APPLICATION = "byte_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"   # сюда собирается статика командой collectstatic (для сервера)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "index"

# YouTube embeds require an HTTP Referer. Keep the origin on cross-site iframe requests.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------------------------------------------------------------------------
# ИИ-помощник по материалам (core/ai.py)
# ---------------------------------------------------------------------------

# Значения читаются из файла .env в корне проекта (создайте его из .env.example).
# Ключ GEMINI_API_KEY никогда не должен попадать в Git — .env уже в .gitignore.

AI_ENABLED = os.environ.get("AI_ENABLED", "1") == "1"
AI_MODEL = os.environ.get("AI_MODEL", "gemini-3.8-flash")
AI_FALLBACK_MODELS = [m.strip() for m in os.environ.get("AI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-3.5-flash,gemini-3.1-flash-lite").split(",") if m.strip()]
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "700"))
AI_HISTORY_MESSAGES = 8    # сколько последних реплик диалога передаём модели как контекст
AI_COOLDOWN_SECONDS = 4    # минимальный промежуток между вопросами одного ученика
AI_DAILY_LIMIT = 200       # вопросов в сутки на одного ученика (защита от случайных расходов)

# Operator identifier is configured on the server, never committed to Git.
BYTE_LEGAL = {
    "operator": os.environ.get("BYTE_LEGAL_OPERATOR", "Жумалипов Тамерлан Айдарович").strip(),
    "identifier": os.environ.get("BYTE_LEGAL_IDENTIFIER", "").strip(),
    "contact": os.environ.get("BYTE_LEGAL_CONTACT", "tamush30@gmail.com").strip(),
    "location": os.environ.get("BYTE_LEGAL_LOCATION", "Казахстан").strip(),
}

# Release defaults: .env is loaded before any setting is evaluated.
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]
if not DEBUG:
    if len(SECRET_KEY) < 50 or SECRET_KEY == "dev-only-secret-key-change-me-before-deploy" or SECRET_KEY.startswith("REPLACE_"):
        raise ImproperlyConfigured("Set a random DJANGO_SECRET_KEY of at least 50 characters, or DJANGO_DEBUG=1 for local development.")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Configure explicit DJANGO_ALLOWED_HOSTS; wildcards are not allowed in production.")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 3600 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]
# Enable only behind a proxy that overwrites this header; never expose Gunicorn directly.
TRUST_PROXY = os.environ.get("DJANGO_TRUST_PROXY", "0") == "1"
if TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 300
AI_HTTP_TIMEOUT_MS = 15000
JUDGE_BACKEND = os.environ.get("BYTE_JUDGE_BACKEND", "docker")
JUDGE_DOCKER_IMAGE = os.environ.get("BYTE_JUDGE_IMAGE", "byte-judge:local")
if JUDGE_BACKEND not in {"docker", "local"} or (not DEBUG and JUDGE_BACKEND != "docker"):
    raise ImproperlyConfigured("Production requires BYTE_JUDGE_BACKEND=docker.")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
