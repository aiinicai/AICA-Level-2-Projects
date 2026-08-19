import { Recipe, InventoryItem, MealEntry, WeeklyMealPlan, MealType, HealthGoal } from '../types';
import { convertUnit } from './unitConversionEngine';

const NON_VEG_KEYWORDS = [
  'chicken',
  'mutton',
  'fish',
  'egg',
  'eggs',
  'prawn',
  'prawns',
  'meat',
  'lamb',
  'pork',
  'beef',
  'seafood',
  'keema',
  'chicken/mutton',
];

/**
 * Checks if a recipe is pure vegetarian (no meat, fish, eggs, etc.)
 */
export function isRecipePureVeg(recipe: Recipe): boolean {
  if (recipe.isVeg !== undefined) return recipe.isVeg;

  const nameLower = recipe.name.toLowerCase();
  for (const kw of NON_VEG_KEYWORDS) {
    if (nameLower.includes(kw)) return false;
  }

  for (const ing of recipe.ingredients) {
    const ingLower = ing.ingredientName.toLowerCase();
    for (const kw of NON_VEG_KEYWORDS) {
      if (ingLower.includes(kw)) return false;
    }
  }

  return true;
}

/**
 * Checks if a seasonal recipe is available in the given month (1 to 12).
 */
export function isRecipeSeasonallyAvailable(recipe: Recipe, month: number = new Date().getMonth() + 1): boolean {
  if (!recipe.isSeasonal || !recipe.availableFromMonth || !recipe.availableToMonth) {
    return true; // Not seasonal, always available
  }

  const { availableFromMonth: from, availableToMonth: to } = recipe;

  if (from <= to) {
    return month >= from && month <= to;
  } else {
    // Crosses year boundary e.g. Oct (10) to Mar (3)
    return month >= from || month <= to;
  }
}

/**
 * Calculates ingredient availability ratio (0.0 to 1.0) for a recipe against current inventory.
 */
export function calculateRecipeInventoryCoverage(
  recipe: Recipe,
  inventory: InventoryItem[],
  femaleMultiplier: number = 1.0
): { coverageRatio: number; missingIngredientsCount: number; usesExpiringIngredient: boolean } {
  let matchedCount = 0;
  let usesExpiring = false;
  const today = new Date();

  const inventoryMap = new Map<string, InventoryItem>();
  inventory.forEach((item) => inventoryMap.set(item.name.toLowerCase(), item));

  recipe.ingredients.forEach((ing) => {
    const invItem = inventoryMap.get(ing.ingredientName.toLowerCase());
    if (invItem) {
      const requiredInBaseUnit = convertUnit(ing.quantityOneFemale * femaleMultiplier, ing.unit, invItem.baseUnit, ing.ingredientName);
      if (invItem.currentQuantity >= requiredInBaseUnit) {
        matchedCount++;
      }

      // Check if item expires in <= 5 days
      if (invItem.expiryDate) {
        const expDate = new Date(invItem.expiryDate);
        const daysLeft = Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 3600 * 24));
        if (daysLeft >= 0 && daysLeft <= 5 && invItem.currentQuantity > 0) {
          usesExpiring = true;
        }
      }
    }
  });

  const total = recipe.ingredients.length;
  const ratio = total > 0 ? matchedCount / total : 1;
  const missing = total - matchedCount;

  return { coverageRatio: ratio, missingIngredientsCount: missing, usesExpiringIngredient: usesExpiring };
}

/**
 * Score a candidate recipe for a specific slot.
 */
function scoreRecipe(
  recipe: Recipe,
  mealType: MealType,
  inventory: InventoryItem[],
  historyMealNamesInLast14Days: Set<string>,
  previousMealCuisines: string[],
  currentMonth: number
): { score: number; rotationWarning?: string } {
  let score = 0;
  let rotationWarning: string | undefined = undefined;

  // Priority b: Seasonal availability check
  if (!isRecipeSeasonallyAvailable(recipe, currentMonth)) {
    score -= 200; // heavy penalty for out of season
  }

  // Priority c: 14-day repetition check
  if (historyMealNamesInLast14Days.has(recipe.name.toLowerCase())) {
    score -= 100;
    rotationWarning = `Note: '${recipe.name}' was prepared within the last 14 days. Selected to satisfy available inventory.`;
  }

  // Priority a & d: Expiry and Inventory Coverage
  const { coverageRatio, usesExpiringIngredient } = calculateRecipeInventoryCoverage(recipe, inventory);
  if (usesExpiringIngredient) {
    score += 60; // Highest priority: prevent food waste!
  }
  score += coverageRatio * 50; // Maximize existing inventory

  // Priority f: Favorite & Rating
  if (recipe.isFavorite) score += 20;
  score += (recipe.userRating || 3) * 4;

  // Priority g: Cuisine variety
  if (previousMealCuisines.length > 0 && !previousMealCuisines.includes(recipe.cuisine)) {
    score += 15;
  }

  return { score, rotationWarning };
}

/**
 * Generates a full 7-day weekly meal plan based on inventory, 14-day history, seasonal rules, and favorites.
 */
