package com.example.domain.engine

import kotlin.math.max
import kotlin.math.pow

data class RetirementPlanResult(
    val yearsToRetire: Int,
    val lifeExpectancyYears: Int,
    val futureMonthlyExpenseAtRetirement: Double,
    val requiredRetirementCorpus: Double,
    val projectedCorpusFromCurrentSavings: Double,
    val corpusGap: Double,
    val recommendedMonthlySip: Double
)

data class InsuranceAnalysisResult(
    val requiredLifeCoverHLV: Double,
    val existingLifeCover: Double,
    val lifeCoverGap: Double,
    val requiredHealthCover: Double,
    val existingHealthCover: Double,
    val healthCoverGap: Double,
    val estimatedAnnualGapPremium: Double
)

object RetirementAndInsuranceEngine {

    fun calculateRetirement(
        currentAge: Int,
        retirementAge: Int,
        lifeExpectancyAge: Int = 85,
        currentMonthlyExpense: Double,
        currentRetirementSavings: Double,
        currentMonthlyInvestment: Double,
        inflationRate: Double = 6.0,
        preRetirementReturn: Double = 12.0,
        postRetirementReturn: Double = 7.5
    ): RetirementPlanResult {
        val yearsToRetire = max(1, retirementAge - currentAge)
        val retirementYears = max(1, lifeExpectancyAge - retirementAge)

        // Inflation adjusted monthly expense at retirement (6% Indian CPI)
        val futureMonthlyExpense = currentMonthlyExpense * (1 + inflationRate / 100.0).pow(yearsToRetire)
        val futureAnnualExpense = futureMonthlyExpense * 12

        // Real rate of return in retirement
        val realReturn = ((1 + postRetirementReturn / 100.0) / (1 + inflationRate / 100.0)) - 1.0

        // Corpus required using annuity present value formula with real return
        val requiredCorpus = if (realReturn > 0.001) {
            futureAnnualExpense * ((1 - (1 + realReturn).pow(-retirementYears)) / realReturn)
        } else {
            futureAnnualExpense * retirementYears
        }

        // Project current savings to retirement age
        val rPreAnnual = preRetirementReturn / 100.0
        val rPreMonthly = rPreAnnual / 12.0
        val months = yearsToRetire * 12
        val projectedLumpSum = currentRetirementSavings * (1 + rPreAnnual).pow(yearsToRetire)
        val projectedSip = currentMonthlyInvestment * ((1 + rPreMonthly).pow(months) - 1) / rPreMonthly * (1 + rPreMonthly)
        val totalProjected = projectedLumpSum + projectedSip

        val gap = max(0.0, requiredCorpus - totalProjected)

        // Recommended additional monthly SIP to bridge the gap
        val recommendedSip = if (gap > 0 && months > 0) {
            gap * rPreMonthly / ((1 + rPreMonthly).pow(months) - 1) / (1 + rPreMonthly)
        } else 0.0

        return RetirementPlanResult(
            yearsToRetire = yearsToRetire,
            lifeExpectancyYears = retirementYears,
            futureMonthlyExpenseAtRetirement = futureMonthlyExpense,
            requiredRetirementCorpus = requiredCorpus,
            projectedCorpusFromCurrentSavings = totalProjected,
            corpusGap = gap,
            recommendedMonthlySip = recommendedSip
        )
    }

    fun analyzeInsurance(
        monthlyIncome: Double,
        totalLiabilities: Double,
        liquidAssets: Double,
        existingLifeCover: Double,
        existingHealthCover: Double,
        familyDependentsCount: Int
    ): InsuranceAnalysisResult {
        val annualIncome = monthlyIncome * 12
        // Human Life Value (HLV) in India: 12x-15x Annual income + Total Debts - Existing Liquid Assets
        val requiredLifeCover = max(10000000.0, (annualIncome * 12) + totalLiabilities - liquidAssets)
        val lifeGap = max(0.0, requiredLifeCover - existingLifeCover)

        // Indian Health Cover Rule: Minimum ₹15 Lakhs base + ₹5 Lakhs per dependent
        val requiredHealthCover = max(1500000.0, 1500000.0 + (familyDependentsCount * 500000.0))
        val healthGap = max(0.0, requiredHealthCover - existingHealthCover)

        // Pure term life in India: ~₹12,000 - ₹18,000 per ₹1 Crore cover
        val lifePrem = (lifeGap / 10000000.0) * 16000.0
        val healthPrem = (healthGap / 1000000.0) * 8000.0
        val totalEstPremium = lifePrem + healthPrem

        return InsuranceAnalysisResult(
            requiredLifeCoverHLV = requiredLifeCover,
            existingLifeCover = existingLifeCover,
            lifeCoverGap = lifeGap,
            requiredHealthCover = requiredHealthCover,
            existingHealthCover = existingHealthCover,
            healthCoverGap = healthGap,
            estimatedAnnualGapPremium = totalEstPremium
        )
    }
}
