package com.example

import com.example.data.JsonTaxSectionRepository
import com.example.model.ExplanationMode
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.TaxSection
import com.example.model.buildGeminiContext
import com.example.network.GeminiTaxService
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class GeminiTaxServiceTest {

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
        }
      ]
    }
    """.trimIndent()

    private lateinit var repository: JsonTaxSectionRepository
    private lateinit var service: GeminiTaxService

    @Before
    fun setUp() {
        repository = JsonTaxSectionRepository(actualAssetsJson)
        service = GeminiTaxService()
    }

    @Test
    fun `context construction includes structured 80C mapping and missing statutory text notice`() {
        val sec80C = repository.getSectionByOldNumber("80C")
        assertNotNull(sec80C)

        val context = buildGeminiContext(sec80C!!)
        assertTrue("Context must specify Old Section 80C", context.contains("Section: 80C"))
        assertTrue("Context must specify New Section 123", context.contains("- Section: 123"))
        assertTrue("Context must specify Schedule XV", context.contains("- Schedule: XV"))
        assertTrue("Context must specify RESTRUCTURED mapping", context.contains("Type: RESTRUCTURED"))
        assertTrue("Context must specify VERIFIED status", context.contains("Status: VERIFIED"))
        assertTrue("Context must include statutory text availability notice", context.contains("IMPORTANT: The current database does not yet contain the complete statutory text."))
    }

    @Test
    fun `unverified provisions are blocked from AI analysis`() = runBlocking {
        val sec43B = repository.getSectionByOldNumber("43B")
        assertNotNull(sec43B)
        assertEquals(MappingStatus.NOT_LOADED, sec43B?.mappingStatus)

        val result = service.generateSectionExplanation(sec43B!!, ExplanationMode.SIMPLE)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()
        assertTrue("Must state that statutory data is not loaded", text.contains(GeminiTaxService.UNVERIFIED_PROVISION_BLOCK_MSG))
    }

    @Test
    fun `unverified provision in chat is blocked from hallucinating concordance`() = runBlocking {
        val sec43B = repository.getSectionByOldNumber("43B")
        assertNotNull(sec43B)

        val result = service.askQuestion("What is the 2025 section for 43B?", sec43B, ExplanationMode.SIMPLE)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()
        assertTrue("Must block unverified provision in chat", text.contains("Verified statutory data for this provision has not yet been loaded"))
    }

    @Test
    fun `service generates simple explanation with required structure for section 80C`() = runBlocking {
        val sec80C = repository.getSectionByOldNumber("80C")!!
        val result = service.generateSectionExplanation(sec80C, ExplanationMode.SIMPLE)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()

        assertTrue("Must contain Short Answer", text.contains("### Short Answer"))
        assertTrue("Must contain Old Act", text.contains("### Old Act"))
        assertTrue("Must contain New Act", text.contains("### New Act"))
        assertTrue("Must contain What Changed", text.contains("### What Changed?"))
        assertTrue("Must contain Why It Matters", text.contains("### Why It Matters"))
        assertTrue("Must contain Example", text.contains("### Example"))
        assertTrue("Must contain Source", text.contains("### Source"))
        assertTrue("Must mention Section 123", text.contains("Section 123"))
        assertTrue("Must mention Schedule XV", text.contains("Schedule XV"))
    }

    @Test
    fun `service generates professional explanation for CA practitioners`() = runBlocking {
        val sec80C = repository.getSectionByOldNumber("80C")!!
        val result = service.generateSectionExplanation(sec80C, ExplanationMode.PROFESSIONAL)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()

        assertTrue(text.contains("### Short Answer"))
        assertTrue(text.contains("RESTRUCTURED"))
        assertTrue(text.contains("Section 123"))
        assertTrue(text.contains("Schedule XV"))
        assertTrue(text.contains("### Source"))
    }

    @Test
    fun `service generates exam revision explanation with memory aid for CA students`() = runBlocking {
        val sec80C = repository.getSectionByOldNumber("80C")!!
        val result = service.generateSectionExplanation(sec80C, ExplanationMode.EXAM_CA_STUDENT)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()

        assertTrue(text.contains("### Short Answer"))
        assertTrue(text.contains("### Old Act Position"))
        assertTrue(text.contains("### New Act Structure"))
        assertTrue(text.contains("### Memory Aid"))
        assertTrue(text.contains("Section 123"))
        assertTrue(text.contains("Schedule XV"))
    }

    @Test
    fun `answers specific question why is Schedule XV involved accurately`() = runBlocking {
        val sec80C = repository.getSectionByOldNumber("80C")!!
        val result = service.askQuestion("Why is Schedule XV involved?", sec80C, ExplanationMode.SIMPLE)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()

        assertTrue(text.contains("Schedule XV"))
        assertTrue(text.contains("Section 123"))
        assertTrue(text.contains("### Short Answer"))
        assertTrue(text.contains("### Source"))
    }

    @Test
    fun `answers specific question is this just renumbering accurately`() = runBlocking {
        val sec80C = repository.getSectionByOldNumber("80C")!!
        val result = service.askQuestion("Is this just renumbering?", sec80C, ExplanationMode.SIMPLE)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()

        assertTrue(text.contains("No, this is not just a simple renumbering"))
        assertTrue(text.contains("RESTRUCTURED"))
    }

    @Test
    fun `answers general query when no section is attached gracefully`() = runBlocking {
        val result = service.askQuestion("Hello, what does TaxBridge do?", null, ExplanationMode.SIMPLE)
        assertTrue(result.isSuccess)
        val text = result.getOrNull().orEmpty()

        assertTrue(text.contains("Welcome to TaxBridge AI"))
        assertTrue(text.contains("Section 80C"))
    }
}
