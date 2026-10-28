/**
 * CubeState.js - Complete 54-facelet 3x3 Rubik's Cube Model
 * Follows standard Kociemba facelet order:
 * U1..U9 (0..8)   - Up / White (U)
 * R1..R9 (9..17)  - Right / Red (R)
 * F1..F9 (18..26) - Front / Green (F)
 * D1..D9 (27..35) - Down / Yellow (D)
 * L1..L9 (36..44) - Left / Orange (L)
 * B1..B9 (45..53) - Back / Blue (B)
 */

export const CubeColor = Object.freeze({
    U: { letter: 'U', name: 'White', hex: '#FFFFFF', darkHex: '#D1D5DB' },
    R: { letter: 'R', name: 'Red', hex: '#DC2626', darkHex: '#991B1B' },
    F: { letter: 'F', name: 'Green', hex: '#16A34A', darkHex: '#166534' },
    D: { letter: 'D', name: 'Yellow', hex: '#FACC15', darkHex: '#CA8A04' },
    L: { letter: 'L', name: 'Orange', hex: '#EA580C', darkHex: '#9A3412' },
    B: { letter: 'B', name: 'Blue', hex: '#2563EB', darkHex: '#1E40AF' }
});

export const FACE_NAMES = ['U', 'R', 'F', 'D', 'L', 'B'];

export const FACE_INDEX = {
    U: 0, R: 1, F: 2, D: 3, L: 4, B: 5
};

export const MOVES_ALL = [
    'U', "U'", 'U2',
    'R', "R'", 'R2',
    'F', "F'", 'F2',
    'D', "D'", 'D2',
    'L', "L'", 'L2',
    'B', "B'", 'B2'
];

export class CubeState {
    constructor(facelets = null) {
        if (facelets && facelets.length === 54) {
            this.facelets = [...facelets];
        } else {
            this.facelets = CubeState.solvedFacelets();
        }
    }

    clone() {
        return new CubeState([...this.facelets]);
    }

    static solvedFacelets() {
        const arr = new Array(54);
        for (let i = 0; i < 9; i++) arr[i] = 'U';
        for (let i = 9; i < 18; i++) arr[i] = 'R';
        for (let i = 18; i < 27; i++) arr[i] = 'F';
        for (let i = 27; i < 36; i++) arr[i] = 'D';
        for (let i = 36; i < 45; i++) arr[i] = 'L';
        for (let i = 45; i < 54; i++) arr[i] = 'B';
        return arr;
    }

    static solved() {
        return new CubeState(CubeState.solvedFacelets());
    }

    static fromString(str) {
        const clean = str.trim().toUpperCase();
        if (clean.length !== 54) {
            throw new Error(`Facelet string must have 54 characters, got ${clean.length}`);
        }
        return new CubeState(clean.split(''));
    }

    toString() {
        return this.facelets.join('');
    }

    getFaceStickers(faceName) {
        const idx = FACE_INDEX[faceName];
        const start = idx * 9;
        return this.facelets.slice(start, start + 9);
    }

    setSticker(faceName, indexOnFace, colorLetter) {
        const idx = FACE_INDEX[faceName];
        this.facelets[idx * 9 + indexOnFace] = colorLetter;
    }

    setGlobalSticker(globalIndex, colorLetter) {
        if (globalIndex >= 0 && globalIndex < 54) {
            this.facelets[globalIndex] = colorLetter;
        }
    }

    getColorCounts() {
        const counts = { U: 0, R: 0, F: 0, D: 0, L: 0, B: 0 };
        for (const c of this.facelets) {
            if (counts[c] !== undefined) counts[c]++;
        }
        return counts;
    }

    isColorDistributionValid() {
        const counts = this.getColorCounts();
        return Object.values(counts).every(c => c === 9);
    }

    isSolved() {
        for (let f = 0; f < 6; f++) {
            const start = f * 9;
            const center = this.facelets[start + 4];
            for (let i = 0; i < 9; i++) {
                if (this.facelets[start + i] !== center) return false;
            }
        }
        return true;
    }

