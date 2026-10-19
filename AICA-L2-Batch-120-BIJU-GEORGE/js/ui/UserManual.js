/**
 * UserManual.js - Illustrated Printable Instruction & Operation Manual
 * Provides comprehensive documentation, visual SVG diagrams, step-by-step
 * walkthroughs, and clean print/PDF export styling for CubeSolver 3D.
 */

export class UserManual {
    constructor(containerElement) {
        this.container = containerElement;
        this.init();
    }

    init() {
        this.render();
    }

    render() {
        this.container.innerHTML = `
            <div class="user-manual-wrap">
                <!-- Manual Header Banner (Hidden during print in favor of print header) -->
                <header class="manual-hero no-print">
                    <div class="manual-hero-left">
                        <div class="manual-badge-row">
                            <span class="manual-badge-pill">📘 Official Documentation</span>
                            <span class="manual-badge-version">v2.4 • Web & PWA</span>
                        </div>
                        <h1 class="manual-hero-title">CubeSolver 3D — Complete User Manual</h1>
                        <p class="manual-hero-desc">The illustrated guide to scanning physical cubes with your webcam, interactive 3D step-by-step solving, the kid-friendly Academy masterclass, and speedcubing timer.</p>
                    </div>
                    <div class="manual-hero-actions">
                        <button id="btn-manual-print" class="manual-action-btn primary" title="Print this manual or save as PDF">
                            <span>🖨️</span> Print / Save as PDF
                        </button>
                    </div>
                </header>

                <!-- Print-Only Document Header -->
                <div class="manual-print-header">
                    <div class="print-header-top">
                        <span class="print-logo">🧊 CubeSolver 3D — Illustrated User Manual</span>
                        <span class="print-meta">Official Documentation • Herbert Kociemba 2-Phase & CFOP Engine</span>
                    </div>
                    <p class="print-header-sub">Complete instructions for scanning, solving, practicing, and timing Rubik's cube solves.</p>
                </div>

                <!-- Quick Navigation Jump Bar (Screen only) -->
                <nav class="manual-quick-nav no-print" aria-label="Manual Sections">
                    <button class="manual-nav-pill" data-target="quickstart">⚡ Quick Start</button>
                    <button class="manual-nav-pill" data-target="workflow">🔄 Workflow</button>
                    <button class="manual-nav-pill" data-target="scanner">📷 Camera Scanner</button>
                    <button class="manual-nav-pill" data-target="editor">🎨 Net Editor</button>
                    <button class="manual-nav-pill" data-target="solver">🎲 3D Solver</button>
                    <button class="manual-nav-pill" data-target="academy">🎓 Cube Academy</button>
                    <button class="manual-nav-pill" data-target="timer">⏱ Speed Timer</button>
                    <button class="manual-nav-pill" data-target="notation">📖 Notation</button>
                    <button class="manual-nav-pill" data-target="shortcuts">⌨️ Shortcuts</button>
                    <button class="manual-nav-pill" data-target="faq">❓ FAQ</button>
                </nav>

                <div class="manual-content-body">
                    <!-- SECTION 1: QUICK START -->
                    <section id="manual-sec-quickstart" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">01</span>
                            <div class="sec-title-wrap">
                                <h2>Quick Start: Solve Any Cube in 3 Steps</h2>
                                <p class="sec-subtitle">Get your real scrambled cube solved in under 2 minutes!</p>
                            </div>
                        </div>

                        <!-- Golden Rule Warning Card -->
                        <div class="manual-alert warning-golden-rule">
                            <div class="golden-rule-header">
                                <span class="golden-rule-icon">⚠️</span>
                                <div class="golden-rule-title-group">
                                    <h3 class="golden-rule-title">CRITICAL GOLDEN RULE: Check Your Center Piece Colors First!</h3>
                                    <span class="golden-rule-badge">#1 Most Common Beginner Mistake</span>
                                </div>
                            </div>
                            <div class="golden-rule-body">
                                <p class="golden-rule-intro">
                                    On every standard 3x3 Rubik's cube, the <strong>6 center pieces are permanently fixed</strong> to the internal core spindle — <em>they NEVER move relative to one another!</em> The color of each center piece defines which face that is. Before scanning, painting, or solving, hold your cube and verify this standard WCA orientation:
                                </p>
                                <div class="golden-rule-checklist">
                                    <div class="checklist-item">
                                        <span class="check-pill green">FRONT = GREEN</span>
                                        <span>Face facing <strong>YOU</strong> must have a <strong>Green center</strong>.</span>
                                    </div>
                                    <div class="checklist-item">
                                        <span class="check-pill red">RIGHT = RED</span>
                                        <span>Face in your <strong>RIGHT HAND</strong> must have a <strong>RED center</strong>.</span>
                                    </div>
                                    <div class="checklist-item">
                                        <span class="check-pill white">TOP = WHITE</span>
                                        <span>Face facing the <strong>CEILING</strong> must have a <strong>White center</strong>.</span>
                                    </div>
                                    <div class="checklist-item">
                                        <span class="check-pill orange">LEFT = ORANGE</span>
                                        <span>Face in your <strong>LEFT HAND</strong> must have an <strong>Orange center</strong>.</span>
                                    </div>
                                    <div class="checklist-item">
                                        <span class="check-pill yellow">BOTTOM = YELLOW</span>
                                        <span>Face facing the <strong>FLOOR</strong> must have a <strong>Yellow center</strong>.</span>
                                    </div>
                                    <div class="checklist-item">
                                        <span class="check-pill blue">BACK = BLUE</span>
                                        <span>Face facing <strong>AWAY</strong> from you must have a <strong>Blue center</strong>.</span>
                                    </div>
                                </div>
                                <div class="golden-rule-warning-note">
                                    <strong>🚨 The Common Mistake:</strong> If your Right face has an Orange or Blue center while Green is in Front, your cube is oriented backwards or inverted! Entering stickers with incorrect centers makes the cube physically impossible to solve (or makes the 3D solver turns twist the wrong faces on your physical cube). Always align your centers first!
                                </div>
                            </div>
                        </div>

                        <div class="manual-grid-2col">
                            <div class="manual-card">
                                <h3 class="card-title">🚀 3-Step Express Walkthrough</h3>
                                <ol class="manual-steps-list">
                                    <li>
                                        <div class="step-badge">1</div>
                                        <div class="step-text">
                                            <strong>Input Your Cube:</strong> Click <strong>📷 Scanner</strong> to scan all 6 faces using your webcam, or click <strong>🎨 Net Editor</strong> to paint the colors on an unfolded 2D cube net.
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">2</div>
                                        <div class="step-text">
                                            <strong>Choose Solver Mode:</strong> Select <strong>Herbert Kociemba Optimal</strong> (super-fast, ~20 moves) or <strong>Beginner CFOP</strong> (learn each layer stage by stage).
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">3</div>
                                        <div class="step-text">
                                            <strong>Follow the 3D Guide:</strong> Press <strong>▶ Play</strong> or click <strong>Step Move ⏭</strong> to watch the 3D cube turn slice by slice with glowing directional arrows!
                                        </div>
                                    </li>
                                </ol>
                            </div>

                            <div class="manual-card illustration-card">
                                <h3 class="card-title">🧠 Cube Anatomy & Face Conventions</h3>
                                <div class="svg-container">
                                    <svg viewBox="0 0 400 225" class="manual-svg" xmlns="http://www.w3.org/2000/svg">
                                        <!-- Isometric 3D Cube Diagram -->
                                        <defs>
                                            <filter id="shadow3d" x="-10%" y="-10%" width="120%" height="120%">
                                                <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.5"/>
                                            </filter>
                                        </defs>

                                        <!-- Top Face (U - White) -->
                                        <polygon points="200,56 268,93 200,130 132,93" fill="#f8fafc" stroke="#334155" stroke-width="2" filter="url(#shadow3d)"/>
                                        <line x1="155" y1="81" x2="223" y2="118" stroke="#94a3b8" stroke-width="1.5"/>
                                        <line x1="177" y1="68" x2="245" y2="105" stroke="#94a3b8" stroke-width="1.5"/>
                                        <line x1="177" y1="118" x2="245" y2="81" stroke="#94a3b8" stroke-width="1.5"/>
                                        <line x1="155" y1="105" x2="223" y2="68" stroke="#94a3b8" stroke-width="1.5"/>
                                        <text x="200" y="97" text-anchor="middle" font-size="13" font-weight="800" fill="#0f172a">U (White)</text>

                                        <!-- Front Face (F - Green) -->
                                        <polygon points="132,93 200,130 200,212 132,175" fill="#16a34a" stroke="#14532d" stroke-width="2"/>
                                        <line x1="155" y1="105" x2="155" y2="187" stroke="#15803d" stroke-width="1.5"/>
                                        <line x1="177" y1="118" x2="177" y2="200" stroke="#15803d" stroke-width="1.5"/>
                                        <line x1="132" y1="120" x2="200" y2="157" stroke="#15803d" stroke-width="1.5"/>
                                        <line x1="132" y1="148" x2="200" y2="185" stroke="#15803d" stroke-width="1.5"/>
                                        <text x="166" y="157" text-anchor="middle" font-size="13" font-weight="800" fill="#ffffff">F (Green)</text>

                                        <!-- Right Face (R - Red) -->
                                        <polygon points="200,130 268,93 268,175 200,212" fill="#dc2626" stroke="#991b1b" stroke-width="2"/>
                                        <line x1="223" y1="118" x2="223" y2="200" stroke="#b91c1c" stroke-width="1.5"/>
                                        <line x1="245" y1="105" x2="245" y2="187" stroke="#b91c1c" stroke-width="1.5"/>
                                        <line x1="200" y1="157" x2="268" y2="120" stroke="#b91c1c" stroke-width="1.5"/>
                                        <line x1="200" y1="185" x2="268" y2="148" stroke="#b91c1c" stroke-width="1.5"/>
                                        <text x="234" y="157" text-anchor="middle" font-size="13" font-weight="800" fill="#ffffff">R (Red)</text>

                                        <!-- Top Annotation: White ↔ Yellow (Positioned above White face, zero overlap) -->
                                        <rect x="120" y="4" width="160" height="40" rx="8" fill="#0f172a" fill-opacity="0.9" stroke="#38bdf8" stroke-width="1.5"/>
                                        <text x="200" y="20" text-anchor="middle" font-size="10" font-weight="800" fill="#38bdf8">TOP ↔ BOTTOM</text>
                                        <text x="200" y="35" text-anchor="middle" font-size="11" font-weight="700" fill="#f8fafc">White (U) ↔ Yellow (D)</text>
                                        <line x1="200" y1="44" x2="200" y2="52" stroke="#38bdf8" stroke-width="2" stroke-linecap="round"/>
                                        <polygon points="197,50 203,50 200,54" fill="#38bdf8"/>

                                        <!-- Left Annotation: Green ↔ Blue (Positioned to the left of Green face, zero overlap) -->
                                        <rect x="6" y="110" width="114" height="48" rx="8" fill="#0f172a" fill-opacity="0.9" stroke="#22c55e" stroke-width="1.5"/>
                                        <text x="63" y="128" text-anchor="middle" font-size="10" font-weight="800" fill="#4ade80">FRONT ↔ BACK</text>
                                        <text x="63" y="145" text-anchor="middle" font-size="11" font-weight="700" fill="#f8fafc">Green (F) ↔ Blue (B)</text>
                                        <line x1="120" y1="134" x2="128" y2="134" stroke="#22c55e" stroke-width="2" stroke-linecap="round"/>
                                        <polygon points="126,131 126,137 130,134" fill="#22c55e"/>

                                        <!-- Right Annotation: Red ↔ Orange (Positioned to the right of Red face, zero overlap) -->
                                        <rect x="280" y="110" width="114" height="48" rx="8" fill="#0f172a" fill-opacity="0.9" stroke="#ef4444" stroke-width="1.5"/>
                                        <text x="337" y="128" text-anchor="middle" font-size="10" font-weight="800" fill="#f87171">RIGHT ↔ LEFT</text>
                                        <text x="337" y="145" text-anchor="middle" font-size="11" font-weight="700" fill="#f8fafc">Red (R) ↔ Orange (L)</text>
                                        <line x1="280" y1="134" x2="272" y2="134" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
                                        <polygon points="274,131 274,137 270,134" fill="#ef4444"/>
                                    </svg>
                                </div>
                                <p class="caption-text">Standard WCA Spatial Orientation: Yellow is opposite White, Blue opposite Green, and Orange opposite Red. Center pieces NEVER move! Always hold Green in Front and RED on the Right when White is on Top.</p>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 2: END-TO-END WORKFLOW -->
                    <section id="manual-sec-workflow" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">02</span>
                            <div class="sec-title-wrap">
                                <h2>Application Architecture & Workflow</h2>
                                <p class="sec-subtitle">How CubeSolver 3D captures, models, solves, and guides you to a solved cube.</p>
                            </div>
                        </div>

                        <div class="manual-card">
                            <div class="svg-container wide">
                                <svg viewBox="0 0 740 130" class="manual-svg" xmlns="http://www.w3.org/2000/svg">
                                    <!-- Flow Chart Nodes -->
                                    <!-- Node 1 -->
                                    <rect x="10" y="25" width="160" height="80" rx="10" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
                                    <text x="90" y="52" text-anchor="middle" font-size="20">📷 / 🎨</text>
                                    <text x="90" y="74" text-anchor="middle" font-size="12" font-weight="800" fill="#ffffff">1. CUBE INPUT</text>
                                    <text x="90" y="90" text-anchor="middle" font-size="10" fill="#94a3b8">Scanner or Net Editor</text>

                                    <!-- Arrow 1 -->
                                    <path d="M 175 65 L 195 65" stroke="#38bdf8" stroke-width="3" fill="none" marker-end="url(#arrowhead)"/>
                                    <polygon points="195,60 205,65 195,70" fill="#38bdf8"/>

                                    <!-- Node 2 -->
                                    <rect x="210" y="25" width="150" height="80" rx="10" fill="#1e293b" stroke="#34d399" stroke-width="2"/>
                                    <text x="285" y="52" text-anchor="middle" font-size="20">🧩</text>
                                    <text x="285" y="74" text-anchor="middle" font-size="12" font-weight="800" fill="#ffffff">2. 54-FACELET MODEL</text>
                                    <text x="285" y="90" text-anchor="middle" font-size="10" fill="#94a3b8">Validation & Integrity Check</text>

                                    <!-- Arrow 2 -->
                                    <path d="M 365 65 L 385 65" stroke="#34d399" stroke-width="3" fill="none"/>
                                    <polygon points="385,60 395,65 385,70" fill="#34d399"/>

                                    <!-- Node 3 -->
                                    <rect x="400" y="25" width="160" height="80" rx="10" fill="#1e293b" stroke="#f59e0b" stroke-width="2"/>
                                    <text x="480" y="52" text-anchor="middle" font-size="20">⚡</text>
                                    <text x="480" y="74" text-anchor="middle" font-size="12" font-weight="800" fill="#ffffff">3. SOLVER ENGINES</text>
                                    <text x="480" y="90" text-anchor="middle" font-size="10" fill="#94a3b8">Kociemba 2-Phase / CFOP</text>

                                    <!-- Arrow 3 -->
                                    <path d="M 565 65 L 585 65" stroke="#f59e0b" stroke-width="3" fill="none"/>
                                    <polygon points="585,60 595,65 585,70" fill="#f59e0b"/>

                                    <!-- Node 4 -->
                                    <rect x="600" y="25" width="130" height="80" rx="10" fill="#1e293b" stroke="#a855f7" stroke-width="2"/>
                                    <text x="665" y="52" text-anchor="middle" font-size="20">🎲</text>
                                    <text x="665" y="74" text-anchor="middle" font-size="12" font-weight="800" fill="#ffffff">4. 3D PLAYER</text>
                                    <text x="665" y="90" text-anchor="middle" font-size="10" fill="#94a3b8">Animated 3D Turns</text>
                                </svg>
                            </div>
                            <div class="card-callout-grid">
                                <div class="callout-box">
                                    <span class="callout-icon">💡</span>
                                    <div>
                                        <strong>Automatic Validation:</strong> Before computing solutions, the mathematical engine verifies that parity, edge orientation, and color distribution (9 stickers of each of 6 colors) are 100% valid.
                                    </div>
                                </div>
                                <div class="callout-box">
                                    <span class="callout-icon">🖨️</span>
                                    <div>
                                        <strong>Offline Solution Sheets:</strong> Need to take the solution away from the screen? Click "🖨️ Printable Sheet" on the solver screen to export a clean, 2-column paper cheat sheet.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 3: CAMERA SCANNER -->
                    <section id="manual-sec-scanner" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">03</span>
                            <div class="sec-title-wrap">
                                <h2>Intelligent Camera Scanner</h2>
                                <p class="sec-subtitle">Capture your real cube using your webcam or phone camera with glint-filtered color recognition.</p>
                            </div>
                        </div>

                        <div class="manual-grid-2col">
                            <div class="manual-card">
                                <h3 class="card-title">📸 How to Scan Your Cube Step-by-Step</h3>
                                <ol class="manual-steps-list">
                                    <li>
                                        <div class="step-badge">0</div>
                                        <div class="step-text">
                                            <strong>Check Center Alignment:</strong> Hold your cube with the <strong>White center on Top (U)</strong> and <strong>Green center in Front (F)</strong>. Glance at your right hand: the <strong>Right center MUST be RED (R)</strong>! Never tilt or rotate the cube randomly.
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">1</div>
                                        <div class="step-text">
                                            <strong>Open Scanner Tab:</strong> Click the <strong>📷 Scanner</strong> tab. Allow camera permissions when prompted by your browser.
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">2</div>
                                        <div class="step-text">
                                            <strong>Align in the 1:1 Square Frame:</strong> Hold your cube so its face fills the centered 3x3 square viewfinder. Look at the letter labels inside each circle (<span class="code-pill">W</span>, <span class="code-pill">R</span>, <span class="code-pill">G</span>, <span class="code-pill">Y</span>, <span class="code-pill">O</span>, <span class="code-pill">B</span>).
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">3</div>
                                        <div class="step-text">
                                            <strong>Capture Face:</strong> Press the <kbd>Spacebar</kbd> or click <strong>Capture Current Face</strong>. The app advances in standard order: <strong>U (White) → R (Red) → F (Green) → D (Yellow) → L (Orange) → B (Blue)</strong>. Check that the center piece of each face matches this sequence!
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">4</div>
                                        <div class="step-text">
                                            <strong>Click-to-Correct (If Needed):</strong> If poor room lighting causes a sticker to misread, simply <em>click any circle in the reticle</em> to cycle through colors until it matches your physical cube!
                                        </div>
                                    </li>
                                </ol>

                                <div class="manual-alert warning-compact">
                                    <span class="alert-icon">⚠️</span>
                                    <div>
                                        <strong>Center Color Verification:</strong> When scanning Face 1 (U), the center sticker must be White. When scanning Face 2 (R), the center must be Red. When scanning Face 3 (F), the center must be Green. If the center in the camera doesn't match the face target, rotate your cube to the correct face!
                                    </div>
                                </div>

                                <div class="manual-alert tips">
                                    <span class="alert-icon">💡</span>
                                    <div>
                                        <strong>Capture & Lighting Modes:</strong>
                                        <ul class="bullet-list-tight">
                                            <li><strong>Manual Capture (Default):</strong> Press <kbd>Spacebar</kbd> or click <strong>Capture Current Face</strong> when you are ready. Gives 100% control with zero accidental snaps!</li>
                                            <li><strong>Auto-Capture (Optional):</strong> Click <strong>⚡ Auto: OFF</strong> to toggle <strong>Auto: ON</strong> for hands-free scanning once you hold the cube steady.</li>
                                            <li><strong>Lighting Modes:</strong> Use the 💡 selector for <em>Standard</em>, <em>Dim Room</em> (boosts saturation), or <em>Anti-Glare</em> (filters sticker reflections).</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            <div class="manual-card illustration-card">
                                <h3 class="card-title">🎯 1:1 Viewfinder & Reticle Overlay</h3>
                                <div class="svg-container">
                                    <svg viewBox="0 0 280 260" class="manual-svg" xmlns="http://www.w3.org/2000/svg">
                                        <!-- Outer Viewfinder Box -->
                                        <rect x="20" y="10" width="240" height="240" rx="14" fill="#070a12" stroke="#38bdf8" stroke-width="2.5"/>
                                        
                                        <!-- Corner brackets -->
                                        <path d="M 30 50 L 30 30 L 50 30" stroke="#38bdf8" stroke-width="3" fill="none"/>
                                        <path d="M 230 30 L 250 30 L 250 50" stroke="#38bdf8" stroke-width="3" fill="none"/>
                                        <path d="M 30 210 L 30 230 L 50 230" stroke="#38bdf8" stroke-width="3" fill="none"/>
                                        <path d="M 230 230 L 250 230 L 250 210" stroke="#38bdf8" stroke-width="3" fill="none"/>

                                        <!-- Reticle Grid 3x3 -->
                                        <!-- Row 1 -->
                                        <circle cx="70" cy="60" r="18" fill="#16a34a" stroke="#ffffff" stroke-width="2"/>
                                        <text x="70" y="65" text-anchor="middle" font-weight="900" font-size="14" fill="#ffffff">G</text>

                                        <circle cx="140" cy="60" r="18" fill="#ffffff" stroke="#334155" stroke-width="2"/>
                                        <text x="140" y="65" text-anchor="middle" font-weight="900" font-size="14" fill="#0f172a">W</text>

                                        <circle cx="210" cy="60" r="18" fill="#dc2626" stroke="#ffffff" stroke-width="2"/>
                                        <text x="210" y="65" text-anchor="middle" font-weight="900" font-size="14" fill="#ffffff">R</text>

                                        <!-- Row 2 -->
                                        <circle cx="70" cy="130" r="18" fill="#facc15" stroke="#ffffff" stroke-width="2"/>
                                        <text x="70" y="135" text-anchor="middle" font-weight="900" font-size="14" fill="#0f172a">Y</text>

                                        <circle cx="140" cy="130" r="22" fill="#16a34a" stroke="#38bdf8" stroke-width="3.5"/>
                                        <text x="140" y="136" text-anchor="middle" font-weight="900" font-size="16" fill="#ffffff">G</text>
                                        <text x="140" y="102" text-anchor="middle" font-weight="700" font-size="9" fill="#38bdf8">CENTER</text>

                                        <circle cx="210" cy="130" r="18" fill="#2563eb" stroke="#ffffff" stroke-width="2"/>
                                        <text x="210" y="135" text-anchor="middle" font-weight="900" font-size="14" fill="#ffffff">B</text>

                                        <!-- Row 3 -->
                                        <circle cx="70" cy="200" r="18" fill="#ea580c" stroke="#ffffff" stroke-width="2"/>
                                        <text x="70" y="205" text-anchor="middle" font-weight="900" font-size="14" fill="#ffffff">O</text>

                                        <circle cx="140" cy="200" r="18" fill="#ffffff" stroke="#334155" stroke-width="2"/>
                                        <text x="140" y="205" text-anchor="middle" font-weight="900" font-size="14" fill="#0f172a">W</text>

                                        <circle cx="210" cy="200" r="18" fill="#16a34a" stroke="#ffffff" stroke-width="2"/>
                                        <text x="210" y="205" text-anchor="middle" font-weight="900" font-size="14" fill="#ffffff">G</text>
                                    </svg>
                                </div>
                                <p class="caption-text">Live glint-filtered reticle: Center cell indicates the face target. Any cell can be clicked directly to correct its color.</p>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 4: 2D NET EDITOR -->
                    <section id="manual-sec-editor" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">04</span>
                            <div class="sec-title-wrap">
                                <h2>2D Net Editor (Manual Color Palette)</h2>
                                <p class="sec-subtitle">Manually paint your cube's facelets using an unfolded cross layout or one-click preset patterns.</p>
                            </div>
                        </div>

                        <div class="manual-grid-2col">
                            <div class="manual-card">
                                <h3 class="card-title">🎨 Painting & Validating Your Cube</h3>
                                <ul class="manual-steps-list-styled">
                                    <li>
                                        <strong>0. Match Physical Centers:</strong> The 6 center squares in the 2D net are permanently locked (<strong>U=White, L=Orange, F=Green, R=Red, B=Blue, D=Yellow</strong>). Hold your physical cube with Green in front and Red on the right so each physical face corresponds to its card on screen!
                                    </li>
                                    <li>
                                        <strong>1. Pick a Color:</strong> Click any of the 6 color buttons in the palette bar (White, Red, Green, Yellow, Orange, Blue). The selected color highlights with an active glow.
                                    </li>
                                    <li>
                                        <strong>2. Paint Stickers:</strong> Click (or click-and-drag) across the sticker tiles in the 2D unfolded cube net.
                                    </li>
                                    <li>
                                        <strong>3. Watch the Validator:</strong> Look at the <strong>Color Counts</strong> badge bar. Each of the 6 colors must show exactly <span class="code-pill">9/9</span>.
                                    </li>
                                    <li>
                                        <strong>4. Solve:</strong> Once all 6 counters turn green (<span class="code-pill">9/9</span>), the <strong>⚡ Solve Cube</strong> button enables automatically!
                                    </li>
                                </ul>

                                <div class="manual-alert note">
                                    <span class="alert-icon">ℹ️</span>
                                    <div>
                                        <strong>Try Fun Presets:</strong> Want to see eye-catching patterns? Use the <strong>Patterns Dropdown</strong> on the 3D solver tab to test <em>Checkerboard</em>, <em>Superflip</em>, <em>Cube in a Cube</em>, <em>Anaconda</em>, or <em>Four Spots</em> with a single click!
                                    </div>
                                </div>
                            </div>

                            <div class="manual-card illustration-card">
                                <h3 class="card-title">🗺️ Unfolded Cube Net Geometry</h3>
                                <div class="svg-container">
                                    <svg viewBox="0 0 340 250" class="manual-svg" xmlns="http://www.w3.org/2000/svg">
                                        <!-- Top Face: U -->
                                        <g transform="translate(85, 10)">
                                            <rect width="60" height="60" fill="#f8fafc" stroke="#334155" stroke-width="2" rx="4"/>
                                            <line x1="20" y1="0" x2="20" y2="60" stroke="#94a3b8"/>
                                            <line x1="40" y1="0" x2="40" y2="60" stroke="#94a3b8"/>
                                            <line x1="0" y1="20" x2="60" y2="20" stroke="#94a3b8"/>
                                            <line x1="0" y1="40" x2="60" y2="40" stroke="#94a3b8"/>
                                            <text x="30" y="36" text-anchor="middle" font-size="12" font-weight="900" fill="#0f172a">U</text>
                                        </g>

                                        <!-- Middle Row: L, F, R, B -->
                                        <!-- L (Orange) -->
                                        <g transform="translate(15, 75)">
                                            <rect width="60" height="60" fill="#ea580c" stroke="#7c2d12" stroke-width="2" rx="4"/>
                                            <line x1="20" y1="0" x2="20" y2="60" stroke="#c2410c"/>
                                            <line x1="40" y1="0" x2="40" y2="60" stroke="#c2410c"/>
                                            <line x1="0" y1="20" x2="60" y2="20" stroke="#c2410c"/>
                                            <line x1="0" y1="40" x2="60" y2="40" stroke="#c2410c"/>
                                            <text x="30" y="36" text-anchor="middle" font-size="12" font-weight="900" fill="#ffffff">L</text>
                                        </g>

                                        <!-- F (Green) -->
                                        <g transform="translate(85, 75)">
                                            <rect width="60" height="60" fill="#16a34a" stroke="#14532d" stroke-width="2" rx="4"/>
                                            <line x1="20" y1="0" x2="20" y2="60" stroke="#15803d"/>
                                            <line x1="40" y1="0" x2="40" y2="60" stroke="#15803d"/>
                                            <line x1="0" y1="20" x2="60" y2="20" stroke="#15803d"/>
                                            <line x1="0" y1="40" x2="60" y2="40" stroke="#15803d"/>
                                            <text x="30" y="36" text-anchor="middle" font-size="12" font-weight="900" fill="#ffffff">F</text>
                                        </g>

                                        <!-- R (Red) -->
                                        <g transform="translate(155, 75)">
                                            <rect width="60" height="60" fill="#dc2626" stroke="#991b1b" stroke-width="2" rx="4"/>
                                            <line x1="20" y1="0" x2="20" y2="60" stroke="#b91c1c"/>
                                            <line x1="40" y1="0" x2="40" y2="60" stroke="#b91c1c"/>
                                            <line x1="0" y1="20" x2="60" y2="20" stroke="#b91c1c"/>
                                            <line x1="0" y1="40" x2="60" y2="40" stroke="#b91c1c"/>
                                            <text x="30" y="36" text-anchor="middle" font-size="12" font-weight="900" fill="#ffffff">R</text>
                                        </g>

                                        <!-- B (Blue) -->
                                        <g transform="translate(225, 75)">
                                            <rect width="60" height="60" fill="#2563eb" stroke="#1e3a8a" stroke-width="2" rx="4"/>
                                            <line x1="20" y1="0" x2="20" y2="60" stroke="#1d4ed8"/>
                                            <line x1="40" y1="0" x2="40" y2="60" stroke="#1d4ed8"/>
                                            <line x1="0" y1="20" x2="60" y2="20" stroke="#1d4ed8"/>
                                            <line x1="0" y1="40" x2="60" y2="40" stroke="#1d4ed8"/>
                                            <text x="30" y="36" text-anchor="middle" font-size="12" font-weight="900" fill="#ffffff">B</text>
                                        </g>

                                        <!-- Bottom Face: D (Yellow) -->
                                        <g transform="translate(85, 145)">
                                            <rect width="60" height="60" fill="#facc15" stroke="#854d0e" stroke-width="2" rx="4"/>
                                            <line x1="20" y1="0" x2="20" y2="60" stroke="#ca8a04"/>
                                            <line x1="40" y1="0" x2="40" y2="60" stroke="#ca8a04"/>
                                            <line x1="0" y1="20" x2="60" y2="20" stroke="#ca8a04"/>
                                            <line x1="0" y1="40" x2="60" y2="40" stroke="#ca8a04"/>
                                            <text x="30" y="36" text-anchor="middle" font-size="12" font-weight="900" fill="#0f172a">D</text>
                                        </g>

                                        <!-- Validator Bar Mock -->
                                        <rect x="15" y="215" width="310" height="28" rx="6" fill="#1e293b" stroke="#334155"/>
                                        <circle cx="35" cy="229" r="6" fill="#ffffff"/>
                                        <text x="46" y="233" font-size="10" font-weight="700" fill="#10b981">9/9</text>

                                        <circle cx="85" cy="229" r="6" fill="#dc2626"/>
                                        <text x="96" y="233" font-size="10" font-weight="700" fill="#10b981">9/9</text>

                                        <circle cx="135" cy="229" r="6" fill="#16a34a"/>
                                        <text x="146" y="233" font-size="10" font-weight="700" fill="#10b981">9/9</text>

                                        <circle cx="185" cy="229" r="6" fill="#facc15"/>
                                        <text x="196" y="233" font-size="10" font-weight="700" fill="#10b981">9/9</text>

                                        <circle cx="235" cy="229" r="6" fill="#ea580c"/>
                                        <text x="246" y="233" font-size="10" font-weight="700" fill="#10b981">9/9</text>

                                        <circle cx="285" cy="229" r="6" fill="#2563eb"/>
                                        <text x="296" y="233" font-size="10" font-weight="700" fill="#10b981">9/9</text>
                                    </svg>
                                </div>
                                <p class="caption-text">Unfolded net with real-time 9-sticker counters. Center squares cannot be edited, preserving core orientation.</p>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 5: 3D SOLVER & PLAYER -->
                    <section id="manual-sec-solver" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">05</span>
                            <div class="sec-title-wrap">
                                <h2>3D Solver & Interactive Player</h2>
                                <p class="sec-subtitle">Experience turn-by-turn Three.js WebGL animations, camera controls, and speed adjustments.</p>
                            </div>
                        </div>

                        <div class="manual-card">
                            <h3 class="card-title">🎮 3D Stage Player Controls Guide</h3>
                            <div class="player-controls-breakdown-grid">
                                <div class="breakdown-item">
                                    <div class="item-icon-title">
                                        <span class="btn-pill">▶ Play / ⏸ Pause</span>
                                    </div>
                                    <p>Autoplays the solution continuously. Turns smoothly animate with easing and realistic physical twist speeds.</p>
                                </div>

                                <div class="breakdown-item">
                                    <div class="item-icon-title">
                                        <span class="btn-pill">Step Move ⏭</span>
                                    </div>
                                    <p>Advances exactly 1 move forward. Perfect for holding your physical cube in your hands and executing one turn at a time.</p>
                                </div>

                                <div class="breakdown-item">
                                    <div class="item-icon-title">
                                        <span class="btn-pill">⏮ Prev Move</span>
                                    </div>
                                    <p>Undoes the last move if you turned the wrong way on your real cube, allowing you to re-verify.</p>
                                </div>

                                <div class="breakdown-item">
                                    <div class="item-icon-title">
                                        <span class="btn-pill">↺ Reset Cam / Stage</span>
                                    </div>
                                    <p>Snaps the 3D perspective back to the standard isometric view (White on Top, Green in Front, Red on Right).</p>
                                </div>
                            </div>

                            <div class="manual-grid-2col" style="margin-top: 14px;">
                                <div class="manual-card sub-card">
                                    <h4>3D Orbit & Touch Gestures</h4>
                                    <ul class="bullet-list-tight">
                                        <li><strong>Rotate Camera:</strong> Click and drag with mouse, or drag with 1 finger on touchscreens.</li>
                                        <li><strong>Zoom In / Out:</strong> Scroll mouse wheel, or pinch with 2 fingers on touchscreens.</li>
                                        <li><strong>3D Directional Arrows:</strong> A glowing neon arrow appears on the active slice showing the exact twist direction.</li>
                                    </ul>
                                </div>

                                <div class="manual-card sub-card">
                                    <h4>Solver Algorithm Engines</h4>
                                    <ul class="bullet-list-tight">
                                        <li><strong>Herbert Kociemba 2-Phase (Default):</strong> Finds the absolute shortest mathematical path to solved (usually 18–22 moves). Ideal for solving quickly.</li>
                                        <li><strong>Beginner CFOP (Layer-by-Layer):</strong> Solves the cube in human-readable stages: White Cross → First Layer Corners → Middle Belt → Yellow Cross → Sune → Headlights. Great for learning!</li>
                                    </ul>
                                </div>

                                <div class="manual-card sub-card">
                                    <h4>🔄 360° Dual-Angle Opposite View</h4>
                                    <ul class="bullet-list-tight">
                                        <li><strong>Zero Blind Spots:</strong> While the primary 3D stage displays <strong>Up (White)</strong>, <strong>Front (Green)</strong>, and <strong>Right (Red)</strong>, the secondary 3D view simultaneously displays the 3 occluded sides: <strong>Down (Yellow)</strong>, <strong>Back (Blue)</strong>, and <strong>Left (Orange)</strong>.</li>
                                        <li><strong>Antipodal Orbit Tracking (🔗 Synced 360°):</strong> Rotating the main cube automatically tracks the opposite angle in real time ($180^\circ$ reverse perspective). Click <strong>🔓 Free Orbit</strong> to inspect either cube independently.</li>
                                        <li><strong>Simultaneous Turn Animation:</strong> Any move (<span class="code-pill">U</span>, <span class="code-pill">R'</span>, scrambles, solution steps) physically animates on both 3D cubes simultaneously!</li>
                                    </ul>
                                </div>
                            </div>

                            <div class="manual-alert warning-compact" style="margin-top: 12px;">
                                <span class="alert-icon">💡</span>
                                <div>
                                    <strong>Solving Tip — Keep Your Grip Fixed:</strong> When turning your physical cube along with the 3D player, always hold <strong>Green facing YOU</strong>, <strong>RED on your Right</strong>, and <strong>White on Top</strong>. When a move says <span class="code-pill">R</span>, turn your right-hand face (Red). Do not rotate the whole cube in your hand unless an algorithm explicitly instructs a rotation!
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 6: CUBE ACADEMY -->
                    <section id="manual-sec-academy" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">06</span>
                            <div class="sec-title-wrap">
                                <h2>Cube Academy (Kid-Friendly Masterclass)</h2>
                                <p class="sec-subtitle">The world's easiest step-by-step method designed for a 12-year-old to master solving from scratch.</p>
                            </div>
                        </div>

                        <div class="manual-card">
                            <h3 class="card-title">🏆 The 8 Academy Mastery Stages</h3>
                            <table class="manual-table">
                                <thead>
                                    <tr>
                                        <th>Stage</th>
                                        <th>Stage Name</th>
                                        <th>Formula / Mnemonic</th>
                                        <th>Key Learning Objective</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>0</strong></td>
                                        <td><strong>The 2 Magic Moves</strong> 🧠</td>
                                        <td><code>R U R' U'</code> & <code>L' U' L U</code></td>
                                        <td>Righty & Lefty triggers. Up, Away, Down, Back. 6 cycles reset cube!</td>
                                    </tr>
                                    <tr>
                                        <td><strong>1</strong></td>
                                        <td><strong>The Daisy</strong> 🌼</td>
                                        <td><code>F / R / F U' R</code></td>
                                        <td>Collect 4 white petals around Yellow center. Ignore corners!</td>
                                    </tr>
                                    <tr>
                                        <td><strong>2</strong></td>
                                        <td><strong>White Cross & Layer 1</strong> 🏁</td>
                                        <td><code>F2</code> then <code>R U R' U'</code></td>
                                        <td>Flip petals down. Park corners over slots and do Magic Move.</td>
                                    </tr>
                                    <tr>
                                        <td><strong>3</strong></td>
                                        <td><strong>Middle Belt (F2L)</strong> 🎽</td>
                                        <td><code>U (R U R' U') y' (L' U' L U)</code></td>
                                        <td>The Big "T" trick. Push away from destination, do trigger, mirror.</td>
                                    </tr>
                                    <tr>
                                        <td><strong>4</strong></td>
                                        <td><strong>The Yellow Cross</strong> ⏰</td>
                                        <td><code>F (R U R' U') F'</code></td>
                                        <td>Clock method: Dot (12:00) → Hook (9:00) → Horizontal Line (-) → Cross!</td>
                                    </tr>
                                    <tr>
                                        <td><strong>5</strong></td>
                                        <td><strong>Yellow Face (Sune)</strong> 🐟</td>
                                        <td><code>R U R' U R U2 R'</code></td>
                                        <td>The Fish algorithm. Put fish mouth at bottom-left and feed it!</td>
                                    </tr>
                                    <tr>
                                        <td><strong>6</strong></td>
                                        <td><strong>Position Corners</strong> 🚗</td>
                                        <td><code>R' F R' B2 R F' R' B2 R2</code></td>
                                        <td>Look for matching car headlights. Put headlights in the back!</td>
                                    </tr>
                                    <tr>
                                        <td><strong>7</strong></td>
                                        <td><strong>The Grand Finale</strong> 🏆</td>
                                        <td><code>R U R' U'</code> (2x or 4x)</td>
                                        <td>Upside down finish! ONLY turn D layer to bring next corner! 100% solved!</td>
                                    </tr>
                                </tbody>
                            </table>

                            <div class="manual-alert tips" style="margin-top: 14px;">
                                <span class="alert-icon">💡</span>
                                <div>
                                    <strong>How to Use the 3D Practice Lab in Academy:</strong> Each lesson includes a live 3D playground. Click on any algorithm card to load it into the 3D lab. Click <strong>🎯 Practice Case</strong> to set up the exact scenario being taught, then click <strong>▶ Play Algorithm</strong> or <strong>Step Move ⏭</strong> to watch the magic happen!
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 7: SPEEDCUBE TIMER -->
                    <section id="manual-sec-timer" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">07</span>
                            <div class="sec-title-wrap">
                                <h2>Speedcube Timer & Statistics</h2>
                                <p class="sec-subtitle">WCA-standard inspection timer, automatic scramble generator, and statistical records.</p>
                            </div>
                        </div>

                        <div class="manual-grid-2col">
                            <div class="manual-card">
                                <h3 class="card-title">⏱ How to Time Solves Like a Pro</h3>
                                <ol class="manual-steps-list">
                                    <li>
                                        <div class="step-badge">1</div>
                                        <div class="step-text">
                                            <strong>Apply the Scramble:</strong> The top bar displays an official 20-move WCA scramble. Follow the moves on your real cube.
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">2</div>
                                        <div class="step-text">
                                            <strong>Get Ready:</strong> Press and hold the <kbd>Spacebar</kbd> (or touch and hold the timer display on your mobile device). The display turns <strong style="color: #ef4444;">Orange</strong> (Preparing) and then <strong style="color: #10b981;">Green</strong> (Ready!).
                                        </div>
                                    </li>
                                    <li>
                                        <div class="step-badge">3</div>
                                        <div class="step-text">
                                            <strong>Solve & Stop:</strong> Release the Spacebar/touch to start the timer. Pick up your cube and solve! When solved, tap any key or touch the screen to immediately freeze the time.
                                        </div>
                                    </li>
                                </ol>
                            </div>

                            <div class="manual-card">
                                <h3 class="card-title">📊 Real-Time Statistics & Tracking</h3>
                                <ul class="bullet-list-tight">
                                    <li><strong>Personal Best (PB):</strong> Tracks your all-time fastest single solve.</li>
                                    <li><strong>Average of 5 (Ao5):</strong> The international competitive standard: takes your last 5 solves, trims the fastest and slowest, and averages the middle 3.</li>
                                    <li><strong>Average of 12 (Ao12):</strong> A longer-term measure of solving consistency.</li>
                                    <li><strong>Offline Persistence:</strong> All solve times and records are saved locally in your browser storage so they stay safe between sessions.</li>
                                </ul>
                            </div>
                        </div>
                    </section>

                    <!-- SECTION 8: WCA NOTATION REFERENCE -->
                    <section id="manual-sec-notation" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">08</span>
                            <div class="sec-title-wrap">
                                <h2>Official WCA Move Notation Guide</h2>
                                <p class="sec-subtitle">Understand every turn notation letter used in cubing tutorials and algorithms worldwide.</p>
                            </div>
                        </div>

                        <div class="manual-card">
                            <table class="manual-table notation-table">
                                <thead>
                                    <tr>
                                        <th>Notation</th>
                                        <th>Name</th>
                                        <th>Direction</th>
                                        <th>Description</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><span class="algo-chip-key">U</span></td>
                                        <td>Up (Top Face)</td>
                                        <td>Clockwise 90°</td>
                                        <td>Turn top layer to the LEFT (flick with right index finger).</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">U'</span></td>
                                        <td>Up Prime</td>
                                        <td>Anticlockwise 90°</td>
                                        <td>Turn top layer to the RIGHT (flick with left index finger).</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">U2</span></td>
                                        <td>Up Double</td>
                                        <td>180° Half Turn</td>
                                        <td>Double twist top layer 180° (index-middle finger double flick).</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">R</span></td>
                                        <td>Right Face</td>
                                        <td>Clockwise 90°</td>
                                        <td>Turn right side UP away from you.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">R'</span></td>
                                        <td>Right Prime</td>
                                        <td>Anticlockwise 90°</td>
                                        <td>Turn right side DOWN towards you.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">L</span></td>
                                        <td>Left Face</td>
                                        <td>Clockwise 90°</td>
                                        <td>Turn left side DOWN towards you.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">L'</span></td>
                                        <td>Left Prime</td>
                                        <td>Anticlockwise 90°</td>
                                        <td>Turn left side UP away from you.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">F</span></td>
                                        <td>Front Face</td>
                                        <td>Clockwise 90°</td>
                                        <td>Turn front face like turning a car steering wheel right.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">F'</span></td>
                                        <td>Front Prime</td>
                                        <td>Anticlockwise 90°</td>
                                        <td>Turn front face to the left.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">D</span> / <span class="algo-chip-key">D'</span></td>
                                        <td>Down (Bottom)</td>
                                        <td>90° Turns</td>
                                        <td>Turn bottom layer with your ring fingers.</td>
                                    </tr>
                                    <tr>
                                        <td><span class="algo-chip-key">B</span> / <span class="algo-chip-key">B'</span></td>
                                        <td>Back Face</td>
                                        <td>90° Turns</td>
                                        <td>Turn rear face facing away from you.</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <!-- SECTION 9: SHORTCUTS & FAQ -->
                    <section id="manual-sec-shortcuts" class="manual-section">
                        <div class="manual-section-header">
                            <span class="sec-number">09</span>
                            <div class="sec-title-wrap">
                                <h2>Keyboard Shortcuts & FAQ</h2>
                                <p class="sec-subtitle">Speed up your workflow and quickly resolve common questions.</p>
                            </div>
                        </div>

                        <div class="manual-grid-2col">
                            <div class="manual-card">
                                <h3 class="card-title">⌨️ Universal Keyboard Shortcuts</h3>
                                <table class="manual-table">
                                    <thead>
                                        <tr>
                                            <th>Key</th>
                                            <th>Function / Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><kbd>Spacebar</kbd></td>
                                            <td>Capture Face in Scanner • Start/Stop Timer • Play/Pause in 3D</td>
                                        </tr>
                                        <tr>
                                            <td><kbd>→</kbd> (Right Arrow)</td>
                                            <td>Step Move ⏭ in 3D Solver & Cube Academy</td>
                                        </tr>
                                        <tr>
                                            <td><kbd>←</kbd> (Left Arrow)</td>
                                            <td>Step Previous Move ⏮ in 3D Solver</td>
                                        </tr>
                                        <tr>
                                            <td><kbd>R</kbd></td>
                                            <td>Reset Camera View ↺ to default isometric angle</td>
                                        </tr>
                                        <tr>
                                            <td><kbd>Esc</kbd></td>
                                            <td>Exit Fullscreen Solution Modal / Close Cheat Sheet</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div class="manual-card">
                                <h3 class="card-title">❓ Frequently Asked Questions (FAQ)</h3>
                                <div class="faq-accordion">
                                    <div class="faq-item">
                                        <strong>Q: Why did my physical cube get scrambled instead of solved after following the 3D moves?</strong>
                                        <p>A: The #1 most common mistake is holding the cube with the wrong center piece facing you! On every Rubik's cube, the 6 centers are permanently fixed. You must always hold <strong>Green in Front</strong>, <strong>RED on your Right</strong>, and <strong>White on Top</strong>. If your Right center was Orange or Blue, you were holding the cube backwards, so turning 'R' was twisting the wrong face on your physical cube!</p>
                                    </div>
                                    <div class="faq-item">
                                        <strong>Q: Why does the scanner or solver say "Invalid Cube Configuration"?</strong>
                                        <p>A: This almost always means the faces were scanned out of order or with incorrect center alignment. Verify that with White on Top and Green in Front, your <strong>Right face center is RED</strong>. A valid standard 3x3 cube also requires exactly 9 stickers of each color, and all corner/edge permutations must be physically reachable.</p>
                                    </div>
                                    <div class="faq-item">
                                        <strong>Q: Can I use this application without an internet connection?</strong>
                                        <p>A: Yes! CubeSolver 3D is a Progressive Web App (PWA). All Three.js graphics, solver algorithms, and assets are cached locally. Click <strong>⬇ Install</strong> in the header to run it like a native desktop app.</p>
                                    </div>
                                    <div class="faq-item">
                                        <strong>Q: Does it matter if my cube has different brand colors?</strong>
                                        <p>A: The computer vision engine uses intelligent color-space ratios (trimmed median) that easily handle both standard vinyl stickers and modern stickerless plastic cubes (Fluorescent Yellow, Light Orange, Deep Blue).</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>

                <!-- Manual Footer -->
                <footer class="manual-footer no-print">
                    <div class="footer-left">
                        <span>🧊 CubeSolver 3D Documentation</span>
                        <small>Engineered with Three.js, Herbert Kociemba 2-Phase Algorithm & Modern Web Standards.</small>
                    </div>
                    <button id="btn-manual-back-to-top" class="manual-action-btn secondary">
                        ↑ Back to Top
                    </button>
                </footer>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        // Print / Save as PDF button
        const printBtn = this.container.querySelector('#btn-manual-print');
        if (printBtn) {
            printBtn.addEventListener('click', () => this.printManual());
        }

        // Quick Jump Nav Pills
        const navPills = this.container.querySelectorAll('.manual-nav-pill');
        navPills.forEach(pill => {
            pill.addEventListener('click', () => {
                const targetId = pill.dataset.target;
                this.scrollToSection(targetId);
            });
        });

        // Back to top
        const backToTopBtn = this.container.querySelector('#btn-manual-back-to-top');
        if (backToTopBtn) {
            backToTopBtn.addEventListener('click', () => {
                const scrollEl = document.getElementById('panel-user-manual') || this.container;
                scrollEl.scrollTo({ top: 0, behavior: 'smooth' });
            });
        }
    }

    scrollToSection(sectionKey) {
        const target = this.container.querySelector(`#manual-sec-${sectionKey}`);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    printManual() {
        document.body.classList.add('printing-manual');
        window.print();
        
        window.addEventListener('afterprint', () => {
            document.body.classList.remove('printing-manual');
        }, { once: true });

        // Fallback cleanup
        setTimeout(() => {
            document.body.classList.remove('printing-manual');
        }, 3000);
    }
}
