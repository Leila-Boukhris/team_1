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
    path('restaurant/orders/live/', views.restaurant_orders_live, name='restaurant_orders_live'),  # Nouvelle route pour les commandes en temps réel
    path('restaurant/stats/', views.restaurant_stats, name='restaurant_stats'),
    path('restaurant/reviews/', views.restaurant_reviews, name='restaurant_reviews'),
    path('restaurant/menu/', views.restaurant_dashboard, name='restaurant_menu'),  # Temporairement mappé vers dashboard
    path('restaurant/menu/create/', views.restaurant_menu_create, name='restaurant_menu_create'),  # Nouvelle route pour créer un plat
    path('restaurant/reservations/', views.restaurant_dashboard, name='restaurant_reservations'),  # Temporairement mappé vers dashboard
    path('restaurant/settings/', views.restaurant_dashboard, name='restaurant_settings'),  # Temporairement mappé vers dashboard
    
    # API Restaurant
    path('restaurant/create-order/', views.create_order, name='create_order'),  # Vue pour créer une commande
    
    # User routes
    path('user/profile/', views.user_profile, name='user_profile'),
    path('user/reservations/', views.user_reservations_list, name='user_reservations_list'),
    path('user/settings/', views.user_settings, name='user_settings'),
    
    # Cuisine et spécialités
    path('cuisine/moroccan/', views.moroccan_cuisine, name='moroccan_cuisine'),
    
    # Forum
    path('forum/', views.dashboard, name='forum_topics_list'),  # Temporairement redirigé vers dashboard
    
    # API
    path('api/dishes/', views.get_dishes, name='api_dishes'),
    path('api/restaurants/', views.get_restaurants, name='api_restaurants'),
    
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('restaurant-signup/', redirect_to_restaurant_wizard, name='restaurant_signup'),  # Redirection vers le wizard d'inscription
    path('restaurant/pending-approval/', views.restaurant_pending_approval, name='restaurant_pending_approval'),  # Page d'attente d'approbation
    path('restaurant/registration-confirmation/', views.restaurant_registration_confirmation, name='restaurant_registration_confirmation'),  # Page de confirmation

    # Legal
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),

    path('restaurants/register/', views.register_restaurant, name='register_restaurant'),

    path('restaurant/register/', 
         RestaurantRegistrationWizard.as_view([
             RestaurantBasicInfoForm,
             RestaurantOwnerInfoForm,
             RestaurantLegalDocsForm,
             RestaurantPhotosForm
         ]), 
         name='restaurant_register'),

    # API Endpoints
    path('api/cart/add/', views.add_to_cart, name='api_add_to_cart'),
    
    # Chatbot URLs
    path('chat/', views.chat_view, name='chat'),
    path('chat/message/', views.chat_message, name='chat_message'),
    path('chat/preferences/', views.update_chat_preferences, name='chat_preferences'),

    # Dashboard restaurant
    path('dashboard/restaurant/', views.restaurant_owner_dashboard, name='restaurant_owner_dashboard'),
    
    # Dashboard admin pour gérer les restaurants
    path('dashboard/admin/restaurants/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('dashboard/admin/restaurants/<int:restaurant_id>/<str:action>/', views.restaurant_approval, name='restaurant_approval'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 