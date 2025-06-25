import os
import sys
import subprocess
import shutil
import pkg_resources

def build_app():
    print("Préparation de la création de l'application FoodFlex...")
    
    # S'assurer que tous les répertoires nécessaires existent
    for directory in ['build', 'dist', 'logs']:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # Vérifier que PyInstaller est installé
    try:
        import PyInstaller
    except ImportError:
        print("Installation de PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Vérifier que les autres dépendances sont installées
    print("Installation des dépendances...")
    required_packages = [
        'django>=3.2.0',
        'pywebview>=3.6.0',
        'requests>=2.25.0',
        'pillow>=8.0.0',
        'django-crispy-forms>=1.10.0'
    ]
    
    # Installer les dépendances qui manquent
    for package in required_packages:
        try:
            pkg_name = package.split('>=')[0]
            pkg_resources.get_distribution(pkg_name)
            print(f"✅ {pkg_name} est déjà installé")
        except pkg_resources.DistributionNotFound:
            print(f"⚙️ Installation de {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Installer les dépendances du fichier requirements.txt si disponible
    if os.path.exists("requirements.txt"):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Préparation du fichier spec pour PyInstaller
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

excluded_modules = [
    'tkinter', 'pytest', 'numpy', 'pandas', 'matplotlib',
    'scipy', 'notebook', 'babel', 'docutils', 'sphinx',
    'jupyter', 'IPython'
]

a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('foodproject', 'foodproject'),
        ('logs', 'logs'),
    ],
    hiddenimports=[
        'django',
        'django.middleware',
        'django.template.defaulttags',
        'django.template.loader_tags',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.auth.backends',
        'django.contrib.auth.hashers',
        'django.contrib.auth.middleware',
        'django.contrib.contenttypes',
        'django.contrib.contenttypes.models',
        'django.contrib.sessions',
        'django.contrib.sessions.middleware',
        'django.contrib.messages',
        'django.contrib.messages.middleware',
        'django.contrib.staticfiles',
        'django.contrib.staticfiles.finders',
        'django.template.loader',
        'django.db.models.query',
        'django.db.models.fields',
        'django.urls.resolvers',
        'django.views.generic',
        'django.forms',
        'foodproject',
        'foodproject.foodapp',
        'foodproject.foodapp.models',
        'foodproject.foodapp.views',
        'foodproject.foodapp.urls',
        'crispy_forms',
        'webview',
        'webview.platforms.win32',
        'socket',
        'threading',
        'time',
        'subprocess',
        'requests',
        'urllib',
        'urllib.parse',
        'logging',
        'datetime',
        'signal',
        'json',
    ],
    excludes=excluded_modules,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FoodFlex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='foodproject/static/foodapp/img/favicon.ico',
    version='file_version_info.txt',
)
"""
    
    # Créer un fichier de version pour Windows
    version_file_content = """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'FoodFlex'),
        StringStruct(u'FileDescription', u'Application FoodFlex - Cuisine Marocaine'),
        StringStruct(u'FileVersion', u'1.0.0'),
        StringStruct(u'InternalName', u'FoodFlex'),
        StringStruct(u'LegalCopyright', u'© 2023 FoodFlex. Tous droits réservés.'),
        StringStruct(u'OriginalFilename', u'FoodFlex.exe'),
        StringStruct(u'ProductName', u'FoodFlex'),
        StringStruct(u'ProductVersion', u'1.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    # Écrire le fichier de version
    with open("file_version_info.txt", "w") as f:
        f.write(version_file_content)
    
    # Écrire le fichier spec
    with open("FoodFlex.spec", "w") as f:
        f.write(spec_content)
    
    # Exécuter PyInstaller pour créer une application autonome
    print("Construction de l'application avec PyInstaller...")
    try:
        subprocess.check_call([
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "FoodFlex.spec"
        ])
        
        print("✅ Construction terminée avec succès!")
        
        # Créer un fichier README pour l'installation
        readme_content = """# FoodFlex - Application Autonome

## Instructions d'installation

1. Téléchargez et décompressez le fichier zip.
2. Exécutez simplement "FoodFlex.exe" pour lancer l'application.
3. Aucune installation de Python ou d'autres dépendances n'est requise.

## Configuration système requise

- Windows 10 ou supérieur
- Au moins 4 Go de RAM
- 500 Mo d'espace disque libre

## Support

En cas de problème, veuillez contacter l'équipe de support ou consulter les logs dans le dossier 'logs'.
"""

        with open("dist/README.txt", "w", encoding="utf-8") as f:
            f.write(readme_content)
            
        # Créer un fichier batch pour le lancement facile
        launcher_content = """@echo off
echo Lancement de FoodFlex...
start "" "%~dp0FoodFlex.exe"
"""
        with open("dist/Lancer_FoodFlex.bat", "w") as f:
            f.write(launcher_content)
            
        print("\nL'application a été construite avec succès!")
        print("Vous pouvez trouver l'application dans le fichier dist/FoodFlex.exe")
        print("Un fichier batch 'Lancer_FoodFlex.bat' a également été créé pour un lancement facile.")
        print("Partagez ces fichiers avec vos utilisateurs, ils n'auront pas besoin d'installer Python.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la construction : {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(build_app()) 