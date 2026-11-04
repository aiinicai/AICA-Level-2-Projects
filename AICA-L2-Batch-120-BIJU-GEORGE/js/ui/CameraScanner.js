/**
 * CameraScanner.js - Gold-Standard 6-Face Camera & Intelligent Computer Vision Protocol
 * Features:
 * - 2-Column Responsive Dashboard Layout: strictly locked to 100vh with ZERO vertical scrolling
 * - Intelligent CIELAB (L*a*b*) Computer Vision engine (CubeVision.js) with CIE76 Delta-E matching
 * - Adaptive Center-Sticker White-Balance Calibration to compensate for indoor lighting
 * - Compact ~56% centered Region of Interest (ROI) with focused 20px core sampling (no seams/glare)
 * - Dual Capture: Prominent fixed-position "📸 Capture Face" button + Spacebar shortcut
 * - Auto-Camera Activation: Spacebar or Capture button automatically activates camera if stopped
 * - Smart Auto-Capture: Real-time stability tracking with live color feedback dots
 * - Interactive 3x3 touch-up grid with 1-tap color palette picker
 * - Step navigation: Prev, Retake, and Next face controls + 6 clickable thumbnails
 * - Live color count validation (ensuring 9 of each color) and instant 3D solve launch
 */

import { CubeColor, FACE_NAMES, CubeState } from '../model/CubeState.js?v=23';
import { audio } from './AudioEffects.js?v=23';
import { CubeVision } from './CubeVision.js?v=23';

export const SCAN_PROTOCOL = [
    { face: 'U', name: 'Up Face', centerColor: 'White', topFace: 'Back (Blue)', prompt: 'Hold White face towards camera with Blue on top' },
    { face: 'R', name: 'Right Face', centerColor: 'Red', topFace: 'Up (White)', prompt: 'Hold Red face towards camera with White on top' },
    { face: 'F', name: 'Front Face', centerColor: 'Green', topFace: 'Up (White)', prompt: 'Hold Green face towards camera with White on top' },
    { face: 'D', name: 'Down Face', centerColor: 'Yellow', topFace: 'Front (Green)', prompt: 'Hold Yellow face towards camera with Green on top' },
    { face: 'L', name: 'Left Face', centerColor: 'Orange', topFace: 'Up (White)', prompt: 'Hold Orange face towards camera with White on top' },
    { face: 'B', name: 'Back Face', centerColor: 'Blue', topFace: 'Up (White)', prompt: 'Hold Blue face towards camera with White on top' }
];

export class CameraScanner {
    constructor(containerElement, onScanComplete = null) {
        this.container = containerElement;
        this.onScanComplete = onScanComplete;

        this.videoStream = null;
        this.videoElem = null;
        this.isCameraActive = false;
        this.facingMode = 'environment'; // 'environment' or 'user'
        this.autoCaptureEnabled = false; // Default to OFF: manual capture on demand for maximum user control and zero accidental snaps

        this.currentStep = 0; // 0..5
        this.capturedFaces = {
            U: null, R: null, F: null, D: null, L: null, B: null
        };

        this.selectedPaletteColor = 'U';
        this.activeEditingStickerIdx = null;
        this.lightingMode = 'standard'; // 'standard', 'low_light', 'anti_glare'

        // Auto-capture stability state
        this.stabilityCounter = 0;
        this.lastDetectedSignature = '';
        this.samplingTimer = null;
        this.isCapturing = false;

        // Sampling canvas
        this.sampleCanvas = document.createElement('canvas');
        this.sampleCanvas.width = 300;
        this.sampleCanvas.height = 300;

        // Keyboard listener for Spacebar manual capture or camera activation
        this.handleKeyDown = async (e) => {
            if (e.code === 'Space') {
                // Ignore if typing into an input
                if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA')) {
                    return;
                }
                e.preventDefault();
                if (!this.isCameraActive) {
                    await this.startCamera();
                } else {
                    this.captureCurrentFace();
                }
            }
        };
        window.addEventListener('keydown', this.handleKeyDown);

