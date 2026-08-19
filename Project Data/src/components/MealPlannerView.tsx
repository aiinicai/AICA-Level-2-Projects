import React, { useState } from 'react';
import {
  CalendarDays,
  Sparkles,
  Lock,
  Unlock,
  RefreshCw,
  ShoppingBag,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Replace,
  XCircle,
  Users,
  Leaf,
} from 'lucide-react';
import { WeeklyMealPlan, MealEntry, Recipe, InventoryItem, MealType } from '../types';
import { ServingSizeModal } from './ServingSizeModal';
import { isRecipePureVeg } from '../services/mealPlannerEngine';

interface MealPlannerViewProps {
  mealPlan: WeeklyMealPlan;
  recipes: Recipe[];
  inventory: InventoryItem[];
  isPureVeg: boolean;
  onTogglePureVeg: (val: boolean) => void;
  onRegenerateFullWeek: () => void;
  onRegenerateDay: (dayOfWeek: string) => void;
  onGenerateSingleMeal: (mealEntryId: string) => void;
  onReplaceMeal: (mealEntryId: string, newRecipeId: string) => void;
  onCancelMeal: (mealEntryId: string) => void;
  onToggleLock: () => void;
  onPrepareMeal: (mealEntryId: string, servings: any) => void;
}

export const MealPlannerView: React.FC<MealPlannerViewProps> = ({
  mealPlan,
  recipes,
  inventory,
  isPureVeg,
  onTogglePureVeg,
  onRegenerateFullWeek,
  onRegenerateDay,
  onGenerateSingleMeal,
  onReplaceMeal,
  onCancelMeal,
  onToggleLock,
  onPrepareMeal,
}) => {
  const [selectedMealForPrepare, setSelectedMealForPrepare] = useState<MealEntry | null>(null);
  const [replacingMealId, setReplacingMealId] = useState<string | null>(null);
  const [selectedReplacementRecipeId, setSelectedReplacementRecipeId] = useState<string>('');
  const [singleMealModalOpen, setSingleMealModalOpen] = useState(false);
  const [selectedDayForSingle, setSelectedDayForSingle] = useState<string>('Monday');
  const [selectedTypeForSingle, setSelectedTypeForSingle] = useState<MealType>('Lunch');

  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const MEAL_TYPES: MealType[] = ['Breakfast', 'Lunch', 'Dinner'];

  const getEntryForSlot = (day: string, type: MealType) =>
    mealPlan.entries.find((e) => e.dayOfWeek === day && e.mealType === type);

  const handleConfirmReplace = (mealEntryId: string) => {
    if (!selectedReplacementRecipeId) return;
    onReplaceMeal(mealEntryId, selectedReplacementRecipeId);
    setReplacingMealId(null);
    setSelectedReplacementRecipeId('');
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner & Control Actions */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
              <CalendarDays className="w-6 h-6 text-orange-500" />
              Weekly Intelligent Meal Planner
            </h2>
            {mealPlan.isLocked ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                <Lock className="w-3 h-3" /> Locked
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                <Unlock className="w-3 h-3" /> Editing Enabled
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Optimized for: Expiry Reduction • 14-day Rotation Rule • Seasonal Availability • Existing Stock
          </p>
        </div>

        {/* Buttons Row */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Pure Veg Checkbox */}
          <label className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl border text-xs font-bold cursor-pointer transition-all select-none shadow-sm ${
            isPureVeg
              ? 'bg-emerald-500 text-white border-emerald-500 shadow-emerald-500/20'
              : 'bg-white/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-white'
          }`}>
            <input
              type="checkbox"
              checked={isPureVeg}
              onChange={(e) => onTogglePureVeg(e.target.checked)}
              className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300"
            />
            <Leaf className={`w-4 h-4 ${isPureVeg ? 'text-white' : 'text-emerald-500'}`} />
            <span>Pure Veg Only</span>
          </label>

          <button
            onClick={onToggleLock}
            className={`flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold border transition-all ${
              mealPlan.isLocked
                ? 'bg-amber-500 text-white border-amber-500 hover:bg-amber-600'
                : 'bg-white/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
            }`}
          >
            {mealPlan.isLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
            {mealPlan.isLocked ? 'Unlock Plan' : 'Lock Plan'}
          </button>

          <button
            onClick={onRegenerateFullWeek}
            disabled={mealPlan.isLocked}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white text-xs font-bold shadow-md shadow-orange-500/20 transition-all disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            Generate Full Week Plan
          </button>

          <button
            onClick={() => setSingleMealModalOpen(true)}
            disabled={mealPlan.isLocked}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white text-xs font-bold shadow-md shadow-indigo-500/20 transition-all disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            Generate Single Meal
          </button>
        </div>
      </div>

      {/* Weekly Planner Calendar Table Grid */}
      <div className="space-y-6">
        {DAYS.map((day) => {
          const dayEntries = mealPlan.entries.filter((e) => e.dayOfWeek === day);

          return (
            <div
              key={day}
              className="p-5 rounded-3xl bg-white/70 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800/70 backdrop-blur-md shadow-sm space-y-4"
            >
              {/* Day Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 rounded-full bg-orange-500" />
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    {day}
                  </h3>
                </div>

                <button
                  onClick={() => onRegenerateDay(day)}
                  disabled={mealPlan.isLocked}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 transition-all disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Regenerate {day}
                </button>
              </div>

              {/* 3 Meal Slots (Breakfast, Lunch, Dinner) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {MEAL_TYPES.map((mType) => {
                  const entry = getEntryForSlot(day, mType);
                  const recipe = entry ? recipes.find((r) => r.id === entry.recipeId || r.name === entry.recipeName) : null;

                  if (!entry || !recipe) {
                    return (
                      <div
                        key={mType}
                        className="p-4 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 flex items-center justify-center text-xs text-slate-400"
                      >
                        No meal planned for {mType}
                      </div>
                    );
                  }

                  return (
                    <div
                      key={mType}
                      className={`p-4 rounded-2xl border transition-all duration-300 relative flex flex-col justify-between ${
                        entry.isPrepared
                          ? 'bg-emerald-500/10 border-emerald-500/30'
                          : 'bg-slate-50/80 dark:bg-slate-800/60 border-slate-200/60 dark:border-slate-700/60'
                      }`}
                    >
                      <div>
                        {/* Slot Label & Prepared Badge */}
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400">
                            {mType}
                          </span>
                          {entry.isPrepared ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                              <CheckCircle2 className="w-3 h-3" /> Prepared
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium text-slate-400">
                              {recipe.cuisine}
                            </span>
                          )}
                        </div>

                        {/* Recipe Image & Title */}
                        <div className="flex items-center gap-3 mt-2.5">
                          <img
                            src={recipe.imageUrl}
                            alt={recipe.name}
                            className="w-12 h-12 rounded-xl object-cover border border-slate-200 dark:border-slate-700 shrink-0"
                          />
                          <div>
                            <h4 className="text-xs font-bold text-slate-900 dark:text-white line-clamp-1">
                              {recipe.name}
                            </h4>
                            <span className="text-[10px] text-slate-500 dark:text-slate-400 block">
                              {recipe.ingredients.length} ingredients • {recipe.prepTimeMinutes || 20}m prep
                            </span>
                          </div>
                        </div>

                        {/* 14-Day Rotation Warning Badge */}
                        {entry.rotationWarning && (
                          <div className="mt-2 p-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 text-[10px] text-amber-800 dark:text-amber-300 flex items-start gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-500 mt-0.5" />
                            <span>{entry.rotationWarning}</span>
                          </div>
                        )}
                      </div>

                      {/* Action Buttons Footer */}
                      <div className="mt-4 pt-3 border-t border-slate-200/50 dark:border-slate-700/50 flex items-center justify-between">
                        {!entry.isPrepared ? (
                          <button
                            onClick={() => setSelectedMealForPrepare(entry)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white text-[11px] font-bold shadow-md transition-all"
                          >
                            <Users className="w-3.5 h-3.5" />
                            Mark as Prepared
                          </button>
                        ) : (
                          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                            Deducted for {entry.totalServingsMultiplier?.toFixed(1)}x servings
                          </span>
                        )}

                        {!entry.isPrepared && !mealPlan.isLocked && (
                          <div className="flex items-center gap-1">
                            {/* Generate Single Meal button */}
                            <button
                              onClick={() => onGenerateSingleMeal(entry.id)}
                              title="Generate Single Meal"
                              className="p-1.5 rounded-lg text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 flex items-center gap-1 text-[10px] font-bold"
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                              Single Meal
                            </button>
                            {/* Replace Recipe button */}
                            <button
                              onClick={() => setReplacingMealId(entry.id)}
                              title="Select Specific Recipe"
                              className="p-1.5 rounded-lg text-slate-500 hover:text-orange-600 hover:bg-slate-200/60 dark:hover:bg-slate-700"
                            >
                              <Replace className="w-3.5 h-3.5" />
                            </button>
                            {/* Cancel Meal button */}
                            <button
                              onClick={() => onCancelMeal(entry.id)}
                              title="Cancel Meal"
                              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-slate-200/60 dark:hover:bg-slate-700"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Serving Calculator Modal */}
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

      {/* Replace Single Recipe Modal */}
      {replacingMealId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Replace Recipe in Meal Slot
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Select an alternative recipe from the master database:
            </p>

            <select
              value={selectedReplacementRecipeId}
              onChange={(e) => setSelectedReplacementRecipeId(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="">-- Choose Replacement Recipe --</option>
              {(isPureVeg ? recipes.filter(isRecipePureVeg) : recipes).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.mealType} • {r.cuisine})
                </option>
              ))}
            </select>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => setReplacingMealId(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={() => handleConfirmReplace(replacingMealId)}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-orange-500 hover:bg-orange-600 text-white shadow-md"
              >
                Confirm Replacement
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generate Single Meal Slot Picker Modal */}
      {singleMealModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Generate Single Meal
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Pick a specific day and meal slot to generate an AI-recommended recipe!
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Day of the Week
                </label>
                <select
                  value={selectedDayForSingle}
                  onChange={(e) => setSelectedDayForSingle(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {DAYS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Meal Type
                </label>
                <select
                  value={selectedTypeForSingle}
                  onChange={(e) => setSelectedTypeForSingle(e.target.value as MealType)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {MEAL_TYPES.map((mt) => (
                    <option key={mt} value={mt}>
                      {mt}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => setSingleMealModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const targetEntry = mealPlan.entries.find(
                    (e) => e.dayOfWeek === selectedDayForSingle && e.mealType === selectedTypeForSingle
                  );
                  if (targetEntry) {
                    onGenerateSingleMeal(targetEntry.id);
                  }
                  setSingleMealModalOpen(false);
                }}
                className="px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-md shadow-indigo-500/20"
              >
                Generate Meal Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
