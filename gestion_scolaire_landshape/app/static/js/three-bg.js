/**
 * EduNova — Three.js WebGL Shader Background (Nebula)
 * Une nébuleuse spatiale qui respire lentement.
 */

document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("bg-canvas");
    if (!canvas) return;

    const scene = new THREE.Scene();
    
    // Orthographic camera for full screen plane
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: false });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Full screen plane
    const geometry = new THREE.PlaneGeometry(2, 2);

    const vertexShader = `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = vec4(position, 1.0);
        }
    `;

    const fragmentShader = `
        uniform float uTime;
        uniform vec2 uResolution;
        varying vec2 vUv;

        // Simplex 2D noise
        vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }
        float snoise(vec2 v){
            const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                     -0.577350269189626, 0.024390243902439);
            vec2 i  = floor(v + dot(v, C.yy) );
            vec2 x0 = v -   i + dot(i, C.xx);
            vec2 i1;
            i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
            vec4 x12 = x0.xyxy + C.xxzz;
            x12.xy -= i1;
            i = mod(i, 289.0);
            vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
            + i.x + vec3(0.0, i1.x, 1.0 ));
            vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
              dot(x12.zw,x12.zw)), 0.0);
            m = m*m ;
            m = m*m ;
            vec3 x = 2.0 * fract(p * C.www) - 1.0;
            vec3 h = abs(x) - 0.5;
            vec3 ox = floor(x + 0.5);
            vec3 a0 = x - ox;
            m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
            vec3 g;
            g.x  = a0.x  * x0.x  + h.x  * x0.y;
            g.yz = a0.yz * x12.xz + h.yz * x12.yw;
            return 130.0 * dot(m, g);
        }

        // Fractional Brownian motion
        float fbm(vec2 st) {
            float value = 0.0;
            float amplitude = 0.5;
            for (int i = 0; i < 5; i++) {
                value += amplitude * snoise(st);
                st *= 2.0;
                amplitude *= 0.5;
            }
            return value;
        }

        void main() {
            vec2 st = gl_FragCoord.xy / uResolution.xy;
            st.x *= uResolution.x / uResolution.y;

            vec2 q = vec2(0.0);
            q.x = fbm(st + 0.00 * uTime);
            q.y = fbm(st + vec2(1.0));

            vec2 r = vec2(0.0);
            r.x = fbm(st + 1.0 * q + vec2(1.7, 9.2) + 0.15 * uTime);
            r.y = fbm(st + 1.0 * q + vec2(8.3, 2.8) + 0.126 * uTime);

            float f = fbm(st + r);

            // Colors: Deep Void (0A0E1A), Aurora Indigo (4F46E5), Nova Cyan (06B6D4)
            vec3 color = mix(
                vec3(0.04, 0.05, 0.1), // Base dark
                vec3(0.31, 0.27, 0.9), // Indigo
                clamp((f*f)*4.0, 0.0, 1.0)
            );

            color = mix(
                color,
                vec3(0.02, 0.71, 0.83), // Cyan
                clamp(length(q), 0.0, 1.0)
            );
            
            color = mix(
                color,
                vec3(0.1, 0.1, 0.2), // Lightness
                clamp(length(r.x), 0.0, 1.0)
            );
            
            // Vignette
            vec2 uv = vUv * 2.0 - 1.0;
            float vignette = 1.0 - smoothstep(0.5, 1.5, length(uv));
            color *= vignette * 1.2;

            gl_FragColor = vec4((f*f*f + 0.6 * f*f + 0.5 * f) * color, 1.0);
        }
    `;

    const material = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: {
            uTime: { value: 0 },
            uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) }
        },
        transparent: true,
        depthWrite: false
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const clock = new THREE.Clock();

    const tick = () => {
        const elapsedTime = clock.getElapsedTime();
        material.uniforms.uTime.value = elapsedTime * 0.2; // Slow breathing
        
        renderer.render(scene, camera);
        window.requestAnimationFrame(tick);
    };

    tick();

    window.addEventListener('resize', () => {
        renderer.setSize(window.innerWidth, window.innerHeight);
        material.uniforms.uResolution.value.set(window.innerWidth, window.innerHeight);
    });
});
