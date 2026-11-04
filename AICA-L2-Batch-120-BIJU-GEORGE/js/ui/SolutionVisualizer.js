/**
 * SolutionVisualizer.js - Step-by-Step Interactive Solution Controller
 * Features:
 * - Full 3D animated playback with animation locks preventing race conditions
 * - Stationary viewport: strictly contained timeline scrolling with zero window drift
 * - Electric Neon Fuchsia turn arrows with high-contrast dual strokes
 * - Prominent Back-face turn guidance & callouts for B, B', B2
 * - Explicit plain-English instructions (Clockwise / Anticlockwise, Left / Right / Up / Down)
 * - Live Front-Face 9-sticker combination verification grid for physical cube alignment
 * - Complete Printable Solution Guide (Diagram Sheet) modal with printer-ready layout
 * - Scrubbable move timeline chips
 * - Speed control slider (150ms to 2000ms)
 * - Victory celebration on all 6 sides solved!
 */

import { CubeColor, CubeState } from '../model/CubeState.js';
import { audio } from './AudioEffects.js';
import { SolutionDiagram, MOVE_DIRECTIONS } from './SolutionDiagram.js';

export const MOVE_DESCRIPTIONS = {
    "U": "Turn Top layer to the LEFT (Clockwise)",
    "U'": "Turn Top layer to the RIGHT (Anticlockwise)",
    "U2": "Turn Top layer to the LEFT 180° (Half turn)",
    "D": "Turn Bottom layer to the RIGHT (Clockwise)",
    "D'": "Turn Bottom layer to the LEFT (Anticlockwise)",
    "D2": "Turn Bottom layer to the RIGHT 180° (Half turn)",
    "R": "Turn Right layer UP away from you (Clockwise)",
    "R'": "Turn Right layer DOWN towards you (Anticlockwise)",
    "R2": "Turn Right layer UP 180° (Half turn)",
    "L": "Turn Left layer DOWN towards you (Clockwise)",
    "L'": "Turn Left layer UP away from you (Anticlockwise)",
    "L2": "Turn Left layer DOWN 180° (Half turn)",
    "F": "Rotate Front face CLOCKWISE (Top moves to Right)",
    "F'": "Rotate Front face ANTICLOCKWISE (Top moves to Left)",
    "F2": "Rotate Front face 180° (Two quarter turns)",
    "B": "Turn Back layer to the LEFT (Clockwise when looking at back)",
    "B'": "Turn Back layer to the RIGHT (Anticlockwise when looking at back)",
    "B2": "Turn Back layer to the LEFT 180° (Half turn)"
};

export class SolutionVisualizer {
    constructor(containerElement, cube3d, options = {}) {
        this.container = containerElement;
        this.cube3d = cube3d;
        this.options = Object.assign({
            oppositeCube3d: null,
            onSolveCompleted: null,
            onStepChange: null
        }, options);

        this.initialState = null;
        this.moves = [];
        this.stages = []; // For beginner method
        this.statesAtSteps = []; // Precalculated states for 0..N
        this.currentStep = 0;
        this.isPlaying = false;
        this.isAnimating = false;
        this.playTimer = null;
        this.speedMs = 450;
        this.activeMethod = 'optimal'; // 'optimal' or 'beginner'

        this.onSaveSolve = options.onSaveSolve || null;
        this.onSolveCompleted = options.onSolveCompleted || null;

        // Persistent DOM element references (never destroyed between steps)
        this.domBuilt = false;
        this.wrapper = null;
        this.controlsBar = null;
        this.buttonsRow = null;
        this.resetBtn = null;
        this.prevBtn = null;
        this.playBtn = null;
        this.nextBtn = null;
        this.speedRow = null;
        this.speedSlider = null;
        this.speedVal = null;
        this.speedHint = null;
        this.header = null;
        this.counterEl = null;
        this.progressFill = null;
        this.moveCard = null;
        this.timeline = null;
        this.timelineChips = [];
        this.solvedChip = null;
        this.stagesSection = null;
        this.stageCards = [];

        // Stationary keyboard navigation shortcuts
        this.handleKeyDown = (e) => {
            const playerCard = document.getElementById('solver-player-card');
            if (!playerCard || playerCard.classList.contains('hidden')) return;

            const tag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
            if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

            if (e.key === 'ArrowRight' || e.key === 'Enter') {
                e.preventDefault();
                this.stepForward();
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.stepBackward();
            } else if (e.key === ' ' || e.code === 'Space') {
                e.preventDefault();
                this.togglePlay();
            } else if (e.key === 'r' || e.key === 'R' || e.key === 'Home') {
                e.preventDefault();
                this.goToStep(0);
            }
        };
        window.addEventListener('keydown', this.handleKeyDown);
    }

