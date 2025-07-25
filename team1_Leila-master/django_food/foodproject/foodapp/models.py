from django.db import models
from django.contrib.auth.models import User
from django.utils.html import mark_safe
from django.utils import timezone
import datetime
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, related_name='categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class City(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='cities/', blank=True, null=True)
    description = models.TextField(blank=True)
    population = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def get_image(self):
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />')
        return "—"
    
    get_image.short_description = "Image"
    
    class Meta:
        verbose_name_plural = "Cities"
        ordering = ['name']

class Dish(models.Model):
    # Types de plats
    SWEET = 'sweet'
    SALTY = 'salty'
    DRINK = 'drink'
    TYPE_CHOICES = [
        (SWEET, 'Sucré'),
        (SALTY, 'Salé'),
        (DRINK, 'Boisson'),
    ]
    
    PRICE_LOW = 'L'
    PRICE_MEDIUM = 'M'
    PRICE_HIGH = 'H'
    
    PRICE_RANGE_CHOICES = [
        (PRICE_LOW, 'Abordable'),
        (PRICE_MEDIUM, 'Modéré'),
        (PRICE_HIGH, 'Premium'),
    ]
    
    # Origine culinaire
    MOROCCAN = 'moroccan'
    INTERNATIONAL = 'international'
    FUSION = 'fusion'
    ORIGIN_CHOICES = [
        (MOROCCAN, 'Marocaine'),
        (INTERNATIONAL, 'Internationale'),
        (FUSION, 'Fusion'),
    ]
    
    # Health Restrictions
    has_sugar = models.BooleanField(default=False, help_text="Contient du sucre")
    has_cholesterol = models.BooleanField(default=False, help_text="Contient du cholestérol élevé")
    has_gluten = models.BooleanField(default=False, help_text="Contient du gluten")
    has_lactose = models.BooleanField(default=False, help_text="Contient du lactose")
    has_nuts = models.BooleanField(default=False, help_text="Contient des noix/arachides")
    is_diabetic_friendly = models.BooleanField(default=False, help_text="Adapté aux diabétiques")
    is_low_calorie = models.BooleanField(default=False, help_text="Faible en calories")
    calories = models.PositiveIntegerField(null=True, blank=True, help_text="Nombre de calories par portion")
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    price_range = models.CharField(max_length=10)
    image = models.ImageField(upload_to='dishes/', null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    ingredients = models.TextField(null=True, blank=True)
    preparation_steps = models.TextField(null=True, blank=True)
    history = models.TextField(null=True, blank=True)
    city = models.ForeignKey('City', related_name='dishes', on_delete=models.SET_NULL, null=True, blank=True)
    restaurant = models.ForeignKey('Restaurant', related_name='dishes', on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey('Category', related_name='dishes', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Nouveaux champs pour l'origine culinaire et recommandations touristiques
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default=MOROCCAN)
    is_tourist_recommended = models.BooleanField(default=False, 
                                              help_text="Cochez cette case si ce plat est particulièrement recommandé aux touristes")
    cultural_notes = models.TextField(blank=True, null=True,
                                     help_text="Notes culturelles sur ce plat pour les touristes")
    
    # Champ pour la date de création du plat (pour l'icône "Nouveau")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Champ pour suivre les utilisateurs qui ont vu ce plat
    viewed_by = models.ManyToManyField(User, related_name='viewed_dishes', blank=True)

    # Champ pour identifier les plats créés via l'interface d'administration
    is_admin_created = models.BooleanField(default=True, 
                                         help_text="Indique si le plat a été créé via le panneau d'administration Django")
    
    def __str__(self):
        return self.name
    
    def is_new(self):
        """Vérifie si le plat est considéré comme nouveau (moins de 3 jours)"""
        three_days_ago = timezone.now() - datetime.timedelta(days=3)
        return self.created_at >= three_days_ago
    
    def mark_as_viewed(self, user):
        """Marque le plat comme vu par l'utilisateur"""
        if user.is_authenticated:
            self.viewed_by.add(user)
    
    def is_new_for_user(self, user):
        """Vérifie si le plat est nouveau pour cet utilisateur spécifique"""
        if not user.is_authenticated:
            return self.is_new()
        return self.is_new() and not self.viewed_by.filter(id=user.id).exists()
    
    def get_image_preview(self):
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="100" height="75" style="object-fit: cover; border-radius: 5px;" />')
        return "—"
    
    get_image_preview.short_description = "Image"

class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='restaurants')
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='restaurants/', blank=True, null=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    capacity = models.PositiveIntegerField(default=50, help_text="Capacité maximale du restaurant")

    def __str__(self):
        return f"{self.name} - {self.city.name}"

    def get_image_preview(self):
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="100" height="75" style="object-fit: cover; border-radius: 5px;" />')
        return "—"
    
    get_image_preview.short_description = "Image"
    
    @property
    def rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / reviews.count()

class RestaurantAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('basic', 'Basique'),
        ('premium', 'Premium'),
        ('gold', 'Gold'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('sanctioned', 'Sanctionné'),
        ('banned', 'Banni'),
        ('rejected', 'Rejeté'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='restaurant_account')
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name='account')
    is_active = models.BooleanField(default=False)
    pending_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Nouveaux champs pour plus de fonctionnalités
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPE_CHOICES, default='basic')
    featured_until = models.DateTimeField(null=True, blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    verification_status = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    theme_preference = models.CharField(max_length=20, default='standard')
    notification_settings = models.JSONField(default=dict, blank=True)
    
    # Nouveaux champs pour la modération
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='restaurant_status_changes')
    rejection_reason = models.TextField(blank=True, null=True)
    sanction_reason = models.TextField(blank=True, null=True)
    ban_reason = models.TextField(blank=True, null=True)
    ban_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Compte restaurant pour {self.restaurant.name}"
    
    @property
    def is_premium(self):
        return self.account_type in ['premium', 'gold']
    
    @property
    def is_featured(self):
        if not self.featured_until:
            return False
        return timezone.now() <= self.featured_until
    
    @property
    def days_since_creation(self):
        return (timezone.now().date() - self.created_at.date()).days
        
    def update_status(self, status, user=None, reason=None):
        """Met à jour le statut du restaurant avec traçabilité"""
        self.status = status
        self.status_changed_at = timezone.now()
        self.status_changed_by = user
        
        # Mettre à jour les champs spécifiques au statut
        if status == 'approved':
            self.is_active = True
            self.pending_approval = False
            self.restaurant.is_open = True
            self.restaurant.save()
        elif status == 'sanctioned':
            self.is_active = True
            self.pending_approval = False
            self.restaurant.is_open = False
            self.sanction_reason = reason
            self.restaurant.save()
        elif status == 'banned':
            self.is_active = False
            self.pending_approval = False
            self.restaurant.is_open = False
            self.ban_reason = reason
            self.restaurant.save()
        elif status == 'rejected':
            self.is_active = False
            self.pending_approval = False
            self.rejection_reason = reason
        
        self.save()

