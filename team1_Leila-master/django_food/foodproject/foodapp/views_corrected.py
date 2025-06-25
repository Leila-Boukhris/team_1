from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from .models import City, Dish, Restaurant, Reservation, RestaurantAccount, UserProfile, ForumTopic, ForumMessage, SubscriptionPlan, RestaurantSubscription, UserSubscription, Order, OrderItem
from .forms import DishFilterForm, CurrencyConverterForm, ReservationForm, ReservationModifyForm
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

try:
    from cpp_modules.food_processor import fast_sort_dishes
    USE_CPP_OPTIMIZATION = True
except ImportError:
    USE_CPP_OPTIMIZATION = False
    print("Module C++ non disponible, utilisation du tri Python standard")

def index(request):
    return redirect('accueil')

def accueil(request):
    featured_dishes = Dish.objects.all().order_by('?')[:5]
    dishes = Dish.objects.all().order_by('-id')[:8]
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
    dishes = Dish.objects.all()
    sort_by = request.GET.get('sort', 'name')
    city_id = request.GET.get('city')

    if city_id:
        dishes = dishes.filter(city_id=city_id)

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
        'selected_city': city_id
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

def get_dishes(request):
    """
    Vue API optimisée pour renvoyer les plats avec mise en cache
    """
    # Vérifier si les données sont en cache
    cache_key = 'all_dishes_data'
    dishes_data = cache.get(cache_key)

    if not dishes_data:
        # Si pas en cache, récupérer depuis la base de données
        start_time = time.time()
        dishes = Dish.objects.select_related('city').all()

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
    # Récupérer les plats marocains recommandés aux touristes
    recommended_dishes = Dish.objects.filter(origin=Dish.MOROCCAN, is_tourist_recommended=True)

    # Tous les plats marocains
    all_moroccan_dishes = Dish.objects.filter(origin=Dish.MOROCCAN)

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

@csrf_exempt
def dish_detail(request, dish_id):
    dish = get_object_or_404(Dish, id=dish_id)
    return render(request, 'foodapp/dish_detail.html', {
        'dish': dish
    })

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
def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            account_type = data.get('account_type', 'user')

            # Vérifier si l'utilisateur existe déj�
            if User.objects.filter(username=username).exists():
                return JsonResponse({'errors': {'username': "Ce nom d'utilisateur est déjà pris"}}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'errors': {'email': "Cette adresse email est déjà utilisée"}}, status=400)

            # Créer un nouvel utilisateur
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()

            # Créer un profil utilisateur standard dans tous les cas
            UserProfile.objects.create(user=user)

            # Si c'est un compte restaurant, créer également un RestaurantAccount
            if account_type == 'restaurant':
                restaurant_name = data.get('restaurant_name')
                restaurant_city_id = data.get('restaurant_city')
                restaurant_phone = data.get('restaurant_phone')
                restaurant_address = data.get('restaurant_address')

                # Vérifier que toutes les données restaurant sont fournies
                if not restaurant_name or not restaurant_city_id or not restaurant_phone or not restaurant_address:
                    return JsonResponse({'errors': {'general': "Informations du restaurant incomplètes"}}, status=400)

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
                        is_active=True
                    )
                except City.DoesNotExist:
                    return JsonResponse({'errors': {'restaurant_city': "Ville non trouvée"}}, status=400)
                except Exception as e:
                    return JsonResponse({'errors': {'general': f"Erreur lors de la création du restaurant: {str(e)}"}}, status=400)

            # Connecter l'utilisateur
            login(request, user)

            return JsonResponse({'success': True, 'account_type': account_type}, status=201)
        except Exception as e:
            return JsonResponse({'errors': {'general': str(e)}}, status=400)
    else:
        # Assurer que le token CSRF est généré
        csrf_token = get_token(request)
        # Passer la liste des villes pour le formulaire restaurant
        cities = City.objects.all()
        return render(request, 'foodapp/signup.html', {'cities': cities})

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
    """Tableau de bord spécifique pour les comptes restaurants"""

    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        if not restaurant_account.is_active:
            return redirect('index')
    except:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        return redirect('index')

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

    return render(request, 'foodapp/restaurant_dashboard.html', context)

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

