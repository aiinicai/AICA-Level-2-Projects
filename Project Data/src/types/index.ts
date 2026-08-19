export type MealType = 'Breakfast' | 'Lunch' | 'Dinner';

export type IngredientCategory =
  | 'Vegetables & Greens'
  | 'Fruits'
  | 'Grains & Pulses'
  | 'Flours & Atta'
  | 'Dairy & Refrigerated'
  | 'Spices & Seasoning'
  | 'Oils & Ghee'
  | 'Nuts & Seeds'
  | 'Condiments & Sauce'
  | 'Bakery & Snacks'
  | 'Beverages'
  | 'Other';

export type UnitType =
  // Weight
  | 'kg'
  | 'g'
  | 'lb'
  // Volume
  | 'L'
  | 'ml'
  | 'cup'
  | 'tbsp'
  | 'tsp'
  // Count
  | 'pieces'
  | 'packets'
  | 'bottles'
  | 'cans'
  | 'eggs'
  | 'cloves'
  | 'leaves'
  | 'pinch'
  | 'bunch';

export interface DensityFactor {
  ingredientName: string;
  category: IngredientCategory;
  gramsPerMl: number; // e.g., Oil = 0.92, Water = 1.0, Sugar = 0.85, Flour = 0.53
  gramsPerCup?: number;
  gramsPerTbsp?: number;
  gramsPerTsp?: number;
}

export interface InventoryItem {
  id: string;
  name: string;
  category: IngredientCategory;
  currentQuantity: number;
  baseUnit: UnitType; // Standard storage unit e.g. kg, L, pieces, packets
  minStockLevel: number; // Reorder level
  expiryDate?: string; // ISO YYYY-MM-DD
  imageUrl?: string;
  lastUpdated: string;
}

export type HealthGoal =
  | 'Muscle Gain'
  | 'Fat Loss'
  | 'Cardiovascular Endurance'
  | 'Heart Health'
  | 'Blood Pressure Control';

export interface FamilyMemberProfile {
  id: string;
  name: string;
  relation: 'Self' | 'Spouse' | 'Parent' | 'Child' | 'Other';
  weightKg: number;
  heightFt: number;
  heightInches: number;
  ageYears: number;
  gender: 'Male' | 'Female';
  activityLevel: 'Sedentary' | 'Light' | 'Moderate' | 'Active';
  primaryGoal: HealthGoal;
}

export interface RecipeIngredient {
  ingredientName: string;
  category: IngredientCategory;
  quantityOneFemale: number; // Serving size for 1 Female
  unit: UnitType;
}

export interface Recipe {
  id: string;
  name: string;
  mealType: MealType;
  cuisine: string;
  ingredients: RecipeIngredient[];
  imageUrl: string;
  isFavorite: boolean;
  timesPrepared: number;
  lastPreparedDate?: string;
  userRating?: number; // 1 to 5
  isSeasonal: boolean;
  availableFromMonth?: number; // 1-12
  availableToMonth?: number; // 1-12
  instructions?: string[];
  prepTimeMinutes?: number;
  isVeg?: boolean;
  dietaryGoals?: HealthGoal[];
}

export interface MealEntry {
  id: string;
  date: string; // YYYY-MM-DD
  dayOfWeek: string; // 'Monday', 'Tuesday', etc.
  mealType: MealType;
  recipeId: string;
  recipeName: string;
  isPrepared: boolean;
  preparedAt?: string;
  servingsCount?: {
    males: number;
    females: number;
    kids: number;
  };
  totalServingsMultiplier?: number;
  rotationWarning?: string;
}

export interface WeeklyMealPlan {
  id: string;
  weekStartDate: string; // YYYY-MM-DD (e.g. Monday)
  weekEndDate: string;
  isLocked: boolean;
  entries: MealEntry[];
}

export type GroceryPriority = 'Critical' | 'High' | 'Medium' | 'Low';
export type GroceryStatus = 'Pending' | 'Purchased' | 'Partially Purchased' | 'Deferred';

export interface GroceryItem {
  id: string;
  ingredientName: string;
  category: IngredientCategory;
  requiredQuantity: number;
  availableQuantity: number;
  baseUnit: UnitType;
  priority: GroceryPriority;
  purchased: boolean;
  status: GroceryStatus;
  purchasedQuantity: number;
  reason?: string; // e.g., 'Below min stock', 'Required for meal plan'
}

export interface InventoryTransaction {
  id: string;
  date: string;
  ingredientName: string;
  type: 'Meal Deduction' | 'Grocery Restock' | 'Manual Adjustment' | 'Bulk Import Overwrite' | 'Bulk Import Add';
  quantityChange: number; // positive or negative
  unit: UnitType;
  previousQuantity: number;
  newQuantity: number;
  referenceMealName?: string;
  notes?: string;
}

export interface ImportValidationError {
  row: number;
  ingredientName: string;
  issue: string;
  suggestedFix: string;
}

export interface ImportSummary {
  totalRows: number;
  importedRows: number;
  skippedRows: number;
  newIngredientsCount: number;
  updatedIngredientsCount: number;
  errors: ImportValidationError[];
  mode: 'replace' | 'update';
}

export interface ServingsCalcInput {
  males: number;
  females: number;
  kids: number;
}
