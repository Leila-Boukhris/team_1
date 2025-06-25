from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView
from .models import City, Dish, Restaurant, Reservation, RestaurantAccount, UserProfile, ForumTopic, ForumMessage, SubscriptionPlan, RestaurantSubscription, UserSubscription, Order, OrderItem, RestaurantDraft, Review, ChatSession, ChatMessage, ChatbotKnowledge
from .forms import DishFilterForm, CurrencyConverterForm, ReservationForm, ReservationModifyForm, RestaurantBasicInfoForm, RestaurantOwnerInfoForm, RestaurantLegalDocsForm, RestaurantPhotosForm
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum, Avg, F, Max
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
import json
import datetime
from django.urls import reverse
from django.shortcuts import redirect
from django.middleware.csrf import get_token
from django.core.cache import cache
from django.utils import timezone
import time
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
from .chatbot import MoroccanFoodChatbot
from django.utils.crypto import get_random_string
from django.db import models, transaction
import threading

try:
    from cpp_modules.food_processor import fast_sort_dishes
    USE_CPP_OPTIMIZATION = True
except ImportError:
    USE_CPP_OPTIMIZATION = False
    print("Module C++ non disponible, utilisation du tri Python standard")

def index(request):
    return redirect('accueil')

def accueil(request):
    # Récupérer uniquement les plats créés via l'interface d'administration Django
    featured_dishes = Dish.objects.filter(is_admin_created=True).order_by('?')[:5]
    dishes = Dish.objects.filter(is_admin_created=True).order_by('-id')[:8]
    cities = City.objects.all()[:4]
    context = {
        'featured_dishes': featured_dishes,
        'dishes': dishes,
        'cities': cities,
    }
    return render(request, 'foodapp/accueil.html', context)

class CityListView(ListView):
    model = City
    template_name = 'foodapp/city_list.html'
    context_object_name = 'cities'

def city_list(request):
    """Vue pour afficher la liste des villes"""
    cities = City.objects.filter(is_active=True).order_by('name')
    
    context = {
        'cities': cities,
    }
    
    return render(request, 'foodapp/city_list.html', context)

def city_detail(request, city_id):
    """Vue pour afficher le détail d'une ville"""
    city = get_object_or_404(City, pk=city_id, is_active=True)
    restaurants = Restaurant.objects.filter(city=city, is_open=True)
    dishes = Dish.objects.filter(city=city)
    
    context = {
        'city': city,
        'restaurants': restaurants,
        'dishes': dishes,
    }
    
    return render(request, 'foodapp/city_detail.html', context)

def dish_list(request):
    # Récupérer uniquement les plats créés via l'interface d'administration Django
    dishes = Dish.objects.filter(is_admin_created=True)
    sort_by = request.GET.get('sort', 'name')
    city_id = request.GET.get('city')
    dish_type = request.GET.get('dish_type')
    price_range = request.GET.get('price_range')
    dietary = request.GET.get('dietary')
    
    # Health restriction filters
    health_filters = {
        'sugar_free': request.GET.get('sugar_free'),
        'cholesterol_free': request.GET.get('cholesterol_free'),
        'gluten_free': request.GET.get('gluten_free'),
        'lactose_free': request.GET.get('lactose_free'),
        'nut_free': request.GET.get('nut_free'),
        'diabetic_friendly': request.GET.get('diabetic_friendly'),
        'low_calorie': request.GET.get('low_calorie'),
        'max_calories': request.GET.get('max_calories')
    }

    if city_id:
        dishes = dishes.filter(city_id=city_id)

    if dish_type:
        dishes = dishes.filter(type=dish_type)

    if price_range:
        dishes = dishes.filter(price_range=price_range)

    if dietary == 'vegetarian':
        dishes = dishes.filter(is_vegetarian=True)
    elif dietary == 'vegan':
        dishes = dishes.filter(is_vegan=True)

    # Apply health restriction filters
    if health_filters['sugar_free'] == 'on':
        dishes = dishes.filter(has_sugar=False)
    if health_filters['cholesterol_free'] == 'on':
        dishes = dishes.filter(has_cholesterol=False)
    if health_filters['gluten_free'] == 'on':
        dishes = dishes.filter(has_gluten=False)
    if health_filters['lactose_free'] == 'on':
        dishes = dishes.filter(has_lactose=False)
    if health_filters['nut_free'] == 'on':
        dishes = dishes.filter(has_nuts=False)
    if health_filters['diabetic_friendly'] == 'on':
        dishes = dishes.filter(is_diabetic_friendly=True)
    if health_filters['low_calorie'] == 'on':
        dishes = dishes.filter(is_low_calorie=True)
    if health_filters['max_calories']:
        try:
            max_calories = int(health_filters['max_calories'])
            dishes = dishes.filter(calories__lte=max_calories)
        except (ValueError, TypeError):
            pass

    if USE_CPP_OPTIMIZATION:
        # Convertir les plats en format compatible avec le module C++
        dishes_data = [
            {
                'id': dish.id,
                'name': dish.name,
                'price_range': dish.price_range,
                'type': dish.type,
                'city_id': dish.city.id if dish.city else 0
            }
            for dish in dishes
        ]
        
        # Utiliser le tri rapide C++
        sorted_dishes = fast_sort_dishes(dishes_data, sort_by)
        
        # Reconvertir en QuerySet Django
        dish_ids = [dish['id'] for dish in sorted_dishes]
        dishes = Dish.objects.filter(id__in=dish_ids)
        # Préserver l'ordre du tri C++
        dishes = sorted(dishes, key=lambda x: dish_ids.index(x.id))
    else:
        # Tri Python standard
        if sort_by == 'price_asc':
            dishes = dishes.order_by('price_range')
        elif sort_by == 'price_desc':
            dishes = dishes.order_by('-price_range')
        elif sort_by == 'name':
            dishes = dishes.order_by('name')

    context = {
        'dishes': dishes,
        'current_sort': sort_by,
        'cities': City.objects.all(),
        'selected_city': city_id,
        'selected_dish_type': dish_type,
        'selected_price_range': price_range,
        'selected_dietary': dietary,
        'dish_types': Dish.TYPE_CHOICES,
        'price_ranges': Dish.PRICE_RANGE_CHOICES,
        'health_filters': health_filters
    }
    
    return render(request, 'foodapp/dish_list.html', context)


def restaurants(request):
    restaurants = Restaurant.objects.all()
    cities = City.objects.all()
    
    # Filtrer par ville si spécifié
    city_id = request.GET.get('city')
    if city_id:
        restaurants = restaurants.filter(city_id=city_id)
    
    # Filtrer par statut (ouvert/fermé) si spécifié
    status = request.GET.get('status')
    if status:
        is_open = status == 'open'
        restaurants = restaurants.filter(is_open=is_open)
    
    # Rechercher par nom si spécifié
    search = request.GET.get('search')
    if search:
        restaurants = restaurants.filter(name__icontains=search)
    
    context = {
        'restaurants': restaurants,
        'cities': cities
    }
    return render(request, 'foodapp/modern_restaurants.html', context)


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            # Essayer de lire les données JSON si disponibles
            try:
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
                remember = data.get('remember', False)
            except:
                # Sinon, traiter comme un formulaire standard
                username = request.POST.get('username')
                password = request.POST.get('password')
                remember = request.POST.get('remember', False)
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Si "remember me" n'est pas coché, le cookie de session expirera à la fermeture du navigateur
                if not remember:
                    request.session.set_expiry(0)
                
                # Vérifier si c'est un compte restaurant et rediriger en conséquence
                try:
                    if hasattr(user, 'restaurant_account') and user.restaurant_account.is_active:
                        # C'est un compte restaurant actif
                        if request.headers.get('Content-Type') == 'application/json':
                            return JsonResponse({
                                'success': True, 
                                'redirect': reverse('restaurant_dashboard'),
                                'account_type': 'restaurant'
                            }, status=200)
                        else:
                            return redirect('restaurant_dashboard')
                except:
                    pass
                
                # Compte utilisateur normal
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'success': True,
                        'account_type': 'user'
                    }, status=200)
                else:
                    return redirect('index')
            else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'errors': {'general': "Nom d'utilisateur ou mot de passe incorrect"}}, status=401)
                else:
                    # Pour les formulaires traditionnels, rediriger avec un message d'erreur
                    return render(request, 'foodapp/login.html', {
                        'error': "Nom d'utilisateur ou mot de passe incorrect"
                    })
        except Exception as e:
            return JsonResponse({'errors': {'general': str(e)}}, status=400)
    else:
        # Assurer que le token CSRF est généré
        csrf_token = get_token(request)
        return render(request, 'foodapp/login.html')

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def restaurant_dashboard(request):
    """Dashboard d'administration pour la gestion des restaurants"""
    if not request.user.is_superuser and not hasattr(request.user, 'userprofile'):
        messages.error(request, "Accès non autorisé")
        return redirect('accueil')
        
    # Récupérer les restaurants en attente d'approbation
    pending_restaurants = RestaurantAccount.objects.filter(pending_approval=True, is_active=False)
    
    # Récupérer les restaurants approuvés
    approved_restaurants = RestaurantAccount.objects.filter(is_active=True)
    
    # Récupérer les restaurants avec sanction
    sanctioned_restaurants = RestaurantAccount.objects.filter(is_active=True, restaurant__is_open=False)
    
    context = {
        'pending_restaurants': pending_restaurants,
        'approved_restaurants': approved_restaurants, 
        'sanctioned_restaurants': sanctioned_restaurants,
        'page_title': 'Dashboard Administration Restaurants'
    }
    
    return render(request, 'foodapp/restaurant_dashboard.html', context)