# Nouvelles fonctions pour améliorer la gestion des réservations

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
                        is_open=True,
                        description=data.get('restaurant_description', ''),
                        website=data.get('restaurant_website', '')
                    )

                    # Créer compte restaurant
                    RestaurantAccount.objects.create(
                        user=user,
                        restaurant=restaurant,
                        is_active=True
                    )

                except City.DoesNotExist:
                    return JsonResponse({'errors': {'restaurant_city': "Ville non trouvée"}}, status=400)

            # Connecter l'utilisateur
            login(request, user)

            # Réponse rapide
            return JsonResponse({'success': True, 'restaurant_id': restaurant.id}, status=201)

        except Exception as e:
            return JsonResponse({'errors': {'general': str(e)}}, status=400)
    else:
        # Assurer que le token CSRF est généré et rendu plus rapidement
        csrf_token = get_token(request)
        # Récupérer uniquement les IDs et noms des villes pour optimiser la requête
        cities = City.objects.all().only('id', 'name')
        return render(request, 'foodapp/restaurant_signup.html', {'cities': cities})

# Vues pour le forum communautaire
@login_required
def forum_topics_list(request):
    """Vue pour afficher la liste des sujets du forum"""
    # Récupérer tous les sujets, triés par épinglés puis par date de dernière mise à jour
    topics = ForumTopic.objects.all()

    # Filtrer par catégorie si demandé
    category = request.GET.get('category')
    if category:
        topics = topics.filter(category=category)

    # Rechercher par titre si spécifié
    search = request.GET.get('search')
    if search:
        topics = topics.filter(title__icontains=search)

    # Compteurs pour la sidebar
    category_counts = {
        'general': ForumTopic.objects.filter(category='general').count(),
        'recipes': ForumTopic.objects.filter(category='recipes').count(),
        'restaurants': ForumTopic.objects.filter(category='restaurants').count(),
        'travel': ForumTopic.objects.filter(category='travel').count(),
        'events': ForumTopic.objects.filter(category='events').count(),
    }

    # Récupérer les sujets récents pour la sidebar
    recent_topics = ForumTopic.objects.order_by('-created_at')[:5]

    context = {
        'topics': topics,
        'category': category,
        'search': search,
        'category_counts': category_counts,
        'recent_topics': recent_topics,
        'categories': ForumTopic.CATEGORY_CHOICES,
    }

    return render(request, 'foodapp/forum/topics_list.html', context)

@login_required
def forum_topics_by_category(request, category):
    """Vue pour afficher les sujets d'une catégorie spécifique"""
    # Rediriger vers la liste des sujets avec un filtre de catégorie
    return redirect(f'{reverse("forum_topics_list")}?category={category}')

@login_required
def forum_topic_detail(request, topic_id):
    """Vue pour afficher le détail d'un sujet et ses messages"""
    topic = get_object_or_404(ForumTopic, id=topic_id)

    # Incrémenter le compteur de vues
    topic.views_count += 1
    topic.save()

    # Récupérer tous les messages pour ce sujet
    messages = topic.messages.all()

    # Formulaire pour ajouter un nouveau message
    form = None
    if request.user.is_authenticated:
        form = ForumMessageForm()

    context = {
        'topic': topic,
        'messages': messages,
        'form': form,
    }

    return render(request, 'foodapp/forum/topic_detail.html', context)

@login_required
def forum_new_topic(request):
    """Vue pour créer un nouveau sujet"""
    if request.method == 'POST':
        form = ForumTopicForm(request.POST)
        if form.is_valid():
            # Créer le sujet mais ne pas l'enregistrer immédiatement
            topic = form.save(commit=False)
            # Définir l'auteur comme l'utilisateur connecté
            topic.author = request.user
            # Enregistrer le sujet
            topic.save()

            # Créer le premier message (le contenu du sujet)
            message = ForumMessage(
                topic=topic,
                author=request.user,
                content=topic.content
            )
            message.save()

            # Rediriger vers le détail du sujet
            return redirect('forum_topic_detail', topic_id=topic.id)
    else:
        form = ForumTopicForm()

    context = {
        'form': form,
        'categories': ForumTopic.CATEGORY_CHOICES,
    }

    return render(request, 'foodapp/forum/new_topic.html', context)

