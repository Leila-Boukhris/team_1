from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Récupère un élément d'un dictionnaire par sa clé.
    Utilisé dans les templates pour accéder aux valeurs d'un dictionnaire.
    """
    return dictionary.get(key, 0)

@register.filter
def truncate_content(content, length=100):
    """
    Tronque le contenu d'un message à une longueur spécifiée.
    Utilisé pour afficher un aperçu du contenu des sujets.
    """
    if len(content) <= length:
        return content
    return content[:length] + "..." 