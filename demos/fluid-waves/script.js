class Wave {
    constructor(canvas, options) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.options = Object.assign({
            speed: 0.1,
            amplitude: 20,
            wavelength: 100,
            color: 'rgba(255, 255, 255, 0.5)',
            lineWidth: 2
        }, options);
        
        this.phase = Math.random() * Math.PI * 2;
    }

    update(audioData) {
        this.phase += this.options.speed;
        
        // Enhance amplitude based on audio frequency data if available
        let audioBoost = 1;
        if (audioData) {
            // Get relevant frequency band for this wave
            const index = Math.floor(this.options.freqIndex * audioData.length);
            audioBoost = 1 + (audioData[index] / 255) * 4;
        }

        this.currentAmplitude = this.options.amplitude * audioBoost;
    }

    draw() {
        const { width, height } = this.canvas;
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.options.color;
        this.ctx.lineWidth = this.options.lineWidth;
        this.ctx.lineCap = 'round';

        for (let x = 0; x <= width; x += 5) {
            const y = height / 2 + Math.sin(x / this.options.wavelength + this.phase) * this.currentAmplitude;
            if (x === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }

        this.ctx.stroke();
    }
}

class FluidAssistant {
    constructor() {
        this.canvas = document.getElementById('waves-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.micBtn = document.getElementById('mic-btn');
        this.startBtn = document.getElementById('start-btn');
        this.overlay = document.getElementById('permission-overlay');
        
        this.isListening = false;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        
        this.waves = [];
        this.initCanvas();
        this.initWaves();
        this.addEventListeners();
        this.animate();
    }

    initCanvas() {
        const resize = () => {
            const dpr = window.devicePixelRatio || 1;
            this.canvas.width = this.canvas.offsetWidth * dpr;
            this.canvas.height = this.canvas.offsetHeight * dpr;
            this.ctx.scale(dpr, dpr);
        };
        window.addEventListener('resize', resize);
        resize();
    }

    initWaves() {
        const colors = [
            'rgba(59, 130, 246, 0.4)', // Blue
            'rgba(139, 92, 246, 0.4)', // Purple
            'rgba(236, 72, 153, 0.4)', // Pink
            'rgba(255, 255, 255, 0.2)'  // White
        ];

        this.waves = colors.map((color, i) => new Wave(this.canvas, {
            color: color,
            speed: 0.02 + i * 0.01,
            amplitude: 15 + i * 5,
            wavelength: 60 + i * 20,
            lineWidth: 3 - i * 0.5,
            freqIndex: 0.1 + i * 0.15 // Which frequency band to respond to
        }));
    }

    addEventListeners() {
        this.startBtn.addEventListener('click', () => this.startExperience());
        
        this.micBtn.addEventListener('click', () => {
            this.isListening = !this.isListening;
            this.micBtn.style.background = this.isListening ? '#ef4444' : 'white';
            this.micBtn.style.color = this.isListening ? 'white' : 'black';
            
            if (this.isListening) {
                this.addMessage("Listening...", "assistant");
            }
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
            this.analyser.fftSize = 512;
            source.connect(this.analyser);
            
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        } catch (err) {
            console.warn('Microphone access denied. Using simulated wave motion.');
        }
    }

    addMessage(text, type) {
        const display = document.getElementById('chat-display');
        const msg = document.createElement('div');
        msg.className = `message ${type}`;
        msg.innerHTML = `<p>${text}</p>`;
        display.appendChild(msg);
        display.scrollTop = display.scrollHeight;
        
        gsap.from(msg, { y: 20, opacity: 0, duration: 0.4, ease: "power2.out" });
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        
        // Clear canvas with a slight trail effect (optional, here we clear fully)
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.analyser) {
            this.analyser.getByteFrequencyData(this.dataArray);
        }

        this.waves.forEach(wave => {
            wave.update(this.isListening ? this.dataArray : null);
            wave.draw();
        });
    }
}

// Start the app
new FluidAssistant();
