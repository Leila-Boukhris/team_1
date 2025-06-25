from django.core.management.base import BaseCommand
from foodapp.models import Dish, City
from django.core.files import File
from django.conf import settings
import os
import random

class Command(BaseCommand):
    help = 'Crée des plats marocains authentiques dans la base de données'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='Nombre de plats à créer')

    def handle(self, *args, **options):
        count = options['count']
        
        # Liste des villes marocaines
        cities = City.objects.filter(name__in=['Marrakech', 'Fès', 'Rabat', 'Casablanca', 'Essaouira', 'Tanger'])
        if not cities.exists():
            self.stdout.write(self.style.WARNING('Aucune ville marocaine trouvée. Création de villes...'))
            cities = self._create_moroccan_cities()
        
        # Création des plats
        created_count = 0
        for dish_data in self.get_moroccan_dishes_data():
            if created_count >= count:
                break
                
            # Attribuer une ville aléatoire
            city = random.choice(cities)
            
            # Créer le plat
            dish = Dish(
                name=dish_data['name'],
                description=dish_data['description'],
                price_range=dish_data['price_range'],
                type=dish_data['type'],
                is_vegetarian=dish_data['is_vegetarian'],
                is_vegan=dish_data['is_vegan'],
                ingredients=dish_data['ingredients'],
                preparation_steps=dish_data['preparation_steps'],
                history=dish_data['history'],
                city=city,
                origin=Dish.MOROCCAN,
                is_tourist_recommended=dish_data['is_tourist_recommended'],
                cultural_notes=dish_data['cultural_notes']
            )
            dish.save()
            
            self.stdout.write(self.style.SUCCESS(f'Plat créé: {dish.name}'))
            created_count += 1
            
        self.stdout.write(self.style.SUCCESS(f'{created_count} plats marocains ont été créés avec succès!'))
    
    def _create_moroccan_cities(self):
        """Crée des villes marocaines si elles n'existent pas"""
        cities_data = [
            {'name': 'Marrakech', 'description': 'La ville rouge, connue pour sa médina et ses souks colorés'},
            {'name': 'Fès', 'description': 'La plus ancienne des villes impériales avec sa médina médiévale'},
            {'name': 'Rabat', 'description': 'La capitale administrative du Maroc'},
            {'name': 'Casablanca', 'description': 'La plus grande ville du Maroc et son centre économique'},
            {'name': 'Essaouira', 'description': 'Ville portuaire et artistique sur la côte atlantique'},
            {'name': 'Tanger', 'description': 'Porte d\'entrée de l\'Afrique, située sur le détroit de Gibraltar'}
        ]
        
        cities = []
        for city_data in cities_data:
            city, created = City.objects.get_or_create(
                name=city_data['name'],
                defaults={'description': city_data['description']}
            )
            cities.append(city)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Ville créée: {city.name}'))
                
        return cities
    
    def get_moroccan_dishes_data(self):
        """Renvoie des données pour des plats marocains authentiques"""
        return [
            {
                'name': 'Tajine d\'agneau aux pruneaux',
                'description': 'Un plat mijoté traditionnel combinant la viande d\'agneau tendre avec des pruneaux sucrés et des épices.',
                'price_range': 'M',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Épaule d\'agneau, pruneaux, amandes, oignons, miel, cannelle, gingembre, safran, huile d\'olive',
                'preparation_steps': '1. Faire revenir la viande avec les épices\n2. Ajouter les oignons et faire mijoter\n3. Incorporer les pruneaux et le miel\n4. Cuire à feu doux pendant 2-3 heures',
                'history': 'Le tajine tire son nom du plat en terre cuite dans lequel il est traditionnellement préparé. Cette méthode de cuisson lente permet aux saveurs de se développer pleinement.',
                'is_tourist_recommended': True,
                'cultural_notes': 'Le tajine est souvent servi lors des grandes occasions et partagé dans un plat commun, symbolisant la convivialité marocaine.'
            },
            {
                'name': 'Couscous Royal',
                'description': 'Le plat national marocain par excellence, composé de semoule de blé vapeur accompagnée de légumes et de viandes variées.',
                'price_range': 'M',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Semoule de blé, agneau, poulet, merguez, carottes, courgettes, navets, pois chiches, oignons, tomates, ras el hanout',
                'preparation_steps': '1. Préparer le bouillon avec les viandes et les épices\n2. Cuire les légumes dans le bouillon\n3. Cuire la semoule à la vapeur\n4. Servir la semoule avec les légumes et les viandes, arrosée de bouillon',
                'history': 'Traditionnellement servi le vendredi après la prière, le couscous est un plat emblématique de l\'Afrique du Nord.',
                'is_tourist_recommended': True,
                'cultural_notes': 'Le couscous est généralement servi le vendredi, jour sacré pour les musulmans, et symbolise le partage et la générosité.'
            },
            {
                'name': 'Pastilla au Pigeon',
                'description': 'Un mélange sucré-salé enveloppé dans une fine pâte filo, garni de pigeon, d\'amandes et saupoudré de sucre et de cannelle.',
                'price_range': 'H',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Pigeon, pâte filo (ouarka), amandes, œufs, oignons, persil, cannelle, sucre glace, huile d\'olive',
                'preparation_steps': '1. Cuire le pigeon avec les épices\n2. Préparer la farce aux amandes\n3. Assembler les couches de pâte filo avec la farce\n4. Cuire au four et saupoudrer de sucre et de cannelle',
                'history': 'Plat d\'origine andalouse, la pastilla était servie dans les cours royales marocaines. Le pigeon peut être remplacé par du poulet.',
                'is_tourist_recommended': True,
                'cultural_notes': 'La pastilla est souvent servie comme entrée lors des mariages et célébrations importantes. Le mélange sucré-salé est caractéristique de la cuisine marocaine.'
            },
            {
                'name': 'Harira',
                'description': 'Soupe traditionnelle à base de tomates, lentilles, pois chiches et viande, parfumée avec des herbes fraîches et des épices.',
                'price_range': 'L',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Tomates, lentilles, pois chiches, viande d\'agneau, céleri, coriandre, persil, farine, œufs, citron',
                'preparation_steps': '1. Faire revenir la viande avec les épices\n2. Ajouter les légumineuses et les tomates\n3. Mijoter longuement\n4. Lier avec un mélange de farine et d\'œufs en fin de cuisson',
                'history': 'Soupe traditionnellement consommée pour rompre le jeûne pendant le mois de Ramadan.',
                'is_tourist_recommended': True,
                'cultural_notes': 'La harira est le plat par excellence pour rompre le jeûne pendant le Ramadan. Elle est généralement servie avec des dattes et des chebakia (pâtisseries au miel).'
            },
            {
                'name': 'Rfissa',
                'description': 'Plat de fête à base de poulet, de lentilles et de msemen (crêpes feuilletées) imprégnés de bouillon parfumé au fenugrec.',
                'price_range': 'M',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Poulet, lentilles, msemen (crêpes feuilletées), oignons, fenugrec, ras el hanout, safran, gingembre',
                'preparation_steps': '1. Cuire le poulet avec les épices\n2. Préparer les lentilles\n3. Déchirer les msemen en morceaux\n4. Servir les msemen recouverts de bouillon, de poulet et de lentilles',
                'history': 'Traditionnellement servi à une nouvelle mère après l\'accouchement, car le fenugrec favorise la lactation.',
                'is_tourist_recommended': False,
                'cultural_notes': 'La rfissa est traditionnellement servie trois jours après un accouchement pour aider la nouvelle mère à récupérer et favoriser la lactation.'
            },
            {
                'name': 'Tanjia Marrakchia',
                'description': 'Spécialité de Marrakech, viande longuement mijotée dans une jarre en terre cuite avec des épices.',
                'price_range': 'M',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Jarret de bœuf, cumin, safran, ail, citron confit, huile d\'olive',
                'preparation_steps': '1. Mélanger la viande avec les épices et l\'huile\n2. Placer dans une jarre en terre cuite\n3. Cuire lentement dans les cendres chaudes du hammam (bain public) pendant 5-8 heures',
                'history': 'Traditionnellement, ce plat était préparé par les hommes et cuit dans les cendres des hammams (bains publics) de Marrakech.',
                'is_tourist_recommended': True,
                'cultural_notes': 'La tanjia est surnommée "le plat du célibataire" car elle était traditionnellement préparée par des hommes célibataires qui travaillaient au souk (marché).'
            },
            {
                'name': 'Méchoui',
                'description': 'Agneau entier rôti à la broche ou au four, assaisonné simplement avec du sel et du cumin.',
                'price_range': 'H',
                'type': 'salty',
                'is_vegetarian': False,
                'is_vegan': False,
                'ingredients': 'Agneau entier, sel, cumin, huile d\'olive',
                'preparation_steps': '1. Frotter l\'agneau avec du sel et du cumin\n2. Rôtir lentement à la broche ou au four\n3. Servir avec du cumin et du sel pour l\'assaisonnement',
                'history': 'Plat de fête traditionnellement servi lors de l\'Aïd al-Adha (fête du sacrifice).',
                'is_tourist_recommended': True,
                'cultural_notes': 'Le méchoui est un plat de célébration, souvent préparé pour les grandes occasions comme les mariages et les fêtes religieuses.'
            },
            {
                'name': 'Zaalouk',
                'description': 'Salade d\'aubergines grillées et de tomates, assaisonnée d\'ail, de cumin et d\'huile d\'olive.',
                'price_range': 'L',
                'type': 'salty',
                'is_vegetarian': True,
                'is_vegan': True,
                'ingredients': 'Aubergines, tomates, ail, cumin, paprika, coriandre, huile d\'olive, jus de citron',
                'preparation_steps': '1. Griller les aubergines\n2. Cuire les tomates avec l\'ail et les épices\n3. Mélanger et écraser grossièrement\n4. Servir froid ou à température ambiante',
                'history': 'Cette salade fait partie des nombreuses salades marocaines servies en début de repas.',
                'is_tourist_recommended': True,
                'cultural_notes': 'Le zaalouk fait partie des salades marocaines (ou "kemia") servies en début de repas. Il est souvent consommé avec du pain pour saucer.'
            },
            {
                'name': 'Chebakia',
                'description': 'Pâtisserie en forme de fleur, frite et trempée dans du miel parfumé à l\'eau de fleur d\'oranger et saupoudrée de graines de sésame.',
                'price_range': 'L',
                'type': 'sweet',
                'is_vegetarian': True,
                'is_vegan': False,
                'ingredients': 'Farine, graines de sésame, graines d\'anis, cannelle, miel, eau de fleur d\'oranger, huile pour friture',
                'preparation_steps': '1. Préparer une pâte avec les épices\n2. Former des fleurs\n3. Frire\n4. Tremper dans le miel parfumé à l\'eau de fleur d\'oranger',
                'history': 'Pâtisserie traditionnellement préparée pour le Ramadan.',
                'is_tourist_recommended': True,
                'cultural_notes': 'Les chebakia sont indissociables du Ramadan au Maroc. Leur préparation est souvent une activité familiale où plusieurs générations se réunissent.'
            },
            {
                'name': 'Thé à la Menthe',
                'description': 'Thé vert infusé avec des feuilles de menthe fraîche et du sucre, servi dans des verres traditionnels.',
                'price_range': 'L',
                'type': 'drink',
                'is_vegetarian': True,
                'is_vegan': True,
                'ingredients': 'Thé vert (gunpowder), menthe fraîche, sucre',
                'preparation_steps': '1. Rincer le thé\n2. Infuser avec de l\'eau bouillante\n3. Ajouter la menthe et le sucre\n4. Verser de haut pour créer de la mousse',
                'history': 'Le thé à la menthe est devenu populaire au Maroc au 18ème siècle, introduit par les commerçants britanniques.',
                'is_tourist_recommended': True,
                'cultural_notes': 'Le thé est un symbole d\'hospitalité au Maroc. La hauteur à laquelle on le verse démontre le respect envers l\'invité.'
            },
            {
                'name': 'Msemen',
                'description': 'Crêpes feuilletées carrées, à la fois croustillantes et moelleuses, traditionnellement servies au petit-déjeuner ou au goûter.',
                'price_range': 'L',
                'type': 'sweet',
                'is_vegetarian': True,
                'is_vegan': False,
                'ingredients': 'Farine, semoule fine, levure, sel, huile',
                'preparation_steps': '1. Préparer une pâte souple\n2. Étaler en carrés très fins\n3. Plier en créant des couches\n4. Cuire à la poêle',
                'history': 'Ces crêpes font partie intégrante du petit-déjeuner traditionnel marocain.',
                'is_tourist_recommended': True,
                'cultural_notes': 'Les msemen sont souvent vendus dans les rues des médinas tôt le matin et en fin d\'après-midi. Ils sont généralement servis avec du miel ou de la confiture.'
            },
            {
                'name': 'Bissara',
                'description': 'Soupe épaisse à base de fèves séchées, assaisonnée d\'huile d\'olive, de cumin et de paprika.',
                'price_range': 'L',
                'type': 'salty',
                'is_vegetarian': True,
                'is_vegan': True,
                'ingredients': 'Fèves séchées, ail, cumin, paprika, huile d\'olive, jus de citron',
                'preparation_steps': '1. Cuire les fèves jusqu\'à ce qu\'elles soient tendres\n2. Mixer avec l\'ail et les épices\n3. Servir garni d\'huile d\'olive et de cumin',
                'history': 'Plat traditionnel des régions montagneuses du Maroc, particulièrement populaire en hiver.',
                'is_tourist_recommended': False,
                'cultural_notes': 'La bissara est considérée comme un plat du peuple, nourrissant et économique. Elle est particulièrement populaire dans le nord du Maroc.'
            }
        ] 