    /**
     * Executes single quarter-turn clockwise on the given face.
     */
    rotateQuarterClockwise(face) {
        const f = [...this.facelets];
        const base = FACE_INDEX[face] * 9;
        const old = f.slice(base, base + 9);

        // 1. Rotate the 9 stickers of the face
        f[base + 0] = old[6];
        f[base + 1] = old[3];
        f[base + 2] = old[0];
        f[base + 3] = old[7];
        f[base + 4] = old[4];
        f[base + 5] = old[1];
        f[base + 6] = old[8];
        f[base + 7] = old[5];
        f[base + 8] = old[2];

        // 2. Cycle the 12 adjacent border stickers
        switch (face) {
            case 'U': {
                const t0 = f[45], t1 = f[46], t2 = f[47];
                f[45] = f[36]; f[46] = f[37]; f[47] = f[38];
                f[36] = f[18]; f[37] = f[19]; f[38] = f[20];
                f[18] = f[9];  f[19] = f[10]; f[20] = f[11];
                f[9] = t0;     f[10] = t1;    f[11] = t2;
                break;
            }
            case 'D': {
                const t0 = f[15], t1 = f[16], t2 = f[17];
                f[15] = f[24]; f[16] = f[25]; f[17] = f[26];
                f[24] = f[42]; f[25] = f[43]; f[26] = f[44];
                f[42] = f[51]; f[43] = f[52]; f[44] = f[53];
                f[51] = t0;    f[52] = t1;    f[53] = t2;
                break;
            }
            case 'F': {
                const t6 = f[6], t7 = f[7], t8 = f[8];
                f[6] = f[44]; f[7] = f[41]; f[8] = f[38];
                f[44] = f[29]; f[41] = f[28]; f[38] = f[27];
                f[27] = f[15]; f[28] = f[12]; f[29] = f[9];
                f[9] = t6;    f[12] = t7;   f[15] = t8;
                break;
            }
            case 'B': {
                const t0 = f[0], t1 = f[1], t2 = f[2];
                f[0] = f[11]; f[1] = f[14]; f[2] = f[17];
                f[11] = f[35]; f[14] = f[34]; f[17] = f[33];
                f[33] = f[36]; f[34] = f[39]; f[35] = f[42];
                f[36] = t2;   f[39] = t1;   f[42] = t0;
                break;
            }
            case 'R': {
                const t2 = f[2], t5 = f[5], t8 = f[8];
                f[2] = f[20]; f[5] = f[23]; f[8] = f[26];
                f[20] = f[29]; f[23] = f[32]; f[26] = f[35];
                f[29] = f[51]; f[32] = f[48]; f[35] = f[45];
                f[45] = t8;   f[48] = t5;   f[51] = t2;
                break;
            }
            case 'L': {
                const t0 = f[0], t3 = f[3], t6 = f[6];
                f[0] = f[53]; f[3] = f[50]; f[6] = f[47];
                f[47] = f[33]; f[50] = f[30]; f[53] = f[27];
                f[27] = f[18]; f[30] = f[21]; f[33] = f[24];
                f[18] = t0;   f[21] = t3;   f[24] = t6;
                break;
            }
        }

        return new CubeState(f);
    }

    /**
     * Applies a standard move (e.g., "R", "U'", "F2").
     */
    applyMove(moveNotation) {
        const notation = moveNotation.trim();
        if (!notation) return this;

        // Extended moves support (M, E, S, x, y, z)
        if (notation === 'M') return this.applyMoves("L' R x'");
        if (notation === "M'") return this.applyMoves("L R' x");
        if (notation === 'M2') return this.applyMoves("M M");
        if (notation === 'E') return this.applyMoves("U D' y'");
        if (notation === "E'") return this.applyMoves("U' D y");
        if (notation === 'E2') return this.applyMoves("E E");
        if (notation === 'S') return this.applyMoves("F' B z");
        if (notation === "S'") return this.applyMoves("F B' z'");
        if (notation === 'S2') return this.applyMoves("S S");

        const face = notation[0];
        if (!FACE_INDEX.hasOwnProperty(face)) return this;

        let times = 1;
        if (notation.endsWith("2")) times = 2;
        else if (notation.endsWith("'")) times = 3;

        let curr = this;
        for (let i = 0; i < times; i++) {
            curr = curr.rotateQuarterClockwise(face);
        }
        return curr;
    }

    applyMoves(seq) {
        if (!seq) return this;
        const tokens = typeof seq === 'string' ? seq.trim().split(/\s+/) : seq;
        let curr = this;
        for (const token of tokens) {
            if (token) curr = curr.applyMove(token);
        }
        return curr;
    }

    applyAlgorithm(seq) {
        return this.applyMoves(seq);
    }

    // Presets
    static presets = {
        checkerboard: "U2 D2 R2 L2 F2 B2",
        superflip: "U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2",
        easy: "R U R' U' F' U F",
        cubeInCube: "F L F U' R U F2 L2 U' L' B D' B' L2 U",
        anaconda: "L U B' U' R L' B R' F B' D R D' F'",
        python: "F2 R' B' U R' L F' L F' B D' R B L2",
        cross: "R2 L' D F2 R' D' R' L U' D R D' B2 R'",
        wire: "R L F B R L F B R L F B",
        fourSpots: "F2 B2 U D' R2 L2 U D'"
    };

    static getPreset(name) {
        const seq = CubeState.presets[name];
        if (!seq) return CubeState.solved();
        return CubeState.solved().applyMoves(seq);
    }

    static generateRandomScramble(moveCount = 20) {
        const moves = MOVES_ALL;
        const result = [];
        let lastFace = '';
        let secondLastFace = '';

        for (let i = 0; i < moveCount; i++) {
            let candidate;
            let face;
            do {
                candidate = moves[Math.floor(Math.random() * moves.length)];
                face = candidate[0];
            } while (face === lastFace || (face === secondLastFace && (
                (face === 'U' && lastFace === 'D') || (face === 'D' && lastFace === 'U') ||
                (face === 'L' && lastFace === 'R') || (face === 'R' && lastFace === 'L') ||
                (face === 'F' && lastFace === 'B') || (face === 'B' && lastFace === 'F')
            )));

            secondLastFace = lastFace;
            lastFace = face;
            result.push(candidate);
        }

        const scrambleStr = result.join(' ');
        const scrambledState = CubeState.solved().applyMoves(scrambleStr);
        return {
            state: scrambledState,
            scrambleStr: scrambleStr,
            moves: result
        };
    }
}
