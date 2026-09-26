package com.example.model

/**
 * Statutory FEMA Residential Status classifications
 * under the Foreign Exchange Management Act, 1999 (India).
 */
enum class FemaStatus(
    val code: String,
    val title: String,
    val shortDescription: String
) {
    PRI(
        code = "PRI",
        title = "Person Resident in India",
        shortDescription = "Subject to Indian foreign exchange regulations for PRI. Cannot open or operate NRE/NRO/FCNR accounts; must use Resident/RFC accounts."
    ),
    PROI(
        code = "PROI",
        title = "Person Resident Outside India",
        shortDescription = "Entitled to NRI banking privileges (NRE/NRO/FCNR accounts). Eligible for FDI & portfolio investments under FEMA non-resident routes."
    )
}

enum class FemaDeparturePurpose(val label: String, val indicatesPermanentOverseas: Boolean) {
    EMPLOYMENT_ABROAD("Taking up employment outside India", true),
    BUSINESS_ABROAD("Carrying on business or vocation outside India", true),
    UNCERTAIN_PERIOD_ABROAD("Any other purpose indicating intention to stay abroad for an uncertain period", true),
    TEMPORARY_OTHER("Temporary visit / vacation / business trip / medical / short education", false)
}

enum class FemaArrivalPurpose(val label: String, val indicatesPermanentIndia: Boolean) {
    EMPLOYMENT_IN_INDIA("Taking up employment in India", true),
    BUSINESS_IN_INDIA("Carrying on business or vocation in India", true),
    UNCERTAIN_PERIOD_IN_INDIA("Any other purpose indicating intention to stay in India for an uncertain period (e.g. permanent return)", true),
    TEMPORARY_VISIT("Temporary visit / holiday / family visit / short project", false)
}

data class FemaInput(
    val assesseeName: String = "",
    val pan: String = "",
    val financialYear: String = "FY 2026-27",
    val precedingYearDays: Int = 0,
    val hasGoneOutsideIndia: Boolean = false,
    val departurePurpose: FemaDeparturePurpose = FemaDeparturePurpose.TEMPORARY_OTHER,
    val hasComeToIndia: Boolean = false,
    val arrivalPurpose: FemaArrivalPurpose = FemaArrivalPurpose.TEMPORARY_VISIT,
    val notes: String = ""
)

data class FemaResult(
    val status: FemaStatus,
    val statutoryProvision: String,
    val executiveSummary: String,
    val rationale: List<String>,
    val keyFactors: Map<String, String>,
    val complianceNotes: List<String>,
    val bankingImplications: List<String>
)