@login_required
def forum_reply(request, topic_id):
    """Vue pour répondre à un sujet"""
    topic = get_object_or_404(ForumTopic, id=topic_id)

    if request.method == 'POST':
        form = ForumMessageForm(request.POST)
        if form.is_valid():
            # Créer le message mais ne pas l'enregistrer immédiatement
            message = form.save(commit=False)
            # Définir l'auteur et le sujet
            message.author = request.user
            message.topic = topic
            # Enregistrer le message
            message.save()

            # Mettre à jour la date de dernière activité du sujet
            topic.updated_at = timezone.now()
            topic.save()

            # Rediriger vers le détail du sujet
            return redirect('forum_topic_detail', topic_id=topic.id)
    else:
        form = ForumMessageForm()

    context = {
        'form': form,
        'topic': topic,
    }

    return render(request, 'foodapp/forum/reply.html', context)

@login_required
def forum_edit_message(request, message_id):
    """Vue pour modifier un message"""
    message = get_object_or_404(ForumMessage, id=message_id)

    # Vérifier que l'utilisateur est bien l'auteur du message
    if message.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Vous n'êtes pas autorisé à modifier ce message.")

    if request.method == 'POST':
        form = ForumMessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            return redirect('forum_topic_detail', topic_id=message.topic.id)
    else:
        form = ForumMessageForm(instance=message)

    context = {
        'form': form,
        'message': message,
        'topic': message.topic,
    }

    return render(request, 'foodapp/forum/edit_message.html', context)

@login_required
def forum_delete_message(request, message_id):
    """Vue pour supprimer un message"""
    message = get_object_or_404(ForumMessage, id=message_id)
    topic = message.topic

    # Vérifier que l'utilisateur est bien l'auteur du message ou un administrateur
    if message.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Vous n'êtes pas autorisé à supprimer ce message.")

    # Vérifier si c'est le premier message (contenu du sujet)
    is_first_message = message.id == topic.messages.order_by('created_at').first().id

    if request.method == 'POST':
        if is_first_message:
            # Si c'est le premier message, supprimer tout le sujet
            topic.delete()
            return redirect('forum_topics_list')
        else:
            # Sinon, supprimer juste le message
            message.delete()
            return redirect('forum_topic_detail', topic_id=topic.id)

    context = {
        'message': message,
        'topic': topic,
        'is_first_message': is_first_message,
    }

    return render(request, 'foodapp/forum/delete_message.html', context)

# Formulaires pour le forum
from django import forms

class ForumTopicForm(forms.ModelForm):
    """Formulaire pour créer un nouveau sujet"""
    class Meta:
        model = ForumTopic
        fields = ['title', 'category', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du sujet'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Contenu du sujet'}),
        }

class ForumMessageForm(forms.ModelForm):
    """Formulaire pour créer un nouveau message"""
    class Meta:
        model = ForumMessage
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Votre message'}),
        }

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

        # Mettre à jour les préférences
        preferences = profile.preferences or {}
        preferences.update({
            'theme': theme,
            'notifications_enabled': notifications_enabled,
            'language': language
        })

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
            'language': 'fr'
        }
        profile.save()

    context = {
        'profile': profile,
        'preferences': profile.preferences
    }

    return render(request, 'foodapp/user_settings.html', context)

