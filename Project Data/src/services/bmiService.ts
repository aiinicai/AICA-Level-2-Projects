import { FamilyMemberProfile, HealthGoal } from '../types';

export interface BmiCalculationResult {
  bmi: number;
  bmiCategory: 'Underweight' | 'Normal Weight' | 'Overweight' | 'Obese';
  bmiColor: string; // Tailwind color class
  bmr: number; // Basal Metabolic Rate in kcal
  tdee: number; // Total Daily Energy Expenditure
  targetCalories: number;
  macros: {
    proteinGrams: number;
    carbsGrams: number;
    fatGrams: number;
    fiberGrams: number;
  };
  goalAdvice: string;
  recommendedFocus: string;
}

/**
 * Calculates BMI from weight (kg) and height (feet + inches)
 */
export function calculateBMI(weightKg: number, heightFt: number, heightInches: number): number {
  const totalInches = heightFt * 12 + heightInches;
  if (totalInches <= 0 || weightKg <= 0) return 0;
  const heightMeters = totalInches * 0.0254;
  const bmi = weightKg / (heightMeters * heightMeters);
  return Number(bmi.toFixed(1));
}

/**
 * Get category label and badge color for BMI
 */
export function getBMICategoryInfo(bmi: number): {
  category: 'Underweight' | 'Normal Weight' | 'Overweight' | 'Obese';
  color: string;
  badgeBg: string;
} {
  if (bmi < 18.5) {
    return {
      category: 'Underweight',
      color: 'text-amber-500',
      badgeBg: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    };
  } else if (bmi <= 24.9) {
    return {
      category: 'Normal Weight',
      color: 'text-emerald-500',
      badgeBg: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    };
  } else if (bmi <= 29.9) {
    return {
      category: 'Overweight',
      color: 'text-orange-500',
      badgeBg: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    };
  } else {
    return {
      category: 'Obese',
      color: 'text-rose-500',
      badgeBg: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
    };
  }
}

/**
 * Full nutritional calculation for a family member profile
 */
export function calculateFamilyMemberNutrition(profile: FamilyMemberProfile): BmiCalculationResult {
  const { weightKg, heightFt, heightInches, ageYears, gender, activityLevel, primaryGoal } = profile;

  const bmi = calculateBMI(weightKg, heightFt, heightInches);
  const { category: bmiCategory, color: bmiColor } = getBMICategoryInfo(bmi);

  // Height in cm
  const heightCm = (heightFt * 12 + heightInches) * 2.54;

  // BMR via Mifflin-St Jeor Formula
  let bmr = 10 * weightKg + 6.25 * heightCm - 5 * ageYears;
  if (gender === 'Male') {
    bmr += 5;
  } else {
    bmr -= 161;
  }
  bmr = Math.round(bmr);

  // Activity Multiplier
  const multipliers = {
    Sedentary: 1.2,
    Light: 1.375,
    Moderate: 1.55,
    Active: 1.725,
  };

  const activityMult = multipliers[activityLevel] || 1.375;
  const tdee = Math.round(bmr * activityMult);

  let targetCalories = tdee;
  let proteinGrams = Math.round(weightKg * 1.5);
  let carbsGrams = Math.round((tdee * 0.5) / 4);
  let fatGrams = Math.round((tdee * 0.25) / 9);
  let fiberGrams = 30;
  let goalAdvice = '';
  let recommendedFocus = '';

  switch (primaryGoal) {
    case 'Muscle Gain':
      targetCalories = tdee + 350;
      proteinGrams = Math.round(weightKg * 2.0); // 2g per kg
      fatGrams = Math.round((targetCalories * 0.25) / 9);
      carbsGrams = Math.round((targetCalories - (proteinGrams * 4 + fatGrams * 9)) / 4);
      fiberGrams = 32;
      goalAdvice = 'Caloric surplus with high bio-available protein & complex carbs for lean muscle hypertrophy.';
      recommendedFocus = 'Paneer, Chana, Moong Sprouts, Dal Makhani, Soy, Eggs / Chicken.';
      break;

    case 'Fat Loss':
      targetCalories = Math.max(1200, tdee - 450);
      proteinGrams = Math.round(weightKg * 1.8);
      fatGrams = Math.round((targetCalories * 0.22) / 9);
      carbsGrams = Math.round((targetCalories - (proteinGrams * 4 + fatGrams * 9)) / 4);
      fiberGrams = 38;
      goalAdvice = 'Moderate caloric deficit with high fiber & satiating protein to boost metabolism.';
      recommendedFocus = 'Oats Chilla, Palak Dal, Moong Salad, Vegetable Sabzi, Buttermilk.';
      break;

    case 'Cardiovascular Endurance':
      targetCalories = tdee + 200;
      proteinGrams = Math.round(weightKg * 1.4);
      carbsGrams = Math.round((targetCalories * 0.58) / 4);
      fatGrams = Math.round((targetCalories - (proteinGrams * 4 + carbsGrams * 4)) / 9);
      fiberGrams = 35;
      goalAdvice = 'Glycogen re-synthesis focus with sustained slow-release complex carbohydrates.';
      recommendedFocus = 'Sabudana Khichdi, Brown Rice Pulao, Idli Sambhar, Multi-grain Roti.';
      break;

    case 'Heart Health':
      targetCalories = tdee;
      proteinGrams = Math.round(weightKg * 1.3);
      fatGrams = Math.round((tdee * 0.25) / 9); // Healthy fats focus
      carbsGrams = Math.round((tdee * 0.55) / 4);
      fiberGrams = 40;
      goalAdvice = 'Low saturated fat, high soluble fiber, omega-3 rich & antioxidant packed nutrition.';
      recommendedFocus = 'Flaxseed, Walnut, Oats, Green Leafy Vegetables, Garlic, Olive/Mustard Oil.';
      break;

    case 'Blood Pressure Control':
      targetCalories = tdee;
      proteinGrams = Math.round(weightKg * 1.3);
      carbsGrams = Math.round((tdee * 0.52) / 4);
      fatGrams = Math.round((tdee * 0.25) / 9);
      fiberGrams = 40;
      goalAdvice = 'DASH diet principles: potassium-rich, low sodium, magnesium & calcium rich whole foods.';
      recommendedFocus = 'Curd/Yogurt, Spinach, Lauki, Cucumber, Banana, Methi Thepla, Almonds.';
      break;
  }

  return {
    bmi,
    bmiCategory,
    bmiColor,
    bmr,
    tdee,
    targetCalories,
    macros: {
      proteinGrams,
      carbsGrams,
      fatGrams,
      fiberGrams,
    },
    goalAdvice,
    recommendedFocus,
  };
}
