from django.urls import path
from . import views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from .views import RestaurantRegistrationWizard
from .forms import RestaurantBasicInfoForm, RestaurantOwnerInfoForm, RestaurantLegalDocsForm, RestaurantPhotosForm

# Fonction pour rediriger vers login
def redirect_to_login(request):
    return redirect('login')

# Fonction pour rediriger vers l'inscription restaurant par étapes
def redirect_to_restaurant_wizard(request):
    return redirect('restaurant_register')

urlpatterns = [
    # Pages principales
    path('', views.index, name='index'),
    path('accueil/', views.accueil, name='accueil'),
    path('restaurants/', views.restaurants, name='restaurants'),
    path('restaurants/<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),
    path('reservation/<int:restaurant_id>/', views.reservation, name='reservation'),
    path('dish-list/', views.dish_list, name='dish_list'),
    path('dish/<int:dish_id>/', views.dish_detail, name='dish_detail'),

    # Restaurant dashboard
    path('restaurant/dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant/orders/', views.restaurant_orders, name='restaurant_orders'),
    path('restaurant/orders/live/', views.restaurant_orders_live, name='restaurant_orders_live'),
    
    # Dashboard admin
    path('dashboard/admin/restaurants/', views.restaurant_lists, name='admin_restaurants'),
    path('restaurant/lists/', views.restaurant_lists, name='restaurant_lists'),
    path('restaurant/approve/<int:restaurant_id>/', views.approve_restaurant, name='approve_restaurant'),
    path('restaurant/sanction/<int:restaurant_id>/', views.sanction_restaurant, name='sanction_restaurant'),
    path('restaurant/unsanction/<int:restaurant_id>/', views.unsanction_restaurant, name='unsanction_restaurant'),
]

# Ajouter les URLs pour les médias si en mode développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 