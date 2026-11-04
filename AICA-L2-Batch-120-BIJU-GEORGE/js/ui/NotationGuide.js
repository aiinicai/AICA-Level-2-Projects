/**
 * NotationGuide.js - Interactive Rubik's Cube Move Notation Reference & Playground
 * Allows users to learn and interactively test every official WCA move.
 */

import { audio } from './AudioEffects.js';

export const NOTATION_DATA = [
    {
        category: "Face Turns (Basic)",
        moves: [
            { notation: "U", name: "Up (Top)", desc: "Turn Top layer to the LEFT (Clockwise)." },
            { notation: "U'", name: "Up Prime", desc: "Turn Top layer to the RIGHT (Anticlockwise)." },
            { notation: "U2", name: "Up Double", desc: "Turn Top layer to the LEFT 180° (Two quarter turns)." },
            { notation: "D", name: "Down (Bottom)", desc: "Turn Bottom layer to the RIGHT (Clockwise)." },
            { notation: "D'", name: "Down Prime", desc: "Turn Bottom layer to the LEFT (Anticlockwise)." },
            { notation: "D2", name: "Down Double", desc: "Turn Bottom layer to the RIGHT 180° (Two quarter turns)." },
            { notation: "R", name: "Right", desc: "Turn Right layer UP away from you (Clockwise)." },
            { notation: "R'", name: "Right Prime", desc: "Turn Right layer DOWN towards you (Anticlockwise)." },
            { notation: "R2", name: "Right Double", desc: "Turn Right layer UP 180° (Two quarter turns)." },
            { notation: "L", name: "Left", desc: "Turn Left layer DOWN towards you (Clockwise)." },
            { notation: "L'", name: "Left Prime", desc: "Turn Left layer UP away from you (Anticlockwise)." },
            { notation: "L2", name: "Left Double", desc: "Turn Left layer DOWN 180° (Two quarter turns)." },
            { notation: "F", name: "Front", desc: "Rotate Front face CLOCKWISE (Top moves to Right)." },
            { notation: "F'", name: "Front Prime", desc: "Rotate Front face ANTICLOCKWISE (Top moves to Left)." },
            { notation: "F2", name: "Front Double", desc: "Rotate Front face 180° (Two quarter turns)." },
            { notation: "B", name: "Back", desc: "Turn Back layer to the LEFT (Clockwise when looking at back)." },
            { notation: "B'", name: "Back Prime", desc: "Turn Back layer to the RIGHT (Anticlockwise when looking at back)." },
            { notation: "B2", name: "Back Double", desc: "Turn Back layer to the LEFT 180° (Two quarter turns)." }
        ]
    },
    {
        category: "Slice Turns (Advanced)",
        moves: [
            { notation: "M", name: "Middle Slice", desc: "Rotate the vertical middle layer in the direction of an L move (downwards)." },
            { notation: "M'", name: "Middle Slice Prime", desc: "Rotate the vertical middle layer in the direction of an R move (upwards)." },
            { notation: "E", name: "Equator Slice", desc: "Rotate the horizontal middle layer in the direction of a D move." },
            { notation: "S", name: "Standing Slice", desc: "Rotate the middle layer between Front and Back in the direction of an F move." }
        ]
    }
];

export class NotationGuide {
    constructor(containerElement, onMoveTest = null) {
        this.container = containerElement;
        this.onMoveTest = onMoveTest;
        this.init();
    }

    init() {
        this.render();
    }

    render() {
        this.container.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.className = 'notation-guide-wrapper';

        const intro = document.createElement('div');
        intro.className = 'guide-intro';
        intro.innerHTML = `
            <div class="guide-title">📖 Interactive Notation Guide</div>
            <div class="guide-subtitle">Tap any move button to see it animated live on the 3D cube!</div>
        `;
        wrapper.appendChild(intro);

        for (const cat of NOTATION_DATA) {
            const catSec = document.createElement('div');
            catSec.className = 'guide-category-section';

            const catTitle = document.createElement('div');
            catTitle.className = 'guide-cat-title';
            catTitle.textContent = cat.category;
            catSec.appendChild(catTitle);

            const grid = document.createElement('div');
            grid.className = 'guide-moves-grid';

            for (const item of cat.moves) {
                const card = document.createElement('div');
                card.className = 'guide-move-card';

                card.innerHTML = `
                    <div class="move-card-top">
                        <button class="btn-notation-test">${item.notation}</button>
                        <span class="move-card-name">${item.name}</span>
                    </div>
                    <div class="move-card-desc">${item.desc}</div>
                `;

                const btn = card.querySelector('.btn-notation-test');
                btn.addEventListener('click', () => {
                    audio.playTurnClick();
                    if (this.onMoveTest) {
                        this.onMoveTest(item.notation);
                    }
                });

                grid.appendChild(card);
            }

            catSec.appendChild(grid);
            wrapper.appendChild(catSec);
        }

        this.container.appendChild(wrapper);
    }
}
