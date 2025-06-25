import re

# Charger le contenu du fichier
with open('django_food/foodproject/foodapp/views.py', 'r') as f:
    content = f.read()

# Charger la fonction corrigée
with open('django_food/foodproject/foodapp/temp_function.py', 'r') as f:
    fixed_function = f.read()

# Localiser le début de la fonction get_dishes
pattern = r"def get_dishes\(request\):[\s\S]*?return JsonResponse\(dishes_data, safe=False\)"


# Remplacer l'ancienne fonction par la nouvelle
new_content = re.sub(pattern, fixed_function.strip(), content)

# Écrire le nouveau contenu
with open('django_food/foodproject/foodapp/views.py', 'w') as f:
    f.write(new_content)

print("Correction appliquée avec succès!") 