class RestaurantAdminNote(models.Model):
    """Modèle pour les notes administratives sur les restaurants"""
    restaurant_account = models.ForeignKey(RestaurantAccount, on_delete=models.CASCADE, related_name='admin_notes')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurant_notes')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note sur {self.restaurant_account.restaurant.name} par {self.admin.username}"


class RestaurantStatusHistory(models.Model):
    """Modèle pour l'historique des changements de statut des restaurants"""
    restaurant_account = models.ForeignKey(RestaurantAccount, on_delete=models.CASCADE, related_name='status_history')
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurant_status_history')
    old_status = models.CharField(max_length=20, choices=RestaurantAccount.STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=RestaurantAccount.STATUS_CHOICES)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Restaurant status histories"
    
    def __str__(self):
        return f"{self.restaurant_account.restaurant.name}: {self.old_status} → {self.new_status}"


class Reservation(models.Model):
    # Statut de réservation
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELED = 'canceled'
    STATUS_COMPLETED = 'completed'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_CONFIRMED, 'Confirmée'),
        (STATUS_CANCELED, 'Annulée'),
        (STATUS_COMPLETED, 'Terminée'),
    ]
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmation_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    
    def __str__(self):
        return f"Réservation de {self.name} au {self.restaurant.name} le {self.date} à {self.time}"
    
    def save(self, *args, **kwargs):
        # Générer un code de confirmation si nécessaire
        if not self.confirmation_code:
            import random
            import string
            # Générer un code aléatoire de 10 caractères alphanumériques
            self.confirmation_code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
        super().save(*args, **kwargs)
    
    @property
    def is_past(self):
        """Vérifie si la réservation est passée"""
        now = timezone.now()
        reservation_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return reservation_datetime < now
    
    @property
    def can_cancel(self):
        """Vérifie si la réservation peut être annulée"""
        return (
            not self.is_past and 
            self.status not in [self.STATUS_CANCELED, self.STATUS_COMPLETED]
        )
    
    @property
    def can_modify(self):
        """Vérifie si la réservation peut être modifiée"""
        if self.is_past or self.status in [self.STATUS_CANCELED, self.STATUS_COMPLETED]:
            return False
        
        # Vérifier que la réservation est au moins 24h dans le futur
        now = timezone.now()
        reservation_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return (reservation_datetime - now).total_seconds() > 24 * 3600

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    photos = models.ImageField(upload_to='reviews/', blank=True, null=True)
    
    def __str__(self):
        return f"Avis de {self.user.username} sur {self.restaurant.name} - {self.rating}/5"
    
    class Meta:
        unique_together = ('user', 'restaurant')
        ordering = ['-created_at']

