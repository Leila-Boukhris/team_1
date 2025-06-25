import os
import sys
import threading
import time
import subprocess
import webview
import socket
import signal
import json
import logging
import requests
from urllib.parse import urlparse
from datetime import datetime

# Configuration du logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f'foodflex_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FoodFlex')

# Variable globale pour garder une référence au processus du serveur
django_process = None

# Fonction pour vérifier si le port est disponible
def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

# Fonction pour vérifier si le serveur Django répond
def is_server_running(url, max_retries=30, delay=1):
    """Vérifie si le serveur Django est opérationnel en envoyant des requêtes."""
    parsed_url = urlparse(url)
    health_url = f"{parsed_url.scheme}://{parsed_url.netloc}/admin/login/"
    
    logger.info(f"Vérification de l'état du serveur à {health_url}")
    
    for i in range(max_retries):
        try:
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                logger.info(f"Serveur opérationnel après {i+1} tentatives")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(delay)
    
    logger.error(f"Serveur non disponible après {max_retries} tentatives")
    return False

# Fonction pour démarrer le serveur Django en arrière-plan
def start_django_server():
    global django_process
    
    # Recherche d'un port disponible
    port = 8000
    while not is_port_available(port):
        port += 1
        if port > 8100:  # Limite à 100 tentatives
            logger.error("Impossible de trouver un port disponible")
            return None, None
    
    logger.info(f"Démarrage du serveur Django sur le port {port}")
    
    # Définir l'environnement pour fonctionner sans navigateur
    os.environ['DJANGO_SETTINGS_MODULE'] = 'foodproject.settings'
    
    # Chemin vers le répertoire du projet Django
    django_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'foodproject')
    
    # Démarrer le serveur Django avec le port sélectionné
    cmd = [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload']
    
    try:
        # Lancer le processus
        django_process = subprocess.Popen(
            cmd,
            cwd=django_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW  # Cache la fenêtre de console sous Windows
        )
        
        logger.info(f"Serveur Django démarré avec PID {django_process.pid}")
        
        # Vérifier que le processus a bien démarré
        if django_process.poll() is not None:
            stderr = django_process.stderr.read().decode('utf-8', errors='ignore')
            logger.error(f"Erreur au démarrage du serveur Django: {stderr}")
            return None, None
            
        return django_process, port
    except Exception as e:
        logger.error(f"Exception lors du démarrage du serveur: {str(e)}")
        return None, None

def create_window(url, title="FoodFlex - Cuisine Marocaine"):
    # Créer la fenêtre principale avec les contrôles natifs de Windows
    logger.info(f"Création de la fenêtre principale avec URL: {url}")
    window = webview.create_window(
        title, 
        url, 
        width=1200, 
        height=800,
        frameless=False,         # Utiliser le cadre système natif avec boutons de contrôle
        easy_drag=False,         # Désactiver le drag personnalisé
        fullscreen=False,
        min_size=(800, 600),     # Taille minimale de la fenêtre
        confirm_close=True       # Demander confirmation à la fermeture
    )
    
    # Ajouter un événement lors de la fermeture pour arrêter le serveur
    @window.events.closed
    def on_closed():
        cleanup()
    
    return window

def cleanup():
    """Nettoie les ressources et arrête le serveur Django."""
    global django_process
    
    logger.info("Nettoyage des ressources...")
    
    if django_process:
        logger.info(f"Arrêt du serveur Django (PID: {django_process.pid})...")
        try:
            # Envoyer un signal SIGTERM pour arrêter proprement le processus
            if hasattr(signal, 'SIGTERM'):
                os.kill(django_process.pid, signal.SIGTERM)
            else:
                django_process.terminate()
                
            # Attendre que le processus se termine (avec timeout)
            django_process.wait(timeout=5)
            logger.info("Serveur Django arrêté avec succès")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout en attendant l'arrêt du serveur, fermeture forcée")
            django_process.kill()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du serveur: {str(e)}")

def show_error_and_exit(message):
    """Affiche une fenêtre d'erreur et quitte l'application."""
    error_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                background-color: #141414;
                color: white;
                font-family: 'Poppins', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                overflow: hidden;
            }}
            .error-container {{
                text-align: center;
                max-width: 80%;
            }}
            .error-title {{
                font-size: 24px;
                font-weight: 700;
                color: #ff6b6b;
                margin-bottom: 20px;
            }}
            .error-message {{
                font-size: 16px;
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 30px;
                line-height: 1.5;
            }}
            .error-button {{
                background-color: #ff6b6b;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-title">Erreur de démarrage</div>
            <div class="error-message">{message}</div>
            <button class="error-button" onclick="window.pywebview.api.exit()">Fermer l'application</button>
        </div>
        
        <script>
            // Mettre à jour la taille du texte d'erreur en fonction de sa longueur
            document.addEventListener('DOMContentLoaded', function() {{
                const messageEl = document.querySelector('.error-message');
                if (messageEl.textContent.length > 300) {{
                    messageEl.style.fontSize = '14px';
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    # Créer une API pour permettre au bouton de fermer l'application
    class CloseAPI:
        def exit(self):
            cleanup()
            sys.exit(1)
    
    window = webview.create_window('FoodFlex - Erreur', html=error_html, width=500, height=300, resizable=False, frameless=True, easy_drag=True)
    webview.start(debug=False, gui='system', func=lambda: None, http_server=False, user_agent=None, api=CloseAPI())

if __name__ == '__main__':
    logger.info("Démarrage de l'application FoodFlex")
    
    # Afficher un écran de démarrage pendant le chargement
    splash_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @keyframes gradient {
                0% {background-position: 0% 50%;}
                50% {background-position: 100% 50%;}
                100% {background-position: 0% 50%;}
            }
            
            body {
                background: linear-gradient(-45deg, #1a1a1a, #222, #333, #222);
                background-size: 400% 400%;
                animation: gradient 15s ease infinite;
                color: white;
                font-family: 'Poppins', Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                overflow: hidden;
            }
            .splash-container {
                text-align: center;
                position: relative;
            }
            .logo {
                font-size: 48px;
                font-weight: 800;
                background: linear-gradient(45deg, #ff6b6b, #ffb347);
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 20px;
                position: relative;
                display: inline-block;
            }
            .logo::after {
                content: '';
                position: absolute;
                width: 0%;
                height: 3px;
                bottom: -5px;
                left: 0;
                background: linear-gradient(45deg, #ff6b6b, #ffb347);
                animation: expand 2s ease-in-out infinite;
            }
            @keyframes expand {
                0% {width: 0%;}
                50% {width: 100%;}
                100% {width: 0%;}
            }
            .tagline {
                font-size: 18px;
                color: rgba(255, 255, 255, 0.7);
                margin-bottom: 40px;
            }
            .progress {
                width: 250px;
                height: 6px;
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                overflow: hidden;
                margin: 0 auto;
            }
            .progress-bar {
                height: 100%;
                width: 0%;
                background: linear-gradient(90deg, #ff6b6b, #ffb347);
                animation: progress 15s ease forwards;
                border-radius: 3px;
            }
            @keyframes progress {
                0% {width: 0%;}
                10% {width: 10%;}
                20% {width: 25%;}
                30% {width: 40%;}
                40% {width: 50%;}
                60% {width: 60%;}
                80% {width: 80%;}
                100% {width: 100%;}
            }
            .status {
                margin-top: 15px;
                color: rgba(255, 255, 255, 0.5);
                font-size: 14px;
                font-style: italic;
            }
            .footer {
                position: absolute;
                bottom: -80px;
                left: 0;
                right: 0;
                text-align: center;
                font-size: 12px;
                color: rgba(255, 255, 255, 0.4);
            }
        </style>
    </head>
    <body>
        <div class="splash-container">
            <div class="logo">FoodFlex</div>
            <div class="tagline">Cuisine Marocaine Authentique</div>
            <div class="progress"><div class="progress-bar"></div></div>
            <div class="status">Initialisation des services...</div>
            <div class="footer">© 2023 FoodFlex - Tous droits réservés</div>
        </div>
        
        <script>
            // Mise à jour dynamique du statut
            const statusMessages = [
                "Initialisation des services...",
                "Préparation des ressources...",
                "Démarrage du serveur...",
                "Chargement de l'application...",
                "Presque prêt..."
            ];
            
            const statusElement = document.querySelector('.status');
            let currentIndex = 0;
            
            setInterval(() => {
                currentIndex = (currentIndex + 1) % statusMessages.length;
                statusElement.textContent = statusMessages[currentIndex];
            }, 2500);
        </script>
    </body>
    </html>
    """
    
    # Créer d'abord une fenêtre avec le splash screen
    splash_window = webview.create_window('FoodFlex - Démarrage', html=splash_html, width=600, height=400, resizable=False, frameless=True, easy_drag=True)
    
    # Variable pour stocker la fenêtre principale
    main_window = None
    
    def on_loaded():
        # Cette fonction est appelée une fois que la fenêtre de splash est chargée
        def startup():
            global main_window
            
            # Démarrer le serveur Django
            process, port = start_django_server()
            
            # Vérifier si le serveur a bien démarré
            if not process or not port:
                splash_window.destroy()
                show_error_and_exit("Le serveur Django n'a pas pu démarrer. Veuillez vérifier le fichier journal pour plus d'informations.")
                return
            
            url = f"http://127.0.0.1:{port}/accueil/"
            
            # Vérifier si le serveur répond
            if not is_server_running(url):
                splash_window.destroy()
                show_error_and_exit("Le serveur Django a démarré mais ne répond pas. Veuillez vérifier le fichier journal pour plus d'informations.")
                return
            
            # Créer la fenêtre principale
            main_window = create_window(url)
            
            # Fermer la fenêtre de splash après un court délai
            def close_splash():
                try:
                    splash_window.destroy()
                except Exception:
                    pass  # Ignorer les erreurs si la fenêtre est déjà fermée
            
            threading.Timer(2.5, close_splash).start()
        
        # Démarrer le processus de démarrage dans un thread séparé
        threading.Thread(target=startup).start()
    
    # Définir le rappel lorsque la fenêtre de splash est chargée
    splash_window.events.loaded += on_loaded
    
    try:
        # Démarrer l'application avec l'interface système native
        webview.start(debug=False, gui='system')
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de l'application: {str(e)}")
        cleanup()
    finally:
        logger.info("Application terminée") 