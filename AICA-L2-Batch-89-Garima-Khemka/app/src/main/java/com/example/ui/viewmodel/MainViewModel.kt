package com.example.ui.viewmodel

import android.app.Application
import android.content.Context
import android.content.Intent
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.alarm.AlarmScheduler
import com.example.data.database.AppDatabase
import com.example.data.database.SampleDataGenerator
import com.example.data.model.AppSettingsEntity
import com.example.data.model.Chemist
import com.example.data.model.EmergencyContact
import com.example.data.model.IntakeLog
import com.example.data.model.MedicalReport
import com.example.data.model.Medicine
import com.example.data.model.PatientProfile
import com.example.data.model.Prescription
import com.example.data.model.RoutineVitalLog
import com.example.data.repository.MedicineRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

data class AutofillMedInfo(
    val name: String,
    val dosage: String,
    val form: String = "Tablet",
    val instructions: String = "After food",
    val timesPerDay: Int = 1,
    val scheduledTimes: String = "08:00",
    val hasTapering: Boolean = false,
    val taperStartDate: String = "",
    val taperDosage: String = "",
    val taperTimesPerDay: Int = 1,
    val taperScheduledTimes: String = "08:00",
    val taperInstructions: String = "",
    val taperEndDate: String = ""
)

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val db = AppDatabase.getInstance(application)
    private val repository = MedicineRepository(db.medicineDao())

    val todayStr: String
        get() = com.example.util.DateUtils.getToday()

    // Currently selected date in Calendar view
    private val _selectedCalendarDate = MutableStateFlow(com.example.util.DateUtils.getToday())
    val selectedCalendarDate: StateFlow<String> = _selectedCalendarDate.asStateFlow()

    // Currently selected profile id
    private val _activeProfileId = MutableStateFlow<Long?>(null)
    val activeProfileId: StateFlow<Long?> = _activeProfileId.asStateFlow()

    // Current navigation tab/module
    private val _currentModule = MutableStateFlow("TODAY")
    val currentModule: StateFlow<String> = _currentModule.asStateFlow()

    // Active alarm / reminder trigger dialog (accessible on lockscreen)
    private val _activeAlarmLog = MutableStateFlow<IntakeLog?>(null)
    val activeAlarmLog: StateFlow<IntakeLog?> = _activeAlarmLog.asStateFlow()

    val allProfiles: StateFlow<List<PatientProfile>> = repository.allProfiles
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val allMedicines: StateFlow<List<Medicine>> = repository.allMedicines
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val allPrescriptions: StateFlow<List<Prescription>> = repository.allPrescriptions
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val allChemists: StateFlow<List<Chemist>> = repository.allChemists
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val allEmergencyContacts: StateFlow<List<EmergencyContact>> = repository.allEmergencyContacts
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val appSettings: StateFlow<AppSettingsEntity?> = repository.appSettings
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    // Today's intake logs for the active profile (or all if none selected)
    val todayLogs: StateFlow<List<IntakeLog>> = combine(
        _activeProfileId,
        repository.allProfiles
    ) { activeId, profiles ->
        activeId ?: profiles.firstOrNull { it.isPrimary }?.id ?: profiles.firstOrNull()?.id ?: 1L
    }.combine(repository.getAllIntakeLogsForDate(todayStr)) { targetProfileId, logs ->
        logs.filter { it.profileId == targetProfileId }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Overdue morning doses (due earlier today that were missed or not yet taken)
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val overdueMorningDoses: StateFlow<List<IntakeLog>> = todayLogs.map { logs ->
        val currentHhMm = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
        logs.filter { it.status == "PENDING" && it.scheduledTime < currentHhMm }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Calendar logs for selected date
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val calendarLogs: StateFlow<List<IntakeLog>> = combine(
        _selectedCalendarDate,
        _activeProfileId,
        repository.allProfiles
    ) { date, activeId, profiles ->
        val targetProfileId = activeId ?: profiles.firstOrNull { it.isPrimary }?.id ?: profiles.firstOrNull()?.id ?: 1L
        targetProfileId to date
    }.flatMapLatest { (targetProfileId, date) ->
        repository.getIntakeLogsForDate(targetProfileId, date)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Reports for active profile
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val activeProfileReports: StateFlow<List<MedicalReport>> = combine(
        _activeProfileId,
        allProfiles
    ) { activeId, profiles ->
        activeId ?: profiles.firstOrNull { it.isPrimary }?.id ?: profiles.firstOrNull()?.id ?: 1L
    }.flatMapLatest { targetProfileId ->
        db.medicineDao().getReportsForProfile(targetProfileId)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Routine Vitals for active profile
    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val routineVitals: StateFlow<List<RoutineVitalLog>> = combine(
        _activeProfileId,
        allProfiles
    ) { activeId, profiles ->
        activeId ?: profiles.firstOrNull { it.isPrimary }?.id ?: profiles.firstOrNull()?.id ?: 1L
    }.flatMapLatest { targetProfileId ->
        db.medicineDao().getRoutineVitalsForProfile(targetProfileId)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Prescription Filter states
    val doctorFilter = MutableStateFlow<String?>(null)
    val medicineFilter = MutableStateFlow<String?>(null)
    val diseaseFilter = MutableStateFlow<String?>(null)

    init {
        viewModelScope.launch {
            val existingProfiles = db.medicineDao().getAllProfiles().firstOrNull()
            if (existingProfiles.isNullOrEmpty()) {
                SampleDataGenerator.populateSampleDataIfEmpty(db.medicineDao())
            }
            // Ensure 17th Sept 2026 prescription with automated dose tapering is loaded
            ensurePrescription17Sept2026Exists()
            // Populate next 45 days in calendar across all profiles so dates beyond today are never blank
            ensureCalendarScheduleRange(45)
            // Schedule alarms for today
            scheduleUpcomingAlarms()
        }
    }

    private suspend fun ensurePrescription17Sept2026Exists() {
        val allPres = db.medicineDao().getAllPrescriptions().firstOrNull() ?: emptyList()
        val has17Sept = allPres.any { it.startDate.contains("17-09-2026") || it.startDate.contains("2026-09-17") }
        if (!has17Sept) {
            val primaryProfile = db.medicineDao().getAllProfiles().firstOrNull()?.firstOrNull { it.isPrimary }
                ?: db.medicineDao().getAllProfiles().firstOrNull()?.firstOrNull() ?: return
            val todayStr = com.example.util.DateUtils.getToday()
            val presId = db.medicineDao().insertPrescription(
                Prescription(
                    profileId = primaryProfile.id,
                    doctorName = "Dr. Sanjeev Kapoor, MD (Internal Medicine & Rheumatology)",
                    clinicOrHospital = "Max Super Specialty Hospital",
                    diseaseOrDiagnosis = "Acute Inflammatory Flare & Reactive Bronchospasm",
                    startDate = "17-09-2026",
                    endDate = null,
                    dischargeAdvice = "Strict tapering schedule: 16mg BD for first 8 days (17th Sept - 24th Sept), then taper down to 8mg OD starting from today ($todayStr) with breakfast. Do not stop abruptly.",
                    notes = "Tapering schedule: Day 1-8: 16mg twice daily. Day 9 onwards (from $todayStr): Taper to 8mg once daily in morning. Check blood glucose and BP regularly."
                )
            )

            db.medicineDao().insertMedicine(
                Medicine(
                    profileId = primaryProfile.id,
                    prescriptionId = presId,
                    name = "Methylprednisolone (Medrol)",
                    dosage = "16 mg (2 Tablets)",
                    form = "Tablet",
                    instructions = "Take after breakfast and dinner (17th to 24th Sept)",
                    timesPerDay = 2,
                    scheduledTimes = "08:00, 20:00",
                    stockQuantity = 24,
                    lowStockThresholdDays = 3,
                    colorTag = "#DC2626",
                    diseaseName = "Acute Inflammatory Flare",
                    hasTapering = true,
                    taperStartDate = todayStr,
                    taperDosage = "8 mg (1 Tablet)",
                    taperTimesPerDay = 1,
                    taperScheduledTimes = "08:00",
                    taperInstructions = "Taper down dose from today ($todayStr): Take 1 tablet (8mg) once daily after breakfast"
                )
            )
        }
    }

    fun onAppResumed() {
        viewModelScope.launch {
            ensureCalendarScheduleRange(45)
            scheduleUpcomingAlarms()
        }
    }

    fun scheduleUpcomingAlarms() {
        viewModelScope.launch {
            val todayStr = com.example.util.DateUtils.getToday()
            val dayLogs = repository.getAllIntakeLogsForDate(todayStr).firstOrNull() ?: emptyList()
            val medicines = db.medicineDao().getAllMedicines().firstOrNull() ?: emptyList()
            val medMap = medicines.associateBy { it.id }

            for (log in dayLogs.filter { it.status == "PENDING" || it.status == "SNOOZED" }) {
                val med = medMap[log.medicineId]
                AlarmScheduler.scheduleAlarm(getApplication(), log, med)
            }
        }
    }

    fun scheduleUpcomingAlarmsForToday() {
        scheduleUpcomingAlarms()
    }

    fun selectModule(module: String) {
        _currentModule.value = module
    }

    fun selectProfile(profileId: Long) {
        _activeProfileId.value = profileId
    }

    fun selectCalendarDate(dateStr: String) {
        _selectedCalendarDate.value = dateStr
        ensureCalendarScheduleForDate(dateStr)
    }

    fun syncAllPrescriptionSchedules() {
        viewModelScope.launch {
            ensureCalendarScheduleRange(45)
            scheduleUpcomingAlarms()
        }
    }

    /**
     * Ensures calendar schedule exists for upcoming dates across ALL patient profiles.
     * Automatically applies dose tapering when date is on or after taperStartDate.
     */
    fun ensureCalendarScheduleRange(daysAhead: Int = 45) {
        viewModelScope.launch {
            val profiles = db.medicineDao().getAllProfiles().firstOrNull() ?: emptyList()
            val sdf = SimpleDateFormat(com.example.util.DateUtils.FORMAT_DD_MM_YYYY, Locale.getDefault())
            val cal = Calendar.getInstance()
            cal.add(Calendar.DAY_OF_YEAR, -14)
            for (i in 0..(daysAhead + 14)) {
                val dateStr = sdf.format(cal.time)
                for (profile in profiles) {
                    ensureCalendarScheduleForDateInternal(dateStr, profile.id)
                }
                cal.add(Calendar.DAY_OF_YEAR, 1)
            }
        }
    }

    fun ensureCalendarScheduleForDate(dateStr: String) {
        viewModelScope.launch {
            val targetProfileId = _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            ensureCalendarScheduleForDateInternal(dateStr, targetProfileId)
        }
    }

    private suspend fun ensureCalendarScheduleForDateInternal(dateStr: String, targetProfileId: Long) {
        val existingLogs = repository.getIntakeLogsForDate(targetProfileId, dateStr).firstOrNull() ?: emptyList()
        val allMeds = db.medicineDao().getAllMedicines().firstOrNull() ?: emptyList()
        val profileMeds = allMeds.filter { it.profileId == targetProfileId }
        val allPrescriptions = db.medicineDao().getAllPrescriptions().firstOrNull() ?: emptyList()

        val existingMedIds = existingLogs.map { it.medicineId }.toSet()
        val newLogs = mutableListOf<IntakeLog>()

        for (med in profileMeds) {
            val pres = allPrescriptions.firstOrNull { it.id == med.prescriptionId }
            val isApplicable = if (pres != null) {
                com.example.util.DateUtils.isDateInRange(dateStr, pres.startDate, pres.endDate)
            } else {
                true
            }

            if (isApplicable) {
                // Check if date falls in tapering phase
                val isTaperPhase = med.hasTapering && com.example.util.DateUtils.isOnOrAfter(dateStr, med.taperStartDate)

                val times = if (isTaperPhase && !med.taperScheduledTimes.isNullOrBlank()) {
                    med.taperScheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                } else {
                    med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                }

                val effectiveDose = if (isTaperPhase && !med.taperDosage.isNullOrBlank()) {
                    med.taperDosage
                } else {
                    med.dosage
                }

                val effectiveNotes = if (isTaperPhase && !med.taperInstructions.isNullOrBlank()) {
                    med.taperInstructions
                } else {
                    med.instructions
                }

                if (med.id !in existingMedIds) {
                    for (time in times) {
                        newLogs.add(
                            IntakeLog(
                                medicineId = med.id,
                                profileId = targetProfileId,
                                scheduledDate = dateStr,
                                scheduledTime = time,
                                status = "PENDING",
                                originalTime = time,
                                notes = effectiveNotes,
                                dosage = effectiveDose,
                                isTapered = isTaperPhase
                            )
                        )
                    }
                } else {
                    // Update existing pending logs if tapering schedule changed
                    val pendingForMed = existingLogs.filter { it.medicineId == med.id && it.status == "PENDING" }
                    for (pendingLog in pendingForMed) {
                        if (isTaperPhase && (!pendingLog.isTapered || pendingLog.dosage != effectiveDose)) {
                            repository.updateIntakeLog(
                                pendingLog.copy(
                                    dosage = effectiveDose,
                                    isTapered = true,
                                    notes = effectiveNotes
                                )
                            )
                        }
                    }
                }
            }
        }
        if (newLogs.isNotEmpty()) {
            repository.addIntakeLogs(newLogs)
        }
    }

    fun showAlarmOverlay(log: IntakeLog?) {
        _activeAlarmLog.value = log
    }

    // Module 1: Today actions
    fun markTaken(log: IntakeLog) {
        viewModelScope.launch {
            AlarmScheduler.cancelAlarm(getApplication(), log.id)
            repository.markIntakeTaken(log.id, log.medicineId)
            if (_activeAlarmLog.value?.id == log.id) {
                _activeAlarmLog.value = null
            }
        }
    }

    fun markSkipped(log: IntakeLog) {
        viewModelScope.launch {
            AlarmScheduler.cancelAlarm(getApplication(), log.id)
            repository.markIntakeSkipped(log.id)
            if (_activeAlarmLog.value?.id == log.id) {
                _activeAlarmLog.value = null
            }
        }
    }

    fun snoozeMedicine(log: IntakeLog, snoozeMinutes: Int = 5, snoozeEntireSchedule: Boolean = true) {
        viewModelScope.launch {
            repository.snoozeMedicine(log, snoozeMinutes, snoozeEntireSchedule)
            if (_activeAlarmLog.value?.id == log.id) {
                _activeAlarmLog.value = null
            }
            scheduleUpcomingAlarmsForToday()
        }
    }

    // Module 2: Add & Edit intake log to calendar date
    fun addScheduleToDate(medicineId: Long, timeStr: String, dateStr: String, notes: String = "") {
        viewModelScope.launch {
            val profileId = _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            val newLog = IntakeLog(
                medicineId = medicineId,
                profileId = profileId,
                scheduledDate = dateStr,
                scheduledTime = timeStr,
                status = "PENDING",
                originalTime = timeStr,
                notes = notes
            )
            val logId = repository.addIntakeLog(newLog)
            if (dateStr == todayStr) {
                val med = db.medicineDao().getMedicineById(medicineId)
                AlarmScheduler.scheduleAlarm(getApplication(), newLog.copy(id = logId), med)
            }
        }
    }

    fun updateScheduleItem(log: IntakeLog) {
        viewModelScope.launch {
            repository.updateIntakeLog(log)
            if (log.scheduledDate == todayStr) {
                val med = db.medicineDao().getMedicineById(log.medicineId)
                AlarmScheduler.scheduleAlarm(getApplication(), log, med)
            }
        }
    }

    fun deleteScheduleItem(logId: Long) {
        viewModelScope.launch {
            AlarmScheduler.cancelAlarm(getApplication(), logId)
            repository.deleteIntakeLog(logId)
        }
    }

    // Module 3: Profile actions (DPDP compliant)
    fun addProfile(name: String, age: Int, sex: String) {
        viewModelScope.launch {
            val id = repository.insertProfile(
                PatientProfile(
                    name = name.trim(),
                    age = age,
                    sex = sex,
                    isPrimary = allProfiles.value.isEmpty(),
                    consentGivenTimestamp = System.currentTimeMillis()
                )
            )
            _activeProfileId.value = id
        }
    }

    fun updateProfile(profile: PatientProfile) {
        viewModelScope.launch {
            repository.updateProfile(profile)
        }
    }

    fun deleteProfile(id: Long) {
        viewModelScope.launch {
            repository.deleteProfile(id)
            if (_activeProfileId.value == id) {
                _activeProfileId.value = null
            }
        }
    }

    // Module 4: Prescriptions
    fun addPrescription(
        doctorName: String,
        clinic: String,
        disease: String,
        startDate: String,
        endDate: String?,
        advice: String,
        imageUri: String?,
        notes: String,
        isFollowUp: Boolean = false,
        parentPrescriptionId: Long? = null
    ) {
        viewModelScope.launch {
            val profileId = _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            repository.insertPrescription(
                Prescription(
                    profileId = profileId,
                    doctorName = doctorName,
                    clinicOrHospital = clinic,
                    diseaseOrDiagnosis = disease,
                    startDate = startDate,
                    endDate = endDate?.takeIf { it.isNotBlank() },
                    dischargeAdvice = advice,
                    imageUri = imageUri,
                    notes = notes,
                    isFollowUp = isFollowUp,
                    parentPrescriptionId = parentPrescriptionId
                )
            )
        }
    }

    fun approveAndSavePrescriptionWithMedicines(
        doctorName: String,
        clinic: String,
        disease: String,
        startDate: String,
        endDate: String?,
        advice: String,
        imageUri: String?,
        notes: String,
        isFollowUp: Boolean,
        parentPrescriptionId: Long?,
        medicines: List<AutofillMedInfo>,
        targetProfileId: Long? = null
    ) {
        viewModelScope.launch {
            val profileId = targetProfileId ?: _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            val presId = repository.insertPrescription(
                Prescription(
                    profileId = profileId,
                    doctorName = doctorName,
                    clinicOrHospital = clinic,
                    diseaseOrDiagnosis = disease,
                    startDate = startDate,
                    endDate = endDate?.takeIf { it.isNotBlank() },
                    dischargeAdvice = advice,
                    imageUri = imageUri,
                    notes = notes,
                    isFollowUp = isFollowUp,
                    parentPrescriptionId = parentPrescriptionId
                )
            )

            // Calculate prescription calendar dates (startDate to endDate, or up to 30 days)
            val sdf = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault())
            val startCal = Calendar.getInstance()
            try {
                if (startDate.isNotBlank()) {
                    com.example.util.DateUtils.parseDate(startDate)?.let { startCal.time = it }
                }
            } catch (_: Exception) {}

            val endCal = Calendar.getInstance()
            var hasExplicitEnd = false
            try {
                if (!endDate.isNullOrBlank()) {
                    com.example.util.DateUtils.parseDate(endDate)?.let {
                        endCal.time = it
                        hasExplicitEnd = true
                    }
                }
            } catch (_: Exception) {}

            val todayCal = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            val minFutureCal = Calendar.getInstance().apply {
                time = todayCal.time
                add(Calendar.DAY_OF_YEAR, 35)
            }
            if (!hasExplicitEnd || endCal.before(minFutureCal)) {
                endCal.time = minFutureCal.time
            }

            val prescriptionDates = mutableListOf<String>()
            val loopCal = Calendar.getInstance().apply { time = startCal.time }
            var limitDays = 0
            while (!loopCal.after(endCal) && limitDays < 75) {
                prescriptionDates.add(sdf.format(loopCal.time))
                loopCal.add(Calendar.DAY_OF_YEAR, 1)
                limitDays++
            }
            if (prescriptionDates.isEmpty()) {
                prescriptionDates.add(todayStr)
            }

            // Insert autofilled and approved medicines and schedules across the prescription timeline
            for (med in medicines) {
                val medId = repository.insertMedicine(
                    Medicine(
                        profileId = profileId,
                        prescriptionId = presId,
                        name = med.name,
                        dosage = med.dosage,
                        form = med.form,
                        instructions = med.instructions,
                        timesPerDay = med.timesPerDay,
                        scheduledTimes = med.scheduledTimes,
                        diseaseName = disease,
                        hasTapering = med.hasTapering,
                        taperStartDate = med.taperStartDate.takeIf { it.isNotBlank() },
                        taperDosage = med.taperDosage.takeIf { it.isNotBlank() },
                        taperTimesPerDay = med.taperTimesPerDay,
                        taperScheduledTimes = med.taperScheduledTimes.takeIf { it.isNotBlank() },
                        taperInstructions = med.taperInstructions.takeIf { it.isNotBlank() },
                        taperEndDate = med.taperEndDate.takeIf { it.isNotBlank() }
                    )
                )

                val createdMedicine = Medicine(
                    id = medId,
                    profileId = profileId,
                    prescriptionId = presId,
                    name = med.name,
                    dosage = med.dosage,
                    form = med.form,
                    instructions = med.instructions,
                    timesPerDay = med.timesPerDay,
                    scheduledTimes = med.scheduledTimes,
                    diseaseName = disease,
                    hasTapering = med.hasTapering,
                    taperStartDate = med.taperStartDate.takeIf { it.isNotBlank() },
                    taperDosage = med.taperDosage.takeIf { it.isNotBlank() },
                    taperTimesPerDay = med.taperTimesPerDay,
                    taperScheduledTimes = med.taperScheduledTimes.takeIf { it.isNotBlank() },
                    taperInstructions = med.taperInstructions.takeIf { it.isNotBlank() },
                    taperEndDate = med.taperEndDate.takeIf { it.isNotBlank() }
                )

                val tomorrowStr = com.example.util.DateUtils.getTomorrow()

                for (dateStr in prescriptionDates) {
                    val isTaperPhase = med.hasTapering && com.example.util.DateUtils.isOnOrAfter(dateStr, med.taperStartDate)
                    val times = if (isTaperPhase && med.taperScheduledTimes.isNotBlank()) {
                        med.taperScheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                    } else {
                        med.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                    }
                    val effectiveDose = if (isTaperPhase && med.taperDosage.isNotBlank()) med.taperDosage else med.dosage
                    val effectiveNotes = if (isTaperPhase && med.taperInstructions.isNotBlank()) med.taperInstructions else med.instructions

                    for (time in times) {
                        val intakeLog = IntakeLog(
                            medicineId = medId,
                            profileId = profileId,
                            scheduledDate = dateStr,
                            scheduledTime = time,
                            status = "PENDING",
                            originalTime = time,
                            notes = effectiveNotes,
                            dosage = effectiveDose,
                            isTapered = isTaperPhase
                        )
                        val logId = repository.addIntakeLog(intakeLog)
                        if (dateStr == todayStr || dateStr == tomorrowStr) {
                            AlarmScheduler.scheduleAlarm(getApplication(), intakeLog.copy(id = logId), createdMedicine)
                        }
                    }
                }
            }
            scheduleUpcomingAlarms()
        }
    }

    /**
     * Tapers down a medicine starting today without needing to re-upload the prescription.
     * Updates future calendar logs and reschedules alarms immediately.
     */
    fun taperMedicineFromToday(
        medicineId: Long,
        taperedDose: String = "1 Tablet",
        taperedTimes: String = "08:00",
        notes: String = "Taper down dose as per prescription"
    ) {
        viewModelScope.launch {
            val med = db.medicineDao().getMedicineById(medicineId) ?: return@launch
            val today = com.example.util.DateUtils.getToday()
            val timesPerDay = taperedTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }.size.coerceAtLeast(1)

            val updatedMed = med.copy(
                hasTapering = true,
                taperStartDate = today,
                taperDosage = taperedDose,
                taperTimesPerDay = timesPerDay,
                taperScheduledTimes = taperedTimes,
                taperInstructions = notes
            )
            repository.updateMedicine(updatedMed)

            // Update pending logs for today and all future dates to the tapered dose and times
            val allMeds = db.medicineDao().getAllMedicines().firstOrNull() ?: emptyList()
            val targetProfileId = med.profileId

            val sdf = SimpleDateFormat(com.example.util.DateUtils.FORMAT_DD_MM_YYYY, Locale.getDefault())
            val cal = Calendar.getInstance()
            for (i in 0..45) {
                val dateStr = sdf.format(cal.time)
                val existingLogs = repository.getIntakeLogsForDate(targetProfileId, dateStr).firstOrNull() ?: emptyList()
                val medLogs = existingLogs.filter { it.medicineId == medicineId }

                // Remove un-taken logs and replace with tapered dose logs
                for (oldLog in medLogs) {
                    if (oldLog.status == "PENDING") {
                        AlarmScheduler.cancelAlarm(getApplication(), oldLog.id)
                        repository.deleteIntakeLog(oldLog.id)
                    }
                }

                // Add tapered dose logs for dates today and onwards
                val times = taperedTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
                for (time in times) {
                    val newLog = IntakeLog(
                        medicineId = medicineId,
                        profileId = targetProfileId,
                        scheduledDate = dateStr,
                        scheduledTime = time,
                        status = "PENDING",
                        originalTime = time,
                        notes = notes,
                        dosage = taperedDose,
                        isTapered = true
                    )
                    val logId = repository.addIntakeLog(newLog)
                    if (dateStr == today || dateStr == com.example.util.DateUtils.getTomorrow()) {
                        AlarmScheduler.scheduleAlarm(getApplication(), newLog.copy(id = logId), updatedMed)
                    }
                }
                cal.add(Calendar.DAY_OF_YEAR, 1)
            }
            scheduleUpcomingAlarms()
        }
    }

    fun updatePrescription(prescription: Prescription) {
        viewModelScope.launch {
            repository.updatePrescription(prescription)
        }
    }

    fun deletePrescription(id: Long) {
        viewModelScope.launch {
            repository.deletePrescription(id)
        }
    }

    // Module 5: Medical Reports
    fun addMedicalReport(
        title: String,
        labName: String,
        date: String,
        metricsJson: String,
        notes: String,
        fileUri: String?
    ) {
        viewModelScope.launch {
            val profileId = _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            repository.insertReport(
                MedicalReport(
                    profileId = profileId,
                    reportTitle = title,
                    labName = labName,
                    reportDate = date,
                    keyMetricsJson = metricsJson,
                    doctorNotes = notes,
                    fileUri = fileUri
                )
            )
        }
    }

    fun updateMedicalReport(report: MedicalReport) {
        viewModelScope.launch {
            repository.updateReport(report)
        }
    }

    fun deleteMedicalReport(id: Long) {
        viewModelScope.launch {
            repository.deleteReport(id)
        }
    }

    // Routine Vitals Module
    fun addRoutineVital(
        recordDate: String,
        recordTime: String,
        vitalCategory: String = "All",
        systolicBp: Int? = null,
        diastolicBp: Int? = null,
        pulseBpm: Int? = null,
        bloodSugarFasting: Float? = null,
        bloodSugarPostPrandial: Float? = null,
        bloodSugarRandom: Float? = null,
        weightKg: Float? = null,
        heightCm: Float? = null,
        bmi: Float? = null,
        bodyFatPercentage: Float? = null,
        spo2Percentage: Int? = null,
        temperatureF: Float? = null,
        notes: String = ""
    ) {
        viewModelScope.launch {
            val profileId = _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            // Calculate BMI if weight and height available and BMI not given
            val calculatedBmi = if (bmi != null) bmi else if (weightKg != null && heightCm != null && heightCm > 0) {
                val heightM = heightCm / 100f
                (weightKg / (heightM * heightM) * 10f).toInt() / 10f
            } else null

            repository.insertRoutineVital(
                RoutineVitalLog(
                    profileId = profileId,
                    recordDate = recordDate,
                    recordTime = recordTime,
                    vitalCategory = vitalCategory,
                    systolicBp = systolicBp,
                    diastolicBp = diastolicBp,
                    pulseBpm = pulseBpm,
                    bloodSugarFasting = bloodSugarFasting,
                    bloodSugarPostPrandial = bloodSugarPostPrandial,
                    bloodSugarRandom = bloodSugarRandom,
                    weightKg = weightKg,
                    heightCm = heightCm,
                    bmi = calculatedBmi,
                    bodyFatPercentage = bodyFatPercentage,
                    spo2Percentage = spo2Percentage,
                    temperatureF = temperatureF,
                    notes = notes
                )
            )
        }
    }

    fun updateRoutineVital(vital: RoutineVitalLog) {
        viewModelScope.launch {
            repository.updateRoutineVital(vital)
        }
    }

    fun deleteRoutineVital(id: Long) {
        viewModelScope.launch {
            repository.deleteRoutineVital(id)
        }
    }

    fun exportVitalsReport(context: Context, format: String, durationDays: Int) {
        val profile = allProfiles.value.firstOrNull { it.id == _activeProfileId.value }
            ?: allProfiles.value.firstOrNull()
        val vitals = routineVitals.value

        val cal = Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -durationDays) }
        val cutoffMillis = cal.timeInMillis
        val filtered = vitals.filter {
            val dateMillis = com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: Long.MAX_VALUE
            dateMillis >= cutoffMillis
        }.sortedWith(
            compareBy<RoutineVitalLog> { com.example.util.DateUtils.parseDate(it.recordDate)?.time ?: 0L }
                .thenBy { it.recordTime }
        )

        val builder = StringBuilder()
        builder.append("====================================================\n")
        builder.append("PATIENT ROUTINE VITALS & HEALTH MONITORING REPORT\n")
        builder.append("====================================================\n")
        builder.append("Patient Name: ${profile?.name ?: "Patient"}\n")
        builder.append("Age/Sex: ${profile?.age ?: "--"} yrs, ${profile?.sex ?: "--"}\n")
        builder.append("Generated On: ${com.example.util.DateUtils.formatDisplayDate(todayStr)} (Past $durationDays Days)\n")
        builder.append("Export Format: $format Clinical Document\n")
        builder.append("----------------------------------------------------\n\n")

        if (filtered.isEmpty()) {
            builder.append("No vitals recorded in the selected period.\n")
        } else {
            builder.append(String.format("%-11s %-6s %-10s %-12s %-10s %-8s\n", "Date", "Time", "Blood Pressure", "Sugar(F/PP)", "Weight/BMI", "SpO2"))
            builder.append("--------------------------------------------------------------------------------\n")
            for (v in filtered) {
                val bp = if (v.systolicBp != null && v.diastolicBp != null) "${v.systolicBp}/${v.diastolicBp}" else "--"
                val sugar = if (v.bloodSugarFasting != null) "F:${v.bloodSugarFasting}" else if (v.bloodSugarPostPrandial != null) "PP:${v.bloodSugarPostPrandial}" else "--"
                val wt = if (v.weightKg != null) "${v.weightKg}kg" else "--"
                val spo2 = if (v.spo2Percentage != null) "${v.spo2Percentage}%" else "--"
                val displayDate = com.example.util.DateUtils.formatDisplayDate(v.recordDate)
                builder.append(String.format("%-11s %-6s %-14s %-12s %-10s %-8s\n", displayDate, v.recordTime, bp, sugar, wt, spo2))
                if (v.notes.isNotBlank()) {
                    builder.append("  Note: ${v.notes}\n")
                }
            }
        }
        builder.append("\n====================================================\n")
        builder.append("End of Medical Report - Saved Locally (DPDP Compliant)\n")

        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = if (format == "WORD") "application/msword" else "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "Medical Vitals Report - ${profile?.name ?: "Patient"}")
            putExtra(Intent.EXTRA_TEXT, builder.toString())
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(Intent.createChooser(shareIntent, "Download / Share Clinical Vitals Report").apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        })
    }

    // Module 6: Medicines & Inventory
    fun addMedicine(
        name: String,
        dosage: String,
        form: String,
        instructions: String,
        timesPerDay: Int,
        scheduledTimes: String,
        stockQuantity: Int,
        lowStockDays: Int = 3,
        diseaseName: String = "",
        imageUri: String? = null,
        colorTag: String = "#0284C7",
        targetProfileId: Long? = null
    ) {
        viewModelScope.launch {
            val profileId = targetProfileId ?: _activeProfileId.value ?: allProfiles.value.firstOrNull()?.id ?: 1L
            val medId = repository.insertMedicine(
                Medicine(
                    profileId = profileId,
                    name = name,
                    dosage = dosage,
                    form = form,
                    instructions = instructions,
                    timesPerDay = timesPerDay,
                    scheduledTimes = scheduledTimes,
                    stockQuantity = stockQuantity,
                    lowStockThresholdDays = lowStockDays,
                    diseaseName = diseaseName,
                    imageUri = imageUri,
                    colorTag = colorTag
                )
            )

            val createdMedicine = Medicine(
                id = medId,
                profileId = profileId,
                name = name,
                dosage = dosage,
                form = form,
                instructions = instructions,
                timesPerDay = timesPerDay,
                scheduledTimes = scheduledTimes,
                stockQuantity = stockQuantity,
                lowStockThresholdDays = lowStockDays,
                diseaseName = diseaseName,
                imageUri = imageUri,
                colorTag = colorTag
            )

            // Auto generate schedule for today based on scheduledTimes
            val times = scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            for (time in times) {
                val intakeLog = IntakeLog(
                    medicineId = medId,
                    profileId = profileId,
                    scheduledDate = todayStr,
                    scheduledTime = time,
                    status = "PENDING",
                    originalTime = time,
                    notes = instructions
                )
                val logId = repository.addIntakeLog(intakeLog)
                AlarmScheduler.scheduleAlarm(getApplication(), intakeLog.copy(id = logId), createdMedicine)
            }
        }
    }

    fun updateMedicine(medicine: Medicine) {
        viewModelScope.launch {
            repository.updateMedicine(medicine)
            // Immediately sync today's reminder alarms with the updated times
            val times = medicine.scheduledTimes.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            val existingLogs = repository.getAllIntakeLogsForDate(todayStr).firstOrNull() ?: emptyList()
            val existingMedLogs = existingLogs.filter { it.medicineId == medicine.id }

            // Cancel any pending alarms whose times were removed
            for (log in existingMedLogs) {
                if (log.status == "PENDING" && !times.contains(log.scheduledTime)) {
                    AlarmScheduler.cancelAlarm(getApplication(), log.id)
                    repository.deleteIntakeLog(log.id)
                }
            }

            // Schedule or reschedule alarms for remaining/new times
            for (time in times) {
                val matchingLog = existingMedLogs.firstOrNull { it.scheduledTime == time }
                if (matchingLog != null) {
                    if (matchingLog.status == "PENDING") {
                        AlarmScheduler.scheduleAlarm(getApplication(), matchingLog, medicine)
                    }
                } else {
                    val newLog = IntakeLog(
                        medicineId = medicine.id,
                        profileId = medicine.profileId,
                        scheduledDate = todayStr,
                        scheduledTime = time,
                        status = "PENDING",
                        originalTime = time,
                        notes = medicine.instructions
                    )
                    val logId = repository.addIntakeLog(newLog)
                    AlarmScheduler.scheduleAlarm(getApplication(), newLog.copy(id = logId), medicine)
                }
            }
        }
    }

    fun deleteMedicine(id: Long) {
        viewModelScope.launch {
            repository.deleteMedicine(id)
        }
    }

    fun updateInventoryStock(medicineId: Long, newStock: Int) {
        viewModelScope.launch {
            val med = db.medicineDao().getMedicineById(medicineId)
            if (med != null) {
                repository.updateMedicine(med.copy(stockQuantity = newStock))
            }
        }
    }

    // Module 7: Chemists
    fun addChemist(name: String, phone: String, address: String, openTime: String, closeTime: String, notes: String, photoUri: String? = null) {
        viewModelScope.launch {
            repository.insertChemist(
                Chemist(
                    name = name,
                    phoneNumber = phone,
                    address = address,
                    openingTime = openTime,
                    closingTime = closeTime,
                    notes = notes,
                    photoUri = photoUri
                )
            )
        }
    }

    fun updateChemist(chemist: Chemist) {
        viewModelScope.launch {
            repository.updateChemist(chemist)
        }
    }

    fun deleteChemist(id: Long) {
        viewModelScope.launch {
            repository.deleteChemist(id)
        }
    }

    fun toggleChemistFavorite(chemist: Chemist) {
        viewModelScope.launch {
            repository.setChemistFavorite(chemist.id, !chemist.isFavorite)
        }
    }

    // Module 8: Emergency Contacts
    fun addEmergencyContact(type: String, name: String, relation: String, phone: String, address: String, notes: String) {
        viewModelScope.launch {
            repository.insertEmergencyContact(
                EmergencyContact(
                    contactType = type,
                    name = name,
                    relationshipOrSpecialty = relation,
                    phoneNumber = phone,
                    address = address,
                    emergencyNotes = notes
                )
            )
        }
    }

    fun updateEmergencyContact(contact: EmergencyContact) {
        viewModelScope.launch {
            repository.updateEmergencyContact(contact)
        }
    }

    fun deleteEmergencyContact(id: Long) {
        viewModelScope.launch {
            repository.deleteEmergencyContact(id)
        }
    }

    // Module 9: Settings
    fun updateThemeMode(theme: String) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(themeMode = theme))
        }
    }

    fun updateFontScale(fontScale: String) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(fontScale = fontScale))
        }
    }

    fun toggleHighContrast(enabled: Boolean) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(highContrast = enabled))
        }
    }

    fun updateLockScreenNotification(enabled: Boolean) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(allowLockScreenNotification = enabled))
        }
    }

    fun updateAlarmSoundType(type: String) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(alarmSoundType = type))
        }
    }

    fun updateVibrate(vibrate: Boolean) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(vibrateInsteadOfSound = vibrate))
        }
    }

    fun updateRemindOnAirplaneMode(remind: Boolean) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(current.copy(remindOnAirplaneMode = remind))
        }
    }

    fun toggleDeactivateReminders(deactivate: Boolean, start: String? = null, end: String? = null) {
        viewModelScope.launch {
            val current = appSettings.value ?: AppSettingsEntity()
            repository.saveSettings(
                current.copy(
                    deactivateAllReminders = deactivate,
                    deactivateStartDate = start,
                    deactivateEndDate = end
                )
            )
        }
    }

    // Test alarm trigger
    fun triggerImmediateTestAlarm(medicineName: String = "Telmisartan 40mg") {
        AlarmScheduler.triggerTestAlarm(getApplication(), 1, medicineName)
        viewModelScope.launch {
            kotlinx.coroutines.delay(1000)
            val dummyLog = IntakeLog(
                id = 9999L,
                medicineId = 1L,
                profileId = _activeProfileId.value ?: 1L,
                scheduledDate = todayStr,
                scheduledTime = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()),
                status = "PENDING",
                notes = "Test Alarm: $medicineName"
            )
            showAlarmOverlay(dummyLog)
        }
    }

    // DPDP Act: Wipe all local data
    fun wipeAllDataLocally() {
        viewModelScope.launch {
            repository.wipeAllLocalData()
            _activeProfileId.value = null
        }
    }
}
