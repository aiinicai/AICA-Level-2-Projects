/**
 * Cube3D.js - Three.js WebGL Interactive 3D Rubik's Cube
 * Features:
 * - 27 cubies with realistic plastic bevels & vibrant stickers
 * - Face labels on center pieces for instant spatial orientation
 * - Smooth slice turn animations with easing
 * - 3D glowing directional arrows showing turn direction
 * - Full touch & mouse OrbitControls with camera reset
 */

import { CubeState, CubeColor, FACE_INDEX } from '../model/CubeState.js';

export class Cube3D {
    constructor(containerElement, options = {}) {
        this.container = containerElement;
        this.options = Object.assign({
            cubeSize: 3,
            spacing: 0.05,
            cubieSize: 0.95,
            turnSpeedMs: 350
        }, options);

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.cubies = []; // 3x3x3 array of meshes
        this.pivotGroup = null;
        this.arrowGroup = null;
        this.isAnimating = false;
        this.animQueue = [];
        this.activeMove = null;

        this.init();
    }

    init() {
        const width = this.container.clientWidth || 320;
        const height = this.container.clientHeight || 320;

        // Scene
        this.scene = new THREE.Scene();

        // Camera
        this.camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
        this.defaultCameraPos = this.options.defaultCameraPos
            ? this.options.defaultCameraPos.clone()
            : new THREE.Vector3(5.2, 4.4, 6.2);
        this.camera.position.copy(this.defaultCameraPos);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);

        // Controls
        if (window.THREE && window.THREE.OrbitControls) {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = this.options.enableDamping !== false;
            this.controls.dampingFactor = 0.06;
            this.controls.minDistance = 3.5;
            this.controls.maxDistance = 15;
            this.controls.enablePan = false;

            this.controls.addEventListener('change', () => {
                if (typeof this.options.onCameraChange === 'function') {
                    this.options.onCameraChange(this.camera, this.controls);
                }
            });
        }

