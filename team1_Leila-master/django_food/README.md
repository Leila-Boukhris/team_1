# FoodFlex - Application de Cuisine Marocaine

FoodFlex est une application de service de restauration marocaine permettant aux utilisateurs de découvrir, commander et profiter de la cuisine marocaine authentique. Elle permet également aux propriétaires de restaurants de gérer leurs menus, leurs commandes et leur présence en ligne.

## Conversion en Application Native

Ce projet inclut des scripts permettant de convertir l'application web Django en une application de bureau native qui s'exécute sans navigateur web visible.

### Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Installation des dépendances

```bash
cd django_food
pip install -r requirements.txt
```

### Lancement de l'application en mode développement

```bash
cd django_food
python app_launcher.py
```

Ce script démarre un serveur Django en arrière-plan et affiche l'application dans une fenêtre native.

### Création d'un exécutable

Pour créer un exécutable Windows standalone :

```bash
cd django_food
python build_app.py
```

Cette commande créera un dossier `dist/FoodFlex` contenant l'application complète. Vous pouvez lancer l'application en exécutant `FoodFlex.exe`.

## Fonctionnalités de l'Application

- **Pour les utilisateurs** :
  - Inscription et connexion
  - Parcourir les restaurants et menus
  - Commander des plats
  - Réserver une table
  - Personnaliser les paramètres utilisateur

- **Pour les restaurants** :
  - Gestion du profil restaurant
  - Création et gestion des menus
  - Gestion des commandes en temps réel
  - Visualisation des statistiques

## Architecture

L'application est construite avec:
- **Backend**: Django (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Application Native**: PyWebView 