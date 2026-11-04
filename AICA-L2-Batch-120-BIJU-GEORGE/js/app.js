/**
 * app.js - Main Application Orchestrator for CubeSolver PWA
 * Connects 3D rendering, solvers, camera scanner, manual editor, notation guide, and timer.
 */

import { CubeState, CubeColor } from './model/CubeState.js?v=25';
import { KociembaSolver } from './solver/KociembaSolver.js?v=25';
import { LayerByLayerSolver } from './solver/LayerByLayerSolver.js?v=25';
import { Cube3D } from './ui/Cube3D.js?v=25';
import { ManualEditor } from './ui/ManualEditor.js?v=25';
import { CameraScanner } from './ui/CameraScanner.js?v=25';
import { SolutionVisualizer } from './ui/SolutionVisualizer.js?v=25';
import { NotationGuide } from './ui/NotationGuide.js?v=25';
import { SpeedcubeTimer } from './ui/Timer.js?v=25';
import { CubeAcademy } from './ui/CubeAcademy.js?v=25';
import { UserManual } from './ui/UserManual.js?v=25';
import { audio } from './ui/AudioEffects.js?v=25';

class CubeSolverApp {
    constructor() {
        this.currentCube = CubeState.solved();
        this.activeTab = '3d-solver';
        this.selectedAlgorithm = 'optimal'; // 'optimal' or 'beginner'
        this.cube3d = null;
        this.oppositeCube3d = null;
        this.isSyncOppositeOrbit = true;
        this.isSyncingCamera = false;
        this.manualEditor = null;
        this.cameraScanner = null;
        this.solutionVisualizer = null;
        this.notationGuide = null;
        this.speedTimer = null;
        this.cubeAcademy = null;
        this.userManual = null;
        this.deferredInstallPrompt = null;
        this.setupViewMode = 'controls'; // 'controls' or 'reverse'
        this.playerViewMode = 'steps'; // 'steps' or 'reverse'

        this.init();
    }

