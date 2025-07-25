from django.shortcuts import redirect
from django.utils.translation import activate, get_language, gettext_lazy as _
from django.utils import translation
from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib import messages

def set_language_custom(request):
    """
    Custom language switching view that preserves the current page and handles user language preferences
    """
    if request.method == 'POST':
        language = request.POST.get('language')
        next_page = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        
        if language and language in dict(settings.LANGUAGES).keys():
            # Update language in session
            if hasattr(request, 'session'):
                request.session[translation.LANGUAGE_SESSION_KEY] = language
                request.session['django_language'] = language
            
            # Update language for authenticated user's profile
            if hasattr(request, 'user') and request.user.is_authenticated:
                profile = getattr(request.user, 'profile', None)
                if profile and hasattr(profile, 'language'):
                    profile.language = language
                    profile.save()
            
            # Activate the language for the current thread
            translation.activate(language)
            
            # Create response with redirect
            response = HttpResponseRedirect(next_page)
            
            # Set language cookie
            if hasattr(settings, 'LANGUAGE_COOKIE_NAME'):
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    language,
                    max_age=getattr(settings, 'LANGUAGE_COOKIE_AGE', 365*24*60*60),
                    path=getattr(settings, 'LANGUAGE_COOKIE_PATH', '/'),
                    domain=getattr(settings, 'LANGUAGE_COOKIE_DOMAIN', None),
                    secure=getattr(settings, 'LANGUAGE_COOKIE_SECURE', False),
                    httponly=getattr(settings, 'LANGUAGE_COOKIE_HTTPONLY', False),
                    samesite=getattr(settings, 'LANGUAGE_COOKIE_SAMESITE', 'Lax')
                )
            
            # Add success message
            messages.success(request, _('Language changed successfully'))
            
            return response
    
    # Default redirect if something goes wrong
    return redirect(next_page if 'next_page' in locals() else '/')
