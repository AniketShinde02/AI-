class Particle {
    constructor(x, y, z) {
        this.x = x;
        this.y = y;
        this.z = z;
        this.baseX = x;
        this.baseY = y;
        this.baseZ = z;
        this.size = 1.5;
    }

    rotate(angleX, angleY) {
        // Rotate around Y
        let rad = angleY;
        let cos = Math.cos(rad);
        let sin = Math.sin(rad);
        let z = this.z * cos - this.x * sin;
        let x = this.z * sin + this.x * cos;
        this.x = x;
        this.z = z;

        // Rotate around X
        rad = angleX;
        cos = Math.cos(rad);
        sin = Math.sin(rad);
        let y = this.y * cos - this.z * sin;
        z = this.y * sin + this.z * cos;
        this.y = y;
        this.z = z;
    }

    project(width, height, fov) {
        const factor = fov / (fov + this.z);
        const x = this.x * factor + width / 2;
        const y = this.y * factor + height / 2;
        return { x, y, factor };
    }
}

class NeuralSystem {
    constructor() {
        this.canvas = document.getElementById('particle-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.micBtn = document.getElementById('mic-btn');
        this.startBtn = document.getElementById('start-btn');
        this.overlay = document.getElementById('permission-overlay');
        this.statusText = document.getElementById('status-indicator');
        this.ring = document.querySelector('.ring-circle');
        
        this.particles = [];
        this.numParticles = 800;
        this.isListening = false;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        
        this.angleX = 0.002;
        this.angleY = 0.005;
        
        this.initCanvas();
        this.initParticles();
        this.addEventListeners();
        this.animate();
    }

    initCanvas() {
        const resize = () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        };
        window.addEventListener('resize', resize);
        resize();
    }

    initParticles() {
        const radius = 200;
        for (let i = 0; i < this.numParticles; i++) {
            const theta = Math.random() * 2 * Math.PI;
            const phi = Math.acos(Math.random() * 2 - 1);
            
            const x = radius * Math.sin(phi) * Math.cos(theta);
            const y = radius * Math.sin(phi) * Math.sin(theta);
            const z = radius * Math.cos(phi);
            
            this.particles.push(new Particle(x, y, z));
        }
    }

    addEventListeners() {
        this.startBtn.addEventListener('click', () => this.startExperience());
        
        this.micBtn.addEventListener('click', () => {
            this.isListening = !this.isListening;
            this.statusText.innerText = this.isListening ? 'LISTENING' : 'IDLE';
            this.statusText.style.color = this.isListening ? '#00f2ff' : '#e0e0ff';
        });

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
        } catch (err) {
            console.warn('Mic access denied.');
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        
        this.ctx.fillStyle = 'rgba(2, 2, 5, 0.2)'; // Trail effect
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        let audioLevel = 0;
        if (this.analyser && this.isListening) {
            this.analyser.getByteFrequencyData(this.dataArray);
            let sum = 0;
            for (let i = 0; i < this.dataArray.length; i++) sum += this.dataArray[i];
            audioLevel = sum / this.dataArray.length;
            
            // Update progress ring
            const offset = 283 - (audioLevel / 255) * 283;
            this.ring.style.strokeDashoffset = offset;
        } else {
            this.ring.style.strokeDashoffset = 283;
        }

        const rotationSpeed = this.isListening ? 0.01 + (audioLevel / 255) * 0.05 : 0.005;

        this.particles.forEach(p => {
            p.rotate(this.angleX, rotationSpeed);
            
            const projection = p.project(this.canvas.width, this.canvas.height, 400);
            
            // Reaction to audio
            let pulse = 0;
            if (this.isListening) {
                pulse = (Math.random() - 0.5) * (audioLevel * 0.5);
            }

            const size = p.size * projection.factor;
            const opacity = Math.max(0, projection.factor * 0.8);
            
            this.ctx.fillStyle = `rgba(0, 242, 255, ${opacity})`;
            this.ctx.beginPath();
            this.ctx.arc(projection.x + pulse, projection.y + pulse, size, 0, Math.PI * 2);
            this.ctx.fill();
        });
    }
}

new NeuralSystem();
