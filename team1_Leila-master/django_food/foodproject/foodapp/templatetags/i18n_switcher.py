from django import template
from django.conf import settings
from django.urls import translate_url
from django.utils.translation import get_language

register = template.Library()

@register.simple_tag(takes_context=True)
def change_lang(context, lang=None, *args, **kwargs):
    """
    Get active page's url by a specified language
    Usage: {% change_lang 'en' %}
    """
    path = context.get('request').get_full_path()
    return translate_url(path, lang) if lang else path

@register.filter
def get_language_info_list(languages):
    """
    Get list of available languages
    Usage: {{ LANGUAGES|get_language_info_list }}
    """
    current_language = get_language()
    return [
        {
            'code': code,
            'name': name,
            'current': code == current_language,
        }
        for code, name in languages
    ]
