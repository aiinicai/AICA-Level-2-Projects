package com.example

import com.example.engine.FemaEngine
import com.example.engine.IncomeTaxEngine
import com.example.model.FemaArrivalPurpose
import com.example.model.FemaDeparturePurpose
import com.example.model.FemaInput
import com.example.model.FemaStatus
import com.example.model.ITCategory
import com.example.model.IncomeTaxInput
import com.example.model.IncomeTaxStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExampleUnitTest {

    // --- Income Tax Engine Tests ---

    @Test
    fun testPrimaryThreshold_ROR() {
        val input = IncomeTaxInput(
            daysInFY = 182,
            category = ITCategory.STANDARD,
            residentIn2Of10Years = true,
            daysInPreceding7Years = 730
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.ROR, res.status)
        assertTrue(res.primaryConditionMet)
    }

    @Test
    fun testPrimaryThreshold_RNOR_Boundary729Days() {
        val input = IncomeTaxInput(
            daysInFY = 182,
            category = ITCategory.STANDARD,
            residentIn2Of10Years = true,
            daysInPreceding7Years = 729 // 729 < 730 -> RNOR
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.RNOR, res.status)
        assertTrue(res.primaryConditionMet)
    }

    @Test
    fun testPrimaryThreshold_RNOR_Failed2of10() {
        val input = IncomeTaxInput(
            daysInFY = 182,
            category = ITCategory.STANDARD,
            residentIn2Of10Years = false,
            daysInPreceding7Years = 730
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.RNOR, res.status)
    }

    @Test
    fun testSecondaryCondition_Boundary59Days_NR() {
        val input = IncomeTaxInput(
            daysInFY = 59,
            category = ITCategory.STANDARD,
            daysInPreceding4Years = 400
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.NR, res.status)
        assertFalse(res.secondaryConditionMet)
    }

    @Test
    fun testSecondaryCondition_Boundary364Days_NR() {
        val input = IncomeTaxInput(
            daysInFY = 60,
            category = ITCategory.STANDARD,
            daysInPreceding4Years = 364 // 364 < 365 -> NR
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.NR, res.status)
        assertFalse(res.secondaryConditionMet)
    }

    @Test
    fun testSecondaryCondition_60Days_365Days_Resident() {
        val input = IncomeTaxInput(
            daysInFY = 60,
            category = ITCategory.STANDARD,
            daysInPreceding4Years = 365,
            residentIn2Of10Years = true,
            daysInPreceding7Years = 730
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.ROR, res.status)
        assertTrue(res.secondaryConditionMet)
    }

    @Test
    fun testCitizenLeavingForEmployment_150Days_NR() {
        val input = IncomeTaxInput(
            daysInFY = 150,
            category = ITCategory.CITIZEN_LEAVING,
            daysInPreceding4Years = 500
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.NR, res.status)
    }

    @Test
    fun testVisitingCitizen_IncomeLess15L_150Days_NR() {
        val input = IncomeTaxInput(
            daysInFY = 150,
            category = ITCategory.VISITING_CITIZEN_OR_PIO,
            indianIncomeExceeds15L = false,
            daysInPreceding4Years = 500
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.NR, res.status)
    }

    @Test
    fun testVisitingCitizen_IncomeGreater15L_119Days_NR() {
        val input = IncomeTaxInput(
            daysInFY = 119,
            category = ITCategory.VISITING_CITIZEN_OR_PIO,
            indianIncomeExceeds15L = true,
            daysInPreceding4Years = 400
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.NR, res.status)
    }

    @Test
    fun testVisitingCitizen_IncomeGreater15L_120Days_MandatoryRNOR() {
        val input = IncomeTaxInput(
            daysInFY = 120,
            category = ITCategory.VISITING_CITIZEN_OR_PIO,
            indianIncomeExceeds15L = true,
            daysInPreceding4Years = 365,
            residentIn2Of10Years = true,
            daysInPreceding7Years = 800
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.RNOR, res.status)
        assertTrue(res.isMandatoryRNOR)
    }

    @Test
    fun testDeemedResident_IndianCitizen() {
        val input = IncomeTaxInput(
            daysInFY = 30,
            category = ITCategory.STANDARD,
            isIndianCitizen = true,
            indianIncomeExceeds15L = true,
            notLiableToTaxElsewhere = true
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals(IncomeTaxStatus.RNOR, res.status)
        assertTrue(res.isDeemedResident)
    }

    @Test
    fun testIta2025_TaxYearTerminology() {
        val input = IncomeTaxInput(
            daysInFY = 182,
            assessmentYear = "Tax Year 2026-27 (ITA 2025)"
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals("Income Tax Act, 2025", res.keyFactors["Governing Act"])
        assertTrue(res.keyFactors.containsKey("Tax Year"))
        assertFalse(res.keyFactors.containsKey("Assessment Year"))
    }

    @Test
    fun testIta1961_AssessmentYearTerminology() {
        val input = IncomeTaxInput(
            daysInFY = 182,
            assessmentYear = "FY 2025-26 / AY 2026-27 (ITA 1961)"
        )
        val res = IncomeTaxEngine.determine(input)
        assertEquals("Income Tax Act, 1961", res.keyFactors["Governing Act"])
        assertTrue(res.keyFactors.containsKey("Assessment Year"))
        assertFalse(res.keyFactors.containsKey("Tax Year"))
    }

    // --- FEMA Engine Tests ---

    @Test
    fun testFema_Boundary182Days_PROI() {
        val input = FemaInput(
            precedingYearDays = 182,
            hasComeToIndia = false
        )
        val res = FemaEngine.determine(input)
        assertEquals(FemaStatus.PROI, res.status)
    }

    @Test
    fun testFema_Boundary183Days_PRI() {
        val input = FemaInput(
            precedingYearDays = 183,
            hasGoneOutsideIndia = false
        )
        val res = FemaEngine.determine(input)
        assertEquals(FemaStatus.PRI, res.status)
    }

    @Test
    fun testFema_Preceding183Days_DepartureForEmployment_PROI() {
        val input = FemaInput(
            precedingYearDays = 183,
            hasGoneOutsideIndia = true,
            departurePurpose = FemaDeparturePurpose.EMPLOYMENT_ABROAD
        )
        val res = FemaEngine.determine(input)
        assertEquals(FemaStatus.PROI, res.status)
    }

    @Test
    fun testFema_Preceding183Days_DepartureForVacation_PRI() {
        val input = FemaInput(
            precedingYearDays = 183,
            hasGoneOutsideIndia = true,
            departurePurpose = FemaDeparturePurpose.TEMPORARY_OTHER
        )
        val res = FemaEngine.determine(input)
        assertEquals(FemaStatus.PRI, res.status)
    }

    @Test
    fun testFema_Preceding100Days_ArrivalForEmployment_PRI() {
        val input = FemaInput(
            precedingYearDays = 100,
            hasComeToIndia = true,
            arrivalPurpose = FemaArrivalPurpose.EMPLOYMENT_IN_INDIA
        )
        val res = FemaEngine.determine(input)
        assertEquals(FemaStatus.PRI, res.status)
    }

    @Test
    fun testFema_Preceding100Days_ArrivalForVacation_PROI() {
        val input = FemaInput(
            precedingYearDays = 100,
            hasComeToIndia = true,
            arrivalPurpose = FemaArrivalPurpose.TEMPORARY_VISIT
        )
        val res = FemaEngine.determine(input)
        assertEquals(FemaStatus.PROI, res.status)
    }
}
