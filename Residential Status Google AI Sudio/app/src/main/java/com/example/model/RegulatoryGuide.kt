package com.example.model

data class StatutoryTopic(
    val title: String,
    val act: String,
    val summary: String,
    val keyPoints: List<String>
)

object RegulatoryGuideData {
    val topics = listOf(
        StatutoryTopic(
            title = "Unified Tax Year Concept (ITA 2025)",
            act = "Income Tax Act, 2025",
            summary = "Elimination of Previous Year & Assessment Year terminology in favor of a single Tax Year.",
            keyPoints = listOf(
                "Under the Income Tax Act, 2025 (applicable from Tax Year 2026-27), the dual concepts of 'Previous Year' and 'Assessment Year' are unified into a single concept: 'Tax Year'.",
                "For example, 'Tax Year 2026-27' refers directly to the financial period April 1, 2026 to March 31, 2027 in which income is earned and assessed.",
                "Residential status physical stay conditions (182 days, 120 days, 60 days) apply to the physical stay within that specific Tax Year."
            )
        ),
        StatutoryTopic(
            title = "Scope of Total Income (Taxability)",
            act = "Income Tax Act, 2025 / 1961",
            summary = "The extent of Indian income-tax liability depends directly on the residential status of the assessee.",
            keyPoints = listOf(
                "ROR (Resident & Ordinarily Resident): Global income taxable in India (income received, accrued, or arising anywhere in the world). Mandatory disclosure of foreign assets in Schedule FA.",
                "RNOR (Resident but Not Ordinarily Resident): Indian income is taxable. Foreign income is exempt UNLESS derived from a business controlled in or profession set up in India.",
                "NR (Non-Resident): Only income received or deemed to be received in India, or accruing/arising (or deemed to accrue/arise) in India is taxable. Foreign income is 100% tax-free in India."
            )
        ),
        StatutoryTopic(
            title = "Physical Presence & Deemed Residency",
            act = "Income Tax Act, 2025 / 1961",
            summary = "Fundamental conditions and exceptions governing residency.",
            keyPoints = listOf(
                "Basic Rule 1: Stay in India for 182 days or more during the financial year.",
                "Basic Rule 2: Stay in India for 60 days or more during FY AND 365 days or more in 4 preceding FYs.",
                "Exception for Indian Citizen leaving for employment abroad or crew: 60-day limit is replaced by 182 days.",
                "Exception for Visiting Indian Citizen / PIO: 60-day limit is replaced by 182 days (if Indian income <= Rs 15 Lakhs) or 120 days (if Indian income > Rs 15 Lakhs).",
                "Deemed Resident: An Indian citizen with Indian income > Rs 15 Lakhs who is not liable to tax in any other country is deemed resident (always RNOR)."
            )
        ),
        StatutoryTopic(
            title = "ROR vs RNOR Tests",
            act = "Income Tax Act, 2025 / 1961",
            summary = "Tests to determine whether a Resident is Ordinarily Resident or Not Ordinarily Resident.",
            keyPoints = listOf(
                "To become ROR, BOTH conditions must be fulfilled: (1) Resident in at least 2 out of 10 preceding financial years, AND (2) Physical stay >= 730 days in the 7 preceding financial years.",
                "If either condition is NOT satisfied, the assessee is RNOR.",
                "Special Statutory Rule: Visiting Citizen/PIO with Indian income > 15L qualifying under the 120-day rule (120 to 181 days) is automatically classified as RNOR.",
                "Deemed residents are automatically classified as RNOR."
            )
        ),
        StatutoryTopic(
            title = "FEMA: Residency vs Income Tax Act",
            act = "FEMA, 1999 vs IT Act 2025/1961",
            summary = "Crucial distinction between FEMA and Income Tax regimes.",
            keyPoints = listOf(
                "Different FY Tested: Income Tax looks at the CURRENT financial year stay; FEMA looks at the PRECEDING financial year stay (> 182 days).",
                "Strict Threshold: FEMA requires strictly MORE than 182 days (> 182, i.e. 183 or more), whereas Income Tax requires >= 182 days.",
                "Intent Override: In FEMA, intention (taking up employment, business abroad, or indefinite stay) overrides physical stay from the exact date of departure or arrival.",
                "Citizenship Irrelevant: FEMA definition applies equally to Indian citizens and foreign nationals based on physical stay and intent."
            )
        ),
        StatutoryTopic(
            title = "FEMA Bank Accounts & Asset Reclassification",
            act = "FEMA, 1999",
            summary = "Rules governing bank accounts and foreign exchange upon status change.",
            keyPoints = listOf(
                "When a Resident becomes PROI (NRI): Existing resident savings accounts must be converted to NRO (Non-Resident Ordinary) accounts. NRE (Non-Resident External) and FCNR (Foreign Currency Non-Resident) accounts may be opened.",
                "Taxability on NRE/FCNR Interest: Interest earned on NRE and FCNR deposits is completely exempt from Indian Income Tax.",
                "When a PROI returns to India permanently (PRI): NRE/FCNR accounts can be converted to Resident accounts or RFC (Resident Foreign Currency) accounts to retain foreign currency freely."
            )
        )
    )
}