class UserProfile(models.Model):
    # Informations de base
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField('À propos de moi', blank=True)
    phone = models.CharField('Téléphone', max_length=20, blank=True)
    profile_image = models.ImageField('Photo de profil', upload_to='profiles/', blank=True, null=True)
    date_of_birth = models.DateField('Date de naissance', null=True, blank=True)
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    
    # Préférences utilisateur
    preferences = models.JSONField(
        'Préférences',
        default=dict,
        blank=True,
        help_text='Préférences utilisateur (thème, notifications, etc.)'
    )
    
    # Préférences linguistiques
    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('en', 'English'),
    ]
    language = models.CharField(
        'Langue préférée',
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='fr',
        help_text='Sélectionnez votre langue préférée',
    )
    
    # Préférences alimentaires
    DIET_CHOICES = [
        ('none', 'Aucun régime spécifique'),
        ('vegetarian', 'Végétarien'),
        ('vegan', 'Végétalien/Végan'),
        ('pescatarian', 'Pescétarien'),
        ('gluten_free', 'Sans gluten'),
        ('lactose_free', 'Sans lactose'),
        ('keto', 'Cétogène (Keto)'),
        ('paleo', 'Paléo'),
        ('mediterranean', 'Méditerranéen'),
        ('other', 'Autre')
    ]
    
    # Allergies et intolérances
    ALLERGY_CHOICES = [
        ('peanuts', 'Arachides'),
        ('tree_nuts', 'Fruits à coque'),
        ('milk', 'Lait'),
        ('eggs', 'Œufs'),
        ('fish', 'Poisson'),
        ('shellfish', 'Fruits de mer'),
        ('soy', 'Soja'),
        ('wheat', 'Blé'),
        ('sesame', 'Sésame'),
        ('mustard', 'Moutarde'),
        ('celery', 'Céleri'),
        ('lupin', 'Lupin'),
        ('molluscs', 'Mollusques'),
        ('none', 'Aucune allergie connue')
    ]
    
    # Préférences de santé
    HEALTH_GOAL_CHOICES = [
        ('weight_loss', 'Perte de poids'),
        ('weight_gain', 'Prise de poids'),
        ('muscle_gain', 'Prise de masse musculaire'),
        ('maintenance', 'Maintien du poids'),
        ('heart_health', 'Santé cardiaque'),
        ('diabetes', 'Gestion du diabète'),
        ('digestive_health', 'Santé digestive'),
        ('energy', 'Plus d\'énergie'),
        ('other', 'Autre')
    ]
    
    # Champs du profil
    dietary_preference = models.CharField(
        'Régime alimentaire',
        max_length=20,
        choices=DIET_CHOICES,
        default='none',
        blank=True
    )
    
    allergies = models.JSONField(
        'Allergies alimentaires',
        default=list,
        blank=True,
        help_text='Liste des allergies de l\'utilisateur'
    )
    
    health_goals = models.JSONField(
        'Objectifs de santé',
        default=list,
        blank=True,
        help_text='Objectifs de santé de l\'utilisateur'
    )
    
    has_diabetes = models.BooleanField('Diabète', default=False)
    has_high_blood_pressure = models.BooleanField('Hypertension artérielle', default=False)
    has_high_cholesterol = models.BooleanField('Cholestérol élevé', default=False)
    has_celiac_disease = models.BooleanField('Maladie cœliaque', default=False)
    has_lactose_intolerance = models.BooleanField('Intolérance au lactose', default=False)
    
    prefers_organic = models.BooleanField('Préfère les produits bio', default=False)
    prefers_halal = models.BooleanField('Préfère la nourriture halal', default=False)
    prefers_kosher = models.BooleanField('Préfère la nourriture casher', default=False)
    avoids_gmo = models.BooleanField('Évite les OGM', default=False)
    
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', 'Sédentaire'),
        ('light', 'Légèrement actif'),
        ('moderate', 'Modérément actif'),
        ('active', 'Très actif'),
        ('extreme', 'Extrêmement actif'),
    ]
    
    activity_level = models.CharField(
        'Niveau d\'activité physique',
        max_length=20,
        choices=ACTIVITY_LEVEL_CHOICES,
        default='moderate',
        blank=True
    )
    
    WEIGHT_GOAL_CHOICES = [
        ('lose', 'Perdre du poids'),
        ('maintain', 'Maintenir mon poids'),
        ('gain', 'Prendre du poids'),
    ]
    
    weight_goal = models.CharField(
        'Objectif de poids',
        max_length=20,
        choices=WEIGHT_GOAL_CHOICES,
        default='maintain',
        blank=True
    )
    
    additional_allergies = models.TextField(
        'Allergies supplémentaires',
        blank=True,
        help_text='Décrivez toute autre allergie ou intolérance non listée ci-dessus'
    )
    
    additional_preferences = models.TextField(
        'Préférences supplémentaires',
        blank=True,
        help_text='Avez-vous d\'autres préférences ou restrictions alimentaires ?'
    )
    
    is_vegetarian = models.BooleanField('Végétarien', default=False)
    is_vegan = models.BooleanField('Végan', default=False)
    
    def __str__(self):
        return f"Profil de {self.user.username}"
    
    def get_image_preview(self):
        if self.profile_image:
            return mark_safe(f'<img src="{self.profile_image.url}" width="50" height="50" style="object-fit: cover; border-radius: 50%;" />')
        return "—"
    
    @property
    def full_name(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username
    
    @property
    def age(self):
        if self.date_of_birth:
            today = datetime.date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    @property
    def dietary_restrictions_summary(self):
        """Retourne un résumé des restrictions alimentaires pour l'affichage"""
        restrictions = []
        
        # Régime principal
        if self.dietary_preference != 'none':
            restrictions.append(dict(self.DIET_CHOICES).get(self.dietary_preference, self.dietary_preference))
        
        # Anciens champs pour la rétrocompatibilité
        if self.is_vegetarian:
            restrictions.append("Végétarien")
        if self.is_vegan:
            restrictions.append("Végan")
        
        # Allergies
        if self.allergies and 'none' not in self.allergies:
            restrictions.extend([dict(self.ALLERGY_CHOICES).get(a, a) for a in self.allergies])
        
        # Conditions de santé
        if self.has_diabetes:
            restrictions.append("Diabète")
        if self.has_high_blood_pressure:
            restrictions.append("Hypertension")
        if self.has_high_cholesterol:
            restrictions.append("Cholestérol élevé")
        
        return ", ".join(restrictions) if restrictions else "Aucune restriction spécifique"
    
    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

class ForumTopic(models.Model):
    """Modèle pour les sujets de discussion du forum"""
    CATEGORY_CHOICES = [
        ('general', 'Discussion Générale'),
        ('recipes', 'Recettes & Astuces'),
        ('restaurants', 'Restaurants'),
        ('travel', 'Voyages Culinaires'),
        ('events', 'Événements & Rencontres'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_topics', verbose_name="Auteur")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general', verbose_name="Catégorie")
    content = models.TextField(verbose_name="Contenu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")
    is_pinned = models.BooleanField(default=False, verbose_name="Épinglé")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de vues")
    
    def __str__(self):
        return self.title
    
    @property
    def messages_count(self):
        return self.messages.count()
    
    @property
    def last_activity(self):
        last_message = self.messages.order_by('-created_at').first()
        if last_message:
            return last_message.created_at
        return self.created_at
    
    class Meta:
        verbose_name = "Sujet de forum"
        verbose_name_plural = "Sujets de forum"
        ordering = ['-is_pinned', '-updated_at']

class ForumMessage(models.Model):
    """Modèle pour les messages dans les sujets du forum"""
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name='messages', verbose_name="Sujet")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_messages', verbose_name="Auteur")
    content = models.TextField(verbose_name="Contenu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")
    is_solution = models.BooleanField(default=False, verbose_name="Marqué comme solution")
    
    def __str__(self):
        return f"Message de {self.author.username} dans {self.topic.title}"
    
    class Meta:
        verbose_name = "Message de forum"
        verbose_name_plural = "Messages de forum"
        ordering = ['created_at']

class RestaurantDraft(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]

    # Restaurant Information
    name = models.CharField(max_length=100, default='')
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True)
    address = models.CharField(max_length=200, default='')
    phone = models.CharField(max_length=20, default='')
    email = models.EmailField(default='')
    website = models.URLField(blank=True)
    description = models.TextField(default='')
    capacity = models.PositiveIntegerField(default=50)
    
    # Owner Information
    owner_first_name = models.CharField(max_length=100, default='')
    owner_last_name = models.CharField(max_length=100, default='')
    owner_email = models.EmailField(default='')
    owner_phone = models.CharField(max_length=20, default='')
    owner_id_card = models.FileField(upload_to='restaurant_docs/id_cards/', null=True, blank=True)
    
    # Legal Documents
    business_registration = models.FileField(upload_to='restaurant_docs/registration/', null=True, blank=True)
    food_safety_certificate = models.FileField(upload_to='restaurant_docs/certificates/', null=True, blank=True)
    tax_document = models.FileField(upload_to='restaurant_docs/tax/', blank=True, null=True)
    
    # Restaurant Photos
    main_image = models.ImageField(upload_to='restaurant_drafts/main/', null=True, blank=True)
    interior_image1 = models.ImageField(upload_to='restaurant_drafts/interior/', null=True, blank=True)
    interior_image2 = models.ImageField(upload_to='restaurant_drafts/interior/', blank=True, null=True)
    menu_sample = models.FileField(upload_to='restaurant_drafts/menus/', null=True, blank=True)
    
    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Restaurant en attente"
        verbose_name_plural = "Restaurants en attente"

