package com.example.domain.engine

import com.example.util.CurrencyFormatter
import kotlin.math.pow

data class BuyVsRentResult(
    val buyNetWorth10Yr: Double,
    val rentNetWorth10Yr: Double,
    val recommendation: String,
    val totalInterestPaid: Double,
    val rentSavingsInvestedWealth: Double
)

data class PrepayVsSipResult(
    val prepayInterestSaved: Double,
    val sipWealthGenerated: Double,
    val netFinancialAdvantage: Double,
    val recommendation: String
)

data class CarAffordabilityResult(
    val isAffordable: Boolean,
    val downPaymentRequired: Double,
    val estimatedMonthlyCost: Double,
    val maxRecommendedMonthlyCost: Double,
    val recommendation: String
)

data class SipVsFdResult(
    val sipCorpus: Double,
    val fdCorpus: Double,
    val wealthDifference: Double
)

object LifeDecisionEngine {

    // 1. Buy vs Rent House Simulator (Indian Context: Bangalore/Mumbai/NCR)
    fun simulateBuyVsRent(
        propertyPrice: Double,
        monthlyRent: Double,
        downPaymentPct: Double = 20.0,
        loanInterestRate: Double = 8.5,
        loanTenureYears: Int = 20,
        propertyAppreciationRate: Double = 6.0,
        rentInflationRate: Double = 5.0,
        sipEquityReturnRate: Double = 12.0
    ): BuyVsRentResult {
        val downPayment = propertyPrice * (downPaymentPct / 100.0)
        val loanAmount = propertyPrice - downPayment

        val monthlyRate = (loanInterestRate / 100.0) / 12.0
        val totalMonths = loanTenureYears * 12
        val emi = loanAmount * (monthlyRate * (1 + monthlyRate).pow(totalMonths)) / ((1 + monthlyRate).pow(totalMonths) - 1)

        val simYears = 10
        val houseValueIn10Yr = propertyPrice * (1 + propertyAppreciationRate / 100.0).pow(simYears)
        val totalEmiPaid10Yr = emi * (simYears * 12)
        val approxPrincipalPaid = loanAmount * 0.38
        val remainingLoan = loanAmount - approxPrincipalPaid
        val totalInterestPaid = totalEmiPaid10Yr - approxPrincipalPaid
        val buyNetWorth10Yr = houseValueIn10Yr - remainingLoan

        val rSipMonthly = (sipEquityReturnRate / 100.0) / 12.0
        val months10 = simYears * 12
        val downPaymentCompounded = downPayment * (1 + rSipMonthly).pow(months10)

        var monthlyInvestableWealth = 0.0
        var currentRent = monthlyRent
        for (m in 1..months10) {
            if (m % 12 == 0) currentRent *= (1 + rentInflationRate / 100.0)
            val diff = emi - currentRent
            if (diff > 0) {
                monthlyInvestableWealth = (monthlyInvestableWealth + diff) * (1 + rSipMonthly)
            }
        }
        val rentNetWorth10Yr = downPaymentCompounded + monthlyInvestableWealth
        val diffNetWorth = rentNetWorth10Yr - buyNetWorth10Yr

        val rec = if (diffNetWorth > 0) {
            "Financially, Renting & investing surplus into Nifty 50 equity mutual funds yields ~${CurrencyFormatter.formatInr(diffNetWorth, compact = true)} higher liquid wealth over 10 years, offering greater career mobility."
        } else {
            "Buying is favored! Property appreciation and rental saving create ~${CurrencyFormatter.formatInr(-diffNetWorth, compact = true)} higher net equity after 10 years."
        }

        return BuyVsRentResult(
            buyNetWorth10Yr = buyNetWorth10Yr,
            rentNetWorth10Yr = rentNetWorth10Yr,
            recommendation = rec,
            totalInterestPaid = totalInterestPaid,
            rentSavingsInvestedWealth = rentNetWorth10Yr
        )
    }

