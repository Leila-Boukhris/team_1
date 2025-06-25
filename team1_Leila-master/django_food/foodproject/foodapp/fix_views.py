# Script pour corriger les problèmes d'indentation dans views.py
with open('views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Corriger les problèmes d'indentation
# 1. Problème dans la fonction get_dishes
content = content.replace('            for dish in dishes:', '        for dish in dishes:')

# 2. Problème dans la fonction reservation
content = content.replace('                    reservation_obj.user = request.user', '                reservation_obj.user = request.user')
content = content.replace('                reservation_obj.save()', '                reservation_obj.save()')
content = content.replace('            success = True', '                success = True')
content = content.replace('            else:', '            else:')

# 3. Problème dans la fonction restaurant_signup_view
content = content.replace('                username_exists = User.objects.filter(username=username).exists()', '            username_exists = User.objects.filter(username=username).exists()')
content = content.replace('                email_exists = User.objects.filter(email=email).exists()', '            email_exists = User.objects.filter(email=email).exists()')

# Écrire le contenu corrigé dans un nouveau fichier
with open('views_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fichier corrigé créé: views_fixed.py") 