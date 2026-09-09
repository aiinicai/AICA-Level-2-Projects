package com.example.model

import com.squareup.moshi.JsonClass

enum class MappingType(val label: String, val description: String) {
    DIRECT("Direct", "Direct one-to-one statutory correspondence"),
    RENUMBERED("Renumbered", "Retained substantive provision with updated section numbering"),
    RESTRUCTURED("Restructured", "Substantively modified or reorganized across clauses/schedules"),
    SPLIT("Split", "Divided into two or more distinct sections or schedules"),
    MERGED("Merged", "Consolidated from multiple old provisions into a single clause"),
    MOVED_TO_SCHEDULE("Moved to Schedule", "Relocated from the main body into a statutory schedule"),
    MULTIPLE_CORRESPONDING_PROVISIONS("Multiple Provisions", "Corresponds to several distinct provisions"),
    REPEALED("Repealed / Omitted", "Discontinued or sunset in the 2025 Act"),
    NO_CORRESPONDING_PROVISION("No Corresponding Provision", "No counterpart in 2025 Act (sunset, omitted, or phased out)"),
    NEW_PROVISION("New Provision", "Newly introduced provision without direct 1961 precedent"),
    UNVERIFIED("Unverified", "Statutory correspondence yet to be verified"),
    OTHER("Other", "Special statutory arrangement or transitional rule")
}

enum class MappingStatus(val label: String, val isVerified: Boolean) {
    VERIFIED("VERIFIED", true),
    PENDING_REVIEW("PENDING REVIEW", false),
    UNVERIFIED("UNVERIFIED", false),
    NOT_LOADED("DATA NOT YET LOADED", false)
}

enum class TextVerificationStatus(val label: String, val tag: String) {
    TEXT_VERIFIED("TEXT VERIFIED", "verified"),
    TEXT_PENDING_REVIEW("TEXT PENDING REVIEW", "pending_review"),
    TEXT_NOT_LOADED("TEXT NOT LOADED", "not_loaded")
}

enum class ExplanationMode(val label: String, val subtitle: String) {
    SIMPLE("Simple", "Plain English for non-tax professionals"),
    PROFESSIONAL("Professional", "Technical analysis for CAs & Advocates"),
    EXAM_CA_STUDENT("Exam / CA Student", "Key distinctions & exam takeaways")
}

enum class ProvisionType(val label: String) {
    SECTION("Section"),
    SCHEDULE("Schedule"),
    CLAUSE("Clause"),
    RULE("Rule"),
    OTHER("Other")
}

@JsonClass(generateAdapter = true)
data class CorrespondingProvision(
    val type: ProvisionType = ProvisionType.SECTION,
    val number: String,
    val title: String? = null,
    val heading: String? = null,
    val relationship: String? = null,
    val text: String? = null,
    val description: String? = null,
    val source: TaxSource? = null,
    val statutoryTextLoaded: Boolean = false,
    val textStatus: TextVerificationStatus = TextVerificationStatus.TEXT_NOT_LOADED
) {
    val displayLabel: String
        get() = "${type.label} $number"

    val displayHeading: String?
        get() = title ?: heading

    val displayText: String
        get() = if (text.isNullOrBlank()) "Official statutory text not yet loaded." else text

    val isTextLoaded: Boolean
        get() = !text.isNullOrBlank() || statutoryTextLoaded

    val effectiveTextStatus: TextVerificationStatus
        get() = when {
            textStatus == TextVerificationStatus.TEXT_VERIFIED -> TextVerificationStatus.TEXT_VERIFIED
            textStatus == TextVerificationStatus.TEXT_PENDING_REVIEW -> TextVerificationStatus.TEXT_PENDING_REVIEW
            !text.isNullOrBlank() && source?.authorityLevel == AuthorityLevel.PRIMARY -> TextVerificationStatus.TEXT_VERIFIED
            !text.isNullOrBlank() -> TextVerificationStatus.TEXT_PENDING_REVIEW
            else -> TextVerificationStatus.TEXT_NOT_LOADED
        }
}

