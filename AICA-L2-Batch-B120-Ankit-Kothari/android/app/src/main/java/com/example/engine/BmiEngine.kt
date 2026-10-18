package com.example.engine

import kotlin.math.roundToInt

object BmiEngine {

    data class BmiAnalysis(
        val bmi: Float,
        val category: String,
        val healthyMinWeight: Float,
        val healthyMaxWeight: Float,
        val waistToHeightRatio: Float?,
        val kindAdvice: String
    )

    fun analyze(
        weightKg: Float,
        heightCm: Float,
        waistCm: Float = 0f,
        useAsianCutoffs: Boolean = false
    ): BmiAnalysis {
        val heightM = heightCm / 100f
        val bmi = if (heightM > 0) weightKg / (heightM * heightM) else 22f

        val (category, kindAdvice) = if (useAsianCutoffs) {
            when {
                bmi < 18.5f -> Pair(
                    "Gentle Nourish (Underweight)",
                    "Focus on nutrient-dense foods, wholesome fats, and strength. Be patient and kind with your body."
                )
                bmi < 23.0f -> Pair(
                    "Optimal Harmony (Healthy)",
                    "Your weight is in a balanced, healthy range. Keep honoring your movement, water, and rest."
                )
                bmi < 27.5f -> Pair(
                    "Mindful Balance (Overweight)",
                    "Small gentle tweaks in daily walking and mindful eating will protect your energy and cardiovascular vitality."
                )
                else -> Pair(
                    "Care & Vitality (Higher Range)",
                    "Celebrate movement for how it makes you feel inside. Gentle walks and consistent hydration work wonders."
                )
            }
        } else {
            when {
                bmi < 18.5f -> Pair(
                    "Gentle Nourish (Underweight)",
                    "Your body may appreciate hearty meals, grounding proteins, and restful sleep."
                )
                bmi < 25.0f -> Pair(
                    "Optimal Harmony (Healthy)",
                    "A vibrant, balanced metric. Celebrate what your body accomplishes every day!"
                )
                bmi < 30.0f -> Pair(
                    "Mindful Balance (Overweight)",
                    "A friendly reminder to stay active and hydrated. Health is about long-term joy, not numbers."
                )
                else -> Pair(
                    "Care & Vitality (Higher Range)",
                    "Focus on daily joyful steps, reducing stress, and nourishing meals that bring steady energy."
                )
            }
        }

        val healthyMaxCutoff = if (useAsianCutoffs) 22.9f else 24.9f
        val healthyMinWeight = (18.5f * heightM * heightM * 10f).roundToInt() / 10f
        val healthyMaxWeight = (healthyMaxCutoff * heightM * heightM * 10f).roundToInt() / 10f

        val waistRatio = if (waistCm > 0 && heightCm > 0) waistCm / heightCm else null

        return BmiAnalysis(
            bmi = (bmi * 10f).roundToInt() / 10f,
            category = category,
            healthyMinWeight = healthyMinWeight,
            healthyMaxWeight = healthyMaxWeight,
            waistToHeightRatio = waistRatio?.let { (it * 100f).roundToInt() / 100f },
            kindAdvice = kindAdvice
        )
    }
}
