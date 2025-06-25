# Guide de Distribution de FoodFlex

Ce document explique comment créer et distribuer une version autonome de l'application FoodFlex qui peut être exécutée sur n'importe quel ordinateur Windows, même sans Python installé.

## Étape 1 : Créer l'application autonome

1. Assurez-vous que vous avez Python installé sur votre ordinateur de développement
2. Double-cliquez sur le fichier `build_standalone_app.bat`
3. Attendez que le processus se termine (cela peut prendre plusieurs minutes)
4. Une fois terminé, vous trouverez l'application dans le dossier `dist/`

## Étape 2 : Distribuer l'application

### Option 1 : Partage direct du fichier exécutable

1. Copiez le fichier `dist/FoodFlex.exe` sur une clé USB ou partagez-le en ligne
2. Les utilisateurs peuvent simplement exécuter ce fichier sans aucune installation

### Option 2 : Créer un installateur (recommandé)

Pour une expérience utilisateur plus professionnelle, vous pouvez créer un installateur simple :

1. Téléchargez et installez [Inno Setup](https://jrsoftware.org/isdl.php)
2. Utilisez le script d'installation fourni dans ce projet ou créez-en un nouveau
3. L'installateur placera l'application dans le dossier Programme et créera un raccourci dans le menu Démarrer

## Étape 3 : Mise à jour de l'application

Pour mettre à jour l'application :

1. Mettez à jour le code source
2. Répétez le processus de création de l'application autonome
3. Distribuez la nouvelle version aux utilisateurs

## Remarques importantes

- La première exécution de l'application peut prendre plus de temps car elle décompresse les fichiers nécessaires
- Assurez-vous que le fichier `FoodFlex.exe` et tous les fichiers associés ne sont pas marqués comme "bloqués" par Windows
- Si les utilisateurs rencontrent des problèmes d'antivirus, vous devrez peut-être signer numériquement l'exécutable 