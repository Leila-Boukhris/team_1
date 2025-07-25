from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from django.db.models import Count, Avg, Q

from .models import (
    RestaurantAccount, Restaurant, RestaurantAdminNote, 
    RestaurantStatusHistory, Order, Review, Dish, Category
)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_restaurant_detail(request, restaurant_id):
    """Vue détaillée d'un restaurant pour les administrateurs"""
    restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id)
    
    # Statistiques
    orders_count = Order.objects.filter(restaurant=restaurant_account.restaurant).count()
    reviews = Review.objects.filter(restaurant=restaurant_account.restaurant)
    reviews_count = reviews.count()
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] if reviews_count > 0 else 0
    
    # Plats et catégories
    dishes = Dish.objects.filter(restaurant=restaurant_account.restaurant)
    dishes_count = dishes.count()
    categories = Category.objects.filter(restaurant=restaurant_account.restaurant)
    categories_count = categories.count()
    
    # Notes administratives
    admin_notes = RestaurantAdminNote.objects.filter(restaurant_account=restaurant_account)
    
    # Historique des statuts
    status_history = RestaurantStatusHistory.objects.filter(restaurant_account=restaurant_account)
    
    # Formater l'historique pour l'affichage
    history_items = []
    for history in status_history:
        icon = 'fas fa-check' if history.new_status == 'approved' else 'fas fa-ban'
        if history.new_status == 'rejected':
            icon = 'fas fa-times'
        elif history.new_status == 'banned':
            icon = 'fas fa-user-slash'
        
        history_items.append({
            'icon': icon,
            'title': f'Statut changé de {history.get_old_status_display()} à {history.get_new_status_display()}',
            'date': history.created_at,
            'description': history.reason or 'Aucune raison fournie'
        })
    
    context = {
        'restaurant_account': restaurant_account,
        'orders_count': orders_count,
        'reviews_count': reviews_count,
        'average_rating': average_rating,
        'dishes': dishes,
        'dishes_count': dishes_count,
        'categories_count': categories_count,
        'admin_notes': admin_notes,
        'history_items': history_items,
    }
    
    return render(request, 'foodapp/admin_restaurant_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_restaurant_note(request, restaurant_id):
    """Ajouter une note administrative à un restaurant"""
    if request.method == 'POST':
        restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id)
        note_content = request.POST.get('note_content')
        
        if note_content:
            RestaurantAdminNote.objects.create(
                restaurant_account=restaurant_account,
                admin=request.user,
                content=note_content
            )
            messages.success(request, "Note ajoutée avec succès.")
        else:
            messages.error(request, "Le contenu de la note ne peut pas être vide.")
    
    return redirect('admin_restaurant_detail', restaurant_id=restaurant_id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_restaurant_status(request, restaurant_id):
    """Mettre à jour le statut d'un restaurant"""
    if request.method == 'POST':
        restaurant_account = get_object_or_404(RestaurantAccount, id=restaurant_id)
        new_status = request.POST.get('status')
        reason = request.POST.get('reason')
        
        if new_status in dict(RestaurantAccount.STATUS_CHOICES).keys():
            old_status = restaurant_account.status
            
            # Enregistrer l'historique
            RestaurantStatusHistory.objects.create(
                restaurant_account=restaurant_account,
                changed_by=request.user,
                old_status=old_status,
                new_status=new_status,
                reason=reason
            )
            
            # Mettre à jour le statut
            restaurant_account.update_status(new_status, user=request.user, reason=reason)
            
            # Envoyer un email de notification
            status_display = dict(RestaurantAccount.STATUS_CHOICES)[new_status]
            send_mail(
                f'Mise à jour du statut de votre restaurant - FoodFlex',
                f'Bonjour {restaurant_account.user.first_name},\n\n'
                f'Nous vous informons que le statut de votre restaurant "{restaurant_account.restaurant.name}" '
                f'a été mis à jour à "{status_display}".\n\n'
                f'Raison: {reason or "Aucune raison fournie"}\n\n'
                f'Pour plus d\'informations, veuillez vous connecter à votre compte.\n\n'
                f'L\'équipe FoodFlex',
                'noreply@foodflex.com',
                [restaurant_account.user.email],
                fail_silently=True,
            )
            
            messages.success(request, f"Le statut du restaurant a été mis à jour à {status_display}.")
        else:
            messages.error(request, "Statut invalide.")
    
    return redirect('admin_restaurant_detail', restaurant_id=restaurant_id)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def restaurant_lists_filtered(request):
    """Liste des restaurants avec filtres avancés"""
    status_filter = request.GET.get('status', 'all')
    city_filter = request.GET.get('city')
    date_filter = request.GET.get('date_range')
    search_query = request.GET.get('search')
    
    # Base query
    restaurants = RestaurantAccount.objects.all()
    
    # Appliquer les filtres
    if status_filter != 'all':
        if status_filter == 'pending':
            restaurants = restaurants.filter(pending_approval=True, is_active=False)
        elif status_filter == 'approved':
            restaurants = restaurants.filter(is_active=True, restaurant__is_open=True)
        elif status_filter == 'sanctioned':
            restaurants = restaurants.filter(is_active=True, restaurant__is_open=False)
        elif status_filter == 'banned':
            restaurants = restaurants.filter(is_active=False, pending_approval=False, status='banned')
        elif status_filter == 'rejected':
            restaurants = restaurants.filter(is_active=False, pending_approval=False, status='rejected')
    
    if city_filter:
        restaurants = restaurants.filter(restaurant__city__id=city_filter)
    
    if date_filter:
        if date_filter == 'today':
            restaurants = restaurants.filter(created_at__date=timezone.now().date())
        elif date_filter == 'week':
            restaurants = restaurants.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7))
        elif date_filter == 'month':
            restaurants = restaurants.filter(created_at__gte=timezone.now() - timezone.timedelta(days=30))
    
    if search_query:
        restaurants = restaurants.filter(
            Q(restaurant__name__icontains=search_query) |
            Q(restaurant__address__icontains=search_query) |
            Q(restaurant__city__name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Grouper par statut pour les statistiques
    pending_restaurants = restaurants.filter(pending_approval=True, is_active=False)
    approved_restaurants = restaurants.filter(is_active=True, restaurant__is_open=True)
    sanctioned_restaurants = restaurants.filter(is_active=True, restaurant__is_open=False)
    banned_restaurants = restaurants.filter(is_active=False, pending_approval=False, status='banned')
    rejected_restaurants = restaurants.filter(is_active=False, pending_approval=False, status='rejected')
    
    context = {
        'restaurants': restaurants,
        'pending_restaurants': pending_restaurants,
        'approved_restaurants': approved_restaurants,
        'sanctioned_restaurants': sanctioned_restaurants,
        'banned_restaurants': banned_restaurants,
        'rejected_restaurants': rejected_restaurants,
        'status_filter': status_filter,
        'city_filter': city_filter,
        'date_filter': date_filter,
        'search_query': search_query,
    }
    
    return render(request, 'foodapp/restaurant_lists_filtered.html', context)