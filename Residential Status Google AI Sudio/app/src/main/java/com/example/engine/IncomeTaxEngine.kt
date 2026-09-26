package com.example.engine

import com.example.model.ITCategory
import com.example.model.IncomeTaxInput
import com.example.model.IncomeTaxResult
import com.example.model.IncomeTaxStatus
import com.example.model.TaxYears

object IncomeTaxEngine {

    fun determine(input: IncomeTaxInput): IncomeTaxResult {
        val daysInFY = input.daysInFY.coerceAtLeast(0)
        val daysInPreceding4Years = input.daysInPreceding4Years.coerceAtLeast(0)
        val daysInPreceding7Years = input.daysInPreceding7Years.coerceAtLeast(0)

        val actTitle = TaxYears.getActTitle(input.assessmentYear)
        val yearLabel = TaxYears.getYearLabel(input.assessmentYear)

        val rationale = mutableListOf<String>()
        val caveats = mutableListOf<String>()
        val taxImplications = mutableListOf<String>()
        val keyFactors = mutableMapOf<String, String>()

        keyFactors["Assessee Name"] = input.assesseeName.ifBlank { "Not Specified" }
        if (input.pan.isNotBlank()) keyFactors["PAN"] = input.pan.uppercase()
        keyFactors["Governing Act"] = actTitle
        keyFactors[yearLabel] = input.assessmentYear
        keyFactors["Category"] = input.category.label
        keyFactors["Days in Relevant Year"] = "$daysInFY days"

        var primaryMet = false
        var secondaryMet = false
        var isDeemedResident = false
        var isMandatoryRNOR = false
        var isResident = false
        var status: IncomeTaxStatus
        var statutoryProvision: String

        // STEP 1: Test Primary Physical Presence Condition (>= 182 days)
        if (daysInFY >= 182) {
            primaryMet = true
            isResident = true
            rationale.add("Primary Condition Met: Assessee was present in India for $daysInFY days (>= 182 days) in the relevant financial year under the Primary Residency Rule of the Act.")
        } else {
            rationale.add("Primary Condition Not Met: Stay of $daysInFY days is less than the statutory threshold of 182 days under the General Stay Rule.")

            // STEP 2: Test Secondary Condition (Stay in FY + Preceding 4 Years >= 365 days)
            when (input.category) {
                ITCategory.CITIZEN_LEAVING -> {
                    keyFactors["60-Day Exception"] = "Indian citizen leaving for employment/crew (threshold remains 182 days)"
                    rationale.add("Special Statutory Exception: As an Indian citizen leaving India during the FY for employment abroad or as crew of an Indian ship, the 60-day threshold is substituted with 182 days under the Employment Abroad Exception rule. Secondary 60-day condition does not apply.")
                }
                ITCategory.VISITING_CITIZEN_OR_PIO -> {
                    keyFactors["Indian Income > 15L"] = if (input.indianIncomeExceeds15L) "Yes (Exceeds Rs. 15 Lakhs)" else "No (<= Rs. 15 Lakhs)"
                    if (input.indianIncomeExceeds15L) {
                        // Relaxed threshold: 120 days + 365 days in 4 preceding years
                        keyFactors["Applicable Threshold"] = "120 days (under Finance Act amendment for income > 15 Lakhs)"
                        if (daysInFY >= 120 && daysInPreceding4Years >= 365) {
                            secondaryMet = true
                            isResident = true
                            isMandatoryRNOR = true
                            rationale.add("Special Condition Satisfied: Visiting Indian citizen/PIO with Indian income exceeding Rs. 15 Lakhs stayed for $daysInFY days (>= 120 days) in the FY AND $daysInPreceding4Years days (>= 365 days) in the 4 preceding FYs under the Visiting Citizen Exception rule.")
                            rationale.add("Mandatory RNOR Classification: Under the Visiting Citizen non-ordinarily resident provision, an individual qualifying under this 120-day visiting window is statutorily classified as Resident but Not Ordinarily Resident (RNOR) regardless of past years' stay.")
                        } else {
                            if (daysInFY < 120) {
                                rationale.add("Special Condition Not Met: Stay in FY is $daysInFY days, which is less than the required 120-day threshold.")
                            }
                            if (daysInPreceding4Years < 365) {
                                rationale.add("Preceding 4-Year Test Failed: Stay in preceding 4 financial years is $daysInPreceding4Years days (required >= 365 days).")
                            }
                        }
                    } else {
                        // Indian income <= 15 Lakhs: Threshold is 182 days
                        keyFactors["Applicable Threshold"] = "182 days (Indian income does not exceed Rs. 15 Lakhs)"
                        rationale.add("Statutory Exception: As a visiting Indian citizen or PIO with Indian income of Rs. 15 Lakhs or less, the 60-day threshold is substituted with 182 days under the Visiting Citizen Exception rule.")
                    }
                }
                ITCategory.STANDARD -> {
                    keyFactors["Preceding 4 Years Stay"] = "$daysInPreceding4Years days"
                    if (daysInFY >= 60 && daysInPreceding4Years >= 365) {
                        secondaryMet = true
                        isResident = true
                        rationale.add("Secondary Condition Met: Assessee stayed for $daysInFY days (>= 60 days) in the FY AND $daysInPreceding4Years days (>= 365 days) during the 4 preceding FYs under the Secondary Stay Rule of the Act.")
                    } else {
                        if (daysInFY < 60) {
                            rationale.add("Secondary Condition Not Met: Stay in FY is $daysInFY days (less than statutory 60 days).")
                        }
                        if (daysInPreceding4Years < 365) {
                            rationale.add("Preceding 4-Year Test Failed: Stay in preceding 4 FYs is $daysInPreceding4Years days (less than required 365 days).")
                        }
                    }
                }
            }
        }

        // STEP 3: If not resident via physical presence, check Deemed Residency
        if (!isResident) {
            val eligibleCitizen = input.isIndianCitizen && (input.category != ITCategory.VISITING_CITIZEN_OR_PIO || input.isIndianCitizen)
            if (eligibleCitizen && input.indianIncomeExceeds15L && input.notLiableToTaxElsewhere) {
                isDeemedResident = true
                isResident = true
                isMandatoryRNOR = true
                keyFactors["Deemed Resident Criteria"] = "Citizen + Income > 15L + Not taxable elsewhere"
                rationale.add("Deemed Resident Provision Satisfied: Under Deemed Residency provisions, an Indian citizen whose total income (other than foreign source income) exceeds Rs. 15 Lakhs and who is not liable to tax in any other country or territory is deemed to be a resident in India.")
                rationale.add("Mandatory RNOR Classification: Under the Deemed Resident status rules, a deemed resident is statutorily classified as Resident but Not Ordinarily Resident (RNOR).")
            } else {
                if (!input.isIndianCitizen) {
                    rationale.add("Deemed Residency is not applicable to foreign nationals / foreign passport holders.")
                } else if (!input.indianIncomeExceeds15L) {
                    rationale.add("Deemed Residency does not trigger because total income (other than foreign sources) does not exceed Rs. 15 Lakhs.")
                } else if (!input.notLiableToTaxElsewhere) {
                    rationale.add("Deemed Residency does not trigger because the assessee is liable to tax in an overseas jurisdiction.")
                }
            }
        }

        // STEP 4: Determine Final Status (ROR vs RNOR vs NR)
        if (isResident) {
            if (isMandatoryRNOR) {
                status = IncomeTaxStatus.RNOR
                statutoryProvision = if (isDeemedResident) {
                    "Deemed Resident Rules of the Act"
                } else {
                    "Visiting Citizen Status Rules of the Act"
                }
            } else {
                keyFactors["Resident in 2 of 10 FYs"] = if (input.residentIn2Of10Years) "Yes" else "No"
                keyFactors["Past 7 Years Stay"] = "$daysInPreceding7Years days (threshold: 730 days)"

                val cond1 = input.residentIn2Of10Years
                val cond2 = daysInPreceding7Years >= 730

                if (cond1 && cond2) {
                    status = IncomeTaxStatus.ROR
                    statutoryProvision = if (primaryMet) "Primary Stay Rules of the Act" else "Secondary Stay Rules of the Act"
                    rationale.add("Ordinarily Resident (ROR) Tests Satisfied:")
                    rationale.add("• Condition 1 Met: Assessee was resident in India in at least 2 out of 10 preceding financial years under the Ordinary Residence Rules of the Act.")
                    rationale.add("• Condition 2 Met: Assessee stayed in India for $daysInPreceding7Years days (>= 730 days) during the 7 preceding financial years under the Ordinary Residence Rules of the Act.")
                } else {
                    status = IncomeTaxStatus.RNOR
                    statutoryProvision = if (primaryMet) "Primary Residency Rules of the Act" else "Secondary Residency Rules of the Act"
                    rationale.add("Classified as Resident but Not Ordinarily Resident (RNOR):")
                    if (!cond1) {
                        rationale.add("• Condition 1 Failed: Assessee was NOT resident in India in at least 2 out of 10 preceding financial years.")
                    }
                    if (!cond2) {
                        rationale.add("• Condition 2 Failed: Stay in India during 7 preceding financial years was $daysInPreceding7Years days (less than required 730 days).")
                    }
                }
            }
        } else {
            status = IncomeTaxStatus.NR
            statutoryProvision = "General Non-Residency Rules of $actTitle"
            rationale.add("Non-Resident Determination: The assessee fails to satisfy both the primary condition and the secondary condition, and does not qualify as a Deemed Resident.")
        }

        // STEP 5: Add Tax Implications & Caveats
        when (status) {
            IncomeTaxStatus.ROR -> {
                taxImplications.add("Global Income Taxable: All income accrued, arisen, received, or deemed to accrue/arise in or outside India is chargeable to tax in India.")
                taxImplications.add("Schedule FA Mandatory: Must disclose all Foreign Assets, overseas bank accounts, foreign trusts, and equity interests in the Indian ITR.")
                taxImplications.add("DTAA Relief: Assessee may claim foreign tax credit (FTC) under double tax avoidance agreements for taxes paid abroad on doubly taxed income.")
                caveats.add("Failure to disclose foreign assets in Schedule FA attracts severe penalties under the Black Money (Undisclosed Foreign Income and Assets) and Imposition of Tax Act, 2015.")
            }
            IncomeTaxStatus.RNOR -> {
                taxImplications.add("Indian Income Taxable: All income received or accruing in India is taxable.")
                taxImplications.add("Foreign Income Exemption: Income accruing or arising outside India is NOT taxable in India, UNLESS it is derived from a business controlled in or profession set up in India.")
                taxImplications.add("No Schedule FA Reporting: RNOR assessees are generally not required to disclose foreign assets in Schedule FA of the ITR (subject to specific CBDT clarifications).")
                taxImplications.add("Interest Exemption: Interest on FCNR / NRE deposits continues to remain exempt under banking interest tax-exempt provisions during the period of RNOR status.")
                caveats.add("Keep documentary evidence of the source and location of business control to substantiate the non-taxability of overseas income.")
            }
            IncomeTaxStatus.NR -> {
                taxImplications.add("Foreign Income 100% Tax-Free: Only income accrued, arisen, or received in India is subject to tax under Indian Income Tax provisions.")
                taxImplications.add("TDS: Payments to Non-Residents are subject to higher withholding tax (TDS) under withholding tax provisions unless lower withholding certificate is obtained.")
                taxImplications.add("NRE / FCNR Interest: Interest on NRE and FCNR accounts is fully exempt from tax in India under banking interest tax-exempt provisions.")
                taxImplications.add("Concessional Tax Regime: May opt for special provisions for investment income and long-term capital gains on foreign exchange assets.")
                caveats.add("Ensure that salary for overseas services is credited directly into an overseas bank account to avoid characterization as 'received in India'.")
            }
        }

        val executiveSummary = buildString {
            append("The assessee, ${input.assesseeName.ifBlank { "The Assessee" }}, is determined to be a ")
            append(status.title.uppercase())
            append(" (${status.code}) for ")
            append(input.assessmentYear)
            append(" under ")
            append(statutoryProvision)
            append(".")
        }

        return IncomeTaxResult(
            status = status,
            primaryConditionMet = primaryMet,
            secondaryConditionMet = secondaryMet,
            isDeemedResident = isDeemedResident,
            isMandatoryRNOR = isMandatoryRNOR,
            statutoryProvision = statutoryProvision,
            executiveSummary = executiveSummary,
            rationale = rationale,
            keyFactors = keyFactors,
            caveats = caveats,
            taxImplications = taxImplications
        )
    }
}
