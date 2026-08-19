import React, { useState } from 'react';
import {
  Package,
  Plus,
  Minus,
  AlertTriangle,
  Clock,
  Download,
  Upload,
  ShoppingBag,
  Search,
  Trash2,
  Edit,
  Sparkles,
  ChevronRight,
  X,
} from 'lucide-react';
import { InventoryItem, IngredientCategory, UnitType } from '../types';
import { downloadSampleExcelTemplate } from '../services/excelService';
import { BulkImportModal } from './BulkImportModal';
import { formatQuantityWithUnit } from '../services/unitConversionEngine';

interface InventoryManagerProps {
  inventory: InventoryItem[];
  onUpdateQuantity: (id: string, delta: number) => void;
  onAddItem: (item: InventoryItem) => void;
  onEditItem: (item: InventoryItem) => void;
  onDeleteItem: (id: string) => void;
  onNavigateToGrocery: () => void;
  onImportSuccess: (updatedInventory: InventoryItem[]) => void;
}

const CATEGORIES: IngredientCategory[] = [
  'Vegetables & Greens',
  'Grains & Pulses',
  'Dairy & Refrigerated',
  'Spices & Seasoning',
  'Flours & Atta',
  'Oils & Ghee',
  'Fruits',
  'Nuts & Seeds',
  'Condiments & Sauce',
  'Bakery & Snacks',
  'Beverages',
];

