import type { MeasurementUnit, WeightUnit, StoneBlock } from '../types/grn';

/**
 * Calculates estimated rectangular volume in Cubic Feet (CFT)
 * Formula:
 * - Inches: (L * W * H) / 1728
 * - Feet: L * W * H
 * - Centimeters: (L * W * H) / 28316.85
 * - Meters: (L * W * H) * 35.3147
 */
export function calculateBlockVolume(
  length: number,
  width: number,
  height: number,
  unit: MeasurementUnit
): { volumeCft: number; formulaLabel: string } {
  if (!length || !width || !height || length <= 0 || width <= 0 || height <= 0) {
    return { volumeCft: 0, formulaLabel: 'नाप दर्ज करें' };
  }

  let volumeCft = 0;
  let formulaLabel = '';

  switch (unit) {
    case 'इंच (Inches)': {
      // 1 cubic foot = 12 x 12 x 12 = 1728 cubic inches
      volumeCft = (length * width * height) / 1728;
      formulaLabel = `(${length} × ${width} × ${height}) ÷ 1728 = ${volumeCft.toFixed(2)} घन फीट (CFT)`;
      break;
    }
    case 'फीट (Feet)': {
      volumeCft = length * width * height;
      formulaLabel = `${length} × ${width} × ${height} = ${volumeCft.toFixed(2)} घन फीट (CFT)`;
      break;
    }
    case 'सेमी (cm)': {
      // 1 cubic foot = 28316.846592 cm³
      volumeCft = (length * width * height) / 28316.85;
      formulaLabel = `(${length} × ${width} × ${height}) सेमी³ ÷ 28317 = ${volumeCft.toFixed(2)} घन फीट (CFT)`;
      break;
    }
    case 'मीटर (m)': {
      // 1 cubic meter = 35.3147 cu ft
      volumeCft = length * width * height * 35.3147;
      formulaLabel = `(${length} × ${width} × ${height}) मी³ × 35.31 = ${volumeCft.toFixed(2)} घन फीट (CFT)`;
      break;
    }
  }

  return {
    volumeCft: Number(volumeCft.toFixed(2)),
    formulaLabel
  };
}

/**
 * Validates weighbridge tare and gross weights
 */
export function calculateNetWeight(
  grossWeight: number,
  tareWeight: number,
  unit: WeightUnit
): { netWeight: number; error: string | null } {
  if (grossWeight <= 0 && tareWeight <= 0) {
    return { netWeight: 0, error: null };
  }

  if (grossWeight < 0) {
    return { netWeight: 0, error: 'सकल वजन शून्य से कम नहीं हो सकता।' };
  }

  if (tareWeight < 0) {
    return { netWeight: 0, error: 'खाली गाड़ी वजन शून्य से कम नहीं हो सकता।' };
  }

  if (tareWeight > grossWeight) {
    return {
      netWeight: 0,
      error: 'खाली गाड़ी का वजन (Tare) सकल वजन (Gross) से अधिक नहीं हो सकता!'
    };
  }

  const net = Number((grossWeight - tareWeight).toFixed(3));
  return { netWeight: net, error: null };
}

/**
 * Calculates totals for a list of blocks
 */
export function calculateGrnTotals(blocks: StoneBlock[]) {
  const totalBlocks = blocks.length;
  const totalPieces = blocks.reduce((acc, b) => acc + (Number(b.pieces) || 1), 0);
  const totalVolumeEstimateCft = Number(
    blocks.reduce((acc, b) => acc + (Number(b.estimatedVolume) || 0), 0).toFixed(2)
  );

  return {
    totalBlocks,
    totalPieces,
    totalVolumeEstimateCft
  };
}
