package com.example.data

import android.content.Context
import com.example.data.ingestion.BatchValidationResult
import com.example.data.ingestion.DefaultTaxSourceImporter
import com.example.data.ingestion.ImportCandidateResult
import com.example.data.ingestion.TaxDataValidator
import com.example.data.ingestion.TaxSourceImporter
import com.example.model.AuthorityLevel
import com.example.model.CorrespondingProvision
import com.example.model.ExtractionStatus
import com.example.model.IngestionStats
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.ProvisionType
import com.example.model.SectionTextPayload
import com.example.model.SourceType
import com.example.model.StatutoryTextBatch
import com.example.model.TaxImportAudit
import com.example.model.TaxSection
import com.example.model.TaxSectionsContainer
import com.example.model.TaxSource
import com.example.model.TaxSourceDocument
import com.example.model.TextVerificationStatus
import com.example.model.ValidationStatus
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

enum class SectionFilterOption(val label: String, val tag: String) {
    ALL("All", "all"),
    VERIFIED("Verified", "verified"),
    PENDING_REVIEW("Pending Review", "pending_review"),
    NO_CORRESPONDING_PROVISION("No Corresponding Provision", "no_corresponding"),
    TEXT_NOT_LOADED("Text Not Loaded", "text_not_loaded"),
    TEXT_LOADED("Text Loaded", "text_loaded")
}

interface TaxSectionRepository {
    fun getAllSections(): List<TaxSection>
    fun getSectionByOldNumber(oldNumber: String): TaxSection?
    fun searchSections(
        query: String,
        category: String? = null,
        status: MappingStatus? = null,
        filterOption: SectionFilterOption = SectionFilterOption.ALL
    ): List<TaxSection>
    fun getCategories(): List<String>
    fun getVersion(): String
    fun getSource(): String
    fun getIngestionStats(): IngestionStats

    // Official Source Ingestion Pipeline
    fun getAvailableDocuments(): List<TaxSourceDocument>
    fun getImportAudits(): List<TaxImportAudit>
    suspend fun importDocument(document: TaxSourceDocument, rawContent: String): ImportCandidateResult
    fun validateCandidateSections(sections: List<TaxSection>, document: TaxSourceDocument): BatchValidationResult
    fun applyStatutoryBatch(batch: StatutoryTextBatch): TaxImportAudit
}