@csrf_exempt
def rapide_restaurant_signup_view(request):
    """Vue pour l'inscription rapide des restaurants sans création de compte complet"""
    if request.method == 'POST':
        try:
            # Traiter les données en asynchrone pour accélérer le processus
            from django.db import transaction
            import threading

            data = json.loads(request.body)

            # Validation minimale côté serveur
            restaurant_name = data.get('restaurant_name')
            restaurant_email = data.get('restaurant_email')
            restaurant_phone = data.get('restaurant_phone')
            restaurant_city_id = data.get('restaurant_city')
            restaurant_address = data.get('restaurant_address')

            # Vérification minimale des champs obligatoires
            if not all([restaurant_name, restaurant_email, restaurant_phone, restaurant_city_id, restaurant_address]):
                return JsonResponse({
                    'success': False,
                    'errors': {'fields': 'Tous les champs obligatoires doivent être remplis'}
                }, status=400)

            # Créer le brouillon immédiatement sans effectuer d'autres vérifications lourdes
            try:
                city = City.objects.get(id=restaurant_city_id)

                # Enregistrement rapide avec transaction atomique
                with transaction.atomic():
                    restaurant_draft = RestaurantDraft(
                        name=restaurant_name,
                        email=restaurant_email,
                        phone=restaurant_phone,
                        city=city,
                        address=restaurant_address,
                        description=data.get('restaurant_description', ''),
                        features={'features': data.get('features', [])}
                    )
                    restaurant_draft.save()

                # Envoi d'email de confirmation en arrière-plan
                def send_confirmation_email():
                    # Code pour envoyer un email (simulé ici)
                    pass

                # Démarrer l'envoi d'email dans un thread séparé pour ne pas bloquer la réponse
                email_thread = threading.Thread(target=send_confirmation_email)
                email_thread.daemon = True
                email_thread.start()

                return JsonResponse({
                    'success': True,
                    'message': 'Restaurant enregistré avec succès! Vous recevrez un email pour finaliser votre inscription.',
                    'draft_id': restaurant_draft.id
                }, status=201)

            except City.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'errors': {'city': 'Ville non trouvée'}
                }, status=400)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'errors': {'json': 'Format JSON invalide'}
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'general': str(e)}
            }, status=500)

    # GET - afficher le formulaire d'inscription rapide
    else:
        # Assurer que le token CSRF est généré
        csrf_token = get_token(request)
        # Passer la liste des villes pour le formulaire
        cities = City.objects.all()
        return render(request, 'foodapp/restaurant_signup_rapide.html', {'cities': cities})

# Views pour les plans d'abonnement
def restaurant_pricing_plans(request):
    """Vue pour afficher les plans d'abonnement restaurant"""
    from .models import SubscriptionPlan, RestaurantSubscription, RestaurantAccount

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
    from .models import SubscriptionPlan, UserSubscription, UserProfile

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
    from .models import SubscriptionPlan
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

                # Vérifier si un abonnement existe déj�
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

                # Vérifier si un abonnement existe déj�
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
def edit_profile_view(request):
    """Vue pour éditer le profil utilisateur"""
    from .models import UserProfile

    try:
        # Récupérer ou créer le profil de l'utilisateur
        profile, created = UserProfile.objects.get_or_create(user=request.user)
    except:
        messages.error(request, "Une erreur s'est produite lors de la récupération de votre profil.")
        return redirect('user_profile')

    if request.method == 'POST':
        # Traitement du formulaire d'édition de profil
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        # Mise à jour du profil
        profile.bio = request.POST.get('bio', '')
        profile.phone = request.POST.get('phone', '')
        profile.favorite_cuisine = request.POST.get('favorite_cuisine', '')

        # Traitement de l'image de profil si fournie
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        # Traitement des préférences
        profile.is_vegetarian = 'is_vegetarian' in request.POST
        profile.is_vegan = 'is_vegan' in request.POST

        # Date de naissance si fournie
        birth_date = request.POST.get('birth_date', '')
        if birth_date:
            try:
                profile.date_of_birth = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except:
                messages.warning(request, "Format de date invalide. La date de naissance n'a pas été mise à jour.")

        profile.save()
        messages.success(request, "Votre profil a été mis à jour avec succès.")
        return redirect('user_profile')

    context = {
        'profile': profile,
    }

    return render(request, 'foodapp/edit_profile.html', context)

