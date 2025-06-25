from django import forms
from .models import City, Dish, Reservation, RestaurantDraft
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
