package com.example.data.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
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

@Dao
interface MedicineDao {

    // --- Profiles (DPDP Act Compliance: Local storage, right to delete) ---
    @Query("SELECT * FROM patient_profiles ORDER BY isPrimary DESC, id ASC")
    fun getAllProfiles(): Flow<List<PatientProfile>>

    @Query("SELECT * FROM patient_profiles WHERE id = :id LIMIT 1")
    suspend fun getProfileById(id: Long): PatientProfile?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProfile(profile: PatientProfile): Long

    @Update
    suspend fun updateProfile(profile: PatientProfile)

    @Query("DELETE FROM patient_profiles WHERE id = :id")
    suspend fun deleteProfile(id: Long)

    @Query("UPDATE patient_profiles SET isPrimary = CASE WHEN id = :profileId THEN 1 ELSE 0 END")
    suspend fun setPrimaryProfile(profileId: Long)

    // --- Prescriptions ---
    @Query("SELECT * FROM prescriptions WHERE profileId = :profileId ORDER BY id DESC")
    fun getPrescriptionsForProfile(profileId: Long): Flow<List<Prescription>>

    @Query("SELECT * FROM prescriptions ORDER BY id DESC")
    fun getAllPrescriptions(): Flow<List<Prescription>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPrescription(prescription: Prescription): Long

    @Update
    suspend fun updatePrescription(prescription: Prescription)

    @Query("DELETE FROM prescriptions WHERE id = :id OR parentPrescriptionId = :id")
    suspend fun deletePrescription(id: Long)

    // --- Medicines & Inventory ---
    @Query("SELECT * FROM medicines WHERE profileId = :profileId ORDER BY name ASC")
    fun getMedicinesForProfile(profileId: Long): Flow<List<Medicine>>

    @Query("SELECT * FROM medicines ORDER BY name ASC")
    fun getAllMedicines(): Flow<List<Medicine>>

    @Query("SELECT * FROM medicines WHERE id = :id LIMIT 1")
    suspend fun getMedicineById(id: Long): Medicine?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMedicine(medicine: Medicine): Long

    @Update
    suspend fun updateMedicine(medicine: Medicine)

    @Query("DELETE FROM medicines WHERE id = :id")
    suspend fun deleteMedicine(id: Long)

    @Query("UPDATE medicines SET stockQuantity = MAX(0, stockQuantity - :amount) WHERE id = :medicineId")
    suspend fun decrementStock(medicineId: Long, amount: Int = 1)

    // --- Intake Logs / Schedule ---
    @Query("SELECT * FROM intake_logs WHERE profileId = :profileId AND (scheduledDate = :date OR scheduledDate = :altDate) ORDER BY scheduledTime ASC")
    fun getIntakeLogsForDate(profileId: Long, date: String, altDate: String): Flow<List<IntakeLog>>

    @Query("SELECT * FROM intake_logs WHERE scheduledDate = :date OR scheduledDate = :altDate ORDER BY scheduledTime ASC")
    fun getAllIntakeLogsForDate(date: String, altDate: String): Flow<List<IntakeLog>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertIntakeLog(log: IntakeLog): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertIntakeLogs(logs: List<IntakeLog>)

    @Update
    suspend fun updateIntakeLog(log: IntakeLog)

    @Query("UPDATE intake_logs SET status = :status, takenTimestamp = :timestamp WHERE id = :id")
    suspend fun updateIntakeStatus(id: Long, status: String, timestamp: Long? = null)

    @Query("DELETE FROM intake_logs WHERE id = :id")
    suspend fun deleteIntakeLog(id: Long)

    // --- Medical Reports ---
    @Query("SELECT * FROM medical_reports WHERE profileId = :profileId ORDER BY reportDate DESC")
    fun getReportsForProfile(profileId: Long): Flow<List<MedicalReport>>

    @Query("SELECT * FROM medical_reports WHERE profileId = :profileId ORDER BY reportDate DESC LIMIT 3")
    fun getLast3ReportsForProfile(profileId: Long): Flow<List<MedicalReport>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertReport(report: MedicalReport): Long

    @Update
    suspend fun updateReport(report: MedicalReport)

    @Query("DELETE FROM medical_reports WHERE id = :id")
    suspend fun deleteReport(id: Long)

    // --- Routine Vitals (Hypertension, Blood Sugar, Weight, BMI, Fat %, etc.) ---
    @Query("SELECT * FROM routine_vitals WHERE profileId = :profileId ORDER BY recordDate DESC, recordTime DESC")
    fun getRoutineVitalsForProfile(profileId: Long): Flow<List<RoutineVitalLog>>

    @Query("SELECT * FROM routine_vitals WHERE profileId = :profileId AND recordDate BETWEEN :startDate AND :endDate ORDER BY recordDate ASC, recordTime ASC")
    fun getRoutineVitalsInRange(profileId: Long, startDate: String, endDate: String): Flow<List<RoutineVitalLog>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRoutineVital(vital: RoutineVitalLog): Long

    @Update
    suspend fun updateRoutineVital(vital: RoutineVitalLog)

    @Query("DELETE FROM routine_vitals WHERE id = :id")
    suspend fun deleteRoutineVital(id: Long)

    // --- Chemists (Preferred / Favorites at start) ---
    @Query("SELECT * FROM chemists ORDER BY isFavorite DESC, name ASC")
    fun getAllChemists(): Flow<List<Chemist>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertChemist(chemist: Chemist): Long

    @Update
    suspend fun updateChemist(chemist: Chemist)

    @Query("DELETE FROM chemists WHERE id = :id")
    suspend fun deleteChemist(id: Long)

    @Query("UPDATE chemists SET isFavorite = :isFavorite WHERE id = :id")
    suspend fun setChemistFavorite(id: Long, isFavorite: Boolean)

    // --- Emergency Contacts ---
    @Query("SELECT * FROM emergency_contacts ORDER BY CASE contactType WHEN 'FAMILY' THEN 1 WHEN 'DOCTOR' THEN 2 WHEN 'AMBULANCE' THEN 3 WHEN 'HOSPITAL' THEN 4 ELSE 5 END, name ASC")
    fun getAllEmergencyContacts(): Flow<List<EmergencyContact>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEmergencyContact(contact: EmergencyContact): Long

    @Update
    suspend fun updateEmergencyContact(contact: EmergencyContact)

    @Query("DELETE FROM emergency_contacts WHERE id = :id")
    suspend fun deleteEmergencyContact(id: Long)

    // --- App Settings ---
    @Query("SELECT * FROM app_settings WHERE id = 1 LIMIT 1")
    fun getSettings(): Flow<AppSettingsEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveSettings(settings: AppSettingsEntity)

    // --- DPDP Act: Wipe all user data locally on device ---
    @Query("DELETE FROM patient_profiles")
    suspend fun clearAllProfiles()

    @Query("DELETE FROM prescriptions")
    suspend fun clearAllPrescriptions()

    @Query("DELETE FROM medicines")
    suspend fun clearAllMedicines()

    @Query("DELETE FROM intake_logs")
    suspend fun clearAllIntakeLogs()

    @Query("DELETE FROM medical_reports")
    suspend fun clearAllReports()

    @Query("DELETE FROM routine_vitals")
    suspend fun clearAllRoutineVitals()

    @Query("DELETE FROM chemists")
    suspend fun clearAllChemists()

    @Query("DELETE FROM emergency_contacts")
    suspend fun clearAllEmergencyContacts()
}
