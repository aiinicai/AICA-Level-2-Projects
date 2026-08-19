import { DensityFactor, IngredientCategory, UnitType } from '../types';

// Standard conversion density defaults for common kitchen ingredients
export const DEFAULT_DENSITY_TABLE: DensityFactor[] = [
  { ingredientName: 'Wheat Flour / Atta', category: 'Flours & Atta', gramsPerMl: 0.53, gramsPerCup: 125, gramsPerTbsp: 7.8, gramsPerTsp: 2.6 },
  { ingredientName: 'All Purpose Flour / Maida', category: 'Flours & Atta', gramsPerMl: 0.53, gramsPerCup: 125, gramsPerTbsp: 7.8, gramsPerTsp: 2.6 },
  { ingredientName: 'Granulated Sugar', category: 'Spices & Seasoning', gramsPerMl: 0.85, gramsPerCup: 200, gramsPerTbsp: 12.5, gramsPerTsp: 4.2 },
  { ingredientName: 'Table Salt', category: 'Spices & Seasoning', gramsPerMl: 1.2, gramsPerCup: 280, gramsPerTbsp: 18, gramsPerTsp: 6 },
  { ingredientName: 'Basmati Rice', category: 'Grains & Pulses', gramsPerMl: 0.8, gramsPerCup: 180, gramsPerTbsp: 11.2, gramsPerTsp: 3.7 },
  { ingredientName: 'Cooking Oil / Mustard Oil', category: 'Oils & Ghee', gramsPerMl: 0.92, gramsPerCup: 220, gramsPerTbsp: 14, gramsPerTsp: 4.6 },
  { ingredientName: 'Desi Ghee / Butter', category: 'Oils & Ghee', gramsPerMl: 0.91, gramsPerCup: 225, gramsPerTbsp: 14, gramsPerTsp: 4.7 },
  { ingredientName: 'Milk / Fresh Milk', category: 'Dairy & Refrigerated', gramsPerMl: 1.03, gramsPerCup: 245, gramsPerTbsp: 15.4, gramsPerTsp: 5.1 },
  { ingredientName: 'Yogurt / Curd (Dahi)', category: 'Dairy & Refrigerated', gramsPerMl: 1.0, gramsPerCup: 240, gramsPerTbsp: 15, gramsPerTsp: 5 },
  { ingredientName: 'Honey', category: 'Condiments & Sauce', gramsPerMl: 1.42, gramsPerCup: 340, gramsPerTbsp: 21, gramsPerTsp: 7 },
  { ingredientName: 'Turmeric Powder / Haldi', category: 'Spices & Seasoning', gramsPerMl: 0.6, gramsPerCup: 140, gramsPerTbsp: 8.8, gramsPerTsp: 3 },
  { ingredientName: 'Red Chili Powder', category: 'Spices & Seasoning', gramsPerMl: 0.5, gramsPerCup: 120, gramsPerTbsp: 7.5, gramsPerTsp: 2.5 },
  { ingredientName: 'Cumin Seeds / Jeera', category: 'Spices & Seasoning', gramsPerMl: 0.55, gramsPerCup: 130, gramsPerTbsp: 8, gramsPerTsp: 2.7 },
  { ingredientName: 'Garam Masala', category: 'Spices & Seasoning', gramsPerMl: 0.5, gramsPerCup: 120, gramsPerTbsp: 7.5, gramsPerTsp: 2.5 },
  { ingredientName: 'Paneer (Cottage Cheese)', category: 'Dairy & Refrigerated', gramsPerMl: 0.6, gramsPerCup: 150, gramsPerTbsp: 9.3, gramsPerTsp: 3.1 },
];

// Helper to determine if a unit belongs to weight, volume, or count
export function getUnitCategory(unit: UnitType): 'weight' | 'volume' | 'count' {
  switch (unit) {
    case 'kg':
    case 'g':
    case 'lb':
      return 'weight';
    case 'L':
    case 'ml':
    case 'cup':
    case 'tbsp':
    case 'tsp':
      return 'volume';
    default:
      return 'count';
  }
}

// Get the recommended standard Base Storage Unit for an ingredient category/name
export function getBaseStorageUnit(ingredientName: string, category: IngredientCategory): UnitType {
  const nameLower = ingredientName.toLowerCase();
  
  if (nameLower.includes('milk') || nameLower.includes('oil') || nameLower.includes('water') || nameLower.includes('juice') || nameLower.includes('sauce') || category === 'Beverages') {
    return 'L';
  }
  if (nameLower.includes('egg') || nameLower.includes('bread') || nameLower.includes('pavia') || nameLower.includes('lemon') || nameLower.includes('banana') || nameLower.includes('apple') || nameLower.includes('clove')) {
    return 'pieces';
  }
  if (nameLower.includes('packet') || nameLower.includes('noodle') || nameLower.includes('biscuit') || nameLower.includes('cheese slice')) {
    return 'packets';
  }
  
  // Default for solids, vegetables, grains, pulses, flours, spices -> kg
  return 'kg';
}

