// FoodFlex Desktop Application - Main JavaScript File

document.addEventListener('DOMContentLoaded', () => {
    // Initialize animations
    initAnimations();
    
    // Initialize window controls
    initWindowControls();
    
    // Initialize sidebar
    initSidebar();
    
    // Initialize search functionality
    initSearch();

    // Initialize food elements instead of 3D objects
    initFoodElements();
    
    // Initialize Swiper if it exists
    initSwiper();
});

// Animation functions with GSAP
function initAnimations() {
    // Check if GSAP is loaded
    if (typeof gsap !== 'undefined') {
        // Fade in elements with the animate-in class
        gsap.from('.animate-in', {
            opacity: 0,
            y: 20,
            stagger: 0.1,
            duration: 0.6,
            ease: 'power2.out'
        });
        
        // Animate hero section
        gsap.from('.hero-section', {
            opacity: 0,
            scale: 0.95,
            duration: 0.8,
            ease: 'power2.out'
        });
        
        // Animate cards on scroll
        const cards = document.querySelectorAll('.food-card, .paladium-card');
        cards.forEach(card => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top bottom-=100',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 30,
                duration: 0.5,
                ease: 'power2.out'
            });
        });

        // Animator sections
        gsap.utils.toArray('.section-title').forEach(title => {
            gsap.fromTo(title, {
                opacity: 0,
                y: 20
            }, {
                scrollTrigger: {
                    trigger: title,
                    start: 'top bottom-=100',
                },
                opacity: 1, 
                y: 0,
                duration: 0.6
            });
        });
    }
}

// Window controls for desktop app behavior
function initWindowControls() {
    const minimizeBtn = document.querySelector('.window-control.minimize');
    const maximizeBtn = document.querySelector('.window-control.maximize');
    const closeBtn = document.querySelector('.window-control.close');
    const titlebar = document.querySelector('.titlebar');
    
    if (minimizeBtn && maximizeBtn && closeBtn) {
        // Make titlebar draggable
        let isDragging = false;
        let dragStartX, dragStartY;
        
        titlebar.addEventListener('mousedown', (e) => {
            isDragging = true;
            dragStartX = e.clientX;
            dragStartY = e.clientY;
        });
        
        window.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const dx = e.clientX - dragStartX;
                const dy = e.clientY - dragStartY;
                
                // In a real Electron app, you would use:
                // window.moveTo(window.screenX + dx, window.screenY + dy);
                // For now we'll just simulate this behavior
                console.log(`Window moved by ${dx}px horizontally and ${dy}px vertically`);
            }
        });
        
        window.addEventListener('mouseup', () => {
            isDragging = false;
        });
        
        // Button click handlers
        minimizeBtn.addEventListener('click', () => {
            console.log('Window minimized');
        });
        
        maximizeBtn.addEventListener('click', () => {
            console.log('Window maximized/restored');
        });
        
        closeBtn.addEventListener('click', () => {
            console.log('Window closed');
        });
    }
}

// Sidebar interaction
function initSidebar() {
    const sidebar = document.querySelector('.app-sidebar');
    
    if (sidebar) {
        const sidebarLinks = sidebar.querySelectorAll('a');
        
        sidebarLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Amélioration pour le bouton restaurant
                if (link.getAttribute('href').includes('restaurants')) {
                    // Assurer que le lien restaurant fonctionne correctement
                    console.log('Restaurant link clicked');
                    // Pas besoin de preventDefault car on veut que la navigation se produise
                }
                
                // Remove active class from all links
                sidebarLinks.forEach(l => l.classList.remove('active'));
                
                // Add active class to clicked link
                link.classList.add('active');
            });
        });
        
        // Toggle sidebar expansion on hover
        sidebar.addEventListener('mouseenter', () => {
            sidebar.classList.add('expanded');
        });
        
        sidebar.addEventListener('mouseleave', () => {
            sidebar.classList.remove('expanded');
        });
    }
}

// Search functionality
function initSearch() {
    const searchInput = document.querySelector('.search-input');
    
    if (searchInput) {
        searchInput.addEventListener('focus', () => {
            document.querySelector('.search-container').classList.add('focused');
        });
        
        searchInput.addEventListener('blur', () => {
            document.querySelector('.search-container').classList.remove('focused');
        });
        
        searchInput.addEventListener('input', (e) => {
            // Implement search functionality
            console.log(`Searching for: ${e.target.value}`);
        });
    }
}

// Remplacer l'objet 3D par des éléments culinaires
function initFoodElements() {
    const sceneContainer = document.querySelector('.scene-container');
    
    if (sceneContainer) {
        // Supprimer tout contenu existant qui pourrait être lié à Three.js
        sceneContainer.innerHTML = '';
        
        // Créer des éléments culinaires flottants
        const foodItems = [
            'hamburger', 'pizza-slice', 'hotdog', 'cookie', 'cheese', 
            'drumstick-bite', 'fish', 'bread-slice', 'pepper-hot', 'egg'
        ];
        
        const colors = ['#FF6B6B', '#4ECDC4', '#FFD166', '#F9F871', '#FC8621'];
        
        // Créer 15 icônes alimentaires flottantes
        for (let i = 0; i < 15; i++) {
            const foodIcon = document.createElement('div');
            foodIcon.className = 'food-icon';
            foodIcon.innerHTML = `<i class="fas fa-${foodItems[i % foodItems.length]}"></i>`;
            foodIcon.style.color = colors[i % colors.length];
            
            // Position aléatoire
            const x = Math.random() * 100;
            const y = Math.random() * 100;
            foodIcon.style.left = `${x}%`;
            foodIcon.style.top = `${y}%`;
            
            // Animation aléatoire
            const delay = Math.random() * 5;
            const duration = 5 + Math.random() * 20;
            
            if (typeof gsap !== 'undefined') {
                gsap.to(foodIcon, {
                    y: -100 + Math.random() * 200,
                    x: -100 + Math.random() * 200,
                    rotation: -360 + Math.random() * 720,
                    duration: duration,
                    delay: delay,
                    repeat: -1,
                    yoyo: true,
                    ease: 'sine.inOut'
                });
            }
            
            sceneContainer.appendChild(foodIcon);
        }
        
        // Ajouter des styles pour les icônes alimentaires
        const style = document.createElement('style');
        style.textContent = `
            .food-icon {
                position: absolute;
                font-size: 2rem;
                opacity: 0.2;
                z-index: 1;
                filter: blur(1px);
                transform: translateZ(0);
            }
            @media (max-width: 768px) {
                .food-icon {
                    font-size: 1.5rem;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize Swiper if available
function initSwiper() {
    if (typeof Swiper !== 'undefined') {
        new Swiper(".mySwiper", {
            effect: "coverflow",
            grabCursor: true,
            centeredSlides: true,
            slidesPerView: "auto",
            coverflowEffect: {
                rotate: 50,
                stretch: 0,
                depth: 100,
                modifier: 1,
                slideShadows: true
            },
            pagination: {
                el: ".swiper-pagination",
                clickable: true
            },
            autoplay: {
                delay: 3000,
                disableOnInteraction: false
            }
        });
    }
} 