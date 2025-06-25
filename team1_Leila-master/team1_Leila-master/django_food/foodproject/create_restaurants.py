#!/usr/bin/env python
import os
import django

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodproject.settings')
django.setup()

# Importer les modèles après configuration de Django
from django.contrib.auth.models import User
from foodapp.models import City, Restaurant, RestaurantAccount

def create_test_restaurants():
    """Créer des exemples de restaurants pour tester le dashboard d'administration"""
    print("Création d'exemples de restaurants...")

    # Vérifier s'il y a déjà des utilisateurs admin
    admin_exists = User.objects.filter(is_superuser=True).exists()
    if not admin_exists:
        # Créer un utilisateur administrateur
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        print("Utilisateur admin créé")

    # Vérifier s'il y a des villes, sinon en créer une
    if not City.objects.exists():
        city = City.objects.create(name='Casablanca', country='Morocco')
        print("Ville créée: Casablanca")
    else:
        city = City.objects.first()
        print(f"Utilisation de la ville existante: {city.name}")

    # 1. Restaurant en attente d'approbation
    if not RestaurantAccount.objects.filter(pending_approval=True, is_active=False).exists():
        # Créer l'utilisateur
        pending_user = User.objects.create_user(
            username='pending_resto',
            email='pending@example.com',
            password='password123',
            first_name='Omar',
            last_name='Benali'
        )
        
        # Créer le restaurant
        pending_restaurant = Restaurant.objects.create(
            name='Restaurant Attente',
            city=city,
            address='123 Avenue Hassan II',
            phone='0612345678',
            email='pending@example.com',
            description='Un nouveau restaurant traditionnel marocain en attente d\'approbation',
            is_open=False,
            capacity=40
        )
        
        # Créer le compte restaurant
        RestaurantAccount.objects.create(
            user=pending_user,
            restaurant=pending_restaurant,
            is_active=False,
            pending_approval=True
        )
        print("Restaurant en attente créé: Restaurant Attente")

    # 2. Restaurant approuvé
    if not RestaurantAccount.objects.filter(is_active=True, restaurant__is_open=True).exists():
        # Créer l'utilisateur
        approved_user = User.objects.create_user(
            username='approved_resto',
            email='approved@example.com',
            password='password123',
            first_name='Karim',
            last_name='Alami'
        )
        
        # Créer le restaurant
        approved_restaurant = Restaurant.objects.create(
            name='Restaurant Approuvé',
            city=city,
            address='456 Rue Mohammed V',
            phone='0623456789',
            email='approved@example.com',
            description='Un restaurant moderne avec une cuisine fusion approuvé',
            is_open=True,
            capacity=60
        )
        
        # Créer le compte restaurant
        RestaurantAccount.objects.create(
            user=approved_user,
            restaurant=approved_restaurant,
            is_active=True,
            pending_approval=False
        )
        print("Restaurant approuvé créé: Restaurant Approuvé")

    # 3. Restaurant sanctionné
    if not RestaurantAccount.objects.filter(is_active=True, restaurant__is_open=False).exists():
        # Créer l'utilisateur
        sanctioned_user = User.objects.create_user(
            username='sanctioned_resto',
            email='sanctioned@example.com',
            password='password123',
            first_name='Samir',
            last_name='Rachidi'
        )
        
        # Créer le restaurant
        sanctioned_restaurant = Restaurant.objects.create(
            name='Restaurant Sanctionné',
            city=city,
            address='789 Boulevard Anfa',
            phone='0634567890',
            email='sanctioned@example.com',
            description='Un restaurant sanctionné temporairement',
            is_open=False,
            capacity=30
        )
        
        # Créer le compte restaurant
        RestaurantAccount.objects.create(
            user=sanctioned_user,
            restaurant=sanctioned_restaurant,
            is_active=True,
            pending_approval=False
        )
        print("Restaurant sanctionné créé: Restaurant Sanctionné")

    print("Création d'exemples terminée.")
    
    # Afficher les totaux
    print(f"Nombre de restaurants en attente: {RestaurantAccount.objects.filter(pending_approval=True, is_active=False).count()}")
    print(f"Nombre de restaurants approuvés: {RestaurantAccount.objects.filter(is_active=True, restaurant__is_open=True).count()}")
    print(f"Nombre de restaurants sanctionnés: {RestaurantAccount.objects.filter(is_active=True, restaurant__is_open=False).count()}")

if __name__ == '__main__':
    create_test_restaurants() 