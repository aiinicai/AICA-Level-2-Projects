package com.example.data.database

import com.example.data.dao.MedicineDao
import com.example.data.model.AppSettingsEntity
import com.example.data.model.Chemist
import com.example.data.model.EmergencyContact
import com.example.data.model.IntakeLog
import com.example.data.model.MedicalReport
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.data.model.Prescription
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

object SampleDataGenerator {

    suspend fun populateSampleDataIfEmpty(dao: MedicineDao) {
        val dateFormat = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault())
        val todayStr = dateFormat.format(Date())

        val cal = Calendar.getInstance()
        cal.add(Calendar.DAY_OF_YEAR, -30)
        val oneMonthAgoStr = dateFormat.format(cal.time)
        cal.add(Calendar.DAY_OF_YEAR, -30)
        val twoMonthsAgoStr = dateFormat.format(cal.time)

        // 1. Check if profile exists
        val profileId = dao.insertProfile(
            PatientProfile(
                name = "Ramesh Sharma",
                age = 68,
                sex = "Male",
                isPrimary = true,
                consentGivenTimestamp = System.currentTimeMillis()
            )
        )

        // Secondary Profile
        dao.insertProfile(
            PatientProfile(
                name = "Kanta Sharma",
                age = 65,
                sex = "Female",
                isPrimary = false,
                consentGivenTimestamp = System.currentTimeMillis()
            )
        )

        // 2. Prescription
        val prescriptionId = dao.insertPrescription(
            Prescription(
                profileId = profileId,
                doctorName = "Dr. A. K. Banerjee, MD (Cardiology)",
                clinicOrHospital = "Max Healthcare & Heart Institute",
                diseaseOrDiagnosis = "Hypertension & Type 2 Diabetes",
                startDate = twoMonthsAgoStr,
                endDate = null, // Ongoing regular medication
                dischargeAdvice = "Maintain BP and Sugar diary. Low sodium (<2g/day) & low glycemic diet. Take medicines on time. Walk 20 minutes daily morning.",
                notes = "Follow-up consultation after 3 months. In case of dizziness, check BP immediately."
            )
        )

        // 3. Medicines
        val med1Id = dao.insertMedicine(
            Medicine(
                profileId = profileId,
                prescriptionId = prescriptionId,
                name = "Telmisartan 40mg",
                dosage = "1 Tablet",
                form = "Tablet",
                instructions = "After breakfast",
                timesPerDay = 1,
                scheduledTimes = "08:00",
                stockQuantity = 25,
                lowStockThresholdDays = 3,
                colorTag = "#0284C7",
                diseaseName = "Hypertension"
            )
        )

        val med2Id = dao.insertMedicine(
            Medicine(
                profileId = profileId,
                prescriptionId = prescriptionId,
                name = "Metformin 500mg",
                dosage = "1 Tablet",
                form = "Tablet",
                instructions = "After meals",
                timesPerDay = 2,
                scheduledTimes = "08:15,20:30",
                stockQuantity = 14,
                lowStockThresholdDays = 3,
                colorTag = "#10B981",
                diseaseName = "Type 2 Diabetes"
            )
        )

        val med3Id = dao.insertMedicine(
            Medicine(
                profileId = profileId,
                prescriptionId = prescriptionId,
                name = "Atorvastatin 10mg",
                dosage = "1 Tablet",
                form = "Tablet",
                instructions = "At bedtime with water",
                timesPerDay = 1,
                scheduledTimes = "21:00",
                stockQuantity = 2, // Low stock! < 3 days left
                lowStockThresholdDays = 3,
                colorTag = "#F59E0B",
                diseaseName = "Cholesterol"
            )
        )

        val med4Id = dao.insertMedicine(
            Medicine(
                profileId = profileId,
                prescriptionId = prescriptionId,
                name = "Pantoprazole 40mg",
                dosage = "1 Capsule",
                form = "Capsule",
                instructions = "Empty stomach before breakfast",
                timesPerDay = 1,
                scheduledTimes = "07:30",
                stockQuantity = 18,
                lowStockThresholdDays = 3,
                colorTag = "#8B5CF6",
                diseaseName = "Acidity / GERD"
            )
        )

