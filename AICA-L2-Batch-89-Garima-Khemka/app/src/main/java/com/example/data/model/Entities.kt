package com.example.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "patient_profiles")
data class PatientProfile(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val age: Int,
    val sex: String, // "Male", "Female", "Other"
    val isPrimary: Boolean = false,
    val consentGivenTimestamp: Long = System.currentTimeMillis(),
    val createdTimestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "prescriptions")
data class Prescription(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val profileId: Long,
    val doctorName: String,
    val clinicOrHospital: String,
    val diseaseOrDiagnosis: String,
    val startDate: String, // YYYY-MM-DD
    val endDate: String? = null, // Blank if chronic / ongoing
    val dischargeAdvice: String = "",
    val imageUri: String? = null,
    val notes: String = "",
    val parentPrescriptionId: Long? = null, // Follow-up prescription linked to original
    val isFollowUp: Boolean = false,
    val createdTimestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "medicines")
data class Medicine(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val profileId: Long,
    val prescriptionId: Long? = null,
    val name: String,
    val dosage: String, // e.g. "500 mg", "1 tablet"
    val form: String = "Tablet", // Tablet, Capsule, Syrup, Injection, Inhaler, Drops
    val instructions: String = "After food", // "After food", "Before food", "With milk", "Empty stomach"
    val timesPerDay: Int = 2,
    val scheduledTimes: String = "08:00,20:00", // comma-separated HH:mm
    val stockQuantity: Int = 30,
    val lowStockThresholdDays: Int = 3,
    val imageUri: String? = null,
    val colorTag: String = "#0284C7",
    val diseaseName: String = "",
    val hasTapering: Boolean = false,
    val taperStartDate: String? = null, // e.g. "25-09-2026"
    val taperDosage: String? = null, // e.g. "1 Tablet", "10 mg"
    val taperTimesPerDay: Int? = null,
    val taperScheduledTimes: String? = null, // e.g. "08:00"
    val taperInstructions: String? = null,
    val taperEndDate: String? = null,
    val createdTimestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "intake_logs")
data class IntakeLog(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val medicineId: Long,
    val profileId: Long,
    val scheduledDate: String, // YYYY-MM-DD or DD-MM-YYYY
    val scheduledTime: String, // HH:mm
    val status: String = "PENDING", // PENDING, TAKEN, SNOOZED, SKIPPED
    val takenTimestamp: Long? = null,
    val snoozeMinutes: Int = 0,
    val originalTime: String = "",
    val notes: String = "",
    val dosage: String = "", // specific dose for this intake, e.g. "1 Tablet (Tapered)"
    val isTapered: Boolean = false
)

@Entity(tableName = "medical_reports")
data class MedicalReport(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val profileId: Long,
    val reportTitle: String,
    val labName: String,
    val reportDate: String, // YYYY-MM-DD
    val keyMetricsJson: String = "[]", // JSON array of {metric, value, unit, normalRange}
    val doctorNotes: String = "",
    val fileUri: String? = null,
    val createdTimestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "routine_vitals")
data class RoutineVitalLog(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val profileId: Long,
    val recordDate: String, // YYYY-MM-DD
    val recordTime: String, // HH:mm
    val vitalCategory: String = "All", // "Blood Pressure", "Blood Sugar", "Body Weight & BMI", "Pulse & SpO2", "Temperature"
    val systolicBp: Int? = null,
    val diastolicBp: Int? = null,
    val pulseBpm: Int? = null,
    val bloodSugarFasting: Float? = null, // mg/dL
    val bloodSugarPostPrandial: Float? = null, // mg/dL
    val bloodSugarRandom: Float? = null, // mg/dL
    val weightKg: Float? = null,
    val heightCm: Float? = null,
    val bmi: Float? = null,
    val bodyFatPercentage: Float? = null,
    val spo2Percentage: Int? = null,
    val temperatureF: Float? = null,
    val notes: String = "",
    val createdTimestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "chemists")
data class Chemist(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val phoneNumber: String,
    val address: String,
    val openingTime: String = "08:00 AM",
    val closingTime: String = "10:30 PM",
    val isFavorite: Boolean = false,
    val photoUri: String? = null,
    val notes: String = ""
)

@Entity(tableName = "emergency_contacts")
data class EmergencyContact(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val contactType: String, // "FAMILY", "DOCTOR", "HOSPITAL", "AMBULANCE"
    val name: String,
    val relationshipOrSpecialty: String, // e.g. "Son", "Cardiologist", "Apex Hospital"
    val phoneNumber: String,
    val address: String = "",
    val emergencyNotes: String = ""
)

@Entity(tableName = "app_settings")
data class AppSettingsEntity(
    @PrimaryKey val id: Int = 1,
    val themeMode: String = "SYSTEM", // SYSTEM, LIGHT, DARK
    val fontScale: String = "STANDARD", // STANDARD, LARGE, EXTRA_LARGE
    val highContrast: Boolean = false,
    val allowLockScreenNotification: Boolean = true,
    val alarmSoundType: String = "ALARM", // ALARM, NOTIFICATION, GENTLE
    val vibrateInsteadOfSound: Boolean = false,
    val autoVibrateOnSilent: Boolean = true,
    val remindOnAirplaneMode: Boolean = true,
    val deactivateAllReminders: Boolean = false,
    val deactivateStartDate: String? = null,
    val deactivateEndDate: String? = null
)
