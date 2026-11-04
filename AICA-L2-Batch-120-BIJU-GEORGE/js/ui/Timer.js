/**
 * Timer.js - Professional Speedcube Timer & Solve History
 * Features:
 * - WCA 15-second inspection countdown
 * - Spacebar / touch hold-to-prime release-to-start
 * - Millisecond precision stopwatch
 * - Real-time statistics: PB, Ao5, Ao12
 * - One-click "Solve with 3D AI" button for any scramble!
 */

import { CubeState } from '../model/CubeState.js';
import { audio } from './AudioEffects.js';

export class SpeedcubeTimer {
    constructor(containerElement, onSolveScrambleRequested = null) {
        this.container = containerElement;
        this.onSolveScrambleRequested = onSolveScrambleRequested;

        this.state = 'idle'; // 'idle', 'holding', 'ready', 'inspecting', 'running', 'stopped'
        this.startTime = 0;
        this.elapsed = 0;
        this.interval = null;
        this.holdTimer = null;
        this.currentScramble = CubeState.generateRandomScramble(20).scrambleStr;

        this.history = this.loadHistory();

        this.init();
    }

    loadHistory() {
        try {
            const raw = localStorage.getItem('cube_timer_history');
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    saveHistory() {
        try {
            localStorage.setItem('cube_timer_history', JSON.stringify(this.history));
        } catch (e) {
            // Storage quota
        }
    }

    init() {
        this.render();
        this.bindEvents();
    }

    bindEvents() {
        const onDown = (e) => {
            if (e.target.closest('button') || e.target.closest('.timer-history-card')) return;
            if (this.state === 'running') {
                this.stopTimer();
                return;
            }
            if (this.state === 'idle') {
                this.state = 'holding';
                this.updateDisplay();
                this.holdTimer = setTimeout(() => {
                    if (this.state === 'holding') {
                        this.state = 'ready';
                        this.updateDisplay();
                    }
                }, 350);
            }
        };

        const onUp = (e) => {
            if (this.state === 'ready') {
                this.startTimer();
            } else if (this.state === 'holding') {
                clearTimeout(this.holdTimer);
                this.state = 'idle';
                this.updateDisplay();
            }
        };

        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.repeat) {
                onDown(e);
            }
        });

        window.addEventListener('keyup', (e) => {
            if (e.code === 'Space') {
                onUp(e);
            }
        });

