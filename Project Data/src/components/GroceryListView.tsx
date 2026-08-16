import React, { useState } from 'react';
import {
  ShoppingBag,
  CheckSquare,
  Square,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  RefreshCw,
  Clock,
  Sparkles,
} from 'lucide-react';
import { GroceryItem, IngredientCategory, GroceryPriority, GroceryStatus } from '../types';

interface GroceryListViewProps {
  groceryList: GroceryItem[];
  onMarkPurchased: (ingredientName: string, purchasedQty: number, unit: string) => void;
  onRefreshList: () => void;
}

export const GroceryListView: React.FC<GroceryListViewProps> = ({
  groceryList,
  onMarkPurchased,
  onRefreshList,
}) => {
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});
  const [purchasedQtyMap, setPurchasedQtyMap] = useState<Record<string, number>>({});

  // Group items by Category
  const categoriesMap: Record<string, GroceryItem[]> = {};
  groceryList.forEach((item) => {
    if (!categoriesMap[item.category]) categoriesMap[item.category] = [];
    categoriesMap[item.category].push(item);
  });

  const toggleCategoryCollapse = (cat: string) => {
    setCollapsedCategories((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  const handleQtyChange = (itemId: string, qty: number) => {
    setPurchasedQtyMap((prev) => ({ ...prev, [itemId]: qty }));
  };

  const getPriorityBadge = (priority: GroceryPriority) => {
    switch (priority) {
      case 'Critical':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/20">
            Critical (Out of Stock)
          </span>
        );
      case 'High':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/20">
            High (Below Min Stock)
          </span>
        );
      case 'Medium':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/15 text-blue-700 dark:text-blue-400 border border-blue-500/20">
            Medium (Meal Requirement)
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-500/15 text-slate-700 dark:text-slate-400 border border-slate-500/20">
            Low (Replenishment)
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
            <ShoppingBag className="w-6 h-6 text-orange-500" />
            Smart Grocery Shopping List
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Prioritized requirement calculation • Automatic inventory restock upon purchase
          </p>
        </div>

        <button
          onClick={onRefreshList}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white text-xs font-bold shadow-md shadow-orange-500/20 transition-all"
        >
          <RefreshCw className="w-4 h-4" />
          Re-Calculate Shopping List
        </button>
      </div>

      {groceryList.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-white/70 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800/70 backdrop-blur-md">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            Kitchen Inventory Fully Stocked!
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
            All ingredients for planned meals and minimum stock levels are satisfied.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.keys(categoriesMap).map((category) => {
            const items = categoriesMap[category];
            const isCollapsed = !!collapsedCategories[category];

            return (
              <div
                key={category}
                className="rounded-3xl bg-white/70 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800/70 backdrop-blur-md overflow-hidden shadow-sm"
              >
                {/* Category Group Header */}
                <div
                  onClick={() => toggleCategoryCollapse(category)}
                  className="p-4 bg-slate-100/60 dark:bg-slate-800/60 flex items-center justify-between cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      {category} ({items.length} items)
                    </h3>
                  </div>
                  <button className="text-slate-400">
                    {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                  </button>
                </div>

                {/* Tabular List */}
                {!isCollapsed && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200/60 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/50 text-slate-400 font-semibold uppercase tracking-wider">
                          <th className="py-3 px-4">Item</th>
                          <th className="py-3 px-4">Required Qty</th>
                          <th className="py-3 px-4">Unit</th>
                          <th className="py-3 px-4">Priority</th>
                          <th className="py-3 px-4">Purchased Qty</th>
                          <th className="py-3 px-4 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                        {items.map((item) => {
                          const currentInputQty =
                            purchasedQtyMap[item.id] !== undefined
                              ? purchasedQtyMap[item.id]
                              : item.requiredQuantity;

                          return (
                            <tr
                              key={item.id}
                              className={`transition-colors ${
                                item.purchased
                                  ? 'bg-emerald-500/5 line-through text-slate-400'
                                  : 'hover:bg-slate-50/60 dark:hover:bg-slate-800/40'
                              }`}
                            >
                              {/* Item Name & Reason */}
                              <td className="py-3.5 px-4">
                                <span className="font-bold text-slate-900 dark:text-white block">
                                  {item.ingredientName}
                                </span>
                                {item.reason && (
                                  <span className="text-[10px] text-slate-400 block">
                                    {item.reason}
                                  </span>
                                )}
                              </td>

                              {/* Required Quantity */}
                              <td className="py-3.5 px-4 font-bold text-slate-800 dark:text-slate-200">
                                {item.requiredQuantity}
                              </td>

                              {/* Unit */}
                              <td className="py-3.5 px-4 text-slate-500">{item.baseUnit}</td>

                              {/* Priority */}
                              <td className="py-3.5 px-4">{getPriorityBadge(item.priority)}</td>

                              {/* Purchased Quantity Input */}
                              <td className="py-3.5 px-4">
                                <input
                                  type="number"
                                  step="0.01"
                                  value={currentInputQty}
                                  disabled={item.purchased}
                                  onChange={(e) => handleQtyChange(item.id, Number(e.target.value))}
                                  className="w-20 px-2.5 py-1 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500"
                                />
                              </td>

                              {/* Action Button */}
                              <td className="py-3.5 px-4 text-right">
                                <button
                                  onClick={() =>
                                    onMarkPurchased(item.ingredientName, currentInputQty, item.baseUnit)
                                  }
                                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all"
                                >
                                  Mark Purchased & Restock
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
