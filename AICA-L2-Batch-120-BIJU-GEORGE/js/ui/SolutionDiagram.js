/**
 * SolutionDiagram.js - Front-Face Reference Isometric Solution Diagram & Printable Sheet
 * Generates intuitive Rubik's cube diagrams matching the user's reference design:
 * - Undistorted 3x3 Front Face facing the user as primary reference with actual real-time colors.
 * - Top Face (3x3) and Right Face (3x3) in oblique/isometric perspective.
 * - Glowing directional Neon Fuchsia arrows (#FF007F) indicating exact layer turn and direction,
 *   strictly avoiding any of the cube's 6 facelet colors for 100% visibility.
 * - Prominent, fully visible Back-layer turn indicators for B, B', B2.
 * - Explicit plain-English instructions (Clockwise / Anticlockwise, Left / Right / Up / Down).
 * - Dedicated Front Face combination verification swatches.
 * - Complete Printable Solution Sheet generator with printer-optimized layout.
 */

import { CubeColor, CubeState } from '../model/CubeState.js';

export const ARROW_COLOR = '#FF007F'; // Electric Neon Fuchsia (not White, Yellow, Green, Blue, Red, or Orange)

export const MOVE_DIRECTIONS = {
    "U":  { face: 'U', type: 'row', layer: 0, dir: 'left', mult: 'X1', desc: "Turn Top layer to the LEFT (Clockwise)" },
    "U'": { face: 'U', type: 'row', layer: 0, dir: 'right', mult: 'X1', desc: "Turn Top layer to the RIGHT (Anticlockwise)" },
    "U2": { face: 'U', type: 'row', layer: 0, dir: 'left', mult: 'X2', desc: "Turn Top layer to the LEFT 180° (Half turn)" },

    "D":  { face: 'D', type: 'row', layer: 2, dir: 'right', mult: 'X1', desc: "Turn Bottom layer to the RIGHT (Clockwise)" },
    "D'": { face: 'D', type: 'row', layer: 2, dir: 'left', mult: 'X1', desc: "Turn Bottom layer to the LEFT (Anticlockwise)" },
    "D2": { face: 'D', type: 'row', layer: 2, dir: 'right', mult: 'X2', desc: "Turn Bottom layer to the RIGHT 180° (Half turn)" },

    "R":  { face: 'R', type: 'col', layer: 2, dir: 'up', mult: 'X1', desc: "Turn Right layer UP away from you (Clockwise)" },
    "R'": { face: 'R', type: 'col', layer: 2, dir: 'down', mult: 'X1', desc: "Turn Right layer DOWN towards you (Anticlockwise)" },
    "R2": { face: 'R', type: 'col', layer: 2, dir: 'up', mult: 'X2', desc: "Turn Right layer UP 180° (Half turn)" },

    "L":  { face: 'L', type: 'col', layer: 0, dir: 'down', mult: 'X1', desc: "Turn Left layer DOWN towards you (Clockwise)" },
    "L'": { face: 'L', type: 'col', layer: 0, dir: 'up', mult: 'X1', desc: "Turn Left layer UP away from you (Anticlockwise)" },
    "L2": { face: 'L', type: 'col', layer: 0, dir: 'down', mult: 'X2', desc: "Turn Left layer DOWN 180° (Half turn)" },

    "F":  { face: 'F', type: 'arc', dir: 'cw', mult: 'X1', desc: "Rotate Front face CLOCKWISE (Top moves to Right)" },
    "F'": { face: 'F', type: 'arc', dir: 'ccw', mult: 'X1', desc: "Rotate Front face ANTICLOCKWISE (Top moves to Left)" },
    "F2": { face: 'F', type: 'arc', dir: 'cw', mult: 'X2', desc: "Rotate Front face 180° (Two quarter turns)" },

    "B":  { face: 'B', type: 'back_arc', dir: 'left', mult: 'X1', desc: "Turn Back layer to the LEFT (Clockwise when looking at back)" },
    "B'": { face: 'B', type: 'back_arc', dir: 'right', mult: 'X1', desc: "Turn Back layer to the RIGHT (Anticlockwise when looking at back)" },
    "B2": { face: 'B', type: 'back_arc', dir: 'left', mult: 'X2', desc: "Turn Back layer to the LEFT 180° (Half turn)" },

    "M":  { face: 'M', type: 'col', layer: 1, dir: 'down', mult: 'X1', desc: "Turn Middle layer DOWN towards you" },
    "M'": { face: 'M', type: 'col', layer: 1, dir: 'up', mult: 'X1', desc: "Turn Middle layer UP away from you" }
};

