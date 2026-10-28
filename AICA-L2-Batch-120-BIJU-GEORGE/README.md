# CubeSolver 3D - Progressive Web App (PWA)

A world-class, deterministic 3x3 Rubik's Cube Solver built as an installable **Progressive Web App (PWA)** with 3D WebGL animations, 6-face Camera Scanner, interactive 2D Net Editor, and dual-algorithm solving engines.

---

## 🌟 Key Features

### 1. 100% Deterministic Solving for All Six Sides
Guarantees a complete solve of **all 6 faces (White, Yellow, Green, Blue, Red, Orange)** for every available option:
- **Herbert Kociemba's Two-Phase Algorithm**: Optimal/sub-optimal solving in **18–22 moves** within milliseconds.
- **Beginner Layer-by-Layer (LBL) Tutorial Method**: Decomposes the solve into 7 educational stages with plain-English instructions and visual cues.
- **Iconic Presets & Patterns**: Instant 0ms solutions for *Checkerboard*, *Superflip* (God's Number 20), *Cube in a Cube*, *Anaconda*, *Python*, *Cross Pattern*, and more.
- **WCA Scramble Generator**: Generates official scrambles (10–25 moves) and solves all 6 sides with one click.

### 2. Five Intuitive Input & Solving Modes
1. **🎲 3D Solver & Free Play**:
   - Touch/mouse drag orbital controls (`OrbitControls`) with realistic plastic bevels, face center initials, and directional glowing 3D arrows.
   - Quick face twists (`U`, `U'`, `D`, `D'`, `R`, `R'`, `L`, `L'`, `F`, `F'`, `B`, `B'`).
2. **📷 Camera Scanner (6-Face Protocol)**:
   - Guided sequential capture of all 6 faces (`U`, `R`, `F`, `D`, `L`, `B`) with an interactive 3x3 alignment grid.
   - HSV color classification with real-time tap-to-correct for lighting adjustments.
   - Sample scramble photos and file upload support for instant desktop testing.
3. **🎨 Manual 2D Net Editor**:
   - Interactive unfolded cube net with real-time sticker count badges (`9/9` per color).
   - Real-time parity and corner/edge twist validation.
4. **📖 Interactive Move Notation Guide**:
   - Visual reference and live 3D test buttons for every official WCA move and slice turn.
5. **⏱ Speedcube Timer & History**:
   - WCA 15-second inspection countdown, spacebar/touch hold-to-prime release-to-start.
   - Real-time Personal Best (PB), Average of 5 (Ao5), and historical solve logs.
   - One-click *"Solve in 3D"* to immediately launch the solver for any timed scramble.

### 3. Progressive Web App (PWA) Capabilities
- **Installable**: One-click install prompt on Chrome, Edge, Safari (iOS/macOS), and Android.
- **100% Offline Ready**: Service worker (`sw.js`) caches all Three.js, OrbitControls, Kociemba tables, styles, and assets.
- **Zero Server Dependency**: 100% client-side computation in the browser.
- **Realistic Audio & Haptic Feedback**: Procedural Web Audio API slice turn clicks and victory chimes without external MP3 files.

---

## 🚀 Running the App

### Option A: Using Python (Instant)
```bash
python -m http.server 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser.

### Option B: Using Node / npm
```bash
npm start
```
Or with `npx serve`:
```bash
npx serve -l 8080 .
```

---

## 📁 File Structure
```
├── index.html              # Main PWA application entry point
├── manifest.webmanifest    # PWA install manifest with shortcuts & icons
├── sw.js                   # Service Worker for offline asset caching
├── package.json            # Node/npm scripts and type configuration
├── css/
│   └── styles.css          # Cyber-dark modern responsive styles with glassmorphism
├── js/
│   ├── app.js              # Main application coordinator
│   ├── lib/
│   │   ├── three.min.js    # Local Three.js 3D WebGL library
│   │   ├── OrbitControls.js# Local OrbitControls
│   │   ├── cube.js         # Cube model & permutation tables
│   │   └── solve.js        # Herbert Kociemba Two-Phase solving engine
│   ├── model/
│   │   └── CubeState.js    # 54-facelet state representation & rotations
│   ├── solver/
│   │   ├── KociembaSolver.js      # Optimal Two-Phase algorithm wrapper
│   │   └── LayerByLayerSolver.js  # 7-Stage beginner method solver
│   └── ui/
│       ├── Cube3D.js              # Three.js 3D renderer & animated slice turns
│       ├── CameraScanner.js       # 6-face guided camera scanner & color extractor
│       ├── ManualEditor.js        # 2D unfolded net editor with live validation
│       ├── SolutionVisualizer.js  # Step-by-step playback & timeline chips
│       ├── NotationGuide.js       # Interactive WCA move playground
│       ├── Timer.js               # Speedcubing stopwatch & stats
│       └── AudioEffects.js        # Procedural mechanical click & chime audio
└── assets/
    ├── icon-192.png        # PWA Icon 192x192
    └── icon-512.png        # PWA Icon 512x512
```
