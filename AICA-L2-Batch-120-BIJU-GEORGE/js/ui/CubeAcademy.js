/**
 * CubeAcademy.js - Interactive Rubik's Cube Masterclass for Kids & Beginners
 *
 * Designed specifically for a 12-year-old to master the Rubik's cube from scratch.
 * Based on the world's most proven beginner-to-expert pedagogy (CFOP Layer-by-Layer / LBL):
 *
 * Stage 0: 🧠 Cube Anatomy & The 2 Magic Moves ("Sexy Move" & Lefty Move)
 * Stage 1: 🌼 The Daisy (4 White Petals around Yellow Center)
 * Stage 2: 🏁 The White Cross & First Layer (Corners with Magic Move)
 * Stage 3: 🎽 The Middle Belt (Second Layer Edges & The "T" Trick)
 * Stage 4: ⏰ The Yellow Cross (The Clock Method: Dot -> 9:00 Hook -> Line -> Cross)
 * Stage 5: 🐟 The Yellow Face (Meet "Sune" the Fish Move)
 * Stage 6: 🚗 Position the Top Corners (Headlights & Niklas Corner Switcher)
 * Stage 7: 🏆 The Grand Finale (Upside-Down Magic Move to 100% Solved!)
 *
 * Features:
 * - Live Interactive 3D Playground with animated algorithm demonstrations
 * - Step-by-Step move stepper (Next Move / Prev Move) to follow along with real cube
 * - Catchy mnemonics, finger trick coaching, and common pitfalls
 * - Practice case generator for each stage
 * - Printable pocket cheat sheet
 */

import { CubeState } from '../model/CubeState.js';
import { Cube3D } from './Cube3D.js';
import { audio } from './AudioEffects.js';

