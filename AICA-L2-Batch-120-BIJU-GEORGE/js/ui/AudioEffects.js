/**
 * AudioEffects.js - Procedural Web Audio API sound generator for Rubik's Cube
 * Features:
 * - Crisp mechanical plastic slice turn clicks
 * - Solve celebration chime
 * - Haptic feedback support for mobile
 */

export class AudioEffects {
    constructor() {
        this.ctx = null;
        this.enabled = true;
    }

    init() {
        if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AudioCtx();
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }

    playTurnClick() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;

            // Generate crisp mechanical click sound using filtered noise + decay sine
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'triangle';
            osc.frequency.setValueAtTime(320 + Math.random() * 80, now);
            osc.frequency.exponentialRampToValueAtTime(110, now + 0.04);

            gain.gain.setValueAtTime(0.18, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.04);

            // Trigger subtle mobile haptic feedback if available
            if (navigator.vibrate) {
                navigator.vibrate(12);
            }
        } catch (e) {
            // Audio context not ready
        }
    }

    playSolvedChime() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        try {
            const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
            notes.forEach((freq, idx) => {
                const now = this.ctx.currentTime + idx * 0.09;
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();

                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, now);

                gain.gain.setValueAtTime(0.14, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

                osc.connect(gain);
                gain.connect(this.ctx.destination);

                osc.start(now);
                osc.stop(now + 0.35);
            });

            if (navigator.vibrate) {
                navigator.vibrate([40, 60, 80]);
            }
        } catch (e) {
            // Audio error
        }
    }

    playCameraShutter() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        try {
            const now = this.ctx.currentTime;
            // First shutter click
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(800, now);
            osc.frequency.exponentialRampToValueAtTime(220, now + 0.04);

            gain.gain.setValueAtTime(0.25, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.04);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now);
            osc.stop(now + 0.04);

            // Second shutter release
            const osc2 = this.ctx.createOscillator();
            const gain2 = this.ctx.createGain();
            osc2.type = 'triangle';
            osc2.frequency.setValueAtTime(540, now + 0.05);
            osc2.frequency.exponentialRampToValueAtTime(110, now + 0.11);

            gain2.gain.setValueAtTime(0.2, now + 0.05);
            gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.11);

            osc2.connect(gain2);
            gain2.connect(this.ctx.destination);

            osc2.start(now + 0.05);
            osc2.stop(now + 0.11);

            if (navigator.vibrate) {
                navigator.vibrate([25, 30, 25]);
            }
        } catch (e) {
            // Audio context not ready
        }
    }
}

export const audio = new AudioEffects();
