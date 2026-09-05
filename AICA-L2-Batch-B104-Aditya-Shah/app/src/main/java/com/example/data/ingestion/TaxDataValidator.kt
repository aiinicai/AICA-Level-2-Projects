package com.example.data.ingestion

import com.example.model.AuthorityLevel
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.ProvisionType
import com.example.model.TaxImportAudit
import com.example.model.TaxSection

data class ValidationResult(
    val isValid: Boolean,
    val validatedSection: TaxSection?,
    val errors: List<String> = emptyList(),
    val warnings: List<String> = emptyList()
)

data class BatchValidationResult(
    val validSections: List<TaxSection>,
    val rejectedSections: List<TaxSection>,
    val audit: TaxImportAudit
)

class TaxDataValidator {

    fun validateSection(
        section: TaxSection,
        existingSectionNumbers: Set<String> = emptySet(),
        requireVerifiedCriteria: Boolean = false
    ): ValidationResult {
        val errors = mutableListOf<String>()
        val warnings = mutableListOf<String>()

        // 1. Section number validation
        val sectionNumber = section.oldSectionNumber.trim()
        if (sectionNumber.isBlank()) {
            errors.add("Section number is required and cannot be blank.")
        }

        // Duplicate check if passed
        if (existingSectionNumbers.contains(sectionNumber.uppercase())) {
            errors.add("Duplicate section number detected: Section $sectionNumber already exists in dataset.")
        }

        // 2. Heading validation where expected
        if (section.mappingStatus == MappingStatus.VERIFIED && section.oldHeading.isNullOrBlank()) {
            errors.add("Verified section $sectionNumber must have an official statutory heading.")
        }

        // 3. Source presence validation
        val hasSource = section.oldActSource != null ||
                section.mappingSource != null ||
                !section.officialSource.isNullOrBlank()

        if (!hasSource && section.mappingStatus != MappingStatus.NOT_LOADED) {
            errors.add("Source provenance is missing for section $sectionNumber.")
        }

        // 4. Source URL validation for official records
        val sourcesToCheck = listOfNotNull(
            section.oldActSource,
            section.newActSource,
            section.mappingSource
        ) + section.explanationSources

        for (src in sourcesToCheck) {
            if (src.authorityLevel in listOf(AuthorityLevel.PRIMARY, AuthorityLevel.OFFICIAL_GUIDANCE)) {
                if (src.url.isBlank() || (!src.url.startsWith("http://") && !src.url.startsWith("https://"))) {
                    errors.add("Official source '${src.title}' (${src.sourceId}) requires a valid HTTP/HTTPS URL. Found: '${src.url}'")
                }
            }
        }

        // 5. Authority level & Statutory text validation
        // RULE: Only PRIMARY sources can be accepted as verified statutory text
        if (!section.oldText.isNullOrBlank()) {
            val oldAuth = section.oldActSource?.authorityLevel
            if (oldAuth != AuthorityLevel.PRIMARY) {
                errors.add("Old statutory text for section $sectionNumber requires a PRIMARY authority source. Current: ${oldAuth?.label ?: "None"}")
            }
        }

        if (!section.newText.isNullOrBlank()) {
            val newAuth = section.newActSource?.authorityLevel
            if (newAuth != AuthorityLevel.PRIMARY) {
                errors.add("New statutory text for section $sectionNumber requires a PRIMARY authority source. Current: ${newAuth?.label ?: "None"}")
            }
        }

        // 6. Mapping verification & Authority level rules
        if (section.mappingStatus == MappingStatus.VERIFIED) {
            if (section.mappingType == MappingType.UNVERIFIED) {
                errors.add("Section $sectionNumber is marked VERIFIED but has mappingType UNVERIFIED.")
            }

            val mapAuth = section.mappingSource?.authorityLevel ?: section.oldActSource?.authorityLevel
            if (mapAuth != null && mapAuth !in listOf(AuthorityLevel.PRIMARY, AuthorityLevel.OFFICIAL_GUIDANCE)) {
                errors.add("Section $sectionNumber mapping cannot be VERIFIED based on secondary or commentary authority (${mapAuth.label}). Official PRIMARY or OFFICIAL_GUIDANCE source required.")
            }

            if (mapAuth == null && section.officialSource.isNullOrBlank()) {
                errors.add("Section $sectionNumber cannot be marked VERIFIED without certified official source provenance.")
            }
        }

        // 7. Corresponding provisions structural validation
        val provisions = section.effectiveCorrespondingProvisions
        for ((idx, prov) in provisions.withIndex()) {
            if (prov.number.isBlank()) {
                errors.add("Corresponding provision at index $idx for section $sectionNumber has a blank provision number.")
            }
            if (prov.type == ProvisionType.SCHEDULE && !prov.number.matches(Regex("^[IVXLCDM0-9A-Za-z\\-]+$"))) {
                warnings.add("Schedule number '${prov.number}' in section $sectionNumber does not match standard schedule numbering.")
            }
        }

        // Check mapping type consistency
        when (section.mappingType) {
            MappingType.MOVED_TO_SCHEDULE -> {
                if (!section.hasSchedule) {
                    warnings.add("Section $sectionNumber has mappingType MOVED_TO_SCHEDULE but no schedule provision is declared.")
                }
            }
            MappingType.SPLIT, MappingType.MULTIPLE_CORRESPONDING_PROVISIONS -> {
                if (provisions.size < 2) {
                    warnings.add("Section $sectionNumber has mappingType ${section.mappingType.name} but fewer than 2 corresponding provisions are specified.")
                }
            }
            MappingType.RESTRUCTURED -> {
                if (provisions.isEmpty() && section.newSectionNumber.isNullOrBlank()) {
                    warnings.add("Section $sectionNumber is marked RESTRUCTURED but has no 2025 corresponding provisions.")
                }
            }
            MappingType.REPEALED -> {
                if (provisions.isNotEmpty()) {
                    warnings.add("Section $sectionNumber is marked REPEALED but still contains active corresponding provisions.")
                }
            }
            else -> { /* OK */ }
        }

        val isValid = errors.isEmpty()
        val finalSection = if (isValid) {
            if (requireVerifiedCriteria && section.mappingStatus != MappingStatus.VERIFIED) {
                section.copy(mappingStatus = MappingStatus.PENDING_REVIEW)
            } else {
                section
            }
        } else null

        return ValidationResult(
            isValid = isValid,
            validatedSection = finalSection,
            errors = errors,
            warnings = warnings
        )
    }