        // 4. Intake Logs for Today
        val todayLogs = listOf(
            IntakeLog(
                medicineId = med4Id,
                profileId = profileId,
                scheduledDate = todayStr,
                scheduledTime = "07:30",
                status = "TAKEN",
                takenTimestamp = System.currentTimeMillis() - 4 * 3600 * 1000,
                originalTime = "07:30",
                notes = "Taken with warm water"
            ),
            IntakeLog(
                medicineId = med1Id,
                profileId = profileId,
                scheduledDate = todayStr,
                scheduledTime = "08:00",
                status = "PENDING",
                originalTime = "08:00",
                notes = "Take after light breakfast"
            ),
            IntakeLog(
                medicineId = med2Id,
                profileId = profileId,
                scheduledDate = todayStr,
                scheduledTime = "08:15",
                status = "PENDING",
                originalTime = "08:15",
                notes = "Part of morning schedule (within 30 mins)"
            ),
            IntakeLog(
                medicineId = med2Id,
                profileId = profileId,
                scheduledDate = todayStr,
                scheduledTime = "20:30",
                status = "PENDING",
                originalTime = "20:30",
                notes = "Take after dinner"
            ),
            IntakeLog(
                medicineId = med3Id,
                profileId = profileId,
                scheduledDate = todayStr,
                scheduledTime = "21:00",
                status = "PENDING",
                originalTime = "21:00",
                notes = "Bedtime pill. Low stock (2 left)"
            )
        )
        dao.insertIntakeLogs(todayLogs)

        // 5. Medical Reports (3 reports for past comparison)
        val report1Metrics = """
            [
                {"metric": "HbA1c", "value": "7.4", "unit": "%", "normalRange": "< 5.7"},
                {"metric": "Fasting Blood Sugar", "value": "142", "unit": "mg/dL", "normalRange": "70-99"},
                {"metric": "Total Cholesterol", "value": "224", "unit": "mg/dL", "normalRange": "< 200"},
                {"metric": "Serum Creatinine", "value": "1.0", "unit": "mg/dL", "normalRange": "0.7-1.3"}
            ]
        """.trimIndent()

        val report2Metrics = """
            [
                {"metric": "HbA1c", "value": "7.0", "unit": "%", "normalRange": "< 5.7"},
                {"metric": "Fasting Blood Sugar", "value": "130", "unit": "mg/dL", "normalRange": "70-99"},
                {"metric": "Total Cholesterol", "value": "208", "unit": "mg/dL", "normalRange": "< 200"},
                {"metric": "Serum Creatinine", "value": "0.95", "unit": "mg/dL", "normalRange": "0.7-1.3"}
            ]
        """.trimIndent()

        val report3Metrics = """
            [
                {"metric": "HbA1c", "value": "6.5", "unit": "%", "normalRange": "< 5.7"},
                {"metric": "Fasting Blood Sugar", "value": "112", "unit": "mg/dL", "normalRange": "70-99"},
                {"metric": "Total Cholesterol", "value": "186", "unit": "mg/dL", "normalRange": "< 200"},
                {"metric": "Serum Creatinine", "value": "0.92", "unit": "mg/dL", "normalRange": "0.7-1.3"}
            ]
        """.trimIndent()

        dao.insertReport(
            MedicalReport(
                profileId = profileId,
                reportTitle = "Quarterly Comprehensive Metabolic Panel",
                labName = "Dr. Lal PathLabs",
                reportDate = twoMonthsAgoStr,
                keyMetricsJson = report1Metrics,
                doctorNotes = "High sugar and elevated cholesterol. Initiated Statin therapy."
            )
        )

