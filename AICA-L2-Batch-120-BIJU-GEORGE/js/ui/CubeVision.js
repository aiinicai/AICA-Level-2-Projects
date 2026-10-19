/**
 * CubeVision.js - Intelligent Computer Vision Color Classifier for Rubik's Cube
 *
 * Engineered specifically for challenging laptop webcams, low resolution (480p/720p),
 * variable indoor lighting, and glossy sticker reflections (laptop screen glare).
 *
 * Core Features:
 * 1. Trimmed-Median Specular Glint Filtering (discards screen reflections & shadows)
 * 2. Hybrid HSV Hue-Angle & CIELAB Delta-E Perceptual Classifier
 * 3. Channel Ratio Discrimination (Red vs Orange G/R ratio, Yellow vs White B ratio)
 * 4. Adaptive Ambient Lighting Modes: 'standard', 'low_light', 'anti_glare'
 */

export class CubeVision {
    // Reference colors in sRGB and CIELAB (D65 standard illuminant)
    static REF_COLORS = {
        'U': { name: 'White',  hex: '#FFFFFF', rgb: [255, 255, 255], L: 94.0, a: -0.5, b: 3.2 },
        'D': { name: 'Yellow', hex: '#FACC15', rgb: [250, 204, 21],  L: 88.0, a: -7.5, b: 86.0 },
        'F': { name: 'Green',  hex: '#16A34A', rgb: [22, 163, 74],   L: 55.0, a: -62.0, b: 38.0 },
        'B': { name: 'Blue',   hex: '#2563EB', rgb: [37, 99, 235],   L: 42.0, a: 16.0, b: -68.0 },
        'R': { name: 'Red',    hex: '#DC2626', rgb: [220, 38, 38],   L: 52.0, a: 66.0, b: 46.0 },
        'L': { name: 'Orange', hex: '#EA580C', rgb: [234, 88, 12],   L: 64.0, a: 45.0, b: 74.0 }
    };

    /**
     * Converts RGB (0-255) to HSV
     * H: 0-360, S: 0-1, V: 0-1
     */
    static rgbToHsv(r, g, b) {
        const rN = r / 255;
        const gN = g / 255;
        const bN = b / 255;
        const max = Math.max(rN, gN, bN);
        const min = Math.min(rN, gN, bN);
        const delta = max - min;
        const v = max;
        const s = max === 0 ? 0 : delta / max;

        let h = 0;
        if (delta !== 0) {
            if (max === rN) h = ((gN - bN) / delta) % 6;
            else if (max === gN) h = (bN - rN) / delta + 2;
            else h = (rN - gN) / delta + 4;
            h = Math.round(h * 60);
            if (h < 0) h += 360;
        }

        return [h, s, v];
    }

    /**
     * Converts sRGB (0-255) to CIELAB (L*, a*, b*)
     */
    static rgbToLab(r, g, b) {
        let rNorm = r / 255;
        let gNorm = g / 255;
        let bNorm = b / 255;

        // Gamma expansion (sRGB -> Linear RGB)
        rNorm = rNorm > 0.04045 ? Math.pow((rNorm + 0.055) / 1.055, 2.4) : rNorm / 12.92;
        gNorm = gNorm > 0.04045 ? Math.pow((gNorm + 0.055) / 1.055, 2.4) : gNorm / 12.92;
        bNorm = bNorm > 0.04045 ? Math.pow((bNorm + 0.055) / 1.055, 2.4) : bNorm / 12.92;

        rNorm *= 100;
        gNorm *= 100;
        bNorm *= 100;

        // D65 transformation matrix
        const x = rNorm * 0.4124564 + gNorm * 0.3575761 + bNorm * 0.1804375;
        const y = rNorm * 0.2126729 + gNorm * 0.7151522 + bNorm * 0.0721750;
        const z = rNorm * 0.0193339 + gNorm * 0.1191920 + bNorm * 0.9503041;

        // D65 reference white points
        const refX = 95.047;
        const refY = 100.000;
        const refZ = 108.883;

        let xR = x / refX;
        let yR = y / refY;
        let zR = z / refZ;

        const epsilon = 0.008856;
        const kappa = 903.3;
        const f = (t) => t > epsilon ? Math.cbrt(t) : (kappa * t + 16) / 116;

        const fx = f(xR);
        const fy = f(yR);
        const fz = f(zR);

        const labL = Math.max(0, 116 * fy - 16);
        const labA = 500 * (fx - fy);
        const labB = 200 * (fy - fz);

        return [labL, labA, labB];
    }

    /**
     * CIE76 Delta-E perceptual color difference
     */
    static deltaE(lab1, lab2) {
        const dL = lab1[0] - lab2[0];
        const da = lab1[1] - lab2[1];
        const db = lab1[2] - lab2[2];
        return Math.sqrt(dL * dL + da * da + db * db);
    }

    /**
     * Extracts pure sticker pigment by filtering out specular glare (screen reflections)
     * and edge shadows via a trimmed median filter on raw ImageData pixels.
     *
     * @param {Uint8ClampedArray} data - RGBA pixel array from sampled patch
     * @returns {[number, number, number]} Filtered [R, G, B]
     */
    static extractPurePigment(data) {
        const pixels = [];
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            // Perceived luminance
            const lum = 0.299 * r + 0.587 * g + 0.114 * b;
            pixels.push({ r, g, b, lum });
        }

        if (pixels.length === 0) return [128, 128, 128];

        // Sort by luminance
        pixels.sort((p1, p2) => p1.lum - p2.lum);

