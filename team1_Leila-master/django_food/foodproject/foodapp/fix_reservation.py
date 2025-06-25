with open('views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher la fonction reservation
in_reservation = False
reservation_start = 0
reservation_end = 0

for i, line in enumerate(lines):
    if 'def reservation(request, restaurant_id):' in line:
        in_reservation = True
        reservation_start = i
    elif in_reservation and line.strip().startswith('def '):
        reservation_end = i
        break

if reservation_end == 0:  # Si on n'a pas trouvé la fin, prendre tout le reste du fichier
    reservation_end = len(lines)

# Remplacer la fonction reservation par une version corrigée
corrected_reservation = '''def reservation(request, restaurant_id):
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
'''

# Créer le nouveau contenu du fichier
new_content = ''.join(lines[:reservation_start]) + corrected_reservation + ''.join(lines[reservation_end:])

# Écrire le contenu corrigé dans un nouveau fichier
with open('views_reservation_fixed.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fonction reservation corrigée dans views_reservation_fixed.py") 