from django import forms
from django.contrib.auth.models import User
from .models import City, Dish, Reservation, RestaurantDraft, Category, Restaurant
from django.utils import timezone
import datetime

class DishFilterForm(forms.Form):
    SORT_CHOICES = [
        ('name', 'Nom (A-Z)'),
        ('price_asc', 'Prix (croissant)'),
        ('price_desc', 'Prix (décroissant)'),
    ]
    
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, label='Trier par')
    city = forms.IntegerField(required=False, widget=forms.HiddenInput())
    type = forms.ChoiceField(choices=[('', 'All')] + Dish.TYPE_CHOICES, required=False, label="Dish Type")
    is_vegetarian = forms.BooleanField(required=False, label="Vegetarian Only")
    is_vegan = forms.BooleanField(required=False, label="Vegan Only")
    price_range = forms.MultipleChoiceField(
        choices=Dish.price_range.field.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Price Range"
    )
    bad_for_cholesterol = forms.BooleanField(
        required=False,
        label="I have cholesterol issues",
        widget=forms.CheckboxInput(attrs={'class': 'health-checkbox'})
    )
    bad_for_sugar = forms.BooleanField(
        required=False,
        label="I have diabetes",
        widget=forms.CheckboxInput(attrs={'class': 'health-checkbox'})
    )
    bad_for_lactose = forms.BooleanField(
        required=False,
        label="I am lactose intolerant",
        widget=forms.CheckboxInput(attrs={'class': 'health-checkbox'})
    )
    