class JsonTaxSectionRepository(
    private val jsonContent: String,
    private val batchJsonContents: List<String> = emptyList(),
    private val importer: TaxSourceImporter = DefaultTaxSourceImporter(),
    private val validator: TaxDataValidator = TaxDataValidator()
) : TaxSectionRepository {

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val container: TaxSectionsContainer = try {
        val adapter = moshi.adapter(TaxSectionsContainer::class.java)
        adapter.fromJson(jsonContent) ?: TaxSectionsContainer()
    } catch (e: Exception) {
        TaxSectionsContainer()
    }

    private val sectionsList: MutableList<TaxSection> = container.sections.toMutableList()
    private val auditLogs: MutableList<TaxImportAudit> = mutableListOf()

    init {
        // Transparently merge statutory text batches
        val batchAdapter = moshi.adapter(StatutoryTextBatch::class.java)
        for (batchJson in batchJsonContents) {
            try {
                val batch = batchAdapter.fromJson(batchJson)
                if (batch != null) {
                    mergeStatutoryBatch(batch)
                }
            } catch (e: Exception) {
                // Ignore parse errors on secondary files
            }
        }
    }

    private fun mergeStatutoryBatch(batch: StatutoryTextBatch): TaxImportAudit {
        var appliedCount = 0
        val warnings = mutableListOf<String>()

        for (payload in batch.payloads) {
            val targetNum = payload.oldSectionNumber.trim().uppercase()
            val index = sectionsList.indexOfFirst { it.oldSectionNumber.trim().uppercase() == targetNum }
            if (index >= 0) {
                val existing = sectionsList[index]

                // Determine default sources if not present on payload
                val resolvedOldSource = payload.oldActSource ?: batch.defaultOldSource ?: existing.oldActSource
                val resolvedNewSource = payload.newActSource ?: batch.defaultNewSource ?: existing.newActSource

                // Merge corresponding provisions
                val mergedProvisions = if (payload.correspondingProvisions.isNotEmpty()) {
                    payload.correspondingProvisions.map { prov ->
                        prov.copy(
                            source = prov.source ?: resolvedNewSource,
                            statutoryTextLoaded = prov.statutoryTextLoaded || !prov.text.isNullOrBlank(),
                            textStatus = if (prov.textStatus != TextVerificationStatus.TEXT_NOT_LOADED) prov.textStatus
                                         else if (!prov.text.isNullOrBlank()) TextVerificationStatus.TEXT_VERIFIED
                                         else TextVerificationStatus.TEXT_NOT_LOADED
                        )
                    }
                } else {
                    existing.effectiveCorrespondingProvisions.map { prov ->
                        val textForProv = if (prov.type == ProvisionType.SECTION && prov.number == (payload.newSectionNumber ?: existing.newSectionNumber)) {
                            payload.newText ?: prov.text
                        } else prov.text
                        prov.copy(
                            text = textForProv,
                            source = prov.source ?: resolvedNewSource,
                            statutoryTextLoaded = !textForProv.isNullOrBlank(),
                            textStatus = if (!textForProv.isNullOrBlank()) TextVerificationStatus.TEXT_VERIFIED else prov.textStatus
                        )
                    }
                }

                val hasOldText = !payload.oldText.isNullOrBlank() || !existing.oldText.isNullOrBlank()
                val hasNewText = !payload.newText.isNullOrBlank() || !existing.newText.isNullOrBlank() || mergedProvisions.any { !it.text.isNullOrBlank() }

                val updatedSection = existing.copy(
                    oldHeading = payload.oldHeading ?: existing.oldHeading,
                    oldText = payload.oldText ?: existing.oldText,
                    oldTextStatus = if (!payload.oldText.isNullOrBlank()) payload.oldTextStatus else existing.oldTextStatus,
                    oldActSource = resolvedOldSource,
                    newSectionNumber = payload.newSectionNumber ?: existing.newSectionNumber,
                    newHeading = payload.newHeading ?: existing.newHeading,
                    newText = payload.newText ?: existing.newText,
                    newTextStatus = if (!payload.newText.isNullOrBlank()) payload.newTextStatus else existing.newTextStatus,
                    newActSource = resolvedNewSource,
                    correspondingProvisions = mergedProvisions,
                    statutoryTextLoaded = payload.statutoryTextLoaded || hasOldText || hasNewText,
                    mappingStatus = payload.mappingStatus ?: existing.mappingStatus,
                    mappingType = payload.mappingType ?: existing.mappingType
                )

                sectionsList[index] = updatedSection
                appliedCount++
            } else {
                warnings.add("Statutory text payload for Section ${payload.oldSectionNumber} not found in 819-section catalogue.")
            }
        }

        val audit = TaxImportAudit(
            sourceId = batch.batchId,
            recordsImported = batch.payloads.size,
            recordsValidated = appliedCount,
            recordsRejected = batch.payloads.size - appliedCount,
            errors = emptyList(),
            warnings = warnings
        )
        auditLogs.add(0, audit)
        return audit
    }

    override fun applyStatutoryBatch(batch: StatutoryTextBatch): TaxImportAudit {
        return mergeStatutoryBatch(batch)
    }

    private val defaultSourceDocuments: List<TaxSourceDocument> = listOf(
        TaxSourceDocument(
            sourceId = "DOC-ITD-ACT-1961",
            publisher = "Income Tax Department",
            title = "Income-tax Act, 1961 (Official Statutory Baseline)",
            sourceType = SourceType.OFFICIAL_ACT,
            url = "https://www.incometaxindia.gov.in/en/income-tax-act",
            documentVersion = "1961.v2025",
            retrievedDate = "2026-08-26",
            effectiveDate = "1962-04-01",
            authorityLevel = AuthorityLevel.PRIMARY,
            extractionStatus = ExtractionStatus.PARSED,
            validationStatus = ValidationStatus.VERIFIED
        ),
        TaxSourceDocument(
            sourceId = "DOC-ITD-ACT-2025",
            publisher = "Income Tax Department / Ministry of Finance",
            title = "Income-tax Act, 2025 (as amended by Finance Act, 2026)",
            sourceType = SourceType.OFFICIAL_ACT,
            url = "https://www.incometaxindia.gov.in/en/income-tax-act-2025",
            documentVersion = "2025.FA2026",
            retrievedDate = "2026-08-26",
            effectiveDate = "2026-04-01",
            authorityLevel = AuthorityLevel.PRIMARY,
            extractionStatus = ExtractionStatus.PARSED,
            validationStatus = ValidationStatus.VERIFIED
        ),
        TaxSourceDocument(
            sourceId = "DOC-CBDT-CONCORDANCE-FAQ",
            publisher = "Income Tax Department / CBDT",
            title = "Official 1961 ↔ 2025 Comparison Utility & Transition Concordance",
            sourceType = SourceType.OFFICIAL_FAQ,
            url = "https://wmstatic-prd.incometaxindia.gov.in/web/guest/utility-to-check-provisions-of-income-tax-act-1961-vis-a-vis-income-tax-act-2025",
            documentVersion = "Utility-v2026",
            retrievedDate = "2026-08-26",
            effectiveDate = "2026-04-01",
            authorityLevel = AuthorityLevel.OFFICIAL_GUIDANCE,
            extractionStatus = ExtractionStatus.PARSED,
            validationStatus = ValidationStatus.VERIFIED
        )
    )

    override fun getAllSections(): List<TaxSection> = sectionsList.toList()

    override fun getSectionByOldNumber(oldNumber: String): TaxSection? {
        val clean = oldNumber.trim().uppercase()
            .removePrefix("SECTION ")
            .removePrefix("SEC ")
            .removePrefix("SEC. ")
            .trim()

        return sectionsList.firstOrNull { section ->
            val num = section.oldSectionNumber.trim().uppercase()
            num == clean || num == oldNumber.trim().uppercase()
        }
    }

    override fun searchSections(
        query: String,
        category: String?,
        status: MappingStatus?,
        filterOption: SectionFilterOption
    ): List<TaxSection> {
        val q = query.trim().lowercase()
            .removePrefix("section ")
            .removePrefix("sec ")
            .removePrefix("sec. ")
            .removePrefix("schedule ")
            .removePrefix("sched ")
            .trim()

        return sectionsList.filter { section ->
            val matchesQuery = if (q.isEmpty()) {
                true
            } else {
                section.oldSectionNumber.lowercase().contains(q) ||
                (section.oldHeading?.lowercase()?.contains(q) == true) ||
                (section.newSectionNumber?.lowercase()?.contains(q) == true) ||
                (section.newScheduleNumber?.lowercase()?.contains(q) == true) ||
                (section.newHeading?.lowercase()?.contains(q) == true) ||
                (section.notes?.lowercase()?.contains(q) == true) ||
                (section.oldText?.lowercase()?.contains(q) == true) ||
                (section.newText?.lowercase()?.contains(q) == true) ||
                (section.category.lowercase().contains(q)) ||
                (section.aiSummary?.lowercase()?.contains(q) == true) ||
                (section.scheduleExplanation?.lowercase()?.contains(q) == true) ||
                section.effectiveCorrespondingProvisions.any { prov ->
                    prov.number.lowercase().contains(q) ||
                    (prov.displayHeading?.lowercase()?.contains(q) == true) ||
                    (prov.relationship?.lowercase()?.contains(q) == true) ||
                    (prov.description?.lowercase()?.contains(q) == true) ||
                    (prov.text?.lowercase()?.contains(q) == true)
                }
            }

            val matchesCategory = category == null || category == "All" || section.category.equals(category, ignoreCase = true)
            val matchesStatus = status == null || section.mappingStatus == status

            val matchesFilterOption = when (filterOption) {
                SectionFilterOption.ALL -> true
                SectionFilterOption.VERIFIED -> section.mappingStatus == MappingStatus.VERIFIED
                SectionFilterOption.PENDING_REVIEW -> section.mappingStatus == MappingStatus.PENDING_REVIEW
                SectionFilterOption.NO_CORRESPONDING_PROVISION -> {
                    section.mappingType == MappingType.NO_CORRESPONDING_PROVISION ||
                    section.mappingType == MappingType.REPEALED ||
                    section.effectiveCorrespondingProvisions.isEmpty()
                }
                SectionFilterOption.TEXT_NOT_LOADED -> {
                    !section.statutoryTextLoaded && section.oldText.isNullOrBlank() && section.newText.isNullOrBlank() &&
                    section.effectiveCorrespondingProvisions.none { !it.text.isNullOrBlank() }
                }
                SectionFilterOption.TEXT_LOADED -> {
                    section.statutoryTextLoaded || !section.oldText.isNullOrBlank() || !section.newText.isNullOrBlank() ||
                    section.effectiveCorrespondingProvisions.any { !it.text.isNullOrBlank() }
                }
            }

            matchesQuery && matchesCategory && matchesStatus && matchesFilterOption
        }
    }

    override fun getCategories(): List<String> {
        val cats = sectionsList.map { it.category }.distinct().filter { it.isNotBlank() }
        return listOf("All") + cats
    }

    override fun getVersion(): String = container.version
    override fun getSource(): String = container.source

    override fun getIngestionStats(): IngestionStats {
        val total1961 = sectionsList.size
        val loaded1961 = sectionsList.count { !it.oldText.isNullOrBlank() }
        val pending1961 = sectionsList.count { !it.oldText.isNullOrBlank() && it.oldTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW }
        val notLoaded1961 = total1961 - loaded1961

        val all2025SectionNumbers = sectionsList.flatMap { sec ->
            sec.effectiveCorrespondingProvisions
                .filter { it.type == ProvisionType.SECTION && it.number.isNotBlank() }
                .map { it.number.trim().uppercase() }
                .let { if (it.isEmpty() && !sec.newSectionNumber.isNullOrBlank()) listOf(sec.newSectionNumber.trim().uppercase()) else it }
        }.distinct()

        val total2025 = if (all2025SectionNumbers.isNotEmpty()) all2025SectionNumbers.size else 536
        val loaded2025 = sectionsList.count { sec ->
            !sec.newText.isNullOrBlank() || sec.effectiveCorrespondingProvisions.any { it.type == ProvisionType.SECTION && !it.text.isNullOrBlank() }
        }
        val pending2025 = sectionsList.count { sec ->
            (!sec.newText.isNullOrBlank() && sec.newTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW) ||
            sec.effectiveCorrespondingProvisions.any { it.textStatus == TextVerificationStatus.TEXT_PENDING_REVIEW }
        }
        val notLoaded2025 = (total2025 - loaded2025).coerceAtLeast(0)

        val loadedSchedules = sectionsList.flatMap { sec ->
            sec.effectiveCorrespondingProvisions.filter { it.type == ProvisionType.SCHEDULE && !it.text.isNullOrBlank() }
        }.map { it.number.trim().uppercase() }.distinct().size

        val totalSchedules = 16
        val notLoadedSchedules = (totalSchedules - loadedSchedules).coerceAtLeast(0)

        val verifiedTextCount = sectionsList.count { sec ->
            sec.statutoryTextLoaded && (
                sec.effectiveOldTextStatus == TextVerificationStatus.TEXT_VERIFIED ||
                sec.effectiveNewTextStatus == TextVerificationStatus.TEXT_VERIFIED
            )
        }

        val pendingReviewCount = sectionsList.count { sec ->
            sec.effectiveOldTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW ||
            sec.effectiveNewTextStatus == TextVerificationStatus.TEXT_PENDING_REVIEW
        }

        return IngestionStats(
            act1961TotalSections = total1961,
            act1961TextLoaded = loaded1961,
            act1961TextNotLoaded = notLoaded1961,
            act1961TextPendingVerification = pending1961,
            act2025TotalSections = total2025,
            act2025TextLoaded = loaded2025,
            act2025TextNotLoaded = notLoaded2025,
            act2025TextPendingVerification = pending2025,
            totalSchedules = totalSchedules,
            scheduleTextLoaded = loadedSchedules,
            scheduleTextNotLoaded = notLoadedSchedules,
            verifiedTextRecords = verifiedTextCount,
            pendingReviewRecords = pendingReviewCount,
            importErrors = auditLogs.sumOf { it.errors.size }
        )
    }

    override fun getAvailableDocuments(): List<TaxSourceDocument> = defaultSourceDocuments

    override fun getImportAudits(): List<TaxImportAudit> = auditLogs.toList()

    override suspend fun importDocument(
        document: TaxSourceDocument,
        rawContent: String
    ): ImportCandidateResult {
        val existingNumbers = sectionsList.map { it.oldSectionNumber.uppercase() }.toSet()
        val result = importer.importSource(
            document = document,
            rawContent = rawContent,
            existingSectionNumbers = existingNumbers
        )
        auditLogs.add(0, result.auditLog)
        return result
    }

    override fun validateCandidateSections(
        sections: List<TaxSection>,
        document: TaxSourceDocument
    ): BatchValidationResult {
        val existingNumbers = sectionsList.map { it.oldSectionNumber.uppercase() }.toSet()
        val result = validator.validateBatch(
            sections = sections,
            sourceId = document.sourceId,
            existingSectionNumbers = existingNumbers
        )
        auditLogs.add(0, result.audit)
        return result
    }

    companion object {
        fun fromAssets(context: Context, fileName: String = "tax_sections.json"): JsonTaxSectionRepository {
            val content = try {
                context.assets.open(fileName).bufferedReader().use { it.readText() }
            } catch (e: Exception) {
                // Fallback default structure
                """
                {
                  "version": "2.2",
                  "lastUpdated": "2026-08-26",
                  "source": "Official Income Tax Department / CBDT Concordance Records",
                  "sections": [
                    {"oldSectionNumber": "80C", "mappingType": "RESTRUCTURED", "mappingStatus": "VERIFIED"},
                    {"oldSectionNumber": "43B", "mappingType": "RENUMBERED", "mappingStatus": "VERIFIED"},
                    {"oldSectionNumber": "14A", "mappingType": "RENUMBERED", "mappingStatus": "VERIFIED"},
                    {"oldSectionNumber": "37", "mappingType": "RENUMBERED", "mappingStatus": "VERIFIED"},
                    {"oldSectionNumber": "10", "mappingType": "MOVED_TO_SCHEDULE", "mappingStatus": "VERIFIED"},
                    {"oldSectionNumber": "2", "mappingType": "DIRECT", "mappingStatus": "VERIFIED"}
                  ]
                }
                """.trimIndent()
            }

            // Scan for batch files in assets/data
            val batchContents = mutableListOf<String>()
            val dataFiles = try {
                context.assets.list("data")?.filter { it.endsWith(".json") } ?: emptyList()
            } catch (e: Exception) {
                emptyList()
            }

            for (dataFile in dataFiles) {
                try {
                    val batchText = context.assets.open("data/$dataFile").bufferedReader().use { it.readText() }
                    if (batchText.isNotBlank()) {
                        batchContents.add(batchText)
                    }
                } catch (e: Exception) {
                    // Ignore missing files
                }
            }

            return JsonTaxSectionRepository(
                jsonContent = content,
                batchJsonContents = batchContents
            )
        }
    }
}

