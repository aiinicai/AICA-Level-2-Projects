import { InventoryItem, IngredientCategory, UnitType } from '../types';
import { INITIAL_RECIPES } from './recipes';
import { getBaseStorageUnit } from '../services/unitConversionEngine';

// Image mapping for common ingredient categories and items
const INGREDIENT_IMAGES: Record<string, string> = {
  'poha': 'https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=400&q=80',
  'rice': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=400&q=80',
  'dal': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=400&q=80',
  'flour': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=400&q=80',
  'paneer': 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=400&q=80',
  'milk': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=400&q=80',
  'oil': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=400&q=80',
  'ghee': 'https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?auto=format&fit=crop&w=400&q=80',
  'egg': 'https://images.unsplash.com/photo-1516448620398-c5f44bf9f441?auto=format&fit=crop&w=400&q=80',
  'chicken': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?auto=format&fit=crop&w=400&q=80',
  'fish': 'https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=400&q=80',
  'potato': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=400&q=80',
  'onion': 'https://images.unsplash.com/photo-1508747703725-719777637510?auto=format&fit=crop&w=400&q=80',
  'tomato': 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=400&q=80',
  'default': 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=400&q=80',
};

export function getIngredientImageUrl(name: string): string {
  const lower = name.toLowerCase();
  for (const key of Object.keys(INGREDIENT_IMAGES)) {
    if (lower.includes(key)) return INGREDIENT_IMAGES[key];
  }
  return INGREDIENT_IMAGES['default'];
}

// Dynamically extract all unique ingredients from recipe database to maintain automatic consistency!
export function getAllUniqueIngredientsFromRecipes(): { name: string; category: IngredientCategory; baseUnit: UnitType }[] {
  const map = new Map<string, { name: string; category: IngredientCategory; baseUnit: UnitType }>();

  INITIAL_RECIPES.forEach((recipe) => {
    recipe.ingredients.forEach((ing) => {
      if (!map.has(ing.ingredientName)) {
        map.set(ing.ingredientName, {
          name: ing.ingredientName,
          category: ing.category,
          baseUnit: getBaseStorageUnit(ing.ingredientName, ing.category),
        });
      }
    });
  });

  return Array.from(map.values());
}

// Generate realistic default initial inventory stock for testing/demo
export function generateInitialInventory(): InventoryItem[] {
  const uniqueIngs = getAllUniqueIngredientsFromRecipes();
  const today = new Date();

  return uniqueIngs.map((ing, idx) => {
    const baseUnit = ing.baseUnit;
    let currentQty = 2.5; // default 2.5 kg or 2.5 L
    let minStock = 1.0;

    if (baseUnit === 'L') {
      currentQty = 3.0;
      minStock = 1.0;
    } else if (baseUnit === 'pieces') {
      currentQty = 12;
      minStock = 4;
    } else if (baseUnit === 'packets') {
      currentQty = 5;
      minStock = 2;
    } else if (ing.category === 'Spices & Seasoning') {
      currentQty = 0.5; // 500g
      minStock = 0.1;
    }

    // Make 2-3 items low stock for instant alert demonstration!
    if (ing.name.includes('Paneer') || ing.name.includes('Milk') || ing.name.includes('Spinach')) {
      currentQty = 0.2; // Very low
    }

    // Generate random future expiry dates (some fresh veggies expiring in 2-4 days)
    const expDate = new Date(today);
    if (ing.category === 'Vegetables & Greens' || ing.category === 'Dairy & Refrigerated') {
      expDate.setDate(today.getDate() + ((idx % 7) + 2)); // 2 to 8 days
    } else {
      expDate.setDate(today.getDate() + 90); // 3 months for grains/spices
    }

    return {
      id: `inv_${idx + 1}`,
      name: ing.name,
      category: ing.category,
      currentQuantity: currentQty,
      baseUnit: baseUnit,
      minStockLevel: minStock,
      expiryDate: expDate.toISOString().split('T')[0],
      imageUrl: getIngredientImageUrl(ing.name),
      lastUpdated: new Date().toISOString(),
    };
  });
}

export const INITIAL_INVENTORY: InventoryItem[] = generateInitialInventory();