export const ACADEMY_LESSONS = [
    {
        id: 0,
        stageNumber: "0",
        badge: "The Secret Weapons",
        title: "Meet the Cube & The 2 Magic Moves",
        icon: "🧠",
        subtitle: "Master the 4-move finger trick that solves 70% of the cube!",
        goal: "Learn how the pieces work and build muscle memory for the Righty and Lefty triggers.",
        story: "Before jumping into solving, you need to know the golden secret: center pieces NEVER move! Yellow is always opposite White, Blue opposite Green, and Red opposite Orange. There are 6 Centers (the Bosses), 12 Edges (2 colors), and 8 Corners (3 colors).",
        algorithms: [
            {
                name: "The Righty Trigger (The 'Sexy Move')",
                moves: ["R", "U", "R'", "U'"],
                mnemonic: "Right Up, Top Away, Right Down, Top Back!",
                cue: "Flick with your right index finger. Repeat it 6 times, and the cube magically returns to solved!"
            },
            {
                name: "The Lefty Trigger",
                moves: ["L'", "U'", "L", "U"],
                mnemonic: "Left Up, Top Away, Left Down, Top Back!",
                cue: "The exact mirror image using your left hand. Practice both!"
            }
        ],
        practiceMoves: ["R", "U", "R'", "U'", "R", "U", "R'", "U'", "R", "U", "R'", "U'", "R", "U", "R'", "U'", "R", "U", "R'", "U'", "R", "U", "R'", "U'"],
        presetScramble: "", // Solved cube to practice 6-cycle
        proTips: [
            "Use your right index finger to flick the top layer (U), don't turn your whole arm!",
            "Keep your thumb on the front center piece for stability."
        ],
        pitfalls: [
            "Don't turn the cube in your hands midway through a 4-move trigger."
        ]
    },
    {
        id: 1,
        stageNumber: "1",
        badge: "Stage 1",
        title: "The Daisy 🌼",
        icon: "🌼",
        subtitle: "Place 4 White petals around the Yellow center on top.",
        goal: "Collect all 4 white edge pieces around the yellow center. Side colors do not need to match yet!",
        story: "Hold the cube so the YELLOW center faces the ceiling. Your mission is to make a sweet yellow daisy by finding the 4 white edge pieces and parking them around the yellow center.",
        algorithms: [
            {
                name: "White Edge on Middle Layer",
                moves: ["R"],
                mnemonic: "One simple twist brings it straight up to the yellow center!",
                cue: "If another petal is already there, turn top layer (U) first to make space."
            },
            {
                name: "White Edge on Bottom Layer",
                moves: ["F2"],
                mnemonic: "Rotate the front face 180° to pop it up!",
                cue: "Two turns (F2) brings it from bottom floor to the penthouse."
            },
            {
                name: "Flipped / Backwards Petal",
                moves: ["F", "U'", "R"],
                mnemonic: "Turn Front sideways -> Clear top space -> Bring Right side up!",
                cue: "Fixes an upside-down white edge sticker in 3 quick twists."
            }
        ],
        practiceMoves: ["F", "U'", "R"],
        presetScramble: "D2 R2 F2 U2 B2 R2 D2 F2 L2 U2 F' L' U' B R' D F' L2 B2",
        proTips: [
            "Always keep the Yellow center facing the ceiling.",
            "Don't worry about corner pieces yet—even if white corners appear, ignore them!"
        ],
        pitfalls: [
            "Accidentally knocking out an existing white petal while bringing up a new one. Always turn U to an empty slot first!"
        ]
    },
    {
        id: 2,
        stageNumber: "2",
        badge: "Stage 2",
        title: "The White Cross & First Layer 🏁",
        icon: "🏁",
        subtitle: "Turn the daisy into the true White Cross and solve all 4 white corners.",
        goal: "Complete the entire White face and the first layer matching belts on all 4 sides.",
        story: "Look at your daisy petals. Each white petal has a side color (Red, Green, Blue, or Orange). Match that side color to its matching center piece, then flip it down 180° (F2) to the bottom! Once all 4 petals are flipped down, flip your cube upside-down so WHITE is now on the bottom forever!",
        algorithms: [
            {
                name: "Drop Petals to Make White Cross",
                moves: ["F2"],
                mnemonic: "Match side color to center -> Turn front 180° down!",
                cue: "Repeat for all 4 petals: Blue to Blue, Red to Red, Green to Green, Orange to Orange."
            },
            {
                name: "Slide Corners In (The Magic Move!)",
                moves: ["R", "U", "R'", "U'"],
                mnemonic: "Park corner above its slot -> Do Righty Trigger 1, 3, or 5 times!",
                cue: "Watch the corner twist right into its home slot on the bottom floor."
            }
        ],
        practiceMoves: ["R", "U", "R'", "U'"],
        presetScramble: "R U R' U' F' U2 F R U R' U'",
        proTips: [
            "White stays on the BOTTOM for the rest of the entire solve!",
            "Only park a corner above the slot that matches its TWO side colors."
        ],
        pitfalls: [
            "Putting a white corner in the wrong slot just because it's white. The side colors MUST match the neighboring centers!"
        ]
    },
    {
        id: 3,
        stageNumber: "3",
        badge: "Stage 3",
        title: "The Middle Layer Belt 🎽",
        icon: "🎽",
        subtitle: "Solve the second layer edges using the Big 'T' trick.",
        goal: "Insert all 4 non-yellow middle edges to complete the bottom two layers (F2L).",
        story: "Look on the top layer for any edge piece that does NOT have yellow on it. Turn the top layer until the front sticker matches its center, creating a giant vertical 'T' shape. Check the top sticker: does it need to go to the RIGHT slot or the LEFT slot?",
        algorithms: [
            {
                name: "Edge Goes to the RIGHT",
                moves: ["U", "R", "U", "R'", "U'", "F'", "U'", "F"],
                mnemonic: "Push AWAY to Left -> Righty Trigger -> Rotate cube right -> Lefty Trigger!",
                cue: "Formula: U (R U R' U') y' (L' U' L U)"
            },
            {
                name: "Edge Goes to the LEFT",
                moves: ["U'", "L'", "U'", "L", "U", "F", "U", "F'"],
                mnemonic: "Push AWAY to Right -> Lefty Trigger -> Rotate cube left -> Righty Trigger!",
                cue: "Formula: U' (L' U' L U) y (R U R' U')"
            }
        ],
        practiceMoves: ["U", "R", "U", "R'", "U'", "F'", "U'", "F"],
        presetScramble: "F R U' R' U' R U R' F' R U R' U'",
        proTips: [
            "If an edge is stuck in the middle layer backwards, do the Righty Trigger once to kick it out to the top layer!"
        ],
        pitfalls: [
            "Forgetting to push the edge AWAY from where it wants to go before doing the trigger."
        ]
    },
    {
        id: 4,
        stageNumber: "4",
        badge: "Stage 4",
        title: "The Yellow Cross ⏰",
        icon: "⏰",
        subtitle: "The Clock Method: Dot -> 9:00 Hook -> Horizontal Line -> Cross!",
        goal: "Form a yellow cross on the top face without messing up the bottom two layers.",
        story: "Look at the yellow pieces on top. You will see one of 4 patterns: a lone Dot (12:00), an 'L' shape (The 9:00 Hook), a Horizontal Line, or the full Cross. A single magic formula takes you through each stage!",
        algorithms: [
            {
                name: "The Clock Formula",
                moves: ["F", "R", "U", "R'", "U'", "F'"],
                mnemonic: "Face Down (F) -> 1 Righty Trigger (R U R' U') -> Face Back Up (F')!",
                cue: "If you have the 9:00 Hook, put one petal at 12:00 and one at 9:00. If you have the Line, hold it horizontally like a minus sign (-)."
            }
        ],
        practiceMoves: ["F", "R", "U", "R'", "U'", "F'"],
        presetScramble: "F R U R' U' F' F R U R' U' F'",
        proTips: [
            "Always hold the line HORIZONTALLY before doing the formula.",
            "Always put the 'L' hook at 9 o'clock and 12 o'clock."
        ],
        pitfalls: [
            "Holding the line vertically (|). It will reset you back to the hook!"
        ]
    },
    {
        id: 5,
        stageNumber: "5",
        badge: "Stage 5",
        title: "The Yellow Face: Meet Sune 🐟",
        icon: "🐟",
        subtitle: "The famous Fish Algorithm that turns the cross into a solid yellow roof.",
        goal: "Orient all yellow corners so the entire top face is solid yellow.",
        story: "Look at your yellow cross. Look for the 'FISH' shape (one yellow corner with little yellow fins sticking out). Put the fish's nose pointing to the BOTTOM-LEFT corner facing you, and feed the fish with Sune!",
        algorithms: [
            {
                name: "Sune (The Fish Algorithm)",
                moves: ["R", "U", "R'", "U", "R", "U2", "R'"],
                mnemonic: "Right Up, Top Away, Right Down, Top Away, Right Up, Top Away TWICE, Right Down!",
                cue: "Notice the rhythm: Up, Away, Down, Away, Up, TWICE, Down! Once or twice solves the whole yellow face."
            }
        ],
        practiceMoves: ["R", "U", "R'", "U", "R", "U2", "R'"],
        presetScramble: "R U R' U R U2 R'",
        proTips: [
            "If you don't see a fish yet, hold any yellow corner on the front-left and do Sune once. A fish will appear!"
        ],
        pitfalls: [
            "Forgetting that the 6th move is U2 (a DOUBLE turn of the top layer)."
        ]
    },
    {
        id: 6,
        stageNumber: "6",
        badge: "Stage 6",
        title: "Position Top Corners 🚗",
        icon: "🚗",
        subtitle: "Find the 'Headlights' and put all 4 corners in their true slots.",
        goal: "Cycle the top corners until all 4 corner pieces are in their correct slots.",
        story: "Look around the sides of the top layer. Are there two corners on the same side that share the same color (like car headlights 🟡--🟡)? Put those headlights in the BACK (facing away from you) and do the Niklas or Headlights algorithm!",
        algorithms: [
            {
                name: "Headlights Algorithm (WCA Standard)",
                moves: ["R'", "F", "R'", "B2", "R", "F'", "R'", "B2", "R2"],
                mnemonic: "Right Down, Front, Right Down, Back Twice, Right Up, Front Back, Right Down, Back Twice, Right Twice!",
                cue: "The most famous corner algorithm in competitive cubing."
            },
            {
                name: "Niklas Move (Kid-Friendly Alternative)",
                moves: ["U", "R", "U'", "L'", "U", "R'", "U'", "L"],
                mnemonic: "Top Right, Right Up, Top Left, Left Up, Top Right, Right Down, Top Left, Left Down!",
                cue: "Cycles corners smoothly with zero wrist strain."
            }
        ],
        practiceMoves: ["U", "R", "U'", "L'", "U", "R'", "U'", "L"],
        presetScramble: "R' F R' B2 R F' R' B2 R2",
        proTips: [
            "If no headlights exist on any side, do the algorithm once from anywhere. Headlights will appear!"
        ],
        pitfalls: [
            "B2 means turning the BACK face twice. Keep your grip steady."
        ]
    },
    {
        id: 7,
        stageNumber: "7",
        badge: "The Grand Finale",
        title: "The Final Corners & 100% Solved! 🏆",
        icon: "🏆",
        subtitle: "The upside-down Magic Move finish that snaps the whole cube solved!",
        goal: "Twist the final corners into place and celebrate your first complete Rubik's cube solve!",
        story: "This is the most thrilling step! Turn the cube UPSIDE DOWN so YELLOW is on the bottom and White is on top. Put an unsolved yellow corner in the bottom-right slot. Repeat the 4-move Righty Trigger until that yellow sticker snaps down into place!",
        algorithms: [
            {
                name: "The Upside-Down Magic Move",
                moves: ["R", "U", "R'", "U'"],
                mnemonic: "Do (R U R' U') 2 or 4 times until the yellow sticker points straight down!",
                cue: "GOLDEN RULE: Do NOT rotate the whole cube! ONLY turn the bottom layer (D) to bring the next unsolved corner to the bottom-right slot!"
            }
        ],
        practiceMoves: ["R", "U", "R'", "U'", "R", "U", "R'", "U'"],
        presetScramble: "R U R' U' R U R' U' D R U R' U' R U R' U' D'",
        proTips: [
            "The cube will look completely scrambled while doing this step! DO NOT PANIC! It fixes itself on the very last move!",
            "Always finish all 4 moves of R U R' U'—never stop after move 3!"
        ],
        pitfalls: [
            "THE #1 MISTAKE: Rotating the whole cube instead of twisting only the D layer to bring the next corner. Keep your front center locked!"
        ]
    }
];

