from django.urls import path
from . import views
from . import views_admin
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from .views_i18n import set_language_custom
from .views import RestaurantRegistrationWizard
from .forms import (
    RestaurantAuthInfoForm, RestaurantBasicInfoForm,
    RestaurantOwnerInfoForm, RestaurantLegalDocsForm, RestaurantPhotosForm
)

# Fonction pour rediriger vers login
def redirect_to_login(request):
    return redirect('login')

# Fonction pour rediriger vers l'inscription restaurant par étapes
def redirect_to_restaurant_wizard(request):
    return redirect('restaurant_register')

# Define the form list for the wizard
RESTAURANT_WIZARD_FORMS = [
    ("auth_info", RestaurantAuthInfoForm),
    ("basic_info", RestaurantBasicInfoForm),
    ("owner_info", RestaurantOwnerInfoForm),
    ("legal_docs", RestaurantLegalDocsForm),
    ("photos", RestaurantPhotosForm),
]

# Define the form list for the wizard
RESTAURANT_WIZARD_FORMS = [
    ("auth_info", RestaurantAuthInfoForm),
    ("basic_info", RestaurantBasicInfoForm),
    ("owner_info", RestaurantOwnerInfoForm),
    ("legal_docs", RestaurantLegalDocsForm),
    ("photos", RestaurantPhotosForm),
]

# Create the wizard view with the form list
restaurant_registration_wizard = RestaurantRegistrationWizard.as_view(form_list=RESTAURANT_WIZARD_FORMS)

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
    path('restaurant/menu/', views.restaurant_dashboard, name='restaurant_menu'),  # Temporairement mappé    # Menu management
    path('restaurant/menu/manage/<int:restaurant_id>/', views.manage_restaurant_menu, name='restaurant_menu_manage'),
    path('restaurant/dish/add/', views.add_dish, name='add_dish'),
    path('restaurant/dish/<int:dish_id>/edit/', views.edit_dish, name='edit_dish'),
    path('restaurant/dish/<int:dish_id>/delete/', views.delete_dish, name='delete_dish'),
    path('restaurant/category/add/', views.add_category, name='add_category'),
    path('restaurant/category/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('restaurant/category/<int:category_id>/delete/', views.delete_category, name='delete_category'),  # Gestion du menu
    path('restaurant/menu/create/', views.restaurant_menu_create, name='restaurant_menu_create'),  # Nouvelle route pour créer un plat
    path('restaurant/reservations/', views.restaurant_dashboard, name='restaurant_reservations'),  # Temporairement mappé vers dashboard
    path('restaurant/settings/', views.restaurant_dashboard, name='restaurant_settings'),  # Temporairement mappé vers dashboard
    
    # API Restaurant
    path('restaurant/create-order/', views.create_order, name='create_order'),  # Vue pour créer une commande
    path('restaurant/pos/<int:restaurant_id>/', views.restaurant_pos, name='restaurant_pos'),  # Vue pour l'interface caisse
    path('restaurant/kitchen/<int:restaurant_id>/', views.kitchen_dashboard, name='kitchen_dashboard'),  # Vue pour l'interface cuisine
    
    # User routes
    path('user/profile/', views.user_profile, name='user_profile'),
    path('user/reservations/', views.user_reservations_list, name='user_reservations_list'),
    path('user/settings/', views.user_settings, name='user_settings'),
    
    # Internationalization
    path('i18n/setlang/', set_language_custom, name='set_language_custom'),
    
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
    path('restaurant/register/', restaurant_registration_wizard, name='restaurant_register'),

    # API Endpoints
    path('api/cart/add/', views.add_to_cart, name='api_add_to_cart'),
    
    # Chatbot URLs
    path('chat/', views.chat_view, name='chat'),
    path('chat/message/', views.chat_message, name='chat_message'),
    path('chat/preferences/', views.update_chat_preferences, name='chat_preferences'),

    # Dashboard restaurant
    path('dashboard/restaurant/', views.restaurant_owner_dashboard, name='restaurant_owner_dashboard'),
    
    # Dashboard admin pour gérer les restaurants
    path('dashboard/admin/restaurants/', views_admin.restaurant_lists_filtered, name='restaurant_lists_filtered'),
    path('dashboard/admin/restaurants/<int:restaurant_id>/', views_admin.admin_restaurant_detail, name='admin_restaurant_detail'),
    
    # Édition du profil restaurant
    path('restaurant/edit/<int:restaurant_id>/', views.restaurant_edit, name='restaurant_edit'),
    path('dashboard/admin/restaurants/<int:restaurant_id>/update-status/', views_admin.update_restaurant_status, name='update_restaurant_status'),
    path('dashboard/admin/restaurants/<int:restaurant_id>/add-note/', views_admin.add_restaurant_note, name='add_restaurant_note'),
    path('dashboard/admin/restaurants/<int:restaurant_id>/<str:action>/', views.restaurant_approval, name='restaurant_approval'),
    
    # Subscription URLs
    path('subscription/plans/', views.user_pricing_plans, name='user_pricing_plans'),
    path('subscription/checkout/<str:plan_type>/<int:plan_id>/', views.subscription_checkout, name='subscription_checkout'),
    path('subscription/my-plan/', views.user_subscription, name='user_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/update-auto-renew/', views.update_auto_renew, name='update_auto_renew'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)