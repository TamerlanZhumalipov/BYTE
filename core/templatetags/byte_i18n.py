from django import template

from core.localization import tr

register = template.Library()


@register.simple_tag(takes_context=True)
def bt(context, text):
    return tr(text, context.get("site_lang", "ru"))