export class CubeAcademy {
    constructor(containerElement) {
        this.container = containerElement;
        this.activeLessonIdx = 0;
        this.activeAlgoIdx = 0;
        this.cube3d = null;
        this.isPlayingAlgo = false;
        this.stepMoveIdx = 0;
        this.activeMoveSequence = [];
        this.currentPracticeState = null;

        this.init();
    }

    destroy() {
        this.isPlayingAlgo = false;
        if (this.cube3d && typeof this.cube3d.dispose === 'function') {
            this.cube3d.dispose();
            this.cube3d = null;
        }
    }

    init() {
        this.render();
    }

    render() {
        this.isPlayingAlgo = false;
        if (this.cube3d && typeof this.cube3d.dispose === 'function') {
            this.cube3d.dispose();
            this.cube3d = null;
        }
        this.container.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.className = 'academy-wrapper';

        // Header Banner
        const header = document.createElement('div');
        header.className = 'academy-header';
        header.innerHTML = `
            <div class="academy-header-left">
                <span class="academy-logo-badge">🎓 Cube Academy</span>
                <h1 class="academy-main-title">Master the Rubik's Cube in 7 Fun Stages</h1>
                <p class="academy-subtitle">The world's easiest kid-friendly method. Master the 2 secret moves and solve from ANY scramble!</p>
            </div>
            <div class="academy-header-right">
                <button id="btn-academy-cheatsheet" class="btn-academy-cheat">📄 Pocket Cheat Sheet</button>
            </div>
        `;
        wrapper.appendChild(header);

        // 2-Column Responsive Dashboard Layout
        const layoutGrid = document.createElement('div');
        layoutGrid.className = 'academy-layout-grid';

        // LEFT COLUMN: Course Stage Navigation Bar
        const navCol = document.createElement('div');
        navCol.className = 'academy-nav-col';
        const navList = this.createStageNavList();
        navCol.appendChild(navList);
        layoutGrid.appendChild(navCol);

        // RIGHT COLUMN: Active Stage Lesson & 3D Practice Playground
        const contentCol = document.createElement('div');
        contentCol.className = 'academy-content-col';
        const lessonView = this.createLessonView();
        contentCol.appendChild(lessonView);
        layoutGrid.appendChild(contentCol);

        wrapper.appendChild(layoutGrid);
        this.container.appendChild(wrapper);

        // Cheat sheet click handler
        const cheatBtn = wrapper.querySelector('#btn-academy-cheatsheet');
        if (cheatBtn) {
            cheatBtn.addEventListener('click', () => this.showCheatSheetModal());
        }

        // Initialize 3D Practice Playground Canvas
        this.init3DPracticeCanvas();
    }

