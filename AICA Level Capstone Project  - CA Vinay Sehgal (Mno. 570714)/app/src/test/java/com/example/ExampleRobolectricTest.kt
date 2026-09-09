package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.data.repository.FirebaseCaRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ExampleRobolectricTest {

    @Test
    fun `read string from context`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val appName = context.getString(R.string.app_name)
        assertEquals("Vinay Sehgal & Co", appName)
    }

    @Test
    fun `verify default roles seeded`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val repository = FirebaseCaRepository(context)
        val roles = repository.roles.value
        assertTrue(roles.contains("Partner"))
        assertTrue(roles.contains("Manager"))
        assertTrue(roles.contains("Accountant"))
        assertTrue(roles.contains("Article"))
    }

    @Test
    fun `verify catalog has income tax and gst`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val repository = FirebaseCaRepository(context)
        val catalog = repository.taskCatalog.value
        assertTrue(catalog.any { it.category == "Income Tax" })
        assertTrue(catalog.any { it.category == "GST" })
        assertTrue(catalog.any { it.category == "PMS" })
    }
}
