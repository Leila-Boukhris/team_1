window.addEventListener('DOMContentLoaded', () => {

    const scene = new THREE.Scene();
    
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 15;
    

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);
    
    const container = document.querySelector('.scene-container');
    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const pointLight1 = new THREE.PointLight(0xff5722, 1);
    pointLight1.position.set(10, 10, 10);
    scene.add(pointLight1);
    
    const pointLight2 = new THREE.PointLight(0x2ed573, 1);
    pointLight2.position.set(-10, -10, 10);
    scene.add(pointLight2);
    

    const foodItems = [];
    
    // pizza 3D
    function createPizza() {
        const pizzaGroup = new THREE.Group();
        
        // Base de pizza
        const baseGeometry = new THREE.CylinderGeometry(3, 3, 0.3, 32);
        const baseMaterial = new THREE.MeshStandardMaterial({ color: 0xe2b971 });
        const base = new THREE.Mesh(baseGeometry, baseMaterial);
        
        // Sauce tomate
        const sauceGeometry = new THREE.CylinderGeometry(2.8, 2.8, 0.1, 32);
        const sauceMaterial = new THREE.MeshStandardMaterial({ color: 0xd63031 });
        const sauce = new THREE.Mesh(sauceGeometry, sauceMaterial);
        sauce.position.y = 0.2;
        
        // Fromage
        const cheeseGeometry = new THREE.CylinderGeometry(2.8, 2.8, 0.05, 32);
        const cheeseMaterial = new THREE.MeshStandardMaterial({ color: 0xf9ca24 });
        const cheese = new THREE.Mesh(cheeseGeometry, cheeseMaterial);
        cheese.position.y = 0.275;
        
        // Créer des toppings 
        for (let i = 0; i < 10; i++) {
            const pepperoniGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.05, 16);
            const pepperoniMaterial = new THREE.MeshStandardMaterial({ color: 0xd63031 });
            const pepperoni = new THREE.Mesh(pepperoniGeometry, pepperoniMaterial);
            
            // Position aléatoire sur la pizza
            const angle = Math.random() * Math.PI * 2;
            const radius = Math.random() * 2;
            pepperoni.position.x = Math.cos(angle) * radius;
            pepperoni.position.z = Math.sin(angle) * radius;
            pepperoni.position.y = 0.3;
            
            pizzaGroup.add(pepperoni);
        }
        
        pizzaGroup.add(base);
        pizzaGroup.add(sauce);
        pizzaGroup.add(cheese);
        
        return pizzaGroup;
    }
    
    // Créer un burger 3D
    function createBurger() {
        const burgerGroup = new THREE.Group();
        
        // Pain du dessous
        const bottomBunGeometry = new THREE.CylinderGeometry(2, 1.8, 0.6, 32);
        const bunMaterial = new THREE.MeshStandardMaterial({ color: 0xe2b971 });
        const bottomBun = new THREE.Mesh(bottomBunGeometry, bunMaterial);
        
        // Steak
        const pattyGeometry = new THREE.CylinderGeometry(1.8, 1.8, 0.4, 32);
        const pattyMaterial = new THREE.MeshStandardMaterial({ color: 0x6d4534 });
        const patty = new THREE.Mesh(pattyGeometry, pattyMaterial);
        patty.position.y = 0.5;
        
        // Fromage
        const cheeseGeometry = new THREE.CylinderGeometry(1.9, 1.9, 0.1, 32);
        const cheeseMaterial = new THREE.MeshStandardMaterial({ color: 0xfdcb6e });
        const cheese = new THREE.Mesh(cheeseGeometry, cheeseMaterial);
        cheese.position.y = 0.75;
        
        // Tomate
        const tomatoGeometry = new THREE.CylinderGeometry(1.7, 1.7, 0.15, 32);
        const tomatoMaterial = new THREE.MeshStandardMaterial({ color: 0xe74c3c });
        const tomato = new THREE.Mesh(tomatoGeometry, tomatoMaterial);
        tomato.position.y = 0.875;
        
        // Salade
        const lettuceGeometry = new THREE.CylinderGeometry(1.9, 1.9, 0.1, 32);
        const lettuceMaterial = new THREE.MeshStandardMaterial({ color: 0x2ecc71 });
        const lettuce = new THREE.Mesh(lettuceGeometry, lettuceMaterial);
        lettuce.position.y = 1;
        
        // Pain du dessus
        const topBunGeometry = new THREE.CylinderGeometry(1.8, 2, 0.6, 32);
        const topBun = new THREE.Mesh(topBunGeometry, bunMaterial);
        topBun.position.y = 1.35;
        
        burgerGroup.add(bottomBun);
        burgerGroup.add(patty);
        burgerGroup.add(cheese);
        burgerGroup.add(tomato);
        burgerGroup.add(lettuce);
        burgerGroup.add(topBun);
        
        return burgerGroup;
    }
    
    // Orange
    function createOrange() {
        const orangeGroup = new THREE.Group();
        
        // Corps de l'orange
        const orangeGeometry = new THREE.SphereGeometry(1.5, 32, 32);
        const orangeMaterial = new THREE.MeshStandardMaterial({ color: 0xf39c12 });
        const orange = new THREE.Mesh(orangeGeometry, orangeMaterial);
        
        // Feuille
        const leafGeometry = new THREE.ConeGeometry(0.4, 0.8, 32);
        const leafMaterial = new THREE.MeshStandardMaterial({ color: 0x2ecc71 });
        const leaf = new THREE.Mesh(leafGeometry, leafMaterial);
        leaf.position.y = 1.5;
        leaf.rotation.x = Math.PI;
        
        orangeGroup.add(orange);
        orangeGroup.add(leaf);
        
        return orangeGroup;
    }
    

    const pizza = createPizza();
    pizza.position.set(-8, 0, 0);
    scene.add(pizza);
    foodItems.push(pizza);
    
    const burger = createBurger();
    burger.position.set(8, 0, 0);
    scene.add(burger);
    foodItems.push(burger);
    
    const orange = createOrange();
    orange.position.set(0, -6, 0);
    scene.add(orange);
    foodItems.push(orange);
    
    // Animation
    function animate() {
        requestAnimationFrame(animate);
        
  
        foodItems.forEach((item, index) => {
            const time = Date.now() * 0.001;
            item.rotation.y = time * (index % 2 === 0 ? 0.5 : -0.5);
            
            
            item.position.y = Math.sin(time * (0.5 + index * 0.1)) * 0.5 + (index === 2 ? -6 : 0);
        });
        
        renderer.render(scene, camera);
    }
    

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    

    animate();
}); 