export class SolutionDiagram {
    /**
     * Renders an SVG string of the cube matching the user's diagram:
     * Front face is facing the user, with Top and Right faces visible.
     */
    static renderStepSvg(cubeState, moveNotation, width = 200, height = 215, options = {}) {
        const isCleanPrint = options.cleanPrint || false;
        const showMultiplier = options.showMultiplier !== undefined ? options.showMultiplier : true;
        const uniqueId = `glow-${Math.floor(Math.random() * 1000000)}`;

        const s = 106;       // Front face size
        const t = s / 3;     // Tile size
        const dx = 30;       // Top/Right projection X
        const dy = 22;       // Top/Right projection Y
        const ox = 31;       // Origin X (centers cube in 200px width: 31 + 106 + 30 = 167, leaving 33px right margin)
        const oy = 52;       // Origin Y (leaves 28px clearance above for Back banner, and 24px below for Multiplier pill)

        const frontStickers = cubeState.getFaceStickers('F');
        const topStickers = cubeState.getFaceStickers('U');
        const rightStickers = cubeState.getFaceStickers('R');

        const isSolvedState = !moveNotation || moveNotation === 'SOLVED';
        const moveInfo = isSolvedState ? { mult: '✓ SOLVED', desc: 'All 6 sides solved' } : (MOVE_DIRECTIONS[moveNotation] || { mult: 'X1', desc: `Apply ${moveNotation}` });

        const bgFill = isCleanPrint ? '#ffffff' : '#090d16';
        const gridColor = isCleanPrint ? '#334155' : '#38bdf8';
        const arrowColor = ARROW_COLOR;

        let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 215" width="${width}" height="${height}" style="display: block; max-width: 100%; max-height: 100%;">
        <defs>
            <filter id="${uniqueId}" x="-25%" y="-25%" width="150%" height="150%">
                <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="${arrowColor}" flood-opacity="0.9"/>
            </filter>
        </defs>
        <rect width="200" height="215" fill="${bgFill}" stroke="${isCleanPrint ? '#cbd5e1' : 'rgba(56, 189, 248, 0.25)'}" stroke-width="1" rx="12"/>
        `;

        // 1. Draw Top Face (U) - 3 rows x 3 cols
        for (let r = 0; r < 3; r++) {
            for (let c = 0; c < 3; c++) {
                const uIdx = r * 3 + c;
                const colLetter = topStickers[uIdx];
                const colHex = CubeColor[colLetter]?.hex || '#FFFFFF';

                // r=0 is Back, r=2 is Front (bordering F)
                const rowOffsetBack = 2 - r;
                const x0 = ox + c * t + rowOffsetBack * (dx / 3);
                const y0 = oy - rowOffsetBack * (dy / 3);
                const x1 = x0 + t;
                const y1 = y0;
                const x2 = x1 + (dx / 3);
                const y2 = y1 - (dy / 3);
                const x3 = x0 + (dx / 3);
                const y3 = y0 - (dy / 3);

                svg += `<polygon points="${x0},${y0} ${x1},${y1} ${x2},${y2} ${x3},${y3}" fill="${colHex}" stroke="${gridColor}" stroke-width="1.2"/>\n`;
            }
        }

        // 2. Draw Right Face (R) - 3 rows x 3 cols
        for (let r = 0; r < 3; r++) {
            for (let c = 0; c < 3; c++) {
                const rIdx = r * 3 + c;
                const colLetter = rightStickers[rIdx];
                const colHex = CubeColor[colLetter]?.hex || '#DC2626';

                const colOffset = c;
                const x0 = ox + s + colOffset * (dx / 3);
                const y0 = oy + r * t - colOffset * (dy / 3);
                const x1 = x0 + (dx / 3);
                const y1 = y0 - (dy / 3);
                const x2 = x1;
                const y2 = y1 + t;
                const x3 = x0;
                const y3 = y0 + t;

                svg += `<polygon points="${x0},${y0} ${x1},${y1} ${x2},${y2} ${x3},${y3}" fill="${colHex}" stroke="${gridColor}" stroke-width="1.2"/>\n`;
            }
        }

        // 3. Draw Front Face (F) - 3 rows x 3 cols (Primary Orthogonal Reference)
        for (let r = 0; r < 3; r++) {
            for (let c = 0; c < 3; c++) {
                const fIdx = r * 3 + c;
                const colLetter = frontStickers[fIdx];
                const colHex = CubeColor[colLetter]?.hex || '#16A34A';
                const isCenter = (r === 1 && c === 1);

                const x = ox + c * t;
                const y = oy + r * t;

                svg += `<rect x="${x}" y="${y}" width="${t}" height="${t}" fill="${colHex}" stroke="${gridColor}" stroke-width="1.2"/>\n`;

                const textColor = (colHex === '#FFFFFF' || colHex === '#FACC15') ? '#18181b' : '#ffffff';
                if (isCenter) {
                    svg += `<text x="${x + t / 2}" y="${y + t / 2 + 5}" font-family="system-ui, sans-serif" font-size="14" font-weight="900" fill="${textColor}" text-anchor="middle">F</text>\n`;
                } else if (options.showStickerLetters) {
                    svg += `<text x="${x + t / 2}" y="${y + t / 2 + 4}" font-family="system-ui, sans-serif" font-size="10" font-weight="700" fill="${textColor}" opacity="0.8" text-anchor="middle">${colLetter}</text>\n`;
                }
            }
        }

        // Outer Outlines for crisp definition
        svg += `<rect x="${ox}" y="${oy}" width="${s}" height="${s}" fill="none" stroke="${gridColor}" stroke-width="2.5" rx="2"/>\n`;
        svg += `<polygon points="${ox + s},${oy} ${ox + s + dx},${oy - dy} ${ox + s + dx},${oy + s - dy} ${ox + s},${oy + s}" fill="none" stroke="${gridColor}" stroke-width="2.5"/>\n`;
        svg += `<polygon points="${ox},${oy} ${ox + dx},${oy - dy} ${ox + s + dx},${oy - dy} ${ox + s},${oy}" fill="none" stroke="${gridColor}" stroke-width="2.5"/>\n`;

        // 4. Directional Neon Fuchsia Arrow (or Solved Star)
        if (!isSolvedState) {
            svg += SolutionDiagram.renderArrowSvg(moveNotation, ox, oy, s, t, dx, dy, arrowColor, uniqueId, isCleanPrint);
        } else {
            // Solved check badge in center
            svg += `<circle cx="${ox + s / 2}" cy="${oy + s / 2}" r="22" fill="#10b981" filter="url(#${uniqueId})"/>\n`;
            svg += `<path d="M ${ox + s / 2 - 8} ${oy + s / 2} L ${ox + s / 2 - 2} ${oy + s / 2 + 7} L ${ox + s / 2 + 10} ${oy + s / 2 - 7}" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>\n`;
        }

        // 5. Multiplier Badge (X1, X2, etc.) - Fully contained inside SVG with zero overflow
        if (showMultiplier) {
            const mult = moveInfo.mult || 'X1';
            let badgeBg = 'rgba(56, 189, 248, 0.15)';
            let badgeBorder = '#38bdf8';
            let badgeText = '#38bdf8';
            let label = `${mult} TURN`;

            if (mult === 'X2') {
                badgeBg = 'rgba(249, 115, 22, 0.16)';
                badgeBorder = '#f97316';
                badgeText = '#f97316';
                label = 'X2 (180° TURN)';
            } else if (isSolvedState) {
                badgeBg = 'rgba(16, 185, 129, 0.2)';
                badgeBorder = '#10b981';
                badgeText = '#34d399';
                label = '✓ SOLVED';
            }

            if (isCleanPrint) {
                if (mult === 'X2') {
                    badgeBg = '#fff7ed';
                    badgeBorder = '#ea580c';
                    badgeText = '#c2410c';
                } else if (isSolvedState) {
                    badgeBg = '#f0fdf4';
                    badgeBorder = '#16a34a';
                    badgeText = '#15803d';
                } else {
                    badgeBg = '#f0f9ff';
                    badgeBorder = '#0284c7';
                    badgeText = '#0369a1';
                }
            }

            const badgeW = mult === 'X2' ? 116 : (isSolvedState ? 96 : 76);
            const badgeH = 25;
            const badgeX = (200 - badgeW) / 2;
            const badgeY = 174;

            svg += `
            <g class="svg-multiplier-badge">
                <rect x="${badgeX}" y="${badgeY}" width="${badgeW}" height="${badgeH}" rx="8" fill="${badgeBg}" stroke="${badgeBorder}" stroke-width="1.5"/>
                <text x="100" y="${badgeY + 17}" font-family="system-ui, sans-serif" font-size="${mult === 'X2' ? 12 : 13.5}" font-weight="900" fill="${badgeText}" text-anchor="middle" letter-spacing="0.6">${label}</text>
            </g>
            `;
        }

        svg += `</svg>`;
        return svg;
    }

    static renderArrowSvg(moveNotation, ox, oy, s, t, dx, dy, color, filterId, isCleanPrint = false) {
        if (!moveNotation) return '';

        const filterAttr = `filter="url(#${filterId})"`;
        const outlineWidth = 8.5;
        const mainWidth = 5.5;
        let svg = '';

        // Helper to draw bold high-contrast arrow with black shadow outline
        const drawArrowLine = (x1, y1, x2, y2, points) => {
            return `
            <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#000000" stroke-width="${outlineWidth}" stroke-linecap="round"/>
            <polygon points="${points}" fill="#000000" stroke="#000000" stroke-width="2"/>
            <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${mainWidth}" stroke-linecap="round" ${filterAttr}/>
            <polygon points="${points}" fill="${color}" stroke="${color}" stroke-width="1" ${filterAttr}/>
            `;
        };

        if (moveNotation === 'R' || moveNotation === 'R2') {
            const ax = ox + 2.5 * t;
            const yStart = oy + s - 10;
            const yEnd = oy + 12;
            const pts = `${ax},${yEnd - 14} ${ax - 8},${yEnd + 2} ${ax + 8},${yEnd + 2}`;
            svg += drawArrowLine(ax, yStart, ax, yEnd, pts);
        } else if (moveNotation === "R'") {
            const ax = ox + 2.5 * t;
            const yStart = oy + 12;
            const yEnd = oy + s - 10;
            const pts = `${ax},${yEnd + 14} ${ax - 8},${yEnd - 2} ${ax + 8},${yEnd - 2}`;
            svg += drawArrowLine(ax, yStart, ax, yEnd, pts);
        } else if (moveNotation === 'L' || moveNotation === 'L2') {
            const ax = ox + 0.5 * t;
            const yStart = oy + 12;
            const yEnd = oy + s - 10;
            const pts = `${ax},${yEnd + 14} ${ax - 8},${yEnd - 2} ${ax + 8},${yEnd - 2}`;
            svg += drawArrowLine(ax, yStart, ax, yEnd, pts);
        } else if (moveNotation === "L'") {
            const ax = ox + 0.5 * t;
            const yStart = oy + s - 10;
            const yEnd = oy + 12;
            const pts = `${ax},${yEnd - 14} ${ax - 8},${yEnd + 2} ${ax + 8},${yEnd + 2}`;
            svg += drawArrowLine(ax, yStart, ax, yEnd, pts);
        } else if (moveNotation === 'U' || moveNotation === 'U2') {
            const ay = oy + 0.5 * t;
            const xStart = ox + s - 10;
            const xEnd = ox + 12;
            const pts = `${xEnd - 14},${ay} ${xEnd + 2},${ay - 8} ${xEnd + 2},${ay + 8}`;
            svg += drawArrowLine(xStart, ay, xEnd, ay, pts);
        } else if (moveNotation === "U'") {
            const ay = oy + 0.5 * t;
            const xStart = ox + 12;
            const xEnd = ox + s - 10;
            const pts = `${xEnd + 14},${ay} ${xEnd - 2},${ay - 8} ${xEnd - 2},${ay + 8}`;
            svg += drawArrowLine(xStart, ay, xEnd, ay, pts);
        } else if (moveNotation === 'D' || moveNotation === 'D2') {
            const ay = oy + 2.5 * t;
            const xStart = ox + 12;
            const xEnd = ox + s - 10;
            const pts = `${xEnd + 14},${ay} ${xEnd - 2},${ay - 8} ${xEnd - 2},${ay + 8}`;
            svg += drawArrowLine(xStart, ay, xEnd, ay, pts);
        } else if (moveNotation === "D'") {
            const ay = oy + 2.5 * t;
            const xStart = ox + s - 10;
            const xEnd = ox + 12;
            const pts = `${xEnd - 14},${ay} ${xEnd + 2},${ay - 8} ${xEnd + 2},${ay + 8}`;
            svg += drawArrowLine(xStart, ay, xEnd, ay, pts);
        } else if (moveNotation === 'F' || moveNotation === 'F2') {
            const cx = ox + s / 2;
            const cy = oy + s / 2;
            const r = s * 0.36;
            const pathData = `M ${cx - r * 0.65} ${cy + r * 0.65} A ${r} ${r} 0 1 1 ${cx + r * 0.72} ${cy + r * 0.65}`;
            const pts = `${cx + r * 0.72 + 6},${cy + r * 0.72 + 10} ${cx + r * 0.72 - 8},${cy + r * 0.72 - 2} ${cx + r * 0.72 + 8},${cy + r * 0.72 - 8}`;
            svg += `<path d="${pathData}" fill="none" stroke="#000000" stroke-width="${outlineWidth}" stroke-linecap="round"/>\n`;
            svg += `<polygon points="${pts}" fill="#000000" stroke="#000000" stroke-width="2"/>\n`;
            svg += `<path d="${pathData}" fill="none" stroke="${color}" stroke-width="${mainWidth}" stroke-linecap="round" ${filterAttr}/>\n`;
            svg += `<polygon points="${pts}" fill="${color}" stroke="${color}" stroke-width="1" ${filterAttr}/>\n`;
        } else if (moveNotation === "F'") {
            const cx = ox + s / 2;
            const cy = oy + s / 2;
            const r = s * 0.36;
            const pathData = `M ${cx + r * 0.65} ${cy + r * 0.65} A ${r} ${r} 0 1 0 ${cx - r * 0.72} ${cy + r * 0.65}`;
            const pts = `${cx - r * 0.72 - 6},${cy + r * 0.72 + 10} ${cx - r * 0.72 + 8},${cy + r * 0.72 - 2} ${cx - r * 0.72 - 8},${cy + r * 0.72 - 8}`;
            svg += `<path d="${pathData}" fill="none" stroke="#000000" stroke-width="${outlineWidth}" stroke-linecap="round"/>\n`;
            svg += `<polygon points="${pts}" fill="#000000" stroke="#000000" stroke-width="2"/>\n`;
            svg += `<path d="${pathData}" fill="none" stroke="${color}" stroke-width="${mainWidth}" stroke-linecap="round" ${filterAttr}/>\n`;
            svg += `<polygon points="${pts}" fill="${color}" stroke="${color}" stroke-width="1" ${filterAttr}/>\n`;
        } else if (moveNotation === 'B' || moveNotation === 'B2') {
            // Back face turn (Clockwise when looking at back = Top moves to LEFT from front view)
            // Draw a prominent glowing arched arrow along the top banner above the cube
            const bannerX = ox + 4;
            const bannerY = 2;
            const bannerW = s + dx - 8;
            const bannerH = 24;
            const bannerFill = isCleanPrint ? '#f8fafc' : 'rgba(15, 23, 42, 0.9)';
            const bannerStroke = isCleanPrint ? '#64748b' : '#38bdf8';
            const bannerTextColor = isCleanPrint ? '#0f172a' : '#38bdf8';
            const labelText = moveNotation === 'B2' ? 'BACK LAYER: 180° TURN' : 'BACK LAYER: TURN LEFT';

            const xStart = ox + s + dx - 18; // Back-Right
            const xEnd = ox + 18;            // Back-Left
            const arrowY = 10;
            const pts = `${xEnd - 8},${arrowY} ${xEnd + 2},${arrowY - 5} ${xEnd + 2},${arrowY + 5}`;

            svg += `<g class="back-arrow-group">`;
            svg += `<rect x="${bannerX}" y="${bannerY}" width="${bannerW}" height="${bannerH}" fill="${bannerFill}" stroke="${bannerStroke}" stroke-width="1.2" rx="6"/>\n`;
            svg += `<text x="${bannerX + bannerW / 2}" y="${bannerY + 19}" font-family="system-ui, sans-serif" font-size="8.5" font-weight="800" fill="${bannerTextColor}" text-anchor="middle" letter-spacing="0.3">${labelText}</text>\n`;
            svg += drawArrowLine(xStart, arrowY, xEnd, arrowY, pts);
            svg += `</g>`;
        } else if (moveNotation === "B'") {
            // Back face turn (Anticlockwise when looking at back = Top moves to RIGHT from front view)
            const bannerX = ox + 4;
            const bannerY = 2;
            const bannerW = s + dx - 8;
            const bannerH = 24;
            const bannerFill = isCleanPrint ? '#f8fafc' : 'rgba(15, 23, 42, 0.9)';
            const bannerStroke = isCleanPrint ? '#64748b' : '#38bdf8';
            const bannerTextColor = isCleanPrint ? '#0f172a' : '#38bdf8';

            const xStart = ox + 18;            // Back-Left
            const xEnd = ox + s + dx - 18;     // Back-Right
            const arrowY = 10;
            const pts = `${xEnd + 8},${arrowY} ${xEnd - 2},${arrowY - 5} ${xEnd - 2},${arrowY + 5}`;

            svg += `<g class="back-arrow-group">`;
            svg += `<rect x="${bannerX}" y="${bannerY}" width="${bannerW}" height="${bannerH}" fill="${bannerFill}" stroke="${bannerStroke}" stroke-width="1.2" rx="6"/>\n`;
            svg += `<text x="${bannerX + bannerW / 2}" y="${bannerY + 19}" font-family="system-ui, sans-serif" font-size="8.5" font-weight="800" fill="${bannerTextColor}" text-anchor="middle" letter-spacing="0.3">BACK LAYER: TURN RIGHT</text>\n`;
            svg += drawArrowLine(xStart, arrowY, xEnd, arrowY, pts);
            svg += `</g>`;
        } else if (moveNotation === 'M' || moveNotation === "M'") {
            const ax = ox + 1.5 * t;
            const isDown = moveNotation === 'M';
            const yStart = isDown ? oy + 12 : oy + s - 10;
            const yEnd = isDown ? oy + s - 10 : oy + 12;
            const pts = isDown ?
                `${ax},${yEnd + 14} ${ax - 8},${yEnd - 2} ${ax + 8},${yEnd - 2}` :
                `${ax},${yEnd - 14} ${ax - 8},${yEnd + 2} ${ax + 8},${yEnd + 2}`;
            svg += drawArrowLine(ax, yStart, ax, yEnd, pts);
        }

        return svg;
    }

    /**
     * Renders a 3x3 Front Face Reference swatch grid SVG so the user can verify the exact
     * 9-color combination facing them on their physical cube before performing the turn.
     */
    static renderFrontFaceGridSvg(cubeState, width = 110, height = 110, options = {}) {
        const isCleanPrint = options.cleanPrint || false;
        const frontStickers = cubeState.getFaceStickers('F');
        const pad = 6;
        const gridSize = width - pad * 2;
        const t = gridSize / 3;

        const bgFill = isCleanPrint ? '#ffffff' : '#0f172a';
        const borderColor = isCleanPrint ? '#64748b' : '#38bdf8';

        let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">
        <rect width="${width}" height="${height}" fill="${bgFill}" rx="8"/>
        `;

        const isSmall = t < 22;
        const centerFontSize = isSmall ? Math.max(8, Math.round(t * 0.6)) : 13;
        const stickerFontSize = isSmall ? Math.max(7, Math.round(t * 0.52)) : 10;
        const yOffsetCenter = isSmall ? Math.round(centerFontSize * 0.35) : 5;
        const yOffsetSticker = isSmall ? Math.round(stickerFontSize * 0.35) : 4;

        for (let r = 0; r < 3; r++) {
            for (let c = 0; c < 3; c++) {
                const idx = r * 3 + c;
                const colLetter = frontStickers[idx];
                const colHex = CubeColor[colLetter]?.hex || '#16A34A';
                const isCenter = (r === 1 && c === 1);

                const x = pad + c * t;
                const y = pad + r * t;

                svg += `<rect x="${x}" y="${y}" width="${t}" height="${t}" fill="${colHex}" stroke="${borderColor}" stroke-width="1.2" rx="2"/>\n`;

                const textColor = (colHex === '#FFFFFF' || colHex === '#FACC15') ? '#18181b' : '#ffffff';
                if (isCenter) {
                    svg += `<text x="${x + t / 2}" y="${y + t / 2 + yOffsetCenter}" font-family="system-ui, sans-serif" font-size="${centerFontSize}" font-weight="900" fill="${textColor}" text-anchor="middle">F</text>\n`;
                } else {
                    svg += `<text x="${x + t / 2}" y="${y + t / 2 + yOffsetSticker}" font-family="system-ui, sans-serif" font-size="${stickerFontSize}" font-weight="700" fill="${textColor}" text-anchor="middle">${colLetter}</text>\n`;
                }
            }
        }

        svg += `<rect x="${pad}" y="${pad}" width="${gridSize}" height="${gridSize}" fill="none" stroke="${borderColor}" stroke-width="2" rx="3"/>\n`;
        svg += `</svg>`;
        return svg;
    }

