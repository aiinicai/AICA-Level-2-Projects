package com.example.model

/**
 * Statutory Income Tax Residential Status classifications
 * under the Income Tax Act, 1961 / Income Tax Act, 2025 (India).
 */
enum class IncomeTaxStatus(
    val code: String,
    val title: String,
    val shortDescription: String
) {
    ROR(
        code = "ROR",
        title = "Resident and Ordinarily Resident",
        shortDescription = "Global income is fully taxable in India. Mandatory disclosure of all foreign assets & bank accounts."
    ),
    RNOR(
        code = "RNOR",
        title = "Resident but Not Ordinarily Resident",
        shortDescription = "Indian-sourced income is taxable. Foreign income is exempt UNLESS derived from a business controlled in or profession set up in India."
    ),
    NR(
        code = "NR",
        title = "Non-Resident",
        shortDescription = "Only income received, accrued, or deemed to accrue/arise in India is taxable. Foreign income is completely tax-free in India."
    )
}

/**
 * Assessee category for Income Tax determination.
 */
enum class ITCategory(val label: String, val subtitle: String) {
    STANDARD(
        label = "Standard Individual",
        subtitle = "General resident/individual assessee"
    ),
    CITIZEN_LEAVING(
        label = "Citizen Leaving for Employment / Crew",
        subtitle = "Indian citizen leaving India for overseas employment or crew of Indian ship"
    ),
    VISITING_CITIZEN_OR_PIO(
        label = "Visiting Citizen / Person of Indian Origin (PIO)",
        subtitle = "Indian citizen or PIO residing abroad visiting India during the year"
    )
}

object TaxYears {
    val INCOME_TAX_YEARS = listOf(
        "Tax Year 2026-27 (ITA 2025)",
        "FY 2025-26 / AY 2026-27 (ITA 1961)",
        "FY 2024-25 / AY 2025-26 (ITA 1961)",
        "FY 2023-24 / AY 2024-25 (ITA 1961)"
    )

    val FEMA_FINANCIAL_YEARS = listOf(
        "FY 2026-27",
        "FY 2025-26",
        "FY 2024-25",
        "FY 2023-24"
    )

    fun isIta2025(selectedYear: String): Boolean {
        return selectedYear.contains("ITA 2025") || selectedYear.startsWith("Tax Year")
    }

    fun getActTitle(selectedYear: String): String {
        return if (isIta2025(selectedYear)) "Income Tax Act, 2025" else "Income Tax Act, 1961"
    }

    fun getYearLabel(selectedYear: String): String {
        return if (isIta2025(selectedYear)) "Tax Year" else "Assessment Year"
    }
}

data class IncomeTaxInput(
    val assesseeName: String = "",
    val pan: String = "",
    val assessmentYear: String = "Tax Year 2026-27 (ITA 2025)",
    val daysInFY: Int = 0,
    val category: ITCategory = ITCategory.STANDARD,
    val indianIncomeExceeds15L: Boolean = false,
    val daysInPreceding4Years: Int = 0,
    val residentIn2Of10Years: Boolean = false,
    val daysInPreceding7Years: Int = 0,
    val isIndianCitizen: Boolean = true,
    val notLiableToTaxElsewhere: Boolean = false,
    val notes: String = ""
)

data class IncomeTaxResult(
    val status: IncomeTaxStatus,
    val primaryConditionMet: Boolean,
    val secondaryConditionMet: Boolean,
    val isDeemedResident: Boolean,
    val isMandatoryRNOR: Boolean,
    val statutoryProvision: String,
    val executiveSummary: String,
    val rationale: List<String>,
    val keyFactors: Map<String, String>,
    val caveats: List<String>,
    val taxImplications: List<String>
)
