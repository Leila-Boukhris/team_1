from django.shortcuts import render, redirect
from django.http import JsonResponse

def index(request):
    return redirect('accueil')

def accueil(request):
    return render(request, 'foodapp/accueil.html', {})

def restaurants(request):
    return render(request, 'foodapp/modern_restaurants.html', {})

def restaurant_dashboard(request):
    return render(request, 'foodapp/restaurant_dashboard.html', {})

def restaurant_orders(request):
    return render(request, 'foodapp/restaurant_orders.html', {})

def restaurant_stats(request):
    return render(request, 'foodapp/restaurant_stats.html', {})

def restaurant_reviews(request):
    return render(request, 'foodapp/restaurant_reviews.html', {}) 