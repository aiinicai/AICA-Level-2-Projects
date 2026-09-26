package com.example.data.repository

import com.example.data.dao.MedicineDao
import com.example.data.model.AppSettingsEntity
import com.example.data.model.Chemist
import com.example.data.model.EmergencyContact
import com.example.data.model.IntakeLog
import com.example.data.model.MedicalReport
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.data.model.Prescription
import com.example.data.model.RoutineVitalLog
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

class MedicineRepository(private val dao: MedicineDao) {

    // --- Profiles ---
    val allProfiles: Flow<List<PatientProfile>> = dao.getAllProfiles()

    suspend fun getProfileById(id: Long): PatientProfile? = dao.getProfileById(id)
    suspend fun insertProfile(profile: PatientProfile): Long = dao.insertProfile(profile)
    suspend fun updateProfile(profile: PatientProfile) = dao.updateProfile(profile)
    suspend fun deleteProfile(id: Long) = dao.deleteProfile(id)
    suspend fun setPrimaryProfile(id: Long) = dao.setPrimaryProfile(id)

    // --- Prescriptions ---
    fun getPrescriptionsForProfile(profileId: Long): Flow<List<Prescription>> =
        dao.getPrescriptionsForProfile(profileId)

    val allPrescriptions: Flow<List<Prescription>> = dao.getAllPrescriptions()

    suspend fun insertPrescription(prescription: Prescription): Long =
        dao.insertPrescription(prescription)

    suspend fun updatePrescription(prescription: Prescription) =
        dao.updatePrescription(prescription)

    suspend fun deletePrescription(id: Long) = dao.deletePrescription(id)

    // --- Medicines ---
    fun getMedicinesForProfile(profileId: Long): Flow<List<Medicine>> =
        dao.getMedicinesForProfile(profileId)

    val allMedicines: Flow<List<Medicine>> = dao.getAllMedicines()

    suspend fun getMedicineById(id: Long): Medicine? = dao.getMedicineById(id)
    suspend fun insertMedicine(medicine: Medicine): Long = dao.insertMedicine(medicine)
    suspend fun updateMedicine(medicine: Medicine) = dao.updateMedicine(medicine)
    suspend fun deleteMedicine(id: Long) = dao.deleteMedicine(id)
    suspend fun decrementStock(medicineId: Long, amount: Int = 1) =
        dao.decrementStock(medicineId, amount)

    // --- Intake Logs / Scheduling ---
    fun getIntakeLogsForDate(profileId: Long, date: String): Flow<List<IntakeLog>> =
        dao.getIntakeLogsForDate(profileId, date, com.example.util.DateUtils.getAlternateDateFormat(date))

    fun getAllIntakeLogsForDate(date: String): Flow<List<IntakeLog>> =
        dao.getAllIntakeLogsForDate(date, com.example.util.DateUtils.getAlternateDateFormat(date))

    suspend fun addIntakeLog(log: IntakeLog): Long = dao.insertIntakeLog(log)
    suspend fun addIntakeLogs(logs: List<IntakeLog>) = dao.insertIntakeLogs(logs)
    suspend fun updateIntakeLog(log: IntakeLog) = dao.updateIntakeLog(log)
    suspend fun deleteIntakeLog(id: Long) = dao.deleteIntakeLog(id)

    suspend fun markIntakeTaken(logId: Long, medicineId: Long) {
        dao.updateIntakeStatus(logId, "TAKEN", System.currentTimeMillis())
        dao.decrementStock(medicineId, 1)
    }

    suspend fun markIntakeSkipped(logId: Long) {
        dao.updateIntakeStatus(logId, "SKIPPED", null)
    }

    suspend fun markIntakePending(logId: Long) {
        dao.updateIntakeStatus(logId, "PENDING", null)
    }

