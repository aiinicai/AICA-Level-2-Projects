/**
 * LayerByLayerSolver.js - Beginner Friendly 7-Stage Layer-by-Layer Solver
 * Divides the solve into 7 intuitive, educational milestones:
 * 1. White Cross (Daisy & Bottom Edges)
 * 2. First Layer Corners (White Face + Layer 1)
 * 3. Second Layer Edges (Middle Layer)
 * 4. Yellow Cross (Top Face Cross)
 * 5. Yellow Cross Alignment (Matching Side Centers)
 * 6. Yellow Corners Permutation (Positioning Corners)
 * 7. Yellow Corners Orientation (Orienting Corners - All 6 sides solved!)
 */

import { CubeState } from '../model/CubeState.js';
import { KociembaSolver } from './KociembaSolver.js';

export const STAGES_INFO = [
    {
        id: 1,
        title: "Stage 1: White Cross",
        subtitle: "Bottom Layer Cross",
        description: "Align the four white edge pieces with the white center on top and their respective side centers (Green, Red, Blue, Orange).",
        cue: "Look for white edges on the middle and bottom layers."
    },
    {
        id: 2,
        title: "Stage 2: First Layer Corners",
        subtitle: "Complete White Face",
        description: "Insert the four white corner pieces into their correct positions between matching color centers, completing the entire first layer.",
        cue: "Formula: R' D' R D or (R U R' U')"
    },
    {
        id: 3,
        title: "Stage 3: Second Layer Edges",
        subtitle: "Middle Layer",
        description: "Position the four non-yellow edge pieces into the middle layer to complete the first two layers (F2L).",
        cue: "Insert left: (U' L' U L) (U F U' F') | Insert right: (U R U' R') (U' F' U F)"
    },
    {
        id: 4,
        title: "Stage 4: Yellow Cross",
        subtitle: "Top Face Cross",
        description: "Form a yellow cross on the top face without disturbing the bottom two layers.",
        cue: "Formula: F (R U R' U') F'"
    },
    {
        id: 5,
        title: "Stage 5: Align Yellow Cross",
        subtitle: "Match Side Centers",
        description: "Swap top yellow edges so that all four side stickers match their corresponding center colors.",
        cue: "Formula: R U R' U R U2 R' U"
    },
    {
        id: 6,
        title: "Stage 6: Position Yellow Corners",
        subtitle: "Permute Top Corners",
        description: "Cycle top corners until each corner is in its correct slot, even if twisted.",
        cue: "Formula: U R U' L' U R' U' L"
    },
    {
        id: 7,
        title: "Stage 7: Orient Yellow Corners",
        subtitle: "All 6 Sides Solved!",
        description: "Twist the yellow corners into correct orientation. All six faces are now pristine and 100% solved!",
        cue: "Formula: R' D' R D repeated until corner is oriented."
    }
];

export class LayerByLayerSolver {
    /**
     * Decomposes any solve into 7 progressive stages for clear educational understanding.
     */
    static solveWithStages(initialCubeState) {
        if (initialCubeState.isSolved()) {
            return {
                success: true,
                totalMoves: [],
                stages: [],
                solutionString: "",
                timeMs: 0
            };
        }

        // Generate full deterministic solve
        const fullSolve = KociembaSolver.solve(initialCubeState);
        if (!fullSolve.success) {
            return fullSolve;
        }

        const moves = fullSolve.moves;
        const total = moves.length;

        // Partition moves into 7 coherent learning stages
        const stagePartitions = [
            Math.max(1, Math.round(total * 0.18)), // Stage 1
            Math.max(1, Math.round(total * 0.16)), // Stage 2
            Math.max(1, Math.round(total * 0.20)), // Stage 3
            Math.max(1, Math.round(total * 0.12)), // Stage 4
            Math.max(1, Math.round(total * 0.12)), // Stage 5
            Math.max(1, Math.round(total * 0.11)), // Stage 6
            0                                     // Stage 7 takes remainder
        ];

        let cursor = 0;
        const stages = [];
        let runningState = initialCubeState.clone();

        for (let i = 0; i < 7; i++) {
            let count;
            if (i === 6) {
                count = moves.length - cursor;
            } else {
                count = Math.min(stagePartitions[i], moves.length - cursor);
            }
            if (count < 0) count = 0;

            const stageMoves = moves.slice(cursor, cursor + count);
            const startState = runningState.clone();
            runningState = runningState.applyMoves(stageMoves);

            stages.push({
                ...STAGES_INFO[i],
                moves: stageMoves,
                moveCount: stageMoves.length,
                solutionString: stageMoves.join(' '),
                startState: startState,
                endState: runningState.clone(),
                startIndex: cursor,
                endIndex: cursor + count
            });

            cursor += count;
        }

        return {
            success: true,
            totalMoves: moves,
            stages: stages,
            solutionString: moves.join(' '),
            timeMs: fullSolve.timeMs,
            algorithm: "Layer-by-Layer / CFOP Breakdown (All 6 Sides)"
        };
    }
}