class SubscriptionPlan(models.Model):
    """Modèle pour les plans d'abonnement (restaurants et utilisateurs)"""
    PLAN_TYPE_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('user', 'Utilisateur')
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)
    price_monthly = models.DecimalField(max_digits=6, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=7, decimal_places=2)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=dict)
    is_featured = models.BooleanField(default=False)
    max_listings = models.IntegerField(default=1)  # Pour les comptes restaurant
    badge_text = models.CharField(max_length=50, blank=True, null=True)
    discount_percent = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"
    
    class Meta:
        verbose_name = "Plan d'abonnement"
        verbose_name_plural = "Plans d'abonnement"
        ordering = ['price_monthly']

class RestaurantSubscription(models.Model):
    """Modèle pour les abonnements restaurant actifs"""
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('canceled', 'Annulé'),
        ('expired', 'Expiré'),
        ('trial', 'Essai')
    ]
    
    restaurant_account = models.OneToOneField(RestaurantAccount, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_auto_renew = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Abonnement {self.plan.name} pour {self.restaurant_account.restaurant.name}"
    
    @property
    def is_active(self):
        return self.status == 'active' and self.end_date >= timezone.now().date()
    
    @property
    def days_remaining(self):
        if self.end_date < timezone.now().date():
            return 0
        return (self.end_date - timezone.now().date()).days

class UserSubscription(models.Model):
    """Modèle pour les abonnements utilisateur actifs"""
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('canceled', 'Annulé'),
        ('expired', 'Expiré'),
        ('trial', 'Essai')
    ]
    
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_auto_renew = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Abonnement {self.plan.name} pour {self.user_profile.user.username}"
    
    @property
    def is_active(self):
        return self.status == 'active' and self.end_date >= timezone.now().date()
    
    @property
    def days_remaining(self):
        if self.end_date < timezone.now().date():
            return 0
        return (self.end_date - timezone.now().date()).days