export function generateWeeklyMealPlan(
  recipes: Recipe[],
  inventory: InventoryItem[],
  existingHistory: MealEntry[] = [],
  startDateISO?: string,
  isPureVeg: boolean = false
): WeeklyMealPlan {
  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const MEAL_TYPES: MealType[] = ['Breakfast', 'Lunch', 'Dinner'];

  const now = new Date();
  const currentMonth = now.getMonth() + 1;

  const activeRecipes = isPureVeg ? recipes.filter(isRecipePureVeg) : recipes;

  // Calculate start date (e.g. next Monday or current Monday)
  let start = startDateISO ? new Date(startDateISO) : new Date();
  const dayOfWeekNum = start.getDay(); // 0 is Sunday
  const diffToMonday = (dayOfWeekNum === 0 ? -6 : 1 - dayOfWeekNum);
  start.setDate(start.getDate() + diffToMonday);

  const end = new Date(start);
  end.setDate(start.getDate() + 6);

  const weekStartDate = start.toISOString().split('T')[0];
  const weekEndDate = end.toISOString().split('T')[0];

  // Build 14-day history set of recipe names
  const historyMealNames = new Set<string>();
  const fourteenDaysAgo = new Date();
  fourteenDaysAgo.setDate(fourteenDaysAgo.getDate() - 14);

  existingHistory.forEach((h) => {
    if (new Date(h.date) >= fourteenDaysAgo) {
      historyMealNames.add(h.recipeName.toLowerCase());
    }
  });

  const entries: MealEntry[] = [];
  const usedInThisWeek = new Set<string>();
  let previousCuisines: string[] = [];

  DAYS.forEach((day, dayIdx) => {
    const currentDate = new Date(start);
    currentDate.setDate(start.getDate() + dayIdx);
    const dateStr = currentDate.toISOString().split('T')[0];

    MEAL_TYPES.forEach((mType) => {
      const candidates = activeRecipes.filter((r) => r.mealType === mType);

      // Score all candidate recipes
      let bestRecipe: Recipe | null = null;
      let bestScore = -99999;
      let bestWarning: string | undefined = undefined;

      candidates.forEach((cand) => {
        // Combined history + current week used
        const combinedHistory = new Set(historyMealNames);
        if (usedInThisWeek.has(cand.name.toLowerCase())) {
          combinedHistory.add(cand.name.toLowerCase());
        }

        const { score, rotationWarning } = scoreRecipe(
          cand,
          mType,
          inventory,
          combinedHistory,
          previousCuisines,
          currentMonth
        );

        if (score > bestScore) {
          bestScore = score;
          bestRecipe = cand;
          bestWarning = rotationWarning;
        }
      });

      // Fallback if no recipe found
      if (!bestRecipe && candidates.length > 0) {
        bestRecipe = candidates[0];
      }

      if (bestRecipe) {
        usedInThisWeek.add(bestRecipe.name.toLowerCase());
        previousCuisines.push(bestRecipe.cuisine);
        if (previousCuisines.length > 3) previousCuisines.shift();

        entries.push({
          id: `meal_${dateStr}_${mType.toLowerCase()}`,
          date: dateStr,
          dayOfWeek: day,
          mealType: mType,
          recipeId: bestRecipe.id,
          recipeName: bestRecipe.name,
          isPrepared: false,
          rotationWarning: bestWarning,
          servingsCount: { males: 1, females: 1, kids: 0 },
          totalServingsMultiplier: 2.25, // 1 male (1.25) + 1 female (1.0) = 2.25
        });
      }
    });
  });

  return {
    id: `plan_${weekStartDate}`,
    weekStartDate,
    weekEndDate,
    isLocked: false,
    entries,
  };
}

/**
 * Generates a single meal replacement for a specific meal entry slot in the weekly plan.
 */
export function generateSingleMealEntry(
  targetMealEntryId: string,
  currentMealPlan: WeeklyMealPlan,
  recipes: Recipe[],
  inventory: InventoryItem[],
  isPureVeg: boolean = false,
  targetGoal?: HealthGoal | 'All'
): WeeklyMealPlan {
  const targetEntry = currentMealPlan.entries.find((e) => e.id === targetMealEntryId);
  if (!targetEntry) return currentMealPlan;

  let candidates = isPureVeg ? recipes.filter(isRecipePureVeg) : recipes;
  candidates = candidates.filter((r) => r.mealType === targetEntry.mealType);

  if (targetGoal && targetGoal !== 'All') {
    const goalFiltered = candidates.filter((r) => r.dietaryGoals?.includes(targetGoal as HealthGoal));
    if (goalFiltered.length > 0) {
      candidates = goalFiltered;
    }
  }

  // Filter out currently scheduled recipe for that slot to ensure a fresh meal choice
  const alternatives = candidates.filter(
    (r) => r.id !== targetEntry.recipeId && r.name.toLowerCase() !== targetEntry.recipeName.toLowerCase()
  );

  const pool = alternatives.length > 0 ? alternatives : candidates;
  if (pool.length === 0) return currentMealPlan;

  const currentMonth = new Date().getMonth() + 1;
  let bestRecipe: Recipe = pool[0];
  let bestScore = -99999;
  let bestWarning: string | undefined = undefined;

  pool.forEach((cand) => {
    const { score, rotationWarning } = scoreRecipe(
      cand,
      targetEntry.mealType,
      inventory,
      new Set(),
      [],
      currentMonth
    );

    if (score > bestScore) {
      bestScore = score;
      bestRecipe = cand;
      bestWarning = rotationWarning;
    }
  });

  const updatedEntries = currentMealPlan.entries.map((entry) => {
    if (entry.id === targetMealEntryId) {
      return {
        ...entry,
        recipeId: bestRecipe.id,
        recipeName: bestRecipe.name,
        rotationWarning: bestWarning,
        isPrepared: false,
      };
    }
    return entry;
  });

  return {
    ...currentMealPlan,
    entries: updatedEntries,
  };
}