    createStageNavList() {
        const container = document.createElement('div');
        container.className = 'academy-stage-list';

        ACADEMY_LESSONS.forEach((lesson, idx) => {
            const btn = document.createElement('button');
            btn.className = `academy-stage-item ${idx === this.activeLessonIdx ? 'active' : ''}`;
            btn.innerHTML = `
                <span class="stage-item-icon">${lesson.icon}</span>
                <div class="stage-item-info">
                    <span class="stage-item-badge">${lesson.badge}</span>
                    <span class="stage-item-title">${lesson.title}</span>
                </div>
                <span class="stage-item-arrow">→</span>
            `;

            btn.addEventListener('click', () => {
                if (this.activeLessonIdx !== idx) {
                    this.activeLessonIdx = idx;
                    this.activeAlgoIdx = 0;
                    audio.playTurnClick();
                    this.render();
                }
            });

            container.appendChild(btn);
        });

        // Speedcubing Secrets Card at bottom of nav
        const proTipsCard = document.createElement('div');
        proTipsCard.className = 'academy-protips-card';
        proTipsCard.innerHTML = `
            <div class="protips-header">⚡ Sub-60 Roadmap</div>
            <div class="protips-desc">Want to solve in under 1 minute? Use index finger flicks, look ahead, and practice Sune!</div>
        `;
        container.appendChild(proTipsCard);

        return container;
    }

