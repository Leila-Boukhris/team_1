"""
Script pour corriger les problèmes d'indentation dans le fichier views.py
"""
import re

def fix_indentation_issues(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.readlines()

    # Corriger les problèmes d'indentation
    fixed_content = []
    in_get_dishes = False
    in_reservation = False
    in_signup = False
    in_dashboard = False
    for line in content:
        # Problème 1: Indentation dans get_dishes
        if 'def get_dishes(request):' in line:
            in_get_dishes = True
        elif in_get_dishes and '    for dish in dishes:' in line:
            line = line.replace('    for dish in dishes:', '        for dish in dishes:')
        elif in_get_dishes and 'return JsonResponse' in line:
            in_get_dishes = False

        # Problème 2: Indentation dans reservation
        if 'def reservation(request, restaurant_id):' in line:
            in_reservation = True
        elif in_reservation and '            if request.user.is_authenticated:' in line:
            # Pas de changement nécessaire
            pass
        elif in_reservation and '                    reservation_obj.user = request.user' in line:
            line = line.replace('                    reservation_obj.user = request.user', '                reservation_obj.user = request.user')
        elif in_reservation and '                reservation_obj.save()' in line:
            # Pas de changement nécessaire
            pass
        elif in_reservation and '            success = True' in line:
            line = line.replace('            success = True', '                success = True')
        elif in_reservation and '            else:' in line:
            line = line.replace('            else:', '                else:')
        elif in_reservation and 'return render(request, ' in line:
            in_reservation = False

        # Problème 3: Indentation dans restaurant_signup_view
        if 'def restaurant_signup_view(request):' in line:
            in_signup = True
        elif in_signup and '                username_exists = User.objects.filter(username=username).exists()' in line:
            line = line.replace('                username_exists = User.objects.filter(username=username).exists()', '            username_exists = User.objects.filter(username=username).exists()')
        elif in_signup and '                email_exists = User.objects.filter(email=email).exists()' in line:
            line = line.replace('                email_exists = User.objects.filter(email=email).exists()', '            email_exists = User.objects.filter(email=email).exists()')
        elif in_signup and 'return render(request, ' in line:
            in_signup = False

        fixed_content.append(line)

    # Écrire le contenu corrigé
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_content)

    print(f"Fichier {file_path} corrigé avec succès!")

if __name__ == "__main__":
    fix_indentation_issues('foodapp/views.py') 