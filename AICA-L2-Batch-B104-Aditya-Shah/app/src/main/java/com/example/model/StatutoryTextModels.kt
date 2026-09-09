package com.example.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class SectionTextPayload(
    val oldSectionNumber: String,
    val oldHeading: String? = null,
    val oldText: String? = null,
    val oldTextStatus: TextVerificationStatus = TextVerificationStatus.TEXT_NOT_LOADED,
    val oldActSource: TaxSource? = null,
    val newSectionNumber: String? = null,
    val newHeading: String? = null,
    val newText: String? = null,
    val newTextStatus: TextVerificationStatus = TextVerificationStatus.TEXT_NOT_LOADED,
    val newActSource: TaxSource? = null,
    val correspondingProvisions: List<CorrespondingProvision> = emptyList(),
    val statutoryTextLoaded: Boolean = false,
    val mappingStatus: MappingStatus? = null,
    val mappingType: MappingType? = null
)

@JsonClass(generateAdapter = true)
data class StatutoryTextBatch(
    val batchId: String,
    val batchNumber: Int = 1,
    val description: String,
    val retrievedDate: String = "2026-08-26",
    val defaultOldSource: TaxSource? = null,
    val defaultNewSource: TaxSource? = null,
    val payloads: List<SectionTextPayload> = emptyList()
)

@JsonClass(generateAdapter = true)
data class IngestionStats(
    val act1961TotalSections: Int = 819,
    val act1961TextLoaded: Int = 0,
    val act1961TextNotLoaded: Int = 819,
    val act1961TextPendingVerification: Int = 0,
    val act2025TotalSections: Int = 536,
    val act2025TextLoaded: Int = 0,
    val act2025TextNotLoaded: Int = 536,
    val act2025TextPendingVerification: Int = 0,
    val totalSchedules: Int = 16,
    val scheduleTextLoaded: Int = 0,
    val scheduleTextNotLoaded: Int = 16,
    val verifiedTextRecords: Int = 0,
    val pendingReviewRecords: Int = 0,
    val importErrors: Int = 0
)