    loadSolution(initialState, solutionData, method = 'optimal') {
        this.initialState = initialState.clone();
        this.activeMethod = method;

        if (method === 'beginner' && solutionData.stages) {
            this.moves = solutionData.totalMoves || [];
            this.stages = solutionData.stages || [];
        } else {
            this.moves = solutionData.moves || [];
            this.stages = [];
        }

        // Precalculate states at every step
        this.statesAtSteps = [this.initialState.clone()];
        let curr = this.initialState.clone();
        for (const mv of this.moves) {
            curr = curr.applyMove(mv);
            this.statesAtSteps.push(curr.clone());
        }

        this.currentStep = 0;
        this.isPlaying = false;
        this.isAnimating = false;
        if (this.playTimer) clearTimeout(this.playTimer);
        if (this.cube3d && this.cube3d.stopAnimation) this.cube3d.stopAnimation();

        // Build stationary persistent DOM skeleton ONCE for this solution
        this.buildDOM();
        this.syncCube3d();
        this.updateView();
    }

    syncCube3d() {
        if (!this.cube3d) return;
        const state = this.statesAtSteps[this.currentStep] || this.statesAtSteps[0];
        this.cube3d.updateFromCubeState(state);
        if (this.options.oppositeCube3d) {
            this.options.oppositeCube3d.updateFromCubeState(state);
        }

        const nextMove = this.currentStep < this.moves.length ? this.moves[this.currentStep] : null;
        if (nextMove) {
            this.cube3d.showTurnArrow(nextMove);
        } else {
            this.cube3d.clearTurnArrow();
        }
    }

    goToStep(targetStep) {
        if (targetStep < 0 || targetStep > this.moves.length) return;
        this.pause();
        if (this.cube3d && this.cube3d.stopAnimation) {
            this.cube3d.stopAnimation();
        }
        if (this.options.oppositeCube3d && this.options.oppositeCube3d.stopAnimation) {
            this.options.oppositeCube3d.stopAnimation();
        }
        this.isAnimating = false;
        this.currentStep = targetStep;
        this.syncCube3d();
        this.updateView();

        if (this.currentStep === this.moves.length) {
            audio.playSolvedChime();
            if (this.onSolveCompleted) this.onSolveCompleted();
        }
    }

    stepForward() {
        if (this.isAnimating || this.currentStep >= this.moves.length) return;
        this.isAnimating = true;

        const move = this.moves[this.currentStep];
        const nextState = this.statesAtSteps[this.currentStep + 1];

        if (this.options.oppositeCube3d) {
            this.options.oppositeCube3d.animateMove(move, nextState, () => {});
        }

        this.cube3d.animateMove(move, nextState, () => {
            this.isAnimating = false;
            this.currentStep++;
            audio.playTurnClick();
            this.syncCube3d();
            this.updateView();

            if (this.currentStep === this.moves.length) {
                this.pause();
                audio.playSolvedChime();
                if (this.onSolveCompleted) this.onSolveCompleted();
            } else if (this.isPlaying) {
                this.playTimer = setTimeout(() => this.stepForward(), this.speedMs);
            }
        });
    }

    stepBackward() {
        if (this.currentStep <= 0) return;
        this.pause();
        if (this.cube3d && this.cube3d.stopAnimation) {
            this.cube3d.stopAnimation();
        }
        if (this.options.oppositeCube3d && this.options.oppositeCube3d.stopAnimation) {
            this.options.oppositeCube3d.stopAnimation();
        }
        this.isAnimating = false;
        this.currentStep--;
        audio.playTurnClick();
        this.syncCube3d();
        this.updateView();
    }

    play() {
        if (this.isPlaying) return;
        if (this.currentStep >= this.moves.length) {
            this.currentStep = 0;
            this.syncCube3d();
        }
        this.isPlaying = true;
        this.updateView();
        if (!this.isAnimating) {
            this.stepForward();
        }
    }

    pause() {
        this.isPlaying = false;
        if (this.playTimer) {
            clearTimeout(this.playTimer);
            this.playTimer = null;
        }
        this.updateView();
    }