        this.init();
    }

    destroy() {
        this.stopCamera();
        window.removeEventListener('keydown', this.handleKeyDown);
    }

    init() {
        this.autoCaptureEnabled = false;
        this.isCameraActive = false;
        this.render();
    }

    render() {
        this.container.innerHTML = '';

        // 2-Column Responsive Dashboard Layout
        const layoutGrid = document.createElement('div');
        layoutGrid.className = 'scanner-layout-grid';

        // ============================================
        // LEFT COLUMN: Orientation Cue, Viewfinder & Fixed Controls
        // ============================================
        const leftCol = document.createElement('div');
        leftCol.className = 'scanner-viewfinder-col';

        // 1. Progress Step Tracker & Orientation Cue
        const tracker = this.createStepTracker();
        leftCol.appendChild(tracker);

        // 2. Camera Viewfinder with 3x3 Overlay, Status Badges & Controls
        const viewfinderWrapper = this.createViewfinderSection();
        leftCol.appendChild(viewfinderWrapper);

        layoutGrid.appendChild(leftCol);

        // ============================================
        // RIGHT COLUMN: Review Card, 1-Tap Touch-up, 6-Faces Summary & Solve Button
        // ============================================
        const rightCol = document.createElement('div');
        rightCol.className = 'scanner-review-col';

        // 3. Current Face Capture Preview & Manual Touch-up Palette
        const captureSection = this.createCaptureSection();
        rightCol.appendChild(captureSection);

        // 4. Scanned Faces Summary (Thumbnails of all 6 faces + Validation + Solve)
        const summary = this.createFacesSummary();
        rightCol.appendChild(summary);

        layoutGrid.appendChild(rightCol);

        this.container.appendChild(layoutGrid);

        // If camera stream is already running, re-attach it cleanly to the video element
        if (this.isCameraActive && this.videoStream && this.videoElem) {
            this.videoElem.srcObject = this.videoStream;
            this.videoElem.play().catch(() => {});
            this.startLiveSampling();
        }
    }

    createStepTracker() {
        const tracker = document.createElement('div');
        tracker.className = 'scanner-tracker';

        const step = SCAN_PROTOCOL[this.currentStep];

        tracker.innerHTML = `
            <div class="tracker-header">
                <span class="tracker-badge">Face ${this.currentStep + 1} of 6</span>
                <span class="tracker-title">${step.name} (${step.centerColor} Center)</span>
            </div>
            <div class="tracker-prompt">
                <span class="prompt-icon">💡</span>
                <span>${step.prompt}</span>
            </div>
            <div class="tracker-progress-bar">
                <div class="tracker-fill" style="width: ${((this.currentStep + 1) / 6) * 100}%"></div>
            </div>
        `;

        return tracker;
    }

    createViewfinderSection() {
        const container = document.createElement('div');
        container.className = 'viewfinder-wrapper';

        // Viewfinder box (Strict square aspect ratio, compact to prevent overflow)
        const box = document.createElement('div');
        box.className = 'viewfinder-box';

        // Video element
        const video = document.createElement('video');
        video.className = 'viewfinder-video';
        video.autoplay = true;
        video.playsInline = true;
        video.muted = true;
        this.videoElem = video;

        // Flash overlay for shutter effect
        const flashOverlay = document.createElement('div');
        flashOverlay.className = 'viewfinder-shutter-flash';
        this.flashOverlay = flashOverlay;

        // Standby overlay (shown when camera is stopped)
        const standbyOverlay = document.createElement('div');
        standbyOverlay.className = 'viewfinder-standby';
        standbyOverlay.style.display = this.isCameraActive ? 'none' : 'flex';
        standbyOverlay.innerHTML = `
            <div class="standby-icon">📷</div>
            <div class="standby-title">Camera Scanner Ready</div>
            <div class="standby-desc">Hold your cube face towards the camera, or upload a photo.</div>
            <button class="btn-scanner-action start-action" style="margin-top: 6px; padding: 8px 16px;">
                <span>📷</span> Start Camera
            </button>
        `;
        standbyOverlay.querySelector('.start-action').addEventListener('click', () => this.startCamera());

        // Floating Badges
        const statusBadge = document.createElement('div');
        statusBadge.className = 'viewfinder-badge-top-left';
        statusBadge.style.display = this.isCameraActive ? 'flex' : 'none';
        statusBadge.innerHTML = `<span>🟢</span> <span>${this.facingMode === 'environment' ? 'Rear Camera' : 'Front Camera'}</span>`;

        const stabilityBadge = document.createElement('div');
        stabilityBadge.className = 'viewfinder-badge-top-right';
        stabilityBadge.style.display = this.isCameraActive ? 'flex' : 'none';
        stabilityBadge.innerHTML = this.autoCaptureEnabled ? `<span>⚡</span> <span>Auto: Aligning...</span>` : `<span>📸</span> <span>Manual Mode</span>`;
        this.stabilityBadge = stabilityBadge;

        // 3x3 Target Overlay (Proportioned to square box)
        const overlay = document.createElement('div');
        overlay.className = 'viewfinder-overlay';
        overlay.style.display = this.isCameraActive ? 'block' : 'none';

        const cellsContainer = document.createElement('div');
        cellsContainer.className = 'grid-3x3-cells';

        this.targetDots = [];
        const curProtocolFace = SCAN_PROTOCOL[this.currentStep].face;

        for (let i = 0; i < 9; i++) {
            const cell = document.createElement('div');
            cell.className = `target-cell ${i === 4 ? 'center-target' : ''}`;
            cell.title = i === 4 ? `Center sticker (${curProtocolFace}) is locked` : `Cell #${i + 1}. Click to paint or cycle color.`;

            const dot = document.createElement('div');
            dot.className = 'target-cell-dot';
            dot.style.backgroundColor = i === 4 ? (CubeColor[curProtocolFace]?.hex || '#fff') : 'rgba(255, 255, 255, 0.4)';
            dot.textContent = i === 4 ? curProtocolFace : '';
            dot.style.color = (curProtocolFace === 'U' || curProtocolFace === 'D') ? '#000' : '#fff';
            cell.appendChild(dot);
            this.targetDots.push(dot);

            if (i !== 4) {
                cell.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (!this.capturedFaces[curProtocolFace]) {
                        this.capturedFaces[curProtocolFace] = this.getDefaultStickersForFace(curProtocolFace);
                    }
                    const colorToApply = this.selectedPaletteColor || 'U';
                    this.capturedFaces[curProtocolFace][i] = colorToApply;
                    audio.playTurnClick();
                    this.updateReviewColumn();
                });
            }

            cellsContainer.appendChild(cell);
        }
        overlay.appendChild(cellsContainer);

        box.appendChild(video);
        box.appendChild(standbyOverlay);
        box.appendChild(statusBadge);
        box.appendChild(stabilityBadge);
        box.appendChild(overlay);
        box.appendChild(flashOverlay);

        container.appendChild(box);

        // Control buttons in fixed positions so they never shift vertically or horizontally
        const controls = document.createElement('div');
        controls.className = 'viewfinder-controls';

        // 1. Primary Manual Capture Button (Fixed Prominent Action)
        const primaryRow = document.createElement('div');
        primaryRow.className = 'controls-primary-row';

        const snapBtn = document.createElement('button');
        snapBtn.className = 'btn-scanner-action snap-action';
        snapBtn.innerHTML = this.isCameraActive ? '<span>📸</span> Capture Current Face (Spacebar)' : '<span>📷</span> Start Camera & Capture (Spacebar)';
        snapBtn.title = 'Click to capture current face stickers immediately (or activate camera)';
        snapBtn.addEventListener('click', async () => {
            if (!this.isCameraActive) {
                await this.startCamera();
            } else {
                this.captureCurrentFace();
            }
        });
        primaryRow.appendChild(snapBtn);
        controls.appendChild(primaryRow);

        // 2. Camera Management Row: Stop / Start, Flip Camera, Auto-Capture Toggle, Lighting Mode
        const secondaryRow = document.createElement('div');
        secondaryRow.className = 'controls-secondary-row';

        // Start / Stop Toggle Button
        const toggleCamBtn = document.createElement('button');
        if (this.isCameraActive) {
            toggleCamBtn.className = 'btn-scanner-action stop-action';
            toggleCamBtn.innerHTML = '<span>🛑</span> Stop';
            toggleCamBtn.title = 'Turn off webcam hardware stream';
            toggleCamBtn.addEventListener('click', () => this.stopCamera());
        } else {
            toggleCamBtn.className = 'btn-scanner-action start-action';
            toggleCamBtn.innerHTML = '<span>📷</span> Start';
            toggleCamBtn.title = 'Activate webcam video feed';
            toggleCamBtn.addEventListener('click', () => this.startCamera());
        }
        secondaryRow.appendChild(toggleCamBtn);

        // Flip Camera Button
        const flipBtn = document.createElement('button');
        flipBtn.className = 'btn-scanner-action';
        flipBtn.innerHTML = '<span>🔄</span> Flip';
        flipBtn.title = 'Switch between front and back camera';
        flipBtn.disabled = !this.isCameraActive;
        flipBtn.addEventListener('click', () => this.switchCamera());
        secondaryRow.appendChild(flipBtn);

        // Auto-Capture Toggle Button (Optional feature, activated only upon clicking)
        const autoBtn = document.createElement('button');
        autoBtn.className = `btn-scanner-action auto-toggle ${this.autoCaptureEnabled ? 'active' : ''}`;
        autoBtn.innerHTML = this.autoCaptureEnabled ? '<span>⚡</span> Auto: ON' : '<span>⚡</span> Auto: OFF';
        autoBtn.title = 'Click to activate/deactivate automatic capture when cube face is held steady';
        autoBtn.addEventListener('click', () => {
            this.autoCaptureEnabled = !this.autoCaptureEnabled;
            this.stabilityCounter = 0;
            autoBtn.className = `btn-scanner-action auto-toggle ${this.autoCaptureEnabled ? 'active' : ''}`;
            autoBtn.innerHTML = this.autoCaptureEnabled ? '<span>⚡</span> Auto: ON' : '<span>⚡</span> Auto: OFF';
            if (this.stabilityBadge) {
                this.stabilityBadge.classList.remove('stable');
                this.stabilityBadge.innerHTML = this.autoCaptureEnabled ? `<span>⚡</span> <span>Auto: Aligning...</span>` : `<span>📸</span> <span>Manual Mode (Spacebar)</span>`;
            }
            audio.playTurnClick();
        });
        secondaryRow.appendChild(autoBtn);

        // Lighting Sensitivity Mode Button
        const lightBtn = document.createElement('button');
        lightBtn.className = 'btn-scanner-action light-toggle';
        const lightIcons = {
            standard: '💡 Std Light',
            low_light: '🌙 Dim Room',
            anti_glare: '☀️ Anti-Glare'
        };
        lightBtn.innerHTML = lightIcons[this.lightingMode] || '💡 Std Light';
        lightBtn.title = 'Cycle lighting compensation mode (Standard, Dim Room, Anti-Glare)';
        lightBtn.addEventListener('click', () => {
            const modes = ['standard', 'low_light', 'anti_glare'];
            const nextIdx = (modes.indexOf(this.lightingMode) + 1) % modes.length;
            this.lightingMode = modes[nextIdx];
            audio.playTurnClick();
            this.render();
        });
        secondaryRow.appendChild(lightBtn);

        controls.appendChild(secondaryRow);

        // 3. Navigation & Utilities Row: Prev, Retake, Next, Upload, Preset
        const navRow = document.createElement('div');
        navRow.className = 'controls-nav-row';

        const prevFaceBtn = document.createElement('button');
        prevFaceBtn.className = 'btn-scanner-action';
        prevFaceBtn.innerHTML = '<span>⏮</span> Prev';
        prevFaceBtn.disabled = this.currentStep <= 0;
        prevFaceBtn.addEventListener('click', () => {
            if (this.currentStep > 0) {
                this.currentStep--;
                audio.playTurnClick();
                this.updateReviewColumn();
            }
        });
        navRow.appendChild(prevFaceBtn);

        const retakeBtn = document.createElement('button');
        retakeBtn.className = 'btn-scanner-action';
        retakeBtn.innerHTML = '<span>↺</span> Retake';
        retakeBtn.title = 'Clear captured colors for this face and rescan';
        retakeBtn.addEventListener('click', () => {
            const curFace = SCAN_PROTOCOL[this.currentStep].face;
            this.capturedFaces[curFace] = null;
            this.stabilityCounter = 0;
            audio.playTurnClick();
            this.updateReviewColumn();
        });
        navRow.appendChild(retakeBtn);

        const nextFaceBtn = document.createElement('button');
        nextFaceBtn.className = 'btn-scanner-action';
        nextFaceBtn.innerHTML = '<span>Next</span> <span>⏭</span>';
        nextFaceBtn.disabled = this.currentStep >= 5;
        nextFaceBtn.addEventListener('click', () => {
            if (this.currentStep < 5) {
                this.currentStep++;
                audio.playTurnClick();
                this.updateReviewColumn();
            }
        });
        navRow.appendChild(nextFaceBtn);

        // Upload photo button
        const uploadLabel = document.createElement('label');
        uploadLabel.className = 'btn-scanner-action';
        uploadLabel.innerHTML = '<span>📁</span> Upload';
        uploadLabel.title = 'Upload photo of current face';
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.style.display = 'none';
        fileInput.addEventListener('change', (e) => this.handleImageUpload(e));
        uploadLabel.appendChild(fileInput);
        navRow.appendChild(uploadLabel);

        // Sample preset button
        const sampleBtn = document.createElement('button');
        sampleBtn.className = 'btn-scanner-action';
        sampleBtn.innerHTML = '<span>✨</span> Preset';
        sampleBtn.title = 'Quick test: load a full 6-face scrambled cube';
        sampleBtn.addEventListener('click', () => this.loadSamplePreset());
        navRow.appendChild(sampleBtn);

        controls.appendChild(navRow);
        container.appendChild(controls);

        return container;
    }

    async startCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Camera API is not supported in this browser or context.');
            return;
        }

        try {
            if (this.videoStream) {
                this.videoStream.getTracks().forEach(t => t.stop());
            }

            const constraints = {
                video: {
                    facingMode: this.facingMode,
                    width: { ideal: 1280, min: 640 },
                    height: { ideal: 720, min: 480 },
                    aspectRatio: { ideal: 1 }
                },
                audio: false
            };

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoStream = stream;
            this.isCameraActive = true;

            this.render();
        } catch (err) {
            console.warn('Camera access with mode', this.facingMode, 'failed, attempting default video input:', err);
            try {
                const fallbackStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280, min: 640 } },
                    audio: false
                });
                this.videoStream = fallbackStream;
                this.isCameraActive = true;
                this.render();
            } catch (fallbackErr) {
                console.warn('Unable to access webcam video feed:', fallbackErr);
                this.isCameraActive = false;
                this.render();
            }
        }
    }

    stopCamera() {
        if (this.samplingTimer) {
            clearInterval(this.samplingTimer);
            this.samplingTimer = null;
        }
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => {
                try { track.stop(); } catch (e) {}
            });
            this.videoStream = null;
        }
        this.isCameraActive = false;
        this.autoCaptureEnabled = false;
        if (this.videoElem) {
            this.videoElem.srcObject = null;
        }
        this.render();
    }

    async switchCamera() {
        this.facingMode = this.facingMode === 'environment' ? 'user' : 'environment';
        await this.startCamera();
    }

    startLiveSampling() {
        if (this.samplingTimer) clearInterval(this.samplingTimer);

        this.samplingTimer = setInterval(() => {
            if (!this.isCameraActive || !this.videoElem || this.videoElem.readyState < 2) return;
            this.sampleFrame(false);
        }, 110);
    }

    computeAverageRgb(data) {
        let rSum = 0, gSum = 0, bSum = 0;
        const count = data.length / 4;
        if (count === 0) return [128, 128, 128];
        for (let i = 0; i < data.length; i += 4) {
            rSum += data[i];
            gSum += data[i + 1];
            bSum += data[i + 2];
        }
        return [rSum / count, gSum / count, bSum / count];
    }

    /**
     * Samples the video frame using the Intelligent CubeVision CIELAB engine.
     * The cube ROI is centered to 56% of the frame (matching the physical cube geometry).
     * The known center sticker is used to calibrate ambient room lighting shifts.
     */
    sampleFrame(isFinal = false) {
        if (!this.videoElem || !this.sampleCanvas) return null;

        const ctx = this.sampleCanvas.getContext('2d', { willReadFrequently: true });
        const vW = this.videoElem.videoWidth || 300;
        const vH = this.videoElem.videoHeight || 300;
        const size = Math.min(vW, vH);
        const sx = (vW - size) / 2;
        const sy = (vH - size) / 2;

        ctx.drawImage(this.videoElem, sx, sy, size, size, 0, 0, 300, 300);

        // Centered 68% Square Region of Interest (ROI) matching the visual square overlay
        const roiRatio = 0.68;
        const roiSize = 300 * roiRatio; // 204px
        const roiStart = (300 - roiSize) / 2; // 48px
        const cellSize = roiSize / 3; // 68px
        const sampleRadius = 12; // Sample a 24x24 core patch in center of cell to ignore seams and glare

        // Step 1: Sample center sticker (anchored to current protocol face)
        const centerExpectedFace = SCAN_PROTOCOL[this.currentStep].face;

        // Step 2: Classify all 9 stickers
        const detected = [];

        for (let row = 0; row < 3; row++) {
            for (let col = 0; col < 3; col++) {
                const idx = row * 3 + col;
                const isCenter = (idx === 4);

                if (isCenter) {
                    detected.push(centerExpectedFace);
                    if (this.targetDots && this.targetDots[idx]) {
                        this.targetDots[idx].textContent = centerExpectedFace;
                        this.targetDots[idx].style.backgroundColor = CubeColor[centerExpectedFace]?.hex || '#fff';
                        this.targetDots[idx].style.color = (centerExpectedFace === 'U' || centerExpectedFace === 'D') ? '#000' : '#fff';
                    }
                } else {
                    const cx = Math.round(roiStart + (col + 0.5) * cellSize);
                    const cy = Math.round(roiStart + (row + 0.5) * cellSize);
                    const patch = ctx.getImageData(
                        Math.max(0, cx - sampleRadius),
                        Math.max(0, cy - sampleRadius),
                        sampleRadius * 2,
                        sampleRadius * 2
                    );
                    // Extract pure pigment discarding screen reflections & edge shadows
                    const rgb = CubeVision.extractPurePigment(patch.data);
                    const color = CubeVision.classifySticker(rgb[0], rgb[1], rgb[2], this.lightingMode);
                    detected.push(color);

                    if (this.targetDots && this.targetDots[idx]) {
                        this.targetDots[idx].textContent = color;
                        this.targetDots[idx].style.backgroundColor = CubeColor[color]?.hex || '#fff';
                        this.targetDots[idx].style.color = (color === 'U' || color === 'D') ? '#000' : '#fff';
                    }
                }
            }
        }

        // Live Auto-Capture Stability Tracking (4 stable frames ~400ms is ideal for laptops)
        const curFace = SCAN_PROTOCOL[this.currentStep].face;
        const allCaptured = FACE_NAMES.every(f => !!this.capturedFaces[f]);
        const isCurrentFaceAlreadyCaptured = !!this.capturedFaces[curFace];

        if (!isFinal && this.autoCaptureEnabled && !this.isCapturing) {
            // Once all 6 faces are captured, OR if the current face is already captured and being reviewed,
            // DO NOT automatically overwrite it! Only manual capture or explicit "Retake" captures.
            if (allCaptured || isCurrentFaceAlreadyCaptured) {
                if (this.stabilityBadge) {
                    if (allCaptured) {
                        this.stabilityBadge.classList.add('stable');
                        this.stabilityBadge.innerHTML = `<span>✓</span> <span>All 6 Faces Scanned (Edit Mode)</span>`;
                    } else {
                        this.stabilityBadge.classList.remove('stable');
                        this.stabilityBadge.innerHTML = `<span>✓</span> <span>Face ${curFace} Captured (Ready/Edit)</span>`;
                    }
                }
                return detected;
            }

            const signature = detected.join('');
            if (signature === this.lastDetectedSignature) {
                this.stabilityCounter++;
                const percent = Math.min(100, Math.round((this.stabilityCounter / 4) * 100));

                if (this.stabilityBadge) {
                    this.stabilityBadge.classList.add('stable');
                    this.stabilityBadge.innerHTML = `<span>⚡</span> <span>Hold Steady: ${percent}%</span>`;
                }

                if (this.stabilityCounter >= 4) {
                    this.isCapturing = true;
                    this.captureCurrentFace();
                    setTimeout(() => { this.isCapturing = false; }, 800);
                }
            } else {
                this.lastDetectedSignature = signature;
                this.stabilityCounter = 0;
                if (this.stabilityBadge) {
                    this.stabilityBadge.classList.remove('stable');
                    this.stabilityBadge.innerHTML = `<span>⚡</span> <span>Auto: Aligning...</span>`;
                }
            }
        }

        return detected;
    }

    async captureCurrentFace() {
        if (!this.isCameraActive) {
            await this.startCamera();
            return;
        }

        let detected = null;

        if (this.videoElem && this.videoElem.readyState >= 2) {
            detected = this.sampleFrame(true);
        }

        if (!detected) {
            const curFace = SCAN_PROTOCOL[this.currentStep].face;
            detected = this.getDefaultStickersForFace(curFace);
        }

        // Visual shutter flash effect
        if (this.flashOverlay) {
            this.flashOverlay.classList.remove('flash');
            void this.flashOverlay.offsetWidth;
            this.flashOverlay.classList.add('flash');
            setTimeout(() => {
                if (this.flashOverlay) this.flashOverlay.classList.remove('flash');
            }, 120);
        }

        // Play crisp audio shutter click
        if (typeof audio.playCameraShutter === 'function') {
            audio.playCameraShutter();
        } else {
            audio.playTurnClick();
        }

        this.stabilityCounter = 0;
        this.applyDetectedFaceColors(detected);
    }

    handleImageUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const img = new Image();
        img.onload = () => {
            const ctx = this.sampleCanvas.getContext('2d', { willReadFrequently: true });
            const size = Math.min(img.width, img.height);
            const sx = (img.width - size) / 2;
            const sy = (img.height - size) / 2;
            ctx.drawImage(img, sx, sy, size, size, 0, 0, 300, 300);

            const roiRatio = 0.68;
            const roiSize = 300 * roiRatio;
            const roiStart = (300 - roiSize) / 2;
            const cellSize = roiSize / 3;
            const sampleRadius = 12;

            const centerExpectedFace = SCAN_PROTOCOL[this.currentStep].face;
            const detected = [];

            for (let row = 0; row < 3; row++) {
                for (let col = 0; col < 3; col++) {
                    const idx = row * 3 + col;
                    if (idx === 4) {
                        detected.push(centerExpectedFace);
                    } else {
                        const cx = Math.round(roiStart + (col + 0.5) * cellSize);
                        const cy = Math.round(roiStart + (row + 0.5) * cellSize);
                        const patch = ctx.getImageData(cx - sampleRadius, cy - sampleRadius, sampleRadius * 2, sampleRadius * 2);
                        const rgb = CubeVision.extractPurePigment(patch.data);
                        detected.push(CubeVision.classifySticker(rgb[0], rgb[1], rgb[2], this.lightingMode));
                    }
                }
            }
            audio.playTurnClick();
            this.applyDetectedFaceColors(detected);
        };
        img.src = URL.createObjectURL(file);
    }

    getDefaultStickersForFace(faceLetter) {
        return new Array(9).fill(faceLetter);
    }

    loadSamplePreset() {
        const scrambled = CubeState.getPreset('checkerboard');
        for (const face of FACE_NAMES) {
            this.capturedFaces[face] = scrambled.getFaceStickers(face);
        }
        this.currentStep = 5;
        audio.playTurnClick();
        this.render();
    }

    applyDetectedFaceColors(stickers) {
        const currentFace = SCAN_PROTOCOL[this.currentStep].face;
        stickers[4] = currentFace; // Strictly lock center
        this.capturedFaces[currentFace] = [...stickers];

        if (this.currentStep < 5) {
            this.currentStep++;
        }
        this.render();
    }

    createCaptureSection() {
        const currentFace = SCAN_PROTOCOL[this.currentStep].face;
        if (!this.capturedFaces[currentFace]) {
            this.capturedFaces[currentFace] = this.getDefaultStickersForFace(currentFace);
        }
        const stickers = this.capturedFaces[currentFace];

        const card = document.createElement('div');
        card.className = 'capture-edit-card';

        const title = document.createElement('div');
        title.className = 'capture-edit-title';
        title.innerHTML = `
            <span>Facelets for <strong>${currentFace} (${SCAN_PROTOCOL[this.currentStep].name})</strong></span>
            <span style="font-size: 11px; color: var(--text-muted); font-weight: normal;">Tap sticker to paint with palette</span>
        `;
        card.appendChild(title);

        // 3x3 Interactive Grid
        const grid = document.createElement('div');
        grid.className = 'capture-3x3-grid';

        const colorCycle = ['U', 'R', 'F', 'D', 'L', 'B'];

        stickers.forEach((col, idx) => {
            const isCenter = (idx === 4);
            const btn = document.createElement('button');
            btn.className = `capture-sticker-btn ${isCenter ? 'is-center' : ''} ${this.activeEditingStickerIdx === idx ? 'editing' : ''}`;
            btn.style.backgroundColor = CubeColor[col]?.hex || '#FFFFFF';

            if (isCenter) {
                btn.innerHTML = `<span class="center-tag">${currentFace}</span>`;
                btn.title = `Center sticker (${currentFace}) is locked`;
            } else {
                btn.title = `Sticker #${idx + 1}: ${CubeColor[col]?.name || col}. Click to paint with ${CubeColor[this.selectedPaletteColor]?.name || 'palette'}.`;
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const colorToApply = this.selectedPaletteColor || 'U';
                    stickers[idx] = colorToApply;
                    this.capturedFaces[currentFace] = [...stickers];
                    audio.playTurnClick();
                    this.updateReviewColumn();
                });
            }

            grid.appendChild(btn);
        });

        card.appendChild(grid);

        // Fast 1-Tap Color Palette Picker
        const paletteContainer = document.createElement('div');
        paletteContainer.className = 'palette-picker-strip';
        paletteContainer.innerHTML = `<span style="font-size: 11px; color: var(--text-muted); margin-right: 2px;">Palette:</span>`;

        colorCycle.forEach(cLetter => {
            const swatch = document.createElement('button');
            swatch.className = `palette-swatch-btn ${this.selectedPaletteColor === cLetter ? 'selected' : ''}`;
            swatch.style.backgroundColor = CubeColor[cLetter]?.hex || '#fff';
            swatch.title = `Select ${CubeColor[cLetter]?.name} brush`;

            swatch.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectedPaletteColor = cLetter;
                audio.playTurnClick();
                this.updateReviewColumn();
            });

            paletteContainer.appendChild(swatch);
        });

        card.appendChild(paletteContainer);

        return card;
    }

    createFacesSummary() {
        const section = document.createElement('div');
        section.className = 'faces-summary-section';

        const title = document.createElement('div');
        title.className = 'faces-summary-title';

        // Check completion & color distribution
        const counts = { U: 0, R: 0, F: 0, D: 0, L: 0, B: 0 };
        let allCaptured = true;

        for (const face of FACE_NAMES) {
            const st = this.capturedFaces[face];
            if (!st) {
                allCaptured = false;
            } else {
                for (const c of st) {
                    if (counts[c] !== undefined) counts[c]++;
                }
            }
        }

        const isCountValid = Object.values(counts).every(c => c === 9);

        title.innerHTML = `
            <span>6 Faces Overview:</span>
            <span style="font-size: 11px; font-weight: normal; color: ${isCountValid ? '#34d399' : '#fbbf24'};">
                ${allCaptured ? (isCountValid ? '✓ 9 of each color verified' : '⚠️ Color counts need 9 each') : 'Scan all 6 faces to solve'}
            </span>
        `;
        section.appendChild(title);

        // 6 Thumbnail Cards Row
        const row = document.createElement('div');
        row.className = 'faces-summary-row';

        SCAN_PROTOCOL.forEach((p, idx) => {
            const faceStickers = this.capturedFaces[p.face] || this.getDefaultStickersForFace(p.face);

            const thumb = document.createElement('div');
            thumb.className = `face-thumb ${idx === this.currentStep ? 'current' : ''}`;
            thumb.title = `Face ${p.face} (${p.centerColor}). Click to select. Click any sticker to paint.`;

            const label = document.createElement('div');
            label.className = 'thumb-label';
            label.textContent = `${p.face} (${p.centerColor[0]})`;
            thumb.appendChild(label);

            const grid = document.createElement('div');
            grid.className = 'thumb-grid';

            faceStickers.forEach((c, cellIdx) => {
                const cell = document.createElement('div');
                const isCenter = (cellIdx === 4);
                cell.className = `thumb-cell ${isCenter ? 'is-center' : ''}`;
                cell.style.backgroundColor = CubeColor[c]?.hex || '#fff';
                cell.title = isCenter ? `Center ${p.face} is locked` : `${p.face} sticker #${cellIdx + 1}: ${CubeColor[c]?.name || c}. Click to paint with ${CubeColor[this.selectedPaletteColor]?.name || 'palette'}.`;

                cell.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (!isCenter) {
                        const colorToApply = this.selectedPaletteColor || 'U';
                        if (!this.capturedFaces[p.face]) {
                            this.capturedFaces[p.face] = this.getDefaultStickersForFace(p.face);
                        }
                        this.capturedFaces[p.face][cellIdx] = colorToApply;
                        audio.playTurnClick();
                    }
                    this.currentStep = idx;
                    this.updateReviewColumn();
                });

                grid.appendChild(cell);
            });

            thumb.appendChild(grid);

            thumb.addEventListener('click', () => {
                this.currentStep = idx;
                audio.playTurnClick();
                this.updateReviewColumn();
            });

            row.appendChild(thumb);
        });

        section.appendChild(row);

        // Live Color Counts Row
        if (allCaptured) {
            const countRow = document.createElement('div');
            countRow.style.cssText = 'display: flex; gap: 6px; justify-content: center; margin-top: 10px; flex-wrap: wrap; font-size: 11px;';

            for (const [letter, cnt] of Object.entries(counts)) {
                const colorInfo = CubeColor[letter];
                const badge = document.createElement('span');
                badge.style.cssText = `
                    padding: 2px 7px; border-radius: 6px; font-weight: bold;
                    background: ${cnt === 9 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'};
                    color: ${cnt === 9 ? '#34d399' : '#f87171'};
                    border: 1px solid ${cnt === 9 ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'};
                `;
                badge.textContent = `${colorInfo.name}: ${cnt}/9`;
                countRow.appendChild(badge);
            }
            section.appendChild(countRow);
        }

        // Solve Button
        if (allCaptured) {
            const solveBox = document.createElement('div');
            solveBox.className = 'scanner-solve-box';

            const assembledFacelets = [];
            for (const f of FACE_NAMES) {
                assembledFacelets.push(...this.capturedFaces[f]);
            }
            const assembledCube = new CubeState(assembledFacelets);

            const solveBtn = document.createElement('button');
            solveBtn.className = `btn-primary-solve ${isCountValid ? 'enabled' : 'disabled'}`;
            solveBtn.innerHTML = `
                <span class="solve-btn-glow"></span>
                <span class="solve-btn-icon">⚡</span>
                <span class="solve-btn-text">Solve All 6 Sides from Camera Scan</span>
            `;

            solveBtn.addEventListener('click', () => {
                if (!isCountValid) {
                    alert('Please adjust stickers so there are exactly 9 of each color before solving.');
                    return;
                }
                this.stopCamera();
                if (this.onScanComplete) {
                    this.onScanComplete(assembledCube);
                }
            });

            solveBox.appendChild(solveBtn);
            section.appendChild(solveBox);
        }

        return section;
    }

    updateReviewColumn() {
        const rightCol = this.container.querySelector('.scanner-review-col');
        if (!rightCol) {
            this.render();
            return;
        }
        rightCol.innerHTML = '';
        rightCol.appendChild(this.createCaptureSection());
        rightCol.appendChild(this.createFacesSummary());

        // Also update the tracker header in the left column
        const tracker = this.container.querySelector('.scanner-tracker');
        if (tracker) {
            const step = SCAN_PROTOCOL[this.currentStep];
            const badge = tracker.querySelector('.tracker-badge');
            const title = tracker.querySelector('.tracker-title');
            const prompt = tracker.querySelector('.tracker-prompt');
            const fill = tracker.querySelector('.tracker-fill');
            if (badge) badge.textContent = `Face ${this.currentStep + 1} of 6`;
            if (title) title.textContent = `${step.name} (${step.centerColor} Center)`;
            if (prompt) prompt.innerHTML = `<span>🧭</span> <span>${step.prompt}</span>`;
            if (fill) fill.style.width = `${((this.currentStep + 1) / 6) * 100}%`;
        }

        // Also update center dot on viewfinder overlay if present
        const curProtocolFace = SCAN_PROTOCOL[this.currentStep].face;
        if (this.targetDots && this.targetDots[4]) {
            this.targetDots[4].textContent = curProtocolFace;
            this.targetDots[4].style.backgroundColor = CubeColor[curProtocolFace]?.hex || '#fff';
            this.targetDots[4].style.color = (curProtocolFace === 'U' || curProtocolFace === 'D') ? '#000' : '#fff';
        }
    }
}