        dao.insertReport(
            MedicalReport(
                profileId = profileId,
                reportTitle = "Follow-up Diabetes & Lipid Panel",
                labName = "Metropolis Healthcare",
                reportDate = oneMonthAgoStr,
                keyMetricsJson = report2Metrics,
                doctorNotes = "Gradual improvement in HbA1c. Continue current prescription."
            )
        )

        dao.insertReport(
            MedicalReport(
                profileId = profileId,
                reportTitle = "Latest Glycemic & Lipid Evaluation",
                labName = "Max Lab Diagnostics",
                reportDate = todayStr,
                keyMetricsJson = report3Metrics,
                doctorNotes = "Excellent response to lifestyle modifications & medication schedule. Target achieved."
            )
        )

        // 6. Chemists
        dao.insertChemist(
            Chemist(
                name = "Apollo Pharmacy (24x7)",
                phoneNumber = "+91 98765 43210",
                address = "Shop 12, Main Market, Sector 14",
                openingTime = "12:00 AM",
                closingTime = "11:59 PM",
                isFavorite = true,
                notes = "Open 24 hours. Home delivery available. Prescription accepted via WhatsApp."
            )
        )
        dao.insertChemist(
            Chemist(
                name = "MedPlus Super Chemist",
                phoneNumber = "+91 98111 22334",
                address = "Opposite Civil Hospital Gate 2",
                openingTime = "08:00 AM",
                closingTime = "11:00 PM",
                isFavorite = true,
                notes = "20% discount on monthly chronic medicines."
            )
        )
        dao.insertChemist(
            Chemist(
                name = "Sanjivani Medicos & Wellness",
                phoneNumber = "+91 98222 33445",
                address = "Booth 45, Community Centre, Block B",
                openingTime = "08:30 AM",
                closingTime = "10:00 PM",
                isFavorite = false,
                notes = "Quick billing and friendly staff."
            )
        )

        // 7. Emergency Contacts
        dao.insertEmergencyContact(
            EmergencyContact(
                contactType = "FAMILY",
                name = "Vikram Sharma",
                relationshipOrSpecialty = "Eldest Son",
                phoneNumber = "+91 98765 11111",
                address = "Flat 402, Green Valley Apartments, Sector 15",
                emergencyNotes = "Lives 5 minutes away. Has spare house keys."
            )
        )
        dao.insertEmergencyContact(
            EmergencyContact(
                contactType = "DOCTOR",
                name = "Dr. A. K. Banerjee",
                relationshipOrSpecialty = "Treating Cardiologist",
                phoneNumber = "+91 98999 88888",
                address = "Max Healthcare, Heart OPD Room 12",
                emergencyNotes = "Call directly in case of severe chest tightness or persistent BP > 180."
            )
        )
        dao.insertEmergencyContact(
            EmergencyContact(
                contactType = "HOSPITAL",
                name = "Max Super Specialty Hospital",
                relationshipOrSpecialty = "Emergency Room & Trauma Center",
                phoneNumber = "+91 11 2651 5050",
                address = "1 Press Enclave Road, Saket",
                emergencyNotes = "24/7 Cardiac Emergency Unit."
            )
        )
        dao.insertEmergencyContact(
            EmergencyContact(
                contactType = "AMBULANCE",
                name = "National Emergency Ambulance",
                relationshipOrSpecialty = "Government Emergency Life Support",
                phoneNumber = "108",
                address = "Central Dispatch Ambulance Hub",
                emergencyNotes = "Free 24x7 Ambulance with paramedics."
            )
        )

        // 8. Default App Settings
        dao.saveSettings(
            AppSettingsEntity(
                id = 1,
                themeMode = "SYSTEM",
                fontScale = "STANDARD",
                highContrast = false,
                allowLockScreenNotification = true,
                alarmSoundType = "ALARM",
                vibrateInsteadOfSound = false,
                autoVibrateOnSilent = true,
                remindOnAirplaneMode = true,
                deactivateAllReminders = false
            )
        )
    }
}
