package com.example.data.ingestion

import com.example.model.ExtractionStatus
import com.example.model.MappingStatus
import com.example.model.TaxImportAudit
import com.example.model.TaxSection
import com.example.model.TaxSectionsContainer
import com.example.model.TaxSourceDocument
import com.example.model.ValidationStatus
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

data class ImportCandidateResult(
    val document: TaxSourceDocument,
    val candidateSections: List<TaxSection>,
    val auditLog: TaxImportAudit
)

interface TaxSourceImporter {
    /**
     * Imports a source document and extracts candidate TaxSection records.
     * Newly extracted records are marked as PENDING_REVIEW or UNVERIFIED,
     * never automatically marked as VERIFIED without explicit verification.
     */
    suspend fun importSource(
        document: TaxSourceDocument,
        rawContent: String,
        existingSectionNumbers: Set<String> = emptySet()
    ): ImportCandidateResult

    /**
     * Validates a batch of candidate sections against the strict validation rules.
     */
    fun validateCandidateBatch(
        candidateSections: List<TaxSection>,
        document: TaxSourceDocument,
        existingSectionNumbers: Set<String> = emptySet()
    ): BatchValidationResult
}

class DefaultTaxSourceImporter(
    private val validator: TaxDataValidator = TaxDataValidator()
) : TaxSourceImporter {

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    override suspend fun importSource(
        document: TaxSourceDocument,
        rawContent: String,
        existingSectionNumbers: Set<String>
    ): ImportCandidateResult {
        if (rawContent.isBlank()) {
            val failedDoc = document.copy(
                extractionStatus = ExtractionStatus.FAILED,
                validationStatus = ValidationStatus.REJECTED
            )
            val audit = TaxImportAudit(
                timestamp = System.currentTimeMillis(),
                sourceId = document.sourceId,
                recordsImported = 0,
                recordsValidated = 0,
                recordsRejected = 0,
                errors = listOf("Raw source content is empty or unreadable.")
            )
            return ImportCandidateResult(failedDoc, emptyList(), audit)
        }

        // Parse candidate sections from JSON structure
        val candidates: List<TaxSection> = try {
            val containerAdapter = moshi.adapter(TaxSectionsContainer::class.java)
            val container = containerAdapter.fromJson(rawContent)
            val rawSections = container?.sections ?: emptyList()

            // Ingestion Rule: Newly imported candidates are initially PENDING_REVIEW unless explicitly verified source document
            rawSections.map { section ->
                if (section.mappingStatus == MappingStatus.NOT_LOADED) {
                    section
                } else if (document.validationStatus == ValidationStatus.VERIFIED && section.mappingStatus == MappingStatus.VERIFIED) {
                    section
                } else {
                    // Imported candidates start as PENDING_REVIEW
                    section.copy(mappingStatus = MappingStatus.PENDING_REVIEW)
                }
            }
        } catch (e: Exception) {
            val failedDoc = document.copy(
                extractionStatus = ExtractionStatus.FAILED,
                validationStatus = ValidationStatus.REJECTED
            )
            val audit = TaxImportAudit(
                timestamp = System.currentTimeMillis(),
                sourceId = document.sourceId,
                recordsImported = 0,
                recordsValidated = 0,
                recordsRejected = 0,
                errors = listOf("JSON extraction error: ${e.message}")
            )
            return ImportCandidateResult(failedDoc, emptyList(), audit)
        }

        // Run validation over extracted candidates
        val batchResult = validator.validateBatch(
            sections = candidates,
            sourceId = document.sourceId,
            existingSectionNumbers = existingSectionNumbers
        )

        val updatedDoc = document.copy(
            extractionStatus = ExtractionStatus.PARSED,
            validationStatus = if (batchResult.rejectedSections.isEmpty()) ValidationStatus.PENDING_REVIEW else ValidationStatus.NOT_VALIDATED
        )

        return ImportCandidateResult(
            document = updatedDoc,
            candidateSections = candidates,
            auditLog = batchResult.audit
        )
    }

    override fun validateCandidateBatch(
        candidateSections: List<TaxSection>,
        document: TaxSourceDocument,
        existingSectionNumbers: Set<String>
    ): BatchValidationResult {
        return validator.validateBatch(
            sections = candidateSections,
            sourceId = document.sourceId,
            existingSectionNumbers = existingSectionNumbers
        )
    }
}