        // Lighting: Balanced ambient and soft directional fills to maintain 100% color integrity at all angles
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.78);
        this.scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.22);
        dirLight1.position.set(10, 16, 12);
        this.scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.15);
        dirLight2.position.set(-10, -10, -10);
        this.scene.add(dirLight2);

        // Third light for negative angle illumination (Down, Back, Left)
        const dirLight3 = new THREE.DirectionalLight(0xffffff, 0.14);
        dirLight3.position.set(-12, -16, -14);
        this.scene.add(dirLight3);

        // Pivot group for slice turns
        this.pivotGroup = new THREE.Group();
        this.scene.add(this.pivotGroup);

        // Arrow group for 3D turn indicators
        this.arrowGroup = new THREE.Group();
        this.scene.add(this.arrowGroup);

        // Animation lock
        this.isAnimating = false;
        this.animationFrameId = null;

        // Build 27 cubies
        this.buildCubies();
        this.updateFromCubeState(CubeState.solved());

        // Handle resize
        this.resizeObserver = new ResizeObserver(() => this.onResize());
        this.resizeObserver.observe(this.container);

        // Render loop
        this.animate = this.animate.bind(this);
        requestAnimationFrame(this.animate);
    }

    setContainer(newContainer) {
        if (!newContainer) return;
        if (this.resizeObserver && this.container) {
            try { this.resizeObserver.unobserve(this.container); } catch (e) {}
        }
        this.container = newContainer;
        if (this.renderer && this.renderer.domElement) {
            if (this.renderer.domElement.parentNode !== newContainer) {
                newContainer.appendChild(this.renderer.domElement);
            }
        }
        if (this.resizeObserver && this.container) {
            try { this.resizeObserver.observe(this.container); } catch (e) {}
        }
        this.onResize();
    }

    onResize() {
        const parent = (this.renderer && this.renderer.domElement && this.renderer.domElement.parentElement) || this.container;
        if (!parent || !this.renderer || !this.camera) return;
        const width = parent.clientWidth;
        const height = parent.clientHeight;
        if (width === 0 || height === 0) return;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    resetCamera() {
        if (!this.camera || !this.controls) return;
        this.camera.position.copy(this.defaultCameraPos);
        this.controls.target.set(0, 0, 0);
        this.controls.update();
        if (typeof this.options.onCameraChange === 'function') {
            this.options.onCameraChange(this.camera, this.controls);
        }
    }

    setCameraPosition(pos) {
        if (!this.camera) return;
        this.camera.position.copy(pos);
        this.camera.lookAt(0, 0, 0);
        if (this.controls) {
            this.controls.target.set(0, 0, 0);
        }
    }

    buildCubies() {
        const size = this.options.cubieSize;
        const geometry = new THREE.BoxGeometry(size, size, size);

        // Materials: [Right(+x), Left(-x), Up(+y), Down(-y), Front(+z), Back(-z)]
        // Default dark inner plastic (matte finish, no glare)
        const darkMaterial = new THREE.MeshStandardMaterial({
            color: 0x18181b,
            roughness: 0.85,
            metalness: 0.0
        });

        this.cubies = [];

        for (let x = -1; x <= 1; x++) {
            for (let y = -1; y <= 1; y++) {
                for (let z = -1; z <= 1; z++) {
                    const materials = [
                        darkMaterial.clone(), // +X (R)
                        darkMaterial.clone(), // -X (L)
                        darkMaterial.clone(), // +Y (U)
                        darkMaterial.clone(), // -Y (D)
                        darkMaterial.clone(), // +Z (F)
                        darkMaterial.clone()  // -Z (B)
                    ];

                    const cubie = new THREE.Mesh(geometry, materials);
                    cubie.position.set(x, y, z);
                    cubie.userData = { origX: x, origY: y, origZ: z };
                    this.scene.add(cubie);
                    this.cubies.push(cubie);
                }
            }
        }
    }

    /**
     * Updates all sticker colors from a CubeState instance.
     */
    updateFromCubeState(cubeState) {
        if (!cubeState || !cubeState.facelets) return;

        // Ensure 100% canonical unrotated cubie alignment before setting colors
        this.resetCubiesCanonical();

        // Map facelet indices to cubie coordinates & face material indices
        // Order: [Right, Left, Up, Down, Front, Back]
        // U face (0..8): y = +1, z from -1 to 1 (top to bottom), x from -1 to 1 (left to right)
        // Kociemba U order:
        // 0: (-1, 1, -1), 1: (0, 1, -1), 2: (1, 1, -1)
        // 3: (-1, 1, 0),  4: (0, 1, 0),  5: (1, 1, 0)
        // 6: (-1, 1, 1),  7: (0, 1, 1),  8: (1, 1, 1)
        const uCoords = [
            [-1, 1, -1], [0, 1, -1], [1, 1, -1],
            [-1, 1, 0],  [0, 1, 0],  [1, 1, 0],
            [-1, 1, 1],  [0, 1, 1],  [1, 1, 1]
        ];

        // R face (9..17): x = +1, y from 1 down to -1, z from 1 down to -1
        // 9: (1, 1, 1),   10: (1, 1, 0),  11: (1, 1, -1)
        // 12: (1, 0, 1),  13: (1, 0, 0),  14: (1, 0, -1)
        // 15: (1, -1, 1), 16: (1, -1, 0), 17: (1, -1, -1)
        const rCoords = [
            [1, 1, 1],  [1, 1, 0],  [1, 1, -1],
            [1, 0, 1],  [1, 0, 0],  [1, 0, -1],
            [1, -1, 1], [1, -1, 0], [1, -1, -1]
        ];

        // F face (18..26): z = +1, y from 1 down to -1, x from -1 to 1
        // 18: (-1, 1, 1), 19: (0, 1, 1), 20: (1, 1, 1)
        // 21: (-1, 0, 1), 22: (0, 0, 1), 23: (1, 0, 1)
        // 24: (-1, -1, 1),25: (0, -1, 1),26: (1, -1, 1)
        const fCoords = [
            [-1, 1, 1],  [0, 1, 1],  [1, 1, 1],
            [-1, 0, 1],  [0, 0, 1],  [1, 0, 1],
            [-1, -1, 1], [0, -1, 1], [1, -1, 1]
        ];

        // D face (27..35): y = -1, z from 1 down to -1, x from -1 to 1
        // 27: (-1, -1, 1), 28: (0, -1, 1), 29: (1, -1, 1)
        // 30: (-1, -1, 0), 31: (0, -1, 0), 32: (1, -1, 0)
        // 33: (-1, -1, -1),34: (0, -1, -1),35: (1, -1, -1)
        const dCoords = [
            [-1, -1, 1],  [0, -1, 1],  [1, -1, 1],
            [-1, -1, 0],  [0, -1, 0],  [1, -1, 0],
            [-1, -1, -1], [0, -1, -1], [1, -1, -1]
        ];

        // L face (36..44): x = -1, y from 1 down to -1, z from -1 to 1
        // 36: (-1, 1, -1), 37: (-1, 1, 0), 38: (-1, 1, 1)
        // 39: (-1, 0, -1), 40: (-1, 0, 0), 41: (-1, 0, 1)
        // 42: (-1, -1, -1),43: (-1, -1, 0),44: (-1, -1, 1)
        const lCoords = [
            [-1, 1, -1],  [-1, 1, 0],  [-1, 1, 1],
            [-1, 0, -1],  [-1, 0, 0],  [-1, 0, 1],
            [-1, -1, -1], [-1, -1, 0], [-1, -1, 1]
        ];

        // B face (45..53): z = -1, y from 1 down to -1, x from 1 down to -1
        // 45: (1, 1, -1),  46: (0, 1, -1),  47: (-1, 1, -1)
        // 48: (1, 0, -1),  49: (0, 0, -1),  50: (-1, 0, -1)
        // 51: (1, -1, -1), 52: (0, -1, -1), 53: (-1, -1, -1)
        const bCoords = [
            [1, 1, -1],  [0, 1, -1],  [-1, 1, -1],
            [1, 0, -1],  [0, 0, -1],  [-1, 0, -1],
            [1, -1, -1], [0, -1, -1], [-1, -1, -1]
        ];

        const faceConfigs = [
            { start: 0,  matIdx: 2, coords: uCoords, label: 'U' }, // Up (+Y, mat index 2)
            { start: 9,  matIdx: 0, coords: rCoords, label: 'R' }, // Right (+X, mat index 0)
            { start: 18, matIdx: 4, coords: fCoords, label: 'F' }, // Front (+Z, mat index 4)
            { start: 27, matIdx: 3, coords: dCoords, label: 'D' }, // Down (-Y, mat index 3)
            { start: 36, matIdx: 1, coords: lCoords, label: 'L' }, // Left (-X, mat index 1)
            { start: 45, matIdx: 5, coords: bCoords, label: 'B' }  // Back (-Z, mat index 5)
        ];

        for (const cfg of faceConfigs) {
            for (let i = 0; i < 9; i++) {
                const colorLetter = cubeState.facelets[cfg.start + i];
                const colorHex = CubeColor[colorLetter]?.hex || '#FFFFFF';
                const [cx, cy, cz] = cfg.coords[i];
                const isCenter = (i === 4);

                const cubie = this.getCubieAt(cx, cy, cz);
                if (cubie) {
                    const mat = cubie.material[cfg.matIdx];
                    // Matte speedcube sticker finish: 0% specular glare, 100% color integrity at all angles
                    mat.roughness = 0.95;
                    mat.metalness = 0.0;

                    // If center piece, render tasteful texture label with full color fidelity
                    if (isCenter) {
                        mat.map = this.createStickerTexture(colorHex, cfg.label);
                        mat.color.set('#FFFFFF');
                        mat.needsUpdate = true;
                    } else {
                        mat.color.set(colorHex);
                        if (mat.map) {
                            mat.map = null;
                            mat.needsUpdate = true;
                        }
                    }
                }
            }
        }
    }

    createStickerTexture(bgHex, labelText) {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');

        // Background
        ctx.fillStyle = bgHex;
        ctx.fillRect(0, 0, 128, 128);

        // Subtle rounded border
        ctx.strokeStyle = 'rgba(0,0,0,0.2)';
        ctx.lineWidth = 6;
        ctx.strokeRect(4, 4, 120, 120);

        // Center Letter
        ctx.fillStyle = (bgHex === '#FFFFFF' || bgHex === '#FACC15') ? '#18181b' : '#ffffff';
        ctx.font = 'bold 54px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(labelText, 64, 66);

        const texture = new THREE.CanvasTexture(canvas);
        return texture;
    }

    getCubieAt(x, y, z) {
        return this.cubies.find(c =>
            Math.round(c.position.x) === x &&
            Math.round(c.position.y) === y &&
            Math.round(c.position.z) === z
        );
    }

    /**
     * Visual 3D Directional Indicator Arrow
     */
    showTurnArrow(moveStr) {
        // Clear previous arrows
        while (this.arrowGroup.children.length > 0) {
            this.arrowGroup.remove(this.arrowGroup.children[0]);
        }

        if (!moveStr) return;

        const face = moveStr[0];
        const isCounter = moveStr.endsWith("'");
        const isDouble = moveStr.endsWith("2");

        const arrowObj = this.createCurvedArrow(face, isCounter, isDouble);
        if (arrowObj) {
            this.arrowGroup.add(arrowObj);
        }
    }

    clearTurnArrow() {
        while (this.arrowGroup.children.length > 0) {
            this.arrowGroup.remove(this.arrowGroup.children[0]);
        }
    }

    createCurvedArrow(face, isCounter, isDouble) {
        const group = new THREE.Group();
        const radius = 1.0;
        const curveSegments = 32;
        const startAngle = 0;
        const endAngle = isDouble ? Math.PI * 1.5 : (Math.PI * 0.9);

        const points = [];
        for (let i = 0; i <= curveSegments; i++) {
            const angle = (i / curveSegments) * (endAngle - startAngle) + startAngle;
            const x = radius * Math.cos(angle);
            const z = radius * Math.sin(angle);
            points.push(new THREE.Vector3(x, 0, z));
        }

        const curve = new THREE.CatmullRomCurve3(points);
        const tubeGeom = new THREE.TubeGeometry(curve, 32, 0.09, 8, false);
        // Electric Neon Fuchsia (not White, Yellow, Green, Blue, Red, or Orange)
        const material = new THREE.MeshStandardMaterial({
            color: 0xff007f,
            emissive: 0xff0055,
            emissiveIntensity: 1.2,
            roughness: 0.15,
            metalness: 0.1
        });
        const tubeMesh = new THREE.Mesh(tubeGeom, material);
        group.add(tubeMesh);

        // Arrow head cone
        const coneGeom = new THREE.ConeGeometry(0.22, 0.4, 16);
        const coneMesh = new THREE.Mesh(coneGeom, material);
        const lastPt = points[points.length - 1];
        const prevPt = points[points.length - 2];
        const dir = new THREE.Vector3().subVectors(lastPt, prevPt).normalize();

        coneMesh.position.copy(lastPt);
        coneMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
        group.add(coneMesh);

        // Position and orient arrow group according to face
        const offset = 1.62;
        switch (face) {
            case 'U':
                group.position.set(0, offset, 0);
                group.rotation.x = 0;
                if (!isCounter) group.scale.set(1, 1, -1);
                break;
            case 'D':
                group.position.set(0, -offset, 0);
                group.rotation.x = Math.PI;
                if (isCounter) group.scale.set(1, 1, -1);
                break;
            case 'R':
                group.position.set(offset, 0, 0);
                group.rotation.z = -Math.PI / 2;
                if (!isCounter) group.scale.set(1, 1, -1);
                break;
            case 'L':
                group.position.set(-offset, 0, 0);
                group.rotation.z = Math.PI / 2;
                if (isCounter) group.scale.set(1, 1, -1);
                break;
            case 'F':
                group.position.set(0, 0, offset);
                group.rotation.x = Math.PI / 2;
                if (!isCounter) group.scale.set(1, 1, -1);
                break;
            case 'B':
                // Position directly above the top-back edge where the camera can clearly see it!
                group.position.set(0, offset + 0.25, -0.95);
                group.rotation.x = Math.PI / 2;
                // Clockwise (looking from front) points LEFT (-X); Counter points RIGHT (+X)
                if (!isCounter) group.scale.set(-1, 1, 1);
                break;
        }

        return group;
    }

    stopAnimation() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.isAnimating = false;
        this.resetCubiesCanonical();
    }

    resetCubiesCanonical() {
        if (!this.scene || !this.pivotGroup) return;

        this.pivotGroup.rotation.set(0, 0, 0);
        this.pivotGroup.position.set(0, 0, 0);

        for (const cubie of this.cubies) {
            if (cubie.parent !== this.scene) {
                this.scene.attach(cubie);
            }
            cubie.position.set(cubie.userData.origX, cubie.userData.origY, cubie.userData.origZ);
            cubie.rotation.set(0, 0, 0);
            cubie.quaternion.identity();
            cubie.scale.set(1, 1, 1);
        }
    }

    /**
     * Executes an animated turn for a move string (e.g. "R", "U'", "F2")
     * Seamlessly resets to canonical orientation upon completion and applies targetCubeState colors.
     */
    animateMove(moveStr, targetCubeState = null, onComplete = null) {
        if (typeof targetCubeState === 'function') {
            onComplete = targetCubeState;
            targetCubeState = null;
        }

        // Halt any existing animation cleanly before starting a new one
        if (this.isAnimating) {
            this.stopAnimation();
        }

        if (!moveStr) {
            if (targetCubeState) this.updateFromCubeState(targetCubeState);
            if (onComplete) onComplete();
            return;
        }

        this.isAnimating = true;

        // Always ensure clean canonical state before starting any new turn
        this.resetCubiesCanonical();

        const face = moveStr[0];
        let angle = -Math.PI / 2;
        if (moveStr.endsWith("'")) angle = Math.PI / 2;
        else if (moveStr.endsWith("2")) angle = -Math.PI;

        let axis = new THREE.Vector3();
        let condition = () => false;

        switch (face) {
            case 'U': axis.set(0, 1, 0); condition = (c) => Math.round(c.position.y) === 1; break;
            case 'D': axis.set(0, 1, 0); angle = -angle; condition = (c) => Math.round(c.position.y) === -1; break;
            case 'R': axis.set(1, 0, 0); condition = (c) => Math.round(c.position.x) === 1; break;
            case 'L': axis.set(1, 0, 0); angle = -angle; condition = (c) => Math.round(c.position.x) === -1; break;
            case 'F': axis.set(0, 0, 1); condition = (c) => Math.round(c.position.z) === 1; break;
            case 'B': axis.set(0, 0, 1); angle = -angle; condition = (c) => Math.round(c.position.z) === -1; break;
        }

        // Attach slice cubies to pivotGroup
        this.pivotGroup.rotation.set(0, 0, 0);
        this.pivotGroup.position.set(0, 0, 0);

        const sliceCubies = this.cubies.filter(condition);
        for (const cubie of sliceCubies) {
            this.pivotGroup.attach(cubie);
        }

        const duration = this.options.turnSpeedMs;
        const startTime = performance.now();

        const step = (currentTime) => {
            if (!this.isAnimating) return; // Cleanly cancelled

            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1.0);
            // Ease out cubic
            const ease = 1 - Math.pow(1 - progress, 3);
            const currentAngle = angle * ease;

            this.pivotGroup.setRotationFromAxisAngle(axis, currentAngle);

            if (progress < 1.0) {
                this.animationFrameId = requestAnimationFrame(step);
            } else {
                this.isAnimating = false;
                this.animationFrameId = null;
                // Animation is complete: reset cubies back to clean canonical state and apply target state colors
                this.resetCubiesCanonical();
                if (targetCubeState) {
                    this.updateFromCubeState(targetCubeState);
                }
                if (onComplete) onComplete();
            }
        };

        this.animationFrameId = requestAnimationFrame(step);
    }

    dispose() {
        this.disposed = true;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        if (this.controls && typeof this.controls.dispose === 'function') {
            this.controls.dispose();
            this.controls = null;
        }
        if (this.renderer && this.renderer.domElement && this.renderer.domElement.parentNode) {
            this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            this.renderer.dispose();
        }
    }

    animate() {
        if (this.disposed) return;
        requestAnimationFrame(this.animate);
        if (this.controls) this.controls.update();

        // Continuous aspect ratio verification: prevents rectangular distortion
        const parent = (this.renderer && this.renderer.domElement && this.renderer.domElement.parentElement) || this.container;
        if (parent && this.camera && this.renderer) {
            const pw = parent.clientWidth;
            const ph = parent.clientHeight;
            if (pw > 0 && ph > 0) {
                const currentAspect = pw / ph;
                if (Math.abs(this.camera.aspect - currentAspect) > 0.005) {
                    this.onResize();
                }
            }
        }

        // Continuous per-frame render callback (for 100% real-time camera sync)
        if (typeof this.options.onRenderFrame === 'function') {
            this.options.onRenderFrame(this.camera, this.controls);
        }

        // Subtle pulse for 3D turn arrows
        if (this.arrowGroup && this.arrowGroup.children.length > 0) {
            const time = performance.now() * 0.004;
            const s = 1.0 + 0.06 * Math.sin(time);
            this.arrowGroup.children[0].scale.set(s, s, s);
        }

        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }
}
