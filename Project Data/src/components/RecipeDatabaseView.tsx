import React, { useState } from 'react';
import {
  BookOpen,
  Search,
  Heart,
  Star,
  Clock,
  Sparkles,
  Calendar,
  Utensils,
  ChevronDown,
  ChevronUp,
  Download,
  Upload,
  ShieldCheck,
  Dumbbell,
  TrendingDown,
  Zap,
} from 'lucide-react';
import { Recipe, MealType, HealthGoal, InventoryItem } from '../types';
import { BulkRecipeImportModal } from './BulkRecipeImportModal';
import { downloadRecipeExcelTemplate, RecipeImportResult } from '../services/excelService';

interface RecipeDatabaseViewProps {
  recipes: Recipe[];
  inventory: InventoryItem[];
  onToggleFavorite: (recipeId: string) => void;
  onUpdateRating: (recipeId: string, rating: number) => void;
  onUpdateSeasonal: (recipeId: string, isSeasonal: boolean, fromMonth?: number, toMonth?: number) => void;
  onImportSuccess: (result: RecipeImportResult) => void;
}

export const RecipeDatabaseView: React.FC<RecipeDatabaseViewProps> = ({
  recipes,
  inventory,
  onToggleFavorite,
  onUpdateRating,
  onUpdateSeasonal,
  onImportSuccess,
}) => {
  const [selectedMealType, setSelectedMealType] = useState<MealType | 'All'>('All');
  const [selectedGoal, setSelectedGoal] = useState<HealthGoal | 'All'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCuisine, setSelectedCuisine] = useState<string>('All');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [expandedRecipeId, setExpandedRecipeId] = useState<string | null>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Extract unique cuisines
  const cuisines = Array.from(new Set(recipes.map((r) => r.cuisine)));

  // Filter recipes
  const filteredRecipes = recipes.filter((r) => {
    const matchesMeal = selectedMealType === 'All' || r.mealType === selectedMealType;
    const matchesCuisine = selectedCuisine === 'All' || r.cuisine === selectedCuisine;
    const matchesFav = !showFavoritesOnly || r.isFavorite;
    const matchesGoal = selectedGoal === 'All' || (r.dietaryGoals && r.dietaryGoals.includes(selectedGoal));
    const matchesSearch =
      r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.cuisine.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.ingredients.some((i) => i.ingredientName.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesMeal && matchesCuisine && matchesFav && matchesGoal && matchesSearch;
  });

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
            <BookOpen className="w-6 h-6 text-orange-500" />
            Master Recipe Collection ({recipes.length} Recipes)
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Baseline Female Servings • Auto-Ingredient Master Sync • Goal-Based Categories
          </p>
        </div>

        {/* Buttons Row */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold shadow-md shadow-orange-500/20 transition-all"
          >
            <Upload className="w-4 h-4" />
            Import Recipe Master
          </button>

          <button
            onClick={downloadRecipeExcelTemplate}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-white/80 dark:bg-slate-800 hover:bg-white text-slate-700 dark:text-slate-300 text-xs font-bold border border-slate-200 dark:border-slate-700 transition-all shadow-sm"
          >
            <Download className="w-4 h-4" />
            Download Recipe Template
          </button>

          <button
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
              showFavoritesOnly
                ? 'bg-rose-500 text-white shadow-rose-500/20'
                : 'bg-white/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
            }`}
          >
            <Heart className={`w-4 h-4 ${showFavoritesOnly ? 'fill-white' : 'text-rose-500'}`} />
            {showFavoritesOnly ? 'Favorites Only' : 'Filter Favorites'}
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 bg-white/80 dark:bg-slate-900/80 p-3 rounded-2xl border border-slate-200/60 dark:border-slate-800/60 backdrop-blur-md">
        {/* Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search recipes or ingredients..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-xl text-xs bg-slate-100/70 dark:bg-slate-800/70 text-slate-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500"
          />
        </div>

        {/* Meal Category Select */}
        <select
          value={selectedMealType}
          onChange={(e) => setSelectedMealType(e.target.value as any)}
          className="px-3.5 py-2 rounded-xl text-xs bg-slate-100/70 dark:bg-slate-800/70 text-slate-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500"
        >
          <option value="All">All Meal Types (Breakfast, Lunch, Dinner)</option>
          <option value="Breakfast">Breakfast</option>
          <option value="Lunch">Lunch</option>
          <option value="Dinner">Dinner</option>
        </select>

        {/* Health Goal Filter */}
        <select
          value={selectedGoal}
          onChange={(e) => setSelectedGoal(e.target.value as any)}
          className="px-3.5 py-2 rounded-xl text-xs bg-slate-100/70 dark:bg-slate-800/70 text-slate-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500"
        >
          <option value="All">All Dietary Goals</option>
          <option value="Muscle Gain">Muscle Gain</option>
          <option value="Fat Loss">Fat Loss</option>
          <option value="Cardiovascular Endurance">Cardiovascular Endurance</option>
          <option value="Heart Health">Heart Health</option>
          <option value="Blood Pressure Control">Blood Pressure Control</option>
        </select>

        {/* Cuisine Select */}
        <select
          value={selectedCuisine}
          onChange={(e) => setSelectedCuisine(e.target.value)}
          className="px-3.5 py-2 rounded-xl text-xs bg-slate-100/70 dark:bg-slate-800/70 text-slate-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500"
        >
          <option value="All">All Cuisines</option>
          {cuisines.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Recipe Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredRecipes.map((recipe) => {
          const isExpanded = expandedRecipeId === recipe.id;

          return (
            <div
              key={recipe.id}
              className="rounded-3xl border border-slate-200/70 dark:border-slate-800/70 bg-white/70 dark:bg-slate-900/70 backdrop-blur-md overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                {/* Image & Badges Banner */}
                <div className="relative h-44 overflow-hidden">
                  <img
                    src={recipe.imageUrl}
                    alt={recipe.name}
                    className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent" />

                  {/* Top Badges */}
                  <div className="absolute top-3 left-3 flex items-center gap-1.5">
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-orange-500 text-white shadow-md">
                      {recipe.mealType}
                    </span>
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-900/80 text-slate-200 backdrop-blur-md border border-slate-700">
                      {recipe.cuisine}
                    </span>
                  </div>

                  {/* Favorite Toggle Button */}
                  <button
                    onClick={() => onToggleFavorite(recipe.id)}
                    className="absolute top-3 right-3 p-2 rounded-full bg-slate-900/60 backdrop-blur-md text-white hover:bg-slate-900 transition-colors"
                  >
                    <Heart
                      className={`w-4 h-4 ${
                        recipe.isFavorite ? 'fill-rose-500 text-rose-500' : 'text-white'
                      }`}
                    />
                  </button>

                  {/* Bottom Image Title overlay */}
                  <div className="absolute bottom-3 left-3 right-3">
                    <h3 className="text-base font-bold text-white drop-shadow-md">
                      {recipe.name}
                    </h3>
                  </div>
                </div>

                {/* Card Content Info */}
                <div className="p-5 space-y-4">
                  {/* Health Goal Badges */}
                  {recipe.dietaryGoals && recipe.dietaryGoals.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {recipe.dietaryGoals.map((g) => (
                        <span
                          key={g}
                          className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20"
                        >
                          🎯 {g}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Rating & Prep stats */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => onUpdateRating(recipe.id, star)}
                          className="focus:outline-none"
                        >
                          <Star
                            className={`w-3.5 h-3.5 ${
                              star <= (recipe.userRating || 4)
                                ? 'fill-amber-400 text-amber-400'
                                : 'text-slate-300 dark:text-slate-700'
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                    <span className="text-slate-500 text-[11px]">
                      Prepared {recipe.timesPrepared || 0} times
                    </span>
                  </div>

                  {/* Seasonal Toggle Info */}
                  <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/50 dark:border-slate-700/50 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-orange-500" />
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        Seasonal Availability
                      </span>
                    </div>
                    <button
                      onClick={() => onUpdateSeasonal(recipe.id, !recipe.isSeasonal, 10, 3)}
                      className={`px-2.5 py-1 rounded-xl text-[10px] font-bold ${
                        recipe.isSeasonal
                          ? 'bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30'
                          : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                      }`}
                    >
                      {recipe.isSeasonal ? 'Seasonal (Oct-Mar)' : 'Year-Round'}
                    </button>
                  </div>

                  {/* Expand Ingredients Drawer */}
                  <button
                    onClick={() => setExpandedRecipeId(isExpanded ? null : recipe.id)}
                    className="w-full flex items-center justify-between p-3 rounded-2xl bg-orange-500/10 text-orange-700 dark:text-orange-400 font-bold text-xs hover:bg-orange-500/15 transition-all"
                  >
                    <span>
                      Ingredients ({recipe.ingredients.length}) — 1 Female Serving
                    </span>
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>

                  {/* Expanded Ingredients List */}
                  {isExpanded && (
                    <div className="space-y-1.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                      {recipe.ingredients.map((ing, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-xs"
                        >
                          <span className="font-medium text-slate-800 dark:text-slate-200">
                            {ing.ingredientName}
                          </span>
                          <span className="font-bold text-slate-900 dark:text-white">
                            {ing.quantityOneFemale} {ing.unit}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bulk Recipe Import Modal */}
      <BulkRecipeImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        recipes={recipes}
        inventory={inventory}
        onImportSuccess={(result) => {
          onImportSuccess(result);
          setIsImportModalOpen(false);
        }}
      />
    </div>
  );
};