    togglePlay() {
        if (this.isPlaying) this.pause();
        else this.play();
    }

    render() {
        if (!this.domBuilt) {
            this.buildDOM();
        }
        this.updateView();
    }

    buildDOM() {
        this.container.innerHTML = '';

        this.wrapper = document.createElement('div');
        this.wrapper.className = 'solution-visualizer-wrapper';

        // 1. STATIONARY CONTROLS BAR (ELEMENT #1: ANCHORED AT ABSOLUTE TOP OF PLAYER CARD)
        // Integrates 4 Playback buttons, Step counter & Speed control, and Slim Progress indicator
        this.controlsBar = this.createControlsBar();
        this.wrapper.appendChild(this.controlsBar);

        // 2. MOVE CARD: Active move description & 3D/2D diagrams (ELEMENT #2)
        this.moveCard = document.createElement('div');
        this.moveCard.className = 'active-move-card';
        this.wrapper.appendChild(this.moveCard);

        // 3. STEPS SECTION: Populates the available card space with full move sequence
        this.stepsSection = this.createStepsSection();
        this.wrapper.appendChild(this.stepsSection);

        // 4. STAGES: 7-Stage breakdown (ELEMENT #4, if beginner method)
        if (this.activeMethod === 'beginner' && this.stages.length > 0) {
            this.stagesSection = this.createStagesSection();
            this.wrapper.appendChild(this.stagesSection);
        } else {
            this.stagesSection = null;
        }

        this.container.appendChild(this.wrapper);
        this.domBuilt = true;
    }

    createControlsBar() {
        const bar = document.createElement('div');
        bar.className = 'solution-controls-bar';

        this.buttonsRow = document.createElement('div');
        this.buttonsRow.className = 'controls-buttons-row';

        // 1. Reset button (Slot 1)
        this.resetBtn = document.createElement('button');
        this.resetBtn.className = 'ctrl-btn ghost-btn';
        this.resetBtn.innerHTML = '↺ Reset';
        this.resetBtn.title = 'Reset to Step 0 (Start of solution) [Key: R]';
        this.resetBtn.addEventListener('click', () => this.goToStep(0));

        // 2. Prev button (Slot 2)
        this.prevBtn = document.createElement('button');
        this.prevBtn.className = 'ctrl-btn';
        this.prevBtn.innerHTML = '⏮ Prev';
        this.prevBtn.title = 'Previous move [Key: ←]';
        this.prevBtn.disabled = this.currentStep <= 0;
        this.prevBtn.addEventListener('click', () => this.stepBackward());

        // 3. Play/Pause/Replay button (Slot 3)
        this.playBtn = document.createElement('button');
        this.playBtn.className = 'ctrl-btn play-btn';
        this.playBtn.innerHTML = '▶ Play';
        this.playBtn.title = 'Auto-play solution [Key: Space]';
        this.playBtn.addEventListener('click', () => {
            if (this.isPlaying) {
                this.pause();
            } else if (this.currentStep >= this.moves.length) {
                this.goToStep(0);
                this.play();
            } else {
                this.play();
            }
        });

        // 4. Next button (Slot 4 - ALWAYS pinned to Column 4, glowing cyan, stationary)
        this.nextBtn = document.createElement('button');
        this.nextBtn.className = 'ctrl-btn next-btn';
        this.nextBtn.innerHTML = 'Next ⏭';
        this.nextBtn.title = 'Execute next move [Key: → or Enter]';
        this.nextBtn.disabled = this.currentStep >= this.moves.length;
        this.nextBtn.addEventListener('click', () => this.stepForward());

        this.buttonsRow.appendChild(this.resetBtn);
        this.buttonsRow.appendChild(this.prevBtn);
        this.buttonsRow.appendChild(this.playBtn);
        this.buttonsRow.appendChild(this.nextBtn);

        // Speed & Step counter row (Balanced row below buttons)
        this.speedRow = document.createElement('div');
        this.speedRow.className = 'controls-speed-row';
        this.speedRow.innerHTML = `
            <div class="controls-status-group">
                <span class="solution-counter">Step 1 of ${this.moves.length}</span>
            </div>
            <div class="controls-speed-group">
                <span class="speed-label-text">⚡</span>
                <input type="range" class="speed-slider" min="150" max="1500" step="50" value="${this.speedMs}" title="Adjust animation and step speed">
                <strong class="speed-val">${(this.speedMs / 1000).toFixed(1)}s</strong>
            </div>
        `;
        this.counterEl = this.speedRow.querySelector('.solution-counter');
        this.speedSlider = this.speedRow.querySelector('.speed-slider');
        this.speedVal = this.speedRow.querySelector('.speed-val');
        this.speedSlider.addEventListener('input', (e) => {
            this.speedMs = parseInt(e.target.value);
            if (this.cube3d) this.cube3d.options.turnSpeedMs = Math.round(this.speedMs * 0.75);
            if (this.options.oppositeCube3d) this.options.oppositeCube3d.options.turnSpeedMs = Math.round(this.speedMs * 0.75);
            if (this.speedVal) this.speedVal.textContent = `${(this.speedMs / 1000).toFixed(1)}s`;
        });

        // Integrated Slim Progress Line at bottom of controls bar
        const progressBar = document.createElement('div');
        progressBar.className = 'solution-progress-bar';
        this.progressFill = document.createElement('div');
        this.progressFill.className = 'solution-progress-fill';
        this.progressFill.style.width = '0%';
        progressBar.appendChild(this.progressFill);

        bar.appendChild(this.buttonsRow);
        bar.appendChild(this.speedRow);
        bar.appendChild(progressBar);

        return bar;
    }

