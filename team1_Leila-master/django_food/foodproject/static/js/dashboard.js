// Fonction pour initialiser les animations et les graphiques du tableau de bord
function initDashboard(cityLabels, cityData, sweetCount, saltyCount, drinkCount) {
    // Timeline principale pour l'animation d'entrée
    const tl = gsap.timeline();
    
    // Animation de chargement
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        tl.to(loadingOverlay, {
            opacity: 0,
            duration: 0.5,
            onComplete: () => loadingOverlay.remove()
        });
    }
    
    // Animation de la sidebar
    tl.from('.sidebar', {
        x: -100,
        opacity: 0,
        duration: 0.8,
        ease: 'power3.out'
    })
    .from('.logo', {
        y: -20,
        opacity: 0,
        duration: 0.5,
        ease: 'back.out(1.7)'
    })
    .from('.nav-link', {
        x: -30,
        opacity: 0,
        stagger: 0.1,
        duration: 0.5,
        ease: 'power2.out'
    }, '-=0.3');
    
    // Animation du contenu principal
    tl.from('.greeting', {
        y: -20,
        opacity: 0,
        duration: 0.5,
        ease: 'power2.out'
    }, '-=0.3')
    .from('.actions .btn', {
        y: -20,
        opacity: 0,
        stagger: 0.1,
        duration: 0.5,
        ease: 'power2.out'
    }, '-=0.3');
    
    // Animation des cartes statistiques avec effet de cascade
    gsap.from('.stat-card', {
        y: 30,
        opacity: 0,
        duration: 0.7,
        stagger: {
            each: 0.1,
            from: "start",
            grid: "auto"
        },
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.stats-grid',
            start: 'top center+=100',
            toggleActions: 'play none none reverse'
        }
    });
    
    // Animation des graphiques
    gsap.from('.chart-card', {
        y: 40,
        opacity: 0,
        duration: 0.8,
        stagger: 0.2,
        ease: 'power3.out',
        scrollTrigger: {
            trigger: '.charts-row',
            start: 'top center+=100',
            toggleActions: 'play none none reverse'
        }
    });
    
    // Configuration du graphique de plats par ville avec animation
    const ctxDishes = document.getElementById('dishes-by-city').getContext('2d');
    const dishesChart = new Chart(ctxDishes, {
        type: 'bar',
        data: {
            labels: cityLabels,
            datasets: [{
                label: 'Nombre de plats',
                data: cityData,
                backgroundColor: '#FF6B6B',
                borderColor: '#FF6B6B',
                borderWidth: 1,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 2000,
                easing: 'easeOutQuart'
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        family: 'Poppins'
                    },
                    bodyFont: {
                        size: 13,
                        family: 'Poppins'
                    }
                }
            }
        }
    });
    
    // Configuration du graphique de types de plats avec animation
    const ctxTypes = document.getElementById('dish-types').getContext('2d');
    const typesChart = new Chart(ctxTypes, {
        type: 'doughnut',
        data: {
            labels: ['Sucré', 'Salé', 'Boisson'],
            datasets: [{
                data: [sweetCount, saltyCount, drinkCount],
                backgroundColor: [
                    '#FF9F1C',
                    '#4ECDC4',
                    '#FF6B6B'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 2000,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            family: 'Poppins',
                            size: 12
                        },
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        family: 'Poppins'
                    },
                    bodyFont: {
                        size: 13,
                        family: 'Poppins'
                    }
                }
            },
            cutout: '70%'
        }
    });
    
    // Ajout d'interactivité aux boutons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
            gsap.to(btn, {
                scale: 1.05,
                duration: 0.3,
                ease: 'power2.out'
            });
        });
        
        btn.addEventListener('mouseleave', () => {
            gsap.to(btn, {
                scale: 1,
                duration: 0.3,
                ease: 'power2.out'
            });
        });
        
        btn.addEventListener('click', () => {
            gsap.to(btn, {
                scale: 0.95,
                duration: 0.1,
                yoyo: true,
                repeat: 1,
                ease: 'power2.inOut'
            });
        });
    });
}

// Initialisation de ScrollTrigger
gsap.registerPlugin(ScrollTrigger);

// Animation des liens de navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        if (!this.classList.contains('active')) {
            gsap.from(this, {
                scale: 0.9,
                duration: 0.3,
                ease: 'power2.out'
            });
        }
    });
});

// La fonction sera appelée depuis le template avec les données Django 