    fun validateBatch(
        sections: List<TaxSection>,
        sourceId: String,
        existingSectionNumbers: Set<String> = emptySet()
    ): BatchValidationResult {
        val validList = mutableListOf<TaxSection>()
        val rejectedList = mutableListOf<TaxSection>()
        val allErrors = mutableListOf<String>()
        val allWarnings = mutableListOf<String>()

        val seenInBatch = mutableSetOf<String>()

        for (sec in sections) {
            val num = sec.oldSectionNumber.trim().uppercase()
            val hasDuplicateInBatch = seenInBatch.contains(num)
            val combinedExisting = if (hasDuplicateInBatch) {
                existingSectionNumbers + num
            } else {
                existingSectionNumbers
            }

            val result = validateSection(sec, combinedExisting)
            if (result.isValid && !hasDuplicateInBatch) {
                seenInBatch.add(num)
                validList.add(result.validatedSection ?: sec)
            } else {
                rejectedList.add(sec)
                allErrors.addAll(result.errors)
                if (hasDuplicateInBatch) {
                    allErrors.add("Batch contains duplicate provision for Section ${sec.oldSectionNumber}")
                }
            }
            allWarnings.addAll(result.warnings)
        }

        val audit = TaxImportAudit(
            timestamp = System.currentTimeMillis(),
            sourceId = sourceId,
            recordsImported = sections.size,
            recordsValidated = validList.size,
            recordsRejected = rejectedList.size,
            errors = allErrors,
            warnings = allWarnings
        )

        return BatchValidationResult(
            validSections = validList,
            rejectedSections = rejectedList,
            audit = audit
        )
    }
}
