from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language

urlpatterns = [
    # URL pour le changement de langue
    path('i18n/', include('django.conf.urls.i18n')),
    
    # Les URLs qui ne doivent pas être internationalisées
    path('admin/', admin.site.urls),
    
    # Les URLs internationalisées
    path('', include('foodapp.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