    createStepsSection() {
        const section = document.createElement('div');
        section.className = 'solution-steps-section';

        const header = document.createElement('div');
        header.className = 'steps-section-header';
        header.innerHTML = `
            <div class="steps-header-left">
                <span class="steps-header-icon">📋</span>
                <span class="steps-header-title">Move Sequence (${this.moves.length} steps)</span>
            </div>
            <div class="steps-header-hint">Click any step to jump</div>
        `;
        section.appendChild(header);

        this.timeline = this.createTimeline();
        section.appendChild(this.timeline);

        return section;
    }

    createTimeline() {
        const timeline = document.createElement('div');
        timeline.className = 'moves-timeline';
        this.timelineChips = [];

        this.moves.forEach((m, idx) => {
            const chip = document.createElement('button');
            chip.className = `move-chip ${idx === this.currentStep ? 'current' : ''} ${idx < this.currentStep ? 'done' : ''}`;
            chip.innerHTML = `<span class="chip-step-num">${idx + 1}.</span><span class="chip-move-name">${m}</span>`;
            chip.title = `Step ${idx + 1}: ${m}`;

            chip.addEventListener('click', () => {
                this.pause();
                this.goToStep(idx);
            });

            timeline.appendChild(chip);
            this.timelineChips.push(chip);
        });

        // Final Solved Status Chip
        this.solvedChip = document.createElement('button');
        const isSolved = this.currentStep >= this.moves.length;
        this.solvedChip.className = `move-chip solved-chip ${isSolved ? 'current' : ''}`;
        this.solvedChip.innerHTML = '<span>🏁 Solved</span>';
        this.solvedChip.title = 'Jump to Solved State (all 6 faces complete)';
        this.solvedChip.addEventListener('click', () => {
            this.pause();
            this.goToStep(this.moves.length);
        });
        timeline.appendChild(this.solvedChip);

        return timeline;
    }

    createStagesSection() {
        const section = document.createElement('div');
        section.className = 'stages-section';
        this.stageCards = [];

        const title = document.createElement('div');
        title.className = 'stages-section-title';
        title.innerHTML = '<span>📚 7-Stage Learning Walkthrough</span> <span class="text-xs text-slate-400">Click any stage to jump</span>';
        section.appendChild(title);

        this.stages.forEach((stg) => {
            const isStageDone = this.currentStep >= stg.endIndex;
            const isStageActive = this.currentStep >= stg.startIndex && this.currentStep < stg.endIndex;

            const card = document.createElement('div');
            card.className = `stage-card ${isStageActive ? 'active' : ''} ${isStageDone ? 'done' : ''}`;

            card.innerHTML = `
                <div class="stage-card-header">
                    <span class="stage-title">${stg.title}</span>
                    <span class="stage-pill">${stg.moveCount} moves</span>
                </div>
                <div class="stage-desc">${stg.description}</div>
                <div class="stage-cue"><strong>Cue:</strong> ${stg.cue}</div>
            `;

            card.addEventListener('click', () => {
                this.pause();
                this.goToStep(stg.startIndex);
            });

            section.appendChild(card);
            this.stageCards.push(card);
        });

        return section;
    }

