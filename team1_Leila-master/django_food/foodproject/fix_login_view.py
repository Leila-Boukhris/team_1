"""
Script pour corriger les problèmes d'indentation dans la fonction login_view
"""

with open('foodapp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Corriger les problèmes d'indentation dans login_view
corrected_section = """                # Vérifier si c'est un compte restaurant et rediriger en conséquence
                try:
                    if hasattr(user, 'restaurant_account') and user.restaurant_account.is_active:
                        # C'est un compte restaurant actif
                        if request.headers.get('Content-Type') == 'application/json':
                            return JsonResponse({
                                'success': True, 
                                'redirect': reverse('restaurant_dashboard'),
                                'account_type': 'restaurant'
                            }, status=200)
                        else:
                            return redirect('restaurant_dashboard')
                except:
                    pass
                
                # Compte utilisateur normal
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'success': True,
                        'account_type': 'user'
                    }, status=200)
                else:
                    return redirect('index')
            else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'errors': {'general': "Nom d'utilisateur ou mot de passe incorrect"}}, status=401)
                else:
                    # Pour les formulaires traditionnels, rediriger avec un message d'erreur
                    return render(request, 'foodapp/login.html', {
                        'error': "Nom d'utilisateur ou mot de passe incorrect"
                    })"""

# Rechercher la section à remplacer
section_to_replace = """                # Vérifier si c'est un compte restaurant et rediriger en conséquence
                try:
                    if hasattr(user, 'restaurant_account') and user.restaurant_account.is_active:
                        # C'est un compte restaurant actif
                        if request.headers.get('Content-Type') == 'application/json':
                            return JsonResponse({
                                'success': True, 
                                'redirect': reverse('restaurant_dashboard'),
                                'account_type': 'restaurant'
                            }, status=200)
                            else:
                            return redirect('restaurant_dashboard')
                except:
                    pass
                
                # Compte utilisateur normal
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'success': True,
                        'account_type': 'user'
                    }, status=200)
                    else:
                    return redirect('index')
                else:
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'errors': {'general': "Nom d'utilisateur ou mot de passe incorrect"}}, status=401)
                    else:
                    # Pour les formulaires traditionnels, rediriger avec un message d'erreur
                    return render(request, 'foodapp/login.html', {
                        'error': "Nom d'utilisateur ou mot de passe incorrect"
                    })"""

# Remplacer la section
content = content.replace(section_to_replace, corrected_section)

# Écrire le contenu corrigé dans un nouveau fichier
with open('foodapp/views_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fichier views_fixed.py créé avec la fonction login_view corrigée.") 