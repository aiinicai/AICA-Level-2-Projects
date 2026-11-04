/**
 * ManualEditor.js - Interactive 2D Unfolded Net & Color Palette Editor
 * Renders the 6 faces in standard net layout:
 *        [ U ]
 *  [ L ] [ F ] [ R ] [ B ]
 *        [ D ]
 * Includes live sticker count badges, parity validation, and instant solve triggers.
 */

import { CubeColor, FACE_NAMES, FACE_INDEX, CubeState } from '../model/CubeState.js';
import { KociembaSolver, CubieCube } from '../solver/KociembaSolver.js';
import { audio } from './AudioEffects.js';

export class ManualEditor {
    constructor(containerElement, onStateChange = null, onSolveRequested = null) {
        this.container = containerElement;
        this.onStateChange = onStateChange;
        this.onSolveRequested = onSolveRequested;
        this.selectedColor = 'U'; // White default
        this.cubeState = CubeState.solved();

        this.init();
    }

    setCubeState(newState) {
        this.cubeState = newState.clone();
        this.render();
    }

    getCubeState() {
        return this.cubeState;
    }

    init() {
        this.render();
    }

    render() {
        this.container.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.className = 'manual-editor-wrapper';

        // 1. Color Palette Bar with Live Counts (Single compact horizontal row)
        const paletteBar = this.createPaletteBar();
        wrapper.appendChild(paletteBar);

        // 2. Unfolded 2D Cube Net
        const netContainer = this.createCubeNet();
        wrapper.appendChild(netContainer);

        // 3. Unified Bottom Bar (Validation Pill + Quick Controls + Primary Solve Button)
        const bottomBar = this.createBottomBar();
        wrapper.appendChild(bottomBar);

        this.container.appendChild(wrapper);
    }

    createPaletteBar() {
        const counts = this.cubeState.getColorCounts();
        const bar = document.createElement('div');
        bar.className = 'palette-bar';

        const label = document.createElement('div');
        label.className = 'palette-label';
        label.innerHTML = '<span class="palette-title">🎨 Active Color:</span> <span class="palette-hint">Tap color to paint</span>';
        bar.appendChild(label);

        const swatches = document.createElement('div');
        swatches.className = 'palette-swatches';

        for (const faceKey of FACE_NAMES) {
            const colorInfo = CubeColor[faceKey];
            const count = counts[faceKey];
            const isSelected = this.selectedColor === faceKey;

            const swatch = document.createElement('button');
            swatch.className = `palette-swatch ${isSelected ? 'active' : ''}`;
            swatch.style.setProperty('--swatch-color', colorInfo.hex);
            swatch.setAttribute('aria-label', `Select ${colorInfo.name}`);

            swatch.innerHTML = `
                <span class="swatch-indicator" style="background-color: ${colorInfo.hex}"></span>
                <span class="swatch-name">${colorInfo.name}</span>
                <span class="swatch-count ${count === 9 ? 'count-ok' : (count > 9 ? 'count-err' : 'count-warn')}">${count}/9</span>
            `;

            swatch.addEventListener('click', () => {
                this.selectedColor = faceKey;
                audio.playTurnClick();
                this.render();
            });

            swatches.appendChild(swatch);
        }

        bar.appendChild(swatches);
        return bar;
    }

    createCubeNet() {
        const net = document.createElement('div');
        net.className = 'cube-net-grid';

        // Layout mapping: 3 rows, 4 columns
        // Row 1: empty, U, empty, empty
        // Row 2: L, F, R, B
        // Row 3: empty, D, empty, empty
        const layout = [
            [null, 'U', null, null],
            ['L', 'F', 'R', 'B'],
            [null, 'D', null, null]
        ];

        for (let r = 0; r < 3; r++) {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'cube-net-row';

            for (let c = 0; c < 4; c++) {
                const faceName = layout[r][c];
                if (faceName) {
                    const faceCard = this.createFaceGrid(faceName);
                    rowDiv.appendChild(faceCard);
                } else {
                    const emptyCell = document.createElement('div');
                    emptyCell.className = 'cube-net-empty';
                    rowDiv.appendChild(emptyCell);
                }
            }
            net.appendChild(rowDiv);
        }

        return net;
    }

