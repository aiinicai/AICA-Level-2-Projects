import React, { useState } from 'react';
import { Database, Code, Server, Network, Table, Check, Layers } from 'lucide-react';

export const DatabaseSchemaView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'er' | 'sql' | 'api'>('er');

  const TABLES = [
    {
      name: 'Inventory',
      columns: [
        { name: 'id', type: 'VARCHAR(50)', pk: true },
        { name: 'name', type: 'VARCHAR(100)', fk: false },
        { name: 'category', type: 'VARCHAR(50)', fk: false },
        { name: 'currentQuantity', type: 'DECIMAL(10,3)', fk: false },
        { name: 'baseUnit', type: 'VARCHAR(20)', fk: false },
        { name: 'minStockLevel', type: 'DECIMAL(10,3)', fk: false },
        { name: 'expiryDate', type: 'DATE', fk: false },
        { name: 'imageUrl', type: 'TEXT', fk: false },
        { name: 'lastUpdated', type: 'TIMESTAMP', fk: false },
      ],
    },
    {
      name: 'Recipes',
      columns: [
        { name: 'id', type: 'VARCHAR(50)', pk: true },
        { name: 'name', type: 'VARCHAR(100)', fk: false },
        { name: 'mealType', type: 'ENUM(Breakfast, Lunch, Dinner)', fk: false },
        { name: 'cuisine', type: 'VARCHAR(50)', fk: false },
        { name: 'isFavorite', type: 'BOOLEAN', fk: false },
        { name: 'timesPrepared', type: 'INT', fk: false },
        { name: 'userRating', type: 'INT', fk: false },
        { name: 'isSeasonal', type: 'BOOLEAN', fk: false },
        { name: 'availableFromMonth', type: 'INT', fk: false },
        { name: 'availableToMonth', type: 'INT', fk: false },
      ],
    },
    {
      name: 'RecipeIngredients',
      columns: [
        { name: 'id', type: 'VARCHAR(50)', pk: true },
        { name: 'recipeId', type: 'VARCHAR(50)', fk: true, ref: 'Recipes.id' },
        { name: 'ingredientName', type: 'VARCHAR(100)', fk: false },
        { name: 'quantityOneFemale', type: 'DECIMAL(10,3)', fk: false },
        { name: 'unit', type: 'VARCHAR(20)', fk: false },
        { name: 'category', type: 'VARCHAR(50)', fk: false },
      ],
    },
    {
      name: 'WeeklyMealPlans',
      columns: [
        { name: 'id', type: 'VARCHAR(50)', pk: true },
        { name: 'weekStartDate', type: 'DATE', fk: false },
        { name: 'weekEndDate', type: 'DATE', fk: false },
        { name: 'isLocked', type: 'BOOLEAN', fk: false },
      ],
    },
    {
      name: 'MealEntries',
      columns: [
        { name: 'id', type: 'VARCHAR(50)', pk: true },
        { name: 'planId', type: 'VARCHAR(50)', fk: true, ref: 'WeeklyMealPlans.id' },
        { name: 'date', type: 'DATE', fk: false },
        { name: 'dayOfWeek', type: 'VARCHAR(20)', fk: false },
        { name: 'mealType', type: 'ENUM', fk: false },
        { name: 'recipeId', type: 'VARCHAR(50)', fk: true, ref: 'Recipes.id' },
        { name: 'isPrepared', type: 'BOOLEAN', fk: false },
        { name: 'preparedAt', type: 'TIMESTAMP', fk: false },
      ],
    },
    {
      name: 'InventoryTransactions',
      columns: [
        { name: 'id', type: 'VARCHAR(50)', pk: true },
        { name: 'date', type: 'TIMESTAMP', fk: false },
        { name: 'ingredientName', type: 'VARCHAR(100)', fk: false },
        { name: 'type', type: 'VARCHAR(50)', fk: false },
        { name: 'quantityChange', type: 'DECIMAL(10,3)', fk: false },
        { name: 'unit', type: 'VARCHAR(20)', fk: false },
        { name: 'previousQuantity', type: 'DECIMAL(10,3)', fk: false },
        { name: 'newQuantity', type: 'DECIMAL(10,3)', fk: false },
        { name: 'referenceMealName', type: 'VARCHAR(100)', fk: false },
      ],
    },
  ];

  const API_ENDPOINTS = [
    { method: 'GET', path: '/api/inventory', desc: 'Fetch full master inventory with stock levels & expiry' },
    { method: 'POST', path: '/api/inventory', desc: 'Create new inventory ingredient record' },
    { method: 'PUT', path: '/api/inventory/:id', desc: 'Update inventory ingredient details/quantity' },
    { method: 'DELETE', path: '/api/inventory/:id', desc: 'Delete ingredient from inventory' },
    { method: 'GET', path: '/api/recipes', desc: 'Fetch all 90 recipes with ingredients' },
    { method: 'POST', path: '/api/recipes', desc: 'Create new custom recipe' },
    { method: 'PUT', path: '/api/recipes/:id', desc: 'Update recipe, favorites, ratings or seasonal months' },
    { method: 'GET', path: '/api/mealplan', desc: 'Get active 7-day weekly meal plan' },
    { method: 'POST', path: '/api/mealplan/generate', desc: 'Trigger smart meal planner optimization engine' },
    { method: 'POST', path: '/api/mealplan/prepare', desc: 'Mark meal prepared & deduct stock with Males=1.25, Females=1.0, Kids=0.75' },
    { method: 'GET', path: '/api/grocery', desc: 'Generate required grocery list against available stock' },
    { method: 'POST', path: '/api/grocery/purchase', desc: 'Restock inventory upon purchasing grocery item' },
    { method: 'GET', path: '/api/transactions', desc: 'Fetch inventory transaction audit log' },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
            <Database className="w-6 h-6 text-orange-500" />
            Database Architecture & REST API Specs
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Normalized ER Diagram • PostgreSQL Schema • RESTful Endpoint Mapping
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-white/80 dark:bg-slate-800 p-1 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <button
            onClick={() => setActiveTab('er')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'er'
                ? 'bg-orange-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-300'
            }`}
          >
            ER Diagram
          </button>
          <button
            onClick={() => setActiveTab('sql')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'sql'
                ? 'bg-orange-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-300'
            }`}
          >
            SQL DDL Schema
          </button>
          <button
            onClick={() => setActiveTab('api')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'api'
                ? 'bg-orange-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-300'
            }`}
          >
            REST API Docs
          </button>
        </div>
      </div>

      {/* ER Diagram Tab */}
      {activeTab === 'er' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {TABLES.map((tbl) => (
            <div
              key={tbl.name}
              className="rounded-3xl border border-slate-200/70 dark:border-slate-800/70 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md overflow-hidden shadow-sm"
            >
              <div className="p-4 bg-orange-500/10 border-b border-slate-200/60 dark:border-slate-800/60 flex items-center justify-between">
                <span className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Table className="w-4 h-4 text-orange-500" />
                  {tbl.name}
                </span>
                <span className="text-[10px] text-orange-600 font-bold uppercase tracking-wider">
                  Table
                </span>
              </div>
              <div className="p-4 space-y-2 text-xs">
                {tbl.columns.map((col, idx) => (
                  <div key={idx} className="flex items-center justify-between font-mono">
                    <span className="flex items-center gap-1.5">
                      {col.pk && <span className="text-[9px] font-bold text-amber-500">PK</span>}
                      {col.fk && <span className="text-[9px] font-bold text-blue-500">FK</span>}
                      <span className="text-slate-800 dark:text-slate-200">{col.name}</span>
                    </span>
                    <span className="text-slate-400 text-[10px]">{col.type}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SQL DDL Schema Tab */}
      {activeTab === 'sql' && (
        <div className="p-6 rounded-3xl bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto space-y-4 shadow-2xl">
          <pre>{`-- Khaana Khazana Kitchen Inventory & Meal Planning Schema