@login_required
def create_reservation(request, restaurant_id):
    """Vue pour créer une réservation de restaurant"""
    restaurant = get_object_or_404(Restaurant, pk=restaurant_id)

    if request.method == 'POST':
        # Traitement du formulaire
        form = ReservationForm(request.POST)
        if form.is_valid():
            # Création de la réservation
            reservation = form.save(commit=False)
            reservation.restaurant = restaurant
            reservation.user = request.user
            reservation.name = f"{request.user.first_name} {request.user.last_name}" if request.user.first_name else request.user.username
            reservation.email = request.user.email

            # Vérifier la disponibilité
            date = form.cleaned_data['date']
            time = form.cleaned_data['time']
            guests = form.cleaned_data['guests']
            is_available = check_availability(restaurant, date, time, guests)

            if not is_available:
                messages.error(request, "Désolé, le restaurant n'est pas disponible à ce créneau. Veuillez choisir un autre horaire.")
                return render(request, 'foodapp/make_reservation.html', {'form': form, 'restaurant': restaurant})

            # Vérifier si l'utilisateur a un abonnement premium pour priorisation
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                user_subscription = UserSubscription.objects.filter(user_profile=user_profile, status='active').first()
                if user_subscription and user_subscription.plan.features.get('priority_booking', False):
                    reservation.notes += "\n[RÉSERVATION PRIORITAIRE]"
            except:
                pass

            reservation.save()

            # Envoi de confirmation (simulation)
            messages.success(request, f"Votre réservation a été enregistrée avec succès! Code de confirmation: {reservation.confirmation_code}")
            return redirect('reservation_detail', reservation_id=reservation.id)
    else:
        form = ReservationForm()

    return render(request, 'foodapp/make_reservation.html', {'form': form, 'restaurant': restaurant})

def check_availability(restaurant, date, time, guests):
    """Fonction utilitaire pour vérifier la disponibilité du restaurant"""
    # Vérifier si le restaurant est ouvert à cette date/heure
    # Vérifier si la capacité est disponible

    # Cette fonction devrait implémenter la logique de vérification de disponibilité
    # Pour l'instant, on simule une vérification simple

    # Nombre de personnes déjà réservées à cette date et heure
    existing_reservations = Reservation.objects.filter(
        restaurant=restaurant,
        date=date,
        time=time,
        status__in=['pending', 'confirmed']
    )

    guests_count = sum(r.guests for r in existing_reservations)

    # Vérifier si la capacité est suffisante
    return (guests_count + guests) <= restaurant.capacity

@login_required
def cancel_reservation(request, reservation_id):
    """Vue pour annuler une réservation"""
    reservation = get_object_or_404(Reservation, pk=reservation_id)

    # Vérifier que la réservation appartient à l'utilisateur
    if reservation.user != request.user:
        messages.error(request, "Vous n'avez pas la permission d'annuler cette réservation.")
        return redirect('user_reservations_list')

    # Vérifier que la réservation peut être annulée
    if not reservation.can_cancel:
        messages.error(request, "Cette réservation ne peut plus être annulée.")
        return redirect('reservation_detail', reservation_id=reservation.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

        # Annuler la réservation
        reservation.status = Reservation.STATUS_CANCELED
        if reason:
            reservation.notes = f"{reservation.notes}\n\nMotif d'annulation: {reason}"
        reservation.save()

        # Envoyer notification (simulation)
        messages.success(request, "Votre réservation a été annulée avec succès.")
        return redirect('user_reservations_list')

    return render(request, 'foodapp/cancel_reservation.html', {'reservation': reservation})

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

            # Vérifier s'il existe déj�
            exists = User.objects.filter(username=username).exists()

            if exists:
                return JsonResponse({'available': False, 'message': 'Ce nom d\'utilisateur est déjà utilisé'})
            else:
                return JsonResponse({'available': True, 'message': 'Nom d\'utilisateur disponible'})

        except Exception as e:
            return JsonResponse({'available': False, 'message': str(e)}, status=400)

    return JsonResponse({'available': False, 'message': 'Méthode non autorisée'}, status=405)

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
def restaurant_order_detail(request, order_id):
    """Vue détaillée d'une commande spécifique"""

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

    # Récupérer la commande demandée
    order = get_object_or_404(Order, id=order_id, restaurant=restaurant)

    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'order': order,
    }

    return render(request, 'foodapp/restaurant_order_detail.html', context)