@login_required
@csrf_exempt
def restaurant_approval(request, restaurant_id, action):
    """Approuver ou rejeter un restaurant"""
    if not request.user.is_superuser:
        messages.error(request, "Accès non autorisé")
        return redirect('accueil')
    
    # Imprimer des informations de débogage
    print(f"Restaurant approval: id={restaurant_id}, action={action}")
    print(f"Requête: {request.method}")
        
    restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id)
    print(f"Restaurant account: {restaurant_account.id}, user={restaurant_account.user.username}, restaurant={restaurant_account.restaurant.name}")
    
    if action == 'approve':
        # Approuver le restaurant
        restaurant_account.is_active = True
        restaurant_account.pending_approval = False
        restaurant_account.restaurant.is_open = True
        restaurant_account.restaurant.save()
        restaurant_account.save()
        
        # Envoyer email de confirmation
        try:
            send_mail(
                'Votre restaurant a été approuvé',
                f"Cher {restaurant_account.user.first_name},\n\n"
                f"Nous sommes heureux de vous informer que votre restaurant '{restaurant_account.restaurant.name}' "
                f"a été approuvé et est maintenant visible sur notre plateforme.\n\n"
                f"Vous pouvez maintenant vous connecter et gérer votre restaurant.\n\n"
                f"L'équipe FoodFlex",
                'noreply@foodflex.com',
                [restaurant_account.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur d'envoi d'email: {str(e)}")
            
        messages.success(request, f"Le restaurant {restaurant_account.restaurant.name} a été approuvé")
        
    elif action == 'reject':
        # Rejeter le restaurant
        restaurant_account.pending_approval = False
        restaurant_account.save()
        
        # Envoyer email de rejet
        try:
            send_mail(
                'Demande de restaurant rejetée',
                f"Cher {restaurant_account.user.first_name},\n\n"
                f"Nous regrettons de vous informer que votre demande pour '{restaurant_account.restaurant.name}' "
                f"n'a pas été approuvée à ce stade.\n\n"
                f"Veuillez nous contacter pour plus d'informations.\n\n"
                f"L'équipe FoodFlex",
                'noreply@foodflex.com',
                [restaurant_account.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur d'envoi d'email: {str(e)}")
            
        messages.success(request, f"Le restaurant {restaurant_account.restaurant.name} a été rejeté")
        
    elif action == 'sanction':
        # Sanctionner le restaurant
        restaurant_account.restaurant.is_open = False
        restaurant_account.restaurant.save()
        
        # Envoyer email de sanction
        try:
            send_mail(
                'Sanction appliquée à votre restaurant',
                f"Cher {restaurant_account.user.first_name},\n\n"
                f"Nous vous informons qu'une sanction a été appliquée à votre restaurant '{restaurant_account.restaurant.name}'. "
                f"Votre restaurant est temporairement fermé sur notre plateforme.\n\n"
                f"Veuillez nous contacter pour plus d'informations et pour résoudre ce problème.\n\n"
                f"L'équipe FoodFlex",
                'noreply@foodflex.com',
                [restaurant_account.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur d'envoi d'email: {str(e)}")
            
        messages.success(request, f"Le restaurant {restaurant_account.restaurant.name} a été sanctionné")
        
    elif action == 'unsanction':
        # Lever la sanction
        restaurant_account.restaurant.is_open = True
        restaurant_account.restaurant.save()
        
        # Envoyer email de levée de sanction
        try:
            send_mail(
                'Sanction levée pour votre restaurant',
                f"Cher {restaurant_account.user.first_name},\n\n"
                f"Nous vous informons que la sanction appliquée à votre restaurant '{restaurant_account.restaurant.name}' "
                f"a été levée. Votre restaurant est à nouveau ouvert sur notre plateforme.\n\n"
                f"L'équipe FoodFlex",
                'noreply@foodflex.com',
                [restaurant_account.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur d'envoi d'email: {str(e)}")
            
        messages.success(request, f"La sanction pour le restaurant {restaurant_account.restaurant.name} a été levée")
    
    print(f"Action '{action}' terminée avec succès pour le restaurant {restaurant_account.restaurant.name}")
    return redirect('restaurant_dashboard')

@login_required
def restaurant_orders(request):
    """Vue pour la gestion des commandes d'un restaurant"""
    
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('accueil')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    # Récupérer les commandes de ce restaurant
    orders = Order.objects.filter(restaurant=restaurant).order_by('-order_time')
    
    # Commandes par statut
    new_orders = orders.filter(status=Order.STATUS_NEW)
    preparing_orders = orders.filter(status=Order.STATUS_PREPARING)
    ready_orders = orders.filter(status=Order.STATUS_READY)
    
    # Commandes à emporter
    takeaway_orders = orders.filter(is_takeaway=True, status__in=[Order.STATUS_NEW, Order.STATUS_PREPARING, Order.STATUS_READY])
    
    # Statistiques
    today = timezone.now().date()
    today_orders = orders.filter(order_time__date=today)
    today_orders_count = today_orders.count()
    in_progress_count = new_orders.count() + preparing_orders.count()
    ready_count = ready_orders.count()
    new_count = new_orders.count()
    preparing_count = preparing_orders.count()
    takeaway_count = takeaway_orders.count()
    
    # Chiffre d'affaires du jour
    today_revenue = today_orders.filter(status__in=[Order.STATUS_DELIVERED, Order.STATUS_PAID]).aggregate(
        total=Sum('total_amount'))['total'] or 0
    
    # Récupérer les plats disponibles pour le restaurant (pour le formulaire de création de commande)
    dishes = Dish.objects.filter(city=restaurant.city)
    
    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'orders': orders,
        'new_orders': new_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'takeaway_orders': takeaway_orders,
        'today_orders_count': today_orders_count,
        'in_progress_count': in_progress_count,
        'ready_count': ready_count,
        'new_count': new_count,
        'preparing_count': preparing_count,
        'takeaway_count': takeaway_count,
        'today_revenue': today_revenue,
        'dishes': dishes,
    }
    
    return render(request, 'foodapp/restaurant_orders.html', context)

@login_required
def restaurant_stats(request):
    """Vue pour les statistiques d'un restaurant"""
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('accueil')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    # Récupérer les dates de filtrage
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    
    # Dates par défaut (mois en cours)
    today = timezone.now().date()
    start_date = today.replace(day=1)  # Premier jour du mois
    end_date = today
    
    # Si des dates sont spécifiées, les utiliser
    if from_date:
        try:
            start_date = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if to_date:
        try:
            end_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Statistiques générales
    # Commandes de la période
    orders = Order.objects.filter(
        restaurant=restaurant,
        order_time__date__gte=start_date,
        order_time__date__lte=end_date
    )
    
    # Réservations de la période
    reservations = Reservation.objects.filter(
        restaurant=restaurant,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Calcul des métriques
    orders_count = orders.count()
    revenue = orders.filter(status__in=[Order.STATUS_DELIVERED, Order.STATUS_PAID]).aggregate(
        total=Sum('total_amount'))['total'] or 0
    
    # Panier moyen
    avg_order_value = 0
    if orders_count > 0:
        avg_order_value = round(revenue / orders_count, 2)
    
    reservations_count = reservations.count()
    
    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue,
        'orders_count': orders_count,
        'avg_order_value': avg_order_value,
        'reservations_count': reservations_count,
    }
    
    return render(request, 'foodapp/restaurant_stats.html', context)

@login_required
def restaurant_reviews(request):
    """Vue pour la gestion des avis d'un restaurant"""
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('accueil')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
    }
    
    return render(request, 'foodapp/restaurant_reviews.html', context)

@csrf_exempt
def dish_detail(request, dish_id):
    """Vue pour afficher le détail d'un plat"""
    dish = get_object_or_404(Dish, id=dish_id)
    
    # Traiter les ingrédients
    ingredients_list = []
    if dish.ingredients:
        ingredients_list = [ingredient.strip() for ingredient in dish.ingredients.split(',')]
    
    context = {
        'dish': dish,
        'ingredients_list': ingredients_list,
        'related_dishes': Dish.objects.filter(type=dish.type).exclude(id=dish.id)[:4]
    }
    return render(request, 'foodapp/dish_detail.html', context)

def get_dishes(request):
    """
    Vue API optimisée pour renvoyer les plats avec mise en cache
    """
    # Vérifier si les données sont en cache
    cache_key = 'admin_dishes_data'  # Clé modifiée pour distinguer des données précédentes
    dishes_data = cache.get(cache_key)
    
    if not dishes_data:
        # Si pas en cache, récupérer depuis la base de données
        start_time = time.time()
        # Filtre pour ne récupérer que les plats créés via l'interface d'administration
        dishes = Dish.objects.select_related('city').filter(is_admin_created=True)
        
        # Préparer les données pour la sérialisation JSON
        dishes_data = []
        for dish in dishes:
            dishes_data.append({
                'id': dish.id,
                'name': dish.name,
                'description': dish.description,
                'price_range': dish.price_range,
                'price_display': dish.get_price_range_display(),
                'type': dish.type,
                'type_display': dish.get_type_display(),
                'image': dish.image.url if dish.image else '',
                'is_vegetarian': dish.is_vegetarian,
                'is_vegan': dish.is_vegan,
                'ingredients': dish.ingredients,
                'history': dish.history,
                'preparation_steps': dish.preparation_steps,
                'city': {
                    'id': dish.city.id if dish.city else None,
                    'name': dish.city.name if dish.city else None
                },
                'timestamp': timezone.now().timestamp()  # Ajouter un horodatage pour le suivi
            })
        
        # Mettre en cache pour 10 minutes
        cache.set(cache_key, dishes_data, 60 * 10)
        
        print(f"Database query completed in {time.time() - start_time:.4f} seconds")
    
    return JsonResponse(dishes_data, safe=False)

def reservation(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    success = False
    reservation_obj = None
    
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            # Vérifier la disponibilité
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            guests = form.cleaned_data['guests']
            
            # Vérifier si le créneau est disponible
            if is_slot_available(restaurant, date, time, guests):
                reservation_obj = form.save(commit=False)
                reservation_obj.restaurant = restaurant
                if request.user.is_authenticated:
                    reservation_obj.user = request.user
                reservation_obj.save()
                success = True
            else:
                form.add_error(None, "Désolé, ce créneau n'est plus disponible. Veuillez choisir un autre horaire.")
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
                'phone': getattr(request.user.profile, 'phone', '') if hasattr(request.user, 'profile') else ''
            }
        form = ReservationForm(initial=initial_data)
    
    # Récupérer les créneaux disponibles pour JavaScript
    available_dates = get_available_dates(restaurant)
    
    context = {
        'restaurant': restaurant,
        'form': form,
        'success': success,
        'reservation': reservation_obj,
        'available_dates': json.dumps([date.strftime('%Y-%m-%d') for date in available_dates])
    }
    
    return render(request, 'foodapp/reservation.html', context)

def is_slot_available(restaurant, date, time, guests, exclude_reservation_id=None):
    """
    Vérifie si un créneau horaire est disponible pour un restaurant donné
    """
    # Récupérer toutes les réservations pour ce restaurant à cette date et heure
    reservations_query = Reservation.objects.filter(
        restaurant=restaurant,
        date=date,
        time=time,
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]
    )
    
    # Exclure une réservation spécifique (utile pour les modifications)
    if exclude_reservation_id:
        reservations_query = reservations_query.exclude(id=exclude_reservation_id)
    
    # Compter le nombre de convives déjà réservés
    total_guests = reservations_query.aggregate(Sum('guests'))['guests__sum'] or 0
    
    # Supposons qu'un restaurant peut accueillir au maximum 50 personnes simultanément
    # Cette valeur devrait être stockée dans le modèle du restaurant en pratique
    max_capacity = 50
    
    # Vérifier si l'ajout de nouveaux convives ne dépasse pas la capacité
    return (total_guests + guests) <= max_capacity

def get_available_dates(restaurant, start_date=None, days_ahead=30):
    """
    Renvoie les dates disponibles pour réserver dans ce restaurant
    """
    if start_date is None:
        start_date = timezone.now().date()
    
    # Générer une liste de dates pour les prochains jours
    available_dates = []
    for i in range(days_ahead):
        date = start_date + datetime.timedelta(days=i)
        # On pourrait vérifier ici si le restaurant est fermé certains jours
        # Par exemple si le restaurant est fermé le lundi
        if date.weekday() != 0:  # 0 = Lundi
            available_dates.append(date)
    
    return available_dates

def currency_converter(request):
    result = None
    rates = {
        'USD': Decimal('10.20'),  # Dollar américain
        'EUR': Decimal('11.10'),  # Euro
        'GBP': Decimal('12.90'),  # Livre sterling
        'CAD': Decimal('7.50'),   # Dollar canadien
        'AED': Decimal('2.78'),   # Dirham émirati
        'CHF': Decimal('11.45'),  # Franc suisse
        'JPY': Decimal('0.069'),  # Yen japonais
        'CNY': Decimal('1.41'),   # Yuan chinois
        'SAR': Decimal('2.72'),   # Riyal saoudien
    }
    
    form = CurrencyConverterForm(request.GET or None)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        from_currency = form.cleaned_data['from_currency']
        result = amount * rates[from_currency]

    return render(request, 'foodapp/currency_converter.html', {
        'form': form,
        'result': result,
        'rates': rates
    })

def restaurant_detail(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    city_dishes = Dish.objects.filter(city=restaurant.city).order_by('-id')[:6]
    
    context = {
        'restaurant': restaurant,
        'city_dishes': city_dishes,
    }
    
    return render(request, 'foodapp/restaurant_detail.html', context)

@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        try:
            # Essai de lecture JSON
            try:
                data = json.loads(request.body)
                is_ajax = True
            except json.JSONDecodeError:
                # Si ce n'est pas du JSON, c'est un formulaire normal
                data = request.POST
                is_ajax = False
                
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            account_type = data.get('account_type', 'user')
            
            # Validation des champs requis
            required_fields = ['username', 'email', 'password']
            if account_type == 'restaurant':
                required_fields.extend(['restaurant_name', 'restaurant_city', 'restaurant_phone', 'restaurant_address'])
            
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                error_message = f"Les champs suivants sont requis : {', '.join(missing_fields)}"
                if is_ajax:
                    return JsonResponse({'errors': {'general': error_message}}, status=400)
                else:
                    return render(request, 'foodapp/signup.html', {
                        'errors': {'general': error_message}, 
                        'cities': City.objects.all(),
                        'form_data': data
                    })
            
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                if is_ajax:
                    return JsonResponse({'errors': {'username': "Ce nom d'utilisateur est déjà pris"}}, status=400)
                else:
                    return render(request, 'foodapp/signup.html', {
                        'errors': {'username': "Ce nom d'utilisateur est déjà pris"}, 
                        'cities': City.objects.all(),
                        'form_data': data
                    })
            
            if User.objects.filter(email=email).exists():
                if is_ajax:
                    return JsonResponse({'errors': {'email': "Cette adresse email est déjà utilisée"}}, status=400)
                else:
                    return render(request, 'foodapp/signup.html', {
                        'errors': {'email': "Cette adresse email est déjà utilisée"}, 
                        'cities': City.objects.all(),
                        'form_data': data
                    })
            
            # Créer un nouvel utilisateur
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # Créer un profil utilisateur standard dans tous les cas
            UserProfile.objects.create(user=user)
            
            # Si c'est un compte restaurant, créer également un RestaurantAccount
            if account_type == 'restaurant':
                restaurant_name = data.get('restaurant_name')
                restaurant_city_id = data.get('restaurant_city')
                restaurant_phone = data.get('restaurant_phone')
                restaurant_address = data.get('restaurant_address')
                
                try:
                    city = City.objects.get(id=restaurant_city_id)
                    
                    # Créer le restaurant
                    restaurant = Restaurant.objects.create(
                        name=restaurant_name,
                        city=city,
                        address=restaurant_address,
                        phone=restaurant_phone,
                        email=email,
                        is_open=True
                    )
                    
                    # Associer le compte restaurant à l'utilisateur
                    RestaurantAccount.objects.create(
                        user=user,
                        restaurant=restaurant,
                        is_active=True,
                        account_type='basic'  # Type de compte par défaut
                    )
                    
                except City.DoesNotExist:
                    # Supprimer l'utilisateur créé en cas d'erreur
                    user.delete()
                    if is_ajax:
                        return JsonResponse({'errors': {'restaurant_city': "Ville non trouvée"}}, status=400)
                    else:
                        return render(request, 'foodapp/signup.html', {
                            'errors': {'restaurant_city': "Ville non trouvée"}, 
                            'cities': City.objects.all(),
                            'form_data': data
                        })
                except Exception as e:
                    # Supprimer l'utilisateur créé en cas d'erreur
                    user.delete()
                    if is_ajax:
                        return JsonResponse({'errors': {'general': f"Erreur lors de la création du restaurant: {str(e)}"}}, status=400)
                    else:
                        return render(request, 'foodapp/signup.html', {
                            'errors': {'general': f"Erreur lors de la création du restaurant: {str(e)}"}, 
                            'cities': City.objects.all(),
                            'form_data': data
                        })
            
            # Connecter l'utilisateur
            login(request, user)
            
            # Répondre en fonction du type de requête
            if is_ajax:
                return JsonResponse({'success': True, 'account_type': account_type}, status=201)
            else:
                messages.success(request, f"Votre compte a été créé avec succès! Vous êtes maintenant connecté.")
                if account_type == 'restaurant':
                    return redirect('restaurant_dashboard')
                else:
                    return redirect('accueil')
                
        except Exception as e:
            if is_ajax:
                return JsonResponse({'errors': {'general': str(e)}}, status=400)
            else:
                return render(request, 'foodapp/signup.html', {
                    'errors': {'general': str(e)}, 
                    'cities': City.objects.all(),
                    'form_data': data
                })
    else:
        # Assurer que le token CSRF est généré
        csrf_token = get_token(request)
        # Passer la liste des villes pour le formulaire restaurant
        cities = City.objects.all()
        return render(request, 'foodapp/signup.html', {'cities': cities})

@login_required
def dashboard(request):
    # Statistics
    restaurants_count = Restaurant.objects.count()
    active_restaurants_count = Restaurant.objects.filter(is_open=True).count()
    dishes_count = Dish.objects.count()
    vegetarian_dishes_count = Dish.objects.filter(is_vegetarian=True).count()
    cities_count = City.objects.count()
    users_count = User.objects.count()
    staff_count = User.objects.filter(is_staff=True).count()
    
    # Dish type counts
    sweet_dishes_count = Dish.objects.filter(type='sweet').count()
    salty_dishes_count = Dish.objects.filter(type='salty').count()
    drink_dishes_count = Dish.objects.filter(type='drink').count()
    
    # Latest data
    latest_restaurants = Restaurant.objects.all().order_by('-created_at')[:5]
    latest_dishes = Dish.objects.all().order_by('-id')[:5]
    
    # All cities for charts
    cities = City.objects.all()
    
    context = {
        'restaurants_count': restaurants_count,
        'active_restaurants_count': active_restaurants_count,
        'dishes_count': dishes_count,
        'vegetarian_dishes_count': vegetarian_dishes_count,
        'cities_count': cities_count,
        'users_count': users_count,
        'staff_count': staff_count,
        'sweet_dishes_count': sweet_dishes_count,
        'salty_dishes_count': salty_dishes_count,
        'drink_dishes_count': drink_dishes_count,
        'latest_restaurants': latest_restaurants,
        'latest_dishes': latest_dishes,
        'cities': cities,
    }
    
    return render(request, 'foodapp/dashboard.html', context)

@csrf_exempt
def restaurant_signup_view(request):
    """Vue spécifique pour l'inscription des restaurants (optimisée)"""
    if request.method == 'POST':
        try:
            # Utilisation de transaction atomique pour améliorer les performances
            from django.db import transaction
            
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            
            # Vérifications rapides en une seule requête pour améliorer les performances
            username_exists = User.objects.filter(username=username).exists()
            if username_exists:
                return JsonResponse({'errors': {'username': "Ce nom d'utilisateur est déjà pris"}}, status=400)
            
            email_exists = User.objects.filter(email=email).exists()
            if email_exists:
                return JsonResponse({'errors': {'email': "Cette adresse email est déjà utilisée"}}, status=400)
            
            # Récupérer les données essentielles du restaurant
                restaurant_name = data.get('restaurant_name')
                restaurant_city_id = data.get('restaurant_city')
                restaurant_phone = data.get('restaurant_phone')
                restaurant_address = data.get('restaurant_address')
                
            # Validation minimale (uniquement champs critiques)
                if not restaurant_name or not restaurant_city_id or not restaurant_phone or not restaurant_address:
                    return JsonResponse({'errors': {'general': "Informations du restaurant incomplètes"}}, status=400)
            
            # Utilisation d'une transaction atomique pour garantir la cohérence des données
            with transaction.atomic():
                # Créer un utilisateur et son profil en une seule transaction
                user = User.objects.create_user(username=username, email=email, password=password)
                UserProfile.objects.create(user=user)
                
                try:
                    city = City.objects.get(id=restaurant_city_id)
                    
                    # Créer restaurant avec données minimales nécessaires
                    restaurant = Restaurant.objects.create(
                        name=restaurant_name,
                        city=city,
                        address=restaurant_address,
                        phone=restaurant_phone,
                        email=email,
                        is_open=False,  # Le restaurant est fermé jusqu'à l'approbation
                        description=data.get('restaurant_description', ''),
                        website=data.get('restaurant_website', '')
                    )
                    
                    # Créer compte restaurant (inactif par défaut)
                    RestaurantAccount.objects.create(
                        user=user,
                        restaurant=restaurant,
                        is_active=False,
                        pending_approval=True
                    )
                    
                    # Envoyer un email aux administrateurs
                    admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
                    if admin_emails:
                        send_mail(
                            'Nouvelle demande de compte restaurant',
                            f'Un nouveau restaurant "{restaurant_name}" attend votre approbation.',
                            'noreply@foodflex.com',
                            list(admin_emails),
                            fail_silently=True,
                        )
                    
                    # Envoyer un email de confirmation au restaurant
                    send_mail(
                        'Demande de compte restaurant reçue',
                        f'Votre demande pour "{restaurant_name}" a été reçue et est en cours d\'examen. '
                        f'Nous vous contacterons dès que votre compte sera approuvé.',
                        'noreply@foodflex.com',
                        [email],
                        fail_silently=True,
                    )
                    
                except City.DoesNotExist:
                    return JsonResponse({'errors': {'restaurant_city': "Ville non trouvée"}}, status=400)
            
            # Ne pas connecter l'utilisateur, rediriger vers la page d'attente
            return JsonResponse({
                'success': True, 
                'message': 'Votre demande a été reçue et est en cours d\'examen.',
                'redirect': 'pending_approval'
            }, status=201)
            
        except Exception as e:
            return JsonResponse({'errors': {'general': str(e)}}, status=400)
    else:
        # Assurer que le token CSRF est généré et rendu plus rapidement
        csrf_token = get_token(request)
        # Récupérer uniquement les IDs et noms des villes pour optimiser la requête
        cities = City.objects.all().only('id', 'name')
        return render(request, 'foodapp/restaurant_signup.html', {'cities': cities})

def get_restaurants(request):
    """
    Vue API pour renvoyer les restaurants avec mise en cache
    """
    # Vérifier si les données sont en cache
    cache_key = 'all_restaurants_data'
    restaurants_data = cache.get(cache_key)
    
    if not restaurants_data:
        # Si pas en cache, récupérer depuis la base de données
        start_time = time.time()
        restaurants = Restaurant.objects.select_related('city').all()
        
        # Préparer les données pour la sérialisation JSON
        restaurants_data = []
        for restaurant in restaurants:
            restaurants_data.append({
                'id': restaurant.id,
                'name': restaurant.name,
                'description': restaurant.description,
                'is_open': restaurant.is_open,
                'address': restaurant.address,
                'phone': restaurant.phone,
                'email': restaurant.email,
                'website': restaurant.website,
                'image': restaurant.image.url if restaurant.image else '',
                'city': {
                    'id': restaurant.city.id,
                    'name': restaurant.city.name
                },
                'timestamp': timezone.now().timestamp()
            })
        
        # Mettre en cache pour 10 minutes
        cache.set(cache_key, restaurants_data, 60 * 10)
        
        print(f"Restaurant query completed in {time.time() - start_time:.4f} seconds")
    
    return JsonResponse(restaurants_data, safe=False)

@csrf_exempt
@require_POST
def mark_dish_viewed(request, dish_id):
    """
    Marque un plat comme vu par l'utilisateur actuel
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Utilisateur non authentifié'}, status=401)
    
    try:
        dish = Dish.objects.get(id=dish_id)
        dish.mark_as_viewed(request.user)
        return JsonResponse({'status': 'success', 'message': 'Plat marqué comme vu'})
    except Dish.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Plat non trouvé'}, status=404)

def moroccan_cuisine(request):
    """
    Vue spéciale pour montrer les plats marocains aux touristes
    """
    # Récupérer uniquement les plats marocains créés depuis l'interface d'administration Django
    
    # Récupérer les plats marocains recommandés aux touristes
    recommended_dishes = Dish.objects.filter(
        origin=Dish.MOROCCAN, 
        is_tourist_recommended=True,
        is_admin_created=True  # Uniquement les plats créés via le panneau d'administration
    )
    
    # Tous les plats marocains créés par des administrateurs
    all_moroccan_dishes = Dish.objects.filter(
        origin=Dish.MOROCCAN,
        is_admin_created=True  # Uniquement les plats créés via le panneau d'administration
    )
    
    # Répartir les plats par type
    sweet_dishes = all_moroccan_dishes.filter(type=Dish.SWEET)
    salty_dishes = all_moroccan_dishes.filter(type=Dish.SALTY)
    drinks = all_moroccan_dishes.filter(type=Dish.DRINK)
    
    # Marquer les plats comme nouveaux pour cet utilisateur
    if request.user.is_authenticated:
        for dish in list(recommended_dishes) + list(sweet_dishes) + list(salty_dishes) + list(drinks):
            dish.is_new_for_current_user = dish.is_new_for_user(request.user)
    else:
        for dish in list(recommended_dishes) + list(sweet_dishes) + list(salty_dishes) + list(drinks):
            dish.is_new_for_current_user = dish.is_new()
    
    context = {
        'recommended_dishes': recommended_dishes,
        'sweet_dishes': sweet_dishes,
        'salty_dishes': salty_dishes,
        'drinks': drinks,
        'total_dishes': all_moroccan_dishes.count(),
    }
    
    return render(request, 'foodapp/moroccan_cuisine.html', context)

@login_required
@csrf_exempt
def update_reservation_status(request, reservation_id):
    """API pour mettre à jour le statut d'une réservation depuis le tableau de bord restaurant"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    # Vérifier que l'utilisateur est bien un compte restaurant
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    except:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    # Récupérer la réservation
    try:
        reservation = Reservation.objects.get(id=reservation_id, restaurant=restaurant_account.restaurant)
    except Reservation.DoesNotExist:
        return JsonResponse({'error': 'Réservation non trouvée'}, status=404)
    
    # Mettre à jour le statut
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status in [s[0] for s in Reservation.STATUS_CHOICES]:
            reservation.status = new_status
            reservation.save()
            return JsonResponse({
                'success': True, 
                'reservation_id': reservation.id,
                'status': reservation.status,
                'status_display': reservation.get_status_display()
            })
        else:
            return JsonResponse({'error': 'Statut invalide'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def user_profile(request):
    """Vue pour afficher et éditer le profil utilisateur"""
    
    # Récupérer ou créer le profil de l'utilisateur
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Récupérer les réservations de l'utilisateur
    user_reservations = Reservation.objects.filter(user=request.user).order_by('-date')
    
    # Traiter le formulaire de mise à jour du profil
    if request.method == 'POST':
        # Mise à jour des informations du profil
        user_profile.bio = request.POST.get('bio', '')
        user_profile.phone = request.POST.get('phone', '')
        user_profile.favorite_cuisine = request.POST.get('favorite_cuisine', '')
        user_profile.is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        user_profile.is_vegan = request.POST.get('is_vegan') == 'on'
        
        # Traiter l'image de profil
        if 'profile_image' in request.FILES:
            user_profile.profile_image = request.FILES['profile_image']
        
        # Enregistrer les modifications
        user_profile.save()
        
        # Rediriger pour éviter les soumissions multiples
        return redirect('user_profile')
    
    # Récupérer quelques plats recommandés
    if user_profile.is_vegan:
        recommended_dishes = Dish.objects.filter(is_vegan=True)[:3]
    elif user_profile.is_vegetarian:
        recommended_dishes = Dish.objects.filter(is_vegetarian=True)[:3]
    else:
        recommended_dishes = Dish.objects.all().order_by('?')[:3]
    
    context = {
        'user_profile': user_profile,
        'user_reservations': user_reservations,
        'recommended_dishes': recommended_dishes,
        'cities': City.objects.all(),
    }
    
    return render(request, 'foodapp/user_profile.html', context)

@login_required
def user_reservations_list(request):
    """Vue pour afficher toutes les réservations d'un utilisateur"""
    
    # Récupérer les réservations de l'utilisateur
    reservations = Reservation.objects.filter(user=request.user).order_by('-date', '-time')
    
    # Filtrer par statut si demandé
    status_filter = request.GET.get('status')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    context = {
        'reservations': reservations,
        'status_filter': status_filter,
        'STATUS_CHOICES': Reservation.STATUS_CHOICES
    }
    
    return render(request, 'foodapp/user_reservations_list.html', context)

@login_required
def reservation_detail(request, reservation_id):
    """Vue pour afficher les détails d'une réservation"""
    
    # Récupérer la réservation
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que l'utilisateur a le droit de voir cette réservation
    if reservation.user != request.user:
        # Vérifier si c'est un restaurateur qui gère ce restaurant
        try:
            restaurant_account = request.user.restaurant_account
            if restaurant_account.restaurant != reservation.restaurant:
                return HttpResponseForbidden("Vous n'êtes pas autorisé à voir cette réservation.")
        except:
            return HttpResponseForbidden("Vous n'êtes pas autorisé à voir cette réservation.")
    
    context = {
        'reservation': reservation,
        'restaurant': reservation.restaurant
    }
    
    return render(request, 'foodapp/reservation_detail.html', context)

@login_required
def available_slots(request, restaurant_id):
    """API pour récupérer les créneaux horaires disponibles pour un restaurant"""
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Date non spécifiée'}, status=400)
    
    try:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Format de date invalide'}, status=400)
    
    # Heures d'ouverture du restaurant (exemple)
    opening_hours = [
        {'start': '12:00', 'end': '14:30'},  # Déjeuner
        {'start': '19:00', 'end': '22:30'}   # Dîner
    ]
    
    # Créneaux de 30 minutes
    time_slots = []
    for period in opening_hours:
        start_time = datetime.datetime.strptime(period['start'], '%H:%M').time()
        end_time = datetime.datetime.strptime(period['end'], '%H:%M').time()
        
        current_time = start_time
        while current_time < end_time:
            # Vérifier si ce créneau est disponible
            is_available = is_slot_available(restaurant, date, current_time, 1)  # 1 = minimum de convives
            
            time_slots.append({
                'time': current_time.strftime('%H:%M'),
                'available': is_available
            })
            
            # Passer au prochain créneau de 30 minutes
            current_datetime = datetime.datetime.combine(date, current_time)
            current_datetime += datetime.timedelta(minutes=30)
            current_time = current_datetime.time()
    
    return JsonResponse({'slots': time_slots})

@login_required
def user_settings(request):
    """
    Vue pour afficher et gérer les paramètres utilisateur
    """
    # Récupérer le profil de l'utilisateur
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Paramètres généraux
        theme = request.POST.get('theme', 'dark')
        notifications_enabled = request.POST.get('notifications_enabled') == 'on'
        language = request.POST.get('language', 'fr')
        
        # Nouveaux paramètres ajoutés
        email_notifications = request.POST.get('email_notifications') == 'on'
        show_recommendations = request.POST.get('show_recommendations') == 'on'
        date_format = request.POST.get('date_format', 'DD/MM/YYYY')
        currency = request.POST.get('currency', 'EUR')
        has_allergies = request.POST.get('has_allergies') == 'on'
        
        # Mettre à jour les préférences
        preferences = profile.preferences or {}
        preferences.update({
            'theme': theme,
            'notifications_enabled': notifications_enabled,
            'language': language,
            'email_notifications': email_notifications,
            'show_recommendations': show_recommendations,
            'date_format': date_format,
            'currency': currency,
            'has_allergies': has_allergies
        })
        
        # Mettre à jour les préférences alimentaires directement dans le profil
        profile.is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        profile.is_vegan = request.POST.get('is_vegan') == 'on'
        
        # Sauvegarder les modifications
        profile.preferences = preferences
        profile.save()
        
        messages.success(request, 'Vos paramètres ont été mis à jour avec succès.')
        return redirect('user_settings')
    
    # Préparer les préférences par défaut si elles n'existent pas
    if not profile.preferences:
        profile.preferences = {
            'theme': 'dark',
            'notifications_enabled': True,
            'language': 'fr',
            'email_notifications': True,
            'show_recommendations': True,
            'date_format': 'DD/MM/YYYY',
            'currency': 'EUR',
            'has_allergies': False
        }
        profile.save()
    
    context = {
        'profile': profile,
        'preferences': profile.preferences
    }
    
    return render(request, 'foodapp/user_settings.html', context)

@login_required
def reservation_modify(request, reservation_id):
    """Vue pour modifier une réservation"""
    
    # Récupérer la réservation
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que l'utilisateur a le droit de modifier cette réservation
    if reservation.user != request.user:
        return HttpResponseForbidden("Vous n'êtes pas autorisé à modifier cette réservation.")
    
    # Vérifier que la réservation n'est pas déjà annulée ou terminée
    if reservation.status in [Reservation.STATUS_CANCELED, Reservation.STATUS_COMPLETED]:
        return redirect('reservation_detail', reservation_id=reservation_id)
    
    # Date limite pour les modifications (24h avant la réservation)
    modification_limit = datetime.datetime.combine(
        reservation.date, 
        reservation.time
    ).replace(tzinfo=timezone.get_current_timezone()) - datetime.timedelta(hours=24)
    
    can_modify = timezone.now() < modification_limit
    
    if request.method == 'POST' and can_modify:
        form = ReservationModifyForm(request.POST, instance=reservation)
        if form.is_valid():
            # Vérifier la disponibilité
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            guests = form.cleaned_data['guests']
            
            # Vérifier si le créneau est disponible (en excluant la réservation actuelle)
            if is_slot_available(reservation.restaurant, date, time, guests, exclude_reservation_id=reservation_id):
                form.save()
                return redirect('reservation_detail', reservation_id=reservation_id)
            else:
                form.add_error(None, "Désolé, ce créneau n'est plus disponible. Veuillez choisir un autre horaire.")
    else:
        form = ReservationModifyForm(instance=reservation)
    
    # Récupérer les créneaux disponibles pour JavaScript
    available_dates = get_available_dates(reservation.restaurant)
    
    context = {
        'form': form,
        'reservation': reservation,
        'restaurant': reservation.restaurant,
        'can_modify': can_modify,
        'modification_limit': modification_limit,
        'available_dates': json.dumps([date.strftime('%Y-%m-%d') for date in available_dates])
    }
    
    return render(request, 'foodapp/reservation_modify.html', context)

@login_required
def reservation_cancel(request, reservation_id):
    """Vue pour annuler une réservation"""
    
    # Récupérer la réservation
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier que l'utilisateur a le droit d'annuler cette réservation
    if reservation.user != request.user:
        return HttpResponseForbidden("Vous n'êtes pas autorisé à annuler cette réservation.")
    
    # Vérifier que la réservation n'est pas déjà annulée ou terminée
    if reservation.status in [Reservation.STATUS_CANCELED, Reservation.STATUS_COMPLETED]:
        return redirect('reservation_detail', reservation_id=reservation_id)
    
    if request.method == 'POST':
        # Annuler la réservation
        reservation.status = Reservation.STATUS_CANCELED
        reservation.save()
        return redirect('user_reservations_list')
    
    context = {
        'reservation': reservation,
        'restaurant': reservation.restaurant
    }
    
    return render(request, 'foodapp/reservation_cancel.html', context)

@csrf_exempt
def check_username(request):
    """API pour vérifier si un nom d'utilisateur est disponible"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '')
            
            if not username:
                return JsonResponse({'available': False, 'message': 'Nom d\'utilisateur requis'})
            
            # Vérifier la longueur
            if len(username) < 4:
                return JsonResponse({'available': False, 'message': 'Le nom d\'utilisateur doit contenir au moins 4 caractères'})
            
            # Vérifier s'il existe déjà
            exists = User.objects.filter(username=username).exists()
            
            if exists:
                return JsonResponse({'available': False, 'message': 'Ce nom d\'utilisateur est déjà utilisé'})
            else:
                return JsonResponse({'available': True, 'message': 'Nom d\'utilisateur disponible'})
                
        except Exception as e:
            return JsonResponse({'available': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'available': False, 'message': 'Méthode non autorisée'}, status=405)

def search(request):
    """Vue pour la recherche globale"""
    query = request.GET.get('q', '')
    
    dishes = []
    restaurants = []
    
    if query:
        # Recherche dans les plats
        dishes = Dish.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(ingredients__icontains=query)
        )
        
        # Recherche dans les restaurants
        restaurants = Restaurant.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(city__name__icontains=query)
        )
    
    context = {
        'query': query,
        'dishes': dishes,
        'restaurants': restaurants,
        'total_results': len(dishes) + len(restaurants)
    }
    
    return render(request, 'foodapp/search_results.html', context)

def restaurant_pricing_plans(request):
    """Vue pour afficher les plans d'abonnement restaurant"""
    
    # Récupérer tous les plans restaurant actifs
    plans = SubscriptionPlan.objects.filter(plan_type='restaurant', is_active=True)
    
    # Si l'utilisateur est connecté et a un compte restaurant
    current_plan = None
    has_restaurant = False
    restaurant_account = None
    
    if request.user.is_authenticated:
        try:
            restaurant_account = request.user.restaurant_account
            has_restaurant = True
            
            # Récupérer l'abonnement actuel s'il existe
            try:
                subscription = RestaurantSubscription.objects.get(restaurant_account=restaurant_account)
                current_plan = subscription.plan
            except RestaurantSubscription.DoesNotExist:
                pass
        except:
            pass
    
    context = {
        'plans': plans,
        'current_plan': current_plan,
        'has_restaurant': has_restaurant,
        'restaurant_account': restaurant_account,
    }
    
    return render(request, 'foodapp/subscription/restaurant_plans.html', context)

def user_pricing_plans(request):
    """Vue pour afficher les plans d'abonnement utilisateur"""
    
    # Récupérer tous les plans utilisateur actifs
    plans = SubscriptionPlan.objects.filter(plan_type='user', is_active=True)
    
    # Si l'utilisateur est connecté
    current_plan = None
    user_profile = None
    
    if request.user.is_authenticated:
        try:
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Récupérer l'abonnement actuel s'il existe
            try:
                subscription = UserSubscription.objects.get(user_profile=user_profile)
                current_plan = subscription.plan
            except UserSubscription.DoesNotExist:
                pass
        except:
            pass
    
    context = {
        'plans': plans,
        'current_plan': current_plan,
        'user_profile': user_profile,
    }
    
    return render(request, 'foodapp/subscription/user_plans.html', context)

@login_required
def subscription_checkout(request, plan_type, plan_id):
    """Vue pour s'abonner à un plan"""
    from datetime import timedelta
    
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    # Vérifier que le type de plan correspond au bon utilisateur
    if plan_type == 'restaurant':
        if not hasattr(request.user, 'restaurant_account'):
            messages.error(request, "Vous devez avoir un compte restaurant pour souscrire à ce plan.")
            return redirect('restaurant_pricing_plans')
    
    # Récupérer les paramètres
    billing_cycle = request.GET.get('billing', 'monthly')
    is_yearly = billing_cycle == 'yearly'
    
    if request.method == 'POST':
        # Simule un paiement réussi
        payment_successful = True
        
        if payment_successful:
            # Calculer la date de fin de l'abonnement
            if is_yearly:
                end_date = timezone.now().date() + timedelta(days=365)
                price = plan.price_yearly
            else:
                end_date = timezone.now().date() + timedelta(days=30)
                price = plan.price_monthly
            
            # Créer ou mettre à jour l'abonnement
            if plan_type == 'restaurant':
                restaurant_account = request.user.restaurant_account
                
                # Vérifier si un abonnement existe déjà
                subscription, created = RestaurantSubscription.objects.get_or_create(
                    restaurant_account=restaurant_account,
                    defaults={
                        'plan': plan,
                        'end_date': end_date,
                        'status': 'active',
                        'notes': f"Abonnement {'annuel' if is_yearly else 'mensuel'} - Prix: {price} €"
                    }
                )
                
                if not created:
                    subscription.plan = plan
                    subscription.end_date = end_date
                    subscription.status = 'active'
                    subscription.notes = f"Abonnement {'annuel' if is_yearly else 'mensuel'} - Prix: {price} €"
                    subscription.save()
                
                messages.success(request, f"Vous êtes maintenant abonné au plan {plan.name}!")
                return redirect('restaurant_dashboard')
                
            else:  # plan_type == 'user'
                user_profile, created = UserProfile.objects.get_or_create(user=request.user)
                
                # Vérifier si un abonnement existe déjà
                subscription, created = UserSubscription.objects.get_or_create(
                    user_profile=user_profile,
                    defaults={
                        'plan': plan,
                        'end_date': end_date,
                        'status': 'active',
                    }
                )
                
                if not created:
                    subscription.plan = plan
                    subscription.end_date = end_date
                    subscription.status = 'active'
                    subscription.save()
                
                messages.success(request, f"Vous êtes maintenant abonné au plan {plan.name}!")
                return redirect('user_profile')
    
    context = {
        'plan': plan,
        'plan_type': plan_type,
        'is_yearly': is_yearly,
        'price': plan.price_yearly if is_yearly else plan.price_monthly,
    }
    
    return render(request, 'foodapp/subscription/checkout.html', context)

@login_required
def restaurant_menu_create(request):
    """Vue pour créer un nouveau plat pour le menu du restaurant"""
    
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('accueil')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    if request.method == 'POST':
        # Traiter les données du formulaire
        name = request.POST.get('name')
        description = request.POST.get('description')
        price_range = request.POST.get('price_range')
        type_plat = request.POST.get('type')
        is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        is_vegan = request.POST.get('is_vegan') == 'on'
        
        # Créer un nouveau plat
        new_dish = Dish(
            name=name,
            description=description,
            price_range=price_range,
            type=type_plat,
            is_vegetarian=is_vegetarian,
            is_vegan=is_vegan,
            city=restaurant.city
        )
        
        # Enregistrer l'image si fournie
        if 'image' in request.FILES:
            new_dish.image = request.FILES['image']
        
        new_dish.save()
        
        messages.success(request, f"Le plat '{name}' a été ajouté avec succès à votre menu!")
        return redirect('restaurant_menu')
    
    # Contexte pour le template
    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
    }
    
    return render(request, 'foodapp/restaurant_menu_create.html', context)

@login_required
@csrf_exempt
def create_order(request):
    """Vue pour créer une nouvelle commande"""
    
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('accueil')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    if request.method == 'POST':
        # Traiter les données du formulaire
        customer_name = request.POST.get('customer_name')
        is_takeaway = request.POST.get('is_takeaway') == 'on'
        table_number = request.POST.get('table_number', '')
        special_instructions = request.POST.get('special_instructions', '')
        payment_method = request.POST.get('payment_method', 'cash')
        total_amount = request.POST.get('total_amount', '0.00')
        
        # Créer une nouvelle commande
        order = Order.objects.create(
            restaurant=restaurant,
            customer_name=customer_name,
            is_takeaway=is_takeaway,
            table_number=table_number,
            special_instructions=special_instructions,
            payment_method=payment_method,
            total_amount=Decimal(total_amount.replace(',', '.'))
        )
        
        # Traiter les articles de la commande
        item_count = int(request.POST.get('item_count', 0))
        for i in range(1, item_count + 1):
            dish_id = request.POST.get(f'dish_{i}')
            quantity = request.POST.get(f'quantity_{i}', 1)
            notes = request.POST.get(f'notes_{i}', '')
            
            if dish_id:
                try:
                    dish = Dish.objects.get(id=dish_id)
                    OrderItem.objects.create(
                        order=order,
                        dish=dish,
                        quantity=quantity,
                        notes=notes
                    )
                except Dish.DoesNotExist:
                    pass
        
        messages.success(request, f"Commande #{order.id} créée avec succès!")
        return redirect('restaurant_orders')
    
    # Si la méthode n'est pas POST, rediriger vers la page des commandes
    return redirect('restaurant_orders')

@login_required
def restaurant_orders_live(request):
    """Vue pour la gestion des commandes en temps réel avec un style différent"""
    
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('accueil')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    # Récupérer les commandes de ce restaurant
    orders = Order.objects.filter(restaurant=restaurant).order_by('-order_time')
    
    # Commandes par statut
    new_orders = orders.filter(status=Order.STATUS_NEW)
    preparing_orders = orders.filter(status=Order.STATUS_PREPARING)
    ready_orders = orders.filter(status=Order.STATUS_READY)
    
    # Commandes à emporter
    takeaway_orders = orders.filter(is_takeaway=True, status__in=[Order.STATUS_NEW, Order.STATUS_PREPARING, Order.STATUS_READY])
    
    # Statistiques
    today = timezone.now().date()
    today_orders = orders.filter(order_time__date=today)
    today_orders_count = today_orders.count()
    in_progress_count = new_orders.count() + preparing_orders.count()
    ready_count = ready_orders.count()
    new_count = new_orders.count()
    preparing_count = preparing_orders.count()
    takeaway_count = takeaway_orders.count()
    
    # Chiffre d'affaires du jour
    today_revenue = today_orders.filter(status__in=[Order.STATUS_DELIVERED, Order.STATUS_PAID]).aggregate(
        total=Sum('total_amount'))['total'] or 0
    
    # Récupérer les plats disponibles pour le restaurant (pour le formulaire de création de commande)
    dishes = Dish.objects.filter(city=restaurant.city)
    
    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'orders': orders,
        'new_orders': new_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'takeaway_orders': takeaway_orders,
        'today_orders_count': today_orders_count,
        'in_progress_count': in_progress_count,
        'ready_count': ready_count,
        'new_count': new_count,
        'preparing_count': preparing_count,
        'takeaway_count': takeaway_count,
        'today_revenue': today_revenue,
        'dishes': dishes,
    }
    
    return render(request, 'foodapp/restaurant_orders_live.html', context)

def privacy_policy(request):
    """Vue pour afficher la politique de confidentialité"""
    return render(request, 'foodapp/privacy_policy.html')

def terms_of_service(request):
    """Vue pour afficher les conditions d'utilisation"""
    return render(request, 'foodapp/terms_of_service.html') 

def register_restaurant(request):
    """Vue pour l'inscription d'un nouveau restaurant"""
    if request.method == 'POST':
        try:
            # Créer un brouillon de restaurant
            restaurant_draft = RestaurantDraft(
                # Informations du restaurant
                name=request.POST['name'],
                city=City.objects.get(id=request.POST['city']),
                address=request.POST['address'],
                phone=request.POST['phone'],
                email=request.POST['email'],
                website=request.POST.get('website', ''),
                description=request.POST['description'],
                capacity=request.POST['capacity'],
                
                # Informations du propriétaire
                owner_first_name=request.POST['owner_first_name'],
                owner_last_name=request.POST['owner_last_name'],
                owner_email=request.POST['owner_email'],
                owner_phone=request.POST['owner_phone'],
                
                # Documents
                owner_id_card=request.FILES['owner_id_card'],
                business_registration=request.FILES['business_registration'],
                food_safety_certificate=request.FILES['food_safety_certificate'],
                
                # Photos
                main_image=request.FILES['main_image'],
                interior_image1=request.FILES['interior_image1'],
                menu_sample=request.FILES['menu_sample']
            )
            
            # Documents optionnels
            if 'tax_document' in request.FILES:
                restaurant_draft.tax_document = request.FILES['tax_document']
            if 'interior_image2' in request.FILES:
                restaurant_draft.interior_image2 = request.FILES['interior_image2']
            
            restaurant_draft.save()
            
            messages.success(
                request,
                'Votre demande a été soumise avec succès ! Nous l\'examinerons dans les plus brefs délais. '
                'Vous recevrez un email dès que votre compte sera approuvé.'
            )
            return redirect('accueil')
            
        except Exception as e:
            messages.error(
                request,
                'Une erreur est survenue lors de la soumission de votre demande. '
                'Veuillez vérifier vos informations et réessayer.'
            )
            return redirect('register_restaurant')
    
    # GET request
    context = {
        'cities': City.objects.all().order_by('name')
    }
    return render(request, 'foodapp/restaurant_registration.html', context)

def restaurant_pending_approval(request):
    """Vue pour la page d'attente d'approbation du restaurant"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.pending_approval:
            # Si le compte n'est plus en attente, rediriger vers le dashboard
            return redirect('restaurant_dashboard')
            
        context = {
            'restaurant': restaurant_account.restaurant,
            'account': restaurant_account,
            'created_at': restaurant_account.created_at
        }
        return render(request, 'foodapp/restaurant_pending_approval.html', context)
        
    except:
        # Si l'utilisateur n'a pas de compte restaurant
        return redirect('accueil')

def restaurant_registration_confirmation(request):
    """Vue pour la page de confirmation d'inscription restaurant"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        restaurant_account = request.user.restaurant_account
        context = {
            'restaurant': restaurant_account.restaurant
        }
        return render(request, 'foodapp/restaurant_registration_confirmation.html', context)
        
    except:
        # Si l'utilisateur n'a pas de compte restaurant
        return redirect('accueil')

class RestaurantRegistrationWizard(SessionWizardView):
    FORMS = [
        ("basic_info", RestaurantBasicInfoForm),
        ("owner_info", RestaurantOwnerInfoForm),
        ("legal_docs", RestaurantLegalDocsForm),
        ("photos", RestaurantPhotosForm),
    ]
    
    # Configuration des fichiers
    allowed_extensions = {
        'owner_id_card': ['.jpg', '.jpeg', '.png', '.pdf'],
        'business_registration': ['.pdf'],
        'food_safety_certificate': ['.pdf'],
        'tax_document': ['.pdf'],
        'main_image': ['.jpg', '.jpeg', '.png'],
        'interior_image1': ['.jpg', '.jpeg', '.png'],
        'interior_image2': ['.jpg', '.jpeg', '.png'],
        'menu_sample': ['.pdf', '.jpg', '.jpeg', '.png'],
    }

    # Optimisation des fichiers
    file_storage = FileSystemStorage(
        location=os.path.join(settings.MEDIA_ROOT, 'temp_uploads'),
        # Optimisation: permettre l'accès en lecture seule pour éviter de copier les fichiers
        file_permissions_mode=0o644,
        # Optimisation: désactiver le nettoyage automatique des fichiers
        # car nous le ferons nous-mêmes
        base_url=settings.MEDIA_URL + 'temp_uploads/'
    )
    
    def get_template_names(self):
        return ["foodapp/restaurant_registration.html"]
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context.update({
            'step_titles': [
                'Informations de base',
                'Informations du propriétaire',
                'Documents légaux',
                'Photos et menu'
            ]
        })
        
        # Taille maximale de fichier (5MB)
        max_file_size = 5 * 1024 * 1024
        
        # Convert to JSON string with proper escaping
        context['allowed_extensions_json'] = json.dumps(self.allowed_extensions)
        # Keep the dictionary for template use
        context['allowed_extensions'] = self.allowed_extensions
        context['max_file_size'] = max_file_size
        
        return context
    
    def done(self, form_list, **kwargs):
        """Traitment final des données du formulaire multi-étape"""
        # Combine all form data
        restaurant_data = {}
        for form in form_list:
            restaurant_data.update(form.cleaned_data)
        
        try:
            # Ajout de logs pour debug
            print("Début de création du compte restaurant...")
            
            # Optimisation: Utiliser ATOMIC_REQUESTS pour une transaction plus rapide
            # Créer d'abord le brouillon du restaurant
            restaurant_draft = RestaurantDraft.objects.create(**restaurant_data)
            print(f"Brouillon de restaurant créé avec ID: {restaurant_draft.id}")
            
            # Création du compte utilisateur optimisée
            username = f"resto_{restaurant_draft.name.lower().replace(' ', '_')}"[:30]  # Limiter la longueur
            password = get_random_string(12)  # Generate a random password
            
            # Check if username exists, make it unique if needed
            if User.objects.filter(username=username).exists():
                username = f"{username[:25]}_{get_random_string(4)}"
            
            # Create user - optimisé
            user = User.objects.create_user(
                username=username,
                email=restaurant_draft.owner_email,
                password=password,
                first_name=restaurant_draft.owner_first_name,
                last_name=restaurant_draft.owner_last_name
            )
            print(f"Utilisateur créé avec ID: {user.id}")
            
            # Create user profile
            UserProfile.objects.create(
                user=user,
                phone=restaurant_draft.owner_phone
            )
            
            # 3. Create Restaurant (inactive by default) - optimisé
            restaurant = Restaurant.objects.create(
                name=restaurant_draft.name,
                city=restaurant_draft.city,
                address=restaurant_draft.address,
                phone=restaurant_draft.phone,
                email=restaurant_draft.email,
                website=restaurant_draft.website or '',
                description=restaurant_draft.description,
                is_open=False,  # Restaurant is closed until approved
                capacity=restaurant_draft.capacity,
                image=restaurant_draft.main_image  # Main image becomes restaurant image
            )
            print(f"Restaurant créé avec ID: {restaurant.id}")
            
            # 4. Create restaurant account (pending approval)
            restaurant_account = RestaurantAccount.objects.create(
                user=user,
                restaurant=restaurant,
                is_active=False,
                pending_approval=True
            )
            
            # 5. Send notification emails - optimisé (asynchrone si possible)
            # Nous allons reporter l'envoi d'emails qui est lent
            # Lancer l'envoi des emails dans un thread séparé pour ne pas bloquer la réponse
            email_thread = threading.Thread(
                target=send_restaurant_registration_emails,
                args=(restaurant.id, restaurant_draft.owner_email, restaurant_draft.owner_first_name, username, password)
            )
            email_thread.daemon = True  # Le thread se terminera automatiquement à la fin du programme
            email_thread.start()
            
            # 6. Log in the user automatically
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(self.request, user)
            print("Utilisateur connecté")
            
            # Mettre un message de succès et rediriger
            messages.success(
                self.request,
                'Votre demande a été soumise avec succès ! Nous l\'examinerons dans les plus brefs délais.'
            )
            
            # 7. Redirect to confirmation page
            print("Redirection vers la page de confirmation")
            return redirect('restaurant_pending_approval')
                
        except Exception as e:
            # Log the error
            print(f"Erreur lors de l'inscription: {str(e)}")
            # Redirect to an error page or back to the first step
            messages.error(self.request, f"Une erreur est survenue lors de l'inscription: {str(e)}")
            return redirect('restaurant_register')

    def process_step(self, form):
        """Traite chaque étape du formulaire"""
        cleaned_data = super().process_step(form)
        
        # Optimisation: Utiliser un cache pour stocker les résultats des validations
        cache_key = f"restaurant_reg_{self.request.session.session_key}_{self.steps.current}"
        cached_data = cache.get(cache_key)
        if cached_data:
            print(f"Utilisation du cache pour l'étape {self.steps.current}")
            return cached_data
        
        # Ajouter des logs pour suivre le temps de traitement
        start_time = time.time()
        
        # Valider les fichiers si présents
        for field_name, field_value in cleaned_data.items():
            if isinstance(field_value, bool) or not field_value:
                continue
                
            if field_name in self.allowed_extensions and hasattr(field_value, 'size'):
                # Optimisation: Ne pas retraiter les fichiers déjà validés
                if hasattr(field_value, '_validated') and field_value._validated:
                    continue
                    
                try:
                    # Vérifier la taille du fichier
                    if field_value.size > 5 * 1024 * 1024:  # 5MB
                        form.add_error(field_name, "Le fichier est trop volumineux (max 5MB)")
                        raise forms.ValidationError("Le fichier est trop volumineux")
                    
                    # Vérifier l'extension
                    ext = os.path.splitext(field_value.name)[1].lower()
                    if ext not in self.allowed_extensions.get(field_name, []):
                        form.add_error(field_name, "Type de fichier non autorisé")
                        raise forms.ValidationError(f"Type de fichier non autorisé: {ext}")
                    
                    # Marquer le fichier comme validé
                    field_value._validated = True
                except Exception as e:
                    print(f"Erreur de validation du fichier {field_name}: {str(e)}")
                    raise
        
        # Stocker les données nettoyées dans le cache pour éviter de retraiter
        cache.set(cache_key, cleaned_data, 3600)  # Expire après 1 heure
        
        end_time = time.time()
        print(f"Traitement de l'étape {self.steps.current} en {end_time - start_time:.2f} secondes")
        
        return cleaned_data

@csrf_exempt
@login_required
def add_to_cart(request):
    """API pour ajouter un plat au panier"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)
    
    try:
        data = json.loads(request.body)
        dish_id = data.get('dish_id')
        quantity = data.get('quantity', 1)
        
        # Vérifier que le plat existe
        dish = get_object_or_404(Dish, id=dish_id)
        
        # Récupérer ou créer le panier de l'utilisateur
        cart, created = Order.objects.get_or_create(
            user=request.user,
            status=Order.STATUS_NEW,
            defaults={'total_amount': 0}
        )
        
        # Ajouter ou mettre à jour l'article dans le panier
        cart_item, created = OrderItem.objects.get_or_create(
            order=cart,
            dish=dish,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Mettre à jour le total de la commande
        cart.update_total()
        
        return JsonResponse({
            'success': True,
            'cart_count': cart.items.count(),
            'cart_total': str(cart.total_amount)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def chat_view(request):
    """View for the chat interface"""
    # Get or create chat session
    session_id = request.session.get('chat_session_id')
    if not session_id:
        chat_session = ChatSession.objects.create(
            user=request.user,
            language=request.LANGUAGE_CODE[:2] if hasattr(request, 'LANGUAGE_CODE') else 'en'
        )
        request.session['chat_session_id'] = str(chat_session.session_id)
    else:
        try:
            chat_session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            chat_session = ChatSession.objects.create(
                user=request.user,
                language=request.LANGUAGE_CODE[:2] if hasattr(request, 'LANGUAGE_CODE') else 'en'
            )
            request.session['chat_session_id'] = str(chat_session.session_id)

    # Get chat history
    chat_history = ChatMessage.objects.filter(session=chat_session).order_by('created_at')
    
    context = {
        'chat_session': chat_session,
        'chat_history': chat_history,
        'available_cities': City.objects.all(),
    }
    return render(request, 'foodapp/chat.html', context)

@csrf_exempt
@login_required
def chat_message(request):
    """API endpoint for chat messages"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})

    try:
        data = json.loads(request.body)
        user_input = data.get('message')
        session_id = request.session.get('chat_session_id')

        if not user_input or not session_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})

        # Initialize chatbot
        chatbot = MoroccanFoodChatbot(session_id)
        
        # Get response
        result = chatbot.get_response(user_input)
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
@login_required
def update_chat_preferences(request):
    """API endpoint to update chat preferences"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})

    try:
        data = json.loads(request.body)
        session_id = request.session.get('chat_session_id')
        
        if not session_id:
            return JsonResponse({'status': 'error', 'message': 'No active chat session'})

        chat_session = ChatSession.objects.get(session_id=session_id)
        
        # Update language if provided
        if 'language' in data:
            chat_session.language = data['language']
        
        # Update selected city if provided
        if 'city_id' in data:
            try:
                city = City.objects.get(id=data['city_id'])
                chat_session.selected_city = city
            except City.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'City not found'})
        
        chat_session.save()
        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def send_restaurant_registration_emails(restaurant_id, owner_email, owner_first_name, username, password):
    """Fonction pour envoyer les emails de façon asynchrone après la création du compte restaurant"""
    try:
        # Récupérer les informations nécessaires
        restaurant = Restaurant.objects.get(id=restaurant_id)
        
        # Email aux administrateurs
        admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
        if admin_emails:
            try:
                send_mail(
                    'Nouvelle demande de compte restaurant',
                    f'Un nouveau restaurant "{restaurant.name}" attend votre approbation. Veuillez consulter le panneau d\'administration pour examiner la demande.',
                    'noreply@foodflex.com',
                    list(admin_emails),
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur lors de l'envoi du mail aux admins: {str(e)}")
        
        # Email au propriétaire du restaurant
        try:
            send_mail(
                'Votre demande d\'inscription restaurant a été reçue',
                f'Cher {owner_first_name},\n\n'
                f'Votre demande d\'inscription pour "{restaurant.name}" a été reçue et est en cours d\'examen. '
                f'Nous vous contacterons dès que votre compte sera approuvé.\n\n'
                f'Vos identifiants de connexion :\n'
                f'Nom d\'utilisateur : {username}\n'
                f'Mot de passe : {password}\n\n'
                f'Conservez ces informations en lieu sûr. Vous pourrez modifier votre mot de passe après l\'approbation.\n\n'
                f'L\'équipe FoodFlex',
                'noreply@foodflex.com',
                [owner_email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur lors de l'envoi du mail au restaurant: {str(e)}")
    except Exception as e:
        print(f"Erreur lors de l'envoi des emails d'inscription: {str(e)}")

@login_required
def restaurant_owner_dashboard(request):
    """Tableau de bord spécifique pour les comptes restaurants"""
    
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('restaurant_pending_approval')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('accueil')
    
    # Récupérer le restaurant associé à ce compte
    restaurant = restaurant_account.restaurant
    
    # Récupérer les réservations de ce restaurant
    # Filtrer par statut si demandé
    status_filter = request.GET.get('status', None)
    date_filter = request.GET.get('date', None)
    
    reservations = Reservation.objects.filter(restaurant=restaurant).order_by('-date', '-time')
    
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    if date_filter:
        reservations = reservations.filter(date=date_filter)
    
    # Statistiques
    total_reservations = Reservation.objects.filter(restaurant=restaurant).count()
    pending_reservations = Reservation.objects.filter(restaurant=restaurant, status=Reservation.STATUS_PENDING).count()
    confirmed_reservations = Reservation.objects.filter(restaurant=restaurant, status=Reservation.STATUS_CONFIRMED).count()
    canceled_reservations = Reservation.objects.filter(restaurant=restaurant, status=Reservation.STATUS_CANCELED).count()
    
    # Réservations pour aujourd'hui
    today = timezone.now().date()
    today_reservations = Reservation.objects.filter(restaurant=restaurant, date=today).order_by('time')
    
    # Commandes récentes
    recent_orders = Order.objects.filter(
        restaurant=restaurant, 
        status__in=[Order.STATUS_NEW, Order.STATUS_PREPARING, Order.STATUS_READY]
    ).order_by('-order_time')[:5]
    
    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'reservations': reservations,
        'today_reservations': today_reservations,
        'total_reservations': total_reservations,
        'pending_reservations': pending_reservations,
        'confirmed_reservations': confirmed_reservations,
        'canceled_reservations': canceled_reservations,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'foodapp/restaurant_owner_dashboard.html', context)