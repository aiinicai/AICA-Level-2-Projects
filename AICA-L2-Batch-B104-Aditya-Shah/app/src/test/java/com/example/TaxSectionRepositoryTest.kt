package com.example

import com.example.data.JsonTaxSectionRepository
import com.example.data.ingestion.DefaultTaxSourceImporter
import com.example.data.ingestion.TaxDataValidator
import com.example.model.AuthorityLevel
import com.example.model.ExtractionStatus
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.ProvisionType
import com.example.model.SourceType
import com.example.model.TaxSection
import com.example.model.TaxSource
import com.example.model.TaxSourceDocument
import com.example.model.ValidationStatus
import com.example.model.buildGeminiContext
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TaxSectionRepositoryTest {

    private val actualAssetsJson = """
    {
      "version": "1.2",
      "lastUpdated": "2026-08-26",
      "source": "Official Income Tax Department / CBDT Verified Provenance",
      "sections": [
        {
          "oldSectionNumber": "80C",
          "oldHeading": "Deduction in respect of life insurance premia, contributions to provident fund, etc.",
          "oldText": null,
          "newSectionNumber": "123",
          "newScheduleNumber": "XV",
          "newHeading": "Deduction in respect of investments and specified payments",
          "newText": null,
          "correspondingProvisions": [
            {
              "type": "SECTION",
              "number": "123",
              "title": "Deduction in respect of investments and specified payments",
              "heading": "Deduction in respect of investments and specified payments",
              "relationship": "Substantive deduction provision retaining general deduction limits previously under Section 80C read with Section 80CCE",
              "description": "Substantive deduction provision retaining basic deductions previously under Section 80C read with Section 80CCE",
              "source": {
                "sourceId": "SRC-ACT-2025",
                "publisher": "Income Tax Department",
                "title": "Income-tax Act, 2025 (as amended by Finance Act, 2026)",
                "sourceType": "OFFICIAL_ACT",
                "url": "https://www.incometaxindia.gov.in/documents/d/guest/income_tax_act_2025_as_amended_by_fa_act_2026-pdf",
                "authorityLevel": "PRIMARY"
              }
            },
            {
              "type": "SCHEDULE",
              "number": "XV",
              "title": "Eligible Instruments and Specified Funds for Investment Deductions",
              "heading": "Eligible Instruments and Specified Funds for Investment Deductions",
              "relationship": "Schedule listing eligible investment instruments, approved funds, and qualifying terms",
              "description": "Itemized statutory list of eligible investment instruments, approved funds, and qualifying terms",
              "source": {
                "sourceId": "SRC-ACT-2025",
                "publisher": "Income Tax Department",
                "title": "Income-tax Act, 2025 (as amended by Finance Act, 2026)",
                "sourceType": "OFFICIAL_ACT",
                "url": "https://www.incometaxindia.gov.in/documents/d/guest/income_tax_act_2025_as_amended_by_fa_act_2026-pdf",
                "authorityLevel": "PRIMARY"
              }
            }
          ],
          "mappingType": "RESTRUCTURED",
          "mappingStatus": "VERIFIED",
          "officialSource": "Income Tax Department / CBDT",
          "sourceUrl": "https://www.incometaxindia.gov.in/documents/81799/11848482/FAQs-on-Interplay-and-Transition.pdf/05f80c1a-073c-a5d7-fb6f-55509242be53",
          "oldActSource": {
            "sourceId": "SRC-ACT-1961-80C",
            "publisher": "Income Tax Department",
            "title": "Income-tax Act, 1961 (Section 80C)",
            "sourceType": "OFFICIAL_ACT",
            "url": "https://www.incometaxindia.gov.in/w/section-80c-43",
            "authorityLevel": "PRIMARY"
          },
          "newActSource": {
            "sourceId": "SRC-ACT-2025",
            "publisher": "Income Tax Department",
            "title": "Income-tax Act, 2025 (as amended by Finance Act, 2026)",
            "sourceType": "OFFICIAL_ACT",
            "url": "https://www.incometaxindia.gov.in/documents/d/guest/income_tax_act_2025_as_amended_by_fa_act_2026-pdf",
            "authorityLevel": "PRIMARY"
          },
          "mappingSource": {
            "sourceId": "SRC-CBDT-FAQ-TRANS",
            "publisher": "Income Tax Department / CBDT",
            "title": "Official 1961 ↔ 2025 Comparison Utility, Navigator & Transition FAQs",
            "sourceType": "OFFICIAL_FAQ",
            "url": "https://www.incometaxindia.gov.in/documents/81799/11848482/FAQs-on-Interplay-and-Transition.pdf/05f80c1a-073c-a5d7-fb6f-55509242be53",
            "authorityLevel": "OFFICIAL_GUIDANCE"
          },
          "explanationSources": [
            {
              "sourceId": "SRC-CBDT-FAQ-TRANS",
              "publisher": "Income Tax Department / CBDT",
              "title": "Official CBDT FAQs on Interplay and Transition (Item 18/24)",
              "sourceType": "OFFICIAL_FAQ",
              "url": "https://www.incometaxindia.gov.in/documents/81799/11848482/FAQs-on-Interplay-and-Transition.pdf/05f80c1a-073c-a5d7-fb6f-55509242be53",
              "authorityLevel": "OFFICIAL_GUIDANCE"
            }
          ],
          "sourceReferences": {
            "oldProvision": "Income-tax Act, 1961 (Section 80C read with Section 80CCE)",
            "newProvision": "Income-tax Act, 2025 (Section 123 read with Schedule XV, as amended by Finance Act, 2026)",
            "mapping": "Official Income Tax Department 1961 ↔ 2025 Navigator (https://www.incometaxindia.gov.in/documents/20117/43138/new-income-tax-bill-2025-navigator.pdf/8df3eecc-8a0d-e28d-85c7-4db6310a52dd)",
            "transitionExplanation": "Official CBDT FAQs on Interplay and Transition (https://www.incometaxindia.gov.in/documents/81799/11848482/FAQs-on-Interplay-and-Transition.pdf/05f80c1a-073c-a5d7-fb6f-55509242be53)"
          },
          "notes": "Section 80C of the Income-tax Act, 1961 is structurally represented in the Income-tax Act, 2025 through Section 123 together with Schedule XV. The old Section 80C framework should therefore not be represented as a simple one-to-one renumbering.",
          "scheduleExplanation": "The old Section 80C framework is represented under Section 123 of the 2025 Act, with eligible instruments/details provided through Schedule XV.",
          "aiSummary": null,
          "category": "Deductions"
        },
        {
          "oldSectionNumber": "43B",
          "oldHeading": null,
          "oldText": null,
          "newSectionNumber": null,
          "newScheduleNumber": null,
          "newHeading": null,
          "newText": null,
          "mappingType": "UNVERIFIED",
          "mappingStatus": "NOT_LOADED",
          "officialSource": null,
          "sourceUrl": null,
          "notes": null,
          "aiSummary": null
        },
        {
          "oldSectionNumber": "14A",
          "oldHeading": null,
          "oldText": null,
          "newSectionNumber": null,
          "newScheduleNumber": null,
          "newHeading": null,
          "newText": null,
          "mappingType": "UNVERIFIED",
          "mappingStatus": "NOT_LOADED",
          "officialSource": null,
          "sourceUrl": null,
          "notes": null,
          "aiSummary": null
        },
        {
          "oldSectionNumber": "37",
          "oldHeading": null,
          "oldText": null,
          "newSectionNumber": null,
          "newScheduleNumber": null,
          "newHeading": null,
          "newText": null,
          "mappingType": "UNVERIFIED",
          "mappingStatus": "NOT_LOADED",
          "officialSource": null,
          "sourceUrl": null,
          "notes": null,
          "aiSummary": null
        },
        {
          "oldSectionNumber": "10",
          "oldHeading": null,
          "oldText": null,
          "newSectionNumber": null,
          "newScheduleNumber": null,
          "newHeading": null,
          "newText": null,
          "mappingType": "UNVERIFIED",
          "mappingStatus": "NOT_LOADED",
          "officialSource": null,
          "sourceUrl": null,
          "notes": null,
          "aiSummary": null
        },
        {
          "oldSectionNumber": "2",
          "oldHeading": null,
          "oldText": null,
          "newSectionNumber": null,
          "newScheduleNumber": null,
          "newHeading": null,
          "newText": null,
          "mappingType": "UNVERIFIED",
          "mappingStatus": "NOT_LOADED",
          "officialSource": null,
          "sourceUrl": null,
          "notes": null,
          "aiSummary": null
        }
      ]
    }
    """.trimIndent()

    @Test
    fun `parses json and retrieves all six required sample records`() {
        val repo = JsonTaxSectionRepository(actualAssetsJson)
        val sections = repo.getAllSections()
        assertEquals(6, sections.size)

        val requiredNumbers = listOf("80C", "43B", "14A", "37", "10", "2")
        for (num in requiredNumbers) {
            val sec = repo.getSectionByOldNumber(num)
            assertNotNull("Section $num should exist", sec)
        }
    }

    @Test
    fun `section 80C loads as verified statutory record with section 123 and schedule XV`() {
        val repo = JsonTaxSectionRepository(actualAssetsJson)
        val sec80C = repo.getSectionByOldNumber("80C")
        assertNotNull(sec80C)
        assertEquals("80C", sec80C?.oldSectionNumber)
        assertEquals("Deduction in respect of life insurance premia, contributions to provident fund, etc.", sec80C?.oldHeading)
        assertEquals(MappingStatus.VERIFIED, sec80C?.mappingStatus)
        assertEquals(MappingType.RESTRUCTURED, sec80C?.mappingType)
        assertEquals("Income Tax Department / CBDT", sec80C?.officialSource)
        assertTrue(sec80C?.isDataLoaded == true)

        // Old act source verification
        assertNotNull(sec80C?.oldActSource)
        assertEquals("SRC-ACT-1961-80C", sec80C?.oldActSource?.sourceId)
        assertEquals(AuthorityLevel.PRIMARY, sec80C?.oldActSource?.authorityLevel)
        assertEquals(SourceType.OFFICIAL_ACT, sec80C?.oldActSource?.sourceType)
        assertEquals("https://www.incometaxindia.gov.in/w/section-80c-43", sec80C?.oldActSource?.url)

        // Mapping source verification
        assertNotNull(sec80C?.mappingSource)
        assertEquals("SRC-CBDT-FAQ-TRANS", sec80C?.mappingSource?.sourceId)
        assertEquals(AuthorityLevel.OFFICIAL_GUIDANCE, sec80C?.mappingSource?.authorityLevel)

        // Corresponding provisions verification
        val provisions = sec80C!!.effectiveCorrespondingProvisions
        assertEquals(2, provisions.size)

        val section123 = provisions.firstOrNull { it.type == ProvisionType.SECTION }
        assertNotNull(section123)
        assertEquals("123", section123?.number)
        assertEquals("Deduction in respect of investments and specified payments", section123?.displayHeading)
        assertEquals(AuthorityLevel.PRIMARY, section123?.source?.authorityLevel)

        val scheduleXV = provisions.firstOrNull { it.type == ProvisionType.SCHEDULE }
        assertNotNull(scheduleXV)
        assertEquals("XV", scheduleXV?.number)
        assertEquals("Eligible Instruments and Specified Funds for Investment Deductions", scheduleXV?.displayHeading)

        assertTrue(sec80C.hasSchedule)
        assertEquals("XV", sec80C.scheduleProvision?.number)

        // Null statutory text does not crash and provides clear placeholder
        assertEquals("Official statutory text not yet loaded.", sec80C.displayOldText)
        assertEquals("Official statutory text not yet loaded.", sec80C.displayNewText)

        // Notes check
        assertTrue(sec80C.notes?.contains("Section 123 together with Schedule XV") == true)
    }

    @Test
    fun `remaining sections 43B 14A 37 10 2 remain not loaded`() {
        val repo = JsonTaxSectionRepository(actualAssetsJson)
        val unverifiedNumbers = listOf("43B", "14A", "37", "10", "2")
        for (num in unverifiedNumbers) {
            val sec = repo.getSectionByOldNumber(num)
            assertNotNull("Section $num should exist", sec)
            assertEquals(MappingStatus.NOT_LOADED, sec?.mappingStatus)
            assertEquals(MappingType.UNVERIFIED, sec?.mappingType)
            assertEquals(false, sec?.isDataLoaded)
        }
    }

    @Test
    fun `finds section by old number with prefix tolerance`() {
        val repo = JsonTaxSectionRepository(actualAssetsJson)
        val sec80C = repo.getSectionByOldNumber("80C")
        assertNotNull(sec80C)
        assertEquals("80C", sec80C?.oldSectionNumber)

        val sec43BPrefixed = repo.getSectionByOldNumber("Section 43B")
        assertNotNull(sec43BPrefixed)
        assertEquals("43B", sec43BPrefixed?.oldSectionNumber)
    }

    @Test
    fun `searchSections filters correctly by query and corresponding provisions`() {
        val repo = JsonTaxSectionRepository(actualAssetsJson)

        val searchResult80C = repo.searchSections("80C")
        assertEquals(1, searchResult80C.size)
        assertEquals("80C", searchResult80C[0].oldSectionNumber)

        val searchResult123 = repo.searchSections("123")
        assertEquals(1, searchResult123.size)
        assertEquals("80C", searchResult123[0].oldSectionNumber)

        val searchResultSchedule = repo.searchSections("Schedule XV")
        assertEquals(1, searchResultSchedule.size)
        assertEquals("80C", searchResultSchedule[0].oldSectionNumber)

        val searchResultEmpty = repo.searchSections("")
        assertEquals(6, searchResultEmpty.size)
    }

    @Test
    fun `validator verifies valid section 80C record successfully`() {
        val validator = TaxDataValidator()
        val repo = JsonTaxSectionRepository(actualAssetsJson)
        val sec80C = repo.getSectionByOldNumber("80C")!!

        val result = validator.validateSection(sec80C)
        assertTrue("80C should be valid", result.isValid)
        assertTrue(result.errors.isEmpty())
    }

    @Test
    fun `validator rejects record with missing section number`() {
        val validator = TaxDataValidator()
        val invalidSec = TaxSection(
            oldSectionNumber = "",
            mappingStatus = MappingStatus.UNVERIFIED
        )
        val result = validator.validateSection(invalidSec)
        assertFalse(result.isValid)
        assertTrue(result.errors.any { it.contains("Section number is required") })
    }

    @Test
    fun `validator rejects verified record without heading`() {
        val validator = TaxDataValidator()
        val invalidSec = TaxSection(
            oldSectionNumber = "80D",
            oldHeading = null,
            mappingStatus = MappingStatus.VERIFIED,
            mappingType = MappingType.DIRECT,
            officialSource = "CBDT",
            mappingSource = TaxSource(
                sourceId = "SRC-1",
                publisher = "CBDT",
                title = "CBDT Concordance",
                sourceType = SourceType.OFFICIAL_FAQ,
                url = "https://incometaxindia.gov.in",
                authorityLevel = AuthorityLevel.OFFICIAL_GUIDANCE
            )
        )
        val result = validator.validateSection(invalidSec)
        assertFalse(result.isValid)
        assertTrue(result.errors.any { it.contains("must have an official statutory heading") })
    }

    @Test
    fun `validator rejects statutory text without primary authority source`() {
        val validator = TaxDataValidator()
        val secWithSecondaryStatute = TaxSection(
            oldSectionNumber = "80D",
            oldHeading = "Deduction in respect of health insurance premia",
            oldText = "Statutory text generated or sourced from commentary",
            mappingStatus = MappingStatus.PENDING_REVIEW,
            mappingType = MappingType.DIRECT,
            oldActSource = TaxSource(
                sourceId = "SRC-COMM-1",
                publisher = "Taxmann / Commentary",
                title = "Taxmann Direct Taxes Law",
                sourceType = SourceType.PROFESSIONAL_COMMENTARY,
                url = "https://taxmann.com",
                authorityLevel = AuthorityLevel.PROFESSIONAL
            )
        )
        val result = validator.validateSection(secWithSecondaryStatute)
        assertFalse("Statutory text with PROFESSIONAL authority must be rejected", result.isValid)
        assertTrue(result.errors.any { it.contains("requires a PRIMARY authority source") })
    }

    @Test
    fun `validator rejects official source with invalid url`() {
        val validator = TaxDataValidator()
        val secWithBadUrl = TaxSection(
            oldSectionNumber = "80D",
            oldHeading = "Deduction in respect of medical insurance",
            mappingStatus = MappingStatus.VERIFIED,
            mappingType = MappingType.DIRECT,
            mappingSource = TaxSource(
                sourceId = "SRC-CBDT",
                publisher = "CBDT",
                title = "CBDT Circular",
                sourceType = SourceType.OFFICIAL_CIRCULAR,
                url = "invalid-url-string",
                authorityLevel = AuthorityLevel.OFFICIAL_GUIDANCE
            )
        )
        val result = validator.validateSection(secWithBadUrl)
        assertFalse("Source with invalid URL should fail validation", result.isValid)
        assertTrue(result.errors.any { it.contains("requires a valid HTTP/HTTPS URL") })
    }

    @Test
    fun `validator detects duplicate section numbers in batch`() {
        val validator = TaxDataValidator()
        val batch = listOf(
            TaxSection(
                oldSectionNumber = "80C",
                oldHeading = "Heading 1",
                mappingStatus = MappingStatus.PENDING_REVIEW,
                officialSource = "CBDT",
                mappingSource = TaxSource(
                    sourceId = "S1",
                    publisher = "CBDT",
                    title = "CBDT FAQ",
                    sourceType = SourceType.OFFICIAL_FAQ,
                    url = "https://incometaxindia.gov.in",
                    authorityLevel = AuthorityLevel.OFFICIAL_GUIDANCE
                )
            ),
            TaxSection(
                oldSectionNumber = "80C",
                oldHeading = "Heading 2 Duplicate",
                mappingStatus = MappingStatus.PENDING_REVIEW,
                officialSource = "CBDT",
                mappingSource = TaxSource(
                    sourceId = "S1",
                    publisher = "CBDT",
                    title = "CBDT FAQ",
                    sourceType = SourceType.OFFICIAL_FAQ,
                    url = "https://incometaxindia.gov.in",
                    authorityLevel = AuthorityLevel.OFFICIAL_GUIDANCE
                )
            )
        )
        val batchResult = validator.validateBatch(batch, "SRC-TEST")
        assertEquals(1, batchResult.validSections.size)
        assertEquals(1, batchResult.rejectedSections.size)
        assertEquals(1, batchResult.audit.recordsRejected)
        assertTrue(batchResult.audit.errors.any { it.contains("Duplicate section number detected") })
    }

    @Test
    fun `taxSourceImporter imports candidate records as pending review`() = runBlocking {
        val importer = DefaultTaxSourceImporter()
        val doc = TaxSourceDocument(
            sourceId = "DOC-TEST-001",
            publisher = "Income Tax Department",
            title = "Test Concordance Draft",
            sourceType = SourceType.OFFICIAL_FAQ,
            url = "https://incometaxindia.gov.in/test.pdf",
            authorityLevel = AuthorityLevel.OFFICIAL_GUIDANCE,
            extractionStatus = ExtractionStatus.NOT_IMPORTED,
            validationStatus = ValidationStatus.PENDING_REVIEW
        )

        val candidateJson = """
        {
          "version": "1.0",
          "sections": [
            {
              "oldSectionNumber": "80D",
              "oldHeading": "Medical insurance premia",
              "newSectionNumber": "124",
              "mappingType": "DIRECT",
              "mappingStatus": "VERIFIED",
              "officialSource": "Income Tax Department",
              "mappingSource": {
                "sourceId": "SRC-CBDT",
                "publisher": "CBDT",
                "title": "CBDT FAQ",
                "sourceType": "OFFICIAL_FAQ",
                "url": "https://incometaxindia.gov.in",
                "authorityLevel": "OFFICIAL_GUIDANCE"
              }
            }
          ]
        }
        """.trimIndent()

        val result = importer.importSource(doc, candidateJson)
        assertEquals(1, result.candidateSections.size)
        // By ingestion rule: newly imported candidates start as PENDING_REVIEW
        assertEquals(MappingStatus.PENDING_REVIEW, result.candidateSections[0].mappingStatus)
        assertEquals(ExtractionStatus.PARSED, result.document.extractionStatus)
        assertEquals(1, result.auditLog.recordsImported)
    }

    @Test
    fun `buildGeminiContext produces comprehensive provenance output`() {
        val repo = JsonTaxSectionRepository(actualAssetsJson)
        val sec = repo.getSectionByOldNumber("80C")!!
        val context = buildGeminiContext(sec)

        assertTrue(context.contains("OLD ACT:"))
        assertTrue(context.contains("Section: 80C"))
        assertTrue(context.contains("Old Act Source: [PRIMARY] Income Tax Department"))
        assertTrue(context.contains("NEW ACT:"))
        assertTrue(context.contains("- Section: 123"))
        assertTrue(context.contains("- Schedule: XV"))
        assertTrue(context.contains("New Act Source: [PRIMARY] Income Tax Department"))
        assertTrue(context.contains("MAPPING:"))
        assertTrue(context.contains("Type: RESTRUCTURED"))
        assertTrue(context.contains("Status: VERIFIED"))
        assertTrue(context.contains("SOURCE PROVENANCE:"))
        assertTrue(context.contains("Mapping Source: [OFFICIAL_GUIDANCE] Income Tax Department / CBDT"))
    }

    private fun loadAssetsFileJson(): String {
        val fileInRoot = java.io.File("app/src/main/assets/tax_sections.json")
        val fileInModule = java.io.File("src/main/assets/tax_sections.json")
        return when {
            fileInRoot.exists() -> fileInRoot.readText()
            fileInModule.exists() -> fileInModule.readText()
            else -> java.io.File("/app/src/main/assets/tax_sections.json").readText()
        }
    }

    @Test
    fun `bulk catalogue loads exactly 819 sections from official assets json`() {
        val json = loadAssetsFileJson()
        val repo = JsonTaxSectionRepository(json)
        val all = repo.getAllSections()
        assertEquals(819, all.size)

        // Verify 80C preservation
        val sec80C = repo.getSectionByOldNumber("80C")
        assertNotNull(sec80C)
        assertEquals("123", sec80C?.newSectionNumber)
        assertEquals("XV", sec80C?.newScheduleNumber)
        assertEquals(MappingStatus.VERIFIED, sec80C?.mappingStatus)
        assertEquals(MappingType.RESTRUCTURED, sec80C?.mappingType)
    }

    @Test
    fun `bulk catalogue contains no duplicate section IDs or old section numbers`() {
        val json = loadAssetsFileJson()
        val repo = JsonTaxSectionRepository(json)
        val all = repo.getAllSections()
        
        val uniqueIds = all.map { it.id }.toSet()
        assertEquals(819, uniqueIds.size)

        val uniqueOldNumbers = all.map { it.oldSectionNumber.trim().uppercase() }.toSet()
        assertEquals(819, uniqueOldNumbers.size)
    }

    @Test
    fun `statutory text batch merges correctly into repository and updates ingestion stats`() {
        val json = loadAssetsFileJson()
        val repo = JsonTaxSectionRepository(json)

        val batch1 = repo.loadBatchFromAsset("data/statutory_batch_01_core.json")
        assertNotNull(batch1)
        val audit = repo.applyStatutoryBatch(batch1!!)
        assertNotNull(audit)
        assertTrue(audit.recordsValidated > 0)

        val stats = repo.getIngestionStats()
        assertTrue(stats.act1961TextLoaded > 0)
        assertTrue(stats.act2025TextLoaded > 0)

        // Verify 80C after batch ingestion
        val sec80C = repo.getSectionByOldNumber("80C")
        assertNotNull(sec80C)
        assertTrue(sec80C!!.isOldTextLoaded)
        assertEquals(com.example.model.TextVerificationStatus.TEXT_VERIFIED, sec80C.oldTextStatus)
        assertNotNull(sec80C.oldActSource)
        assertEquals(AuthorityLevel.PRIMARY, sec80C.oldActSource?.authorityLevel)

        // Verify corresponding provisions in 80C
        val provisions = sec80C.effectiveCorrespondingProvisions
        assertEquals(2, provisions.size)
        val sec123 = provisions.find { it.type == ProvisionType.SECTION }
        assertNotNull(sec123)
        assertTrue(sec123!!.isTextLoaded)
        assertEquals(com.example.model.TextVerificationStatus.TEXT_VERIFIED, sec123.textStatus)

        val sched15 = provisions.find { it.type == ProvisionType.SCHEDULE }
        assertNotNull(sched15)
        assertTrue(sched15!!.isTextLoaded)

        // Verify 194J after batch ingestion
        val sec194J = repo.getSectionByOldNumber("194J")
        assertNotNull(sec194J)
        assertTrue(sec194J!!.isOldTextLoaded)
        assertEquals(com.example.model.TextVerificationStatus.TEXT_VERIFIED, sec194J.oldTextStatus)
        assertTrue(sec194J.isNewTextLoaded)
    }
}
