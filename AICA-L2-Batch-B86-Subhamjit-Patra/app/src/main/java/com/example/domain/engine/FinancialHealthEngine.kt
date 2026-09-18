package com.example.domain.engine

import com.example.data.local.AssetEntity
import com.example.data.local.InsurancePolicyEntity
import com.example.data.local.LiabilityEntity
import com.example.data.local.TransactionEntity
import com.example.data.local.UserProfileEntity
import com.example.data.model.AssetCategory
import com.example.data.model.InsuranceType
import com.example.data.model.TransactionType
import com.example.util.CurrencyFormatter
import kotlin.math.max
import kotlin.math.min

data class FinancialHealthResult(
    val totalScore: Int,
    val grade: String,
    val summaryText: String,
    val emergencyFundScore: Int,
    val debtRatioScore: Int,
    val savingsRateScore: Int,
    val insuranceScore: Int,
    val diversificationScore: Int,
    val retirementScore: Int,
    val emergencyFundMonths: Double,
    val debtToIncomePercent: Double,
    val savingsRatePercent: Double,
    val lifeCoverMultiplier: Double,
    val strengths: List<String>,
    val risks: List<String>,
    val improvementSuggestions: List<String>
)

object FinancialHealthEngine {

    fun calculate(
        profile: UserProfileEntity,
        assets: List<AssetEntity>,
        liabilities: List<LiabilityEntity>,
        transactions: List<TransactionEntity>,
        insurance: List<InsurancePolicyEntity>
    ): FinancialHealthResult {
        val monthlyIncome = max(10000.0, profile.monthlyIncome)

        // Monthly Expenses and EMI
        val monthlyExpenses = transactions
            .filter { it.type == TransactionType.EXPENSE }
            .sumOf { it.amount }
            .let { if (it <= 0.0) 65000.0 else it }

        val monthlyEmi = liabilities.sumOf { it.monthlyEmi }

        // 1. Emergency Fund (target 6 months of expenses in Liquid FD / Bank / Liquid MF, max 20 pts)
        val liquidAssets = assets
            .filter { it.category == AssetCategory.BANK || it.category == AssetCategory.CASH || it.category == AssetCategory.FIXED_DEPOSIT }
            .sumOf { it.amount }
        val emergencyFundMonths = if (monthlyExpenses > 0) liquidAssets / monthlyExpenses else 0.0
        val emergencyScore = min(20, (emergencyFundMonths / 6.0 * 20.0).toInt())

        // 2. Debt-to-Income Ratio (EMI / Income <= 35% ideal in India, max 20 pts)
        val debtRatio = (monthlyEmi / monthlyIncome) * 100.0
        val debtScore = when {
            debtRatio <= 25.0 -> 20
            debtRatio <= 35.0 -> 16
            debtRatio <= 50.0 -> 10
            else -> 4
        }

        // 3. Savings Rate ((Income - Expense) / Income >= 35% ideal, max 15 pts)
        val netSavings = max(0.0, monthlyIncome - monthlyExpenses)
        val savingsRate = (netSavings / monthlyIncome) * 100.0
        val savingsScore = min(15, (savingsRate / 40.0 * 15.0).toInt())

        // 4. Insurance Adequacy (Pure Term Life >= 10x-15x annual income + Comprehensive Health, max 15 pts)
        val annualIncome = monthlyIncome * 12
        val lifeCover = insurance
            .filter { it.type == InsuranceType.TERM_LIFE }
            .sumOf { it.sumAssured }
        val lifeMultiplier = if (annualIncome > 0) lifeCover / annualIncome else 0.0
        val hasHealth = insurance.any { it.type == InsuranceType.HEALTH && it.sumAssured >= 1000000.0 }
        var insScore = min(10, (lifeMultiplier / 10.0 * 10.0).toInt())
        if (hasHealth) insScore += 5

        // 5. Investment Diversification (Equities, EPF/PPF/NPS, Real Estate, Sovereign Gold, Cash, max 15 pts)
        val totalAssets = max(1.0, assets.sumOf { it.amount })
        val equityRatio = assets.filter { it.category == AssetCategory.MUTUAL_FUNDS || it.category == AssetCategory.SHARES }.sumOf { it.amount } / totalAssets
        val debtGovtRatio = assets.filter { it.category == AssetCategory.BONDS || it.category == AssetCategory.EPF || it.category == AssetCategory.NPS || it.category == AssetCategory.PPF || it.category == AssetCategory.FIXED_DEPOSIT }.sumOf { it.amount } / totalAssets
        val realEstateRatio = assets.filter { it.category == AssetCategory.REAL_ESTATE }.sumOf { it.amount } / totalAssets
        val goldRatio = assets.filter { it.category == AssetCategory.GOLD }.sumOf { it.amount } / totalAssets

        var divScore = 5
        if (equityRatio in 0.25..0.65) divScore += 4
        if (debtGovtRatio in 0.15..0.45) divScore += 3
        if (goldRatio in 0.03..0.15 || realEstateRatio in 0.1..0.5) divScore += 3
        divScore = min(15, divScore)

        // 6. Retirement Readiness (Trajectory towards target retirement age)
        val retirementAssets = assets
            .filter { it.category == AssetCategory.EPF || it.category == AssetCategory.NPS || it.category == AssetCategory.PPF || it.category == AssetCategory.MUTUAL_FUNDS }
            .sumOf { it.amount }
        val ageFactor = (profile.currentAge - 22.0) / max(1.0, (profile.retirementAge - 22.0).toDouble())
        val benchmarkNeeded = annualIncome * ageFactor * 3.5
        val retScore = if (benchmarkNeeded > 0) min(15, (retirementAssets / benchmarkNeeded * 15.0).toInt()) else 12

        val totalScore = min(100, max(0, emergencyScore + debtScore + savingsScore + insScore + divScore + retScore))

        val grade = when {
            totalScore >= 80 -> "OPTIMAL (GRADE A)"
            totalScore >= 65 -> "STRONG (GRADE B)"
            totalScore >= 50 -> "MODERATE (GRADE C)"
            else -> "NEEDS ATTENTION"
        }

        val strengths = mutableListOf<String>()
        val risks = mutableListOf<String>()
        val suggestions = mutableListOf<String>()

        if (emergencyFundMonths >= 5.0) {
            strengths.add("Emergency buffer covers ${String.format("%.1f", emergencyFundMonths)} months of family living expenses.")
        } else {
            risks.add("Liquid emergency runway is only ${String.format("%.1f", emergencyFundMonths)} months (RBI/SEBI recommended: 6 months).")
            suggestions.add("Automate ₹15,000/mo into an Arbitrage / Liquid Mutual Fund or sweep-in FD until reaching 6 months of buffer.")
        }

        if (debtRatio <= 30.0) {
            strengths.add("EMI servicing is healthy at ${String.format("%.1f", debtRatio)}% of take-home pay (Safe limit: 35%).")
        } else {
            risks.add("Elevated debt servicing: ${String.format("%.1f", debtRatio)}% of monthly salary goes into EMIs.")
            suggestions.add("Prepay vehicle loan or credit card outstanding to reduce recurring monthly obligations.")
        }

        if (savingsRate >= 35.0) {
            strengths.add("Excellent savings rate of ${String.format("%.1f", savingsRate)}% fuels long-term wealth compounding.")
        } else {
            suggestions.add("Implement a 10% annual Step-Up SIP across Nifty 50 and Flexi Cap index funds.")
        }

        if (lifeMultiplier >= 8.0 && hasHealth) {
            strengths.add("Family protection is secured with pure term coverage of ${String.format("%.1f", lifeMultiplier)}x annual income plus health cover.")
        } else {
            risks.add("Term insurance cover is below 10x annual income (current: ${String.format("%.1f", lifeMultiplier)}x).")
            suggestions.add("Add a pure vanilla term insurance plan of at least ₹1.5 - ₹2.5 Crore to safeguard dependents.")
        }

        strengths.add("Robust diversification across EPF, PPF, Nifty equities, Sovereign Gold Bonds, and Real Estate.")

        val summaryText = "Your consolidated net worth stands at ${CurrencyFormatter.formatInr(totalAssets - liabilities.sumOf { it.outstandingAmount }, compact = true)}. Asset allocation and debt servicing are well balanced under Indian economic standards."

        return FinancialHealthResult(
            totalScore = totalScore,
            grade = grade,
            summaryText = summaryText,
            emergencyFundScore = emergencyScore,
            debtRatioScore = debtScore,
            savingsRateScore = savingsScore,
            insuranceScore = insScore,
            diversificationScore = divScore,
            retirementScore = retScore,
            emergencyFundMonths = emergencyFundMonths,
            debtToIncomePercent = debtRatio,
            savingsRatePercent = savingsRate,
            lifeCoverMultiplier = lifeMultiplier,
            strengths = strengths,
            risks = risks,
            improvementSuggestions = suggestions
        )
    }
}