class Order(models.Model):
    """Modèle pour les commandes au restaurant"""
    STATUS_NEW = 'new'
    STATUS_PREPARING = 'preparing'
    STATUS_READY = 'ready'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAID = 'paid'
    
    STATUS_CHOICES = [
        (STATUS_NEW, 'Nouvelle'),
        (STATUS_PREPARING, 'En préparation'),
        (STATUS_READY, 'Prête'),
        (STATUS_DELIVERED, 'Livrée'),
        (STATUS_CANCELLED, 'Annulée'),
        (STATUS_PAID, 'Payée')
    ]
    
    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_ONLINE = 'online'
    
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Espèces'),
        (PAYMENT_CARD, 'Carte bancaire'),
        (PAYMENT_ONLINE, 'Paiement en ligne')
    ]
    
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    table_number = models.CharField(max_length=10, blank=True, null=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CASH)
    is_takeaway = models.BooleanField(default=False)
    order_time = models.DateTimeField(auto_now_add=True)
    delivery_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    order_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    
    def __str__(self):
        return f"Commande #{self.id} - {self.restaurant.name} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # Générer un code de commande si nécessaire
        if not self.order_code:
            import random
            import string
            # Générer un code aléatoire de 6 caractères alphanumériques
            self.order_code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        return self.status in [self.STATUS_DELIVERED, self.STATUS_PAID]
    
    @property
    def can_cancel(self):
        return self.status not in [self.STATUS_DELIVERED, self.STATUS_CANCELLED, self.STATUS_PAID]
    
    @property
    def preparation_time_minutes(self):
        if not self.delivery_time:
            return 0
        diff = self.delivery_time - self.order_time
        return int(diff.total_seconds() / 60)

