import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';

// Data & Engines
import { INITIAL_RECIPES } from './src/data/recipes';
import { INITIAL_INVENTORY, getAllUniqueIngredientsFromRecipes } from './src/data/ingredients';
import { generateWeeklyMealPlan } from './src/services/mealPlannerEngine';
import { convertUnit, getBaseStorageUnit } from './src/services/unitConversionEngine';
import {
  InventoryItem,
  Recipe,
  WeeklyMealPlan,
  GroceryItem,
  InventoryTransaction,
  MealEntry,
  ServingsCalcInput,
  GroceryPriority,
} from './src/types';

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '10mb' }));

// Server State Store (In-memory + REST persistence)
let inventory: InventoryItem[] = [...INITIAL_INVENTORY];
let recipes: Recipe[] = [...INITIAL_RECIPES];
let mealHistory: MealEntry[] = [];
let currentWeeklyPlan: WeeklyMealPlan = generateWeeklyMealPlan(recipes, inventory, mealHistory);
let transactions: InventoryTransaction[] = [
  {
    id: 'tx_init_1',
    date: new Date().toISOString(),
    ingredientName: 'Basmati Rice',
    type: 'Manual Adjustment',
    quantityChange: 5.0,
    unit: 'kg',
    previousQuantity: 0,
    newQuantity: 5.0,
    notes: 'Initial inventory load',
  },
];

// Helper: Calculate Grocery Requirements
function calculateGroceryList(): GroceryItem[] {
  const map = new Map<string, GroceryItem>();

  // 1. Items below minimum stock level
  inventory.forEach((item) => {
    if (item.currentQuantity <= item.minStockLevel) {
      const needed = Math.max(0, item.minStockLevel * 2 - item.currentQuantity);
      let priority: GroceryPriority = 'High';
      if (item.currentQuantity === 0) priority = 'Critical';

      map.set(item.name.toLowerCase(), {
        id: `groc_${item.id}`,
        ingredientName: item.name,
        category: item.category,
        requiredQuantity: Number(needed.toFixed(2)),
        availableQuantity: item.currentQuantity,
        baseUnit: item.baseUnit,
        priority,
        purchased: false,
        status: 'Pending',
        purchasedQuantity: Number(needed.toFixed(2)),
        reason: item.currentQuantity === 0 ? 'Out of stock' : 'Below minimum stock level',
      });
    }
  });

  // 2. Ingredients needed for active weekly meal plan
  currentWeeklyPlan.entries.forEach((meal) => {
    if (!meal.isPrepared) {
      const rec = recipes.find((r) => r.id === meal.recipeId || r.name === meal.recipeName);
      if (rec) {
        const mult = meal.totalServingsMultiplier || 2.25;
        rec.ingredients.forEach((ing) => {
          const invItem = inventory.find((i) => i.name.toLowerCase() === ing.ingredientName.toLowerCase());
          const baseUnit = invItem ? invItem.baseUnit : getBaseStorageUnit(ing.ingredientName, ing.category);
          const reqQty = convertUnit(ing.quantityOneFemale * mult, ing.unit, baseUnit, ing.ingredientName);
          const currentAvail = invItem ? invItem.currentQuantity : 0;

          if (currentAvail < reqQty) {
            const deficit = reqQty - currentAvail;
            const key = ing.ingredientName.toLowerCase();
            const existing = map.get(key);

            if (existing) {
              existing.requiredQuantity = Number((existing.requiredQuantity + deficit).toFixed(2));
              existing.purchasedQuantity = existing.requiredQuantity;
            } else {
              map.set(key, {
                id: `groc_meal_${key}`,
                ingredientName: ing.ingredientName,
                category: ing.category,
                requiredQuantity: Number(deficit.toFixed(2)),
                availableQuantity: currentAvail,
                baseUnit: baseUnit,
                priority: deficit > 1.0 ? 'High' : 'Medium',
                purchased: false,
                status: 'Pending',
                purchasedQuantity: Number(deficit.toFixed(2)),
                reason: `Required for planned meal: ${meal.recipeName}`,
              });
            }
          }
        });
      }
    }
  });

  return Array.from(map.values());
}

// REST API Endpoints
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', appName: 'Khaana Khazana' });
});

// Inventory APIs
app.get('/api/inventory', (req, res) => {
  res.json(inventory);
});

app.post('/api/inventory', (req, res) => {
  const newItem: InventoryItem = req.body;
  newItem.id = `inv_${Date.now()}`;
  newItem.lastUpdated = new Date().toISOString();
  inventory.push(newItem);
  res.status(201).json(newItem);
});

app.put('/api/inventory/:id', (req, res) => {
  const { id } = req.params;
  const index = inventory.findIndex((item) => item.id === id);
  if (index !== -1) {
    inventory[index] = { ...inventory[index], ...req.body, lastUpdated: new Date().toISOString() };
    res.json(inventory[index]);
  } else {
    res.status(404).json({ error: 'Item not found' });
  }
});

app.delete('/api/inventory/:id', (req, res) => {
  const { id } = req.params;
  inventory = inventory.filter((item) => item.id !== id);
  res.json({ success: true });
});

// Recipe APIs
app.get('/api/recipes', (req, res) => {
  res.json(recipes);
});

app.post('/api/recipes', (req, res) => {
  const newRecipe: Recipe = req.body;
  newRecipe.id = `rec_${Date.now()}`;
  recipes.push(newRecipe);
  res.status(201).json(newRecipe);
});

app.put('/api/recipes/:id', (req, res) => {
  const { id } = req.params;
  const idx = recipes.findIndex((r) => r.id === id);
  if (idx !== -1) {
    recipes[idx] = { ...recipes[idx], ...req.body };
    res.json(recipes[idx]);
  } else {
    res.status(404).json({ error: 'Recipe not found' });
  }
});

