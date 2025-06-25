from django.core.management.base import BaseCommand
from django.utils import timezone
from foodapp.models import SubscriptionPlan
import datetime

class Command(BaseCommand):
    help = 'Crée les plans d\'abonnement par défaut'

    def handle(self, *args, **kwargs):
        # Supprimer tous les plans existants avant de recréer
        # SubscriptionPlan.objects.all().delete()
        
        # Plans pour restaurants
        restaurant_plans = [
            {
                'name': 'Free',
                'plan_type': 'restaurant',
                'price_monthly': 0.00,
                'price_yearly': 0.00,
                'description': 'Plan gratuit avec fonctionnalités de base',
                'is_active': True,
                'features': {
                    'listing_visibility': 'standard',
                    'max_dishes': 5,
                    'reservations': True,
                    'analytics': False,
                    'featured_listing': False,
                    'support': 'email',
                    'reviews_management': False,
                    'profile_customization': 'basic',
                },
                'max_listings': 1,
                'badge_text': 'FREE',
                'is_featured': False,
                'discount_percent': 0,
            },
            {
                'name': 'Basic',
                'plan_type': 'restaurant',
                'price_monthly': 9.99,
                'price_yearly': 99.90,
                'description': 'Plan idéal pour les petits restaurants',
                'is_active': True,
                'features': {
                    'listing_visibility': 'enhanced',
                    'max_dishes': 15,
                    'reservations': True,
                    'analytics': True,
                    'featured_listing': False,
                    'support': 'email',
                    'reviews_management': True,
                    'profile_customization': 'standard',
                    'discount_codes': True,
                },
                'max_listings': 1,
                'badge_text': None,
                'is_featured': False,
                'discount_percent': 10,
            },
            {
                'name': 'Premium',
                'plan_type': 'restaurant',
                'price_monthly': 29.99,
                'price_yearly': 299.90,
                'description': 'Notre plan le plus populaire avec toutes les fonctionnalités essentielles',
                'is_active': True,
                'features': {
                    'listing_visibility': 'premium',
                    'max_dishes': 50,
                    'reservations': True,
                    'analytics': True,
                    'featured_listing': True,
                    'support': 'priority',
                    'reviews_management': True,
                    'profile_customization': 'advanced',
                    'discount_codes': True,
                    'marketing_tools': True,
                    'featured_in_search': True,
                },
                'max_listings': 1,
                'badge_text': 'PREMIUM',
                'is_featured': True,
                'discount_percent': 15,
            },
            {
                'name': 'Professional',
                'plan_type': 'restaurant',
                'price_monthly': 79.99,
                'price_yearly': 799.90,
                'description': 'Plan complet pour les restaurants professionnels avec chaînes multiples',
                'is_active': True,
                'features': {
                    'listing_visibility': 'maximum',
                    'max_dishes': -1,  # illimité
                    'reservations': True,
                    'analytics': True,
                    'featured_listing': True,
                    'support': '24/7',
                    'reviews_management': True,
                    'profile_customization': 'complete',
                    'discount_codes': True,
                    'marketing_tools': True,
                    'featured_in_search': True,
                    'api_access': True,
                    'dedicated_account_manager': True,
                },
                'max_listings': 5,
                'badge_text': 'PRO',
                'is_featured': False,
                'discount_percent': 20,
            },
        ]
        
        # Plans pour utilisateurs
        user_plans = [
            {
                'name': 'Free',
                'plan_type': 'user',
                'price_monthly': 0.00,
                'price_yearly': 0.00,
                'description': 'Fonctionnalités de base pour les utilisateurs',
                'is_active': True,
                'features': {
                    'reservations': True,
                    'reviews': True,
                    'favorites': 5,
                    'notifications': False,
                },
                'max_listings': 0,
                'badge_text': None,
                'is_featured': False,
                'discount_percent': 0,
            },
            {
                'name': 'FoodLover',
                'plan_type': 'user',
                'price_monthly': 4.99,
                'price_yearly': 49.90,
                'description': 'Pour les amateurs de cuisine qui veulent plus de fonctionnalités',
                'is_active': True,
                'features': {
                    'reservations': True,
                    'reviews': True,
                    'favorites': -1, # illimité
                    'notifications': True,
                    'priority_booking': True,
                    'discount_access': True,
                    'premium_content': True,
                },
                'max_listings': 0,
                'badge_text': 'FOODIE',
                'is_featured': True,
                'discount_percent': 10,
            }
        ]
        
        # Créer les plans restaurant
        for plan_data in restaurant_plans:
            SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
        
        # Créer les plans utilisateur
        for plan_data in user_plans:
            SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
        
        self.stdout.write(self.style.SUCCESS('Plans d\'abonnement créés avec succès !')) 