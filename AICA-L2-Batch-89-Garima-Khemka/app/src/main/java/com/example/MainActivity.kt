package com.example

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.lifecycle.lifecycleScope
import com.example.alarm.AlarmRingtonePlayer
import com.example.alarm.AlarmTriggerHub
import kotlinx.coroutines.launch
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import com.example.data.model.IntakeLog
import com.example.ui.components.AppTopBar
import com.example.ui.components.HomeModuleBar
import com.example.ui.screens.alarmdialog.ActiveAlarmOverlay
import com.example.ui.screens.calendar.CalendarScreen
import com.example.ui.screens.chemist.ChemistScreen
import com.example.ui.screens.emergency.EmergencyContactsScreen
import com.example.ui.screens.medicines.MedicineScreen
import com.example.ui.screens.prescriptions.PrescriptionsScreen
import com.example.ui.screens.profile.ProfileScreen
import com.example.ui.screens.reports.MedicalReportsScreen
import com.example.ui.screens.settings.SettingsScreen
import com.example.ui.screens.today.TodayScreen
import com.example.ui.screens.vitals.VitalsScreen
import com.example.ui.theme.MyApplicationTheme
import com.example.ui.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        handleAlarmIntent(intent)

        lifecycleScope.launch {
            AlarmTriggerHub.liveAlarmEvents.collect { event ->
                val dummyLog = IntakeLog(
                    id = if (event.logId != -1L) event.logId else 9999L,
                    medicineId = 1L,
                    profileId = 1L,
                    scheduledDate = viewModel.todayStr,
                    scheduledTime = "Now",
                    status = "PENDING",
                    notes = "Scheduled reminder: ${event.medicineName} (${event.dosage})"
                )
                viewModel.showAlarmOverlay(dummyLog)
            }
        }

        setContent {
            val appSettings by viewModel.appSettings.collectAsState()
            val themeMode = appSettings?.themeMode ?: "SYSTEM"
            val highContrast = appSettings?.highContrast ?: false
            val fontScaleFactor = when (appSettings?.fontScale) {
                "LARGE" -> 1.15f
                "EXTRA_LARGE" -> 1.30f
                else -> 1.0f
            }

            // Notification permission request for Android 13+
            val notificationPermissionLauncher = rememberLauncherForActivityResult(
                contract = ActivityResultContracts.RequestPermission()
            ) {}

            LaunchedEffect(Unit) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    if (ContextCompat.checkSelfPermission(
                            this@MainActivity,
                            Manifest.permission.POST_NOTIFICATIONS
                        ) != PackageManager.PERMISSION_GRANTED
                    ) {
                        notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                    }
                }
            }

            MyApplicationTheme(
                themePreference = themeMode,
                highContrast = highContrast,
                fontScaleFactor = fontScaleFactor
            ) {
                MainAppContent(
                    viewModel = viewModel,
                    onAlarmStateChanged = { isAlarmActive ->
                        setLockScreenVisibility(isAlarmActive)
                    }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleAlarmIntent(intent)
    }

    private fun handleAlarmIntent(intent: Intent?) {
        if (intent?.getBooleanExtra("EXTRA_ALARM_TRIGGERED", false) == true) {
            val logId = intent.getLongExtra("EXTRA_LOG_ID", -1L)
            val medName = intent.getStringExtra("EXTRA_MED_NAME") ?: "Medicine"
            val dummyLog = IntakeLog(
                id = if (logId != -1L) logId else 9999L,
                medicineId = 1L,
                profileId = 1L,
                scheduledDate = viewModel.todayStr,
                scheduledTime = "Now",
                status = "PENDING",
                notes = "Scheduled reminder: $medName"
            )
            viewModel.showAlarmOverlay(dummyLog)
        }
    }

    private fun setLockScreenVisibility(showOnLockScreen: Boolean) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(showOnLockScreen)
            setTurnScreenOn(showOnLockScreen)
        } else {
            @Suppress("DEPRECATION")
            if (showOnLockScreen) {
                window.addFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                    WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                )
            } else {
                window.clearFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                    WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        viewModel.onAppResumed()
    }

    override fun onDestroy() {
        super.onDestroy()
        AlarmRingtonePlayer.stop(this)
    }
}

