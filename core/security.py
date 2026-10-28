"""Small DB-backed abuse limits shared by all WSGI workers."""
import hashlib
import hmac
import math
import time
from datetime import datetime, timezone

from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin

from .models import RequestBucket


def consume(scope, identity, limit, seconds):
    now = time.time()
    window = int(now // seconds)
    digest = hmac.new(settings.SECRET_KEY.encode(), identity.encode(), hashlib.sha256).hexdigest()
    key = f'{scope}:{window}:{digest}'
    expiry = datetime.fromtimestamp((window+1)*seconds, tz=timezone.utc)
    RequestBucket.objects.get_or_create(key=key, defaults={'expires_at': expiry})
    allowed = RequestBucket.objects.filter(pk=key, hits__lt=limit).update(hits=F('hits')+1)
    return bool(allowed), max(1, math.ceil(expiry.timestamp()-now))


class RequestProtectionMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != 'POST':
            return None
        name = request.resolver_match.url_name
        # Only a loopback reverse proxy may supply an overwritten X-Real-IP.
        ip = request.META.get('REMOTE_ADDR', '')
        if settings.TRUST_PROXY and ip in {'127.0.0.1', '::1'}:
            ip = request.META.get('HTTP_X_REAL_IP', ip)
        rules = []
        if name in {'login', 'contest_login'}:
            rules = [('login-ip', ip, 40, 600)]
            login = request.POST.get('username', request.POST.get('login', '')).strip().casefold()[:150]
            rules.append(('login-pair', ip+'|'+login, 12, 600))
        elif name == 'lead_create':
            rules = [('lead', ip, 10, 3600)]
        elif name in {'ai_ask', 'ai_ask_home'} and request.user.is_authenticated:
            # Atomic reservation is independent of AI history/archiving and of
            # whether upstream succeeds. Concurrent requests cannot bypass it.
            rules = [('ai-cooldown', str(request.user.pk), 1, 4),
                     ('ai-day', str(request.user.pk), settings.AI_DAILY_LIMIT, 86400)]
        for scope, identity, limit, seconds in rules:
            allowed, wait = consume(scope, identity, limit, seconds)
            if not allowed:
                response = JsonResponse({'error': 'Слишком часто. Попробуйте позже.', 'ok': False}, status=429)
                response['Retry-After'] = str(wait)
                return response
        return None

    def process_response(self, request, response):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            add_never_cache_headers(response)
        if not request.path.startswith('/admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; "
                "frame-src https://www.youtube.com https://www.youtube-nocookie.com https://player.vimeo.com; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
            )
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response
