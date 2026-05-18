/**
 * EduNova — Three.js WebGL Animated Background
 * Une nébuleuse spatiale lente et immersive.
 */

document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("bg-canvas");
    if (!canvas) return;

    // Configuration de base
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0e1a, 0.001);

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 2000);
    camera.position.z = 1000;

    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Particules
    const geometry = new THREE.BufferGeometry();
    const particlesCount = 1500;

    const posArray = new Float32Array(particlesCount * 3);
    const colorsArray = new Float32Array(particlesCount * 3);

    const color1 = new THREE.Color(0x4f46e5); // Aurora Indigo
    const color2 = new THREE.Color(0x06b6d4); // Nova Cyan

    for (let i = 0; i < particlesCount * 3; i += 3) {
        // Sphère de distribution
        const r = 800 * Math.cbrt(Math.random());
        const theta = Math.random() * 2 * Math.PI;
        const phi = Math.acos(2 * Math.random() - 1);

        posArray[i] = r * Math.sin(phi) * Math.cos(theta);     // x
        posArray[i + 1] = r * Math.sin(phi) * Math.sin(theta); // y
        posArray[i + 2] = r * Math.cos(phi);                   // z

        // Mélange de couleurs
        const mixedColor = color1.clone().lerp(color2, Math.random());
        colorsArray[i] = mixedColor.r;
        colorsArray[i + 1] = mixedColor.g;
        colorsArray[i + 2] = mixedColor.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colorsArray, 3));

    // Texture pour les particules (cercle flou au lieu de carré)
    const createCircleTexture = () => {
        const canvas = document.createElement('canvas');
        canvas.width = 32;
        canvas.height = 32;
        const context = canvas.getContext('2d');
        const gradient = context.createRadialGradient(16, 16, 0, 16, 16, 16);
        gradient.addColorStop(0, 'rgba(255,255,255,1)');
        gradient.addColorStop(1, 'rgba(255,255,255,0)');
        context.fillStyle = gradient;
        context.fillRect(0, 0, 32, 32);
        const texture = new THREE.CanvasTexture(canvas);
        return texture;
    };

    const material = new THREE.PointsMaterial({
        size: 8,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        map: createCircleTexture(),
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });

    const particlesMesh = new THREE.Points(geometry, material);
    scene.add(particlesMesh);

    // Mouvement de la souris
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;
    const windowHalfX = window.innerWidth / 2;
    const windowHalfY = window.innerHeight / 2;

    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX - windowHalfX) * 0.5;
        mouseY = (event.clientY - windowHalfY) * 0.5;
    });

    // Animation
    const clock = new THREE.Clock();

    const tick = () => {
        const elapsedTime = clock.getElapsedTime();

        targetX = mouseX * 0.001;
        targetY = mouseY * 0.001;

        particlesMesh.rotation.y += 0.0005 + (targetX - particlesMesh.rotation.y) * 0.05;
        particlesMesh.rotation.x += 0.0005 + (targetY - particlesMesh.rotation.x) * 0.05;

        // Vague légère
        const positions = geometry.attributes.position.array;
        for (let i = 0; i < particlesCount; i++) {
            const i3 = i * 3;
            const x = geometry.attributes.position.array[i3];
            geometry.attributes.position.array[i3 + 1] += Math.sin(elapsedTime + x) * 0.05;
        }
        geometry.attributes.position.needsUpdate = true;

        renderer.render(scene, camera);
        window.requestAnimationFrame(tick);
    };

    tick();

    // Redimensionnement
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
});