    updateView() {
        if (!this.controlsBar) return;

        const totalMoves = this.moves.length;
        const isSolved = this.currentStep >= totalMoves;
        const progressPercent = totalMoves === 0 ? 100 : Math.round((this.currentStep / totalMoves) * 100);

        // 1. Update buttons in-place (Permanent DOM nodes - ZERO movement)
        if (this.prevBtn) {
            this.prevBtn.disabled = this.currentStep <= 0;
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = isSolved;
        }
        if (this.playBtn) {
            if (this.isPlaying) {
                this.playBtn.innerHTML = '⏸ Pause';
                this.playBtn.title = 'Pause playback [Key: Space]';
            } else if (isSolved) {
                this.playBtn.innerHTML = '↺ Replay';
                this.playBtn.title = 'Replay solution from start';
            } else {
                this.playBtn.innerHTML = '▶ Play';
                this.playBtn.title = 'Auto-play solution [Key: Space]';
            }
        }

        // 2. Update Step Counter & Progress bar in-place
        if (this.counterEl) {
            const counterText = isSolved
                ? `🎉 Solved! (${totalMoves}/${totalMoves})`
                : (totalMoves === 0 ? 'Cube is Solved' : `Step ${this.currentStep + 1} of ${totalMoves}`);
            this.counterEl.textContent = counterText;
            this.counterEl.style.color = isSolved ? '#34d399' : '';
        }
        if (this.progressFill) {
            this.progressFill.style.width = `${progressPercent}%`;
        }

        // 3. Update Move Card in-place (placed BELOW controls)
        if (this.moveCard) {
            this.updateMoveCardContent();
        }

        // 4. Update Timeline chips in-place
        if (this.timelineChips) {
            this.timelineChips.forEach((chip, idx) => {
                const isCurrent = idx === this.currentStep;
                const isDone = idx < this.currentStep;
                chip.className = `move-chip ${isCurrent ? 'current' : ''} ${isDone ? 'done' : ''}`;
            });
        }
        if (this.solvedChip) {
            this.solvedChip.className = `move-chip solved-chip ${isSolved ? 'current' : ''}`;
        }

        // Keep active chip in view inside timeline smoothly (strictly within container, never window scroll!)
        if (this.timeline) {
            const currentChip = isSolved ? this.solvedChip : this.timelineChips[this.currentStep];
            if (currentChip) {
                const cTop = currentChip.offsetTop - this.timeline.offsetTop;
                const cBottom = cTop + currentChip.offsetHeight;
                const sTop = this.timeline.scrollTop;
                const sBottom = sTop + this.timeline.clientHeight;

                if (cTop < sTop || cBottom > sBottom) {
                    this.timeline.scrollTo({
                        top: Math.max(0, cTop - 8),
                        behavior: 'smooth'
                    });
                }
            }
        }

        // 5. Update Stages section if beginner
        if (this.stagesSection && this.stageCards) {
            this.stages.forEach((stg, idx) => {
                const card = this.stageCards[idx];
                if (card) {
                    const isStageDone = this.currentStep >= stg.endIndex;
                    const isStageActive = this.currentStep >= stg.startIndex && this.currentStep < stg.endIndex;
                    card.className = `stage-card ${isStageActive ? 'active' : ''} ${isStageDone ? 'done' : ''}`;
                }
            });
        }

        // 6. External onStepChange hook (for syncing reverse 3D banner & player controls)
        if (typeof this.options.onStepChange === 'function') {
            const currentMove = !isSolved ? this.moves[this.currentStep] : 'SOLVED';
            const desc = isSolved ? 'Cube Solved! All 6 sides complete.' : (MOVE_DESCRIPTIONS[currentMove] || `Move ${currentMove}`);
            this.options.onStepChange(this.currentStep, totalMoves, currentMove, desc, this.isPlaying);
        }
    }

