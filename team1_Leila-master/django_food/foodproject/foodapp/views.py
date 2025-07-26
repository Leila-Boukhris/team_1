# Standard library imports
import json
import os
from datetime import datetime, timedelta

# Django imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm, UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import FileSystemStorage
from django.db.models import Count, Q, Sum, F, Case, When, IntegerField, Prefetch
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import ListView, TemplateView, UpdateView
from formtools.wizard.views import SessionWizardView

# Local application imports
from .models import (
    Restaurant, Dish, Reservation, Review, Category, RestaurantAccount,
    City, UserProfile, ForumTopic, ForumMessage, SubscriptionPlan,
    RestaurantSubscription, UserSubscription
)
from .forms import (
    DishFilterForm, CurrencyConverterForm, ReservationForm,
    ReservationModifyForm, RestaurantBasicInfoForm, RestaurantAuthInfoForm,
    RestaurantOwnerInfoForm, RestaurantLegalDocsForm, RestaurantPhotosForm,
    DishForm, CategoryForm
)

def index(request):
    """Vue de la page d'accueil qui redirige vers la page d'accueil principale"""
    return redirect('accueil')

def restaurants(request):
    """Vue pour afficher la liste des restaurants avec filtres"""
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
def dish_detail(request, dish_id):
    """Vue pour afficher les détails d'un plat spécifique"""
    dish = get_object_or_404(Dish, id=dish_id)
    return render(request, 'foodapp/dish_detail.html', {
        'dish': dish
    })

def dish_list(request):
    """Vue pour afficher la liste des plats avec tri et filtrage"""
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

