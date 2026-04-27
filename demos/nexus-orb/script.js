import * as THREE from 'three';

// Advanced Glass Shader uses onBeforeCompile on MeshPhysicalMaterial
const snoiseFunc = `
    // Simplex 3D Noise function
    vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
    vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

    float snoise(vec3 v){ 
      const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
      const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);

      vec3 i  = floor(v + dot(v, C.yyy) );
      vec3 x0 =   v - i + dot(i, C.xxx) ;

      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min( g.xyz, l.zxy );
      vec3 i2 = max( g.xyz, l.zxy );

      vec3 x1 = x0 - i1 + 1.0 * C.xxx;
      vec3 x2 = x0 - i2 + 2.0 * C.xxx;
      vec3 x3 = x0 - D.yyy;

      i = mod(i, 289.0); 
      vec4 p = permute( permute( permute( 
                 i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
               + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
               + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));

      float n_ = 1.0/7.0;
      vec3  ns = n_ * D.wyz - D.xzx;

      vec4 j = p - 49.0 * floor(p * ns.z *ns.z);

      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_ );

      vec4 x = x_ *ns.x + ns.yyyy;
      vec4 y = y_ *ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);

      vec4 b0 = vec4( x.xy, y.xy );
      vec4 b1 = vec4( x.zw, y.zw );

      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));

      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;

      vec3 p0 = vec3(a0.xy,h.x);
      vec3 p1 = vec3(a0.zw,h.y);
      vec3 p2 = vec3(a1.xy,h.z);
      vec3 p3 = vec3(a1.zw,h.w);

      vec4 sig = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
      p0 *= sig.x;
      p1 *= sig.y;
      p2 *= sig.z;
      p3 *= sig.w;

      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), 
                                    dot(p2,x2), dot(p3,x3) ) );
    }
`;

// --- App Class ---
class NexusOrbApp {
    constructor() {
        this.container = document.getElementById('orb-container');
        this.micBtn = document.getElementById('mic-btn');
        this.startBtn = document.getElementById('start-btn');
        this.overlay = document.getElementById('permission-overlay');
        
        this.isListening = false;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        
        this.initThree();
        this.addEventListeners();
        this.animate();
    }

    initThree() {
        // Scene setup
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
        this.camera.position.z = 2.5;

        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        
        const width = this.container.clientWidth || 400;
        const height = this.container.clientHeight || 400;
        
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Orb Geometry
        const geometry = new THREE.IcosahedronGeometry(1.2, 128); // Higher poly count for smooth glass deformation
        
        // Custom uniforms for the animation
        this.customUniforms = {
            uTime: { value: 0 },
            uIntensity: { value: 0.15 },
            uSpeed: { value: 0.4 }
        };

        // Advanced Glass Material
        this.material = new THREE.MeshPhysicalMaterial({
            color: 0xffffff,
            metalness: 0.1,
            roughness: 0.05,
            transmission: 1.0, // Glass effect
            ior: 1.5,
            thickness: 1.5,
            envMapIntensity: 1.5,
            clearcoat: 1.0,
            clearcoatRoughness: 0.1,
            iridescence: 1.0,
            iridescenceIOR: 1.3,
            iridescenceThicknessRange: [100, 400],
            transparent: true,
            opacity: 1.0,
        });

        // Inject vertex displacement into standard material
        this.material.onBeforeCompile = (shader) => {
            shader.uniforms.uTime = this.customUniforms.uTime;
            shader.uniforms.uIntensity = this.customUniforms.uIntensity;
            shader.uniforms.uSpeed = this.customUniforms.uSpeed;

            shader.vertexShader = `
                uniform float uTime;
                uniform float uIntensity;
                uniform float uSpeed;
                varying vec3 vViewPosition;
                ${snoiseFunc}
            ` + shader.vertexShader;

            shader.vertexShader = shader.vertexShader.replace(
                '#include <begin_vertex>',
                `
                float noise = snoise(vec3(position.xyz * 1.2 + uTime * uSpeed));
                vec3 transformed = vec3(position) + normal * (noise * uIntensity);
                `
            );
        };

        this.orb = new THREE.Mesh(geometry, this.material);
        this.scene.add(this.orb);

        // Colorful Lights to reflect inside the glass
        const light1 = new THREE.PointLight(0xa855f7, 5, 10);
        light1.position.set(2, 2, 2);
        this.scene.add(light1);

        const light2 = new THREE.PointLight(0x3b82f6, 5, 10);
        light2.position.set(-2, -2, 2);
        this.scene.add(light2);

        const light3 = new THREE.PointLight(0xf43f5e, 3, 10);
        light3.position.set(0, 0, -3);
        this.scene.add(light3);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
        this.scene.add(ambientLight);
    }

    addEventListeners() {
        this.startBtn.addEventListener('click', () => this.startExperience());
        
        this.micBtn.addEventListener('click', () => this.toggleListening());
        
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        
        const toggleSidebar = () => {
            document.querySelector('.sidebar').classList.toggle('open');
        };

        if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
        if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', toggleSidebar);

        window.addEventListener('resize', () => {
            if (!this.camera || !this.renderer) return;
            const width = this.container.clientWidth;
            const height = this.container.clientHeight;
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
        });

        // Initialize Lucide icons
        lucide.createIcons();
    }

    async startExperience() {
        this.overlay.classList.add('hidden');
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const source = this.audioContext.createMediaStreamSource(stream);
            
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);
            
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            console.log('Audio initialized');
        } catch (err) {
            console.warn('Microphone access denied or not available. Using simulated data.', err);
        }
    }

    toggleListening() {
        this.isListening = !this.isListening;
        this.micBtn.classList.toggle('active', this.isListening);
        
        if (this.isListening) {
            gsap.to(this.customUniforms.uIntensity, { value: 0.35, duration: 0.5 });
            gsap.to(this.customUniforms.uSpeed, { value: 1.0, duration: 0.5 });
        } else {
            gsap.to(this.customUniforms.uIntensity, { value: 0.15, duration: 0.5 });
            gsap.to(this.customUniforms.uSpeed, { value: 0.4, duration: 0.5 });
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const time = performance.now() * 0.001;
        this.customUniforms.uTime.value = time;

        if (this.isListening && this.analyser) {
            this.analyser.getByteFrequencyData(this.dataArray);
            
            // Get average volume
            let sum = 0;
            for (let i = 0; i < this.dataArray.length; i++) {
                sum += this.dataArray[i];
            }
            const average = sum / this.dataArray.length;
            
            // Map volume to intensity
            const targetIntensity = 0.2 + (average / 255) * 0.8;
            this.customUniforms.uIntensity.value = THREE.MathUtils.lerp(
                this.customUniforms.uIntensity.value,
                targetIntensity,
                0.1
            );
            
            // Subtle scale change
            const scale = 1.0 + (average / 255) * 0.15;
            this.orb.scale.set(scale, scale, scale);
        } else if (!this.isListening) {
            // Idle breathing effect
            const breathing = Math.sin(time * 2) * 0.02 + 1.0;
            this.orb.scale.set(breathing, breathing, breathing);
        }

        // Constant rotation
        this.orb.rotation.y += 0.005;
        this.orb.rotation.z += 0.003;

        this.renderer.render(this.scene, this.camera);
    }
}

// Start the app
new NexusOrbApp();
