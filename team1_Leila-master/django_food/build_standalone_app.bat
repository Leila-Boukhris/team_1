@echo off
echo Creation de l'application autonome FoodFlex...
echo.

:: Vérification de l'existence de Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python n'est pas installé ou n'est pas dans le PATH.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    echo Assurez-vous de cocher "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

:: Exécution du script de construction
python build_app.py

:: Si la construction se termine avec succès
if %errorlevel% equ 0 (
    echo.
    echo La création de l'application autonome est terminée avec succès.
    echo L'application se trouve dans le dossier dist/.
    echo.
    echo Vous pouvez maintenant partager le fichier FoodFlex.exe avec les utilisateurs.
    echo Ils n'auront pas besoin d'installer Python ou d'autres dépendances.
) else (
    echo.
    echo Une erreur s'est produite lors de la création de l'application.
    echo Vérifiez que toutes les dépendances sont correctement installées.
)

pause 