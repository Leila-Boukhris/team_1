@echo off
echo Démarrage de FoodFlex...
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

:: Vérification des dépendances
python -c "import webview" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installation des dépendances...
    pip install -r requirements.txt
)

:: Lancement de l'application
python app_launcher.py

:: Si l'application se ferme avec une erreur
if %errorlevel% neq 0 (
    echo.
    echo Une erreur s'est produite lors du lancement de l'application.
    echo Vérifiez que toutes les dépendances sont correctement installées.
    pause
) 