        // Discard top 25% brightest pixels (specular glare from laptop screen / light bulbs)
        // Discard bottom 15% darkest pixels (shadows / plastic seam dust)
        const startIndex = Math.floor(pixels.length * 0.15);
        const endIndex = Math.floor(pixels.length * 0.75);
        const corePixels = pixels.slice(startIndex, endIndex);

        if (corePixels.length === 0) return [pixels[0].r, pixels[0].g, pixels[0].b];

        let rSum = 0, gSum = 0, bSum = 0;
        for (const p of corePixels) {
            rSum += p.r;
            gSum += p.g;
            bSum += p.b;
        }

        return [
            Math.round(rSum / corePixels.length),
            Math.round(gSum / corePixels.length),
            Math.round(bSum / corePixels.length)
        ];
    }

    /**
     * Classifies an RGB color into one of the 6 Rubik's cube face letters ('U','R','F','D','L','B').
     * Uses a multi-stage decision tree combining HSV, channel ratio geometry, and CIELAB Delta-E.
     *
     * @param {number} r - Red (0-255)
     * @param {number} g - Green (0-255)
     * @param {number} b - Blue (0-255)
     * @param {string} [lightingMode='standard'] - 'standard', 'low_light', 'anti_glare'
     * @returns {string} Face letter: 'U' (White), 'D' (Yellow), 'F' (Green), 'B' (Blue), 'R' (Red), 'L' (Orange)
     */
    static classifySticker(r, g, b, lightingMode = 'standard') {
        const [h, s, v] = CubeVision.rgbToHsv(r, g, b);
        const maxVal = Math.max(r, g, b);
        const minVal = Math.min(r, g, b);

        // Dynamic saturation threshold for White depending on mode
        let whiteSatThreshold = 0.28;
        if (lightingMode === 'low_light') whiteSatThreshold = 0.35;
        if (lightingMode === 'anti_glare') whiteSatThreshold = 0.24;

        // Channel ratios
        const grRatio = r > 0 ? (g / r) : 0;
        const brRatio = r > 0 ? (b / r) : 0;
        const bgDiff = b - g;

        // ============================================================
        // 1. WHITE (U) DISCRIMINATION
        // White stickers consistently have low saturation and balanced RGB channels.
        // ============================================================
        const isRgbBalanced = Math.abs(r - g) < 45 && Math.abs(g - b) < 45 && Math.abs(r - b) < 55;
        if (s <= whiteSatThreshold && isRgbBalanced && v > 0.32) {
            return 'U'; // White
        }

        // ============================================================
        // 2. BLUE (B) DISCRIMINATION
        // Blue has Hue in [165, 265] and Blue channel is dominant over Red and Green.
        // ============================================================
        if (h >= 165 && h <= 265) {
            if (b > r * 1.15 && b >= g) {
                return 'B'; // Blue
            }
        }

        // ============================================================
        // 3. GREEN (F) DISCRIMINATION
        // Green has Hue in [72, 165] and Green channel is strictly dominant over Red and Blue.
        // ============================================================
        if (h >= 72 && h <= 165) {
            if (g > r && g > b) {
                return 'F'; // Green
            }
        }

        // ============================================================
        // 4. YELLOW (D) DISCRIMINATION
        // Yellow has high Red, high Green, low Blue. Hue in [42, 72].
        // ============================================================
        if (h >= 42 && h <= 72) {
            // Yellow has strong Green-to-Red ratio (grRatio > 0.65) and low Blue
            if (grRatio >= 0.65 && b < (r * 0.75)) {
                return 'D'; // Yellow
            }
        }

        // ============================================================
        // 5. ORANGE (L) VS RED (R) DISCRIMINATION
        // Both have high Red and low Blue.
        // The definitive distinction:
        // - Orange has substantial Green pigment (Hue 15-42°, G/R ratio > 0.30).
        // - Red has very low Green pigment (Hue < 14° or > 340°, G/R ratio < 0.28).
        // ============================================================
        if ((h >= 0 && h < 42) || h >= 335) {
            // Check for Yellow spillover into warm Hue:
            if (h >= 40 && grRatio > 0.75) {
                return 'D'; // Yellow
            }

            // Orange range:
            if (h >= 14 && h < 42) {
                if (grRatio >= 0.28) {
                    return 'L'; // Orange
                }
            }

            // Red range:
            if (h < 14 || h >= 335) {
                if (grRatio < 0.28) {
                    return 'R'; // Red
                }
                // If Hue is near 12-14 and green is moderate, classify as Orange
                if (grRatio >= 0.32) {
                    return 'L'; // Orange
                }
                return 'R'; // Red
            }
        }

        // ============================================================
        // 6. CIELAB DELTA-E FALLBACK (For edge cases / unusual sensors)
        // ============================================================
        const sampleLab = CubeVision.rgbToLab(r, g, b);
        let bestMatch = 'U';
        let minDelta = Infinity;

        for (const [letter, ref] of Object.entries(CubeVision.REF_COLORS)) {
            let dist = CubeVision.deltaE(sampleLab, [ref.L, ref.a, ref.b]);

            // Add domain-specific penalties
            if (letter === 'U' && s > 0.35) dist += 30; // Don't match White if saturated
            if (letter === 'D' && grRatio < 0.5) dist += 25; // Don't match Yellow without green
            if (letter === 'B' && b < g) dist += 30; // Don't match Blue if green is higher

            if (dist < minDelta) {
                minDelta = dist;
                bestMatch = letter;
            }
        }

        return bestMatch;
    }
}
