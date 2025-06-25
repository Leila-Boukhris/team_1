@echo off
:: FoodFlex Launcher
:: Ce script permet de lancer l'application FoodFlex facilement

echo.
echo   ███████╗ ██████╗  ██████╗ ██████╗ ███████╗██╗     ███████╗██╗  ██╗
echo   ██╔════╝██╔═══██╗██╔═══██╗██╔══██╗██╔════╝██║     ██╔════╝╚██╗██╔╝
echo   █████╗  ██║   ██║██║   ██║██║  ██║█████╗  ██║     █████╗   ╚███╔╝ 
echo   ██╔══╝  ██║   ██║██║   ██║██║  ██║██╔══╝  ██║     ██╔══╝   ██╔██╗ 
echo   ██║     ╚██████╔╝╚██████╔╝██████╔╝██║     ███████╗███████╗██╔╝ ██╗
echo   ╚═╝      ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝
echo.
echo   Cuisine Marocaine Authentique - Version 1.0.0
echo   (C) 2023 FoodFlex Team. Tous droits réservés.
echo.
echo   [DÉMARRAGE DE L'APPLICATION...]
echo.

:: Vérifier si nous sommes dans le dossier d'installation ou dans le dossier de développement
if exist dist\FoodFlex.exe (
    :: Mode développement - exécutable dans le dossier dist
    echo   [MODE DÉVELOPPEMENT]
    echo   Lancement de l'application depuis le dossier dist...
    start "" "dist\FoodFlex.exe"
) else if exist FoodFlex.exe (
    :: Mode installation - exécutable dans le même dossier
    echo   [MODE INSTALLATION]
    echo   Lancement de l'application...
    start "" "FoodFlex.exe"
) else if exist foodproject\manage.py (
    :: Mode développement - lancer via app_launcher.py
    echo   [MODE DÉVELOPPEMENT]
    echo   Démarrage de Django via le lanceur d'application...
    python app_launcher.py
) else (
    echo   [ERREUR] Impossible de trouver l'application FoodFlex.
    echo   Veuillez vous assurer que vous êtes dans le bon répertoire.
    echo.
    pause
    exit /b 1
)

echo   Application lancée avec succès !
echo   Vous pouvez fermer cette fenêtre.
timeout /t 5 /nobreak > nul 