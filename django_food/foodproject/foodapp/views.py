class RestaurantRegistrationWizard(SessionWizardView):
    FORMS = [
        ("basic_info", RestaurantBasicInfoForm),
        ("owner_info", RestaurantOwnerInfoForm),
        ("legal_docs", RestaurantLegalDocsForm),
        ("photos", RestaurantPhotosForm),
    ]

    # Configuration des fichiers
    ALLOWED_EXTENSIONS = {
        'owner_id_card': ['.jpg', '.jpeg', '.png', '.pdf'],
        'business_registration': ['.pdf'],
        'food_safety_certificate': ['.pdf'],
        'tax_document': ['.pdf'],
        'main_image': ['.jpg', '.jpeg', '.png'],
        'interior_image1': ['.jpg', '.jpeg', '.png'],
        'interior_image2': ['.jpg', '.jpeg', '.png'],
        'menu_sample': ['.jpg', '.jpeg', '.png', '.pdf']
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp_uploads'))
    
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
            ],
            'allowed_extensions': self.ALLOWED_EXTENSIONS,
            'max_file_size': self.MAX_FILE_SIZE
        })
        return context
    
    def clean_file(self, file, field_name):
        """Valide un fichier uploadé"""
        if not file:
            return None
            
        # Vérifier l'extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS.get(field_name, []):
            raise forms.ValidationError(
                f"Type de fichier non autorisé. Extensions autorisées : {', '.join(self.ALLOWED_EXTENSIONS[field_name])}"
            )
            
        # Vérifier la taille
        if file.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError(
                f"Le fichier est trop volumineux. Taille maximum : {self.MAX_FILE_SIZE / (1024*1024)}MB"
            )
            
        return file
    
    def process_step(self, form):
        """Traite chaque étape du formulaire"""
        cleaned_data = super().process_step(form)
        
        # Valider les fichiers si présents
        for field_name, field_value in cleaned_data.items():
            if field_name in self.ALLOWED_EXTENSIONS and field_value:
                try:
                    cleaned_data[field_name] = self.clean_file(field_value, field_name)
                except forms.ValidationError as e:
                    form.add_error(field_name, e)
                    raise
        
        return cleaned_data
    
    def done(self, form_list, **kwargs):
        """Finalise l'inscription"""
        try:
            # Combiner les données de tous les formulaires
            restaurant_data = {}
            for form in form_list:
                restaurant_data.update(form.cleaned_data)
            
            # Créer le brouillon de restaurant
            restaurant_draft = RestaurantDraft.objects.create(**restaurant_data)
            
            # Nettoyer les fichiers temporaires
            self.clean_temp_files()
            
            # Envoyer une notification aux administrateurs
            self.notify_admins(restaurant_draft)
            
            # Envoyer un email de confirmation au restaurant
            self.send_confirmation_email(restaurant_draft)
            
            messages.success(
                self.request,
                'Votre demande a été soumise avec succès ! Nous l\'examinerons dans les plus brefs délais.'
            )
            return redirect('restaurant_pending_approval')
            
        except Exception as e:
            messages.error(
                self.request,
                'Une erreur est survenue lors de la soumission de votre demande. '
                'Veuillez vérifier vos informations et réessayer.'
            )
            return redirect('restaurant_register')
    
    def clean_temp_files(self):
        """Nettoie les fichiers temporaires"""
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f'Erreur lors de la suppression du fichier {file_path}: {e}')
    
    def notify_admins(self, restaurant_draft):
        """Envoie une notification aux administrateurs"""
        admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
        if admin_emails:
            send_mail(
                'Nouvelle demande de restaurant à valider',
                f'Un nouveau restaurant "{restaurant_draft.name}" attend votre approbation.\n\n'
                f'Propriétaire : {restaurant_draft.owner_first_name} {restaurant_draft.owner_last_name}\n'
                f'Email : {restaurant_draft.owner_email}\n'
                f'Téléphone : {restaurant_draft.owner_phone}',
                settings.DEFAULT_FROM_EMAIL,
                list(admin_emails),
                fail_silently=True,
            )
    
    def send_confirmation_email(self, restaurant_draft):
        """Envoie un email de confirmation au restaurant"""
        send_mail(
            'Demande d\'inscription reçue - FoodFlex',
            f'Bonjour {restaurant_draft.owner_first_name},\n\n'
            f'Nous avons bien reçu votre demande d\'inscription pour le restaurant "{restaurant_draft.name}".\n'
            f'Notre équipe va examiner votre dossier dans les plus brefs délais.\n\n'
            f'Vous recevrez un email dès que votre compte sera validé.\n\n'
            f'Cordialement,\n'
            f'L\'équipe FoodFlex',
            settings.DEFAULT_FROM_EMAIL,
            [restaurant_draft.owner_email],
            fail_silently=True,
        ) 