import React, { useState, useEffect } from 'react';
import {
  Package,
  Plus,
  Search,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Percent,
  Layers,
  Fuel,
  Truck,
  Filter,
  DollarSign,
  Info,
  Check,
  X
} from 'lucide-react';
import { ItemMaster, VatRule } from '../../types';
import { StorageService } from '../../services/storage';

export const ManageProductsView: React.FC = () => {
  const storage = StorageService.getInstance();
  const currentUser = storage.getCurrentUser();
  const companyProfile = storage.getCompanyProfile();

  const [products, setProducts] = useState<ItemMaster[]>(storage.getItemCatalog());
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [vatRuleFilter, setVatRuleFilter] = useState<string>('all');

  // Modal / Form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ItemMaster | null>(null);

  const [name, setName] = useState('');
  const [category, setCategory] = useState<ItemMaster['category']>('Bitumen');
  const [unit, setUnit] = useState('MT');
  const [standardRate, setStandardRate] = useState<number>(1000000);
  const [vatRule, setVatRule] = useState<VatRule>('optional');
  const [defaultVatPercent, setDefaultVatPercent] = useState<number>(18);
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);

  const refreshProducts = () => {
    setProducts(storage.getItemCatalog());
  };

  useEffect(() => {
    const unsub = storage.subscribe(() => {
      refreshProducts();
    });
    return unsub;
  }, []);

  const handleOpenAdd = () => {
    setEditingProduct(null);
    setName('');
    setCategory('Bitumen');
    setUnit('MT');
    setStandardRate(1200000);
    setVatRule('optional');
    setDefaultVatPercent(18);
    setDescription('');
    setIsActive(true);
    setIsFormOpen(true);
  };

  const handleOpenEdit = (p: ItemMaster) => {
    setEditingProduct(p);
    setName(p.name);
    setCategory(p.category);
    setUnit(p.unit);
    setStandardRate(p.standardRate);
    setVatRule(p.vatRule);
    setDefaultVatPercent(p.defaultVatPercent);
    setDescription(p.description || '');
    setIsActive(p.isActive !== false);
    setIsFormOpen(true);
  };

  const handleVatRuleChange = (rule: VatRule) => {
    setVatRule(rule);
    if (rule === 'exempt') {
      setDefaultVatPercent(0);
    } else {
      setDefaultVatPercent(18);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      alert('Product name is required');
      return;
    }

    const newProduct: ItemMaster = {
      id: editingProduct ? editingProduct.id : `itm_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      companyId: storage.getCurrentCompanyId(),
      name: name.trim(),
      category,
      unit: unit.trim(),
      standardRate: Number(standardRate) || 0,
      vatRule,
      defaultVatPercent: vatRule === 'exempt' ? 0 : Number(defaultVatPercent) || 0,
      description: description.trim(),
      isActive,
    };

    storage.saveItem(newProduct);
    setIsFormOpen(false);
    refreshProducts();
  };

  const handleToggleStatus = (p: ItemMaster) => {
    const updated: ItemMaster = {
      ...p,
      isActive: p.isActive === false ? true : false,
    };
    storage.saveItem(updated);
    refreshProducts();
  };

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to remove "${name}" from the product catalog?`)) {
      storage.deleteItem(id);
      refreshProducts();
    }
  };

  // Filter products
  const filteredProducts = products.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesCategory = categoryFilter === 'all' || p.category === categoryFilter;
    const matchesVat = vatRuleFilter === 'all' || p.vatRule === vatRuleFilter;

    return matchesSearch && matchesCategory && matchesVat;
  });

  const categories: ItemMaster['category'][] = [
    'Bitumen',
    'Fuel',
    'Logistics & Transport',
    'Construction',
    'Custom',
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="w-10 h-10 rounded-lg bg-blue-900 text-white flex items-center justify-center shadow-xs">
              <Package className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Product & Catalog Master</h1>
              <p className="text-xs text-slate-500">
                Manage commercial items, units, standard rates, and TRA VAT rules for {companyProfile.name}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleOpenAdd}
            className="flex items-center space-x-2 px-4 py-2.5 bg-blue-900 hover:bg-blue-800 text-white rounded-lg text-xs font-bold shadow-xs transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Product</span>
          </button>
        </div>
      </div>

      {/* KPI Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Catalog Items</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{products.length}</p>
          <p className="text-[10px] text-slate-400 mt-0.5">Scoped to {companyProfile.companyCode}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">Active Items</p>
          <p className="text-2xl font-bold text-emerald-800 mt-1">
            {products.filter((p) => p.isActive !== false).length}
          </p>
          <p className="text-[10px] text-emerald-600 mt-0.5">Available on Vouchers</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[11px] font-semibold text-blue-700 uppercase tracking-wider">Standard VAT (18%)</p>
          <p className="text-2xl font-bold text-blue-900 mt-1">
            {products.filter((p) => p.vatRule === 'standard' || p.vatRule === 'optional').length}
          </p>
          <p className="text-[10px] text-blue-600 mt-0.5">Bitumen & Commercial items</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">Exempt / Non-Vat (0%)</p>
          <p className="text-2xl font-bold text-amber-800 mt-1">
            {products.filter((p) => p.vatRule === 'exempt').length}
          </p>
          <p className="text-[10px] text-amber-600 mt-0.5">Fuel & statutory exemptions</p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search products by name, unit, category or description..."
              className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={vatRuleFilter}
              onChange={(e) => setVatRuleFilter(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All VAT Rules</option>
              <option value="standard">Standard (18% Vatable)</option>
              <option value="exempt">Exempt (0% Non-Vatable / Fuel)</option>
              <option value="optional">Optional (0% or 18% Toggleable)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Products Table */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3.5 px-4">Item Name & Category</th>
                <th className="py-3.5 px-4">Unit</th>
                <th className="py-3.5 px-4 text-right">Standard Rate (TZS)</th>
                <th className="py-3.5 px-4">TRA VAT Rule</th>
                <th className="py-3.5 px-4 text-center">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredProducts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    <Package className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                    <p className="font-semibold text-xs text-slate-600">No products match your criteria</p>
                    <p className="text-[11px] text-slate-400">Click "Add New Product" to expand your catalog</p>
                  </td>
                </tr>
              ) : (
                filteredProducts.map((p) => {
                  const active = p.isActive !== false;
                  return (
                    <tr
                      key={p.id}
                      className={`hover:bg-slate-50/80 transition ${!active ? 'opacity-60 bg-slate-50/40' : ''}`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900">{p.name}</div>
                        <div className="flex items-center space-x-2 mt-0.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                            {p.category}
                          </span>
                          {p.description && (
                            <span className="text-[10px] text-slate-400 truncate max-w-xs">{p.description}</span>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-700">{p.unit}</td>

                      <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900">
                        {p.standardRate.toLocaleString()}
                      </td>

                      <td className="py-3.5 px-4">
                        {p.vatRule === 'exempt' && (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                            <span>Exempt (0% Fuel/Statutory)</span>
                          </span>
                        )}
                        {p.vatRule === 'standard' && (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                            <span>Standard (18% TRA VAT)</span>
                          </span>
                        )}
                        {p.vatRule === 'optional' && (
                          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-800 border border-purple-200">
                            <span>Optional (0% / 18% Toggleable)</span>
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={() => handleToggleStatus(p)}
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold transition ${
                            active
                              ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                              : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                          }`}
                          title="Click to toggle active status"
                        >
                          {active ? (
                            <>
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              <span>Active</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="w-3 h-3 text-slate-500" />
                              <span>Inactive</span>
                            </>
                          )}
                        </button>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleOpenEdit(p)}
                            className="p-1.5 text-blue-700 hover:bg-blue-50 border border-blue-200 rounded text-xs transition"
                            title="Edit product"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(p.id, p.name)}
                            className="p-1.5 text-rose-600 hover:bg-rose-50 border border-rose-200 rounded text-xs transition"
                            title="Delete product"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Product Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden my-8">
            <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Package className="w-5 h-5 text-blue-400" />
                <h3 className="font-semibold text-sm">
                  {editingProduct ? 'Edit Catalog Product' : 'Add New Product to Catalog'}
                </h3>
              </div>
              <button
                onClick={() => setIsFormOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSave} className="p-6 space-y-4 text-xs">
              {/* Name */}
              <div className="space-y-1">
                <label className="font-bold text-slate-700">Product / Service Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Bitumen Grade 60/70 (Bulk MT / Steel Drums 200L)"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* Category */}
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as ItemMaster['category'])}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs bg-white focus:ring-2 focus:ring-blue-500"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Unit */}
                <div className="space-y-1">
                  <label className="font-bold text-slate-700">Unit of Measure (UOM)</label>
                  <input
                    type="text"
                    required
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    placeholder="e.g. MT, Liters, Drums, Trips"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Standard Rate */}
              <div className="space-y-1">
                <label className="font-bold text-slate-700">Standard Base Rate (TZS)</label>
                <input
                  type="number"
                  required
                  min={0}
                  step="any"
                  value={standardRate}
                  onChange={(e) => setStandardRate(Number(e.target.value))}
                  placeholder="1200000"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-mono font-bold focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* VAT Rule */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
                <label className="font-bold text-slate-800 block">TRA VAT Taxation Rule</label>
                <div className="space-y-2">
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="vatRule"
                      checked={vatRule === 'optional'}
                      onChange={() => handleVatRuleChange('optional')}
                      className="mt-0.5 text-blue-600"
                    />
                    <div>
                      <span className="font-semibold text-slate-800">Optional / Toggleable (0% or 18%)</span>
                      <p className="text-[10px] text-slate-500">
                        Default is 18%, but users can uncheck VAT on vouchers for tax-exempt projects.
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="vatRule"
                      checked={vatRule === 'standard'}
                      onChange={() => handleVatRuleChange('standard')}
                      className="mt-0.5 text-blue-600"
                    />
                    <div>
                      <span className="font-semibold text-slate-800">Standard-Rated (18% mandatory)</span>
                      <p className="text-[10px] text-slate-500">
                        Standard commercial items requiring 18% Value Added Tax.
                      </p>
                    </div>
                  </label>

                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="vatRule"
                      checked={vatRule === 'exempt'}
                      onChange={() => handleVatRuleChange('exempt')}
                      className="mt-0.5 text-blue-600"
                    />
                    <div>
                      <span className="font-semibold text-slate-800">Exempt / Non-Vatable (0% locked)</span>
                      <p className="text-[10px] text-slate-500">
                        Fuel (AGO Diesel, MOGAS Petrol) and statutory non-taxable goods.
                      </p>
                    </div>
                  </label>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1">
                <label className="font-bold text-slate-700">Description & Technical Specification</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Medium-curing liquid asphalt conforming to ASTM D2027 standards"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Status */}
              <div className="flex items-center space-x-2 pt-1">
                <input
                  type="checkbox"
                  id="isActiveToggle"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-slate-300"
                />
                <label htmlFor="isActiveToggle" className="font-bold text-slate-800 cursor-pointer">
                  Item is active and available in voucher line items
                </label>
              </div>

              {/* Footer */}
              <div className="pt-3 border-t border-slate-200 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex items-center space-x-1.5 px-5 py-2 bg-blue-900 hover:bg-blue-800 text-white rounded-lg font-bold shadow-xs transition"
                >
                  <Check className="w-4 h-4" />
                  <span>{editingProduct ? 'Update Product' : 'Save Product'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
