import React, { useState } from 'react';
import { Calculator, Scale, Droplets, BookOpen, ArrowRightLeft } from 'lucide-react';
import { DEFAULT_DENSITY_TABLE, convertUnit } from '../services/unitConversionEngine';
import { UnitType } from '../types';

export const ConversionSettingsView: React.FC = () => {
  const [testQty, setTestQty] = useState<number>(500);
  const [fromUnit, setFromUnit] = useState<UnitType>('g');
  const [toUnit, setToUnit] = useState<UnitType>('kg');
  const [testIngredient, setTestIngredient] = useState<string>('Wheat Flour / Atta');

  const convertedResult = convertUnit(testQty, fromUnit, toUnit, testIngredient);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
          <Calculator className="w-6 h-6 text-orange-500" />
          Intelligent Unit Conversion Engine
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Supports Weight (kg, g, lb) • Volume (L, ml, cup, tbsp, tsp) • Density-Based Mass ↔ Volume Conversions
        </p>
      </div>

      {/* Live Unit Converter Test Sandbox */}
      <div className="p-6 rounded-3xl bg-white/70 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800/70 backdrop-blur-md shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <ArrowRightLeft className="w-4 h-4 text-orange-500" />
          Live Conversion Calculator Sandbox
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
              Quantity
            </label>
            <input
              type="number"
              value={testQty}
              onChange={(e) => setTestQty(Number(e.target.value))}
              className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
              From Unit
            </label>
            <select
              value={fromUnit}
              onChange={(e) => setFromUnit(e.target.value as UnitType)}
              className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="g">g (grams)</option>
              <option value="kg">kg (kilograms)</option>
              <option value="ml">ml (milliliters)</option>
              <option value="L">L (liters)</option>
              <option value="cup">cup (240 ml)</option>
              <option value="tbsp">tbsp (15 ml)</option>
              <option value="tsp">tsp (5 ml)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
              To Unit
            </label>
            <select
              value={toUnit}
              onChange={(e) => setToUnit(e.target.value as UnitType)}
              className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="kg">kg (kilograms)</option>
              <option value="g">g (grams)</option>
              <option value="L">L (liters)</option>
              <option value="ml">ml (milliliters)</option>
              <option value="cup">cup (240 ml)</option>
              <option value="tbsp">tbsp (15 ml)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1">
              Ingredient Density Factors
            </label>
            <select
              value={testIngredient}
              onChange={(e) => setTestIngredient(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
            >
              {DEFAULT_DENSITY_TABLE.map((d) => (
                <option key={d.ingredientName} value={d.ingredientName}>
                  {d.ingredientName}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Calculation Result */}
        <div className="p-4 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-between">
          <span className="text-xs font-semibold text-orange-900 dark:text-orange-300">
            Conversion Output:
          </span>
          <span className="text-lg font-bold text-orange-600 dark:text-orange-400">
            {testQty} {fromUnit} = {convertedResult.toFixed(3)} {toUnit}
          </span>
        </div>
      </div>

      {/* Density Conversion Factor Reference Table */}
      <div className="p-6 rounded-3xl bg-white/70 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800/70 backdrop-blur-md shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Scale className="w-4 h-4 text-orange-500" />
          Centralized Ingredient Density Table (Mass ↔ Volume)
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200/60 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/50 text-slate-400 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Ingredient Name</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Density (g/ml)</th>
                <th className="py-3 px-4">1 Cup (g)</th>
                <th className="py-3 px-4">1 Tbsp (g)</th>
                <th className="py-3 px-4">1 Tsp (g)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {DEFAULT_DENSITY_TABLE.map((item, i) => (
                <tr key={i} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-4 font-bold text-slate-900 dark:text-white">
                    {item.ingredientName}
                  </td>
                  <td className="py-3 px-4 text-slate-500">{item.category}</td>
                  <td className="py-3 px-4 font-semibold text-orange-600 dark:text-orange-400">
                    {item.gramsPerMl} g/ml
                  </td>
                  <td className="py-3 px-4">{item.gramsPerCup} g</td>
                  <td className="py-3 px-4">{item.gramsPerTbsp} g</td>
                  <td className="py-3 px-4">{item.gramsPerTsp} g</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