@JsonClass(generateAdapter = true)
data class SourceReferences(
    val oldProvision: String? = null,
    val newProvision: String? = null,
    val mapping: String? = null,
    val transitionExplanation: String? = null
)

@JsonClass(generateAdapter = true)
data class TaxSection(
    val id: String? = null,
    val oldActName: String? = "Income-tax Act, 1961",
    val oldActYear: String? = "1961",
    val oldSectionNumber: String,
    val oldHeading: String? = null,
    val oldText: String? = null,
    val oldTextStatus: TextVerificationStatus = TextVerificationStatus.TEXT_NOT_LOADED,
    val newSectionNumber: String? = null,
    val newScheduleNumber: String? = null,
    val newHeading: String? = null,
    val newText: String? = null,
    val newTextStatus: TextVerificationStatus = TextVerificationStatus.TEXT_NOT_LOADED,
    val statutoryTextLoaded: Boolean = false,
    val correspondingProvisions: List<CorrespondingProvision> = emptyList(),
    val mappingType: MappingType = MappingType.UNVERIFIED,
    val mappingStatus: MappingStatus = MappingStatus.NOT_LOADED,
    val officialSource: String? = null,
    val sourceUrl: String? = null,
    val oldActSource: TaxSource? = null,
    val newActSource: TaxSource? = null,
    val mappingSource: TaxSource? = null,
    val explanationSources: List<TaxSource> = emptyList(),
    val sourceReferences: SourceReferences? = null,
    val notes: String? = null,
    val aiSummary: String? = null,
    val scheduleExplanation: String? = null,
    val category: String = "General"
) {
    // Effective corresponding provisions list ensuring backward compatibility
    val effectiveCorrespondingProvisions: List<CorrespondingProvision>
        get() {
            if (correspondingProvisions.isNotEmpty()) return correspondingProvisions
            val list = mutableListOf<CorrespondingProvision>()
            if (!newSectionNumber.isNullOrBlank()) {
                list.add(
                    CorrespondingProvision(
                        type = ProvisionType.SECTION,
                        number = newSectionNumber,
                        heading = newHeading,
                        title = newHeading,
                        text = newText,
                        source = newActSource,
                        statutoryTextLoaded = !newText.isNullOrBlank(),
                        textStatus = if (!newText.isNullOrBlank()) TextVerificationStatus.TEXT_VERIFIED else TextVerificationStatus.TEXT_NOT_LOADED
                    )
                )
            }
            if (!newScheduleNumber.isNullOrBlank()) {
                list.add(
                    CorrespondingProvision(
                        type = ProvisionType.SCHEDULE,
                        number = newScheduleNumber,
                        heading = if (newSectionNumber.isNullOrBlank()) newHeading else null,
                        title = if (newSectionNumber.isNullOrBlank()) newHeading else null,
                        text = if (newSectionNumber.isNullOrBlank()) newText else null,
                        source = newActSource,
                        statutoryTextLoaded = if (newSectionNumber.isNullOrBlank()) !newText.isNullOrBlank() else false,
                        textStatus = if (newSectionNumber.isNullOrBlank() && !newText.isNullOrBlank()) TextVerificationStatus.TEXT_VERIFIED else TextVerificationStatus.TEXT_NOT_LOADED
                    )
                )
            }
            return list
        }

    // Convenience display helpers
    val displayOldHeading: String
        get() = oldHeading ?: "Official data not yet loaded"

    val displayOldText: String
        get() = if (oldText.isNullOrBlank()) "Official statutory text not yet loaded." else oldText

    val isOldTextLoaded: Boolean
        get() = !oldText.isNullOrBlank()

    val effectiveOldTextStatus: TextVerificationStatus
        get() = when {
            oldTextStatus == TextVerificationStatus.TEXT_VERIFIED -> TextVerificationStatus.TEXT_VERIFIED
            oldTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW -> TextVerificationStatus.TEXT_PENDING_REVIEW
            !oldText.isNullOrBlank() && oldActSource?.authorityLevel == AuthorityLevel.PRIMARY -> TextVerificationStatus.TEXT_VERIFIED
            !oldText.isNullOrBlank() -> TextVerificationStatus.TEXT_PENDING_REVIEW
            else -> TextVerificationStatus.TEXT_NOT_LOADED
        }

    val displayNewSection: String
        get() {
            if (effectiveCorrespondingProvisions.isNotEmpty()) {
                val sections = effectiveCorrespondingProvisions.filter { it.type == ProvisionType.SECTION }
                val schedules = effectiveCorrespondingProvisions.filter { it.type == ProvisionType.SCHEDULE }
                val parts = mutableListOf<String>()
                if (sections.isNotEmpty()) {
                    parts.add(sections.joinToString(", ") { "Section ${it.number}" })
                }
                if (schedules.isNotEmpty()) {
                    parts.add(schedules.joinToString(", ") { "Schedule ${it.number}" })
                }
                if (parts.isNotEmpty()) return parts.joinToString(" + ")
                return effectiveCorrespondingProvisions.joinToString(", ") { it.displayLabel }
            }
            return if (!newSectionNumber.isNullOrBlank()) "Section $newSectionNumber" else "Official data not yet loaded"
        }

    val displayNewHeading: String
        get() = newHeading ?: "Official data not yet loaded"

    val displayNewText: String
        get() = if (newText.isNullOrBlank()) "Official statutory text not yet loaded." else newText

    val isNewTextLoaded: Boolean
        get() = !newText.isNullOrBlank() || effectiveCorrespondingProvisions.any { !it.text.isNullOrBlank() }

    val effectiveNewTextStatus: TextVerificationStatus
        get() = when {
            newTextStatus == TextVerificationStatus.TEXT_VERIFIED -> TextVerificationStatus.TEXT_VERIFIED
            newTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW -> TextVerificationStatus.TEXT_PENDING_REVIEW
            !newText.isNullOrBlank() && newActSource?.authorityLevel == AuthorityLevel.PRIMARY -> TextVerificationStatus.TEXT_VERIFIED
            !newText.isNullOrBlank() -> TextVerificationStatus.TEXT_PENDING_REVIEW
            effectiveCorrespondingProvisions.any { it.effectiveTextStatus == TextVerificationStatus.TEXT_VERIFIED } -> TextVerificationStatus.TEXT_VERIFIED
            effectiveCorrespondingProvisions.any { it.effectiveTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW } -> TextVerificationStatus.TEXT_PENDING_REVIEW
            else -> TextVerificationStatus.TEXT_NOT_LOADED
        }

    val displaySource: String
        get() = officialSource ?: mappingSource?.publisher ?: "Official data not yet loaded"

    val hasSchedule: Boolean
        get() = effectiveCorrespondingProvisions.any { it.type == ProvisionType.SCHEDULE } || !newScheduleNumber.isNullOrBlank()

    val scheduleProvision: CorrespondingProvision?
        get() = effectiveCorrespondingProvisions.firstOrNull { it.type == ProvisionType.SCHEDULE }

    val mainSectionProvision: CorrespondingProvision?
        get() = effectiveCorrespondingProvisions.firstOrNull { it.type == ProvisionType.SECTION }

    val isDataLoaded: Boolean
        get() = mappingStatus != MappingStatus.NOT_LOADED
}

