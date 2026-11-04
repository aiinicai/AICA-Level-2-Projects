package com.example

import com.example.data.ai.PhotoKnowledgeBase
import com.example.data.model.FriendRequestStatus
import com.example.data.model.MedStatus
import com.example.data.model.StoryChoice
import com.example.data.model.StoryTurn
import com.example.data.model.UserRole
import com.example.data.repository.GenerationsRepository
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class GenerationsAppTest {

    private lateinit var repository: GenerationsRepository

    @Before
    fun setup() {
        repository = GenerationsRepository()
    }

    @Test
    fun testDefaultRoleIsSenior() {
        assertEquals(UserRole.SENIOR, repository.currentRole.value)
        repository.setRole(UserRole.CHILD)
        assertEquals(UserRole.CHILD, repository.currentRole.value)
        repository.setRole(UserRole.PARENT)
        assertEquals(UserRole.PARENT, repository.currentRole.value)
    }

    @Test
    fun testMarkMedicationTakenAndUndo() {
        val meds = repository.medications.value
        val pendingMed = meds.first { it.status != MedStatus.TAKEN }
        val medId = pendingMed.id

        repository.markMedicationTaken(medId)
        val updatedMed = repository.medications.value.first { it.id == medId }
        assertEquals(MedStatus.TAKEN, updatedMed.status)
        assertNotNull(updatedMed.takenAt)

        // Test Undo
        val undoResult = repository.undoLastMedication()
        assertTrue(undoResult)
        val undoneMed = repository.medications.value.first { it.id == medId }
        assertEquals(MedStatus.PENDING, undoneMed.status)
    }

    @Test
    fun testSleepRecordsTracking() {
        val initialCount = repository.sleepRecords.value.size
        repository.addSleepRecord(
            bedtime = "10:30 PM",
            wakeTime = "7:00 AM",
            hours = 8.5f,
            quality = 5,
            notes = "Peaceful restorative night"
        )
        val updated = repository.sleepRecords.value
        assertEquals(7, updated.size) // Maintained 7-day window
        assertEquals(8.5f, updated.last().durationHours, 0.01f)
    }

    @Test
    fun testParentApprovalAndBlock() {
        val pendingReq = repository.friendRequests.value.first { it.status == FriendRequestStatus.PENDING }
        repository.approveFriendRequest(pendingReq.id)
        val approved = repository.friendRequests.value.first { it.id == pendingReq.id }
        assertEquals(FriendRequestStatus.APPROVED, approved.status)
        assertTrue(approved.safetyApprovedByParent)

        // Block test
        repository.blockUser(pendingReq.id)
        val blocked = repository.friendRequests.value.first { it.id == pendingReq.id }
        assertEquals(FriendRequestStatus.BLOCKED, blocked.status)
    }

    @Test
    fun testPhotoKnowledgeBaseIdentification() {
        val chamomile = PhotoKnowledgeBase.getOrGenerateAnalysis("chamomile flower")
        assertTrue(chamomile.subjectTitle.contains("Chamomile", ignoreCase = true))
        assertTrue(chamomile.medicinalProperties.contains("apigenin", ignoreCase = true))

        val lavender = PhotoKnowledgeBase.getOrGenerateAnalysis("english lavender")
        assertTrue(lavender.subjectTitle.contains("Lavender", ignoreCase = true))
        assertEquals(1, lavender.triviaCorrectIndex)
    }

    @Test
    fun testStoryTurnAdvancement() {
        val initialTurnCount = repository.currentStory.value.turns.size
        val nextTurn = StoryTurn(
            turnNumber = initialTurnCount + 1,
            narratorText = "The bicycle soared gently above the sunset clouds.",
            choices = listOf(StoryChoice("c_test", "Wave to the birds"))
        )
        repository.advanceStoryWithChoice("Pedal faster", nextTurn)
        val updatedStory = repository.currentStory.value
        assertEquals(initialTurnCount + 1, updatedStory.turns.size)
        assertEquals("Pedal faster", updatedStory.turns[initialTurnCount - 1].chosenChoice)
    }

    @Test
    fun testChildPointsAndMissions() {
        val initialPoints = repository.childPoints.value
        val mission = repository.dailyMissions.value.first { !it.isCompleted }
        repository.completeMission(mission.id)
        assertEquals(initialPoints + mission.pointsReward, repository.childPoints.value)
        assertTrue(repository.dailyMissions.value.first { it.id == mission.id }.isCompleted)
    }

    @Test
    fun testMedicationReminderConstants() {
        assertEquals("medication_reminders_channel", com.example.data.reminder.MedicationNotificationManager.CHANNEL_ID)
        assertEquals("com.example.ACTION_MEDICATION_REMINDER", com.example.data.reminder.MedicationNotificationManager.ACTION_REMINDER)
        
        val newMedName = "Vitamin C"
        val newMedTime = "10:00 AM"
        repository.addMedication(newMedName, "1000 mg", newMedTime, "With breakfast")
        val added = repository.medications.value.firstOrNull { it.name == newMedName }
        assertNotNull(added)
        assertEquals(newMedTime, added?.scheduledTime)
    }

    @Test
    fun testBreathingCycleCalculations() {
        val totalSeconds = 60
        val inhaleSeconds = 4
        val holdSeconds = 2
        val exhaleSeconds = 4
        val cycleSeconds = inhaleSeconds + holdSeconds + exhaleSeconds
        
        assertEquals(10, cycleSeconds)
        val totalCycles = totalSeconds / cycleSeconds
        assertEquals(6, totalCycles)

        // Verify phase mapping for any second within cycle (0-9)
        fun getPhaseForSecond(sec: Int): String {
            val mod = sec % cycleSeconds
            return when {
                mod < inhaleSeconds -> "INHALE"
                mod < inhaleSeconds + holdSeconds -> "HOLD"
                else -> "EXHALE"
            }
        }

        assertEquals("INHALE", getPhaseForSecond(0))
        assertEquals("INHALE", getPhaseForSecond(3))
        assertEquals("HOLD", getPhaseForSecond(4))
        assertEquals("HOLD", getPhaseForSecond(5))
        assertEquals("EXHALE", getPhaseForSecond(6))
        assertEquals("EXHALE", getPhaseForSecond(9))
    }
}