class CurrencyConverterForm(forms.Form):
    CURRENCY_CHOICES = [
        ('USD', 'Dollar américain (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'Livre sterling (GBP)'),
        ('CAD', 'Dollar canadien (CAD)'),
        ('AED', 'Dirham émirati (AED)'),
        ('CHF', 'Franc suisse (CHF)'),
        ('JPY', 'Yen japonais (JPY)'),
        ('CNY', 'Yuan chinois (CNY)'),
        ('SAR', 'Riyal saoudien (SAR)'),
    ]
    
    amount = forms.DecimalField(
        label='Montant en MAD',
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    from_currency = forms.ChoiceField(
        label='Devise',
        choices=CURRENCY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ReservationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajouter des classes CSS pour le style
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Définir les dates minimales et maximales
        today = timezone.now().date()
        min_date = today
        max_date = today + datetime.timedelta(days=90)  # 3 mois à l'avance maximum
        
        self.fields['date'].widget.attrs['min'] = min_date.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs['max'] = max_date.strftime('%Y-%m-%d')
    
    class Meta:
        model = Reservation
        fields = ['name', 'email', 'phone', 'date', 'time', 'guests', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        
    def clean_date(self):
        date = self.cleaned_data.get('date')
        today = timezone.now().date()
        
        if date < today:
            raise forms.ValidationError("Vous ne pouvez pas réserver pour une date passée.")
        
        if date > today + datetime.timedelta(days=90):
            raise forms.ValidationError("Les réservations sont limitées à 3 mois à l'avance.")
        
        return date
    
    def clean_time(self):
        time = self.cleaned_data.get('time')
        date = self.cleaned_data.get('date')
        
        if date == timezone.now().date() and time < timezone.now().time():
            raise forms.ValidationError("Vous ne pouvez pas réserver pour une heure déjà passée.")
        
        # Vérifier que l'heure est dans les créneaux acceptables (exemple: 12h-14h30 et 19h-22h30)
        lunch_start = datetime.time(12, 0)
        lunch_end = datetime.time(14, 30)
        dinner_start = datetime.time(19, 0)
        dinner_end = datetime.time(22, 30)
        
        if not ((lunch_start <= time <= lunch_end) or (dinner_start <= time <= dinner_end)):
            raise forms.ValidationError("Veuillez choisir une heure pendant les services: 12h-14h30 ou 19h-22h30.")
        
        return time
    
    def clean_guests(self):
        guests = self.cleaned_data.get('guests')
        
        if guests < 1:
            raise forms.ValidationError("Le nombre de convives doit être d'au moins 1.")
        
        if guests > 20:
            raise forms.ValidationError("Pour les groupes de plus de 20 personnes, veuillez contacter directement le restaurant.")
        
        return guests

class ReservationModifyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ajouter des classes CSS pour le style
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Définir les dates minimales et maximales
        today = timezone.now().date()
        min_date = today
        max_date = today + datetime.timedelta(days=90)  # 3 mois à l'avance maximum
        
        self.fields['date'].widget.attrs['min'] = min_date.strftime('%Y-%m-%d')
        self.fields['date'].widget.attrs['max'] = max_date.strftime('%Y-%m-%d')
    
    class Meta:
        model = Reservation
        fields = ['date', 'time', 'guests', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        today = timezone.now().date()
        
        if date < today:
            raise forms.ValidationError("Vous ne pouvez pas réserver pour une date passée.")
        
        if date > today + datetime.timedelta(days=90):
            raise forms.ValidationError("Les réservations sont limitées à 3 mois à l'avance.")
        
        return date
    
    def clean_time(self):
        time = self.cleaned_data.get('time')
        date = self.cleaned_data.get('date')
        
        if date == timezone.now().date() and time < timezone.now().time():
            raise forms.ValidationError("Vous ne pouvez pas réserver pour une heure déjà passée.")
        
        # Vérifier que l'heure est dans les créneaux acceptables
        lunch_start = datetime.time(12, 0)
        lunch_end = datetime.time(14, 30)
        dinner_start = datetime.time(19, 0)
        dinner_end = datetime.time(22, 30)
        
        if not ((lunch_start <= time <= lunch_end) or (dinner_start <= time <= dinner_end)):
            raise forms.ValidationError("Veuillez choisir une heure pendant les services: 12h-14h30 ou 19h-22h30.")
        
        return time

class RestaurantAuthInfoForm(forms.Form):
    """Étape d'authentification : Nom d'utilisateur et mot de passe"""
    username = forms.CharField(
        label="Nom d'utilisateur",
        max_length=150,
        help_text="Requis. 150 caractères maximum. Lettres, chiffres et @/./+/-/_ uniquement.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choisissez un nom d\'utilisateur'})
    )
    password1 = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Créez un mot de passe'}),
        help_text="Votre mot de passe doit contenir au moins 8 caractères et ne peut pas être entièrement numérique.",
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmez votre mot de passe'}),
        strip=False,
        help_text="Entrez le même mot de passe que précédemment, pour vérification.",
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les deux mots de passe ne correspondent pas.")
        return password2

    def _post_clean(self):
        super()._post_clean()
        # Valider la force du mot de passe
        password = self.cleaned_data.get('password2')
        if password:
            try:
                from django.contrib.auth.password_validation import validate_password
                # Ne pas passer self.instance, car ce n'est pas un ModelForm
                validate_password(password)
            except forms.ValidationError as error:
                self.add_error('password2', error)

class RestaurantBasicInfoForm(forms.ModelForm):
    """Première étape : Informations de base du restaurant"""
    class Meta:
        model = RestaurantDraft
        fields = ['name', 'city', 'address', 'phone', 'email', 'website', 'description', 'capacity']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class RestaurantOwnerInfoForm(forms.ModelForm):
    """Deuxième étape : Informations sur le propriétaire"""
    class Meta:
        model = RestaurantDraft
        fields = ['owner_first_name', 'owner_last_name', 'owner_email', 'owner_phone', 'owner_id_card']
        widgets = {
            'owner_id_card': forms.FileInput(attrs={'accept': 'image/*,.pdf'})
        }

class RestaurantLegalDocsForm(forms.ModelForm):
    """Troisième étape : Documents légaux"""
    class Meta:
        model = RestaurantDraft
        fields = ['business_registration', 'food_safety_certificate', 'tax_document']
        widgets = {
            'business_registration': forms.FileInput(attrs={'accept': '.pdf'}),
            'food_safety_certificate': forms.FileInput(attrs={'accept': '.pdf'}),
            'tax_document': forms.FileInput(attrs={'accept': '.pdf'})
        }

class DishForm(forms.ModelForm):
    """Form for adding/editing dishes in the restaurant menu"""
    class Meta:
        model = Dish
        fields = [
            'name', 'description', 'price_range', 'type', 'category',
            'is_vegetarian', 'is_vegan', 'ingredients', 'preparation_steps',
            'image', 'calories', 'is_tourist_recommended'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'ingredients': forms.Textarea(attrs={'rows': 3}),
            'preparation_steps': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        restaurant = kwargs.pop('restaurant', None)
        super().__init__(*args, **kwargs)
        
        # Filter categories to only show those belonging to the restaurant
        if restaurant:
            self.fields['category'].queryset = Category.objects.filter(restaurant=restaurant)
        else:
            self.fields['category'].queryset = Category.objects.none()
        
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field_name != 'is_vegetarian' and field_name != 'is_vegan' and field_name != 'is_tourist_recommended':
                field.widget.attrs['class'] = 'form-control'
            
            # Add placeholder text
            if field_name == 'name':
                field.widget.attrs['placeholder'] = 'Nom du plat'
            elif field_name == 'description':
                field.widget.attrs['placeholder'] = 'Description détaillée du plat'
            elif field_name == 'ingredients':
                field.widget.attrs['placeholder'] = 'Liste des ingrédients, séparés par des virgules'
            elif field_name == 'preparation_steps':
                field.widget.attrs['placeholder'] = 'Étapes de préparation (une par ligne)'
            
            # Add help text
            if field_name == 'price_range':
                field.help_text = 'Niveau de prix du plat'
            elif field_name == 'calories':
                field.help_text = 'Nombre approximatif de calories par portion (optionnel)'


class CategoryForm(forms.ModelForm):
    """Form for adding/editing menu categories"""
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Nom de la catégorie'})
        self.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Description de la catégorie (optionnel)'})


class RestaurantPhotosForm(forms.ModelForm):
    """Quatrième étape : Photos et menu"""
    class Meta:
        model = RestaurantDraft
        fields = ['main_image', 'interior_image1', 'interior_image2', 'menu_sample']
        widgets = {
            'main_image': forms.FileInput(attrs={'accept': 'image/*'}),
            'interior_image1': forms.FileInput(attrs={'accept': 'image/*'}),
            'interior_image2': forms.FileInput(attrs={'accept': 'image/*'}),
            'menu_sample': forms.FileInput(attrs={'accept': '.pdf,image/*'})
        }