    /**
     * Generates a complete, beautiful HTML printable sheet containing the full step-by-step
     * diagrams for all moves in the solution (matching the user's reference diagram).
     */
    static generatePrintableSheetHtml(initialState, moves, algorithmName = "Optimal Kociemba") {
        let current = initialState.clone();
        const stepsData = [];

        for (let i = 0; i < moves.length; i++) {
            const mv = moves[i];
            const stateBeforeMove = current.clone();
            current = current.applyMove(mv);
            const moveInfo = MOVE_DIRECTIONS[mv] || { mult: 'X1', desc: `Apply move ${mv}` };

            stepsData.push({
                stepIndex: i + 1,
                move: mv,
                mult: moveInfo.mult || 'X1',
                desc: moveInfo.desc || `Turn ${mv}`,
                state: stateBeforeMove,
                nextState: current.clone()
            });
        }

        const cardsHtml = stepsData.map(st => {
            const svgDiagram = SolutionDiagram.renderStepSvg(st.state, st.move, 200, 215, { cleanPrint: false, showStickerLetters: true, showMultiplier: true });
            const svgFrontRef = SolutionDiagram.renderFrontFaceGridSvg(st.state, 84, 84, { cleanPrint: false });

            return `
            <div class="print-step-card">
                <div class="print-step-header">
                    <span class="step-num">Step ${st.stepIndex} / ${moves.length}</span>
                    <span class="step-badge">${st.move}</span>
                    <label class="step-checkbox"><input type="checkbox"> Done</label>
                </div>
                <div class="print-step-visuals">
                    <div class="print-step-svg-wrap">
                        ${svgDiagram}
                    </div>
                    <div class="print-front-ref-wrap">
                        <div class="front-ref-tag">Front Reference</div>
                        ${svgFrontRef}
                        <div class="front-ref-sub">Face: <strong>Green Center</strong></div>
                    </div>
                </div>
                <div class="print-step-desc">${st.desc}</div>
                <div class="print-step-cue">Hold cube with Front face colors matching the reference swatch above, then execute the neon fuchsia turn arrow.</div>
            </div>
            `;
        }).join('');

        // Final Solved Card
        const finalSolvedSvg = SolutionDiagram.renderStepSvg(current, 'SOLVED', 200, 215, { cleanPrint: false, showMultiplier: true });
        const finalFrontRef = SolutionDiagram.renderFrontFaceGridSvg(current, 84, 84, { cleanPrint: false });

        const solvedCardHtml = `
        <div class="print-step-card print-solved-card">
            <div class="print-step-header">
                <span class="step-num">🎉 Final Goal</span>
                <span class="step-badge solved-badge">SOLVED</span>
            </div>
            <div class="print-step-visuals">
                <div class="print-step-svg-wrap">
                    ${finalSolvedSvg}
                </div>
                <div class="print-front-ref-wrap">
                    <div class="front-ref-tag">Solved Front</div>
                    ${finalFrontRef}
                    <div class="front-ref-sub">All 9 Green</div>
                </div>
            </div>
            <div class="print-step-desc" style="color: #10b981; font-weight: 800;">All 6 Sides Complete!</div>
            <div class="print-step-cue">White, Yellow, Green, Blue, Red, Orange faces are completely in pristine solved state!</div>
        </div>
        `;

        return `
        <div class="printable-solution-container">
            <div class="print-toolbar no-print">
                <div class="print-info">
                    <h2>📄 Complete Rubik's Cube Solution Guide</h2>
                    <p>Total Moves: <strong>${moves.length}</strong> • Algorithm: <strong>${algorithmName}</strong></p>
                    <p class="text-xs text-slate-400">Reference: Always hold the cube with <strong>Front (Green Center)</strong> facing you and <strong>Top (White Center)</strong> facing up.</p>
                </div>
                <div class="print-btns">
                    <button id="btn-trigger-print" class="btn-action-primary">🖨️ Print / Save as PDF</button>
                    <button id="btn-close-print-view" class="btn-action-secondary">✕ Close Guide</button>
                </div>
            </div>

            <div class="print-steps-grid">
                ${cardsHtml}
                ${solvedCardHtml}
            </div>

            <div class="print-footer">
                <div>🎉 All 6 Sides (White, Yellow, Green, Blue, Red, Orange) Solved!</div>
                <div class="text-xs">Generated by CubeSolver 3D PWA • Front-Face Reference System</div>
            </div>
        </div>
        `;
    }
}