class OrderItem(models.Model):
    """Éléments individuels d'une commande"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    dish = models.ForeignKey(Dish, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.quantity}x {self.dish.name} (Commande #{self.order.id})"
    
    @property
    def subtotal(self):
        return self.price * self.quantity

class ChatSession(models.Model):
    """Model for storing chat sessions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_interaction = models.DateTimeField(auto_now=True)
    selected_city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    language = models.CharField(max_length=10, choices=[('en', 'English'), ('fr', 'French')], default='en')
    context = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Chat {self.session_id} - {'Anonymous' if not self.user else self.user.username}"

class KitchenOrderStatus(models.Model):
    """Suivi de l'état des commandes en cuisine"""
    STATUS_QUEUED = 'queued'
    STATUS_PREPARING = 'preparing'
    STATUS_READY = 'ready'
    STATUS_SERVED = 'served'
    
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'En attente'),
        (STATUS_PREPARING, 'En préparation'),
        (STATUS_READY, 'Prêt à servir'),
        (STATUS_SERVED, 'Servi')
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='kitchen_status')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    estimated_prep_time = models.PositiveIntegerField(help_text="Temps estimé de préparation en minutes", null=True, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Commande #{self.order.id} - {self.get_status_display()}"
    
    class Meta:
        verbose_name = "Statut cuisine"
        verbose_name_plural = "Statuts cuisine"
        ordering = ['-updated_at']

class ChatMessage(models.Model):
    """Model for storing chat messages"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System')
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.role} message in {self.session}"
    
    class Meta:
        ordering = ['timestamp']

class ChatbotKnowledge(models.Model):
    """Model for storing chatbot knowledge base"""
    CATEGORY_CHOICES = [
        ('dish', 'Moroccan Dish'),
        ('ingredient', 'Ingredient'),
        ('etiquette', 'Food Etiquette'),
        ('fun_fact', 'Fun Fact'),
        ('market', 'Local Market'),
        ('custom', 'Custom Knowledge')
    ]
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    content_fr = models.TextField(verbose_name="French Content")
    keywords = models.CharField(max_length=500, help_text="Comma-separated keywords")
    related_dish = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True, blank=True)
    related_city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    image_url = models.URLField(blank=True, null=True)
    source = models.CharField(max_length=200, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"
    
    class Meta:
        verbose_name_plural = "Chatbot Knowledge Base"