def restaurant_detail(request, restaurant_id):
    """Vue pour afficher les détails d'un restaurant spécifique"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    city_dishes = Dish.objects.filter(city=restaurant.city).order_by('-id')[:6]
    
    context = {
        'restaurant': restaurant,
        'city_dishes': city_dishes,
    }
    
    return render(request, 'foodapp/restaurant_detail.html', context)

@login_required
def dashboard(request):
    """Vue pour le tableau de bord principal avec les statistiques"""
    # Statistiques
    restaurants_count = Restaurant.objects.count()
    active_restaurants_count = Restaurant.objects.filter(is_open=True).count()
    dishes_count = Dish.objects.count()
    vegetarian_dishes_count = Dish.objects.filter(is_vegetarian=True).count()
    cities_count = City.objects.count()
    users_count = User.objects.count()
    staff_count = User.objects.filter(is_staff=True).count()
    
    # Comptage par type de plat
    sweet_dishes_count = Dish.objects.filter(type='sweet').count()
    salty_dishes_count = Dish.objects.filter(type='salty').count()
    drink_dishes_count = Dish.objects.filter(type='drink').count()
    
    # Dernières données
    latest_restaurants = Restaurant.objects.all().order_by('-created_at')[:5]
    latest_dishes = Dish.objects.all().order_by('-id')[:5]
    
    # Toutes les villes pour les graphiques
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
    pending_reservations = Reservation.objects.filter(
        restaurant=restaurant, 
        status=Reservation.STATUS_PENDING
    ).count()
    confirmed_reservations = Reservation.objects.filter(
        restaurant=restaurant, 
        status=Reservation.STATUS_CONFIRMED
    ).count()
    canceled_reservations = Reservation.objects.filter(
        restaurant=restaurant, 
        status=Reservation.STATUS_CANCELED
    ).count()
    
    # Réservations pour aujourd'hui
    today = timezone.now().date()
    today_reservations = Reservation.objects.filter(
        restaurant=restaurant, 
        date=today
    ).order_by('time')
    
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
def restaurant_orders_live(request):
    """
    Vue pour les mises à jour en temps réel des commandes d'un restaurant.
    Retourne les nouvelles commandes et les mises à jour d'état au format JSON.
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'restaurant_account'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
        
    restaurant = request.user.restaurant_account.restaurant
    
    # Récupérer les commandes récentes (par exemple, des dernières 24 heures)
    time_threshold = timezone.now() - timezone.timedelta(hours=24)
    orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    # Formater les données pour la réponse JSON
    orders_data = []
    for order in orders:
        order_items = [{
            'dish_name': item.dish.name,
            'quantity': item.quantity,
            'price': str(item.price),
            'notes': item.notes or ''
        } for item in order.items.all()]
        
        orders_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'status': order.get_status_display(),
            'status_code': order.status,
            'created_at': order.created_at.isoformat(),
            'customer_name': order.customer_name,
            'total_amount': str(order.total_amount),
            'items': order_items
        })
    
    # Vérifier les nouvelles commandes (pour les mises à jour en temps réel)
    last_order_id = request.GET.get('last_order_id')
    if last_order_id:
        try:
            last_order = Order.objects.get(id=last_order_id, restaurant=restaurant)
            new_orders = orders.filter(created_at__gt=last_order.created_at)
            has_new_orders = new_orders.exists()
        except Order.DoesNotExist:
            has_new_orders = False
    else:
        has_new_orders = orders.exists()
    
    response_data = {
        'success': True,
        'orders': orders_data,
        'has_new_orders': has_new_orders,
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(response_data)

@login_required
def restaurant_reviews(request):
    """
    Vue pour afficher et gérer les avis des clients pour le restaurant de l'utilisateur connecté.
    """
    # Vérifier que l'utilisateur est un propriétaire de restaurant
    if not hasattr(request.user, 'restaurant_account'):
        messages.error(request, "Accès réservé aux propriétaires de restaurant.")
        return redirect('dashboard')
    
    restaurant = request.user.restaurant_account.restaurant
    
    # Récupérer les avis avec pagination
    reviews_list = Review.objects.filter(restaurant=restaurant).order_by('-created_at')
    
    # Filtrer par statut si spécifié
    status = request.GET.get('status')
    if status in ['published', 'pending', 'rejected']:
        reviews_list = reviews_list.filter(status=status)
    
    # Recherche par texte
    search_query = request.GET.get('search', '')
    if search_query:
        reviews_list = reviews_list.filter(
            Q(comment__icontains=search_query) | 
            Q(user__username__icontains(search_query))
        )
    
    # Pagination
    paginator = Paginator(reviews_list, 10)  # 10 avis par page
    page = request.GET.get('page')
    reviews = paginator.get_page(page)
    
    # Calculer la note moyenne
    avg_rating = reviews_list.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Compter les avis par statut
    review_stats = reviews_list.values('status').annotate(count=Count('id'))
    status_counts = {stat['status']: stat['count'] for stat in review_stats}
    
    context = {
        'reviews': reviews,
        'restaurant': restaurant,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'total_reviews': reviews_list.count(),
        'status_counts': status_counts,
        'current_status': status,
        'search_query': search_query,
    }
    
    return render(request, 'foodapp/restaurant/reviews.html', context)


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
    
    return render(request, 'foodapp/restaurant/orders.html', context)

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

def reservation(request, restaurant_id):
    """Vue pour gérer les réservations de restaurant"""
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

def accueil(request):
    """Vue principale de la page d'accueil avec les plats et villes en vedette"""
    try:
        featured_dishes = Dish.objects.all().order_by('?')[:5]
        dishes = Dish.objects.all().order_by('-id')[:8]
        cities = City.objects.all()[:4]
    except Exception as e:
        # En cas d'erreur (par exemple, tables pas encore créées), on utilise des listes vides
        featured_dishes = []
        dishes = []
        cities = []
        
    context = {
        'featured_dishes': featured_dishes,
        'dishes': dishes,
        'cities': cities,
    }
    return render(request, 'foodapp/accueil.html', context)

@login_required
def manage_restaurant_menu(request, restaurant_id):
    """View for managing a restaurant's menu"""
    # Verify the user is the owner of the restaurant
    if not is_restaurant_owner(request.user, restaurant_id):
        return HttpResponseForbidden("You don't have permission to manage this restaurant's menu.")
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    categories = Category.objects.filter(restaurant=restaurant).order_by('name')
    
    # Get all dishes for this restaurant
    dishes = Dish.objects.filter(restaurant=restaurant).select_related('category')
    
    # Group dishes by category
    menu = {}
    for category in categories:
        menu[category] = dishes.filter(category=category)
    
    # Handle uncategorized dishes
    uncategorized_dishes = dishes.filter(category__isnull=True)
    if uncategorized_dishes.exists():
        menu[None] = uncategorized_dishes
    
    # Handle form submissions
    if request.method == 'POST':
        if 'add_category' in request.POST:
            category_form = CategoryForm(request.POST, prefix='category')
            if category_form.is_valid():
                category = category_form.save(commit=False)
                category.restaurant = restaurant
                category.save()
                messages.success(request, 'Category added successfully!')
                return redirect('restaurant_menu_manage', restaurant_id=restaurant.id)
        elif 'add_dish' in request.POST:
            dish_form = DishForm(request.POST, request.FILES, prefix='dish')
            if dish_form.is_valid():
                dish = dish_form.save(commit=False)
                dish.restaurant = restaurant
                dish.save()
                messages.success(request, 'Dish added successfully!')
                return redirect('restaurant_menu_manage', restaurant_id=restaurant.id)
    else:
        category_form = CategoryForm(prefix='category')
        dish_form = DishForm(prefix='dish')
    
    context = {
        'restaurant': restaurant,
        'menu': menu,
        'category_form': category_form,
        'dish_form': dish_form,
    }
    
    return render(request, 'foodapp/restaurant/menu_manage.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    """
    API endpoint to create a new order.
    Expected JSON payload:
    {
        "restaurant_id": 1,
        "customer_id": 1,  # Optional if user is authenticated
        "items": [
            {"dish_id": 1, "quantity": 2, "notes": "No onions"},
            ...
        ],
        "table_number": "A12",  # Optional
        "special_instructions": "Please bring extra napkins"  # Optional
    }
    """
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['restaurant_id', 'items']
        for field in required_fields:
            if field not in data:
                return JsonResponse(
                    {'error': f'Missing required field: {field}'}, 
                    status=400
                )
        
        # Get or validate restaurant
        try:
            restaurant = Restaurant.objects.get(id=data['restaurant_id'])
        except Restaurant.DoesNotExist:
            return JsonResponse(
                {'error': 'Restaurant not found'}, 
                status=404
            )
        
        # Get or validate customer
        customer = None
        if request.user.is_authenticated:
            customer = request.user
        elif 'customer_id' in data:
            try:
                User = get_user_model()
                customer = User.objects.get(id=data['customer_id'])
            except User.DoesNotExist:
                pass
        
        # Start transaction to ensure data consistency
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                restaurant=restaurant,
                customer=customer,
                status='pending',
                table_number=data.get('table_number', ''),
                special_instructions=data.get('special_instructions', '')
            )
            
            # Add order items
            total_amount = 0
            for item in data['items']:
                try:
                    dish = Dish.objects.get(id=item['dish_id'], restaurant=restaurant)
                    quantity = int(item.get('quantity', 1))
                    order_item = OrderItem.objects.create(
                        order=order,
                        dish=dish,
                        quantity=quantity,
                        price=dish.price,
                        notes=item.get('notes', '')
                    )
                    total_amount += dish.price * quantity
                except (Dish.DoesNotExist, ValueError, KeyError) as e:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {'error': f'Invalid dish data: {str(e)}'}, 
                        status=400
                    )
            
            # Update order total
            order.total_amount = total_amount
            order.save()
            
            # TODO: Add notification to restaurant staff
            
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'status': order.get_status_display(),
                'total_amount': str(total_amount),
                'created_at': order.created_at.isoformat()
            })
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON data'}, 
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Error creating order: {str(e)}'}, 
            status=500
        )


@login_required
@login_required
def user_settings(request):
    """
    View for users to update their account settings.
    Handles both profile updates and password changes.
    """
    user = request.user
    
    # Handle profile update form
    profile_form = UserProfileForm(instance=user)
    password_form = PasswordChangeForm(user=user)
    
    if request.method == 'POST':
        # Check which form was submitted
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile was successfully updated!')
                return redirect('user_settings')
                
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important to keep the user logged in
                messages.success(request, 'Your password was successfully updated!')
                return redirect('user_settings')
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    
    return render(request, 'foodapp/user/settings.html', context)


def user_reservations_list(request):
    """
    View to display a list of the current user's reservations.
    Shows both upcoming and past reservations with pagination.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to view your reservations.')
        return redirect('login')
    
    # Get current date for filtering
    now = timezone.now()
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')  # 'upcoming', 'past', or 'all'
    page = request.GET.get('page', 1)
    
    # Base queryset
    reservations = Reservation.objects.filter(user=request.user).order_by('-reservation_date', '-reservation_time')
    
    # Apply filters
    if status_filter == 'upcoming':
        reservations = reservations.filter(
            reservation_date__gte=now.date()
        ).exclude(
            reservation_date=now.date(),
            reservation_time__lt=now.time()
        )
    elif status_filter == 'past':
        reservations = reservations.filter(
            models.Q(reservation_date__lt=now.date()) |
            models.Q(reservation_date=now.date(), reservation_time__lte=now.time())
        )
    
    # Pagination
    paginator = Paginator(reservations, 10)  # Show 10 reservations per page
    try:
        reservations_page = paginator.page(page)
    except PageNotAnInteger:
        reservations_page = paginator.page(1)
    except EmptyPage:
        reservations_page = paginator.page(paginator.num_pages)
    
    context = {
        'reservations': reservations_page,
        'status_filter': status_filter,
        'now': now,
    }
    
    return render(request, 'foodapp/user/reservations_list.html', context)


def restaurant_menu_create(request):
    """
    View to create a new dish in the restaurant's menu.
    This is a simplified version of add_dish that redirects to the main menu management page.
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'restaurant_account'):
        messages.error(request, 'You must be logged in as a restaurant owner to access this page.')
        return redirect('login')
    
    restaurant = request.user.restaurant_account.restaurant
    
    if request.method == 'POST':
        form = DishForm(request.POST, request.FILES)
        if form.is_valid():
            dish = form.save(commit=False)
            dish.restaurant = restaurant
            dish.save()
            messages.success(request, 'Dish added successfully!')
            return redirect('restaurant_menu_manage', restaurant_id=restaurant.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DishForm()
    
    context = {
        'form': form,
        'restaurant': restaurant,
    }
    
    return render(request, 'foodapp/restaurant/menu_create.html', context)


def add_dish(request):
    """View to add a new dish to the menu"""
    if request.method == 'POST':
        form = DishForm(request.POST, request.FILES)
        if form.is_valid():
            dish = form.save(commit=False)
            # Get the restaurant from the user's account
            try:
                restaurant_account = request.user.restaurant_account
                dish.restaurant = restaurant_account.restaurant
                dish.save()
                messages.success(request, 'Dish added successfully!')
                return redirect('restaurant_menu_manage', restaurant_id=dish.restaurant.id)
            except RestaurantAccount.DoesNotExist:
                messages.error(request, 'You are not associated with any restaurant.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DishForm()
    
    return render(request, 'foodapp/restaurant/dish_form.html', {'form': form, 'action': 'Add'})

@login_required
def edit_dish(request, dish_id):
    """View to edit an existing dish"""
    dish = get_object_or_404(Dish, id=dish_id)
    
    # Check if the user is the owner of the restaurant
    if not is_restaurant_owner(request.user, dish.restaurant.id):
        return HttpResponseForbidden("You don't have permission to edit this dish.")
    
    if request.method == 'POST':
        form = DishForm(request.POST, request.FILES, instance=dish, restaurant=dish.restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dish updated successfully!')
            return redirect('restaurant_menu_manage', restaurant_id=dish.restaurant.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DishForm(instance=dish, restaurant=dish.restaurant)
    
    return render(request, 'foodapp/restaurant/dish_form.html', {
        'form': form, 
        'action': 'Edit',
        'dish': dish
    })

@login_required
@require_POST
def delete_dish(request, dish_id):
    """View to delete a dish"""
    dish = get_object_or_404(Dish, id=dish_id)
    
    # Check if the user is the owner of the restaurant
    if not is_restaurant_owner(request.user, dish.restaurant.id):
        return HttpResponseForbidden("You don't have permission to delete this dish.")
    
    restaurant_id = dish.restaurant.id
    dish.delete()
    messages.success(request, 'Dish deleted successfully.')
    return redirect('restaurant_menu_manage', restaurant_id=restaurant_id)

@login_required
def add_category(request, restaurant_id):
    """View to add a new category to the menu"""
    # Check if the user is the owner of the restaurant
    if not is_restaurant_owner(request.user, restaurant_id):
        return HttpResponseForbidden("You don't have permission to add categories to this restaurant.")
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.restaurant = restaurant
            category.save()
            messages.success(request, 'Category added successfully!')
            return redirect('restaurant_menu_manage', restaurant_id=restaurant.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm()
    
    return render(request, 'foodapp/restaurant/category_form.html', {
        'form': form,
        'action': 'Add',
        'restaurant': restaurant
    })

@login_required
def edit_category(request, category_id):
    """View to edit an existing category"""
    category = get_object_or_404(Category, id=category_id)
    
    # Check if the user is the owner of the restaurant
    if not is_restaurant_owner(request.user, category.restaurant.id):
        return HttpResponseForbidden("You don't have permission to edit this category.")
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('restaurant_menu_manage', restaurant_id=category.restaurant.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'foodapp/restaurant/category_form.html', {
        'form': form,
        'action': 'Edit',
        'category': category,
        'restaurant': category.restaurant
    })

@login_required
@require_http_methods(["POST"])
def delete_category(request, category_id):
    """View to delete a category"""
    category = get_object_or_404(Category, id=category_id)
    
    # Check if the user is the owner of the restaurant
    if not is_restaurant_owner(request.user, category.restaurant.id):
        return HttpResponseForbidden("You don't have permission to delete this category.")
    
    restaurant_id = category.restaurant.id
    
    # Move dishes to uncategorized (category=None)
    Dish.objects.filter(category=category).update(category=None)
    
    # Delete the category
    category.delete()
    
    messages.success(request, 'Category deleted. Dishes have been moved to uncategorized.')
    return redirect('restaurant_menu_manage', restaurant_id=restaurant_id)

def terms_of_service(request):
    """Vue pour afficher les conditions d'utilisation"""
    return render(request, 'foodapp/terms_of_service.html') 

def register_restaurant(request):
    """Vue pour l'inscription d'un nouveau restaurant"""
    if request.method == 'POST':
        try:
            # Vérifier les champs obligatoires
            required_fields = [
                'name', 'city', 'address', 'phone', 'email', 'description', 'capacity',
                'owner_first_name', 'owner_last_name', 'owner_email', 'owner_phone'
            ]
            
            missing_fields = [field for field in required_fields if not request.POST.get(field)]
            if missing_fields:
                messages.error(
                    request,
                    f'Champs obligatoires manquants : {", ".join(missing_fields)}'
                )
                return redirect('register_restaurant')
                
            # Vérifier les fichiers obligatoires
            required_files = [
                'owner_id_card', 'business_registration', 
                'food_safety_certificate', 'main_image', 
                'interior_image1', 'menu_sample'
            ]
            
            missing_files = [field for field in required_files if field not in request.FILES]
            if missing_files:
                messages.error(
                    request,
                    f'Fichiers obligatoires manquants : {", ".join(missing_files)}'
                )
                return redirect('register_restaurant')
            
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
                owner_phone=request.POST['owner_phone']
            )
            
            # Ajouter les fichiers obligatoires
            file_fields = {
                'owner_id_card': 'owner_id_card',
                'business_registration': 'business_registration',
                'food_safety_certificate': 'food_safety_certificate',
                'tax_document': 'tax_document',
                'main_image': 'main_image',
                'interior_image1': 'interior_image1',
                'interior_image2': 'interior_image2',
                'menu_sample': 'menu_sample'
            }
            
            for field_name, file_key in file_fields.items():
                if file_key in request.FILES:
                    setattr(restaurant_draft, field_name, request.FILES[file_key])
            
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
            
        except City.DoesNotExist:
            messages.error(
                request,
                'La ville sélectionnée est invalide. Veuillez réessayer.'
            )
        except Exception as e:
            # Afficher l'erreur réelle en mode débogage
            import traceback
            error_message = str(e)
            if settings.DEBUG:
                error_message += f"\n\n{traceback.format_exc()}"
                
            messages.error(
                request,
                f'Une erreur est survenue lors de la soumission de votre demande : {error_message}'
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
    form_list = [
        ("auth_info", RestaurantAuthInfoForm),
        ("basic_info", RestaurantBasicInfoForm),
        ("owner_info", RestaurantOwnerInfoForm),
        ("legal_docs", RestaurantLegalDocsForm),
        ("photos", RestaurantPhotosForm),
    ]
    
    def __init__(self, **kwargs):
        # Remove url_name if it exists in kwargs to prevent the error
        kwargs.pop('url_name', None)
        super().__init__(**kwargs)
        
        # Ensure form_list is properly set
        if not hasattr(self, 'form_list') or not self.form_list:
            self.form_list = [
                ("auth_info", RestaurantAuthInfoForm),
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
    
    file_storage = FileSystemStorage(
        location=os.path.join(settings.MEDIA_ROOT, 'temp_uploads'),
        file_permissions_mode=0o644,
        base_url=settings.MEDIA_URL + 'temp_uploads/'
    )
    
    def get_form_list(self):
        # Get forms from the URL configuration
        form_list = self.get_form_list()
        if not form_list:
            # Fallback to default forms if none provided
            from .forms import (
                RestaurantAuthInfoForm, RestaurantBasicInfoForm,
                RestaurantOwnerInfoForm, RestaurantLegalDocsForm, RestaurantPhotosForm
            )
            form_list = [
                ("auth_info", RestaurantAuthInfoForm),
                ("basic_info", RestaurantBasicInfoForm),
                ("owner_info", RestaurantOwnerInfoForm),
                ("legal_docs", RestaurantLegalDocsForm),
                ("photos", RestaurantPhotosForm),
            ]
        return form_list
    
    def get_template_names(self):
        return ["foodapp/restaurant_registration.html"]
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context.update({
            'step_titles': [
                'Informations de base',
                'Plat',
                'Catégorie'
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
        # Combiner les données de tous les formulaires
        restaurant_data = {}
        
        for form in form_list:
            restaurant_data.update(form.cleaned_data)
        
        try:
            # Créer un nouveau restaurant avec les données du formulaire
            restaurant = Restaurant(**restaurant_data)
            restaurant.save()
            
            # Si l'utilisateur est connecté, l'associer au restaurant
            if self.request.user.is_authenticated:
                restaurant.owner = self.request.user
                restaurant.save()
            
            # Rediriger vers une page de confirmation ou le tableau de bord
            return redirect('restaurant_owner_dashboard')
            
        except Exception as e:
            # En cas d'erreur, afficher un message d'erreur et rediriger
            messages.error(self.request, f"Une erreur est survenue lors de la création du restaurant: {str(e)}")
            return redirect('restaurant_registration')

    def get_form(self, step=None, data=None, files=None):
        """Surcharge pour personnaliser l'initialisation du formulaire"""
        form = super().get_form(step, data, files)
        
        # Ajouter des classes CSS aux champs du formulaire
        if form:
            for field_name, field in form.fields.items():
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
                    
                # Ajouter des placeholders spécifiques pour le formulaire d'authentification
                if step == 'auth_info':
                    if field_name == 'username':
                        field.widget.attrs['placeholder'] = 'Choisissez un nom d\'utilisateur'
                    elif field_name == 'password1':
                        field.widget.attrs['placeholder'] = 'Créez un mot de passe sécurisé'
                    elif field_name == 'password2':
                        field.widget.attrs['placeholder'] = 'Confirmez votre mot de passe'
        
        return form
        
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
    chat_history = ChatMessage.objects.filter(session=chat_session).order_by('timestamp')
    
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

        # Simple response since we've removed the chatbot
        return JsonResponse({
            'status': 'success',
            'message': 'Chat functionality is currently unavailable.',
            'session_id': session_id
        })

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
def restaurant_approval(request, restaurant_id, action):
    """
    Vue pour approuver ou rejeter un restaurant
    """
    if not request.user.is_staff:
        return HttpResponseForbidden("Accès refusé")
    
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    if action == 'approve':
        restaurant.is_approved = True
        restaurant.approval_date = timezone.now()
        restaurant.approved_by = request.user
        messages.success(request, f"Le restaurant {restaurant.name} a été approuvé avec succès.")
    elif action == 'reject':
        restaurant.is_approved = False
        messages.success(request, f"Le restaurant {restaurant.name} a été rejeté.")
    else:
        messages.error(request, "Action non valide.")
        return redirect('admin_restaurant_detail', restaurant_id=restaurant_id)
    
    restaurant.save()
    
    # Envoyer un email de notification au propriétaire du restaurant
    try:
        if restaurant.owner and restaurant.owner.email:
            subject = f"Statut de votre restaurant : {restaurant.name}"
            message = f"Votre restaurant {restaurant.name} a été "
            message += "approuvé" if restaurant.is_approved else "rejeté"
            message += " par l'administrateur."
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [restaurant.owner.email],
                fail_silently=False,
            )
    except Exception as e:
        # Ne pas échouer si l'email ne peut pas être envoyé
        print(f"Erreur lors de l'envoi de l'email de notification : {e}")
    
    return redirect('admin_restaurant_detail', restaurant_id=restaurant_id)


def restaurant_edit(request, restaurant_id):
    """
    Vue pour modifier les informations d'un restaurant
    """
    # Récupérer le restaurant ou retourner une 404 si non trouvé
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Vérifier que l'utilisateur est bien le propriétaire du restaurant
    if not request.user.is_authenticated or request.user != restaurant.owner:
        messages.error(request, "Vous n'êtes pas autorisé à modifier ce restaurant.")
        return redirect('restaurant_owner_dashboard')
    
    if request.method == 'POST':
        # Créer une instance du formulaire avec les données soumises
        form = RestaurantBasicInfoForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            # Sauvegarder les modifications
            restaurant = form.save(commit=False)
            
            # Gérer l'image de couverture si une nouvelle est fournie
            if 'main_image' in request.FILES:
                restaurant.main_image = request.FILES['main_image']
            
            restaurant.save()
            messages.success(request, "Les informations du restaurant ont été mises à jour avec succès.")
            return redirect('restaurant_owner_dashboard')
    else:
        # Afficher le formulaire pré-rempli avec les données actuelles
        form = RestaurantBasicInfoForm(instance=restaurant)
    
    context = {
        'form': form,
        'restaurant': restaurant,
        'title': f'Modifier {restaurant.name}'
    }
    
    return render(request, 'foodapp/restaurant_edit.html', context)

@login_required
def restaurant_owner_dashboard(request):
    """
    Tableau de bord spécifique pour les comptes restaurants
    """
    
    # Vérifier si l'utilisateur est authentifié
    if not request.user.is_authenticated:
        print("DEBUG: Utilisateur non authentifié")
        messages.error(request, "Veuillez vous connecter pour accéder à cette page.")
        return redirect('login')
    
    print(f"DEBUG: Utilisateur connecté: {request.user.username}")
    
    # Vérifier si l'utilisateur a bien un compte restaurant associé
    try:
        restaurant_account = request.user.restaurant_account
        print(f"DEBUG: Compte restaurant trouvé - ID: {restaurant_account.id}, Actif: {restaurant_account.is_active}")
        
        if not restaurant_account.is_active:
            print("DEBUG: Compte restaurant non actif, redirection vers l'approbation")
            messages.warning(request, "Votre compte est en attente d'approbation par l'administrateur.")
            return redirect('restaurant_pending_approval')
            
    except Exception as e:
        # Si l'utilisateur n'a pas de compte restaurant associé, le rediriger vers l'accueil
        print(f"DEBUG: Erreur lors de la récupération du compte restaurant: {str(e)}")
        messages.error(request, "Accès refusé. Vous n'avez pas les droits nécessaires pour accéder à cette page.")
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

@login_required
def restaurant_pos(request, restaurant_id):
    """
    Vue pour l'interface caisse (POS) du restaurant
    """
    # Vérifier si l'utilisateur a les droits d'accès
    if not hasattr(request.user, 'restaurant_account') or not request.user.restaurant_account.is_active:
        messages.error(request, "Accès refusé. Vous n'avez pas les droits nécessaires pour accéder à cette page.")
        return redirect('accueil')
    
    # Vérifier que le restaurant existe et appartient à l'utilisateur
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, restaurant_account=request.user.restaurant_account)
    
    # Récupérer les plats du restaurant
    dishes = Dish.objects.filter(restaurant=restaurant, is_available=True).order_by('type', 'name')
    
    # Préparer les catégories de plats pour le menu
    categories = {}
    for dish in dishes:
        if dish.type not in categories:
            categories[dish.type] = []
        categories[dish.type].append(dish)
    
    # Récupérer les commandes en cours
    active_orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=['new', 'preparing']
    ).order_by('-created_at')
    
    context = {
        'restaurant': restaurant,
        'categories': categories,
        'active_orders': active_orders,
        'active_tab': 'pos',
    }
    
    return render(request, 'foodapp/restaurant_pos.html', context)

@login_required
def kitchen_dashboard(request, restaurant_id):
    """
    Vue pour l'interface cuisine du restaurant
    """
    # Vérifier si l'utilisateur a les droits d'accès
    if not hasattr(request.user, 'restaurant_account') or not request.user.restaurant_account.is_active:
        messages.error(request, "Accès refusé. Vous n'avez pas les droits nécessaires pour accéder à cette page.")
        return redirect('accueil')
    
    # Vérifier que le restaurant existe et appartient à l'utilisateur
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, restaurant_account=request.user.restaurant_account)
    
    # Récupérer les commandes par statut
    new_orders = Order.objects.filter(
        restaurant=restaurant,
        status='new'
    ).order_by('created_at')
    
    preparing_orders = Order.objects.filter(
        restaurant=restaurant,
        status='preparing'
    ).order_by('updated_at')
    
    ready_orders = Order.objects.filter(
        restaurant=restaurant,
        status='ready',
        updated_at__date=timezone.now().date()
    ).order_by('-updated_at')
    
    # Statistiques du jour
    today = timezone.now().date()
    today_orders = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today
    )
    
    today_stats = {
        'total_orders': today_orders.count(),
        'new_orders': today_orders.filter(status='new').count(),
        'preparing_orders': today_orders.filter(status='preparing').count(),
        'completed_orders': today_orders.filter(status='completed').count(),
        'revenue': today_orders.filter(status__in=[Order.STATUS_DELIVERED, Order.STATUS_PAID]).aggregate(
            total=Sum('total_amount'))['total'] or 0,
    }
    
    context = {
        'restaurant': restaurant,
        'new_orders': new_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'today_stats': today_stats,
        'active_tab': 'kitchen',
    }
    
    return render(request, 'foodapp/kitchen_dashboard.html', context)

@login_required
def subscription_checkout(request, plan_type, plan_id):
    """Vue pour s'abonner à un plan"""
    from .models import SubscriptionPlan
    from datetime import timedelta
    
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    
    # Vérifier que le type de plan correspond au bon utilisateur
    if plan_type == 'restaurant':
        if not hasattr(request.user, 'restaurant_account'):
            messages.error(request, "Ce plan est réservé aux restaurants.")
            return redirect('user_pricing_plans')
    elif plan_type == 'user':
        if hasattr(request.user, 'restaurant_account'):
            messages.error(request, "Ce plan est réservé aux utilisateurs réguliers.")
            return redirect('restaurant_pricing_plans')
    else:
        messages.error(request, "Type de plan invalide.")
        return redirect('user_pricing_plans')
    
    # Gérer la soumission du formulaire
    if request.method == 'POST':
        is_yearly = request.POST.get('period') == 'yearly'
        
        # Ici, vous intégrerez la logique de paiement (Stripe, PayPal, etc.)
        # Pour l'instant, nous allons simplement créer l'abonnement
        
        # Calculer la date d'expiration
        from django.utils import timezone
        now = timezone.now()
        if is_yearly:
            expires_at = now + timedelta(days=365)
            price = plan.price_yearly
        else:
            expires_at = now + timedelta(days=30)
            price = plan.price_monthly
        
        # Créer ou mettre à jour l'abonnement
        subscription, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'start_date': now,
                'expires_at': expires_at,
                'is_active': True,
                'auto_renew': True,
                'price': price,
                'is_yearly': is_yearly
            }
        )
        
        messages.success(request, f"Vous êtes maintenant abonné au plan {plan.name}!")
        return redirect('user_profile')
    
    # Afficher le formulaire de paiement
    context = {
        'plan': plan,
        'plan_type': plan_type,
        'is_yearly': request.GET.get('period') == 'yearly',
    }
    
    return render(request, 'foodapp/subscription/checkout.html', context)


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
def user_subscription(request):
    """Vue pour afficher l'abonnement actuel de l'utilisateur"""
    from .models import UserProfile, UserSubscription
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        user_subscription = UserSubscription.objects.filter(
            user_profile=user_profile
        ).select_related('plan').first()
        
        context = {
            'user_profile': user_profile,
            'subscription': user_subscription,
            'now': timezone.now().date()
        }
        return render(request, 'foodapp/subscription/user_subscription.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, "Profil utilisateur non trouvé.")
        return redirect('user_profile')

@login_required
def cancel_subscription(request):
    """Vue pour annuler un abonnement utilisateur"""
    from .models import UserProfile, UserSubscription
    
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            subscription = UserSubscription.objects.filter(
                user_profile=user_profile,
                status='active'
            ).first()
            
            if subscription:
                # Marquer l'abonnement comme annulé (mais le conserver pour l'historique)
                subscription.status = 'cancelled'
                subscription.cancellation_date = timezone.now()
                subscription.save()
                
                messages.success(
                    request,
                    "Votre abonnement a été annulé avec succès. "
                    "Il restera actif jusqu'à la fin de la période payée."
                )
            else:
                messages.warning(request, "Aucun abonnement actif trouvé.")
                
        except UserProfile.DoesNotExist:
            messages.error(request, "Profil utilisateur non trouvé.")
            
        return redirect('user_subscription')
    
    # Si la méthode n'est pas POST, rediriger vers la page d'abonnement
    return redirect('user_subscription')

@login_required
def update_auto_renew(request):
    """Vue pour mettre à jour le renouvellement automatique d'un abonnement"""
    from .models import UserProfile, UserSubscription
    
    if request.method == 'POST':
        try:
            auto_renew = request.POST.get('auto_renew', 'off') == 'on'
            user_profile = UserProfile.objects.get(user=request.user)
            subscription = UserSubscription.objects.filter(
                user_profile=user_profile,
                status='active'
            ).first()
            
            if subscription:
                subscription.auto_renew = auto_renew
                subscription.save()
                
                if auto_renew:
                    messages.success(request, "Le renouvellement automatique a été activé pour votre abonnement.")
                else:
                    messages.success(request, "Le renouvellement automatique a été désactivé pour votre abonnement.")
            else:
                messages.warning(request, "Aucun abonnement actif trouvé.")
                
        except UserProfile.DoesNotExist:
            messages.error(request, "Profil utilisateur non trouvé.")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue: {str(e)}")
    
    return redirect('user_subscription')

def moroccan_cuisine(request):
    """
    View to display Moroccan cuisine restaurants and dishes.
    Shows both restaurants serving Moroccan cuisine and individual Moroccan dishes.
    """
    # Get Moroccan restaurants (assuming there's a cuisine field in the Restaurant model)
    moroccan_restaurants = Restaurant.objects.filter(
        Q(cuisine__icontains='moroccan') | 
        Q(description__icontains='moroccan')
    ).distinct()
    
    # Get Moroccan dishes
    moroccan_dishes = Dish.objects.filter(
        Q(description__icontains='moroccan') |
        Q(name__icontains='tajine') |
        Q(name__icontains='couscous') |
        Q(name__icontains='pastilla')
    ).select_related('restaurant').distinct()
    
    # Get featured Moroccan dishes (for carousel or highlights)
    featured_dishes = moroccan_dishes.order_by('?')[:5]  # Random 5 dishes
    
    # Get categories specific to Moroccan cuisine
    moroccan_categories = Category.objects.filter(
        Q(name__icontains='moroccan') |
        Q(description__icontains='moroccan')
    )
    
    context = {
        'restaurants': moroccan_restaurants,
        'dishes': moroccan_dishes,
        'featured_dishes': featured_dishes,
        'categories': moroccan_categories,
        'cuisine_name': 'Moroccan',
    }
    
    return render(request, 'foodapp/cuisine/moroccan.html', context)

def get_dishes(request):
    """
    API endpoint to return a list of dishes as JSON.
    Supports filtering by various parameters:
    - restaurant_id: Filter by restaurant
    - category_id: Filter by category
    - dish_type: Filter by dish type (sweet, salty, drink)
    - origin: Filter by origin (moroccan, international, fusion)
    - is_vegetarian: Filter vegetarian dishes
    - is_vegan: Filter vegan dishes
    - is_tourist_recommended: Filter tourist recommended dishes
    - search: Search in dish name and description
    - limit: Limit number of results (default: 20)
    - offset: Offset for pagination (default: 0)
    """
    try:
        # Get query parameters
        restaurant_id = request.GET.get('restaurant_id')
        category_id = request.GET.get('category_id')
        dish_type = request.GET.get('dish_type')
        origin = request.GET.get('origin')
        is_vegetarian = request.GET.get('is_vegetarian')
        is_vegan = request.GET.get('is_vegan')
        is_tourist_recommended = request.GET.get('is_tourist_recommended')
        search = request.GET.get('search', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 items per page
        offset = int(request.GET.get('offset', 0))

        # Start with base queryset
        from .models import Dish, Restaurant, Category
        dishes = Dish.objects.select_related('restaurant', 'category', 'city')
        
        # Apply filters
        if restaurant_id:
            dishes = dishes.filter(restaurant_id=restaurant_id)
            
        if category_id:
            dishes = dishes.filter(category_id=category_id)
            
        if dish_type:
            dishes = dishes.filter(type=dish_type)
            
        if origin:
            dishes = dishes.filter(origin=origin)
            
        if is_vegetarian and is_vegetarian.lower() == 'true':
            dishes = dishes.filter(is_vegetarian=True)
            
        if is_vegan and is_vegan.lower() == 'true':
            dishes = dishes.filter(is_vegan=True)
            
        if is_tourist_recommended and is_tourist_recommended.lower() == 'true':
            dishes = dishes.filter(is_tourist_recommended=True)
            
        if search:
            dishes = dishes.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(ingredients__icontains=search) |
                Q(cultural_notes__icontains=search)
            )
        
        # Apply pagination
        total_count = dishes.count()
        dishes = dishes[offset:offset + limit]
        
        # Prepare response data
        dishes_data = []
        for dish in dishes:
            dish_data = {
                'id': dish.id,
                'name': dish.name,
                'description': dish.description,
                'price_range': dish.price_range,
                'type': dish.type,
                'origin': dish.origin,
                'is_vegetarian': dish.is_vegetarian,
                'is_vegan': dish.is_vegan,
                'is_tourist_recommended': dish.is_tourist_recommended,
                'calories': dish.calories,
                'image_url': dish.image.url if dish.image else None,
                'restaurant': {
                    'id': dish.restaurant.id if dish.restaurant else None,
                    'name': dish.restaurant.name if dish.restaurant else None,
                } if dish.restaurant else None,
                'category': {
                    'id': dish.category.id if dish.category else None,
                    'name': dish.category.name if dish.category else None,
                } if dish.category else None,
                'city': {
                    'id': dish.city.id if dish.city else None,
                    'name': dish.city.name if dish.city else None,
                } if dish.city else None,
            }
            dishes_data.append(dish_data)
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'count': len(dishes_data),
            'total_count': total_count,
            'next': f"{request.path}?{request.GET.urlencode()}&offset={offset + limit}" if offset + limit < total_count else None,
            'previous': f"{request.path}?{request.GET.urlencode()}&offset={max(0, offset - limit)}" if offset > 0 else None,
            'results': dishes_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def user_settings(request):
    """
    View for users to update their account settings.
    Handles both profile updates and password changes.
    """
    user = request.user
    
    # Handle profile update form
    profile_form = UserProfileForm(instance=user)
    password_form = PasswordChangeForm(user=user)
    
    if request.method == 'POST':
        # Check which form was submitted
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Your profile was successfully updated!')
                return redirect('user_settings')
                
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Important to keep the user logged in
                messages.success(request, 'Your password was successfully updated!')
                return redirect('user_settings')
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    
    return render(request, 'foodapp/user/settings.html', context)

def handler500(request):
    """Vue personnalisée pour les erreurs 500"""
    return render(request, '500.html', status=500)

def handler404(request, exception):
    """Vue personnalisée pour les erreurs 404"""
    return render(request, '404.html', status=404)

def get_restaurants(request):
    """
    API endpoint to return a list of restaurants as JSON.
    Supports filtering by various parameters:
    - city_id: Filter by city
    - cuisine: Filter by cuisine type
    - is_open: Filter by open status (true/false)
    - has_delivery: Filter restaurants with delivery
    - has_takeaway: Filter restaurants with takeaway
    - search: Search in restaurant name and description
    - limit: Limit number of results (default: 20)
    - offset: Offset for pagination (default: 0)
    - ordering: Field to order by (name, -name, rating, -rating, etc.)
    """
    try:
        # Get query parameters
        city_id = request.GET.get('city_id')
        cuisine = request.GET.get('cuisine')
        is_open = request.GET.get('is_open')
        has_delivery = request.GET.get('has_delivery')
        has_takeaway = request.GET.get('has_takeaway')
        search = request.GET.get('search', '').strip()
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 items per page
        offset = int(request.GET.get('offset', 0))
        ordering = request.GET.get('ordering', 'name')

        # Start with base queryset
        restaurants = Restaurant.objects.all()
        
        # Apply filters
        if city_id:
            restaurants = restaurants.filter(city_id=city_id)
            
        if cuisine:
            restaurants = restaurants.filter(Q(cuisine__icontains=cuisine) | 
                                          Q(description__icontains=cuisine))
            
        if is_open and is_open.lower() in ['true', '1', 'yes']:
            restaurants = restaurants.filter(is_open=True)
        elif is_open and is_open.lower() in ['false', '0', 'no']:
            restaurants = restaurants.filter(is_open=False)
            
        if has_delivery and has_delivery.lower() in ['true', '1', 'yes']:
            restaurants = restaurants.filter(has_delivery=True)
            
        if has_takeaway and has_takeaway.lower() in ['true', '1', 'yes']:
            restaurants = restaurants.filter(has_takeaway=True)
            
        if search:
            restaurants = restaurants.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(address__icontains=search) |
                Q(cuisine__icontains=search)
            )
        
        # Apply ordering
        if ordering.lstrip('-') in ['name', 'rating', 'created_at']:
            restaurants = restaurants.order_by(ordering)
        
        # Apply pagination
        total_count = restaurants.count()
        restaurants = restaurants[offset:offset + limit]
        
        # Prepare response data
        restaurants_data = []
        for restaurant in restaurants:
            # Calculate average rating
            avg_rating = restaurant.reviews.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0
            
            restaurant_data = {
                'id': restaurant.id,
                'name': restaurant.name,
                'description': restaurant.description,
                'address': restaurant.address,
                'phone': restaurant.phone,
                'email': restaurant.email,
                'website': restaurant.website,
                'is_open': restaurant.is_open,
                'cuisine': restaurant.cuisine,
                'average_rating': round(float(avg_rating), 1),
                'review_count': restaurant.reviews.count(),
                'image_url': restaurant.image.url if restaurant.image else None,
                'city': {
                    'id': restaurant.city.id,
                    'name': restaurant.city.name,
                } if restaurant.city else None,
                'created_at': restaurant.created_at.isoformat(),
            }
            restaurants_data.append(restaurant_data)
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'count': len(restaurants_data),
            'total_count': total_count,
            'next': f"{request.path}?{request.GET.urlencode()}&offset={offset + limit}" if offset + limit < total_count else None,
            'previous': f"{request.path}?{request.GET.urlencode()}&offset={max(0, offset - limit)}" if offset > 0 else None,
            'results': restaurants_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def login_view(request):
    """
    Vue de connexion personnalisée
    """
    # Si l'utilisateur est déjà connecté, on le redirige
    if request.user.is_authenticated:
        return redirect('index')
    
    # Gestion du formulaire de connexion
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Récupération des données du formulaire
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Authentification de l'utilisateur
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Connexion de l'utilisateur
                login(request, user)
                
                # Redirection vers la page demandée ou la page d'accueil
                next_url = request.POST.get('next', 'index')
                messages.success(request, f'Bienvenue, {user.username} !')
                return redirect(next_url)
            else:
                messages.error(request, 'Identifiants invalides. Veuillez réessayer.')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = AuthenticationForm()
        next_url = request.GET.get('next', 'index')
    
    context = {
        'form': form,
        'next': next_url if 'next_url' in locals() else request.GET.get('next', 'index'),
        'title': 'Connexion',
    }
    
    return render(request, 'registration/login.html', context)

