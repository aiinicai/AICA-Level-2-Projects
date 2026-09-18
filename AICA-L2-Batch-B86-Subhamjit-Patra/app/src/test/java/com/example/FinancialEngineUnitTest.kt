package com.example

import com.example.data.local.AssetEntity
import com.example.data.local.LiabilityEntity
import com.example.data.local.UserProfileEntity
import com.example.data.model.AssetCategory
import com.example.data.model.LiabilityCategory
import com.example.domain.engine.FinancialHealthEngine
import com.example.domain.engine.RetirementAndInsuranceEngine
import com.example.util.CurrencyFormatter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class FinancialEngineUnitTest {

    @Test
    fun testFinancialHealthCalculation() {
        val profile = UserProfileEntity(
            name = "Subhamjit Patra",
            monthlyIncome = 225000.0,
            currentAge = 32,
            retirementAge = 55
        )
        val assets = listOf(
            AssetEntity(name = "Emergency Savings", category = AssetCategory.BANK, amount = 450000.0, institution = "HDFC Bank")
        )
        val liabilities = listOf(
            LiabilityEntity(name = "Auto Loan", category = LiabilityCategory.VEHICLE_LOAN, outstandingAmount = 525000.0, interestRate = 8.7, monthlyEmi = 15800.0, tenureMonthsRemaining = 38)
        )

        val result = FinancialHealthEngine.calculate(
            profile = profile,
            assets = assets,
            liabilities = liabilities,
            transactions = emptyList(),
            insurance = emptyList()
        )

        assertNotNull(result)
        assertTrue(result.totalScore in 0..100)
        assertTrue(result.emergencyFundMonths >= 5.0)
        assertTrue(result.debtToIncomePercent < 30.0)
    }

    @Test
    fun testRetirementCalculation() {
        val result = RetirementAndInsuranceEngine.calculateRetirement(
            currentAge = 32,
            retirementAge = 55,
            lifeExpectancyAge = 85,
            currentMonthlyExpense = 68000.0,
            currentRetirementSavings = 5000000.0,
            currentMonthlyInvestment = 65000.0
        )

        assertEquals(23, result.yearsToRetire)
        assertTrue(result.requiredRetirementCorpus > 0.0)
        assertTrue(result.projectedCorpusFromCurrentSavings > 0.0)
    }

    @Test
    fun testIndianCurrencyFormatter() {
        assertEquals("₹1,50,000", CurrencyFormatter.formatInr(150000.0))
        assertEquals("₹1,25,00,000", CurrencyFormatter.formatInr(12500000.0))
        assertEquals("₹1.25 Cr", CurrencyFormatter.formatInr(12500000.0, compact = true))
        assertEquals("₹25.50 L", CurrencyFormatter.formatInr(2550000.0, compact = true))
    }
}