    init() {
        this.initPWA();
        this.initUI();
        this.init3DCube();
        this.bindEvents();

        // Support direct linking to tabs (e.g. ?tab=manual or #manual)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('tab') === 'manual' || window.location.hash === '#manual') {
            this.switchTab('user-manual');
        } else {
            this.switchTab('3d-solver');
        }
    }

    initPWA() {
        const CURRENT_CACHE = 'cubesolver-pwa-v28';
        // Purge legacy caches immediately
        if ('caches' in window) {
            caches.keys().then(keys => {
                for (const k of keys) {
                    if (k !== CURRENT_CACHE) {
                        console.log('Purging legacy cache key:', k);
                        caches.delete(k);
                    }
                }
            });
        }

        // Register Service Worker for offline capability
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('./sw.js?v=29').then(reg => {
                    console.log('CubeSolver PWA Service Worker registered:', reg.scope);
                    reg.update(); // Always check for fresh service worker
                }).catch(err => {
                    console.warn('Service Worker registration failed:', err);
                });
            });

            let hadController = Boolean(navigator.serviceWorker.controller);
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                if (hadController) {
                    hadController = false;
                    console.log('CubeSolver PWA Service Worker updated in background.');
                }
            });
        }

        // Absolute viewport lock: prevent accidental window scroll drift on desktop
        window.addEventListener('scroll', () => {
            if (window.innerWidth > 820) {
                if (window.scrollX !== 0 || window.scrollY !== 0) {
                    window.scrollTo(0, 0);
                }
            } else if (window.scrollX !== 0) {
                window.scrollTo(0, window.scrollY);
            }
        }, { passive: true });

        // Install prompt handling
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredInstallPrompt = e;
            const installBtn = document.getElementById('btn-pwa-install');
            if (installBtn) installBtn.style.display = 'inline-flex';
        });
    }

    initUI() {
        // Tab switching
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                this.switchTab(tab);
            });
        });

        // PWA Install Button
        const installBtn = document.getElementById('btn-pwa-install');
        if (installBtn) {
            installBtn.addEventListener('click', async () => {
                if (this.deferredInstallPrompt) {
                    this.deferredInstallPrompt.prompt();
                    const choice = await this.deferredInstallPrompt.userChoice;
                    if (choice.outcome === 'accepted') {
                        installBtn.style.display = 'none';
                    }
                    this.deferredInstallPrompt = null;
                }
            });
        }

        // Direct User Manual shortcuts
        const headerManualBtn = document.getElementById('btn-header-manual');
        if (headerManualBtn) {
            headerManualBtn.addEventListener('click', () => {
                this.switchTab('user-manual');
            });
        }

        const cardManualBtn = document.getElementById('btn-card-manual');
        if (cardManualBtn) {
            cardManualBtn.addEventListener('click', () => {
                this.switchTab('user-manual');
            });
        }

        // Sound toggle
        const soundBtn = document.getElementById('btn-sound-toggle');
        if (soundBtn) {
            soundBtn.addEventListener('click', () => {
                const enabled = audio.toggle();
                soundBtn.textContent = enabled ? '🔊' : '🔇';
                soundBtn.setAttribute('title', enabled ? 'Sound On' : 'Sound Muted');
            });
        }
    }

    init3DCube() {
        const container = document.getElementById('cube-3d-canvas-container');
        if (container) {
            this.cube3d = new Cube3D(container, {
                turnSpeedMs: 350,
                // Continuous per-frame antipodal synchronization: 100% real-time tracking
                onRenderFrame: (cam) => {
                    this.syncOppositeCamera(cam);
                }
            });
            this.cube3d.updateFromCubeState(this.currentCube);

            // Reset camera button
            const resetCamBtn = document.getElementById('btn-reset-camera');
            if (resetCamBtn) {
                resetCamBtn.addEventListener('click', () => {
                    this.cube3d.resetCamera();
                    if (this.oppositeCube3d) {
                        this.oppositeCube3d.resetCamera();
                    }
                    audio.playTurnClick();
                });
            }
        }

        // Initialize 360° Opposite Angle 3D Cube (shows occluded faces: Down, Back, Left)
        const oppContainer = document.getElementById('setup-opposite-canvas');
        if (oppContainer && window.THREE) {
            // Canonical opposite isometric angle looking directly at Down (-Y), Back (-Z), Left (-X)
            const canonicalOppositePos = new THREE.Vector3(-5.2, -4.4, -6.2);
            this.oppositeCube3d = new Cube3D(oppContainer, {
                defaultCameraPos: canonicalOppositePos,
                turnSpeedMs: 350,
                enableDamping: false
            });
            this.oppositeCube3d.updateFromCubeState(this.currentCube);

            // In sync mode, secondary OrbitControls is disabled so it doesn't fight antipodal position
            if (this.oppositeCube3d.controls) {
                this.oppositeCube3d.controls.enabled = !this.isSyncOppositeOrbit;
            }

            // Sync opposite camera immediately
            if (this.cube3d) {
                this.syncOppositeCamera(this.cube3d.camera);
            }
        }
    }

    syncOppositeCamera(mainCam) {
        if (!this.isSyncOppositeOrbit || !this.oppositeCube3d || !this.oppositeCube3d.camera) return;
        // Precise antipodal position: exact 180° opposite angle
        const oppPos = mainCam.position.clone().negate();
        this.oppositeCube3d.camera.position.copy(oppPos);
        this.oppositeCube3d.camera.lookAt(0, 0, 0);
        if (this.oppositeCube3d.controls) {
            this.oppositeCube3d.controls.target.set(0, 0, 0);
        }
    }

    attachOppositeCanvas(targetContainerId) {
        if (!this.oppositeCube3d || !this.oppositeCube3d.renderer) return;
        const target = document.getElementById(targetContainerId);
        if (!target) return;
        if (typeof this.oppositeCube3d.setContainer === 'function') {
            this.oppositeCube3d.setContainer(target);
        } else {
            const canvas = this.oppositeCube3d.renderer.domElement;
            if (canvas.parentNode !== target) {
                target.appendChild(canvas);
            }
            this.oppositeCube3d.container = target;
        }
        requestAnimationFrame(() => {
            if (this.oppositeCube3d) this.oppositeCube3d.onResize();
        });
        setTimeout(() => {
            if (this.oppositeCube3d) this.oppositeCube3d.onResize();
        }, 50);
    }

    setOppositeSyncMode(enable) {
        this.isSyncOppositeOrbit = enable;
        const syncButtons = [
            document.getElementById('btn-setup-reverse-sync'),
            document.getElementById('btn-player-reverse-sync')
        ];

        syncButtons.forEach(btn => {
            if (!btn) return;
            if (enable) {
                btn.classList.add('active');
                btn.innerHTML = '<span class="sync-icon">🔗</span> Synced';
                btn.setAttribute('title', '360° Antipodal Camera Tracking active: follows main cube in 100% lockstep');
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '<span class="sync-icon">🔓</span> Free Orbit';
                btn.setAttribute('title', 'Free Orbit mode: drag secondary cube to inspect any angle. Click to re-sync.');
            }
        });

        if (this.oppositeCube3d && this.oppositeCube3d.controls) {
            this.oppositeCube3d.controls.enabled = !enable;
        }

        if (enable && this.cube3d && this.oppositeCube3d) {
            this.syncOppositeCamera(this.cube3d.camera);
        }
    }

    setSetupViewMode(mode) {
        this.setupViewMode = mode;
        const btnControls = document.getElementById('btn-setup-tab-controls');
        const btnReverse = document.getElementById('btn-setup-tab-reverse');
        const bodyControls = document.getElementById('setup-controls-body');
        const bodyReverse = document.getElementById('setup-reverse-body');

        if (mode === 'reverse') {
            if (btnControls) btnControls.classList.remove('active');
            if (btnReverse) btnReverse.classList.add('active');
            if (bodyControls) bodyControls.classList.add('hidden');
            if (bodyReverse) bodyReverse.classList.remove('hidden');
            this.attachOppositeCanvas('setup-opposite-canvas');
        } else {
            if (btnControls) btnControls.classList.add('active');
            if (btnReverse) btnReverse.classList.remove('active');
            if (bodyControls) bodyControls.classList.remove('hidden');
            if (bodyReverse) bodyReverse.classList.add('hidden');
        }
    }

    setPlayerViewMode(mode) {
        this.playerViewMode = mode;
        const btnSteps = document.getElementById('btn-player-tab-steps');
        const btnReverse = document.getElementById('btn-player-tab-reverse');
        const stepsContainer = document.getElementById('solution-visualizer-inline-container');
        const bodyReverse = document.getElementById('player-reverse-body');

        if (mode === 'reverse') {
            if (btnSteps) btnSteps.classList.remove('active');
            if (btnReverse) btnReverse.classList.add('active');
            if (stepsContainer) stepsContainer.classList.add('hidden');
            if (bodyReverse) bodyReverse.classList.remove('hidden');
            this.attachOppositeCanvas('player-opposite-canvas');
            this.updatePlayerReverseBanner();
        } else {
            if (btnSteps) btnSteps.classList.add('active');
            if (btnReverse) btnReverse.classList.remove('active');
            if (stepsContainer) stepsContainer.classList.remove('hidden');
            if (bodyReverse) bodyReverse.classList.add('hidden');
        }
    }

    updatePlayerReverseBanner() {
        if (!this.solutionVisualizer) return;
        const bubble = document.getElementById('player-rev-step-bubble');
        const text = document.getElementById('player-rev-step-text');
        const btnReset = document.getElementById('btn-rev-player-reset');
        const btnPrev = document.getElementById('btn-rev-player-prev');
        const btnPlay = document.getElementById('btn-rev-player-play');
        const btnNext = document.getElementById('btn-rev-player-next');

        const currentStep = this.solutionVisualizer.currentStep;
        const totalMoves = this.solutionVisualizer.moves.length;
        const isSolved = currentStep >= totalMoves;
        const move = !isSolved ? this.solutionVisualizer.moves[currentStep] : 'SOLVED';

        if (bubble) bubble.textContent = isSolved ? '🏁' : move;
        if (text) {
            text.textContent = isSolved
                ? '🎉 Cube Solved! All 6 sides complete.'
                : `Step ${currentStep + 1} of ${totalMoves}: Move ${move}`;
        }
        if (btnReset) btnReset.disabled = currentStep <= 0;
        if (btnPrev) btnPrev.disabled = currentStep <= 0;
        if (btnNext) btnNext.disabled = isSolved;
        if (btnPlay) {
            btnPlay.innerHTML = this.solutionVisualizer.isPlaying
                ? '⏸ Pause'
                : (isSolved ? '↺ Replay' : '▶ Play');
        }
    }

    bindEvents() {
        // Algorithm mode switchers
        document.querySelectorAll('input[name="algo-choice"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.selectedAlgorithm = e.target.value;
                audio.playTurnClick();
            });
        });

        // Setup Card Mode Toggles (Controls vs Reverse 3D)
        const btnSetupControls = document.getElementById('btn-setup-tab-controls');
        if (btnSetupControls) {
            btnSetupControls.addEventListener('click', () => {
                this.setSetupViewMode('controls');
                audio.playTurnClick();
            });
        }
        const btnSetupReverse = document.getElementById('btn-setup-tab-reverse');
        if (btnSetupReverse) {
            btnSetupReverse.addEventListener('click', () => {
                this.setSetupViewMode('reverse');
                audio.playTurnClick();
            });
        }

        // Setup reverse toolbar sync & reset buttons
        const btnSetupRevSync = document.getElementById('btn-setup-reverse-sync');
        if (btnSetupRevSync) {
            btnSetupRevSync.addEventListener('click', () => {
                this.setOppositeSyncMode(!this.isSyncOppositeOrbit);
                audio.playTurnClick();
            });
        }
        const btnSetupRevReset = document.getElementById('btn-setup-reverse-reset');
        if (btnSetupRevReset) {
            btnSetupRevReset.addEventListener('click', () => {
                if (this.oppositeCube3d) {
                    this.oppositeCube3d.resetCamera();
                    this.setOppositeSyncMode(false);
                    audio.playTurnClick();
                }
            });
        }

        // Solution Player Card Mode Toggles (Steps Guide vs Reverse 3D)
        const btnPlayerSteps = document.getElementById('btn-player-tab-steps');
        if (btnPlayerSteps) {
            btnPlayerSteps.addEventListener('click', () => {
                this.setPlayerViewMode('steps');
                audio.playTurnClick();
            });
        }
        const btnPlayerReverse = document.getElementById('btn-player-tab-reverse');
        if (btnPlayerReverse) {
            btnPlayerReverse.addEventListener('click', () => {
                this.setPlayerViewMode('reverse');
                audio.playTurnClick();
            });
        }

        // Player reverse sync button
        const btnPlayerRevSync = document.getElementById('btn-player-reverse-sync');
        if (btnPlayerRevSync) {
            btnPlayerRevSync.addEventListener('click', () => {
                this.setOppositeSyncMode(!this.isSyncOppositeOrbit);
                audio.playTurnClick();
            });
        }

        // Player reverse mini playback buttons
        const btnRevReset = document.getElementById('btn-rev-player-reset');
        if (btnRevReset) {
            btnRevReset.addEventListener('click', () => {
                if (this.solutionVisualizer) {
                    this.solutionVisualizer.goToStep(0);
                    this.updatePlayerReverseBanner();
                }
            });
        }
        const btnRevPrev = document.getElementById('btn-rev-player-prev');
        if (btnRevPrev) {
            btnRevPrev.addEventListener('click', () => {
                if (this.solutionVisualizer) {
                    this.solutionVisualizer.stepBackward();
                    this.updatePlayerReverseBanner();
                }
            });
        }
        const btnRevPlay = document.getElementById('btn-rev-player-play');
        if (btnRevPlay) {
            btnRevPlay.addEventListener('click', () => {
                if (this.solutionVisualizer) {
                    this.solutionVisualizer.togglePlay();
                    this.updatePlayerReverseBanner();
                }
            });
        }
        const btnRevNext = document.getElementById('btn-rev-player-next');
        if (btnRevNext) {
            btnRevNext.addEventListener('click', () => {
                if (this.solutionVisualizer) {
                    this.solutionVisualizer.stepForward();
                    this.updatePlayerReverseBanner();
                }
            });
        }

        // Printable Solution Guide Button in Top Bar
        const btnHeaderPrintGuide = document.getElementById('btn-header-print-guide');
        if (btnHeaderPrintGuide) {
            btnHeaderPrintGuide.addEventListener('click', () => {
                if (this.solutionVisualizer) {
                    this.solutionVisualizer.openPrintableGuide();
                }
            });
        }

        // Quick Face Twists (works in both Controls and Reverse views)
        document.querySelectorAll('.twist-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const move = btn.dataset.move;
                if (move) {
                    const nextState = this.currentCube.applyMove(move);
                    this.currentCube = nextState;
                    this.cube3d.animateMove(move, nextState);
                    if (this.oppositeCube3d) {
                        this.oppositeCube3d.animateMove(move, nextState);
                    }
                    audio.playTurnClick();
                    this.updateSolveButtonState();
                }
            });
        });

        // Preset Patterns Dropdown
        const presetSelect = document.getElementById('preset-pattern-select');
        if (presetSelect) {
            presetSelect.addEventListener('change', (e) => {
                const val = e.target.value;
                if (val) {
                    this.currentCube = CubeState.getPreset(val);
                    this.cube3d.updateFromCubeState(this.currentCube);
                    if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    audio.playTurnClick();
                    this.updateSolveButtonState();
                }
            });
        }

        // Random Scramble Button
        const scrambleBtn = document.getElementById('btn-random-scramble');
        if (scrambleBtn) {
            scrambleBtn.addEventListener('click', () => {
                const { state, scrambleStr } = CubeState.generateRandomScramble(20);
                this.currentCube = state;
                this.cube3d.updateFromCubeState(this.currentCube);
                if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                audio.playTurnClick();

                const scrambleDisplay = document.getElementById('active-scramble-display');
                if (scrambleDisplay) {
                    scrambleDisplay.textContent = scrambleStr;
                }
                this.updateSolveButtonState();
            });
        }

        // Reset to Solved Button
        const resetSolvedBtn = document.getElementById('btn-cube-reset-solved');
        if (resetSolvedBtn) {
            resetSolvedBtn.addEventListener('click', () => {
                this.currentCube = CubeState.solved();
                this.cube3d.updateFromCubeState(this.currentCube);
                if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                audio.playTurnClick();
                this.updateSolveButtonState();
            });
        }

        // Big Primary Solve Button
        const solveBtn = document.getElementById('btn-solve-main');
        if (solveBtn) {
            solveBtn.addEventListener('click', () => {
                this.executeSolve(this.currentCube, this.selectedAlgorithm);
            });
        }

        // Exit Solution Button (Main Stage Inline Player)
        const exitBtn = document.getElementById('btn-exit-solution');
        if (exitBtn) {
            exitBtn.addEventListener('click', () => {
                this.exitSolutionScreen();
            });
        }
    }

    updateSolveButtonState() {
        const solveBtn = document.getElementById('btn-solve-main');
        const statusText = document.getElementById('cube-status-banner');
        const isSolved = this.currentCube.isSolved();

        if (statusText) {
            statusText.textContent = isSolved ? 'Cube is Solved' : 'Cube is Scrambled';
            statusText.className = `status-banner ${isSolved ? 'solved' : 'scrambled'}`;
        }

        if (solveBtn) {
            if (isSolved) {
                solveBtn.classList.add('disabled');
            } else {
                solveBtn.classList.remove('disabled');
            }
        }
    }

    executeSolve(cubeState, algorithmMode = 'optimal') {
        const loadingOverlay = document.getElementById('solver-loading-overlay');
        if (loadingOverlay) loadingOverlay.classList.remove('hidden');

        setTimeout(() => {
            let result;
            if (algorithmMode === 'beginner') {
                result = LayerByLayerSolver.solveWithStages(cubeState);
            } else {
                result = KociembaSolver.solve(cubeState);
            }

            if (loadingOverlay) loadingOverlay.classList.add('hidden');

            if (!result.success) {
                alert(`Solver Notice:\n${result.error || 'Unable to solve this configuration. Please verify colors.'}`);
                return;
            }

            // Launch solution visualizer
            this.showSolutionScreen(cubeState, result, algorithmMode);
        }, 50);
    }

    showSolutionScreen(cubeState, solutionData, algorithmMode) {
        this.switchTab('3d-solver');

        const setupCard = document.getElementById('solver-setup-card');
        const playerCard = document.getElementById('solver-player-card');
        const container = document.getElementById('solution-visualizer-inline-container');

        if (setupCard) {
            setupCard.classList.add('hidden');
            setupCard.style.display = 'none';
        }
        if (playerCard) {
            playerCard.classList.remove('hidden');
            playerCard.style.display = 'flex';
        }

        // Always default to clean, uncramped Steps Guide view
        this.setPlayerViewMode('steps');

        if (!this.solutionVisualizer) {
            this.solutionVisualizer = new SolutionVisualizer(container, this.cube3d, {
                oppositeCube3d: this.oppositeCube3d,
                onSolveCompleted: () => {
                    this.currentCube = CubeState.solved();
                    if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    this.updateSolveButtonState();
                    this.updatePlayerReverseBanner();
                },
                onStepChange: () => {
                    this.updatePlayerReverseBanner();
                }
            });
        }

        this.solutionVisualizer.loadSolution(cubeState, solutionData, algorithmMode);
        this.updatePlayerReverseBanner();

        const exitBtn = document.getElementById('btn-exit-solution');
        if (exitBtn) {
            exitBtn.onclick = () => this.exitSolutionScreen();
        }
    }

    exitSolutionScreen() {
        if (this.solutionVisualizer) {
            this.solutionVisualizer.pause();
        }

        const setupCard = document.getElementById('solver-setup-card');
        const playerCard = document.getElementById('solver-player-card');

        if (playerCard) {
            playerCard.classList.add('hidden');
            playerCard.style.display = 'none';
        }
        if (setupCard) {
            setupCard.classList.remove('hidden');
            setupCard.style.display = 'flex';
        }

        // Return to Controls view in Setup card
        this.setSetupViewMode('controls');

        if (this.cube3d) {
            this.cube3d.clearTurnArrow();
            if (this.cube3d.stopAnimation) this.cube3d.stopAnimation();

            if (this.solutionVisualizer && this.solutionVisualizer.currentStep === this.solutionVisualizer.moves.length) {
                this.currentCube = CubeState.solved();
            } else if (this.solutionVisualizer && this.solutionVisualizer.statesAtSteps) {
                const stepState = this.solutionVisualizer.statesAtSteps[this.solutionVisualizer.currentStep];
                if (stepState) this.currentCube = stepState.clone();
            }
            this.cube3d.updateFromCubeState(this.currentCube);
            if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
        }

        this.updateSolveButtonState();
        window.scrollTo(0, 0);
    }

    switchTab(tabId) {
        this.activeTab = tabId;

        // Update nav buttons
        document.querySelectorAll('.nav-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Hide all views
        document.querySelectorAll('.tab-view-panel').forEach(panel => {
            panel.classList.add('hidden');
        });

        // Show active view
        const activePanel = document.getElementById(`panel-${tabId}`);
        if (activePanel) {
            activePanel.classList.remove('hidden');
        }

        // Cleanly stop camera if navigating away from camera scanner
        if (tabId !== 'camera-scanner' && this.cameraScanner) {
            this.cameraScanner.stopCamera();
        }

        // Lazy initialize or refresh components
        if (tabId === '3d-solver') {
            if (this.cube3d) {
                setTimeout(() => {
                    this.cube3d.onResize();
                    if (this.oppositeCube3d) {
                        this.oppositeCube3d.onResize();
                        this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    }
                }, 100);
            }
        } else if (tabId === 'camera-scanner') {
            const container = document.getElementById('scanner-container');
            if (container && !this.cameraScanner) {
                this.cameraScanner = new CameraScanner(container, (scannedCube) => {
                    this.currentCube = scannedCube;
                    this.cube3d.updateFromCubeState(this.currentCube);
                    if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    this.switchTab('3d-solver');
                    this.executeSolve(scannedCube, this.selectedAlgorithm);
                });
            } else if (this.cameraScanner) {
                this.cameraScanner.autoCaptureEnabled = false;
                this.cameraScanner.isCameraActive = false;
                this.cameraScanner.render();
            }
        } else if (tabId === 'manual-editor') {
            const container = document.getElementById('manual-editor-container');
            if (container && !this.manualEditor) {
                this.manualEditor = new ManualEditor(container, (updatedState) => {
                    this.currentCube = updatedState;
                    this.cube3d.updateFromCubeState(this.currentCube);
                    if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                }, (solveState) => {
                    this.currentCube = solveState;
                    this.cube3d.updateFromCubeState(this.currentCube);
                    if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    this.switchTab('3d-solver');
                    this.executeSolve(solveState, this.selectedAlgorithm);
                });
            } else if (this.manualEditor) {
                this.manualEditor.setCubeState(this.currentCube);
            }
        } else if (tabId === 'notation-guide') {
            const container = document.getElementById('notation-guide-container');
            if (container && !this.notationGuide) {
                this.notationGuide = new NotationGuide(container, (moveNotation) => {
                    this.cube3d.animateMove(moveNotation, () => {
                        this.currentCube = this.currentCube.applyMove(moveNotation);
                        this.cube3d.updateFromCubeState(this.currentCube);
                        if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    });
                });
            }
        } else if (tabId === 'cube-academy') {
            const container = document.getElementById('academy-container');
            if (container && !this.cubeAcademy) {
                this.cubeAcademy = new CubeAcademy(container);
            } else if (this.cubeAcademy) {
                this.cubeAcademy.render();
            }
            setTimeout(() => {
                if (this.cubeAcademy && this.cubeAcademy.cube3d) {
                    this.cubeAcademy.cube3d.onResize();
                }
            }, 80);
        } else if (tabId === 'speed-timer') {
            const container = document.getElementById('speed-timer-container');
            if (container && !this.speedTimer) {
                this.speedTimer = new SpeedcubeTimer(container, (scrambledState) => {
                    this.currentCube = scrambledState;
                    this.cube3d.updateFromCubeState(this.currentCube);
                    if (this.oppositeCube3d) this.oppositeCube3d.updateFromCubeState(this.currentCube);
                    this.switchTab('3d-solver');
                    this.executeSolve(scrambledState, this.selectedAlgorithm);
                });
            }
        } else if (tabId === 'user-manual') {
            const container = document.getElementById('user-manual-container');
            if (container && !this.userManual) {
                this.userManual = new UserManual(container);
            }
        }
    }
}

// Bootstrap app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CubeSolverApp();
});