/**
 * Converts a quantity from one unit to another for a given ingredient.
 * Uses exact weight/volume factors and density table for weight <-> volume conversions.
 */
export function convertUnit(
  quantity: number,
  fromUnit: UnitType,
  toUnit: UnitType,
  ingredientName?: string,
  densityTable: DensityFactor[] = DEFAULT_DENSITY_TABLE
): number {
  if (quantity === 0 || fromUnit === toUnit) return quantity;

  const fromCategory = getUnitCategory(fromUnit);
  const toCategory = getUnitCategory(toUnit);

  // Case 1: Same category conversion (Weight <-> Weight or Volume <-> Volume)
  if (fromCategory === 'weight' && toCategory === 'weight') {
    // Convert to grams first
    let grams = quantity;
    if (fromUnit === 'kg') grams = quantity * 1000;
    else if (fromUnit === 'lb') grams = quantity * 453.592;

    // Convert from grams to target unit
    if (toUnit === 'kg') return grams / 1000;
    if (toUnit === 'lb') return grams / 453.592;
    return grams; // g
  }

  if (fromCategory === 'volume' && toCategory === 'volume') {
    // Convert to ml first
    let ml = quantity;
    if (fromUnit === 'L') ml = quantity * 1000;
    else if (fromUnit === 'cup') ml = quantity * 240;
    else if (fromUnit === 'tbsp') ml = quantity * 15;
    else if (fromUnit === 'tsp') ml = quantity * 5;

    // Convert from ml to target unit
    if (toUnit === 'L') return ml / 1000;
    if (toUnit === 'cup') return ml / 240;
    if (toUnit === 'tbsp') return ml / 15;
    if (toUnit === 'tsp') return ml / 5;
    return ml; // ml
  }

  if (fromCategory === 'count' && toCategory === 'count') {
    // Handle count units loosely or as 1:1 if custom count
    return quantity;
  }

  // Case 2: Cross Category (Weight <-> Volume using Density)
  const density = densityTable.find(
    (d) => ingredientName && d.ingredientName.toLowerCase().includes(ingredientName.toLowerCase())
  );

  const gramsPerMl = density ? density.gramsPerMl : 0.8; // Default kitchen density assumption ~0.8g/ml

  if (fromCategory === 'volume' && toCategory === 'weight') {
    // Convert from volume unit to ml
    let ml = quantity;
    if (fromUnit === 'L') ml = quantity * 1000;
    else if (fromUnit === 'cup') ml = quantity * 240;
    else if (fromUnit === 'tbsp') ml = quantity * 15;
    else if (fromUnit === 'tsp') ml = quantity * 5;

    const grams = ml * gramsPerMl;

    if (toUnit === 'kg') return grams / 1000;
    if (toUnit === 'lb') return grams / 453.592;
    return grams; // g
  }

  if (fromCategory === 'weight' && toCategory === 'volume') {
    // Convert weight to grams
    let grams = quantity;
    if (fromUnit === 'kg') grams = quantity * 1000;
    else if (fromUnit === 'lb') grams = quantity * 453.592;

    const ml = grams / gramsPerMl;

    if (toUnit === 'L') return ml / 1000;
    if (toUnit === 'cup') return ml / 240;
    if (toUnit === 'tbsp') return ml / 15;
    if (toUnit === 'tsp') return ml / 5;
    return ml; // ml
  }

  // Fallback if converting Count <-> Weight/Volume
  // Assume 1 piece ~ 100g if unknown
  if (fromCategory === 'count' && toCategory === 'weight') {
    const grams = quantity * 100;
    return toUnit === 'kg' ? grams / 1000 : grams;
  }
  if (fromCategory === 'weight' && toCategory === 'count') {
    let grams = quantity;
    if (fromUnit === 'kg') grams = quantity * 1000;
    return Math.max(1, Math.round(grams / 100));
  }

  return quantity;
}

// Format numbers nicely for UI (e.g., 0.250 kg -> "250 g" or "0.25 kg")
export function formatQuantityWithUnit(quantity: number, unit: UnitType): string {
  if (quantity === 0) return `0 ${unit}`;
  
  if (unit === 'kg' && quantity < 1) {
    return `${Math.round(quantity * 1000)} g`;
  }
  if (unit === 'L' && quantity < 1) {
    return `${Math.round(quantity * 1000)} ml`;
  }
  
  const rounded = Number(quantity.toFixed(2));
  return `${rounded} ${unit}`;
}
