from django import template
import re

register = template.Library()

@register.filter
def split(value, arg):
    """
    Découpe une chaîne de caractères selon un séparateur.
    Usage: {{ value|split:"," }}
    """
    return value.split(arg)

@register.filter
def trim(value):
    """
    Supprime les espaces en début et fin de chaîne.
    Usage: {{ value|trim }}
    """
    return value.strip() if value else value 