    updateMoveCardContent() {
        const isSolved = this.currentStep >= this.moves.length;
        const currentState = this.statesAtSteps[this.currentStep] || this.statesAtSteps[0];

        if (isSolved) {
            this.moveCard.className = 'active-move-card solved-state';
            const solvedSvg = SolutionDiagram.renderStepSvg(currentState, 'SOLVED', 110, 95, { showMultiplier: false });
            const frontSvg = SolutionDiagram.renderFrontFaceGridSvg(currentState, 54, 54);

            this.moveCard.innerHTML = `
                <div class="solved-banner">
                    <span class="solved-trophy" style="font-size: 26px; margin-bottom: 2px;">🎉</span>
                    <div class="solved-title" style="font-size: 15px; font-weight: 800; color: #34d399;">Cube Solved! All 6 Sides Complete!</div>
                    <div class="solved-subtitle" style="font-size: 11px; margin-top: 2px; color: var(--text-muted);">Every face (White, Yellow, Green, Blue, Red, Orange) is in solved state.</div>
                    <div class="active-move-visual-row">
                        <div class="active-diagram-container">
                            <div class="visual-panel-title">📐 Solved Isometric</div>
                            <div class="active-diagram-svg">
                                ${solvedSvg}
                            </div>
                        </div>
                        <div class="active-front-ref-container">
                            <div class="visual-panel-title">🟩 Front Face (Green)</div>
                            <div class="active-front-ref-content">
                                <div class="front-ref-grid-box">
                                    ${frontSvg}
                                </div>
                                <div class="front-ref-text-box">
                                    <div class="front-ref-prompt" style="color: #34d399;">All Faces Verified</div>
                                    <div class="front-ref-instruction" style="color: #94a3b8; font-size: 10px;">
                                        Front shows solid Green. Top is White, Right is Red, Left is Orange, Down is Yellow, Back is Blue.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        this.moveCard.className = 'active-move-card';
        const moveStr = this.moves[this.currentStep];
        const moveInfo = MOVE_DIRECTIONS[moveStr] || { mult: 'X1', desc: MOVE_DESCRIPTIONS[moveStr] || `Apply move ${moveStr}` };
        const desc = moveInfo.desc;
        const mult = moveInfo.mult;

        const isBackMove = moveStr && (moveStr.startsWith('B'));
        const guidanceBannerHtml = isBackMove ? `
            <div class="move-guidance-banner is-back">
                <span class="callout-icon">🔄</span>
                <span><strong>BACK LAYER (${moveStr}):</strong> Look above top-back edge! Turn back layer <strong>${moveStr.includes("'") ? 'to RIGHT (Anticlockwise)' : 'to LEFT (Clockwise)'}</strong>.</span>
            </div>
        ` : '';

        const stepSvg = SolutionDiagram.renderStepSvg(currentState, moveStr, 110, 95, { showStickerLetters: true, showMultiplier: false });
        const frontGridSvg = SolutionDiagram.renderFrontFaceGridSvg(currentState, 54, 54);

        this.moveCard.innerHTML = `
            <div class="move-bubble-wrapper">
                <div class="move-bubble">${moveStr}</div>
                <div class="move-desc-block">
                    <div class="move-desc-title">Step ${this.currentStep + 1} of ${this.moves.length}: ${desc}</div>
                    <div class="move-desc-hint">Multiplier: <strong>${mult}</strong> • Follow glowing neon fuchsia arrow & front alignment</div>
                </div>
            </div>

            ${guidanceBannerHtml}

            <div class="active-move-visual-row">
                <div class="active-diagram-container">
                    <div class="visual-panel-title">📐 Move Diagram</div>
                    <div class="active-diagram-svg">
                        ${stepSvg}
                    </div>
                </div>

                <div class="active-front-ref-container">
                    <div class="visual-panel-title">🟩 Front Face Alignment</div>
                    <div class="active-front-ref-content">
                        <div class="front-ref-grid-box">
                            ${frontGridSvg}
                        </div>
                        <div class="front-ref-text-box">
                            <div class="front-ref-prompt">Alignment Check:</div>
                            <div class="front-ref-instruction">
                                Match <strong>Front (Green Center)</strong> to this pattern before turning.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    openPrintableGuide() {
        let modal = document.getElementById('printable-sheet-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'printable-sheet-modal';
            modal.className = 'printable-modal';
            document.body.appendChild(modal);
        }

        const algoName = this.activeMethod === 'beginner' ? 'Beginner Layer-by-Layer' : 'Optimal Kociemba Algorithm';
        modal.innerHTML = SolutionDiagram.generatePrintableSheetHtml(this.initialState, this.moves, algoName);
        modal.classList.remove('hidden');

        // Prevent body scrolling behind modal
        document.body.style.overflow = 'hidden';

        const closeBtn = modal.querySelector('#btn-close-print-view');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
            });
        }

        const triggerPrintBtn = modal.querySelector('#btn-trigger-print');
        if (triggerPrintBtn) {
            triggerPrintBtn.addEventListener('click', () => {
                window.print();
            });
        }
    }
}
