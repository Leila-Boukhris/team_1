from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire par sa clé"""
    return dictionary.get(key)

@register.filter
def split(value, delimiter=','):
    """Divise une chaîne en liste selon un délimiteur"""
    return value.split(delimiter)

@register.filter
def filesizeformat(bytes):
    """Formate une taille en bytes en format lisible"""
    try:
        bytes = float(bytes)
        kb = bytes / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        mb = kb / 1024
        if mb < 1024:
            return f"{mb:.1f} MB"
        gb = mb / 1024
        return f"{gb:.1f} GB"
    except:
        return "0 KB" 