def get_dishes(request):
    """
    Vue API optimisée pour renvoyer les plats avec mise en cache
    """
    # Vérifier si les données sont en cache
    cache_key = 'all_dishes_data'
    dishes_data = cache.get(cache_key)
    
    if not dishes_data:
        # Si pas en cache, récupérer depuis la base de données
        start_time = time.time()
        dishes = Dish.objects.select_related('city').all()
        
        # Préparer les données pour la sérialisation JSON
        dishes_data = []
        for dish in dishes:
            dishes_data.append({
                'id': dish.id,
                'name': dish.name,
                'description': dish.description,
                'price_range': dish.price_range,
                'price_display': dish.get_price_range_display(),
                'type': dish.type,
                'type_display': dish.get_type_display(),
                'image': dish.image.url if dish.image else '',
                'is_vegetarian': dish.is_vegetarian,
                'is_vegan': dish.is_vegan,
                'ingredients': dish.ingredients,
                'history': dish.history,
                'preparation_steps': dish.preparation_steps,
                'city': {
                    'id': dish.city.id if dish.city else None,
                    'name': dish.city.name if dish.city else None
                },
                'timestamp': timezone.now().timestamp()  # Ajouter un horodatage pour le suivi
            })
        
        # Mettre en cache pour 10 minutes
        cache.set(cache_key, dishes_data, 60 * 10)
        
        print(f"Database query completed in {time.time() - start_time:.4f} seconds")
    
    return JsonResponse(dishes_data, safe=False) 