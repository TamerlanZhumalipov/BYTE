from django.conf import settings
from django.shortcuts import render
from django.template.loader import render_to_string

LEGAL_VERSION = "2026-10-26.1"
LEAD_RETENTION_DAYS = 90


def legal_context(request):
    details = settings.BYTE_LEGAL
    return {
        "legal": details,
        "legal_version": LEGAL_VERSION,
        "lead_retention_days": LEAD_RETENTION_DAYS,
    }


def consent_snapshot(request):
    from .localization import get_request_language
    context = legal_context(request)
    context["site_lang"] = get_request_language(request)
    return render_to_string("legal/lead_consent.html", context).strip()


def privacy(request):
    return render(request, "legal/privacy.html")


def terms(request):
    return render(request, "legal/terms.html")


def cookies(request):
    return render(request, "legal/cookies.html", {
        "session_cookie_name": settings.SESSION_COOKIE_NAME,
        "session_cookie_days": settings.SESSION_COOKIE_AGE // 86400,
        "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
        "csrf_cookie_days": settings.CSRF_COOKIE_AGE // 86400,
    })
