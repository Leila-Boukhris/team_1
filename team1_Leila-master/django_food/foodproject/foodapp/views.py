from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q, Sum, F, Case, When, IntegerField
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
import json
from django.views.decorators.http import require_POST, require_http_methods

from .models import (
    Restaurant, Dish, Reservation, Review, Category, RestaurantAccount,
    City, UserProfile, ForumTopic, ForumMessage, SubscriptionPlan,
    RestaurantSubscription, UserSubscription
)
from .forms import (
    DishFilterForm, CurrencyConverterForm, ReservationForm,
    ReservationModifyForm, RestaurantForm, DishForm, ReviewForm, CategoryForm
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
                'main_image': 'main_image',
                'interior_image1': 'interior_image1',
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
                'Authentification',
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
        # Récupérer d'abord les données d'authentification séparément
        auth_data = self.get_cleaned_data_for_step('auth_info')
        
        # Combiner les données des autres formulaires, en excluant les champs d'authentification
        restaurant_data = {}
        auth_fields = {'username', 'password1', 'password2'}
        
        for form in form_list:
            # Ne pas inclure les champs d'authentification dans restaurant_data
            form_data = {k: v for k, v in form.cleaned_data.items() 
                        if k not in auth_fields}
            restaurant_data.update(form_data)
        
        try:
            # Ajout de logs pour debug
            print("Début de création du compte restaurant...")
            
            # Créer le brouillon du restaurant avec les données nettoyées
            restaurant_draft = RestaurantDraft.objects.create(**restaurant_data)
            print(f"Brouillon de restaurant créé avec ID: {restaurant_draft.id}")
            
            # Création du compte utilisateur avec les informations fournies
            user = User.objects.create_user(
                username=auth_data['username'],
                email=restaurant_draft.owner_email,
                password=auth_data['password1'],
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
                args=(restaurant.id, restaurant_draft.owner_email, restaurant_draft.owner_first_name, auth_data['username'], auth_data['password1'])
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