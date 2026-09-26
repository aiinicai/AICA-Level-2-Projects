package com.example

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.example.data.database.AppDatabase
import com.example.data.model.IntakeLog
import com.example.data.model.MedicalReport
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.data.model.Prescription
import com.example.data.model.RoutineVitalLog
import com.example.data.repository.MedicineRepository
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [36])
class ExampleRobolectricTest {

    private lateinit var database: AppDatabase
    private lateinit var repository: MedicineRepository

    @Before
    fun setup() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java)
            .allowMainThreadQueries()
            .build()
        repository = MedicineRepository(database.medicineDao())
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun `read string from context`() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val appName = context.getString(R.string.app_name)
        assertEquals("My Medicine reminder", appName)
    }

    @Test
    fun `verify profile creation and DPDP compliance storage`() = runBlocking {
        val profileId = repository.insertProfile(
            PatientProfile(
                name = "Ramesh Sharma",
                age = 68,
                sex = "Male",
                isPrimary = true
            )
        )
        assertTrue(profileId > 0)

        val profiles = repository.allProfiles.first()
        assertEquals(1, profiles.size)
        assertEquals("Ramesh Sharma", profiles[0].name)
        assertEquals(68, profiles[0].age)
        assertEquals("Male", profiles[0].sex)
    }

    @Test
    fun `verify medicine schedule and 30-min window snooze logic`() = runBlocking {
        val profileId = repository.insertProfile(
            PatientProfile(name = "Kanta Sharma", age = 64, sex = "Female", isPrimary = true)
        )

        val med1Id = repository.insertMedicine(
            Medicine(
                profileId = profileId,
                name = "Telmisartan 40mg",
                dosage = "1 Tablet",
                instructions = "After breakfast",
                timesPerDay = 1,
                scheduledTimes = "08:00",
                stockQuantity = 20
            )
        )

        val med2Id = repository.insertMedicine(
            Medicine(
                profileId = profileId,
                name = "Amlodipine 5mg",
                dosage = "1 Tablet",
                instructions = "With water",
                timesPerDay = 1,
                scheduledTimes = "08:05",
                stockQuantity = 15
            )
        )

        val log1 = IntakeLog(
            medicineId = med1Id,
            profileId = profileId,
            scheduledDate = "2026-09-18",
            scheduledTime = "08:00",
            status = "PENDING",
            originalTime = "08:00"
        )
        val log1Id = repository.addIntakeLog(log1)

        val log2 = IntakeLog(
            medicineId = med2Id,
            profileId = profileId,
            scheduledDate = "2026-09-18",
            scheduledTime = "08:05",
            status = "PENDING",
            originalTime = "08:05"
        )
        repository.addIntakeLog(log2)

        // Snooze log1 by 10 minutes with snoozeEntireSchedule = true
        // Rule: All medicines in next 10 mins shift by 10 mins, and next med must be >= 5 mins after 1st med
        val savedLog1 = log1.copy(id = log1Id)
        repository.snoozeMedicine(savedLog1, 10, snoozeEntireSchedule = true)

        val updatedLogs = repository.getAllIntakeLogsForDate("2026-09-18").first()
        val updatedLog1 = updatedLogs.firstOrNull { it.id == log1Id }
        assertNotNull(updatedLog1)
        assertEquals("08:10", updatedLog1?.scheduledTime)
        assertEquals("SNOOZED", updatedLog1?.status)

        // Log2 was at 08:05 (within 10 mins of 08:00). Shifted by 10 mins = 08:15, and is 5 mins after 08:10.
        val updatedLog2 = updatedLogs.firstOrNull { it.medicineId == med2Id }
        assertNotNull(updatedLog2)
        assertEquals("08:15", updatedLog2?.scheduledTime)
    }

    @Test
    fun `verify routine vital logging with optional fields and retrieval`() = runBlocking {
        val profileId = repository.insertProfile(
            PatientProfile(name = "Surender Gupta", age = 72, sex = "Male", isPrimary = true)
        )

        // Add vital with BP only at 08:30 (no field is mandatory)
        val vitalId1 = repository.insertRoutineVital(
            RoutineVitalLog(
                profileId = profileId,
                recordDate = "2026-09-18",
                recordTime = "08:30",
                vitalCategory = "Blood Pressure",
                systolicBp = 128,
                diastolicBp = 82,
                pulseBpm = 74
            )
        )
        assertTrue(vitalId1 > 0)

        // Add vital with Blood sugar only at 09:15
        val vitalId2 = repository.insertRoutineVital(
            RoutineVitalLog(
                profileId = profileId,
                recordDate = "2026-09-18",
                recordTime = "09:15",
                vitalCategory = "Blood Sugar",
                bloodSugarFasting = 104f
            )
        )
        assertTrue(vitalId2 > 0)

        // Query is ordered DESC by date, time -> 09:15 is first, 08:30 is second
        val vitals = repository.getRoutineVitalsForProfile(profileId).first()
        assertEquals(2, vitals.size)
        assertEquals(104f, vitals[0].bloodSugarFasting)
        assertEquals(128, vitals[1].systolicBp)
    }

    @Test
    fun `verify medical lab report persistence and comparison query`() = runBlocking {
        val profileId = repository.insertProfile(
            PatientProfile(name = "Sunita Rao", age = 59, sex = "Female", isPrimary = true)
        )

        val reportId = repository.insertReport(
            MedicalReport(
                profileId = profileId,
                reportTitle = "Lipid & Sugar Profile",
                labName = "Dr. Lal PathLabs",
                reportDate = "2026-09-18",
                keyMetricsJson = "[{\"metric\":\"HbA1c\",\"value\":\"6.2\",\"unit\":\"%\"},{\"metric\":\"Total Cholesterol\",\"value\":\"192\",\"unit\":\"mg/dL\"}]",
                doctorNotes = "Parameters well controlled on current regimen"
            )
        )
        assertTrue(reportId > 0)

        val reports = repository.getReportsForProfile(profileId).first()
        assertEquals(1, reports.size)
        assertEquals("Dr. Lal PathLabs", reports[0].labName)
        assertTrue(reports[0].keyMetricsJson.contains("HbA1c"))
    }

    @Test
    fun `verify 5 minute snooze defaults and companion schedule shift`() = runBlocking {
        val profileId = repository.insertProfile(
            PatientProfile(name = "Kavita Sen", age = 68, sex = "Female", isPrimary = true)
        )
        val medId = repository.insertMedicine(
            Medicine(profileId = profileId, name = "Amlodipine 5mg", dosage = "1 tablet", scheduledTimes = "09:00")
        )
        val logId = repository.addIntakeLog(
            IntakeLog(
                medicineId = medId,
                profileId = profileId,
                scheduledDate = "2026-09-21",
                scheduledTime = "09:00",
                status = "PENDING"
            )
        )

        val log = repository.getAllIntakeLogsForDate("2026-09-21").first().first { it.id == logId }
        // Snooze with default parameters (snoozeMinutes defaults to 5)
        repository.snoozeMedicine(log)

        val updatedLog = repository.getAllIntakeLogsForDate("2026-09-21").first().first { it.id == logId }
        assertEquals("09:05", updatedLog.scheduledTime)
        assertEquals("SNOOZED", updatedLog.status)
        assertEquals(5, updatedLog.snoozeMinutes)
    }

    @Test
    fun `verify DD-MM-YYYY date format and backward compatibility`() = runBlocking {
        assertEquals("22-09-2026", com.example.util.DateUtils.formatDisplayDate("2026-09-22"))
        assertEquals("22-09-2026", com.example.util.DateUtils.formatDisplayDate("22-09-2026"))
        assertEquals("2026-09-22", com.example.util.DateUtils.getAlternateDateFormat("22-09-2026"))
        assertEquals("22-09-2026", com.example.util.DateUtils.getAlternateDateFormat("2026-09-22"))

        val profileId = repository.insertProfile(
            PatientProfile(name = "Devendra", age = 70, sex = "Male", isPrimary = true)
        )
        val medId = repository.insertMedicine(
            Medicine(profileId = profileId, name = "Metformin 500mg", dosage = "1 tab", scheduledTimes = "08:00")
        )
        // Store log with DD-MM-YYYY format
        val logId = repository.addIntakeLog(
            IntakeLog(
                medicineId = medId,
                profileId = profileId,
                scheduledDate = "22-09-2026",
                scheduledTime = "08:00",
                status = "PENDING"
            )
        )

        // Query using DD-MM-YYYY
        val logsByNewFormat = repository.getAllIntakeLogsForDate("22-09-2026").first()
        assertTrue(logsByNewFormat.any { it.id == logId })

        // Query using legacy format (cross-compatibility)
        val logsByLegacyFormat = repository.getAllIntakeLogsForDate("2026-09-22").first()
        assertTrue(logsByLegacyFormat.any { it.id == logId })
    }
}