    createLessonView() {
        const lesson = ACADEMY_LESSONS[this.activeLessonIdx];

        const card = document.createElement('div');
        card.className = 'academy-lesson-card';

        // 1. Lesson Header
        const header = document.createElement('div');
        header.className = 'lesson-header';
        header.innerHTML = `
            <div class="lesson-badge-row">
                <span class="lesson-stage-pill">${lesson.badge}</span>
                <span class="lesson-goal-pill">🎯 Goal: ${lesson.goal}</span>
            </div>
            <h2 class="lesson-title">${lesson.icon} ${lesson.title}</h2>
            <p class="lesson-story">${lesson.story}</p>
        `;
        card.appendChild(header);

        // 2. Interactive 3D Practice Playground
        const curAlgo = lesson.algorithms[this.activeAlgoIdx] || lesson.algorithms[0] || { name: 'Algorithm', moves: [], mnemonic: '' };
        const practiceArea = document.createElement('div');
        practiceArea.className = 'lesson-practice-area';

        practiceArea.innerHTML = `
            <div class="practice-top-bar">
                <span class="practice-title">🕹️ Interactive 3D Practice Lab</span>
                <span class="practice-status-hint">Follow along with your cube or watch the algorithm in 3D!</span>
            </div>
            <div class="practice-main-row">
                <div id="academy-3d-canvas-wrap" class="academy-canvas-wrap"></div>
                <div class="practice-controls-wrap">
                    <div class="practice-algo-title">${curAlgo.name}</div>
                    <div class="practice-chips-row" id="practice-chips-row">
                        ${curAlgo.moves.map(m => `<span class="algo-chip-key">${m}</span>`).join('')}
                    </div>
                    <div class="practice-mnemonic">"${curAlgo.mnemonic}"</div>
                    
                    <div class="practice-btns-grid">
                        <button id="btn-algo-play" class="btn-practice-action primary">▶ Play Algorithm</button>
                        <button id="btn-algo-step-next" class="btn-practice-action">Step Move ⏭</button>
                        <button id="btn-algo-reset" class="btn-practice-action">↺ Reset</button>
                        <button id="btn-algo-scramble" class="btn-practice-action">🎯 Practice Case</button>
                    </div>
                    <div class="practice-step-counter" id="practice-step-counter">Move: 0 of ${curAlgo.moves.length}</div>
                </div>
            </div>
        `;
        card.appendChild(practiceArea);

        // 3. Algorithm Cards Section (clickable to load into 3D lab)
        if (lesson.algorithms && lesson.algorithms.length > 0) {
            const algoSection = document.createElement('div');
            algoSection.className = 'lesson-algos-section';

            lesson.algorithms.forEach((algo, idx) => {
                const item = document.createElement('div');
                const isCur = (idx === this.activeAlgoIdx);
                item.className = `lesson-algo-box ${isCur ? 'active' : ''}`;
                item.innerHTML = `
                    <div class="algo-box-header">
                        <span class="algo-box-name">${algo.name} ${isCur ? '<span class="algo-loaded-badge">● Active in 3D</span>' : ''}</span>
                        <span class="algo-box-cue">${algo.cue}</span>
                    </div>
                    <div class="algo-box-chips">
                        ${algo.moves.map(m => `<span class="algo-chip-key">${m}</span>`).join('')}
                    </div>
                    <div class="algo-box-mnemonic">🗣️ Mnemonic: <strong>"${algo.mnemonic}"</strong></div>
                `;
                item.addEventListener('click', () => {
                    this.selectAlgorithm(idx);
                });
                algoSection.appendChild(item);
            });
            card.appendChild(algoSection);
        }

        // 4. Pro Tips & Mistakes to Avoid
        const coachingRow = document.createElement('div');
        coachingRow.className = 'lesson-coaching-row';

        const tipsCol = document.createElement('div');
        tipsCol.className = 'coaching-col tips';
        tipsCol.innerHTML = `
            <div class="coaching-title">💡 Pro Tips for 12-Year-Olds</div>
            <ul>${lesson.proTips.map(t => `<li>${t}</li>`).join('')}</ul>
        `;

        const pitfallsCol = document.createElement('div');
        pitfallsCol.className = 'coaching-col pitfalls';
        pitfallsCol.innerHTML = `
            <div class="coaching-title">⚠️ Common Mistakes to Avoid</div>
            <ul>${lesson.pitfalls.map(p => `<li>${p}</li>`).join('')}</ul>
        `;

        coachingRow.appendChild(tipsCol);
        coachingRow.appendChild(pitfallsCol);
        card.appendChild(coachingRow);

        // 5. Bottom Navigation Actions (Next Stage / Previous Stage)
        const bottomNav = document.createElement('div');
        bottomNav.className = 'lesson-bottom-nav';

        const prevBtn = document.createElement('button');
        prevBtn.className = 'btn-scanner-action';
        prevBtn.innerHTML = '<span>⏮</span> Previous Lesson';
        prevBtn.disabled = (this.activeLessonIdx <= 0);
        prevBtn.addEventListener('click', () => {
            if (this.activeLessonIdx > 0) {
                this.activeLessonIdx--;
                this.activeAlgoIdx = 0;
                audio.playTurnClick();
                this.render();
            }
        });

        const nextBtn = document.createElement('button');
        nextBtn.className = 'btn-scanner-action snap-action';
        nextBtn.style.padding = '10px 22px';
        nextBtn.innerHTML = (this.activeLessonIdx < ACADEMY_LESSONS.length - 1)
            ? '<span>Next Lesson →</span>'
            : '<span>🎉 All Stages Complete! Solve Any Cube!</span>';

        nextBtn.addEventListener('click', () => {
            if (this.activeLessonIdx < ACADEMY_LESSONS.length - 1) {
                this.activeLessonIdx++;
                this.activeAlgoIdx = 0;
                audio.playTurnClick();
                this.render();
            } else {
                audio.playSolvedChime();
                alert("🏆 You've mastered all 7 stages of the Rubik's Cube! Grab your physical cube and show your family and friends your speed!");
            }
        });

        bottomNav.appendChild(prevBtn);
        bottomNav.appendChild(nextBtn);
        card.appendChild(bottomNav);

        return card;
    }

