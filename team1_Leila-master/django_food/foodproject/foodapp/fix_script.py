with open('views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Corriger les problèmes d'indentation
content = content.replace('            for dish in dishes:', '        for dish in dishes:')
content = content.replace('                    reservation_obj.user = request.user', '                reservation_obj.user = request.user')
content = content.replace('            success = True', '                success = True')
content = content.replace('            else:', '                else:')
content = content.replace('                username_exists = User.objects.filter(username=username).exists()', '            username_exists = User.objects.filter(username=username).exists()')
content = content.replace('                email_exists = User.objects.filter(email=email).exists()', '            email_exists = User.objects.filter(email=email).exists()')

with open('views_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fichier corrigé créé: views_fixed.py') 