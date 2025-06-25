from django import template
from django.conf import settings

register = template.Library()

@register.filter
def get_image_url(obj, field_name='image'):
    """
    Returns the URL of an image field if it exists, otherwise returns a default image URL.
    Usage: {{ object|get_image_url:'field_name' }}
    """
    image_field = getattr(obj, field_name, None)
    if image_field and hasattr(image_field, 'url'):
        return image_field.url
    
    # Return appropriate default image based on model type
    model_name = obj.__class__.__name__.lower()
    if model_name == 'dish':
        return settings.STATIC_URL + 'foodapp/img/default-dish.jpg'
    elif model_name == 'restaurant':
        return settings.STATIC_URL + 'foodapp/img/default-restaurant.jpg'
    elif model_name == 'city':
        return settings.STATIC_URL + 'foodapp/img/default-city.jpg'
    else:
        return settings.STATIC_URL + 'foodapp/img/default.jpg'

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