export const InventoryManager: React.FC<InventoryManagerProps> = ({
  inventory,
  onUpdateQuantity,
  onAddItem,
  onEditItem,
  onDeleteItem,
  onNavigateToGrocery,
  onImportSuccess,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<IngredientCategory | 'All'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);

  // New item form state
  const [formName, setFormName] = useState('');
  const [formCategory, setFormCategory] = useState<IngredientCategory>('Vegetables & Greens');
  const [formQty, setFormQty] = useState('1.0');
  const [formUnit, setFormUnit] = useState<UnitType>('kg');
  const [formMinStock, setFormMinStock] = useState('0.5');

  const today = new Date();

  // Filter inventory
  const filteredInventory = inventory.filter((item) => {
    const matchesCategory = selectedCategory === 'All' || item.category === selectedCategory;
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Calculate category stats
  const getCategoryCount = (cat: IngredientCategory) =>
    inventory.filter((i) => i.category === cat).length;

  const lowStockItems = inventory.filter((i) => i.currentQuantity <= i.minStockLevel);
  const expiringSoonItems = inventory.filter((i) => {
    if (!i.expiryDate) return false;
    const days = Math.ceil((new Date(i.expiryDate).getTime() - today.getTime()) / (1000 * 3600 * 24));
    return days >= 0 && days <= 5;
  });

  const handleOpenAddModal = (itemToEdit?: InventoryItem) => {
    if (itemToEdit) {
      setEditingItem(itemToEdit);
      setFormName(itemToEdit.name);
      setFormCategory(itemToEdit.category);
      setFormQty(String(itemToEdit.currentQuantity));
      setFormUnit(itemToEdit.baseUnit);
      setFormMinStock(String(itemToEdit.minStockLevel));
    } else {
      setEditingItem(null);
      setFormName('');
      setFormCategory('Vegetables & Greens');
      setFormQty('1.0');
      setFormUnit('kg');
      setFormMinStock('0.5');
    }
    setIsAddModalOpen(true);
  };

  const handleSaveForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    if (editingItem) {
      onEditItem({
        ...editingItem,
        name: formName,
        category: formCategory,
        currentQuantity: Number(formQty) || 0,
        baseUnit: formUnit,
        minStockLevel: Number(formMinStock) || 0,
        lastUpdated: new Date().toISOString(),
      });
    } else {
      onAddItem({
        id: `inv_${Date.now()}`,
        name: formName,
        category: formCategory,
        currentQuantity: Number(formQty) || 0,
        baseUnit: formUnit,
        minStockLevel: Number(formMinStock) || 0,
        lastUpdated: new Date().toISOString(),
        expiryDate: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0],
        imageUrl: 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=400&q=80',
      });
    }
    setIsAddModalOpen(false);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner & Action Controls */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
            <Package className="w-6 h-6 text-orange-500" />
            Kitchen Inventory Master
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time stock control, organized bento categories, and automated reorder alerts
          </p>
        </div>

        {/* Buttons Row */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-500/20 transition-all"
          >
            <Upload className="w-4 h-4" />
            Import Opening Inventory
          </button>

          <button
            onClick={downloadSampleExcelTemplate}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-white/80 dark:bg-slate-800 hover:bg-white text-slate-700 dark:text-slate-300 text-xs font-bold border border-slate-200 dark:border-slate-700 transition-all shadow-sm"
          >
            <Download className="w-4 h-4" />
            Download Sample Template
          </button>

          <button
            onClick={() => handleOpenAddModal()}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-xs font-bold hover:opacity-90 transition-all shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Add Item
          </button>
        </div>
      </div>

      {/* Glassmorphic Category Rectangles */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Stock Categories
          </h3>
          <button
            onClick={() => setSelectedCategory('All')}
            className={`text-xs font-semibold ${
              selectedCategory === 'All'
                ? 'text-orange-600 dark:text-orange-400 font-bold'
                : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Show All ({inventory.length})
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {CATEGORIES.map((cat) => {
            const count = getCategoryCount(cat);
            const isSelected = selectedCategory === cat;
            return (
              <div
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`cursor-pointer p-4 rounded-2xl border transition-all duration-300 relative overflow-hidden backdrop-blur-md ${
                  isSelected
                    ? 'bg-orange-500/20 border-orange-500 shadow-xl ring-2 ring-orange-500/30'
                    : 'bg-white/60 dark:bg-slate-900/60 border-slate-200/60 dark:border-slate-800/60 hover:border-orange-300 dark:hover:border-slate-700 shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200 line-clamp-1">
                    {cat}
                  </span>
                  <ChevronRight className={`w-3.5 h-3.5 ${isSelected ? 'text-orange-500' : 'text-slate-400'}`} />
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  <span>{count} items</span>
                  {count > 0 && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Search & Filter bar */}
      <div className="flex items-center justify-between gap-4 bg-white/80 dark:bg-slate-900/80 p-3 rounded-2xl border border-slate-200/60 dark:border-slate-800/60 backdrop-blur-md">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search ingredients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl text-xs bg-slate-100/70 dark:bg-slate-800/70 text-slate-900 dark:text-white border-0 focus:ring-2 focus:ring-orange-500 outline-none"
          />
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Showing <strong>{filteredInventory.length}</strong> items
        </div>
      </div>

      {/* Ingredient Items Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {filteredInventory.map((item) => {
          const isLowStock = item.currentQuantity <= item.minStockLevel;
          const isExpiringSoon =
            item.expiryDate &&
            Math.ceil((new Date(item.expiryDate).getTime() - today.getTime()) / (1000 * 3600 * 24)) <= 5;

          return (
            <div
              key={item.id}
              className={`p-4 rounded-3xl border transition-all duration-300 relative bg-white/70 dark:bg-slate-900/70 backdrop-blur-md shadow-sm hover:shadow-md ${
                isLowStock
                  ? 'border-amber-300 dark:border-amber-800/60 bg-amber-50/20 dark:bg-amber-950/20'
                  : 'border-slate-200/70 dark:border-slate-800/70'
              }`}
            >
              {/* Item Top Row */}
              <div className="flex items-start gap-3">
                <img
                  src={item.imageUrl}
                  alt={item.name}
                  className="w-12 h-12 rounded-2xl object-cover bg-slate-100 dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700/60 shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white truncate">
                    {item.name}
                  </h4>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 block truncate">
                    {item.category}
                  </span>

                  {/* Status Badges */}
                  <div className="flex flex-wrap items-center gap-1 mt-1.5">
                    {isLowStock && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                        <AlertTriangle className="w-2.5 h-2.5" /> Low Stock
                      </span>
                    )}
                    {isExpiringSoon && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/20">
                        <Clock className="w-2.5 h-2.5" /> Expiring Soon
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Quantity Controls Row */}
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                    Current Qty
                  </span>
                  <span className="text-sm font-bold text-slate-900 dark:text-white">
                    {formatQuantityWithUnit(item.currentQuantity, item.baseUnit)}
                  </span>
                </div>

                {/* Plus & Minus Buttons */}
                <div className="flex items-center gap-1.5 bg-slate-100/80 dark:bg-slate-800/80 p-1 rounded-2xl border border-slate-200/50 dark:border-slate-700/50">
                  <button
                    onClick={() => onUpdateQuantity(item.id, -0.25)}
                    className="w-7 h-7 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white flex items-center justify-center font-bold text-xs hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors shadow-2xs"
                  >
                    <Minus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => onUpdateQuantity(item.id, 0.25)}
                    className="w-7 h-7 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white flex items-center justify-center font-bold text-xs hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors shadow-2xs"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="mt-2.5 flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-100/60 dark:border-slate-800/40">
                <span>Min: {item.minStockLevel} {item.baseUnit}</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleOpenAddModal(item)}
                    className="p-1 hover:text-orange-500 transition-colors"
                  >
                    <Edit className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => onDeleteItem(item.id)}
                    className="p-1 hover:text-rose-500 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bulk Import Modal */}
      <BulkImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        inventory={inventory}
        onImportSuccess={(updatedInv) => {
          onImportSuccess(updatedInv);
          setIsImportModalOpen(false);
        }}
      />

      {/* Add / Edit Item Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <form
            onSubmit={handleSaveForm}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                {editingItem ? 'Edit Ingredient' : 'Add New Ingredient'}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Ingredient Name
              </label>
              <input
                type="text"
                required
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Category
              </label>
              <select
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value as IngredientCategory)}
                className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Current Quantity
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={formQty}
                  onChange={(e) => setFormQty(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Base Storage Unit
                </label>
                <select
                  value={formUnit}
                  onChange={(e) => setFormUnit(e.target.value as UnitType)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="kg">kg</option>
                  <option value="g">g</option>
                  <option value="L">L</option>
                  <option value="ml">ml</option>
                  <option value="pieces">pieces</option>
                  <option value="packets">packets</option>
                  <option value="bottles">bottles</option>
                  <option value="cans">cans</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                Reorder Level (Minimum Stock)
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={formMinStock}
                onChange={(e) => setFormMinStock(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-orange-500 hover:bg-orange-600 text-white shadow-md"
              >
                Save Ingredient
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
