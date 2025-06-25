from django.contrib import admin
from .models import (
    City, 
    Dish, 
    Restaurant, 
    Reservation, 
    RestaurantAccount, 
    UserProfile, 
    Review,
    ForumTopic,
    ForumMessage,
    RestaurantDraft
)
from django.utils.html import format_html
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.crypto import get_random_string
from django.shortcuts import redirect, render
from django.urls import path
from django import forms
from django.contrib import messages
from django.contrib.admin.widgets import AdminDateWidget
from django.core.mail import send_mail

# Register your models here.
class DishInline(admin.TabularInline):
    model = Dish
    extra = 0

class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_image', 'get_dishes_count', 'get_restaurants_count')
    search_fields = ('name',)
    inlines = [DishInline]
    
    def get_dishes_count(self, obj):
        return obj.dishes.count()
    get_dishes_count.short_description = "Nombre de plats"
    
    def get_restaurants_count(self, obj):
        return obj.restaurants.count()
    get_restaurants_count.short_description = "Nombre de restaurants"

class DishAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_image_preview', 'type', 'price_range', 'city', 'is_vegetarian', 'is_vegan', 'origin', 'is_tourist_recommended', 'is_newly_added', 'calories')
    list_filter = ('type', 'price_range', 'city', 'is_vegetarian', 'is_vegan', 'is_tourist_recommended', 'origin', 'created_at',
                  'has_sugar', 'has_cholesterol', 'has_gluten', 'has_lactose', 'has_nuts', 'is_diabetic_friendly', 'is_low_calorie')
    search_fields = ('name', 'description', 'ingredients')
    readonly_fields = ('created_at', 'viewed_by')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'description', 'type', 'price_range', 'image', 'city', 'origin')
        }),
        ('Caractéristiques', {
            'fields': ('is_vegetarian', 'is_vegan', 'is_tourist_recommended')
        }),
        ('Restrictions de santé', {
            'fields': (
                'has_sugar', 'has_cholesterol', 'has_gluten', 'has_lactose', 
                'has_nuts', 'is_diabetic_friendly', 'is_low_calorie', 'calories'
            ),
            'description': 'Informations sur les restrictions alimentaires et la santé'
        }),
        ('Détails de la recette', {
            'fields': ('ingredients', 'preparation_steps', 'history', 'cultural_notes')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'viewed_by'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_tourist_recommended', 'mark_as_vegetarian', 'mark_as_moroccan', 'mark_as_diabetic_friendly', 'mark_as_gluten_free']
    
    def is_newly_added(self, obj):
        if obj.is_new():
            return format_html('<span style="color: green; font-weight: bold;">✓</span>')
        return format_html('<span style="color: gray;">✗</span>')
    is_newly_added.short_description = "Nouveau"
    
    def mark_as_tourist_recommended(self, request, queryset):
        queryset.update(is_tourist_recommended=True)
        self.message_user(request, f"{queryset.count()} plat(s) marqué(s) comme recommandé(s) aux touristes.")
    mark_as_tourist_recommended.short_description = "Marquer comme recommandé aux touristes"
    
    def mark_as_vegetarian(self, request, queryset):
        queryset.update(is_vegetarian=True)
        self.message_user(request, f"{queryset.count()} plat(s) marqué(s) comme végétarien(s).")
    mark_as_vegetarian.short_description = "Marquer comme végétarien"
    
    def mark_as_moroccan(self, request, queryset):
        queryset.update(origin=Dish.MOROCCAN)
        self.message_user(request, f"{queryset.count()} plat(s) marqué(s) comme d'origine marocaine.")
    mark_as_moroccan.short_description = "Marquer comme cuisine marocaine"
    
    def mark_as_diabetic_friendly(self, request, queryset):
        queryset.update(is_diabetic_friendly=True, has_sugar=False)
        self.message_user(request, f"{queryset.count()} plat(s) marqué(s) comme adapté(s) aux diabétiques.")
    mark_as_diabetic_friendly.short_description = "Marquer comme adapté aux diabétiques"
    
    def mark_as_gluten_free(self, request, queryset):
        queryset.update(has_gluten=False)
        self.message_user(request, f"{queryset.count()} plat(s) marqué(s) comme sans gluten.")
    mark_as_gluten_free.short_description = "Marquer comme sans gluten"

class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 0
    fields = ('name', 'date', 'time', 'guests', 'status')
    readonly_fields = ('name', 'date', 'time', 'guests')

# Formulaire pour créer un compte restaurant
class RestaurantAccountForm(forms.ModelForm):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150, required=True, 
                              help_text="Nom d'utilisateur pour le compte restaurant")
    email = forms.EmailField(label="Email", required=True)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=True,
                              help_text="Mot de passe pour le compte restaurant")
    is_active = forms.BooleanField(label="Compte actif", initial=True, required=False)
    
    class Meta:
        model = RestaurantAccount
        fields = ('username', 'email', 'password', 'is_active')

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_image_preview', 'city', 'is_open', 'phone', 'email', 'get_reservations_count', 'has_account')
    list_filter = ('city', 'is_open')
    search_fields = ('name', 'description', 'address', 'email', 'phone')
    inlines = [ReservationInline]
    actions = ['create_restaurant_accounts']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:restaurant_id>/create-account/', 
                 self.admin_site.admin_view(self.create_account_view), 
                 name='foodapp_restaurant_create_account'),
        ]
        return custom_urls + urls
    
    def get_reservations_count(self, obj):
        return obj.reservations.count()
    get_reservations_count.short_description = "Réservations"
    
    def has_account(self, obj):
        try:
            has_account = hasattr(obj, 'account')
            if has_account:
                return format_html('<span style="color: green;">✓</span>')
            return format_html('<span style="color: red;">✗</span>')
        except:
            return format_html('<span style="color: red;">✗</span>')
    has_account.short_description = "Compte"
    
    def create_account_view(self, request, restaurant_id):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        
        if request.method == 'POST':
            form = RestaurantAccountForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                is_active = form.cleaned_data['is_active']
                
                # Vérifier si l'utilisateur existe déjà
                if User.objects.filter(username=username).exists():
                    messages.error(request, f"Un utilisateur avec le nom '{username}' existe déjà.")
                    return redirect('admin:foodapp_restaurant_create_account', restaurant_id=restaurant_id)
                
                # Créer l'utilisateur
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                
                # Créer le compte restaurant
                RestaurantAccount.objects.create(
                    user=user,
                    restaurant=restaurant,
                    is_active=is_active
                )
                
                # Créer un profil utilisateur associé
                UserProfile.objects.create(user=user)
                
                messages.success(request, f"Compte restaurant créé avec succès pour {restaurant.name}.")
                return redirect('admin:foodapp_restaurant_changelist')
        else:
            # Pré-remplir avec les informations du restaurant
            initial_data = {
                'username': restaurant.name.lower().replace(' ', '_')[:20],
                'email': restaurant.email,
                'is_active': True
            }
            form = RestaurantAccountForm(initial=initial_data)
        
        context = {
            'title': f"Créer un compte pour le restaurant: {restaurant.name}",
            'form': form,
            'restaurant': restaurant,
            'opts': self.model._meta,
            'has_permission': True,
        }
        return render(request, 'admin/foodapp/restaurant/create_account_form.html', context)
    
    def create_restaurant_accounts(self, request, queryset):
        success_count = 0
        error_count = 0
        
        for restaurant in queryset:
            # Vérifier si le restaurant a déjà un compte
            if hasattr(restaurant, 'account'):
                error_count += 1
                continue
            
            # Générer un nom d'utilisateur basé sur le nom du restaurant
            base_username = restaurant.name.lower().replace(' ', '_')[:16]
            username = base_username
            
            # Assurer que le nom d'utilisateur est unique
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Générer un mot de passe aléatoire
            password = get_random_string(12)
            
            try:
                # Créer l'utilisateur
                user = User.objects.create_user(
                    username=username,
                    email=restaurant.email,
                    password=password
                )
                
                # Créer le compte restaurant
                RestaurantAccount.objects.create(
                    user=user,
                    restaurant=restaurant,
                    is_active=True
                )
                
                # Créer un profil utilisateur
                UserProfile.objects.create(user=user)
                
                success_count += 1
            except Exception as e:
                error_count += 1
        
        if success_count:
            self.message_user(request, f"{success_count} compte(s) restaurant créé(s) avec succès.", messages.SUCCESS)
        if error_count:
            self.message_user(request, f"{error_count} restaurant(s) ont été ignorés car ils avaient déjà un compte ou une erreur s'est produite.", messages.WARNING)
    
    create_restaurant_accounts.short_description = "Créer des comptes restaurant pour les restaurants sélectionnés"

class RestaurantAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'restaurant__name')
    raw_id_fields = ('user', 'restaurant')

class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'date', 'time', 'guests', 'status', 'created_at')
    list_filter = ('status', 'date', 'restaurant')
    search_fields = ('name', 'email', 'phone', 'restaurant__name')
    readonly_fields = ('created_at', 'updated_at', 'confirmation_code')
    date_hierarchy = 'date'
    
    actions = ['mark_as_confirmed', 'mark_as_canceled', 'mark_as_completed']
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status=Reservation.STATUS_CONFIRMED)
    mark_as_confirmed.short_description = "Confirmer les réservations sélectionnées"
    
    def mark_as_canceled(self, request, queryset):
        queryset.update(status=Reservation.STATUS_CANCELED)
    mark_as_canceled.short_description = "Annuler les réservations sélectionnées"
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status=Reservation.STATUS_COMPLETED)
    mark_as_completed.short_description = "Marquer les réservations sélectionnées comme terminées"

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profil utilisateur"

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_restaurant_account')
    
    def get_restaurant_account(self, obj):
        try:
            return obj.restaurant_account.restaurant.name if hasattr(obj, 'restaurant_account') else '-'
        except:
            return '-'
    get_restaurant_account.short_description = "Compte restaurant"

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'restaurant', 'rating', 'is_published', 'created_at')
    list_filter = ('rating', 'is_published', 'restaurant')
    search_fields = ('user__username', 'restaurant__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['publish_reviews', 'unpublish_reviews']
    
    def publish_reviews(self, request, queryset):
        queryset.update(is_published=True)
    publish_reviews.short_description = "Publier les avis sélectionnés"
    
    def unpublish_reviews(self, request, queryset):
        queryset.update(is_published=False)
    unpublish_reviews.short_description = "Masquer les avis sélectionnés"

@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at', 'views_count', 'messages_count', 'is_pinned')
    list_filter = ('category', 'is_pinned', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('created_at', 'updated_at', 'views_count')
    
    def messages_count(self, obj):
        return obj.messages_count
    messages_count.short_description = "Nombre de messages"

@admin.register(ForumMessage)
class ForumMessageAdmin(admin.ModelAdmin):
    list_display = ('topic', 'author', 'created_at', 'is_solution')
    list_filter = ('is_solution', 'created_at')
    search_fields = ('content', 'author__username', 'topic__title')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(RestaurantDraft)
class RestaurantDraftAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'owner_full_name', 'status', 'created_at')
    list_filter = ('status', 'city', 'created_at')
    search_fields = ('name', 'owner_first_name', 'owner_last_name', 'email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informations du restaurant', {
            'fields': ('name', 'city', 'address', 'phone', 'email', 'website', 'description', 'capacity')
        }),
        ('Informations du propriétaire', {
            'fields': ('owner_first_name', 'owner_last_name', 'owner_email', 'owner_phone', 'owner_id_card')
        }),
        ('Documents légaux', {
            'fields': ('business_registration', 'food_safety_certificate', 'tax_document')
        }),
        ('Photos et Menu', {
            'fields': ('main_image', 'interior_image1', 'interior_image2', 'menu_sample')
        }),
        ('Statut', {
            'fields': ('status', 'admin_notes', 'created_at', 'updated_at')
        })
    )
    
    def owner_full_name(self, obj):
        return f"{obj.owner_first_name} {obj.owner_last_name}"
    owner_full_name.short_description = "Propriétaire"
    
    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data:
            if obj.status == 'approved':
                # Créer le restaurant et le compte utilisateur
                user = User.objects.create_user(
                    username=f"{obj.owner_first_name.lower()}{obj.owner_last_name.lower()}",
                    email=obj.owner_email,
                    password=get_random_string(12),  # Mot de passe temporaire
                    first_name=obj.owner_first_name,
                    last_name=obj.owner_last_name
                )
                
                restaurant = Restaurant.objects.create(
                    name=obj.name,
                    city=obj.city,
                    address=obj.address,
                    phone=obj.phone,
                    email=obj.email,
                    website=obj.website,
                    description=obj.description,
                    capacity=obj.capacity,
                    image=obj.main_image
                )
                
                RestaurantAccount.objects.create(
                    user=user,
                    restaurant=restaurant,
                    is_active=True
                )
                
                # Envoyer un email au propriétaire avec ses identifiants
                send_mail(
                    'Votre compte restaurant a été approuvé',
                    f'Félicitations ! Votre restaurant a été approuvé.\n\n'
                    f'Vous pouvez vous connecter avec les identifiants suivants :\n'
                    f'Email : {obj.owner_email}\n'
                    f'Mot de passe temporaire : {password}\n\n'
                    f'Veuillez changer votre mot de passe lors de votre première connexion.',
                    'noreply@foodflex.com',
                    [obj.owner_email],
                    fail_silently=False,
                )
                
                messages.success(request, f"Le restaurant {obj.name} a été approuvé et le compte a été créé.")
            
            elif obj.status == 'rejected':
                # Envoyer un email de rejet
                send_mail(
                    'Statut de votre demande de restaurant',
                    f'Malheureusement, votre demande pour {obj.name} n\'a pas été approuvée.\n\n'
                    f'Raison : {obj.admin_notes}\n\n'
                    f'Vous pouvez nous contacter pour plus d\'informations.',
                    'noreply@foodflex.com',
                    [obj.owner_email],
                    fail_silently=False,
                )
                
                messages.warning(request, f"Le restaurant {obj.name} a été rejeté.")
        
        super().save_model(request, obj, form, change)

# Modifier RestaurantAdmin pour ajouter l'action de changement de type de compte
class RestaurantAccountChangeTypeForm(forms.Form):
    ACCOUNT_TYPE_CHOICES = RestaurantAccount.ACCOUNT_TYPE_CHOICES
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE_CHOICES, label='Type de compte')
    featured_until = forms.DateTimeField(
        required=False, 
        widget=AdminDateWidget(attrs={'type': 'date'}),
        label='Mis en avant jusqu\'au'
    )

# Enregistrer les modèles dans l'interface d'administration
admin.site.register(City, CityAdmin)
admin.site.register(Dish, DishAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(RestaurantAccount, RestaurantAccountAdmin)
admin.site.register(Review, ReviewAdmin)

# Remplacer l'admin utilisateur par défaut
admin.site.unregister(User)
admin.site.register(User, UserAdmin) 