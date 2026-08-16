import React, { useState } from 'react';
import {
  HeartPulse,
  Plus,
  Trash2,
  Edit,
  Activity,
  Flame,
  ShieldCheck,
  Dumbbell,
  Heart,
  Zap,
  TrendingDown,
  Info,
  CheckCircle2,
  Scale,
  Users,
} from 'lucide-react';
import { FamilyMemberProfile, HealthGoal, Recipe } from '../types';
import { calculateFamilyMemberNutrition, getBMICategoryInfo } from '../services/bmiService';

interface FamilyBmiViewProps {
  familyProfiles: FamilyMemberProfile[];
  onAddProfile: (profile: FamilyMemberProfile) => void;
  onEditProfile: (profile: FamilyMemberProfile) => void;
  onDeleteProfile: (id: string) => void;
  recipes: Recipe[];
  onSelectGoalFilter?: (goal: HealthGoal) => void;
}

const GOALS: { id: HealthGoal; label: string; icon: any; color: string; bg: string; description: string }[] = [
  {
    id: 'Muscle Gain',
    label: 'Muscle Gain',
    icon: Dumbbell,
    color: 'text-indigo-600 dark:text-indigo-400',
    bg: 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800',
    description: 'Caloric surplus with high bio-available protein to maximize lean muscle hypertrophy.',
  },
  {
    id: 'Fat Loss',
    label: 'Fat Loss',
    icon: TrendingDown,
    color: 'text-rose-600 dark:text-rose-400',
    bg: 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800',
    description: 'Controlled caloric deficit with satiating fiber & high protein for fat breakdown.',
  },
  {
    id: 'Cardiovascular Endurance',
    label: 'Cardiovascular Endurance',
    icon: Zap,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800',
    description: 'Sustained energy via complex carbohydrates and stamina-building nutrition.',
  },
  {
    id: 'Heart Health',
    label: 'Heart Health',
    icon: Heart,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800',
    description: 'Low saturated fat, high soluble fiber, omega-3 fatty acids & rich antioxidants.',
  },
  {
    id: 'Blood Pressure Control',
    label: 'Blood Pressure Control',
    icon: ShieldCheck,
    color: 'text-cyan-600 dark:text-cyan-400',
    bg: 'bg-cyan-50 dark:bg-cyan-950/40 border-cyan-200 dark:border-cyan-800',
    description: 'DASH diet principles: potassium-rich, low sodium, magnesium & calcium rich whole foods.',
  },
];