    // 2. Prepay Home Loan vs Invest in Nifty 50 Mutual Fund SIP
    fun simulatePrepayVsSip(
        prepaymentLumpSum: Double,
        loanInterestRate: Double = 8.5,
        sipReturnRate: Double = 12.5,
        tenureYearsRemaining: Int = 10
    ): PrepayVsSipResult {
        val monthlyLoanRate = (loanInterestRate / 100.0) / 12.0
        val months = tenureYearsRemaining * 12
        val futureLoanObligationSaved = prepaymentLumpSum * (1 + monthlyLoanRate).pow(months) - prepaymentLumpSum

        val monthlyEquityRate = (sipReturnRate / 100.0) / 12.0
        val equityValue = prepaymentLumpSum * (1 + monthlyEquityRate).pow(months)
        val sipWealthGenerated = equityValue - prepaymentLumpSum

        val advantage = sipWealthGenerated - futureLoanObligationSaved
        val rec = if (advantage > 0) {
            "Investing in diversified equity index funds provides a net ${CurrencyFormatter.formatInr(advantage, compact = true)} wealth advantage over prepaying home loan at ${loanInterestRate}%."
        } else {
            "Prepaying debt is mathematically optimal, securing a guaranteed ${loanInterestRate}% risk-free tax-free savings."
        }

        return PrepayVsSipResult(
            prepayInterestSaved = futureLoanObligationSaved,
            sipWealthGenerated = sipWealthGenerated,
            netFinancialAdvantage = advantage,
            recommendation = rec
        )
    }

    // 3. 20/4/10 Car Affordability Engine in INR
    fun checkCarAffordability(
        onRoadPrice: Double,
        monthlyTakeHomeIncome: Double,
        loanInterestRate: Double = 8.75
    ): CarAffordabilityResult {
        val requiredDownPayment = onRoadPrice * 0.20
        val loanAmount = onRoadPrice * 0.80
        val tenureMonths = 48
        val r = (loanInterestRate / 100.0) / 12.0
        val emi = loanAmount * (r * (1 + r).pow(tenureMonths)) / ((1 + r).pow(tenureMonths) - 1)
        val insuranceAndMaintenanceMonthly = onRoadPrice * 0.0035
        val totalMonthlyCarCost = emi + insuranceAndMaintenanceMonthly

        val maxAllowedMonthly = monthlyTakeHomeIncome * 0.10
        val affordable = totalMonthlyCarCost <= maxAllowedMonthly

        val rec = if (affordable) {
            "Fits the 20/4/10 rule comfortably! Monthly outflow is ${CurrencyFormatter.formatInr(totalMonthlyCarCost)} (${String.format("%.1f", (totalMonthlyCarCost / monthlyTakeHomeIncome) * 100)}% of monthly take-home, below 10% limit)."
        } else {
            "Violates the 20/4/10 rule. Monthly vehicle expenditure of ${CurrencyFormatter.formatInr(totalMonthlyCarCost)} exceeds your 10% income threshold (${CurrencyFormatter.formatInr(maxAllowedMonthly)}). Consider a lower trim or pre-owned car."
        }

        return CarAffordabilityResult(
            isAffordable = affordable,
            downPaymentRequired = requiredDownPayment,
            estimatedMonthlyCost = totalMonthlyCarCost,
            maxRecommendedMonthlyCost = maxAllowedMonthly,
            recommendation = rec
        )
    }

    // 4. SIP vs Fixed Deposit Wealth Growth (Indian Context)
    fun simulateSipVsFd(
        monthlyAmount: Double,
        years: Int,
        sipRate: Double = 12.5,
        fdRate: Double = 7.1
    ): SipVsFdResult {
        val months = years * 12
        val rSip = (sipRate / 100.0) / 12.0
        val rFd = (fdRate / 100.0) / 12.0

        val sipCorpus = monthlyAmount * ((1 + rSip).pow(months) - 1) / rSip * (1 + rSip)
        val fdCorpus = monthlyAmount * ((1 + rFd).pow(months) - 1) / rFd * (1 + rFd)

        return SipVsFdResult(
            sipCorpus = sipCorpus,
            fdCorpus = fdCorpus,
            wealthDifference = sipCorpus - fdCorpus
        )
    }
}
