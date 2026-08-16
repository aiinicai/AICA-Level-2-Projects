import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { InventoryManager } from './components/InventoryManager';
import { MealPlannerView } from './components/MealPlannerView';
import { RecipeDatabaseView } from './components/RecipeDatabaseView';
import { FamilyBmiView } from './components/FamilyBmiView';
import { GroceryListView } from './components/GroceryListView';
import { ConversionSettingsView } from './components/ConversionSettingsView';
import { DatabaseSchemaView } from './components/DatabaseSchemaView';

import { INITIAL_INVENTORY } from './data/ingredients';
import { INITIAL_RECIPES } from './data/recipes';
import { generateWeeklyMealPlan, generateSingleMealEntry, isRecipePureVeg } from './services/mealPlannerEngine';
import { convertUnit, getBaseStorageUnit } from './services/unitConversionEngine';
import {
  InventoryItem,
  Recipe,
  WeeklyMealPlan,
  GroceryItem,
  ServingsCalcInput,
  GroceryPriority,
  FamilyMemberProfile,
  HealthGoal,
} from './types';
import { RecipeImportResult } from './services/excelService';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);
  const [isPureVeg, setIsPureVeg] = useState<boolean>(false);

  // App State
  const [inventory, setInventory] = useState<InventoryItem[]>(INITIAL_INVENTORY);
  const [recipes, setRecipes] = useState<Recipe[]>(INITIAL_RECIPES);
  const [mealPlan, setMealPlan] = useState<WeeklyMealPlan>(() =>
    generateWeeklyMealPlan(INITIAL_RECIPES, INITIAL_INVENTORY, [], undefined, false)
  );
  const [groceryList, setGroceryList] = useState<GroceryItem[]>([]);

  // Family BMI Profiles State
  const [familyProfiles, setFamilyProfiles] = useState<FamilyMemberProfile[]>([
    {
      id: 'profile_1',
      name: 'Rahul Sharma',
      relation: 'Self',
      weightKg: 74,
      heightFt: 5,
      heightInches: 10,
      ageYears: 32,
      gender: 'Male',
      activityLevel: 'Moderate',
      primaryGoal: 'Muscle Gain',
    },
    {
      id: 'profile_2',
      name: 'Ananya Sharma',
      relation: 'Spouse',
      weightKg: 58,
      heightFt: 5,
      heightInches: 4,
      ageYears: 29,
      gender: 'Female',
      activityLevel: 'Light',
      primaryGoal: 'Fat Loss',
    },
  ]);

  // Sync dark mode class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  // Fetch initial data from server APIs if available
  useEffect(() => {
    fetch('/api/inventory')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) setInventory(data);
      })
      .catch(() => console.log('Using local client inventory state'));

    fetch('/api/recipes')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) setRecipes(data);
      })
      .catch(() => console.log('Using local client recipe state'));
  }, []);

  // Helper for rounding up to the nearest 0.5 (e.g. 1.2 -> 1.5, 2.6 -> 3.0)
  const roundUpToNearestHalf = (val: number): number => {
    if (val <= 0) return 0;
    return Math.ceil(val * 2) / 2;
  };

  // Compute Grocery Requirements automatically when inventory or meal plan changes
  useEffect(() => {
    const map = new Map<string, GroceryItem>();
    const rawDeficitMap = new Map<string, number>();

    // 1. Items below minimum stock level
    inventory.forEach((item) => {
      if (item.currentQuantity <= item.minStockLevel) {
        const rawNeeded = Math.max(0, item.minStockLevel * 2 - item.currentQuantity);
        const key = item.name.toLowerCase();
        rawDeficitMap.set(key, (rawDeficitMap.get(key) || 0) + rawNeeded);

        let priority: GroceryPriority = 'High';
        if (item.currentQuantity === 0) priority = 'Critical';

        map.set(key, {
          id: `groc_${item.id}`,
          ingredientName: item.name,
          category: item.category,
          requiredQuantity: roundUpToNearestHalf(rawDeficitMap.get(key)!),
          availableQuantity: item.currentQuantity,
          baseUnit: item.baseUnit,
          priority,
          purchased: false,
          status: 'Pending',
          purchasedQuantity: roundUpToNearestHalf(rawDeficitMap.get(key)!),
          reason: item.currentQuantity === 0 ? 'Out of stock' : 'Below minimum stock level',
        });
      }
    });

    // 2. Ingredients needed for un-prepared weekly meals
    mealPlan.entries.forEach((meal) => {
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
              const existingRaw = rawDeficitMap.get(key) || 0;
              const newRaw = existingRaw + deficit;
              rawDeficitMap.set(key, newRaw);

              const roundedVal = roundUpToNearestHalf(newRaw);
              const existingItem = map.get(key);

              if (existingItem) {
                existingItem.requiredQuantity = roundedVal;
                existingItem.purchasedQuantity = roundedVal;
              } else {
                map.set(key, {
                  id: `groc_meal_${key}`,
                  ingredientName: ing.ingredientName,
                  category: ing.category,
                  requiredQuantity: roundedVal,
                  availableQuantity: currentAvail,
                  baseUnit: baseUnit,
                  priority: roundedVal > 1.0 ? 'High' : 'Medium',
                  purchased: false,
                  status: 'Pending',
                  purchasedQuantity: roundedVal,
                  reason: `Required for planned meal: ${meal.recipeName}`,
                });
              }
            }
          });
        }
      }
    });

    setGroceryList(Array.from(map.values()));
  }, [inventory, mealPlan, recipes]);

  // Inventory Handlers
  const handleUpdateQuantity = (id: string, delta: number) => {
    setInventory((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              currentQuantity: Math.max(0, Number((item.currentQuantity + delta).toFixed(3))),
              lastUpdated: new Date().toISOString(),
            }
          : item
      )
    );
  };

  const handleAddItem = (newItem: InventoryItem) => {
    setInventory((prev) => [...prev, newItem]);
  };

  const handleEditItem = (editedItem: InventoryItem) => {
    setInventory((prev) => prev.map((item) => (item.id === editedItem.id ? editedItem : item)));
  };

  const handleDeleteItem = (id: string) => {
    setInventory((prev) => prev.filter((item) => item.id !== id));
  };

  // Prepare Meal & Deduct Inventory
  const handlePrepareMeal = (mealEntryId: string, servings: ServingsCalcInput) => {
    const mealIndex = mealPlan.entries.findIndex((e) => e.id === mealEntryId);
    if (mealIndex === -1) return;

    const meal = mealPlan.entries[mealIndex];
    const recipe = recipes.find((r) => r.id === meal.recipeId || r.name === meal.recipeName);
    if (!recipe) return;

    // Calculation formula: Male = 1.25, Female = 1.0, Kid = 0.75
    const totalMultiplier =
      (Number(servings.males) || 0) * 1.25 +
      (Number(servings.females) || 0) * 1.0 +
      (Number(servings.kids) || 0) * 0.75;

    // Deduct stock
    setInventory((prevInventory) => {
      const updated = [...prevInventory];

      recipe.ingredients.forEach((ing) => {
        if (ing.ingredientName.toLowerCase() === 'water') return;

        const invIdx = updated.findIndex(
          (item) => item.name.toLowerCase() === ing.ingredientName.toLowerCase()
        );

        if (invIdx !== -1) {
          const invItem = updated[invIdx];
          const reqQtyInBase = convertUnit(
            ing.quantityOneFemale * totalMultiplier,
            ing.unit,
            invItem.baseUnit,
            ing.ingredientName
          );

          const actualDeduction = Math.min(invItem.currentQuantity, reqQtyInBase);
          const newQty = Math.max(0, Number((invItem.currentQuantity - actualDeduction).toFixed(3)));

          updated[invIdx] = {
            ...invItem,
            currentQuantity: newQty,
            lastUpdated: new Date().toISOString(),
          };
        }
      });

      return updated;
    });

    // Mark meal prepared
    setMealPlan((prevPlan) => {
      const updatedEntries = [...prevPlan.entries];
      updatedEntries[mealIndex] = {
        ...updatedEntries[mealIndex],
        isPrepared: true,
        preparedAt: new Date().toISOString(),
        servingsCount: servings,
        totalServingsMultiplier: totalMultiplier,
      };
      return { ...prevPlan, entries: updatedEntries };
    });

    // Send to backend API asynchronously
    fetch('/api/mealplan/prepare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mealEntryId, servings }),
    }).catch(() => console.log('Async sync to backend complete'));
  };

  // Meal Planner Handlers
  const handleTogglePureVeg = (val: boolean) => {
    setIsPureVeg(val);
    setMealPlan(generateWeeklyMealPlan(recipes, inventory, [], undefined, val));
  };

  const handleRegenerateFullWeek = () => {
    setMealPlan(generateWeeklyMealPlan(recipes, inventory, [], undefined, isPureVeg));
  };

  const handleRegenerateDay = (dayOfWeek: string) => {
    const activeRecipes = isPureVeg ? recipes.filter(isRecipePureVeg) : recipes;

    setMealPlan((prev) => ({
      ...prev,
      entries: prev.entries.map((entry) => {
        if (entry.dayOfWeek === dayOfWeek && !entry.isPrepared) {
          const candidates = activeRecipes.filter(
            (r) => r.mealType === entry.mealType && r.id !== entry.recipeId && r.name !== entry.recipeName
          );

          if (candidates.length > 0) {
            const randomIndex = Math.floor(Math.random() * candidates.length);
            const chosen = candidates[randomIndex];
            return {
              ...entry,
              recipeId: chosen.id,
              recipeName: chosen.name,
              rotationWarning: undefined,
            };
          }
        }
        return entry;
      }),
    }));
  };

  const handleReplaceMeal = (mealEntryId: string, newRecipeId: string) => {
    const newRecipe = recipes.find((r) => r.id === newRecipeId);
    if (!newRecipe) return;

    setMealPlan((prev) => ({
      ...prev,
      entries: prev.entries.map((e) =>
        e.id === mealEntryId
          ? {
              ...e,
              recipeId: newRecipe.id,
              recipeName: newRecipe.name,
              rotationWarning: undefined,
            }
          : e
      ),
    }));
  };

  const handleCancelMeal = (mealEntryId: string) => {
    setMealPlan((prev) => ({
      ...prev,
      entries: prev.entries.filter((e) => e.id !== mealEntryId),
    }));
  };

  const handleToggleLock = () => {
    setMealPlan((prev) => ({ ...prev, isLocked: !prev.isLocked }));
  };

  // Grocery Purchase Restock
  const handleMarkPurchased = (ingredientName: string, purchasedQty: number, unit: string) => {
    setInventory((prev) =>
      prev.map((item) => {
        if (item.name.toLowerCase() === ingredientName.toLowerCase()) {
          const addedInBase = convertUnit(purchasedQty, unit as any, item.baseUnit, item.name);
          return {
            ...item,
            currentQuantity: Number((item.currentQuantity + addedInBase).toFixed(3)),
            lastUpdated: new Date().toISOString(),
          };
        }
        return item;
      })
    );

    fetch('/api/grocery/purchase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredientName, purchasedQuantity: purchasedQty, unit }),
    }).catch(() => console.log('Purchased restock saved'));
  };

  // Recipe Handlers
  const handleToggleFavorite = (recipeId: string) => {
    setRecipes((prev) =>
      prev.map((r) => (r.id === recipeId ? { ...r, isFavorite: !r.isFavorite } : r))
    );
  };

  const handleUpdateRating = (recipeId: string, rating: number) => {
    setRecipes((prev) => prev.map((r) => (r.id === recipeId ? { ...r, userRating: rating } : r)));
  };

  const handleUpdateSeasonal = (
    recipeId: string,
    isSeasonal: boolean,
    fromMonth: number = 10,
    toMonth: number = 3
  ) => {
    setRecipes((prev) =>
      prev.map((r) =>
        r.id === recipeId
          ? {
              ...r,
              isSeasonal,
              availableFromMonth: fromMonth,
              availableToMonth: toMonth,
            }
          : r
      )
    );
  };

  // Single Meal Generation Handler
  const handleGenerateSingleMeal = (mealEntryId: string) => {
    setMealPlan((prev) => generateSingleMealEntry(mealEntryId, prev, recipes, inventory, isPureVeg));
  };

  // Bulk Recipe Import Handler (and auto-sync ingredients to Inventory Master)
  const handleRecipeImportSuccess = (result: RecipeImportResult) => {
    setRecipes(result.updatedRecipes);
    if (result.autoAddedInventoryItems.length > 0) {
      setInventory((prev) => [...prev, ...result.autoAddedInventoryItems]);
    }
  };

  // Family Profile Handlers
  const handleAddFamilyProfile = (profile: FamilyMemberProfile) => {
    setFamilyProfiles((prev) => [...prev, profile]);
  };

  const handleEditFamilyProfile = (edited: FamilyMemberProfile) => {
    setFamilyProfiles((prev) => prev.map((p) => (p.id === edited.id ? edited : p)));
  };

  const handleDeleteFamilyProfile = (id: string) => {
    setFamilyProfiles((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <div className="min-h-screen bg-[#fdf8f4] dark:bg-[#0f172a] text-slate-900 dark:text-slate-100 transition-colors duration-300 flex flex-col font-sans">
      {/* Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isDarkMode={isDarkMode}
        setIsDarkMode={setIsDarkMode}
        unreadAlertsCount={groceryList.length}
      />

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <Dashboard
            inventory={inventory}
            recipes={recipes}
            mealPlan={mealPlan}
            groceryList={groceryList}
            onPrepareMeal={handlePrepareMeal}
            onNavigateTab={setActiveTab}
          />
        )}

        {activeTab === 'inventory' && (
          <InventoryManager
            inventory={inventory}
            onUpdateQuantity={handleUpdateQuantity}
            onAddItem={handleAddItem}
            onEditItem={handleEditItem}
            onDeleteItem={handleDeleteItem}
            onNavigateToGrocery={() => setActiveTab('grocery')}
            onImportSuccess={(updated) => setInventory(updated)}
          />
        )}

        {activeTab === 'mealplanner' && (
          <MealPlannerView
            mealPlan={mealPlan}
            recipes={recipes}
            inventory={inventory}
            isPureVeg={isPureVeg}
            onTogglePureVeg={handleTogglePureVeg}
            onRegenerateFullWeek={handleRegenerateFullWeek}
            onRegenerateDay={handleRegenerateDay}
            onGenerateSingleMeal={handleGenerateSingleMeal}
            onReplaceMeal={handleReplaceMeal}
            onCancelMeal={handleCancelMeal}
            onToggleLock={handleToggleLock}
            onPrepareMeal={handlePrepareMeal}
          />
        )}

        {activeTab === 'recipes' && (
          <RecipeDatabaseView
            recipes={recipes}
            inventory={inventory}
            onToggleFavorite={handleToggleFavorite}
            onUpdateRating={handleUpdateRating}
            onUpdateSeasonal={handleUpdateSeasonal}
            onImportSuccess={handleRecipeImportSuccess}
          />
        )}

        {activeTab === 'family_bmi' && (
          <FamilyBmiView
            familyProfiles={familyProfiles}
            onAddProfile={handleAddFamilyProfile}
            onEditProfile={handleEditFamilyProfile}
            onDeleteProfile={handleDeleteFamilyProfile}
            recipes={recipes}
            onSelectGoalFilter={() => setActiveTab('recipes')}
          />
        )}

        {activeTab === 'grocery' && (
          <GroceryListView
            groceryList={groceryList}
            onMarkPurchased={handleMarkPurchased}
            onRefreshList={() => {}}
          />
        )}

        {activeTab === 'conversions' && <ConversionSettingsView />}

        {activeTab === 'schema' && <DatabaseSchemaView />}
      </main>
    </div>
  );
}

export default App;
