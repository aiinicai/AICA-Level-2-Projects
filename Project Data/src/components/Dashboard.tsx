import React, { useState } from 'react';
import {
  UtensilsCrossed,
  Package,
  CalendarDays,
  ShoppingBag,
  AlertTriangle,
  Clock,
  CheckCircle2,
  TrendingUp,
  Plus,
  Flame,
  Activity,
  Droplets,
  Leaf,
  Sparkles,
  Check,
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';
import { InventoryItem, Recipe, WeeklyMealPlan, GroceryItem, MealEntry } from '../types';
import { ServingSizeModal } from './ServingSizeModal';
import { Logo } from './Logo';

interface DashboardProps {
  inventory: InventoryItem[];
  recipes: Recipe[];
  mealPlan: WeeklyMealPlan;
  groceryList: GroceryItem[];
  onPrepareMeal: (mealEntryId: string, servings: any) => void;
  onNavigateTab: (tab: string) => void;
}

interface PrepItem {
  id: string;
  foodName: string;
  prepAction: string;
  timeframe: string;
  recipeName: string;
}

function getAdvancePrepTasks(mealPlan: WeeklyMealPlan, recipes: Recipe[]): PrepItem[] {
  const today = new Date();
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const todayName = dayNames[today.getDay()];
  const tomorrowName = dayNames[(today.getDay() + 1) % 7];

  const relevantEntries = mealPlan.entries.filter(
    (e) => e.dayOfWeek === todayName || e.dayOfWeek === tomorrowName
  );

  const prepList: PrepItem[] = [];

  relevantEntries.forEach((entry) => {
    const recipe = recipes.find((r) => r.id === entry.recipeId || r.name === entry.recipeName);
    if (!recipe) return;

    const rName = recipe.name.toLowerCase();
    const isTomorrow = entry.dayOfWeek === tomorrowName;
    const whenText = isTomorrow ? `Tomorrow (${entry.mealType})` : `Today (${entry.mealType})`;

    const ingNames = recipe.ingredients.map((i) => i.ingredientName.toLowerCase());

    if (rName.includes('sabudana') || ingNames.some((i) => i.includes('sabudana'))) {
      prepList.push({
        id: `prep_sabudana_${entry.id}`,
        foodName: 'Sabudana (Tapioca Pearls)',
        prepAction: 'Soak in equal volume water for 4–6 hours',
        timeframe: whenText,
        recipeName: recipe.name,
      });
    }

    if (
      rName.includes('chana') ||
      rName.includes('chole') ||
      rName.includes('rajma') ||
      ingNames.some((i) => i.includes('chana') || i.includes('rajma') || i.includes('chickpeas'))
    ) {
      prepList.push({
        id: `prep_chana_${entry.id}`,
        foodName: 'Kabuli Chana / Rajma / Chickpeas',
        prepAction: 'Soak in water overnight (8–10 hours)',
        timeframe: whenText,
        recipeName: recipe.name,
      });
    }

    if (
      rName.includes('dosa') ||
      rName.includes('idli') ||
      rName.includes('dhokla') ||
      rName.includes('appam')
    ) {
      prepList.push({
        id: `prep_ferment_${entry.id}`,
        foodName: 'Rice & Urad Dal Batter',
        prepAction: 'Grind & ferment batter overnight at warm room temp',
        timeframe: whenText,
        recipeName: recipe.name,
      });
    }

    if (rName.includes('paneer') || ingNames.some((i) => i.includes('paneer'))) {
      prepList.push({
        id: `prep_paneer_${entry.id}`,
        foodName: 'Paneer Cubes',
        prepAction: 'Marinate in curd, turmeric & kitchen spices for 30 mins',
        timeframe: whenText,
        recipeName: recipe.name,
      });
    }

    if (
      rName.includes('moong') ||
      rName.includes('dal makhani') ||
      ingNames.some((i) => i.includes('moong dal') || i.includes('urad dal'))
    ) {
      prepList.push({
        id: `prep_moong_${entry.id}`,
        foodName: 'Moong Dal / Whole Lentils',
        prepAction: 'Soak Moong / Lentils in water for 3–4 hours before cooking',
        timeframe: whenText,
        recipeName: recipe.name,
      });
    }

    if (rName.includes('sprout') || ingNames.some((i) => i.includes('sprout'))) {
      prepList.push({
        id: `prep_sprout_${entry.id}`,
        foodName: 'Whole Moong / Chana Sprouts',
        prepAction: 'Moisten and wrap in damp cotton cloth to sprout (12 hrs)',
        timeframe: whenText,
        recipeName: recipe.name,
      });
    }
  });

  // Default fallback prep reminders
  if (prepList.length === 0) {
    prepList.push(
      {
        id: 'prep_def_1',
        foodName: 'Sabudana (Tapioca)',
        prepAction: 'Soak in water (4–6 hours) before Khichdi / Vada',
        timeframe: 'General Reminder',
        recipeName: 'Sabudana Khichdi',
      },
      {
        id: 'prep_def_2',
        foodName: 'Rajma & Kabuli Chana',
        prepAction: 'Soak overnight (8–10 hrs) with pinch of baking soda',
        timeframe: 'General Reminder',
        recipeName: 'Rajma Masala / Chole',
      },
      {
        id: 'prep_def_3',
        foodName: 'Moong Dal / Chana Dal',
        prepAction: 'Soak 3–4 hours prior to grinding or boiling',
        timeframe: 'General Reminder',
        recipeName: 'Moong Dal Halwa / Chilla',
      }
    );
  }

  const uniqueMap = new Map<string, PrepItem>();
  prepList.forEach((p) => {
    if (!uniqueMap.has(p.foodName)) {
      uniqueMap.set(p.foodName, p);
    }
  });

  return Array.from(uniqueMap.values());
}

export const Dashboard: React.FC<DashboardProps> = ({
  inventory,
  recipes,
  mealPlan,
  groceryList,
  onPrepareMeal,
  onNavigateTab,
}) => {
  const [selectedMealForPrepare, setSelectedMealForPrepare] = useState<MealEntry | null>(null);
  const [completedPreps, setCompletedPreps] = useState<Record<string, boolean>>({});

  const today = new Date();
  const todayDayName = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][
    today.getDay()
  ];

  // Get Today's planned meals
  const todaysMeals = mealPlan.entries.filter((e) => e.dayOfWeek === todayDayName);

  // Low stock items
  const lowStockItems = inventory.filter((i) => i.currentQuantity <= i.minStockLevel);

  // Advance prep tasks
  const prepTasks = getAdvancePrepTasks(mealPlan, recipes);

  const togglePrepDone = (id: string) => {
    setCompletedPreps((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Calculate today's estimated nutrition from planned meals
  const todayNutrition = todaysMeals.reduce(
    (acc, meal) => {
      const recipe = recipes.find((r) => r.id === meal.recipeId || r.name === meal.recipeName);
      if (!recipe) return acc;

      let cal = 450;
      let prot = 16;
      let carb = 62;
      let fat = 14;
      let fib = 7;

      if (meal.mealType === 'Breakfast') {
        cal = 380;
        prot = 14;
        carb = 54;
        fat = 12;
        fib = 6;
      } else if (meal.mealType === 'Lunch') {
        cal = 650;
        prot = 26;
        carb = 88;
        fat = 18;
        fib = 11;
      } else if (meal.mealType === 'Dinner') {
        cal = 580;
        prot = 22;
        carb = 76;
        fat = 15;
        fib = 9;
      }

      return {
        calories: acc.calories + cal,
        protein: acc.protein + prot,
        carbs: acc.carbs + carb,
        fat: acc.fat + fat,
        fiber: acc.fiber + fib,
      };
    },
    { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 }
  );

  const targets = {
    calories: 2000,
    protein: 75,
    carbs: 250,
    fat: 60,
    fiber: 30,
  };

  // Chart data for Macro breakdown
  const macroChartData = [
    { name: 'Protein', value: todayNutrition.protein * 4, color: '#10b981' },
    { name: 'Carbs', value: todayNutrition.carbs * 4, color: '#3b82f6' },
    { name: 'Healthy Fats', value: todayNutrition.fat * 9, color: '#f59e0b' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Banner */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <Logo size="lg" showSubtitle={true} />
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateTab('inventory')}
            className="flex items-center gap-2 bg-white/80 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 px-4 py-2.5 rounded-xl text-xs font-semibold hover:bg-white dark:hover:bg-slate-700 transition-all text-slate-700 dark:text-slate-200 shadow-sm"
          >
            <Package className="w-4 h-4" />
            Import Inventory
          </button>
          <button
            onClick={() => onNavigateTab('mealplanner')}
            className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-md shadow-orange-500/20"
          >
            <CalendarDays className="w-4 h-4" />
            Weekly Meal Plan
          </button>
        </div>
      </div>

      {/* Main Top Bento Row: Today's Menu (8 Cols) & Critical Stock (4 Cols) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Today's Menu Bento Box (8 Cols) */}
        <div className="md:col-span-8 backdrop-blur-md bg-white/70 dark:bg-slate-900/70 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                  Today's Scheduled Menu ({todayDayName})
                </h3>
                <p className="text-xs text-slate-400">Automated ingredient allocation and portioning</p>
              </div>
              <span className="text-xs font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 px-3 py-1 rounded-full border border-emerald-200/50">
                Inventory Optimized
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              {['Breakfast', 'Lunch', 'Dinner'].map((mType) => {
                const entry = todaysMeals.find((m) => m.mealType === mType);
                const recipe = entry
                  ? recipes.find((r) => r.id === entry.recipeId || r.name === entry.recipeName)
                  : null;

                if (!entry || !recipe) {
                  return (
                    <div
                      key={mType}
                      className="p-4 bg-white/80 dark:bg-slate-800/80 border border-slate-100 dark:border-slate-700/60 rounded-2xl shadow-sm flex flex-col justify-between text-center min-h-[160px]"
                    >
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{mType}</p>
                      <p className="text-xs text-slate-400 italic my-auto">No recipe assigned</p>
                      <button
                        onClick={() => onNavigateTab('mealplanner')}
                        className="text-[10px] font-bold text-orange-500 hover:underline"
                      >
                        + Add Meal
                      </button>
                    </div>
                  );
                }

                return (
                  <div
                    key={mType}
                    className={`p-3.5 rounded-2xl border transition-all flex flex-col justify-between ${
                      entry.isPrepared
                        ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/50'
                        : 'bg-white/90 dark:bg-slate-800/90 border-slate-200/80 dark:border-slate-700/80 border-t-4 border-t-orange-500 shadow-sm'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <p className="text-[10px] font-bold text-orange-600 dark:text-orange-400 uppercase tracking-widest">{mType}</p>
                        {entry.isPrepared && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                      </div>

                      {/* Recipe Photo Image */}
                      <div className="relative h-28 w-full rounded-xl overflow-hidden mb-2.5 border border-slate-200/60 dark:border-slate-700/60 shadow-2xs group">
                        <img
                          src={recipe.imageUrl}
                          alt={recipe.name}
                          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/70 via-transparent to-transparent" />
                        <span className="absolute bottom-1.5 left-2 text-[10px] font-bold text-white drop-shadow-sm">
                          {recipe.cuisine} • {recipe.prepTimeMinutes || 20}m prep
                        </span>
                      </div>

                      <p className="font-bold text-xs leading-tight text-slate-800 dark:text-slate-100 line-clamp-1">
                        {recipe.name}
                      </p>
                    </div>

                    <div className="mt-3">
                      {entry.isPrepared ? (
                        <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 block text-center py-1 bg-emerald-100/60 dark:bg-emerald-900/40 rounded-lg">
                          Prepared & Deducted
                        </span>
                      ) : (
                        <button
                          onClick={() => setSelectedMealForPrepare(entry)}
                          className="w-full py-1.5 bg-orange-500 hover:bg-orange-600 text-white text-[11px] font-bold rounded-xl shadow-md shadow-orange-500/20 transition-all"
                        >
                          Mark Prepared
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Critical Stock Bento Box (4 Cols) */}
        <div className="md:col-span-4 backdrop-blur-md bg-rose-50/60 dark:bg-rose-950/30 border border-rose-100 dark:border-rose-900/50 p-5 rounded-3xl shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
                <AlertTriangle className="w-4 h-4" />
                <h3 className="text-xs font-bold uppercase tracking-wider">Critical Stock Alerts</h3>
              </div>
              <span className="text-[10px] font-bold bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 px-2 py-0.5 rounded-full">
                {lowStockItems.length} Low
              </span>
            </div>

            <div className="space-y-2.5 max-h-[210px] overflow-y-auto pr-1">
              {lowStockItems.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-500 bg-white/60 dark:bg-slate-800/60 rounded-2xl">
                  All inventory levels are healthy!
                </div>
              ) : (
                lowStockItems.slice(0, 4).map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-3 bg-white/80 dark:bg-slate-800/80 rounded-2xl border border-rose-200/80 dark:border-rose-900/60 text-xs shadow-xs"
                  >
                    <div>
                      <p className="font-bold text-slate-800 dark:text-slate-200 text-xs line-clamp-1">
                        {item.name}
                      </p>
                      <p className="text-[10px] text-rose-600 dark:text-rose-400 font-medium mt-0.5">
                        Stock: <span className="font-bold">{item.currentQuantity} {item.baseUnit}</span> (Min Threshold: {item.minStockLevel} {item.baseUnit})
                      </p>
                    </div>
                    <button
                      onClick={() => onNavigateTab('grocery')}
                      className="p-2 bg-rose-500 text-white rounded-xl hover:bg-rose-600 transition-colors shadow-xs"
                      title="Add reorder to Grocery List"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <button
            onClick={() => onNavigateTab('grocery')}
            className="mt-4 w-full py-2.5 bg-rose-500 hover:bg-rose-600 text-white rounded-xl text-xs font-bold shadow-md shadow-rose-500/20 transition-all flex items-center justify-center gap-2"
          >
            <ShoppingBag className="w-4 h-4" />
            View Full Grocery Shopping List
          </button>
        </div>
      </div>

      {/* Bottom Bento Row: Advance Prep & Reminders (5 Cols) + Nutritional Stats & Goals (7 Cols) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Advance Prep & Reminders Tile (5 Cols) */}
        <div className="md:col-span-5 backdrop-blur-md bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 p-5 rounded-3xl shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                <Clock className="w-4 h-4" />
                <h3 className="text-xs font-bold uppercase tracking-wider">Advance Kitchen Prep & Reminders</h3>
              </div>
              <span className="text-[10px] font-bold bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded-full">
                Soaking & Fermenting
              </span>
            </div>

            <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
              {prepTasks.map((task) => {
                const isDone = !!completedPreps[task.id];
                return (
                  <div
                    key={task.id}
                    onClick={() => togglePrepDone(task.id)}
                    className={`p-3 rounded-2xl border cursor-pointer transition-all flex items-start gap-3 ${
                      isDone
                        ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/50 opacity-80'
                        : 'bg-white/90 dark:bg-slate-800/90 border-amber-200/70 dark:border-amber-900/50 hover:border-amber-400'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-lg border mt-0.5 flex items-center justify-center shrink-0 transition-all ${
                        isDone
                          ? 'bg-emerald-500 border-emerald-500 text-white'
                          : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700'
                      }`}
                    >
                      {isDone && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>

                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-bold ${isDone ? 'line-through text-slate-400' : 'text-slate-800 dark:text-slate-100'}`}>
                          {task.foodName}
                        </span>
                        <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-100/60 dark:bg-amber-900/40 px-2 py-0.5 rounded-md">
                          {task.timeframe}
                        </span>
                      </div>
                      <p className={`text-[11px] mt-0.5 ${isDone ? 'line-through text-slate-400' : 'text-slate-600 dark:text-slate-300'}`}>
                        {task.prepAction}
                      </p>
                      <span className="text-[10px] text-slate-400 italic mt-1 block">
                        For: {task.recipeName}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 p-2.5 bg-amber-100/60 dark:bg-amber-900/30 rounded-xl text-[11px] text-amber-800 dark:text-amber-300 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            <span>Timely soaking improves bioavailability, digestability & cooking speed!</span>
          </div>
        </div>

        {/* Nutritional Stats & Goals Tile (7 Cols) */}
        <div className="md:col-span-7 backdrop-blur-md bg-white/70 dark:bg-slate-900/70 border border-white/80 dark:border-slate-800/80 p-5 rounded-3xl shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  Nutritional Stats & Daily Goals
                </h3>
                <p className="text-[11px] text-slate-400">Derived from today's scheduled meals</p>
              </div>
              <span className="text-xs font-bold bg-orange-100 dark:bg-orange-950/60 text-orange-700 dark:text-orange-300 px-3 py-1 rounded-full">
                {todayNutrition.calories} / {targets.calories} kcal
              </span>
            </div>

            {/* Macro Goals Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              {/* Protein */}
              <div className="p-3 rounded-2xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900/50">
                <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider block">
                  Protein
                </span>
                <p className="text-lg font-black text-slate-800 dark:text-slate-100 mt-0.5">
                  {todayNutrition.protein}g{' '}
                  <span className="text-[10px] font-normal text-slate-400">/ {targets.protein}g</span>
                </p>
                <div className="w-full h-1.5 bg-emerald-200 dark:bg-emerald-900 rounded-full mt-2 overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${Math.min(100, (todayNutrition.protein / targets.protein) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Carbs */}
              <div className="p-3 rounded-2xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/50">
                <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider block">
                  Carbohydrates
                </span>
                <p className="text-lg font-black text-slate-800 dark:text-slate-100 mt-0.5">
                  {todayNutrition.carbs}g{' '}
                  <span className="text-[10px] font-normal text-slate-400">/ {targets.carbs}g</span>
                </p>
                <div className="w-full h-1.5 bg-blue-200 dark:bg-blue-900 rounded-full mt-2 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${Math.min(100, (todayNutrition.carbs / targets.carbs) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Healthy Fats */}
              <div className="p-3 rounded-2xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-900/50">
                <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider block">
                  Healthy Fats
                </span>
                <p className="text-lg font-black text-slate-800 dark:text-slate-100 mt-0.5">
                  {todayNutrition.fat}g{' '}
                  <span className="text-[10px] font-normal text-slate-400">/ {targets.fat}g</span>
                </p>
                <div className="w-full h-1.5 bg-amber-200 dark:bg-amber-900 rounded-full mt-2 overflow-hidden">
                  <div
                    className="h-full bg-amber-500 rounded-full"
                    style={{ width: `${Math.min(100, (todayNutrition.fat / targets.fat) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Dietary Fiber */}
              <div className="p-3 rounded-2xl bg-purple-50/70 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-900/50">
                <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400 uppercase tracking-wider block">
                  Dietary Fiber
                </span>
                <p className="text-lg font-black text-slate-800 dark:text-slate-100 mt-0.5">
                  {todayNutrition.fiber}g{' '}
                  <span className="text-[10px] font-normal text-slate-400">/ {targets.fiber}g</span>
                </p>
                <div className="w-full h-1.5 bg-purple-200 dark:bg-purple-900 rounded-full mt-2 overflow-hidden">
                  <div
                    className="h-full bg-purple-500 rounded-full"
                    style={{ width: `${Math.min(100, (todayNutrition.fiber / targets.fiber) * 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Macro Distribution Stack Bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span className="font-semibold">Macro Caloric Split</span>
                <div className="flex gap-3 text-[10px] font-bold">
                  <span className="text-emerald-600 dark:text-emerald-400">● Protein 20%</span>
                  <span className="text-blue-600 dark:text-blue-400">● Carbs 55%</span>
                  <span className="text-amber-600 dark:text-amber-400">● Fats 25%</span>
                </div>
              </div>
              <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
                <div className="h-full bg-emerald-500" style={{ width: '20%' }} title="Protein" />
                <div className="h-full bg-blue-500" style={{ width: '55%' }} title="Carbs" />
                <div className="h-full bg-amber-500" style={{ width: '25%' }} title="Fats" />
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1.5 font-medium">
              <Leaf className="w-3.5 h-3.5 text-emerald-500" />
              Balanced Whole-Food Plant Nutrition
            </span>
            <span className="font-bold text-slate-700 dark:text-slate-300">
              Goal Progress: {Math.round((todayNutrition.calories / targets.calories) * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Serving Size Modal */}
      {selectedMealForPrepare && (
        <ServingSizeModal
          mealEntry={selectedMealForPrepare}
          recipe={recipes.find(
            (r) => r.id === selectedMealForPrepare.recipeId || r.name === selectedMealForPrepare.recipeName
          )}
          inventory={inventory}
          isOpen={!!selectedMealForPrepare}
          onClose={() => setSelectedMealForPrepare(null)}
          onConfirmPrepare={onPrepareMeal}
        />
      )}
    </div>
  );
};
