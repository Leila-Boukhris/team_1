from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('foodapp.urls')),
    
    # Les URLs d'authentification sont gérées dans foodapp.urls
    # path('accounts/login/', auth_views.LoginView.as_view(template_name='foodapp/auth/login.html'), name='login'),
    # path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
