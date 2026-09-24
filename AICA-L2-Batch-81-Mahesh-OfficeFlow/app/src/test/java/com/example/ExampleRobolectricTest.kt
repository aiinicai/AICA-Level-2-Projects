package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.data.model.TeamMember
import com.example.data.model.UserRole
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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
    assertEquals("OfficeFlow", appName)
  }

  @Test
  fun `admin and partner are treated as elevated, manager and member are not`() {
    // Partner is deliberately equivalent to Admin; the whole permission model keys off this.
    assertTrue(member(UserRole.ADMIN).isPartnerOrAdmin)
    assertTrue(member(UserRole.PARTNER).isPartnerOrAdmin)
    assertFalse(member(UserRole.MANAGER).isPartnerOrAdmin)
    assertFalse(member(UserRole.TEAM_MEMBER).isPartnerOrAdmin)
  }

  @Test
  fun `primary admin stays elevated regardless of assigned role`() {
    val demoted = member(UserRole.TEAM_MEMBER).copy(isPrimaryAdmin = true)
    assertTrue("The primary admin must never lock themselves out", demoted.isPartnerOrAdmin)
  }

  private fun member(role: UserRole) = TeamMember(
    id = "uid-test",
    name = "Test",
    role = "Associate",
    userRole = role,
    email = "test@primeaccounting.in"
  )
}
