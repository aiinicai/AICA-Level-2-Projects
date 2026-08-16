import React, { useState } from 'react';
import { Users, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { MealEntry, Recipe, InventoryItem, ServingsCalcInput } from '../types';
import { convertUnit, formatQuantityWithUnit } from '../services/unitConversionEngine';

interface ServingSizeModalProps {
  mealEntry: MealEntry;
  recipe?: Recipe;
  inventory: InventoryItem[];
  isOpen: boolean;
  onClose: () => void;
  onConfirmPrepare: (mealEntryId: string, servings: ServingsCalcInput) => void;
}

export const ServingSizeModal: React.FC<ServingSizeModalProps> = ({
  mealEntry,
  recipe,
  inventory,
  isOpen,
  onClose,
  onConfirmPrepare,
}) => {
  const [males, setMales] = useState(1);
  const [females, setFemales] = useState(1);
  const [kids, setKids] = useState(0);

  if (!isOpen || !recipe) return null;

  // Multiplier formula: Male = 1.25, Female = 1.0, Kid = 0.75
  const totalMultiplier = males * 1.25 + females * 1.0 + kids * 0.75;

  // Build deduction preview table
  const inventoryMap = new Map<string, InventoryItem>();
  inventory.forEach((i) => inventoryMap.set(i.name.toLowerCase(), i));

  const ingredientDeductions = recipe.ingredients
    .filter((ing) => ing.ingredientName.toLowerCase() !== 'water') // Ignore water
    .map((ing) => {
      const invItem = inventoryMap.get(ing.ingredientName.toLowerCase());
      const baseUnit = invItem ? invItem.baseUnit : ing.unit;
      const requiredQtyInBase = convertUnit(
        ing.quantityOneFemale * totalMultiplier,
        ing.unit,
        baseUnit,
        ing.ingredientName
      );

      const availableQty = invItem ? invItem.currentQuantity : 0;
      const isSufficient = availableQty >= requiredQtyInBase;

      return {
        name: ing.ingredientName,
        requiredQtyInBase,
        baseUnit,
        availableQty,
        isSufficient,
      };
    });

  const hasShortage = ingredientDeductions.some((d) => !d.isSufficient);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirmPrepare(mealEntry.id, { males, females, kids });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-orange-500/10 text-orange-600 dark:text-orange-400">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Serving Calculator
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {recipe.name} ({mealEntry.mealType})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Serving Counters */}
        <div className="grid grid-cols-3 gap-3">
          {/* Males (1.25x) */}
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-center">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Males (1.25×)
            </span>
            <div className="flex items-center justify-center gap-3 mt-2">
              <button
                type="button"
                onClick={() => setMales(Math.max(0, males - 1))}
                className="w-8 h-8 rounded-xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                -
              </button>
              <span className="text-lg font-bold text-slate-900 dark:text-white">
                {males}
              </span>
              <button
                type="button"
                onClick={() => setMales(males + 1)}
                className="w-8 h-8 rounded-xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                +
              </button>
            </div>
          </div>

          {/* Females (1.0x) */}
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-center">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Females (1.0×)
            </span>
            <div className="flex items-center justify-center gap-3 mt-2">
              <button
                type="button"
                onClick={() => setFemales(Math.max(0, females - 1))}
                className="w-8 h-8 rounded-xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                -
              </button>
              <span className="text-lg font-bold text-slate-900 dark:text-white">
                {females}
              </span>
              <button
                type="button"
                onClick={() => setFemales(females + 1)}
                className="w-8 h-8 rounded-xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                +
              </button>
            </div>
          </div>

          {/* Kids (0.75x) */}
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-center">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Kids (0.75×)
            </span>
            <div className="flex items-center justify-center gap-3 mt-2">
              <button
                type="button"
                onClick={() => setKids(Math.max(0, kids - 1))}
                className="w-8 h-8 rounded-xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                -
              </button>
              <span className="text-lg font-bold text-slate-900 dark:text-white">
                {kids}
              </span>
              <button
                type="button"
                onClick={() => setKids(kids + 1)}
                className="w-8 h-8 rounded-xl bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                +
              </button>
            </div>
          </div>
        </div>

        {/* Total Servings Calculation Result */}
        <div className="p-3.5 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-between">
          <span className="text-xs font-semibold text-orange-800 dark:text-orange-300">
            Total Servings Multiplier
          </span>
          <span className="text-base font-bold text-orange-600 dark:text-orange-400">
            {totalMultiplier.toFixed(2)}× Female Servings
          </span>
        </div>

        {/* Ingredient Deduction Preview */}
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
            Required Inventory Deductions
          </h4>
          <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
            {ingredientDeductions.map((d, i) => (
              <div
                key={i}
                className={`flex items-center justify-between p-2.5 rounded-xl border text-xs ${
                  d.isSufficient
                    ? 'bg-slate-50 dark:bg-slate-800/40 border-slate-200/50 dark:border-slate-700/50'
                    : 'bg-rose-50 dark:bg-rose-900/20 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  {d.isSufficient ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-rose-500" />
                  )}
                  <span className="font-medium text-slate-800 dark:text-slate-200">
                    {d.name}
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-slate-900 dark:text-white">
                    -{formatQuantityWithUnit(d.requiredQtyInBase, d.baseUnit)}
                  </span>
                  <span className="text-[10px] text-slate-400 block">
                    Available: {formatQuantityWithUnit(d.availableQty, d.baseUnit)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {hasShortage && (
          <p className="text-[11px] text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 p-2.5 rounded-xl border border-amber-200 dark:border-amber-800">
            <strong>Stock Alert:</strong> Some ingredients have low stock. Deductions will floor at 0.
          </p>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg shadow-orange-500/20 transition-all"
          >
            Mark as Prepared & Deduct
          </button>
        </div>
      </div>
    </div>
  );
};
