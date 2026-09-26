package com.example.engine

import com.example.model.FemaArrivalPurpose
import com.example.model.FemaDeparturePurpose
import com.example.model.FemaInput
import com.example.model.FemaResult
import com.example.model.FemaStatus

object FemaEngine {

    fun determine(input: FemaInput): FemaResult {
        val precedingDays = input.precedingYearDays.coerceAtLeast(0)
        val rationale = mutableListOf<String>()
        val complianceNotes = mutableListOf<String>()
        val bankingImplications = mutableListOf<String>()
        val keyFactors = mutableMapOf<String, String>()

        keyFactors["Assessee Name"] = input.assesseeName.ifBlank { "Not Specified" }
        if (input.pan.isNotBlank()) keyFactors["PAN"] = input.pan.uppercase()
        keyFactors["Relevant Financial Year"] = input.financialYear
        keyFactors["Stay in Preceding FY"] = "$precedingDays days"

        val status: FemaStatus
        val statutoryProvision: String

        // Statutory Rule: FEMA requires stay of MORE than 182 days (> 182, i.e., 183+)
        if (precedingDays > 182) {
            rationale.add("Preceding Financial Year Threshold Satisfied: Assessee resided in India for $precedingDays days (> 182 days) in the preceding financial year.")

            if (input.hasGoneOutsideIndia) {
                keyFactors["Departure Outside India"] = "Yes"
                keyFactors["Purpose of Departure"] = input.departurePurpose.label

                if (input.departurePurpose.indicatesPermanentOverseas) {
                    // Falls into Exclusion (A)
                    status = FemaStatus.PROI
                    statutoryProvision = "FEMA, 1999 (Exclusion Clause A)"
                    rationale.add("Exclusion (A) Triggered: Even though preceding year stay exceeded 182 days, the individual has gone or stays outside India for: ${input.departurePurpose.label}.")
                    rationale.add("Under FEMA provisions, such departure immediately converts the residential status to Person Resident Outside India (PROI) from the date of departure.")
                } else {
                    status = FemaStatus.PRI
                    statutoryProvision = "FEMA, 1999 (General Residency Rule)"
                    rationale.add("Exclusion (A) Not Triggered: Departure outside India was for a temporary or vacation purpose without intention to stay abroad for an uncertain period.")
                    rationale.add("The assessee retains residential status as Person Resident in India (PRI).")
                }
            } else {
                keyFactors["Departure Outside India"] = "No (Continues to reside in India)"
                status = FemaStatus.PRI
                statutoryProvision = "FEMA, 1999 (General Residency Rule)"
                rationale.add("Assessee satisfied the physical stay requirement (> 182 days in preceding FY) and has not departed India for employment, business, or uncertain period abroad.")
            }
        } else {
            // Stay <= 182 days in preceding FY
            rationale.add("Preceding FY Physical Threshold Not Met: Stay was $precedingDays days (statutory requirement is strictly MORE than 182 days).")

            if (input.hasComeToIndia) {
                keyFactors["Arrival in India"] = "Yes"
                keyFactors["Purpose of Arrival"] = input.arrivalPurpose.label

                if (input.arrivalPurpose.indicatesPermanentIndia) {
                    // Falls into Inclusion (B)
                    status = FemaStatus.PRI
                    statutoryProvision = "FEMA, 1999 (Inclusion Clause B)"
                    rationale.add("Inclusion (B) Satisfied: Although preceding year stay was <= 182 days, the individual has come to or stays in India for: ${input.arrivalPurpose.label}.")
                    rationale.add("Under FEMA provisions, arriving for employment, business, or indefinite relocation confers Person Resident in India (PRI) status from the date of arrival.")
                } else {
                    status = FemaStatus.PROI
                    statutoryProvision = "FEMA, 1999 (Relocation & Non-Residency Rules)"
                    rationale.add("Inclusion (B) Not Satisfied: Coming to India for a temporary visit, vacation, or short project does not confer PRI status.")
                    rationale.add("The assessee remains a Person Resident Outside India (PROI).")
                }
            } else {
                keyFactors["Arrival in India"] = "No"
                status = FemaStatus.PROI
                statutoryProvision = "FEMA, 1999 (Non-Residency Rule)"
                rationale.add("Assessee stayed <= 182 days in preceding FY and has not come to or stayed in India during the current FY.")
                rationale.add("The individual is classified as a Person Resident Outside India (PROI).")
            }
        }

        // Regulatory & Banking Implications
        when (status) {
            FemaStatus.PRI -> {
                bankingImplications.add("Bank Accounts: Must hold Resident Rupee Bank Accounts. If returning from abroad, NRE/FCNR accounts must be redesignated as Resident Savings Accounts or transferred to RFC (Resident Foreign Currency) accounts.")
                bankingImplications.add("RFC Account Advantage: Funds held in RFC accounts can be maintained in freely convertible foreign currencies without restriction.")
                bankingImplications.add("LRS Eligibility: Eligible for the Liberalised Remittance Scheme (LRS) up to USD 250,000 per financial year for permissible current/capital account transactions.")
                complianceNotes.add("Foreign Assets: An individual who becomes PRI can continue to hold, own, transfer, or invest in foreign currency, foreign securities, or immovable property situated outside India if acquired when resident outside India under FEMA provisions.")
            }
            FemaStatus.PROI -> {
                bankingImplications.add("NRO Account: Existing Indian resident bank accounts must be redesignated as Non-Resident Ordinary (NRO) accounts upon becoming PROI.")
                bankingImplications.add("NRE Account: Permitted to maintain Non-Resident External (NRE) accounts in Indian Rupees (fully repatriable principal and interest).")
                bankingImplications.add("FCNR(B) Deposit: Permitted to maintain Foreign Currency Non-Resident (Bank) deposits in foreign currencies (free from exchange rate risk).")
                complianceNotes.add("Acquisition of Immovable Property: PROI (NRIs/OCIs) can acquire residential and commercial properties in India, but CANNOT acquire agricultural land, plantation property, or farmhouses [FEMA Non-Debt Instruments Rules].")
                complianceNotes.add("Investment Routes: Eligible to invest in Indian shares, securities, and mutual funds under FDI or Portfolio Investment Scheme (PIS) on repatriable or non-repatriable basis.")
            }
        }

        val executiveSummary = buildString {
            append("The assessee, ${input.assesseeName.ifBlank { "The Assessee" }}, is determined to be a ")
            append(status.title.uppercase())
            append(" (${status.code}) for ")
            append(input.financialYear)
            append(" under ")
            append(statutoryProvision)
            append(".")
        }

        return FemaResult(
            status = status,
            statutoryProvision = statutoryProvision,
            executiveSummary = executiveSummary,
            rationale = rationale,
            keyFactors = keyFactors,
            complianceNotes = complianceNotes,
            bankingImplications = bankingImplications
        )
    }
}
