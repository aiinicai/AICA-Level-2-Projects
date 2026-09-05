package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.data.JsonTaxSectionRepository
import com.example.model.AuthorityLevel
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.SourceType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ExampleRobolectricTest {

  @Test
  fun `read string from context`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val appName = context.getString(R.string.app_name)
    assertEquals("TaxBridge AI", appName)
  }

  @Test
  fun `loads tax_sections json and verifies Section 80C official statutory data accuracy`() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val repo = JsonTaxSectionRepository.fromAssets(context)
    val sections = repo.getAllSections()
    assertEquals(819, sections.size)

    val sec80C = repo.getSectionByOldNumber("80C")
    assertNotNull(sec80C)
    
    // 1. Heading verification
    assertEquals(
      "Deduction in respect of life insurance premia, contributions to provident fund, etc.",
      sec80C?.oldHeading
    )
    assertEquals(
      "Deduction in respect of life insurance premia, contributions to provident fund, etc.",
      sec80C?.displayOldHeading
    )

    // 2. Mapping verification
    assertEquals("123", sec80C?.newSectionNumber)
    assertEquals("XV", sec80C?.newScheduleNumber)
    assertEquals(MappingStatus.VERIFIED, sec80C?.mappingStatus)
    assertEquals(MappingType.RESTRUCTURED, sec80C?.mappingType)
    assertEquals(2, sec80C?.effectiveCorrespondingProvisions?.size)
    assertEquals("123", sec80C?.mainSectionProvision?.number)
    assertEquals("XV", sec80C?.scheduleProvision?.number)
    assertTrue(sec80C?.hasSchedule == true)

    // 3. Source provenance verification
    assertNotNull(sec80C?.oldActSource)
    assertEquals("Income Tax Department", sec80C?.oldActSource?.publisher)
    assertEquals("Income-tax Act, 1961 (Section 80C)", sec80C?.oldActSource?.title)
    assertEquals("https://www.incometaxindia.gov.in/w/section-80c-43", sec80C?.oldActSource?.url)
    assertEquals(SourceType.OFFICIAL_ACT, sec80C?.oldActSource?.sourceType)
    assertEquals(AuthorityLevel.PRIMARY, sec80C?.oldActSource?.authorityLevel)

    assertNotNull(sec80C?.newActSource)
    assertEquals("Income Tax Department", sec80C?.newActSource?.publisher)
    assertEquals(
      "Income-tax Act, 2025 (as amended by Finance Act, 2026)",
      sec80C?.newActSource?.title
    )
    assertEquals(
      "https://www.incometaxindia.gov.in/documents/d/guest/income_tax_act_2025_as_amended_by_fa_act_2026-pdf",
      sec80C?.newActSource?.url
    )
    assertEquals(AuthorityLevel.PRIMARY, sec80C?.newActSource?.authorityLevel)

    assertNotNull(sec80C?.mappingSource)
    assertEquals("Income Tax Department / CBDT", sec80C?.mappingSource?.publisher)
    assertEquals(
      "Official 1961 ↔ 2025 Comparison Utility, Navigator & Transition FAQs",
      sec80C?.mappingSource?.title
    )
    assertEquals(
      "https://www.incometaxindia.gov.in/documents/81799/11848482/FAQs-on-Interplay-and-Transition.pdf/05f80c1a-073c-a5d7-fb6f-55509242be53",
      sec80C?.mappingSource?.url
    )
    assertEquals(AuthorityLevel.OFFICIAL_GUIDANCE, sec80C?.mappingSource?.authorityLevel)

    // 4. Statutory text integrity (no fabricated text; null text displays placeholder)
    assertNull(sec80C?.oldText)
    assertNull(sec80C?.newText)
    assertEquals("Official statutory text not yet loaded.", sec80C?.displayOldText)
    assertEquals("Official statutory text not yet loaded.", sec80C?.displayNewText)

    // 5. Sample sections exist in catalogue
    val sampleSections = listOf("43B", "14A", "37", "10", "2")
    for (num in sampleSections) {
      val sec = repo.getSectionByOldNumber(num)
      assertNotNull("Section $num must exist in 819 catalogue", sec)
    }
  }
}
