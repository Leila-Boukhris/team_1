from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q, Sum, F, Case, When, IntegerField
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
import json
import os
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings

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

from .models import (
    Restaurant, Dish, Reservation, Review, Category, RestaurantAccount,
    City, UserProfile, ForumTopic, ForumMessage, SubscriptionPlan,
    RestaurantSubscription, UserSubscription
)
from .forms import (
    DishFilterForm, CurrencyConverterForm, ReservationForm,
    ReservationModifyForm, RestaurantBasicInfoForm, DishForm, CategoryForm
)

def is_restaurant_owner(user, restaurant_id):
    """Check if the user is the owner of the restaurant"""
    if not user.is_authenticated:
        return False
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
        return restaurant.account.user == user
    except (Restaurant.DoesNotExist, RestaurantAccount.DoesNotExist):
        return False

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
    FORMS = [
        ("basic_info", RestaurantBasicInfoForm),
        ("dish", DishForm),
        ("category", CategoryForm),
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
        'revenue': today_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
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