@login_required
def restaurant_menu(request):
    """Vue pour la gestion du menu d'un restaurant"""
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

    # Traiter le formulaire d'ajout/édition de plat si soumis
    if request.method == 'POST':
        dish_id = request.POST.get('dish_id')

        # Édition d'un plat existant
        if dish_id:
            try:
                dish = Dish.objects.get(id=dish_id, city=restaurant.city)

                # Mettre à jour les informations du plat
                dish.name = request.POST.get('name')
                dish.description = request.POST.get('description')
                dish.price_range = request.POST.get('price_range')
                dish.type = request.POST.get('type')
                dish.ingredients = request.POST.get('ingredients')
                dish.is_vegetarian = 'is_vegetarian' in request.POST
                dish.is_vegan = 'is_vegan' in request.POST

                # Traiter l'image si fournie
                if 'image' in request.FILES:
                    dish.image = request.FILES['image']

                dish.save()

                messages.success(request, f"Le plat '{dish.name}' a été mis à jour avec succès.")
            except Dish.DoesNotExist:
                messages.error(request, "Le plat demandé n'existe pas ou vous n'avez pas les droits pour le modifier.")

        # Ajout d'un nouveau plat
        else:
            try:
                dish = Dish(
                    name=request.POST.get('name'),
                    description=request.POST.get('description'),
                    price_range=request.POST.get('price_range'),
                    type=request.POST.get('type'),
                    ingredients=request.POST.get('ingredients'),
                    is_vegetarian='is_vegetarian' in request.POST,
                    is_vegan='is_vegan' in request.POST,
                    city=restaurant.city
                )

                # Traiter l'image si fournie
                if 'image' in request.FILES:
                    dish.image = request.FILES['image']

                dish.save()

                messages.success(request, f"Le plat '{dish.name}' a été ajouté avec succès.")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout du plat: {str(e)}")

        # Rediriger pour éviter les soumissions multiples
        return redirect('restaurant_menu')

    # Récupérer les plats associés à la ville du restaurant
    dishes = Dish.objects.filter(city=restaurant.city)

    # Compter les plats par type
    all_dishes_count = dishes.count()
    salty_dishes_count = dishes.filter(type=Dish.SALTY).count()
    sweet_dishes_count = dishes.filter(type=Dish.SWEET).count()
    drink_dishes_count = dishes.filter(type=Dish.DRINK).count()

    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'dishes': dishes,
        'all_dishes_count': all_dishes_count,
        'salty_dishes_count': salty_dishes_count,
        'sweet_dishes_count': sweet_dishes_count,
        'drink_dishes_count': drink_dishes_count,
    }

    return render(request, 'foodapp/restaurant_menu.html', context)