    /**
     * Snooze a medicine and shift all medicines scheduled in the window
     * by snooze duration for that day, ensuring a minimum 5-minute gap after the first medicine.
     */
    suspend fun snoozeMedicine(
        targetLog: IntakeLog,
        snoozeMinutes: Int = 5,
        snoozeEntireSchedule: Boolean = true
    ) {
        val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
        val targetParsed = try {
            timeFormat.parse(targetLog.scheduledTime)
        } catch (_: Exception) { null } ?: return

        val targetCal = Calendar.getInstance().apply { time = targetParsed }
        val targetMinutesFromMidnight = targetCal.get(Calendar.HOUR_OF_DAY) * 60 + targetCal.get(Calendar.MINUTE)

        val newTargetMinutes = (targetMinutesFromMidnight + snoozeMinutes) % (24 * 60)
        val newTargetCal = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, newTargetMinutes / 60)
            set(Calendar.MINUTE, newTargetMinutes % 60)
        }
        val newTargetTimeString = timeFormat.format(newTargetCal.time)

        val updatedTarget = targetLog.copy(
            scheduledTime = newTargetTimeString,
            status = "SNOOZED",
            snoozeMinutes = targetLog.snoozeMinutes + snoozeMinutes,
            originalTime = if (targetLog.originalTime.isEmpty()) targetLog.scheduledTime else targetLog.originalTime
        )
        dao.updateIntakeLog(updatedTarget)

        if (snoozeEntireSchedule) {
            val dateLogs = dao.getIntakeLogsForDate(
                targetLog.profileId,
                targetLog.scheduledDate,
                com.example.util.DateUtils.getAlternateDateFormat(targetLog.scheduledDate)
            ).firstOrNull() ?: emptyList()

            // Find companion medicines scheduled in the next window (10 mins) from target original time
            val companionLogs = dateLogs
                .filter { it.id != targetLog.id && it.status != "TAKEN" }
                .mapNotNull { log ->
                    val parsed = try { timeFormat.parse(log.scheduledTime) } catch (_: Exception) { null }
                    if (parsed != null) {
                        val cal = Calendar.getInstance().apply { time = parsed }
                        val mins = cal.get(Calendar.HOUR_OF_DAY) * 60 + cal.get(Calendar.MINUTE)
                        log to mins
                    } else null
                }
                .filter { (_, mins) ->
                    // Scheduled at or within next 10 minutes of target's previous time
                    mins >= targetMinutesFromMidnight && mins <= (targetMinutesFromMidnight + 10)
                }
                .sortedBy { it.second }

            var previousMedicineTime = newTargetMinutes
            for ((compLog, compMins) in companionLogs) {
                // Shift companion medicine by the snooze duration, ensuring at least 5 mins gap after previous
                val shiftedMins = compMins + snoozeMinutes
                val minSeparatedMins = previousMedicineTime + 5
                val finalMins = maxOf(shiftedMins, minSeparatedMins) % (24 * 60)

                val shiftedCal = Calendar.getInstance().apply {
                    set(Calendar.HOUR_OF_DAY, finalMins / 60)
                    set(Calendar.MINUTE, finalMins % 60)
                }
                val shiftedTimeString = timeFormat.format(shiftedCal.time)

                val updatedCompanion = compLog.copy(
                    scheduledTime = shiftedTimeString,
                    status = "SNOOZED",
                    snoozeMinutes = compLog.snoozeMinutes + snoozeMinutes,
                    originalTime = if (compLog.originalTime.isEmpty()) compLog.scheduledTime else compLog.originalTime
                )
                dao.updateIntakeLog(updatedCompanion)
                previousMedicineTime = finalMins
            }
        }
    }

    // --- Routine Vitals ---
    fun getRoutineVitalsForProfile(profileId: Long): Flow<List<RoutineVitalLog>> =
        dao.getRoutineVitalsForProfile(profileId)

    fun getRoutineVitalsInRange(profileId: Long, startDate: String, endDate: String): Flow<List<RoutineVitalLog>> =
        dao.getRoutineVitalsInRange(profileId, startDate, endDate)

    suspend fun insertRoutineVital(vital: RoutineVitalLog): Long = dao.insertRoutineVital(vital)
    suspend fun updateRoutineVital(vital: RoutineVitalLog) = dao.updateRoutineVital(vital)
    suspend fun deleteRoutineVital(id: Long) = dao.deleteRoutineVital(id)

    // --- Medical Reports ---
    fun getReportsForProfile(profileId: Long): Flow<List<MedicalReport>> =
        dao.getReportsForProfile(profileId)

    fun getLast3ReportsForProfile(profileId: Long): Flow<List<MedicalReport>> =
        dao.getLast3ReportsForProfile(profileId)

    suspend fun insertReport(report: MedicalReport): Long = dao.insertReport(report)
    suspend fun updateReport(report: MedicalReport) = dao.updateReport(report)
    suspend fun deleteReport(id: Long) = dao.deleteReport(id)

    // --- Chemists ---
    val allChemists: Flow<List<Chemist>> = dao.getAllChemists()
    suspend fun insertChemist(chemist: Chemist): Long = dao.insertChemist(chemist)
    suspend fun updateChemist(chemist: Chemist) = dao.updateChemist(chemist)
    suspend fun deleteChemist(id: Long) = dao.deleteChemist(id)
    suspend fun setChemistFavorite(id: Long, isFav: Boolean) = dao.setChemistFavorite(id, isFav)

    // --- Emergency Contacts ---
    val allEmergencyContacts: Flow<List<EmergencyContact>> = dao.getAllEmergencyContacts()
    suspend fun insertEmergencyContact(contact: EmergencyContact): Long =
        dao.insertEmergencyContact(contact)
    suspend fun updateEmergencyContact(contact: EmergencyContact) =
        dao.updateEmergencyContact(contact)
    suspend fun deleteEmergencyContact(id: Long) = dao.deleteEmergencyContact(id)

    // --- App Settings ---
    val appSettings: Flow<AppSettingsEntity?> = dao.getSettings()
    suspend fun saveSettings(settings: AppSettingsEntity) = dao.saveSettings(settings)

    // --- Legal DPDP Erasure ---
    suspend fun wipeAllLocalData() {
        dao.clearAllProfiles()
        dao.clearAllPrescriptions()
        dao.clearAllMedicines()
        dao.clearAllIntakeLogs()
        dao.clearAllReports()
        dao.clearAllRoutineVitals()
        dao.clearAllChemists()
        dao.clearAllEmergencyContacts()
    }
}
