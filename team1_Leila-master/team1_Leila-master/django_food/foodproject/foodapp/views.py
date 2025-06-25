from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django import forms
import os
import json
import threading
from .models import Restaurant, RestaurantAccount, RestaurantDraft, City
from django.utils import timezone
from datetime import timedelta

class RestaurantRegistrationWizard(SessionWizardView):
    FORMS = [
        ("basic_info", "RestaurantBasicInfoForm"),
        ("owner_info", "RestaurantOwnerInfoForm"),
        ("legal_docs", "RestaurantLegalDocsForm"),
        ("photos", "RestaurantPhotosForm"),
    ]

    # Configuration des fichiers
    ALLOWED_EXTENSIONS = {
        'owner_id_card': ['.jpg', '.jpeg', '.png', '.pdf'],
        'business_registration': ['.pdf'],
        'food_safety_certificate': ['.pdf'],
        'tax_document': ['.pdf'],
        'main_image': ['.jpg', '.jpeg', '.png'],
        'interior_image1': ['.jpg', '.jpeg', '.png'],
        'interior_image2': ['.jpg', '.jpeg', '.png'],
        'menu_sample': ['.jpg', '.jpeg', '.png', '.pdf']
    }
    
    def get_template_names(self):
        return ["foodapp/restaurant_registration.html"]

# Vue pour afficher les listes des restaurants approuvés et sanctionnés
@login_required
@user_passes_test(lambda u: u.is_staff)
def restaurant_lists(request):
    # Récupérer tous les restaurants
    pending_restaurants = RestaurantAccount.objects.filter(is_approved=False, is_sanctioned=False)
    approved_restaurants = RestaurantAccount.objects.filter(is_approved=True, is_sanctioned=False)
    sanctioned_restaurants = RestaurantAccount.objects.filter(is_sanctioned=True)

    # Calculer les statistiques pour les restaurants en attente
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # Restaurants créés aujourd'hui
    new_today = pending_restaurants.filter(created_at__date=today)
    
    # Restaurants en attente depuis plus de 7 jours
    old_pending = pending_restaurants.filter(created_at__date__lte=week_ago)

    # Statistiques par ville
    cities = City.objects.all()
    for city in cities:
        city.pending_count = pending_restaurants.filter(restaurant__city=city).count()

    context = {
        'pending_restaurants': pending_restaurants,
        'approved_restaurants': approved_restaurants,
        'sanctioned_restaurants': sanctioned_restaurants,
        'cities': cities,
        'new_today_count': new_today.count(),
        'old_pending_count': old_pending.count(),
    }
    
    return render(request, 'foodapp/restaurant_lists.html', context)

# Vue pour approuver un restaurant
@login_required
@user_passes_test(lambda u: u.is_superuser)
def approve_restaurant(request, restaurant_id):
    """Approuve un restaurant en attente"""
    if request.method == 'POST':
        restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id, pending_approval=True)
        restaurant_account.is_active = True
        restaurant_account.pending_approval = False
        restaurant_account.save()
        
        # Activer le restaurant
        restaurant = restaurant_account.restaurant
        restaurant.is_open = True
        restaurant.save()
        
        # Envoyer un email de confirmation
        send_mail(
            'Votre restaurant a été approuvé - FoodFlex',
            f'Bonjour {restaurant_account.user.first_name},\n\n'
            f'Nous sommes heureux de vous informer que votre restaurant "{restaurant.name}" a été approuvé.\n'
            f'Vous pouvez maintenant vous connecter à votre compte et commencer à gérer votre restaurant.\n\n'
            f'Cordialement,\n'
            f'L\'équipe FoodFlex',
            settings.DEFAULT_FROM_EMAIL,
            [restaurant_account.user.email],
            fail_silently=True,
        )
        
        messages.success(request, f'Le restaurant "{restaurant.name}" a été approuvé avec succès.')
        
    return redirect('restaurant_dashboard')

# Vue pour sanctionner un restaurant
@login_required
@user_passes_test(lambda u: u.is_superuser)
def sanction_restaurant(request, restaurant_id):
    """Sanctionne un restaurant approuvé"""
    if request.method == 'POST':
        restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id, is_active=True)
        
        # Fermer le restaurant (mais garder le compte actif)
        restaurant = restaurant_account.restaurant
        restaurant.is_open = False
        restaurant.save()
        
        # Envoyer un email de notification
        send_mail(
            'Votre restaurant a été temporairement fermé - FoodFlex',
            f'Bonjour {restaurant_account.user.first_name},\n\n'
            f'Nous vous informons que votre restaurant "{restaurant.name}" a été temporairement fermé '
            f'suite à une décision administrative.\n\n'
            f'Veuillez nous contacter pour plus d\'informations.\n\n'
            f'Cordialement,\n'
            f'L\'équipe FoodFlex',
            settings.DEFAULT_FROM_EMAIL,
            [restaurant_account.user.email],
            fail_silently=True,
        )
        
        messages.warning(request, f'Le restaurant "{restaurant.name}" a été sanctionné.')
        
    return redirect('restaurant_lists')

# Vue pour lever la sanction d'un restaurant
@login_required
@user_passes_test(lambda u: u.is_superuser)
def unsanction_restaurant(request, restaurant_id):
    """Lève la sanction d'un restaurant"""
    if request.method == 'POST':
        restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id, is_active=True)
        
        # Réouvrir le restaurant
        restaurant = restaurant_account.restaurant
        restaurant.is_open = True
        restaurant.save()
        
        # Envoyer un email de notification
        send_mail(
            'Votre restaurant a été réouvert - FoodFlex',
            f'Bonjour {restaurant_account.user.first_name},\n\n'
            f'Nous sommes heureux de vous informer que votre restaurant "{restaurant.name}" '
            f'a été réouvert.\n\n'
            f'Vous pouvez maintenant reprendre vos activités normalement.\n\n'
            f'Cordialement,\n'
            f'L\'équipe FoodFlex',
            settings.DEFAULT_FROM_EMAIL,
            [restaurant_account.user.email],
            fail_silently=True,
        )
        
        messages.success(request, f'La sanction du restaurant "{restaurant.name}" a été levée.')
        
    return redirect('restaurant_lists') 