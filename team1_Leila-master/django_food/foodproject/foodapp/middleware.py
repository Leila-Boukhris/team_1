from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.conf.locale import LANG_INFO

class UserLanguageMiddleware(MiddlewareMixin):
    """
    Middleware pour définir automatiquement la langue de l'utilisateur
    en fonction de sa préférence dans le profil ou de la session.
    """
    def process_request(self, request):
        language = None
        
        # 1. Vérifier d'abord la langue dans la session
        if hasattr(request, 'session'):
            language = request.session.get('django_language')
        
        # 2. Si pas dans la session, vérifier le cookie
        if not language and hasattr(request, 'COOKIES'):
            language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        
        # 3. Si toujours pas de langue, vérifier le profil utilisateur
        if not language and hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'language'):
                language = request.user.profile.language
        
        # 4. Si toujours pas de langue, utiliser la langue par défaut
        if not language or language not in dict(settings.LANGUAGES).keys():
            language = settings.LANGUAGE_CODE
        
        # Activer la langue pour cette requête
        translation.activate(language)
        request.LANGUAGE_CODE = language
        
        # Mettre à jour la session si nécessaire
        if hasattr(request, 'session') and \
           request.session.get('django_language') != language:
            request.session['django_language'] = language