def logout_view(request):
    """
    Vue de déconnexion personnalisée
    """
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('index')

def signup_view(request):
    """
    Vue d'inscription des utilisateurs
    """
    # Si l'utilisateur est déjà connecté, on le redirige
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Enregistrement du nouvel utilisateur
            user = form.save()
            
            # Connexion automatique après inscription
            login(request, user)
            
            # Message de succès
            messages.success(request, f'Votre compte a été créé avec succès, {user.username} !')
            
            # Redirection vers la page d'accueil ou la page demandée
            next_url = request.POST.get('next', 'index')
            return redirect(next_url)
        else:
            # Affichage des erreurs de formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()
    
    context = {
        'form': form,
        'title': 'Inscription',
        'next': request.GET.get('next', 'index')
    }
    
    return render(request, 'registration/signup.html', context)

def privacy_policy(request):
    """
    Vue pour afficher la politique de confidentialité
    """
    context = {
        'title': 'Politique de confidentialité',
        'last_updated': '26 juillet 2025',
        'company_name': 'FoodApp',
        'contact_email': 'privacy@foodapp.com',
    }
    return render(request, 'legal/privacy_policy.html', context)

def terms_of_service(request):
    """
    Vue pour afficher les conditions générales d'utilisation
    """
    context = {
        'title': 'Conditions Générales d\'Utilisation',
        'last_updated': '26 juillet 2025',
        'company_name': 'FoodApp',
        'contact_email': 'legal@foodapp.com',
    }
    return render(request, 'legal/terms_of_service.html', context)