    createFaceGrid(faceName) {
        const card = document.createElement('div');
        card.className = `face-grid-card face-${faceName.toLowerCase()}`;

        const header = document.createElement('div');
        header.className = 'face-grid-header';
        const colorInfo = CubeColor[faceName];
        header.innerHTML = `<strong>${faceName}</strong> <span class="face-title-sub">(${colorInfo.name})</span>`;
        card.appendChild(header);

        const grid = document.createElement('div');
        grid.className = 'face-3x3-grid';

        const stickers = this.cubeState.getFaceStickers(faceName);

        for (let i = 0; i < 9; i++) {
            const stickerColorLetter = stickers[i];
            const stickerHex = CubeColor[stickerColorLetter]?.hex || '#FFFFFF';
            const isCenter = (i === 4);

            const cell = document.createElement('button');
            cell.className = `net-sticker ${isCenter ? 'center-sticker' : ''}`;
            cell.style.backgroundColor = stickerHex;
            cell.setAttribute('title', `${faceName}${i + 1} (${CubeColor[stickerColorLetter]?.name})`);

            if (isCenter) {
                cell.innerHTML = `<span class="center-letter">${faceName}</span>`;
            }

            cell.addEventListener('click', () => {
                if (isCenter) {
                    // Center defines face orientation
                    return;
                }
                this.cubeState.setSticker(faceName, i, this.selectedColor);
                audio.playTurnClick();
                if (this.onStateChange) this.onStateChange(this.cubeState);
                this.render();
            });

            grid.appendChild(cell);
        }

        card.appendChild(grid);
        return card;
    }

    validateCurrentState() {
        const counts = this.cubeState.getColorCounts();
        for (const f of FACE_NAMES) {
            if (counts[f] !== 9) {
                return {
                    valid: false,
                    message: `Color mismatch: ${CubeColor[f].name} has ${counts[f]} stickers (must be exactly 9).`
                };
            }
        }

        const cc = new CubieCube();
        const parseErr = KociembaSolver.parseFacelets(this.cubeState.toString(), cc);
        if (parseErr) {
            return { valid: false, message: parseErr };
        }

        const parityErr = cc.verify();
        if (parityErr) {
            return { valid: false, message: parityErr };
        }

        return { valid: true, message: "Valid 3x3 Rubik's Cube state. Ready to solve all 6 sides!" };
    }

    createBottomBar() {
        const val = this.validateCurrentState();
        const bar = document.createElement('div');
        bar.className = 'editor-bottom-bar';

        // 1. Validation status pill
        const valPill = document.createElement('div');
        valPill.className = `editor-val-pill ${val.valid ? 'is-valid' : 'is-invalid'}`;
        valPill.innerHTML = `
            <span class="val-pill-icon">${val.valid ? '✓' : '⚠'}</span>
            <div class="val-pill-text">
                <span class="val-pill-title">${val.valid ? 'Cube Validated' : 'Color Notice'}</span>
                <span class="val-pill-desc" title="${val.message}">${val.message}</span>
            </div>
        `;
        bar.appendChild(valPill);

        // 2. Quick buttons: Solved & Scramble
        const quickBtns = document.createElement('div');
        quickBtns.className = 'editor-quick-btns';

        const resetBtn = document.createElement('button');
        resetBtn.className = 'editor-quick-btn';
        resetBtn.innerHTML = '↺ Solved';
        resetBtn.title = 'Reset net to solved state';
        resetBtn.addEventListener('click', () => {
            this.setCubeState(CubeState.solved());
            audio.playTurnClick();
            if (this.onStateChange) this.onStateChange(this.cubeState);
        });
        quickBtns.appendChild(resetBtn);

        const scrambleBtn = document.createElement('button');
        scrambleBtn.className = 'editor-quick-btn';
        scrambleBtn.innerHTML = '🔀 Scramble';
        scrambleBtn.title = 'Scramble net configuration';
        scrambleBtn.addEventListener('click', () => {
            const { state } = CubeState.generateRandomScramble(18);
            this.setCubeState(state);
            audio.playTurnClick();
            if (this.onStateChange) this.onStateChange(this.cubeState);
        });
        quickBtns.appendChild(scrambleBtn);
        bar.appendChild(quickBtns);

        // 3. Primary Solve Action
        const solveBtn = document.createElement('button');
        solveBtn.className = `btn-primary-solve ${val.valid ? 'enabled' : 'disabled'}`;
        solveBtn.innerHTML = `
            <span class="solve-btn-glow"></span>
            <span class="solve-btn-icon">⚡</span>
            <span class="solve-btn-text">Solve All 6 Sides</span>
        `;
        solveBtn.addEventListener('click', () => {
            if (!val.valid) {
                alert(`Please fix cube validation before solving:\n${val.message}`);
                return;
            }
            if (this.onSolveRequested) {
                this.onSolveRequested(this.cubeState);
            }
        });
        bar.appendChild(solveBtn);

        return bar;
    }
}