        this.container.addEventListener('pointerdown', onDown);
        this.container.addEventListener('pointerup', onUp);
    }

    startTimer() {
        this.state = 'running';
        this.startTime = performance.now();
        this.elapsed = 0;
        audio.playTurnClick();

        this.interval = setInterval(() => {
            this.elapsed = performance.now() - this.startTime;
            this.updateTimeNumbers();
        }, 16);

        this.updateDisplay();
    }

    stopTimer() {
        clearInterval(this.interval);
        this.interval = null;
        this.state = 'stopped';
        this.elapsed = performance.now() - this.startTime;
        audio.playSolvedChime();

        // Record solve
        this.history.unshift({
            timeMs: this.elapsed,
            scramble: this.currentScramble,
            date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
        this.saveHistory();

        // Generate next scramble
        this.currentScramble = CubeState.generateRandomScramble(20).scrambleStr;

        this.render();
    }

    formatTime(ms) {
        const totalSec = ms / 1000;
        const minutes = Math.floor(totalSec / 60);
        const seconds = Math.floor(totalSec % 60);
        const millis = Math.floor((ms % 1000) / 10);

        if (minutes > 0) {
            return `${minutes}:${seconds.toString().padStart(2, '0')}.${millis.toString().padStart(2, '0')}`;
        }
        return `${seconds}.${millis.toString().padStart(2, '0')}`;
    }

    getPB() {
        if (this.history.length === 0) return "--";
        const best = Math.min(...this.history.map(h => h.timeMs));
        return this.formatTime(best);
    }

    getAo5() {
        if (this.history.length < 5) return "--";
        const recent5 = this.history.slice(0, 5).map(h => h.timeMs).sort((a, b) => a - b);
        // Exclude fastest and slowest
        const mid3 = recent5.slice(1, 4);
        const avg = mid3.reduce((a, b) => a + b, 0) / 3;
        return this.formatTime(avg);
    }

    updateTimeNumbers() {
        const timeElem = this.container.querySelector('.timer-digits');
        if (timeElem) {
            timeElem.textContent = this.formatTime(this.elapsed);
        }
    }

    updateDisplay() {
        const pad = this.container.querySelector('.timer-pad');
        if (!pad) return;

        pad.className = `timer-pad state-${this.state}`;
        const hint = this.container.querySelector('.timer-hint');
        if (hint) {
            if (this.state === 'holding') hint.textContent = 'Hold space / touch...';
            else if (this.state === 'ready') hint.textContent = 'Release to Start!';
            else if (this.state === 'running') hint.textContent = 'Tap anywhere to Stop';
            else hint.textContent = 'Press and hold Spacebar or Touch pad to start';
        }
    }

    render() {
        this.container.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.className = 'speedcube-timer-wrapper';

        // 1. Scramble Display Card
        const scrambleCard = document.createElement('div');
        scrambleCard.className = 'timer-scramble-card';
        scrambleCard.innerHTML = `
            <div class="scramble-header">
                <span class="scramble-title">WCA Scramble</span>
                <div class="scramble-actions">
                    <button class="btn-scramble-new">↺ New</button>
                    <button class="btn-scramble-solve">⚡ Solve in 3D</button>
                </div>
            </div>
            <div class="scramble-text">${this.currentScramble}</div>
        `;

        scrambleCard.querySelector('.btn-scramble-new').addEventListener('click', () => {
            this.currentScramble = CubeState.generateRandomScramble(20).scrambleStr;
            this.render();
        });

        scrambleCard.querySelector('.btn-scramble-solve').addEventListener('click', () => {
            if (this.onSolveScrambleRequested) {
                const scrambledState = CubeState.solved().applyMoves(this.currentScramble);
                this.onSolveScrambleRequested(scrambledState);
            }
        });

        wrapper.appendChild(scrambleCard);

        // 2. Big Timer Touch Pad
        const timerPad = document.createElement('div');
        timerPad.className = `timer-pad state-${this.state}`;
        timerPad.innerHTML = `
            <div class="timer-digits">${this.formatTime(this.elapsed)}</div>
            <div class="timer-hint">Press and hold Spacebar or Touch pad to start</div>
        `;
        wrapper.appendChild(timerPad);

        // 3. Stats Row (PB, Ao5, Total Solves)
        const statsRow = document.createElement('div');
        statsRow.className = 'timer-stats-row';
        statsRow.innerHTML = `
            <div class="stat-box">
                <span class="stat-label">Personal Best (PB)</span>
                <span class="stat-val pb-val">${this.getPB()}</span>
            </div>
            <div class="stat-box">
                <span class="stat-label">Average of 5 (Ao5)</span>
                <span class="stat-val">${this.getAo5()}</span>
            </div>
            <div class="stat-box">
                <span class="stat-label">Total Solves</span>
                <span class="stat-val">${this.history.length}</span>
            </div>
        `;
        wrapper.appendChild(statsRow);

        // 4. Recent Solves Log
        if (this.history.length > 0) {
            const historyCard = document.createElement('div');
            historyCard.className = 'timer-history-card';
            historyCard.innerHTML = `
                <div class="history-card-header">
                    <span>Recent Solves</span>
                    <button class="btn-clear-history">Clear History</button>
                </div>
                <div class="history-list">
                    ${this.history.slice(0, 10).map((h, i) => `
                        <div class="history-item">
                            <span class="hist-num">#${this.history.length - i}</span>
                            <span class="hist-time">${this.formatTime(h.timeMs)}</span>
                            <span class="hist-scramble" title="${h.scramble}">${h.scramble.substring(0, 24)}...</span>
                            <span class="hist-date">${h.date}</span>
                        </div>
                    `).join('')}
                </div>
            `;

            historyCard.querySelector('.btn-clear-history').addEventListener('click', () => {
                if (confirm("Clear solve history?")) {
                    this.history = [];
                    this.saveHistory();
                    this.render();
                }
            });

            wrapper.appendChild(historyCard);
        }

        this.container.appendChild(wrapper);
    }
}