CREATE TABLE Inventory (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  category VARCHAR(50) NOT NULL,
  current_quantity DECIMAL(10,3) NOT NULL DEFAULT 0.000,
  base_unit VARCHAR(20) NOT NULL,
  min_stock_level DECIMAL(10,3) NOT NULL DEFAULT 1.000,
  expiry_date DATE,
  image_url TEXT,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Recipes (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  meal_type VARCHAR(20) NOT NULL, -- Breakfast, Lunch, Dinner
  cuisine VARCHAR(50) NOT NULL,
  is_favorite BOOLEAN DEFAULT FALSE,
  times_prepared INT DEFAULT 0,
  user_rating INT DEFAULT 5,
  is_seasonal BOOLEAN DEFAULT FALSE,
  available_from_month INT,
  available_to_month INT
);

CREATE TABLE RecipeIngredients (
  id VARCHAR(50) PRIMARY KEY,
  recipe_id VARCHAR(50) REFERENCES Recipes(id) ON DELETE CASCADE,
  ingredient_name VARCHAR(100) NOT NULL,
  quantity_one_female DECIMAL(10,3) NOT NULL,
  unit VARCHAR(20) NOT NULL,
  category VARCHAR(50) NOT NULL
);

CREATE TABLE InventoryTransactions (
  id VARCHAR(50) PRIMARY KEY,
  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ingredient_name VARCHAR(100) NOT NULL,
  type VARCHAR(50) NOT NULL,
  quantity_change DECIMAL(10,3) NOT NULL,
  unit VARCHAR(20) NOT NULL,
  previous_quantity DECIMAL(10,3) NOT NULL,
  new_quantity DECIMAL(10,3) NOT NULL,
  reference_meal_name VARCHAR(100)
);`}</pre>
        </div>
      )}

      {/* REST API Tab */}
      {activeTab === 'api' && (
        <div className="rounded-3xl border border-slate-200/70 dark:border-slate-800/70 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md overflow-hidden shadow-sm">
          <div className="p-4 bg-slate-100/60 dark:bg-slate-800/60 border-b border-slate-200/60 dark:border-slate-800/60 font-bold text-sm text-slate-900 dark:text-white">
            Express REST API Endpoints
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {API_ENDPOINTS.map((ep, idx) => (
              <div key={idx} className="p-4 flex items-center justify-between text-xs hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2.5 py-1 rounded-lg font-mono font-bold text-[10px] ${
                      ep.method === 'GET'
                        ? 'bg-blue-500/15 text-blue-600 dark:text-blue-400'
                        : ep.method === 'POST'
                        ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        : ep.method === 'PUT'
                        ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                        : 'bg-rose-500/15 text-rose-600 dark:text-rose-400'
                    }`}
                  >
                    {ep.method}
                  </span>
                  <span className="font-mono font-bold text-slate-900 dark:text-white">
                    {ep.path}
                  </span>
                </div>
                <span className="text-slate-500 text-[11px]">{ep.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