@login_required
def restaurant_reservations(request):
    """Vue pour la gestion des réservations d'un restaurant"""
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

    # Récupérer les réservations
    reservations = Reservation.objects.filter(restaurant=restaurant).order_by('-date', '-time')

    # Filtres
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    calendar_date = request.GET.get('calendar_date', '')

    if status_filter:
        reservations = reservations.filter(status=status_filter)

    if date_filter:
        reservations = reservations.filter(date=date_filter)

    # Statistiques
    today = timezone.now().date()
    total_reservations = Reservation.objects.filter(restaurant=restaurant).count()
    upcoming_reservations = Reservation.objects.filter(
        restaurant=restaurant,
        date__gte=today,
        status__in=[Reservation.STATUS_PENDING, Reservation.STATUS_CONFIRMED]
    ).count()
    today_reservations = Reservation.objects.filter(
        restaurant=restaurant,
        date=today
    )
    today_reservations_count = today_reservations.count()

    # Calcul du taux d'occupation
    # Récupérer les réservations confirmées des 30 derniers jours
    thirty_days_ago = today - timezone.timedelta(days=30)
    recent_confirmed_reservations = Reservation.objects.filter(
        restaurant=restaurant,
        date__gte=thirty_days_ago,
        date__lte=today,
        status__in=[Reservation.STATUS_CONFIRMED, Reservation.STATUS_COMPLETED]
    )

    # Si des réservations existent, calculer le taux moyen d'occupation
    if recent_confirmed_reservations:
        total_guests = sum(res.guests for res in recent_confirmed_reservations)
        num_reservations = recent_confirmed_reservations.count()
        avg_guests_per_reservation = total_guests / num_reservations if num_reservations > 0 else 0
        occupancy_rate = int((avg_guests_per_reservation / restaurant.capacity) * 100) if restaurant.capacity > 0 else 0
        # Limiter à 100% maximum
        occupancy_rate = min(occupancy_rate, 100)
    else:
        occupancy_rate = 0

    # Préparer les données pour la vue du calendrier
    # Si aucune date n'est spécifiée, utiliser la date actuelle
    if not calendar_date:
        calendar_start_date = today
    else:
        try:
            calendar_start_date = datetime.datetime.strptime(calendar_date, '%Y-%m-%d').date()
        except ValueError:
            calendar_start_date = today

    # Ajuster pour commencer le calendrier au lundi de la semaine
    weekday = calendar_start_date.weekday()
    calendar_start_date = calendar_start_date - timezone.timedelta(days=weekday)

    # Préparer les jours du calendrier (7 jours à partir du lundi)
    calendar_days = []
    day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']

    for i in range(7):
        current_date = calendar_start_date + timezone.timedelta(days=i)
        day_reservations = reservations.filter(date=current_date)

        calendar_days.append({
            'name': day_names[i],
            'date': current_date,
            'reservations': day_reservations,
            'is_today': current_date == today
        })

    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'reservations': reservations,
        'total_reservations': total_reservations,
        'upcoming_reservations': upcoming_reservations,
        'today_reservations_count': today_reservations_count,
        'occupancy_rate': occupancy_rate,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'calendar_date': calendar_date,
        'calendar_days': calendar_days,
    }

    return render(request, 'foodapp/restaurant_reservations.html', context)


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

    # Récupérer les avis pour ce restaurant
    reviews = restaurant.reviews.all()

    # Filtres
    status_filter = request.GET.get('status', '')
    if status_filter == 'published':
        reviews = reviews.filter(is_published=True)
    elif status_filter == 'unpublished':
        reviews = reviews.filter(is_published=False)

    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        reviews = reviews.filter(
            Q(comment__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # Tri
    sort_by = request.GET.get('sort', '-created_at')
    reviews = reviews.order_by(sort_by)

    # Pagination
    paginator = Paginator(reviews, 10)  # 10 avis par page
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    # Statistiques
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews else 0
    if avg_rating:
        avg_rating = round(avg_rating, 1)

    # Distribution des notes
    ratings_distribution = {
        5: reviews.filter(rating=5).count(),
        4: reviews.filter(rating=4).count(),
        3: reviews.filter(rating=3).count(),
        2: reviews.filter(rating=2).count(),
        1: reviews.filter(rating=1).count(),
    }

    # Calculer les pourcentages pour les barres de progression
    if total_reviews > 0:
        for rating in ratings_distribution:
            ratings_distribution[rating] = (ratings_distribution[rating] / total_reviews) * 100

    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'reviews': reviews_page,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'ratings_distribution': ratings_distribution,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
    }

    return render(request, 'foodapp/restaurant_reviews.html', context)


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

    # Générer les données pour les graphiques
    # Liste des dates entre start_date et end_date
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += datetime.timedelta(days=1)

    # Formater les dates pour l'affichage
    dates = [date.strftime('%d/%m') for date in date_range]

    # Données de chiffre d'affaires par jour
    revenue_data = []
    for date in date_range:
        daily_revenue = orders.filter(
            order_time__date=date,
            status__in=[Order.STATUS_DELIVERED, Order.STATUS_PAID]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        revenue_data.append(daily_revenue)

    # Données de commandes par jour
    orders_data = []
    for date in date_range:
        daily_orders = orders.filter(order_time__date=date).count()
        orders_data.append(daily_orders)

    # Répartition des ventes par catégorie de plat
    # Récupérer les articles de commande pour la période
    order_items = OrderItem.objects.filter(
        order__restaurant=restaurant,
        order__order_time__date__gte=start_date,
        order__order_time__date__lte=end_date,
        order__status__in=[Order.STATUS_DELIVERED, Order.STATUS_PAID]
    )

    # Catégories de plats (simplifiées)
    dish_categories = ['Salé', 'Sucré', 'Boissons']

    # Calculer les ventes par catégorie
    dish_categories_data = [
        order_items.filter(dish__type='salty').aggregate(total=Sum('price'))['total'] or 0,
        order_items.filter(dish__type='sweet').aggregate(total=Sum('price'))['total'] or 0,
        order_items.filter(dish__type='drink').aggregate(total=Sum('price'))['total'] or 0
    ]

    # Modes de paiement
    payment_methods = ['Espèces', 'Carte bancaire', 'En ligne']
    payment_methods_data = [
        orders.filter(payment_method=Order.PAYMENT_CASH).count(),
        orders.filter(payment_method=Order.PAYMENT_CARD).count(),
        orders.filter(payment_method=Order.PAYMENT_ONLINE).count()
    ]

    # Top des plats les plus vendus
    top_dishes_data = order_items.values('dish__name').annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum(F('price') * F('quantity'))
    ).order_by('-quantity_sold')[:10]

    # Calculer le pourcentage des ventes
    total_revenue = sum(item['revenue'] for item in top_dishes_data)

    top_dishes = []
    for dish in top_dishes_data:
        percentage = 0
        if total_revenue > 0:
            percentage = round((dish['revenue'] / total_revenue) * 100, 1)

        top_dishes.append({
            'name': dish['dish__name'],
            'quantity_sold': dish['quantity_sold'],
            'revenue': dish['revenue'],
            'percentage': percentage
        })

    # Clients récurrents
    recurring_customers = orders.values('customer_name').annotate(
        order_count=Count('id'),
        total_spent=Sum('total_amount'),
        last_visit=Max('order_time')
    ).filter(order_count__gt=1).order_by('-order_count')[:10]

    context = {
        'restaurant': restaurant,
        'account': restaurant_account,
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue,
        'orders_count': orders_count,
        'avg_order_value': avg_order_value,
        'reservations_count': reservations_count,

        # Données pour les graphiques (converties en JSON)
        'dates': json.dumps(dates),
        'revenue_data': json.dumps(revenue_data),
        'orders_data': json.dumps(orders_data),
        'dish_categories': json.dumps(dish_categories),
        'dish_categories_data': json.dumps(dish_categories_data),
        'payment_methods': json.dumps(payment_methods),
        'payment_methods_data': json.dumps(payment_methods_data),

        # Données pour les tableaux
        'top_dishes': top_dishes,
        'recurring_customers': recurring_customers
    }

    return render(request, 'foodapp/restaurant_stats.html', context)

def safe_json_list(data):
    """Helper function to safely convert Python lists to JSON for template use"""
    import json
    return json.dumps(data)

@login_required
def restaurant_settings(request):
    """Vue pour les paramètres d'un restaurant"""
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

    # Récupérer les informations de base de la commande
    customer_name = request.POST.get('customer_name', '')
    is_takeaway = 'is_takeaway' in request.POST
    table_number = None if is_takeaway else request.POST.get('table_number')
    special_instructions = request.POST.get('special_instructions', '')
    payment_method = request.POST.get('payment_method', Order.PAYMENT_CASH)

    # Créer la commande
    order = Order.objects.create(
        restaurant=restaurant,
        customer_name=customer_name,
        is_takeaway=is_takeaway,
        table_number=table_number,
        special_instructions=special_instructions,
        payment_method=payment_method,
        status=Order.STATUS_NEW
    )

    # Traiter les articles de la commande
    i = 1
    total_amount = 0

    while f'dish_{i}' in request.POST:
        dish_id = request.POST.get(f'dish_{i}')
        if dish_id:
            try:
                dish = Dish.objects.get(id=dish_id)
                quantity = int(request.POST.get(f'quantity_{i}', 1))
                notes = request.POST.get(f'notes_{i}', '')

                # Déterminer le prix en fonction de la fourchette de prix du plat
                if dish.price_range == Dish.PRICE_LOW:
                    price = 5.99
                elif dish.price_range == Dish.PRICE_MEDIUM:
                    price = 10.99
                else:  # PRICE_HIGH
                    price = 15.99

                # Créer l'élément de commande
                order_item = OrderItem.objects.create(
                    order=order,
                    dish=dish,
                    quantity=quantity,
                    price=price,
                    notes=notes
                )

                # Ajouter au total
                total_amount += price * quantity

            except Dish.DoesNotExist:
                pass

        i += 1

    # Mettre à jour le montant total
    order.total_amount = total_amount
    order.save()

    messages.success(request, f"Commande #{order.order_code} créée avec succès")
    return redirect('restaurant_orders')