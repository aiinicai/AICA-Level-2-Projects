package com.example.model

import com.squareup.moshi.JsonClass

enum class SourceType(val label: String) {
    OFFICIAL_ACT("Official Act"),
    OFFICIAL_MAPPING("Official Mapping"),
    OFFICIAL_FAQ("Official FAQ"),
    OFFICIAL_CIRCULAR("Official Circular"),
    OFFICIAL_NOTIFICATION("Official Notification"),
    OFFICIAL_RULE("Official Rule"),
    PROFESSIONAL_COMMENTARY("Professional Commentary"),
    SECONDARY_COMMENTARY("Secondary Commentary")
}

enum class AuthorityLevel(val label: String, val allowsStatutoryText: Boolean) {
    PRIMARY("Primary", true),
    OFFICIAL_GUIDANCE("Official Guidance", false),
    PROFESSIONAL("Professional", false),
    SECONDARY("Secondary", false)
}

@JsonClass(generateAdapter = true)
data class TaxSource(
    val sourceId: String,
    val publisher: String,
    val title: String,
    val sourceType: SourceType,
    val url: String,
    val publicationDate: String? = null,
    val effectiveDate: String? = null,
    val retrievedDate: String? = null,
    val version: String? = null,
    val actName: String? = null,
    val actYear: String? = null,
    val authorityLevel: AuthorityLevel = AuthorityLevel.PRIMARY
)

enum class ExtractionStatus(val label: String) {
    NOT_IMPORTED("Not Imported"),
    IMPORTED("Imported"),
    TEXT_EXTRACTED("Text Extracted"),
    PARSED("Parsed"),
    VALIDATED("Validated"),
    FAILED("Failed")
}

enum class ValidationStatus(val label: String) {
    NOT_VALIDATED("Not Validated"),
    PENDING_REVIEW("Pending Review"),
    VERIFIED("Verified"),
    REJECTED("Rejected")
}

@JsonClass(generateAdapter = true)
data class TaxSourceDocument(
    val sourceId: String,
    val publisher: String,
    val title: String,
    val sourceType: SourceType,
    val url: String,
    val localFileName: String? = null,
    val documentVersion: String? = null,
    val retrievedDate: String? = null,
    val effectiveDate: String? = null,
    val checksum: String? = null,
    val authorityLevel: AuthorityLevel = AuthorityLevel.PRIMARY,
    val extractionStatus: ExtractionStatus = ExtractionStatus.NOT_IMPORTED,
    val validationStatus: ValidationStatus = ValidationStatus.NOT_VALIDATED
)

@JsonClass(generateAdapter = true)
data class TaxImportAudit(
    val timestamp: Long = System.currentTimeMillis(),
    val sourceId: String,
    val recordsImported: Int = 0,
    val recordsValidated: Int = 0,
    val recordsRejected: Int = 0,
    val errors: List<String> = emptyList(),
    val warnings: List<String> = emptyList()
)