// Meal Planner APIs
app.get('/api/mealplan', (req, res) => {
  res.json(currentWeeklyPlan);
});

app.post('/api/mealplan/generate', (req, res) => {
  currentWeeklyPlan = generateWeeklyMealPlan(recipes, inventory, mealHistory);
  res.json(currentWeeklyPlan);
});

app.put('/api/mealplan/entry/:id', (req, res) => {
  const { id } = req.params;
  const idx = currentWeeklyPlan.entries.findIndex((e) => e.id === id);
  if (idx !== -1) {
    currentWeeklyPlan.entries[idx] = { ...currentWeeklyPlan.entries[idx], ...req.body };
    res.json(currentWeeklyPlan.entries[idx]);
  } else {
    res.status(404).json({ error: 'Meal entry not found' });
  }
});

// Mark Meal Prepared & Deduct Inventory
app.post('/api/mealplan/prepare', (req, res) => {
  const { mealEntryId, servings }: { mealEntryId: string; servings: ServingsCalcInput } = req.body;

  const mealIndex = currentWeeklyPlan.entries.findIndex((e) => e.id === mealEntryId);
  if (mealIndex === -1) {
    return res.status(404).json({ error: 'Meal entry not found' });
  }

  const meal = currentWeeklyPlan.entries[mealIndex];
  const recipe = recipes.find((r) => r.id === meal.recipeId || r.name === meal.recipeName);

  if (!recipe) {
    return res.status(404).json({ error: 'Recipe not found' });
  }

  // Calculate consumption multiplier: Males = 1.25, Females = 1.0, Kids = 0.75
  const males = Number(servings.males) || 0;
  const females = Number(servings.females) || 0;
  const kids = Number(servings.kids) || 0;
  const totalMultiplier = males * 1.25 + females * 1.0 + kids * 0.75;

  const deductionsSummary: { ingredient: string; deducted: number; unit: string }[] = [];

  // Deduct each ingredient from inventory safely (Never below 0)
  recipe.ingredients.forEach((ing) => {
    // Skip water
    if (ing.ingredientName.toLowerCase() === 'water') return;

    const invIdx = inventory.findIndex((item) => item.name.toLowerCase() === ing.ingredientName.toLowerCase());
    if (invIdx !== -1) {
      const invItem = inventory[invIdx];
      const reqQtyInBaseUnit = convertUnit(ing.quantityOneFemale * totalMultiplier, ing.unit, invItem.baseUnit, ing.ingredientName);

      const actualDeduction = Math.min(invItem.currentQuantity, reqQtyInBaseUnit);
      const prevQty = invItem.currentQuantity;
      const newQty = Math.max(0, Number((prevQty - actualDeduction).toFixed(3)));

      inventory[invIdx].currentQuantity = newQty;
      inventory[invIdx].lastUpdated = new Date().toISOString();

      // Record transaction
      transactions.unshift({
        id: `tx_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
        date: new Date().toISOString(),
        ingredientName: invItem.name,
        type: 'Meal Deduction',
        quantityChange: -actualDeduction,
        unit: invItem.baseUnit,
        previousQuantity: prevQty,
        newQuantity: newQty,
        referenceMealName: recipe.name,
      });

      deductionsSummary.push({ ingredient: invItem.name, deducted: actualDeduction, unit: invItem.baseUnit });
    }
  });

  // Mark meal as prepared
  meal.isPrepared = true;
  meal.preparedAt = new Date().toISOString();
  meal.servingsCount = servings;
  meal.totalServingsMultiplier = totalMultiplier;

  // Add to 14-day history
  mealHistory.push(meal);

  // Update recipe stats
  const recIdx = recipes.findIndex((r) => r.id === recipe.id);
  if (recIdx !== -1) {
    recipes[recIdx].timesPrepared = (recipes[recIdx].timesPrepared || 0) + 1;
    recipes[recIdx].lastPreparedDate = new Date().toISOString();
  }

  res.json({ success: true, meal, deductions: deductionsSummary, inventory });
});

// Grocery List APIs
app.get('/api/grocery', (req, res) => {
  const groceryList = calculateGroceryList();
  res.json(groceryList);
});

app.post('/api/grocery/purchase', (req, res) => {
  const { ingredientName, purchasedQuantity, unit }: { ingredientName: string; purchasedQuantity: number; unit: string } = req.body;

  const invIdx = inventory.findIndex((i) => i.name.toLowerCase() === ingredientName.toLowerCase());
  if (invIdx !== -1) {
    const item = inventory[invIdx];
    const addedInBaseUnit = convertUnit(purchasedQuantity, unit as any, item.baseUnit, item.name);

    const prev = item.currentQuantity;
    const next = Number((prev + addedInBaseUnit).toFixed(3));

    inventory[invIdx].currentQuantity = next;
    inventory[invIdx].lastUpdated = new Date().toISOString();

    transactions.unshift({
      id: `tx_restock_${Date.now()}`,
      date: new Date().toISOString(),
      ingredientName: item.name,
      type: 'Grocery Restock',
      quantityChange: addedInBaseUnit,
      unit: item.baseUnit,
      previousQuantity: prev,
      newQuantity: next,
      notes: 'Purchased from grocery list',
    });

    res.json({ success: true, updatedItem: inventory[invIdx] });
  } else {
    res.status(404).json({ error: 'Ingredient not found in inventory' });
  }
});

// Transactions API
app.get('/api/transactions', (req, res) => {
  res.json(transactions);
});

// Vite middleware in dev mode
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Khaana Khazana server running on http://localhost:${PORT}`);
  });
}

startServer();
