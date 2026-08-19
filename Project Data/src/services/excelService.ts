import * as XLSX from 'xlsx';
import { InventoryItem, Recipe, RecipeIngredient, HealthGoal, ImportSummary, ImportValidationError, UnitType, MealType } from '../types';
import { getAllUniqueIngredientsFromRecipes } from '../data/ingredients';
import { convertUnit, getBaseStorageUnit } from './unitConversionEngine';

export const SUPPORTED_UNITS: UnitType[] = [
  'kg',
  'g',
  'lb',
  'L',
  'ml',
  'cup',
  'tbsp',
  'tsp',
  'pieces',
  'packets',
  'bottles',
  'cans',
  'eggs',
  'cloves',
  'leaves',
  'pinch',
  'bunch',
];

/**
 * Downloads the sample Excel template pre-populated with all unique ingredients
 * extracted from the recipe database.
 */
export function downloadSampleExcelTemplate(): void {
  const ingredients = getAllUniqueIngredientsFromRecipes();

  // Prepare row data
  const templateData = ingredients.map((ing) => ({
    'Ingredient Name': ing.name,
    'Category': ing.category,
    'Quantity': '', // Blank for user input
    'Unit': ing.baseUnit, // Default recommended unit
    'Minimum Stock Level (Optional)': 1.0,
  }));

  const worksheet = XLSX.utils.json_to_sheet(templateData);

  // Set column widths for clean presentation
  worksheet['!cols'] = [
    { wch: 35 }, // Ingredient Name
    { wch: 25 }, // Category
    { wch: 15 }, // Quantity
    { wch: 15 }, // Unit
    { wch: 30 }, // Minimum Stock Level
  ];

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Opening Inventory');

  // Export & trigger browser download
  XLSX.writeFile(workbook, 'Khaana_Khazana_Opening_Inventory_Template.xlsx');
}

/**
 * Parses an uploaded Excel file and converts quantities to standard base units.
 */
