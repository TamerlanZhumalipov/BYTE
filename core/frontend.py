"""Explicit, read-only page props for React. Never serialize model.__dict__."""
import json
from pathlib import Path

from django.conf import settings
from django.contrib.messages import get_messages
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.html import json_script

from .localization import TRANSLATIONS, get_request_language


class UnicodeJSONEncoder(DjangoJSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['ensure_ascii'] = False
        super().__init__(*args, **kwargs)


def section(obj, *, children=False, content=False):
    if obj is None:
        return None
    data = {
        'id': obj.pk, 'slug': obj.slug, 'parent_id': obj.parent_id,
        'title': getattr(obj, 'display_title', obj.title),
        'summary': getattr(obj, 'display_summary', obj.summary),
        'url': obj.get_absolute_url(), 'locked': getattr(obj, 'is_locked', False),
        'completed': getattr(obj, 'is_completed', False),
        'best_score': getattr(obj, 'best_score', None),
    }
    if children:
        data['children'] = [section(child, children=True) for child in getattr(obj, 'kids', [])]
    if content and not data['locked']:
        data.update(content=obj.display_content, video_url=obj.display_video_url,
                    video_embed_url=obj.display_video_embed_url)
    return data


def contest_info(obj):
    if obj is None:
        return None
    return {'id': obj.pk, 'title': obj.title, 'starts_at': obj.starts_at,
            'ends_at': obj.ends_at, 'duration_minutes': obj.duration_minutes}


def attempt(obj):
    return {'id': obj.pk, 'score': obj.score_percent, 'passed': obj.passed,
            'created_at': obj.created_at, 'topic': section(obj.quiz.topic)} if obj else None


def page_props(page, context):
    c = context
    if page == 'dashboard':
        current = c['current']
        return {
            'roots': [section(s, children=True) for s in c['roots']],
            'current': section(current, children=True, content=True),
            'breadcrumbs': [section(s) for s in c['breadcrumbs']],
            'previous': section(c['prev_section']), 'next': section(c['next_section']),
            'open_ids': list(c['open_ids']), 'next_contest': contest_info(c['next_contest']),
            'current_root': section(c['current_root']),
            'quiz': {'pass_percent': c['current_quiz'].pass_percent,
                     'url': reverse('topic_quiz', args=[c['current_root'].slug])} if c['current_quiz'] else None,
            'best_score': c['current_best_score'], 'completed': c['current_topic_completed'],
            'next_is_quiz': c['next_is_quiz'],
            'ai': {'enabled': c['ai_enabled'],
                   'ask_url': reverse('ai_ask', args=[current.slug]) if current else reverse('ai_ask_home'),
                   'reset_url': reverse('ai_reset', args=[current.slug]) if current else reverse('ai_reset_home')},
        }
    if page == 'topic_quiz':
        result = c['result']
        return {
            'topic': section(c['topic']), 'pass_percent': c['quiz'].pass_percent,
            'best_score': c['best_score'],
            # No correct flags or answers in the question payload, including GET.
            'questions': [{'id': q.pk, 'text': q.display_text,
                           'choices': [{'id': a.pk, 'text': a.display_text} for a in q.choices.all()]}
                          for q in c['questions']],
            'result': {'score': result['score'], 'passed': result['passed'],
                       'correct_count': result['correct_count'], 'total': result['total'],
                       'next': section(result['unlocked_next']),
                       'review': [{'question': r['question'].display_text,
                                   'selected': r['selected'].display_text if r['selected'] else None,
                                   'correct': r['correct_choice'].display_text if r['correct_choice'] else None,
                                   'is_correct': r['is_correct']} for r in result['review']]} if result else None,
        }
    if page == 'analytics':
        return {**{key: c[key] for key in ('total_topics', 'completed_topics', 'progress_percent', 'average_score', 'forecast')},
                'rows': [{'topic': section(r['topic']), 'locked': r['locked'], 'completed': r['completed'],
                          'best_score': r['best_score'], 'attempts_count': r['attempts_count'],
                          'latest': attempt(r['latest'])} for r in c['rows']],
                'recent_attempts': [attempt(a) for a in c['recent_attempts']]}
    if page == 'contest_login':
        return {'error': c['error'], 'next_contest': contest_info(c['next_contest'])}
    if page == 'contest':
        data = c.get('contest_data', {})
        histories = {t['id']: t for t in data.get('tasks', [])}
        return {'contest': contest_info(c['contest']), 'state': c['state'],
                'account': {'id': c['account'].pk, 'login': c['account'].login, 'name': c['account'].full_name},
                'remaining': c.get('seconds_to_start', data.get('remaining', 0)),
                'tasks': [{'id': row['task'].pk, 'title': row['task'].title,
                           'statement': row['task'].statement, 'time_limit': row['task'].time_limit,
                           'total': row['total'], 'best': row['best'],
                           'history': histories[row['task'].pk]['history']} for row in c.get('items', [])]}
    if page == 'login':
        return {'error': bool(c['form'].errors), 'next': c.get('next', ''),
                'username': c['form']['username'].value() or ''}
    return {}


def render_page(request, template, context=None, **kwargs):
    context = context or {}
    if not settings.REACT_FRONTEND_ENABLED:
        return render(request, template, context, **kwargs)
    page = Path(template).stem
    routes = {name: reverse(name) for name in (
        'index', 'login', 'logout', 'set_language', 'lead_create', 'dashboard',
        'analytics', 'contest', 'contest_login', 'contest_logout', 'contest_submit',
    )}
    bootstrap = {
        'page': page, 'language': get_request_language(request), 'csrf': get_token(request),
        'path': request.get_full_path(), 'routes': routes, 'logo': static('img/logo.jpg'),
        'user': {'id': request.user.pk, 'username': request.user.get_username(),
                 'name': request.user.first_name or request.user.get_username()} if request.user.is_authenticated else None,
        'translations': TRANSLATIONS, 'props': page_props(page, context),
        'messages': [{'text': str(m), 'level': m.tags} for m in get_messages(request)],
    }
    if 'application/json' in request.headers.get('Accept', ''):
        response = JsonResponse(bootstrap)
    else:
        manifest = json.loads((settings.BASE_DIR / 'static/react/.vite/manifest.json').read_text())
        entry = manifest['src/main.jsx']
        response = render(request, 'react.html', {
            'bootstrap': bootstrap,
            'bootstrap_script': json_script(bootstrap, 'byte-bootstrap', encoder=UnicodeJSONEncoder),
            'react_js': static('react/' + entry['file']),
            'react_css': [static('react/' + css) for css in entry.get('css', [])],
        }, **kwargs)
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ["Accept"])
    return response