@JsonClass(generateAdapter = true)
data class TaxSectionsContainer(
    val version: String = "1.0",
    val lastUpdated: String = "",
    val source: String = "",
    val sections: List<TaxSection> = emptyList()
)

fun buildGeminiContext(taxSection: TaxSection): String {
    return buildString {
        appendLine("OLD ACT:")
        appendLine("Section: ${taxSection.oldSectionNumber}")
        appendLine("Heading: ${taxSection.oldHeading ?: "Official data not yet loaded"}")
        appendLine("Text: ${taxSection.oldText ?: "Official statutory text not yet loaded."}")
        if (taxSection.oldActSource != null) {
            appendLine("Old Act Source: [${taxSection.oldActSource.authorityLevel.name}] ${taxSection.oldActSource.publisher} — ${taxSection.oldActSource.title} (${taxSection.oldActSource.url})")
        }
        appendLine()
        appendLine("NEW ACT:")
        if (taxSection.effectiveCorrespondingProvisions.isNotEmpty()) {
            taxSection.effectiveCorrespondingProvisions.forEach { prov ->
                appendLine("- ${prov.type.label}: ${prov.number}")
                val h = prov.displayHeading
                if (!h.isNullOrBlank()) {
                    appendLine("  Heading: $h")
                }
                if (!prov.relationship.isNullOrBlank()) {
                    appendLine("  Relationship: ${prov.relationship}")
                }
            }
        } else {
            appendLine("Section: ${taxSection.newSectionNumber ?: "Official data not yet loaded"}")
            if (!taxSection.newScheduleNumber.isNullOrBlank()) {
                appendLine("Schedule: ${taxSection.newScheduleNumber}")
            }
        }
        appendLine("Heading: ${taxSection.newHeading ?: "Official data not yet loaded"}")
        appendLine("Text: ${taxSection.newText ?: "Official statutory text not yet loaded."}")
        if (taxSection.newActSource != null) {
            appendLine("New Act Source: [${taxSection.newActSource.authorityLevel.name}] ${taxSection.newActSource.publisher} — ${taxSection.newActSource.title} (${taxSection.newActSource.url})")
        }
        appendLine()
        appendLine("MAPPING:")
        appendLine("Type: ${taxSection.mappingType.name} (${taxSection.mappingType.label})")
        appendLine("Status: ${taxSection.mappingStatus.name} (${taxSection.mappingStatus.label})")
        appendLine()
        appendLine("SOURCE PROVENANCE:")
        appendLine("Official Source: ${taxSection.officialSource ?: "Official data not yet loaded"}")
        appendLine("Source URL: ${taxSection.sourceUrl ?: "Not available"}")
        if (taxSection.mappingSource != null) {
            appendLine("Mapping Source: [${taxSection.mappingSource.authorityLevel.name}] ${taxSection.mappingSource.publisher} — ${taxSection.mappingSource.title} (${taxSection.mappingSource.url})")
        }
        if (taxSection.explanationSources.isNotEmpty()) {
            appendLine("Explanation Sources:")
            taxSection.explanationSources.forEach { exp ->
                appendLine("- [${exp.authorityLevel.name}] ${exp.publisher} — ${exp.title} (${exp.url})")
            }
        }
        if (taxSection.sourceReferences != null) {
            val refs = taxSection.sourceReferences
            if (!refs.oldProvision.isNullOrBlank()) appendLine("Old Provision Source Ref: ${refs.oldProvision}")
            if (!refs.newProvision.isNullOrBlank()) appendLine("New Provision Source Ref: ${refs.newProvision}")
            if (!refs.mapping.isNullOrBlank()) appendLine("Mapping Source Ref: ${refs.mapping}")
            if (!refs.transitionExplanation.isNullOrBlank()) appendLine("Transition Source Ref: ${refs.transitionExplanation}")
        }
        if (!taxSection.notes.isNullOrBlank()) {
            appendLine()
            appendLine("NOTES:")
            appendLine(taxSection.notes)
        }
        appendLine()
        appendLine("STATUTORY TEXT AVAILABILITY:")
        if (taxSection.oldText == null && taxSection.newText == null) {
            appendLine("IMPORTANT: The current database does not yet contain the complete statutory text. Therefore Gemini must not pretend that complete statutory text was supplied.")
        } else {
            appendLine("Statutory text is partially or fully loaded.")
        }
    }
}

data class ChatMessage(
    val id: String,
    val sender: MessageSender,
    val text: String,
    val timestamp: Long = System.currentTimeMillis(),
    val attachedSectionNumber: String? = null,
    val explanationMode: ExplanationMode? = null,
    val isStatutoryQuote: Boolean = false
)

enum class MessageSender {
    USER,
    AI,
    SYSTEM
}