    init3DPracticeCanvas() {
        const wrap = this.container.querySelector('#academy-3d-canvas-wrap');
        if (!wrap) return;

        wrap.innerHTML = '';

        if (this.cube3d && typeof this.cube3d.dispose === 'function') {
            this.cube3d.dispose();
            this.cube3d = null;
        }

        const lesson = ACADEMY_LESSONS[this.activeLessonIdx];
        const algo = lesson.algorithms[this.activeAlgoIdx] || lesson.algorithms[0];
        this.activeMoveSequence = [...(algo?.moves || [])];
        this.stepMoveIdx = 0;

        this.cube3d = new Cube3D(wrap, { turnSpeedMs: 280 });

        // Set starting state
        this.resetStageCubeState();

        // Bind 3D playground buttons
        const playBtn = this.container.querySelector('#btn-algo-play');
        const stepNextBtn = this.container.querySelector('#btn-algo-step-next');
        const resetBtn = this.container.querySelector('#btn-algo-reset');
        const scrambleBtn = this.container.querySelector('#btn-algo-scramble');

        if (playBtn) {
            playBtn.addEventListener('click', () => this.playFullAlgorithm());
        }
        if (stepNextBtn) {
            stepNextBtn.addEventListener('click', () => this.stepNextMove());
        }
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetStageCubeState();
                audio.playTurnClick();
            });
        }
        if (scrambleBtn) {
            scrambleBtn.addEventListener('click', () => {
                this.loadPracticeScramble();
                audio.playTurnClick();
            });
        }
    }

    selectAlgorithm(algoIdx) {
        const lesson = ACADEMY_LESSONS[this.activeLessonIdx];
        if (!lesson.algorithms || !lesson.algorithms[algoIdx]) return;

        this.activeAlgoIdx = algoIdx;
        const algo = lesson.algorithms[algoIdx];
        this.activeMoveSequence = [...algo.moves];
        this.stepMoveIdx = 0;

        const titleEl = this.container.querySelector('.practice-algo-title');
        if (titleEl) titleEl.textContent = algo.name;

        const chipsRow = this.container.querySelector('#practice-chips-row');
        if (chipsRow) {
            chipsRow.innerHTML = algo.moves.map(m => `<span class="algo-chip-key">${m}</span>`).join('');
        }

        const mnemonicEl = this.container.querySelector('.practice-mnemonic');
        if (mnemonicEl) mnemonicEl.textContent = `"${algo.mnemonic}"`;

        const boxes = this.container.querySelectorAll('.lesson-algo-box');
        boxes.forEach((box, i) => {
            box.classList.toggle('active', i === algoIdx);
            const badge = box.querySelector('.algo-loaded-badge');
            if (badge) badge.remove();
            if (i === algoIdx) {
                const nameEl = box.querySelector('.algo-box-name');
                if (nameEl) {
                    nameEl.insertAdjacentHTML('beforeend', ' <span class="algo-loaded-badge">● Active in 3D</span>');
                }
            }
        });

        this.resetStageCubeState();
        audio.playTurnClick();
    }

    resetStageCubeState() {
        this.isPlayingAlgo = false;
        const playBtn = this.container.querySelector('#btn-algo-play');
        const stepBtn = this.container.querySelector('#btn-algo-step-next');
        if (playBtn) {
            playBtn.disabled = false;
            playBtn.textContent = '▶ Play Algorithm';
        }
        if (stepBtn) stepBtn.disabled = false;

        const lesson = ACADEMY_LESSONS[this.activeLessonIdx];
        let state = CubeState.solved();

        if (lesson.presetScramble) {
            state = state.applyMoves(lesson.presetScramble);
        }

        this.currentPracticeState = state;
        if (this.cube3d) {
            this.cube3d.updateFromCubeState(this.currentPracticeState);
        }

        this.stepMoveIdx = 0;
        this.updateStepDisplay();
    }

    loadPracticeScramble() {
        this.isPlayingAlgo = false;
        const playBtn = this.container.querySelector('#btn-algo-play');
        const stepBtn = this.container.querySelector('#btn-algo-step-next');
        if (playBtn) {
            playBtn.disabled = false;
            playBtn.textContent = '▶ Play Algorithm';
        }
        if (stepBtn) stepBtn.disabled = false;

        const lesson = ACADEMY_LESSONS[this.activeLessonIdx];
        let state = CubeState.solved();

        const activeMoves = (this.activeMoveSequence && this.activeMoveSequence.length > 0)
            ? this.activeMoveSequence
            : (lesson.algorithms[this.activeAlgoIdx]?.moves || lesson.algorithms[0]?.moves || []);

        if (activeMoves.length > 0) {
            const inverted = [...activeMoves].reverse().map(m => {
                if (m.endsWith('2')) return m;
                if (m.endsWith("'")) return m.slice(0, -1);
                return m + "'";
            });
            state = state.applyMoves(inverted.join(' '));
        } else if (lesson.presetScramble) {
            state = state.applyMoves(lesson.presetScramble);
        }

        this.currentPracticeState = state;
        if (this.cube3d) {
            this.cube3d.updateFromCubeState(this.currentPracticeState);
        }
        this.stepMoveIdx = 0;
        this.updateStepDisplay();
    }

    stepNextMove() {
        if (this.isPlayingAlgo || !this.cube3d || !this.currentPracticeState) return;

        if (this.stepMoveIdx >= this.activeMoveSequence.length) {
            this.stepMoveIdx = 0;
        }

        const move = this.activeMoveSequence[this.stepMoveIdx];
        this.stepMoveIdx++;

        const nextState = this.currentPracticeState.applyMove(move);
        this.cube3d.animateMove(move, nextState, () => {
            this.currentPracticeState = nextState;
            this.updateStepDisplay();
            audio.playTurnClick();
        });
    }

    playFullAlgorithm() {
        if (this.isPlayingAlgo || !this.cube3d || !this.currentPracticeState) return;

        this.isPlayingAlgo = true;
        const playBtn = this.container.querySelector('#btn-algo-play');
        const stepBtn = this.container.querySelector('#btn-algo-step-next');
        if (playBtn) {
            playBtn.disabled = true;
            playBtn.textContent = '⏳ Playing...';
        }
        if (stepBtn) stepBtn.disabled = true;

        const moves = [...this.activeMoveSequence];
        let idx = 0;

        const executeNext = () => {
            if (!this.isPlayingAlgo) return;
            if (idx >= moves.length) {
                this.isPlayingAlgo = false;
                if (playBtn) {
                    playBtn.disabled = false;
                    playBtn.textContent = '▶ Play Algorithm';
                }
                if (stepBtn) stepBtn.disabled = false;
                audio.playTurnClick();
                return;
            }

            const m = moves[idx];
            idx++;
            this.stepMoveIdx = idx;
            this.updateStepDisplay();

            const nextState = this.currentPracticeState.applyMove(m);
            this.cube3d.animateMove(m, nextState, () => {
                this.currentPracticeState = nextState;
                if (this.isPlayingAlgo) {
                    setTimeout(executeNext, 120);
                }
            });
        };

        executeNext();
    }

    updateStepDisplay() {
        const counter = this.container.querySelector('#practice-step-counter');
        if (counter) {
            counter.textContent = `Move: ${this.stepMoveIdx} of ${this.activeMoveSequence.length}`;
        }

        const chips = this.container.querySelectorAll('.algo-chip-key');
        chips.forEach((c, idx) => {
            if (idx === this.stepMoveIdx - 1) {
                c.classList.add('active');
            } else {
                c.classList.remove('active');
            }
        });
    }

    showCheatSheetModal() {
        const modal = document.createElement('div');
        modal.className = 'academy-cheatsheet-modal';

        modal.innerHTML = `
            <div class="cheatsheet-card">
                <div class="cheatsheet-header">
                    <h2>📄 1-Page Rubik's Cube Pocket Cheat Sheet</h2>
                    <button class="header-btn" id="btn-close-cheatsheet">✕ Close</button>
                </div>
                <div class="cheatsheet-body">
                    <table class="cheatsheet-table">
                        <thead>
                            <tr>
                                <th>Stage</th>
                                <th>Name & Mnemonic</th>
                                <th>Formula (Algorithm)</th>
                                <th>Pro Tip</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>0</strong></td>
                                <td><strong>The 4-Move Magic Trick</strong><br><small>Sexy Move</small></td>
                                <td><code>R U R' U'</code></td>
                                <td>Up, Away, Down, Back. 6 cycles reset cube!</td>
                            </tr>
                            <tr>
                                <td><strong>1</strong></td>
                                <td><strong>The Daisy</strong><br><small>Yellow center</small></td>
                                <td><code>F / R / F' U' R</code></td>
                                <td>Put 4 white petals around yellow center.</td>
                            </tr>
                            <tr>
                                <td><strong>2</strong></td>
                                <td><strong>White Cross & Layer 1</strong><br><small>White on bottom</small></td>
                                <td><code>F2</code> then <code>R U R' U'</code></td>
                                <td>Flip side matching petals down. Solve corners with Righty Trigger.</td>
                            </tr>
                            <tr>
                                <td><strong>3</strong></td>
                                <td><strong>Middle Belt</strong><br><small>Big 'T' trick</small></td>
                                <td><code>U (R U R' U') y' (L' U' L U)</code></td>
                                <td>Push away from slot -> Trigger -> Turn cube -> Mirror Trigger!</td>
                            </tr>
                            <tr>
                                <td><strong>4</strong></td>
                                <td><strong>Yellow Cross</strong><br><small>Clock Method</small></td>
                                <td><code>F (R U R' U') F'</code></td>
                                <td>Dot (12:00) -> Hook (9:00) -> Line (-) -> Cross!</td>
                            </tr>
                            <tr>
                                <td><strong>5</strong></td>
                                <td><strong>Yellow Face</strong><br><small>Meet Sune the Fish</small></td>
                                <td><code>R U R' U R U2 R'</code></td>
                                <td>Put fish head at bottom-left. Up, Away, Down, Away, Up, TWICE, Down!</td>
                            </tr>
                            <tr>
                                <td><strong>6</strong></td>
                                <td><strong>Position Corners</strong><br><small>Headlights</small></td>
                                <td><code>R' F R' B2 R F' R' B2 R2</code><br>or <code>U R U' L' U R' U' L</code></td>
                                <td>Put matching headlights in the back!</td>
                            </tr>
                            <tr>
                                <td><strong>7</strong></td>
                                <td><strong>The Grand Finale</strong><br><small>Upside Down Finish</small></td>
                                <td><code>R U R' U'</code> (2x or 4x)</td>
                                <td>Yellow on bottom! Only turn D layer to bring next corner!</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.querySelector('#btn-close-cheatsheet').addEventListener('click', () => {
            modal.remove();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }
}