export const FamilyBmiView: React.FC<FamilyBmiViewProps> = ({
  familyProfiles,
  onAddProfile,
  onEditProfile,
  onDeleteProfile,
  recipes,
  onSelectGoalFilter,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [relation, setRelation] = useState<'Self' | 'Spouse' | 'Parent' | 'Child' | 'Other'>('Self');
  const [weightKg, setWeightKg] = useState('65');
  const [heightFt, setHeightFt] = useState('5');
  const [heightInches, setHeightInches] = useState('7');
  const [ageYears, setAgeYears] = useState('32');
  const [gender, setGender] = useState<'Male' | 'Female'>('Female');
  const [activityLevel, setActivityLevel] = useState<'Sedentary' | 'Light' | 'Moderate' | 'Active'>('Moderate');
  const [primaryGoal, setPrimaryGoal] = useState<HealthGoal>('Heart Health');

  const [activeTabGoal, setActiveTabGoal] = useState<HealthGoal | 'All'>('All');

  const handleOpenAdd = (profile?: FamilyMemberProfile) => {
    if (profile) {
      setEditingId(profile.id);
      setName(profile.name);
      setRelation(profile.relation);
      setWeightKg(String(profile.weightKg));
      setHeightFt(String(profile.heightFt));
      setHeightInches(String(profile.heightInches));
      setAgeYears(String(profile.ageYears));
      setGender(profile.gender);
      setActivityLevel(profile.activityLevel);
      setPrimaryGoal(profile.primaryGoal);
    } else {
      setEditingId(null);
      setName('');
      setRelation('Family Member' as any);
      setWeightKg('65');
      setHeightFt('5');
      setHeightInches('0');
      setAgeYears('30');
      setGender('Female');
      setActivityLevel('Moderate');
      setPrimaryGoal('Heart Health');
    }
    setIsModalOpen(true);
  };

  const handleSaveForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const parsedInches = heightInches === '' || isNaN(Number(heightInches)) ? 0 : Number(heightInches);
    const parsedFt = heightFt === '' || isNaN(Number(heightFt)) ? 5 : Number(heightFt);
    const parsedWeight = weightKg === '' || isNaN(Number(weightKg)) ? 60 : Number(weightKg);
    const parsedAge = ageYears === '' || isNaN(Number(ageYears)) ? 30 : Number(ageYears);

    const profileData: FamilyMemberProfile = {
      id: editingId || `profile_${Date.now()}`,
      name,
      relation,
      weightKg: parsedWeight,
      heightFt: parsedFt,
      heightInches: parsedInches,
      ageYears: parsedAge,
      gender,
      activityLevel,
      primaryGoal,
    };

    if (editingId) {
      onEditProfile(profileData);
    } else {
      onAddProfile(profileData);
    }
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Hero Header */}
      <div className="backdrop-blur-md bg-white/60 dark:bg-slate-900/60 border border-white/80 dark:border-slate-800/80 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2.5">
            <HeartPulse className="w-6 h-6 text-rose-500 animate-pulse" />
            Family BMI & Goal-Based Diet Planner
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Personalized BMI tracking, BMR calculation, and target macro recommendations for every family member
          </p>
        </div>

        <button
          onClick={() => handleOpenAdd()}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-orange-500 to-rose-500 hover:from-orange-600 hover:to-rose-600 text-white text-xs font-bold shadow-md transition-all"
        >
          <Plus className="w-4 h-4" />
          Add Family Profile
        </button>
      </div>

      {/* Goal Strategy Overview Banner */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Supported Health & Goal Categories
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {GOALS.map((g) => {
            const Icon = g.icon;
            const matchingRecipesCount = recipes.filter((r) => r.dietaryGoals?.includes(g.id)).length;
            const isSelected = activeTabGoal === g.id;

            return (
              <div
                key={g.id}
                onClick={() => {
                  setActiveTabGoal(isSelected ? 'All' : g.id);
                  if (onSelectGoalFilter) onSelectGoalFilter(g.id);
                }}
                className={`p-4 rounded-2xl border cursor-pointer transition-all duration-300 relative overflow-hidden backdrop-blur-md ${
                  isSelected
                    ? 'ring-2 ring-orange-500 shadow-lg bg-orange-500/10 border-orange-500'
                    : 'bg-white/60 dark:bg-slate-900/60 border-slate-200/60 dark:border-slate-800/60 hover:border-orange-300'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`w-5 h-5 ${g.color}`} />
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white line-clamp-1">
                    {g.label}
                  </h4>
                </div>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-2">
                  {g.description}
                </p>
                <div className="mt-3 flex items-center justify-between text-[10px] font-bold text-orange-600 dark:text-orange-400 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <span>{matchingRecipesCount || 15}+ Recipes</span>
                  <span>Select Goal →</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Family Profiles Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-orange-500" />
            Family Member Health Profiles ({familyProfiles.length})
          </h3>
        </div>

        {familyProfiles.length === 0 ? (
          <div className="p-8 rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 text-center space-y-3 bg-white/40 dark:bg-slate-900/40">
            <Scale className="w-10 h-10 text-slate-400 mx-auto" />
            <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">
              No Family Profiles Created Yet
            </h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Add family members with their weight, height, age, and health goals to generate custom tailored meal plans!
            </p>
            <button
              onClick={() => handleOpenAdd()}
              className="px-4 py-2 rounded-xl bg-orange-500 text-white text-xs font-bold shadow-md hover:bg-orange-600"
            >
              Add First Member
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {familyProfiles.map((profile) => {
              const nutrition = calculateFamilyMemberNutrition(profile);
              const bmiInfo = getBMICategoryInfo(nutrition.bmi);
              const goalObj = GOALS.find((g) => g.id === profile.primaryGoal);
              const GoalIcon = goalObj?.icon || Heart;

              return (
                <div
                  key={profile.id}
                  className="rounded-3xl border border-slate-200/70 dark:border-slate-800/70 bg-white/75 dark:bg-slate-900/75 backdrop-blur-md p-5 shadow-sm space-y-4 relative overflow-hidden"
                >
                  {/* Top Header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-base font-bold text-slate-900 dark:text-white">
                          {profile.name}
                        </h4>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                          {profile.relation}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {profile.ageYears} Yrs • {profile.gender} • {profile.weightKg} kg • {profile.heightFt}'{profile.heightInches}"
                      </p>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleOpenAdd(profile)}
                        className="p-1.5 text-slate-400 hover:text-orange-500 transition-colors"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onDeleteProfile(profile.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* BMI Gauge Badge */}
                  <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/50 dark:border-slate-700/50 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                        Body Mass Index (BMI)
                      </span>
                      <div className="flex items-baseline gap-2 mt-0.5">
                        <span className="text-xl font-black text-slate-900 dark:text-white">
                          {nutrition.bmi}
                        </span>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${bmiInfo.badgeBg}`}>
                          {nutrition.bmiCategory}
                        </span>
                      </div>
                    </div>
                    <Scale className={`w-8 h-8 ${nutrition.bmiColor} opacity-80`} />
                  </div>

                  {/* Goal Badge & Description */}
                  <div className={`p-3.5 rounded-2xl border ${goalObj?.bg || 'bg-slate-50 border-slate-200'} space-y-1`}>
                    <div className="flex items-center gap-2">
                      <GoalIcon className={`w-4 h-4 ${goalObj?.color || 'text-orange-500'}`} />
                      <span className="text-xs font-bold text-slate-900 dark:text-white">
                        Goal: {profile.primaryGoal}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-tight">
                      {nutrition.goalAdvice}
                    </p>
                  </div>

                  {/* Calories & Macros Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20">
                      <span className="text-[10px] text-orange-600 dark:text-orange-400 font-bold block">
                        Target Calories
                      </span>
                      <span className="text-sm font-black text-slate-900 dark:text-white">
                        {nutrition.targetCalories} <span className="text-[10px] font-normal">kcal/day</span>
                      </span>
                      <span className="text-[9px] text-slate-400 block">BMR: {nutrition.bmr} kcal</span>
                    </div>

                    <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                      <span className="text-[10px] text-indigo-600 dark:text-indigo-400 font-bold block">
                        Daily Protein
                      </span>
                      <span className="text-sm font-black text-slate-900 dark:text-white">
                        {nutrition.macros.proteinGrams} <span className="text-[10px] font-normal">grams</span>
                      </span>
                      <span className="text-[9px] text-slate-400 block">Fiber: {nutrition.macros.fiberGrams}g</span>
                    </div>
                  </div>

                  {/* Recommended Foods */}
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
                    <span className="font-bold text-slate-700 dark:text-slate-300 block mb-0.5">
                      Recommended Ingredients:
                    </span>
                    <p className="line-clamp-2">{nutrition.recommendedFocus}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add / Edit Profile Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <form
            onSubmit={handleSaveForm}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                {editingId ? 'Edit Family Profile' : 'Add Family Profile'}
              </h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rahul / Ananya"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Relation
                </label>
                <select
                  value={relation}
                  onChange={(e) => setRelation(e.target.value as any)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="Self">Self</option>
                  <option value="Spouse">Spouse</option>
                  <option value="Parent">Parent</option>
                  <option value="Child">Child</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Weight (Kg)
                </label>
                <input
                  type="number"
                  step="0.5"
                  required
                  value={weightKg}
                  onChange={(e) => setWeightKg(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Height (Feet)
                </label>
                <input
                  type="number"
                  min="1"
                  max="8"
                  required
                  value={heightFt}
                  onChange={(e) => setHeightFt(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Height (Inches)
                </label>
                <input
                  type="number"
                  min="0"
                  max="11"
                  required
                  value={heightInches}
                  onChange={(e) => setHeightInches(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Age (Years)
                </label>
                <input
                  type="number"
                  min="1"
                  max="120"
                  required
                  value={ageYears}
                  onChange={(e) => setAgeYears(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Gender
                </label>
                <select
                  value={gender}
                  onChange={(e) => setGender(e.target.value as any)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Activity Level
                </label>
                <select
                  value={activityLevel}
                  onChange={(e) => setActivityLevel(e.target.value as any)}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-orange-500"
                >
                  <option value="Sedentary">Sedentary (Desk Job)</option>
                  <option value="Light">Light Exercise (1-2 days/wk)</option>
                  <option value="Moderate">Moderate (3-5 days/wk)</option>
                  <option value="Active">Active (6-7 days/wk)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1 uppercase tracking-wider">
                Primary Dietary & Health Goal
              </label>
              <select
                value={primaryGoal}
                onChange={(e) => setPrimaryGoal(e.target.value as HealthGoal)}
                className="w-full px-3.5 py-2.5 rounded-xl text-xs font-bold bg-orange-50 dark:bg-slate-800 text-orange-900 dark:text-orange-300 border border-orange-200 dark:border-slate-700 outline-none focus:ring-2 focus:ring-orange-500"
              >
                {GOALS.map((g) => (
                  <option key={g.id} value={g.id}>
                    🎯 {g.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-xl text-xs font-bold bg-orange-500 hover:bg-orange-600 text-white shadow-md"
              >
                Save Family Profile
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
