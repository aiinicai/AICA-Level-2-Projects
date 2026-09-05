package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.core.model.Money
import org.junit.Assert.assertEquals
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
    assertEquals("LedgerPro", appName)
  }

  @Test
  fun `test financial conversion precision`() {
    val paise = Money.rupeesToPaise(1250.75)
    assertEquals(125075L, paise)
    assertEquals(1250.75, Money.paiseToRupees(paise), 0.001)
  }

  @Test
  fun `test Indian currency formatting`() {
    val formatted = Money.formatIndianPaise(10000000L) // 1 Lakh Rupees = 1,00,000.00
    assertEquals("₹1,00,000.00", formatted)
  }
}