@Composable
fun MainAppContent(
    viewModel: MainViewModel,
    onAlarmStateChanged: (Boolean) -> Unit = {}
) {
    val currentModule by viewModel.currentModule.collectAsState()
    val profiles by viewModel.allProfiles.collectAsState()
    val activeProfileId by viewModel.activeProfileId.collectAsState()
    val medicines by viewModel.allMedicines.collectAsState()
    val todayLogs by viewModel.todayLogs.collectAsState()
    val calendarLogs by viewModel.calendarLogs.collectAsState()
    val selectedCalendarDate by viewModel.selectedCalendarDate.collectAsState()
    val prescriptions by viewModel.allPrescriptions.collectAsState()
    val reports by viewModel.activeProfileReports.collectAsState()
    val chemists by viewModel.allChemists.collectAsState()
    val emergencyContacts by viewModel.allEmergencyContacts.collectAsState()
    val appSettings by viewModel.appSettings.collectAsState()
    val activeAlarmLog by viewModel.activeAlarmLog.collectAsState()
    val routineVitals by viewModel.routineVitals.collectAsState()

    var showQuickAddProfileDialog by remember { mutableStateOf(false) }

    LaunchedEffect(activeAlarmLog) {
        onAlarmStateChanged(activeAlarmLog != null)
    }

    Scaffold(
        topBar = {
            AppTopBar(
                profiles = profiles,
                activeProfileId = activeProfileId,
                onSelectProfile = { viewModel.selectProfile(it) },
                onAddProfileClick = { showQuickAddProfileDialog = true },
                onSosClick = { viewModel.selectModule("EMERGENCY") },
                onTestAlarmClick = {
                    val sampleLog = todayLogs.firstOrNull() ?: IntakeLog(
                        id = 9999L,
                        medicineId = medicines.firstOrNull()?.id ?: 1L,
                        profileId = activeProfileId ?: 1L,
                        scheduledDate = viewModel.todayStr,
                        scheduledTime = "12:00",
                        status = "PENDING",
                        notes = "After meals"
                    )
                    viewModel.showAlarmOverlay(sampleLog)
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .imePadding()
        ) {
            // Top Module Navigation Bar (all 9 modules accessible via 1 click)
            HomeModuleBar(
                currentModule = currentModule,
                onSelectModule = { viewModel.selectModule(it) }
            )

            // Content Area for currently selected module
            Box(modifier = Modifier.weight(1f)) {
                when (currentModule) {
                    "TODAY" -> TodayScreen(
                        todayDateStr = viewModel.todayStr,
                        logs = todayLogs,
                        medicines = medicines,
                        onMarkTaken = { viewModel.markTaken(it) },
                        onMarkSkipped = { viewModel.markSkipped(it) },
                        onSnoozeMedicine = { log, mins, shiftSchedule ->
                            viewModel.snoozeMedicine(log, mins, shiftSchedule)
                        },
                        onTriggerAlarmSim = { viewModel.showAlarmOverlay(it) },
                        onTaperMedicineFromToday = { viewModel.taperMedicineFromToday(it) }
                    )

                    "CALENDAR" -> CalendarScreen(
                        selectedDate = selectedCalendarDate,
                        logsForDate = calendarLogs,
                        allMedicines = medicines,
                        prescriptions = prescriptions,
                        onSelectDate = { viewModel.selectCalendarDate(it) },
                        onAddSchedule = { medId, time, date, notes ->
                            viewModel.addScheduleToDate(medId, time, date, notes)
                        },
                        onUpdateSchedule = { viewModel.updateScheduleItem(it) },
                        onDeleteSchedule = { viewModel.deleteScheduleItem(it) },
                        onSyncPrescriptions = { viewModel.syncAllPrescriptionSchedules() }
                    )

                    "VITALS" -> VitalsScreen(
                        vitals = routineVitals,
                        onAddVital = { date, time, cat, sys, dia, pulse, fSugar, ppSugar, rSugar, wt, ht, bmi, fat, spo2, temp, notes ->
                            viewModel.addRoutineVital(
                                date, time, cat, sys, dia, pulse, fSugar, ppSugar, rSugar, wt, ht, bmi, fat, spo2, temp, notes
                            )
                        },
                        onUpdateVital = { viewModel.updateRoutineVital(it) },
                        onDeleteVital = { viewModel.deleteRoutineVital(it) },
                        onExportReport = { ctx, fmt, days ->
                            viewModel.exportVitalsReport(ctx, fmt, days)
                        }
                    )

                    "PROFILE" -> ProfileScreen(
                        profiles = profiles,
                        activeProfileId = activeProfileId,
                        onSelectProfile = { viewModel.selectProfile(it) },
                        onAddProfile = { name, age, sex -> viewModel.addProfile(name, age, sex) },
                        onUpdateProfile = { viewModel.updateProfile(it) },
                        onDeleteProfile = { viewModel.deleteProfile(it) },
                        onWipeAllData = { viewModel.wipeAllDataLocally() }
                    )

                    "PRESCRIPTIONS" -> PrescriptionsScreen(
                        prescriptions = prescriptions,
                        allMedicines = medicines,
                        profiles = profiles,
                        activeProfileId = activeProfileId,
                        onApproveAndSavePrescription = { doc, clinic, dis, start, end, adv, img, notes, isFollowUp, parentId, meds, targetProfileId ->
                            viewModel.approveAndSavePrescriptionWithMedicines(
                                doc, clinic, dis, start, end, adv, img, notes, isFollowUp, parentId, meds, targetProfileId
                            )
                        },
                        onUpdatePrescription = { viewModel.updatePrescription(it) },
                        onDeletePrescription = { viewModel.deletePrescription(it) },
                        onAddMedicineClick = { presId ->
                            viewModel.selectModule("MEDICINES")
                        },
                        onEditMedicineClick = { med ->
                            viewModel.selectModule("MEDICINES")
                        },
                        onDeleteMedicineClick = { medId ->
                            viewModel.deleteMedicine(medId)
                        },
                        onUpdateMedicine = { viewModel.updateMedicine(it) }
                    )

                    "REPORTS" -> MedicalReportsScreen(
                        reports = reports,
                        onAddReport = { title, lab, date, metrics, notes, uri ->
                            viewModel.addMedicalReport(title, lab, date, metrics, notes, uri)
                        },
                        onUpdateReport = { viewModel.updateMedicalReport(it) },
                        onDeleteReport = { viewModel.deleteMedicalReport(it) }
                    )

                    "MEDICINES" -> MedicineScreen(
                        medicines = medicines,
                        profiles = profiles,
                        activeProfileId = activeProfileId,
                        onAddMedicine = { name, dosage, form, inst, times, schTimes, stock, low, dis, img, targetProfileId ->
                            viewModel.addMedicine(
                                name = name,
                                dosage = dosage,
                                form = form,
                                instructions = inst,
                                timesPerDay = times,
                                scheduledTimes = schTimes,
                                stockQuantity = stock,
                                lowStockDays = low,
                                diseaseName = dis,
                                imageUri = img,
                                targetProfileId = targetProfileId
                            )
                        },
                        onUpdateMedicine = { viewModel.updateMedicine(it) },
                        onDeleteMedicine = { viewModel.deleteMedicine(it) },
                        onUpdateStock = { id, stock -> viewModel.updateInventoryStock(id, stock) },
                        onTaperMedicine = { viewModel.taperMedicineFromToday(it) }
                    )

                    "CHEMIST" -> ChemistScreen(
                        chemists = chemists,
                        onAddChemist = { name, phone, addr, open, close, notes, photo ->
                            viewModel.addChemist(name, phone, addr, open, close, notes, photo)
                        },
                        onUpdateChemist = { viewModel.updateChemist(it) },
                        onDeleteChemist = { viewModel.deleteChemist(it) },
                        onToggleFavorite = { viewModel.toggleChemistFavorite(it) }
                    )

                    "EMERGENCY" -> EmergencyContactsScreen(
                        contacts = emergencyContacts,
                        onAddContact = { type, name, rel, phone, addr, notes ->
                            viewModel.addEmergencyContact(type, name, rel, phone, addr, notes)
                        },
                        onUpdateContact = { viewModel.updateEmergencyContact(it) },
                        onDeleteContact = { viewModel.deleteEmergencyContact(it) }
                    )

                    "SETTINGS" -> SettingsScreen(
                        settings = appSettings,
                        onUpdateTheme = { viewModel.updateThemeMode(it) },
                        onUpdateFontScale = { viewModel.updateFontScale(it) },
                        onToggleHighContrast = { viewModel.toggleHighContrast(it) },
                        onToggleLockScreenNotification = { viewModel.updateLockScreenNotification(it) },
                        onUpdateAlarmType = { viewModel.updateAlarmSoundType(it) },
                        onToggleVibrate = { viewModel.updateVibrate(it) },
                        onToggleAirplaneRemind = { viewModel.updateRemindOnAirplaneMode(it) },
                        onToggleDeactivateReminders = { deact, start, end ->
                            viewModel.toggleDeactivateReminders(deact, start, end)
                        },
                        onTriggerTestAlarm = { viewModel.triggerImmediateTestAlarm() },
                        onWipeData = { viewModel.wipeAllDataLocally() }
                    )
                }
            }
        }
    }

    // Active full screen alarm reminder overlay
    activeAlarmLog?.let { log ->
        val med = medicines.firstOrNull { it.id == log.medicineId }
        ActiveAlarmOverlay(
            log = log,
            medicine = med,
            onMarkTaken = { viewModel.markTaken(log) },
            onSnooze = { mins, entireSchedule ->
                viewModel.snoozeMedicine(log, mins, entireSchedule)
            },
            onDismiss = { viewModel.showAlarmOverlay(null) }
        )
    }

    // Quick Add Profile Dialog from TopBar
    if (showQuickAddProfileDialog) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showQuickAddProfileDialog = false },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = { com.example.ui.components.AccessibleText("Add Patient Profile", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold) },
            text = {
                var name by remember { mutableStateOf("") }
                var age by remember { mutableStateOf("") }
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    androidx.compose.material3.OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { androidx.compose.material3.Text("Name") }
                    )
                    androidx.compose.material3.OutlinedTextField(
                        value = age,
                        onValueChange = { age = it.filter { c -> c.isDigit() } },
                        label = { androidx.compose.material3.Text("Age") },
                        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number)
                    )
                }
            },
            confirmButton = {
                androidx.compose.material3.Button(onClick = {
                    showQuickAddProfileDialog = false
                    viewModel.selectModule("PROFILE")
                }) {
                    androidx.compose.material3.Text("Go to Profiles")
                }
            },
            dismissButton = {
                androidx.compose.material3.OutlinedButton(onClick = { showQuickAddProfileDialog = false }) {
                    androidx.compose.material3.Text("Cancel")
                }
            }
        )
    }
}