export async function parseAndValidateInventoryExcel(
  file: File,
  currentInventory: InventoryItem[],
  mode: 'replace' | 'update'
): Promise<{ summary: ImportSummary; updatedInventory: InventoryItem[] }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];

        const jsonRows: any[] = XLSX.utils.sheet_to_json(worksheet, { defval: '' });

        const errors: ImportValidationError[] = [];
        const seenIngredients = new Set<string>();

        let importedCount = 0;
        let skippedCount = 0;
        let newCount = 0;
        let updatedCount = 0;

        // Clone current inventory list
        const inventoryMap = new Map<string, InventoryItem>();
        currentInventory.forEach((item) => inventoryMap.set(item.name.toLowerCase().trim(), { ...item }));

        jsonRows.forEach((row, index) => {
          const rowNum = index + 2; // Row 1 is header
          const ingNameRaw = row['Ingredient Name'] || row['IngredientName'] || row['Name'] || '';
          const ingName = String(ingNameRaw).trim();
          const category = (row['Category'] || 'Other').trim();
          const qtyRaw = row['Quantity'];
          const unitRaw = (row['Unit'] || 'kg').trim();
          const minStockRaw = row['Minimum Stock Level (Optional)'] || row['Minimum Stock Level'] || row['MinStock'] || 0;

          // 1. Skip completely blank rows or missing ingredient names
          if (!ingName && (qtyRaw === '' || qtyRaw === undefined)) {
            skippedCount++;
            return;
          }

          // 2. Validate mandatory ingredient name
          if (!ingName) {
            errors.push({
              row: rowNum,
              ingredientName: 'Unknown',
              issue: 'Missing mandatory field: Ingredient Name',
              suggestedFix: 'Provide a valid ingredient name.',
            });
            return;
          }

          // 3. Ignore blank quantity rows (as per spec: "Ignore rows with blank quantities")
          if (qtyRaw === '' || qtyRaw === undefined || qtyRaw === null) {
            skippedCount++;
            return;
          }

          const numericQty = Number(qtyRaw);

          // 4. Validate numeric values
          if (isNaN(numericQty) || numericQty < 0) {
            errors.push({
              row: rowNum,
              ingredientName: ingName,
              issue: `Invalid numeric quantity: '${qtyRaw}'`,
              suggestedFix: 'Enter a valid non-negative number.',
            });
            return;
          }

          // 5. Check duplicate entries in file
          const ingKey = ingName.toLowerCase();
          if (seenIngredients.has(ingKey)) {
            errors.push({
              row: rowNum,
              ingredientName: ingName,
              issue: `Duplicate ingredient entry found in row ${rowNum}`,
              suggestedFix: 'Combine duplicate rows into a single entry.',
            });
            return;
          }
          seenIngredients.add(ingKey);

          // 6. Validate supported unit
          const normalizedUnit = unitRaw as UnitType;
          if (!SUPPORTED_UNITS.includes(normalizedUnit)) {
            errors.push({
              row: rowNum,
              ingredientName: ingName,
              issue: `Unsupported unit: '${unitRaw}'`,
              suggestedFix: `Choose a supported unit: ${SUPPORTED_UNITS.slice(0, 6).join(', ')}, etc.`,
            });
            return;
          }

          // Convert quantity to ingredient's Base Storage Unit
          const baseUnit = getBaseStorageUnit(ingName, category as any);
          const convertedQty = convertUnit(numericQty, normalizedUnit, baseUnit, ingName);
          const convertedMinStock = convertUnit(Number(minStockRaw) || 0, normalizedUnit, baseUnit, ingName);

          // Update inventory map
          const existingItem = inventoryMap.get(ingKey);
          if (existingItem) {
            updatedCount++;
            const newQuantity = mode === 'replace' ? convertedQty : existingItem.currentQuantity + convertedQty;
            inventoryMap.set(ingKey, {
              ...existingItem,
              currentQuantity: Number(newQuantity.toFixed(3)),
              baseUnit: baseUnit,
              minStockLevel: convertedMinStock || existingItem.minStockLevel,
              lastUpdated: new Date().toISOString(),
            });
          } else {
            newCount++;
            inventoryMap.set(ingKey, {
              id: `inv_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
              name: ingName,
              category: (category as any) || 'Other',
              currentQuantity: Number(convertedQty.toFixed(3)),
              baseUnit: baseUnit,
              minStockLevel: convertedMinStock || 1.0,
              lastUpdated: new Date().toISOString(),
              expiryDate: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
              imageUrl: `https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=400&q=80`,
            });
          }

          importedCount++;
        });

        const updatedInventoryList = Array.from(inventoryMap.values());

        const summary: ImportSummary = {
          totalRows: jsonRows.length,
          importedRows: importedCount,
          skippedRows: skippedCount,
          newIngredientsCount: newCount,
          updatedIngredientsCount: updatedCount,
          errors,
          mode,
        };

        resolve({ summary, updatedInventory: updatedInventoryList });
      } catch (err: any) {
        reject(new Error(`Failed to parse Excel file: ${err.message || err}`));
      }
    };

    reader.onerror = () => reject(new Error('File reading error.'));
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Downloads a sample Recipe Master Excel Template
 */
export function downloadRecipeExcelTemplate(): void {
  const sampleData = [
    {
      'Recipe Name': 'High Protein Paneer Bhurji',
      'Meal Type': 'Breakfast',
      'Cuisine': 'North Indian',
      'Prep Time (Mins)': 15,
      'Is Vegetarian': 'Yes',
      'Dietary Goals': 'Muscle Gain, Fat Loss, Heart Health',
      'Ingredients List (Name:Qty:Unit)': 'Paneer:120:g, Green Pea:30:g, Tomato:1:pieces, Mustard Oil:5:ml, Turmeric Powder:2:g',
      'Image URL': 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=600&q=80',
      'Instructions': 'Crumble paneer; Saute onions and spices in mustard oil; Add peas and paneer; Serve hot with multi-grain toast.',
    },
    {
      'Recipe Name': 'Oats & Flaxseed Upma',
      'Meal Type': 'Breakfast',
      'Cuisine': 'South Indian',
      'Prep Time (Mins)': 12,
      'Is Vegetarian': 'Yes',
      'Dietary Goals': 'Heart Health, Blood Pressure Control, Fat Loss',
      'Ingredients List (Name:Qty:Unit)': 'Rolled Oats:60:g, Flaxseeds:10:g, Carrot:30:g, Mustard Seeds:2:g, Curry Leaves:5:leaves',
      'Image URL': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80',
      'Instructions': 'Dry roast oats and flaxseeds; Temper mustard seeds; Cook veggies; Add water and oats; Simmer until fluffy.',
    },
  ];

  const worksheet = XLSX.utils.json_to_sheet(sampleData);

  worksheet['!cols'] = [
    { wch: 28 }, // Recipe Name
    { wch: 15 }, // Meal Type
    { wch: 18 }, // Cuisine
    { wch: 18 }, // Prep Time
    { wch: 15 }, // Is Vegetarian
    { wch: 35 }, // Dietary Goals
    { wch: 65 }, // Ingredients List
    { wch: 35 }, // Image URL
    { wch: 50 }, // Instructions
  ];

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Recipe Master');

  XLSX.writeFile(workbook, 'Ai_ki_Rasoi_Recipe_Master_Import_Template.xlsx');
}

export interface RecipeImportResult {
  summary: ImportSummary;
  updatedRecipes: Recipe[];
  autoAddedInventoryItems: InventoryItem[];
}

/**
 * Parses uploaded Recipe Excel sheet.
 * If any ingredient in the new recipes is missing from the Inventory Master,
 * it automatically generates a new InventoryItem in inventory so it's tracked for grocery reorders!
 */
export async function parseAndValidateRecipeExcel(
  file: File,
  currentRecipes: Recipe[],
  currentInventory: InventoryItem[]
): Promise<RecipeImportResult> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];

        const jsonRows: any[] = XLSX.utils.sheet_to_json(worksheet, { defval: '' });

        const errors: ImportValidationError[] = [];
        let importedCount = 0;
        let skippedCount = 0;
        let newCount = 0;
        let updatedCount = 0;

        const recipeMap = new Map<string, Recipe>();
        currentRecipes.forEach((r) => recipeMap.set(r.name.toLowerCase().trim(), { ...r }));

        const inventoryMap = new Map<string, InventoryItem>();
        currentInventory.forEach((inv) => inventoryMap.set(inv.name.toLowerCase().trim(), { ...inv }));

        const autoAddedInventory: InventoryItem[] = [];

        jsonRows.forEach((row, index) => {
          const rowNum = index + 2;
          const recipeNameRaw = row['Recipe Name'] || row['RecipeName'] || row['Name'] || '';
          const recipeName = String(recipeNameRaw).trim();

          if (!recipeName) {
            skippedCount++;
            return;
          }

          const mealTypeRaw = (row['Meal Type'] || row['MealType'] || 'Lunch').trim();
          const mealType: MealType = ['Breakfast', 'Lunch', 'Dinner'].includes(mealTypeRaw)
            ? (mealTypeRaw as MealType)
            : 'Lunch';

          const cuisine = (row['Cuisine'] || 'Indian').trim();
          const prepTimeMinutes = Number(row['Prep Time (Mins)']) || 20;
          const isVegRaw = String(row['Is Vegetarian'] || 'Yes').toLowerCase();
          const isVeg = isVegRaw.startsWith('y') || isVegRaw === 'true';

          const goalsRaw = String(row['Dietary Goals'] || '').split(',');
          const dietaryGoals: HealthGoal[] = goalsRaw
            .map((g) => g.trim())
            .filter((g) =>
              [
                'Muscle Gain',
                'Fat Loss',
                'Cardiovascular Endurance',
                'Heart Health',
                'Blood Pressure Control',
              ].includes(g)
            ) as HealthGoal[];

          const ingredientsListRaw = String(row['Ingredients List (Name:Qty:Unit)'] || row['Ingredients'] || '');
          const parsedIngredients: RecipeIngredient[] = [];

          if (ingredientsListRaw) {
            const ingTokens = ingredientsListRaw.split(',');
            ingTokens.forEach((tok) => {
              const parts = tok.trim().split(':');
              if (parts.length >= 2) {
                const ingName = parts[0].trim();
                const qty = Number(parts[1]) || 1;
                const unitRaw = (parts[2] || 'g').trim() as UnitType;
                const unit: UnitType = SUPPORTED_UNITS.includes(unitRaw) ? unitRaw : 'g';

                if (ingName) {
                  parsedIngredients.push({
                    ingredientName: ingName,
                    category: (getBaseStorageUnit(ingName, 'Other') as any) ? 'Other' : 'Vegetables & Greens',
                    quantityOneFemale: qty,
                    unit: unit,
                  });

                  // REQUIREMENT #4: Check if ingredient exists in inventory master!
                  const ingKey = ingName.toLowerCase();
                  if (!inventoryMap.has(ingKey)) {
                    const baseUnit = getBaseStorageUnit(ingName, 'Other');
                    const newInvItem: InventoryItem = {
                      id: `inv_auto_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
                      name: ingName,
                      category: 'Other',
                      currentQuantity: 0, // Starts at 0 stock so it triggers grocery reorder!
                      baseUnit: baseUnit,
                      minStockLevel: 1.0,
                      lastUpdated: new Date().toISOString(),
                      expiryDate: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
                      imageUrl: 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=400&q=80',
                    };
                    inventoryMap.set(ingKey, newInvItem);
                    autoAddedInventory.push(newInvItem);
                  }
                }
              }
            });
          }

          const imageUrl =
            row['Image URL'] ||
            'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80';

          const instructionsRaw = String(row['Instructions'] || '');
          const instructions = instructionsRaw ? instructionsRaw.split(';').map((s) => s.trim()) : undefined;

          const recipeKey = recipeName.toLowerCase();
          if (recipeMap.has(recipeKey)) {
            updatedCount++;
          } else {
            newCount++;
          }

          const recipeObj: Recipe = {
            id: `rec_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
            name: recipeName,
            mealType,
            cuisine,
            ingredients: parsedIngredients.length > 0 ? parsedIngredients : [
              { ingredientName: 'Salt', category: 'Spices & Seasoning', quantityOneFemale: 2, unit: 'g' }
            ],
            imageUrl,
            isFavorite: false,
            timesPrepared: 0,
            isSeasonal: false,
            prepTimeMinutes,
            isVeg,
            dietaryGoals: dietaryGoals.length > 0 ? dietaryGoals : ['Heart Health'],
            instructions,
          };

          recipeMap.set(recipeKey, recipeObj);
          importedCount++;
        });

        const updatedRecipes = Array.from(recipeMap.values());

        const summary: ImportSummary = {
          totalRows: jsonRows.length,
          importedRows: importedCount,
          skippedRows: skippedCount,
          newIngredientsCount: newCount,
          updatedIngredientsCount: updatedCount,
          errors,
          mode: 'update',
        };

        resolve({ summary, updatedRecipes, autoAddedInventoryItems: autoAddedInventory });
      } catch (err: any) {
        reject(new Error(`Failed to parse recipe Excel file: ${err.message || err}`));
      }
    };

    reader.onerror = () => reject(new Error('File reading error.'));
    reader.readAsArrayBuffer(file);
  });
}
