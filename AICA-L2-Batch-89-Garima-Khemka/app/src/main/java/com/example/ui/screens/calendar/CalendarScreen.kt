package com.example.ui.screens.calendar

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import kotlinx.coroutines.launch
import com.example.service.DoseScheduleAiService
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import com.example.data.model.IntakeLog
import com.example.data.model.Medicine
import com.example.ui.components.AccessibleText
import com.example.ui.components.CalendarDatePickerField
import com.example.ui.components.ClockTimePickerField
import com.example.ui.components.showCalendarDatePicker
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarScreen(
    selectedDate: String,
    logsForDate: List<IntakeLog>,
    allMedicines: List<Medicine>,
    prescriptions: List<com.example.data.model.Prescription> = emptyList(),
    onSelectDate: (String) -> Unit,
    onAddSchedule: (medicineId: Long, timeStr: String, dateStr: String, notes: String) -> Unit,
    onUpdateSchedule: (IntakeLog) -> Unit,
    onDeleteSchedule: (Long) -> Unit,
    onSyncPrescriptions: () -> Unit = {}
) {
    val context = LocalContext.current
    var showAddDialog by remember { mutableStateOf(false) }
    var logToEdit by remember { mutableStateOf<IntakeLog?>(null) }

    // Generate date range (-14 days to +45 days) to cover past prescription start (e.g. 17 Sept) and all future dates
    val cal = Calendar.getInstance()
    val dateFormat = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault())
    val dayNameFormat = SimpleDateFormat("EEE", Locale.getDefault())
    val dayNumberFormat = SimpleDateFormat("dd", Locale.getDefault())
    val monthYearFormat = SimpleDateFormat("MMMM yyyy", Locale.getDefault())

    val daysList = remember {
        val list = mutableListOf<Triple<String, String, String>>() // (dd-MM-yyyy, EEE, dd)
        val c = Calendar.getInstance()
        c.add(Calendar.DAY_OF_YEAR, -14)
        for (i in 0..59) {
            val dateStr = dateFormat.format(c.time)
            val dayName = dayNameFormat.format(c.time)
            val dayNum = dayNumberFormat.format(c.time)
            list.add(Triple(dateStr, dayName, dayNum))
            c.add(Calendar.DAY_OF_YEAR, 1)
        }
        list
    }
    val todayDate = remember { com.example.util.DateUtils.getToday() }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddDialog = true },
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.testTag("fab_add_calendar_schedule")
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add medicine to schedule")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 14.dp)
        ) {
            // Calendar Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.CalendarMonth,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    AccessibleText(
                        text = "Medicine Schedule Calendar",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primaryContainer,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable {
                            showCalendarDatePicker(context, selectedDate) { pickedDate ->
                                onSelectDate(pickedDate)
                            }
                        }
                        .testTag("btn_calendar_picker_header")
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.CalendarMonth,
                            contentDescription = "Pick Date from Calendar",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(
                            text = com.example.util.DateUtils.formatDisplayDate(selectedDate),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    }
                }
            }

            // Horizontal Date Scroller
            val scrollState = rememberScrollState()
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(scrollState)
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                daysList.forEach { (dateStr, dayName, dayNum) ->
                    val isSelected = dateStr == selectedDate || com.example.util.DateUtils.getAlternateDateFormat(dateStr) == selectedDate
                    val isToday = dateStr == todayDate || com.example.util.DateUtils.getAlternateDateFormat(dateStr) == todayDate

                    Card(
                        modifier = Modifier
                            .clip(RoundedCornerShape(14.dp))
                            .clickable { onSelectDate(dateStr) }
                            .width(62.dp)
                            .testTag("date_chip_$dateStr"),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSelected) MaterialTheme.colorScheme.primary
                            else if (isToday) MaterialTheme.colorScheme.primaryContainer
                            else MaterialTheme.colorScheme.surfaceVariant
                        ),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 10.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            AccessibleText(
                                text = dayName.uppercase(),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isSelected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            AccessibleText(
                                text = dayNum,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = if (isSelected) Color.White else MaterialTheme.colorScheme.onSurface
                            )
                            if (isToday) {
                                Spacer(modifier = Modifier.height(2.dp))
                                Box(
                                    modifier = Modifier
                                        .size(6.dp)
                                        .clip(CircleShape)
                                        .background(if (isSelected) Color.White else MaterialTheme.colorScheme.primary)
                                )
                            }
                        }
                    }
                }
            }

            // Prescription verification note
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 6.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = Color(0xFF047857),
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    AccessibleText(
                        text = "Verify daily dosage against doctor's prescription. Tap + to adjust doses.",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Schedule list for selected day
            if (logsForDate.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        AccessibleText(
                            text = "No medicines scheduled on $selectedDate",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            textAlign = TextAlign.Center
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        AccessibleText(
                            text = "Tap the button below to auto-load prescription schedules or add a custom dose.",
                            fontSize = 13.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.Center
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(
                            onClick = {
                                onSyncPrescriptions()
                                onSelectDate(selectedDate)
                            },
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Icon(Icons.Default.Schedule, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Sync Prescribed Medicines", fontSize = 12.sp)
                        }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(bottom = 80.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(logsForDate, key = { it.id }) { log ->
                        val med = allMedicines.firstOrNull { it.id == log.medicineId }
                        val isTaperedDose = log.isTapered || (med?.hasTapering == true && com.example.util.DateUtils.isOnOrAfter(log.scheduledDate, med.taperStartDate))
                        val displayDose = log.dosage.ifBlank {
                            if (isTaperedDose && !med?.taperDosage.isNullOrBlank()) med.taperDosage else med?.dosage ?: "1 Dose"
                        }

                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .testTag("calendar_item_${log.id}"),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (isTaperedDose) Color(0xFFFFFBEB) else MaterialTheme.colorScheme.surface
                            ),
                            elevation = CardDefaults.cardElevation(2.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(42.dp)
                                            .clip(CircleShape)
                                            .background(if (isTaperedDose) Color(0xFFFEF3C7) else MaterialTheme.colorScheme.primaryContainer),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Medication,
                                            contentDescription = null,
                                            tint = if (isTaperedDose) Color(0xFFD97706) else MaterialTheme.colorScheme.primary,
                                            modifier = Modifier.size(24.dp)
                                        )
                                    }

                                    Spacer(modifier = Modifier.width(12.dp))

                                    Column {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            AccessibleText(
                                                text = med?.name ?: "Medicine",
                                                fontSize = 17.sp,
                                                fontWeight = FontWeight.Bold
                                            )
                                            if (isTaperedDose) {
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Surface(
                                                    shape = RoundedCornerShape(6.dp),
                                                    color = Color(0xFFFEF3C7)
                                                ) {
                                                    Text(
                                                        text = "📉 Tapered",
                                                        fontSize = 10.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color(0xFFB45309),
                                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                    )
                                                }
                                            }
                                        }
                                        AccessibleText(
                                            text = "Time: ${log.scheduledTime} • Dose: $displayDose",
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = if (isTaperedDose) Color(0xFFB45309) else MaterialTheme.colorScheme.primary
                                        )
                                        AccessibleText(
                                            text = "Instructions: ${med?.instructions ?: log.notes.ifEmpty { "As directed" }}",
                                            fontSize = 12.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }

                                Row {
                                    IconButton(
                                        onClick = { logToEdit = log },
                                        modifier = Modifier.testTag("btn_edit_schedule_${log.id}")
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Edit,
                                            contentDescription = "Edit schedule",
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                    IconButton(
                                        onClick = { onDeleteSchedule(log.id) },
                                        modifier = Modifier.testTag("btn_delete_schedule_${log.id}")
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Delete,
                                            contentDescription = "Remove schedule",
                                            tint = Color(0xFFDC2626)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Add Schedule Dialog
    if (showAddDialog) {
        var selectedMedId by remember { mutableStateOf(allMedicines.firstOrNull()?.id ?: 1L) }
        val currentMed = allMedicines.firstOrNull { it.id == selectedMedId }
        val relatedPrescription = prescriptions.firstOrNull { it.id == currentMed?.prescriptionId }

        var scheduleTimesList by remember(selectedMedId) {
            val initial = currentMed?.scheduledTimes?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() }
            mutableStateOf(
                if (!initial.isNullOrEmpty()) initial
                else {
                    val calc = DoseScheduleAiService.calculateClinicalSchedule(
                        medicineName = currentMed?.name ?: "",
                        instructions = currentMed?.instructions ?: "",
                        prescriptionAdvice = relatedPrescription?.dischargeAdvice ?: relatedPrescription?.notes ?: "",
                        firstDoseTime = "08:00",
                        timesPerDay = currentMed?.timesPerDay,
                        existingScheduledTimes = currentMed?.scheduledTimes ?: ""
                    )
                    calc.doseTimes
                }
            )
        }
        var aiExplanation by remember(selectedMedId) {
            val calc = DoseScheduleAiService.calculateClinicalSchedule(
                medicineName = currentMed?.name ?: "",
                instructions = currentMed?.instructions ?: "",
                prescriptionAdvice = relatedPrescription?.dischargeAdvice ?: relatedPrescription?.notes ?: "",
                firstDoseTime = scheduleTimesList.firstOrNull() ?: "08:00",
                timesPerDay = currentMed?.timesPerDay,
                existingScheduledTimes = currentMed?.scheduledTimes ?: ""
            )
            mutableStateOf<String?>(calc.explanation)
        }
        var isCalculatingAi by remember { mutableStateOf(false) }
        val coroutineScope = rememberCoroutineScope()
        var notesInput by remember { mutableStateOf("") }
        var isMenuExpanded by remember { mutableStateOf(false) }

        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                AccessibleText(
                    text = "Add Dose to ${com.example.util.DateUtils.formatDisplayDate(selectedDate)}",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    AccessibleText(text = "Select Medicine:", fontSize = 14.sp, fontWeight = FontWeight.Medium)

                    // Medicine selector
                    ExposedDropdownMenuBox(
                        expanded = isMenuExpanded,
                        onExpandedChange = { isMenuExpanded = it }
                    ) {
                        OutlinedTextField(
                            value = currentMed?.let { "${it.name} (${it.dosage})" } ?: "Select Medicine",
                            onValueChange = {},
                            readOnly = true,
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = isMenuExpanded) },
                            modifier = Modifier
                                .menuAnchor()
                                .fillMaxWidth()
                        )
                        ExposedDropdownMenu(
                            expanded = isMenuExpanded,
                            onDismissRequest = { isMenuExpanded = false }
                        ) {
                            allMedicines.forEach { m ->
                                DropdownMenuItem(
                                    text = { Text("${m.name} (${m.dosage})") },
                                    onClick = {
                                        selectedMedId = m.id
                                        isMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }

                    // Medicine & Prescription Context Card
                    if (currentMed != null) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Column(modifier = Modifier.padding(10.dp)) {
                                AccessibleText(
                                    text = "💊 ${currentMed.name} • ${currentMed.dosage} (${currentMed.form})",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                if (currentMed.instructions.isNotBlank()) {
                                    Spacer(modifier = Modifier.height(2.dp))
                                    AccessibleText(
                                        text = "📋 Instructions: ${currentMed.instructions}",
                                        fontSize = 12.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                                if (relatedPrescription != null && relatedPrescription.doctorName.isNotBlank()) {
                                    Spacer(modifier = Modifier.height(2.dp))
                                    AccessibleText(
                                        text = "👨‍⚕️ Prescribed by Dr. ${relatedPrescription.doctorName}",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.outline
                                    )
                                }
                            }
                        }
                    }

                    // AI & Next Doses Bar
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        AccessibleText(
                            text = "Daily Doses (${scheduleTimesList.size}):",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )

                        OutlinedButton(
                            onClick = {
                                coroutineScope.launch {
                                    isCalculatingAi = true
                                    val firstTime = scheduleTimesList.firstOrNull() ?: "08:00"
                                    val result = DoseScheduleAiService.generateNextDoses(
                                        medicineName = currentMed?.name ?: "",
                                        dosage = currentMed?.dosage ?: "",
                                        instructions = currentMed?.instructions ?: "",
                                        prescriptionAdvice = relatedPrescription?.dischargeAdvice ?: relatedPrescription?.notes ?: "",
                                        firstDoseTime = firstTime,
                                        timesPerDay = currentMed?.timesPerDay,
                                        existingScheduledTimes = currentMed?.scheduledTimes ?: ""
                                    )
                                    scheduleTimesList = result.doseTimes
                                    aiExplanation = result.explanation
                                    isCalculatingAi = false
                                }
                            },
                            enabled = !isCalculatingAi,
                            shape = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                            modifier = Modifier.testTag("btn_ai_auto_schedule")
                        ) {
                            if (isCalculatingAi) {
                                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Calculating...", fontSize = 11.sp)
                            } else {
                                Icon(
                                    imageVector = Icons.Default.AutoAwesome,
                                    contentDescription = null,
                                    modifier = Modifier.size(14.dp),
                                    tint = MaterialTheme.colorScheme.primary
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("AI Next Doses ✨", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }

                    aiExplanation?.let { explanation ->
                        Surface(
                            color = Color(0xFFEFF6FF),
                            shape = RoundedCornerShape(6.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBFDBFE)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = "💡 $explanation",
                                fontSize = 11.sp,
                                color = Color(0xFF1D4ED8),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp)
                            )
                        }
                    }

                    // Dose time slots with clock inputs for Dose 1, Dose 2, Dose 3, etc.
                    scheduleTimesList.forEachIndexed { index, timeStr ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Box(modifier = Modifier.weight(1f)) {
                                ClockTimePickerField(
                                    value = timeStr,
                                    onValueChange = { newTime ->
                                        val mutable = scheduleTimesList.toMutableList()
                                        mutable[index] = newTime
                                        scheduleTimesList = mutable
                                    },
                                    label = "Dose ${index + 1} Time (Clock)",
                                    tag = "input_add_schedule_time_$index",
                                    showQuickPresets = false,
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }

                            if (scheduleTimesList.size > 1) {
                                IconButton(
                                    onClick = {
                                        val mutable = scheduleTimesList.toMutableList()
                                        mutable.removeAt(index)
                                        scheduleTimesList = mutable
                                    },
                                    modifier = Modifier.testTag("btn_remove_dose_$index")
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Delete,
                                        contentDescription = "Remove Dose ${index + 1}",
                                        tint = Color(0xFFDC2626)
                                    )
                                }
                            }
                        }
                    }

                    // Button to add subsequent dose time with Clock
                    OutlinedButton(
                        onClick = {
                            val lastTime = scheduleTimesList.lastOrNull() ?: "08:00"
                            val parts = lastTime.split(":")
                            val h = (parts.getOrNull(0)?.toIntOrNull() ?: 8) + 4
                            val m = parts.getOrNull(1)?.toIntOrNull() ?: 0
                            val nextTime = String.format(Locale.US, "%02d:%02d", h % 24, m)
                            scheduleTimesList = (scheduleTimesList + nextTime).distinct().sorted()
                        },
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("btn_add_dose_clock")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("+ Add Another Dose (Clock)", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }

                    OutlinedTextField(
                        value = notesInput,
                        onValueChange = { notesInput = it },
                        label = { Text("Special notes (e.g. after lunch)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val timesToSchedule = if (scheduleTimesList.isEmpty()) listOf("08:00") else scheduleTimesList
                        timesToSchedule.forEach { timeStr ->
                            onAddSchedule(selectedMedId, timeStr.trim(), selectedDate, notesInput.trim())
                        }
                        showAddDialog = false
                    },
                    modifier = Modifier.testTag("btn_confirm_add_calendar")
                ) {
                    AccessibleText(text = "Add to Schedule (${scheduleTimesList.size} Doses)", color = Color.White)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showAddDialog = false }) {
                    AccessibleText(text = "Cancel")
                }
            }
        )
    }

    // Edit Schedule Dialog (Rule: Option to edit medicine for the selected date)
    logToEdit?.let { log ->
        val med = allMedicines.firstOrNull { it.id == log.medicineId }
        var editedTime by remember(log) { mutableStateOf(log.scheduledTime) }
        var editedDate by remember(log) { mutableStateOf(com.example.util.DateUtils.formatDisplayDate(log.scheduledDate)) }
        var editedDosage by remember(log) { mutableStateOf(log.dosage.ifBlank { med?.dosage ?: "" }) }
        var editedNotes by remember(log) { mutableStateOf(log.notes) }
        var editedStatus by remember(log) { mutableStateOf(log.status) }
        var isTaperedDose by remember(log) { mutableStateOf(log.isTapered) }

        AlertDialog(
            onDismissRequest = { logToEdit = null },
            properties = DialogProperties(decorFitsSystemWindows = false),
            title = {
                AccessibleText(
                    text = "Edit Scheduled Dose",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .imePadding()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    AccessibleText(
                        text = "Medicine: ${med?.name ?: "Medicine"}",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )

                    OutlinedTextField(
                        value = editedDosage,
                        onValueChange = { editedDosage = it },
                        label = { Text("Dose / Strength for this date") },
                        placeholder = { Text("e.g. 1 Tablet, 10 mg (Tapered)") },
                        modifier = Modifier.fillMaxWidth().testTag("input_edit_schedule_dosage")
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        androidx.compose.material3.Checkbox(
                            checked = isTaperedDose,
                            onCheckedChange = { isTaperedDose = it }
                        )
                        AccessibleText(
                            text = "Mark as Tapered Down Dose 📉",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }

                    ClockTimePickerField(
                        value = editedTime,
                        onValueChange = { editedTime = it },
                        label = "Scheduled Time (Clock)",
                        tag = "input_edit_schedule_time",
                        modifier = Modifier.fillMaxWidth()
                    )

                    CalendarDatePickerField(
                        value = editedDate,
                        onValueChange = { editedDate = it },
                        label = "Scheduled Date (Calendar)",
                        tag = "input_edit_schedule_date",
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = editedNotes,
                        onValueChange = { editedNotes = it },
                        label = { Text("Dose Notes / Instructions") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("input_edit_schedule_notes")
                    )

                    AccessibleText(
                        text = "Intake Status:",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("PENDING", "TAKEN", "SKIPPED").forEach { statusOption ->
                            Button(
                                onClick = { editedStatus = statusOption },
                                modifier = Modifier.weight(1f),
                                colors = androidx.compose.material3.ButtonDefaults.buttonColors(
                                    containerColor = if (editedStatus == statusOption) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                                    contentColor = if (editedStatus == statusOption) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            ) {
                                Text(statusOption, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val updated = log.copy(
                            scheduledTime = editedTime.trim(),
                            scheduledDate = editedDate.trim(),
                            notes = editedNotes.trim(),
                            status = editedStatus,
                            dosage = editedDosage.trim(),
                            isTapered = isTaperedDose
                        )
                        onUpdateSchedule(updated)
                        logToEdit = null
                    },
                    modifier = Modifier.testTag("btn_confirm_edit_calendar")
                ) {
                    AccessibleText(text = "Save Changes", color = Color.White)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { logToEdit = null }) {
                    AccessibleText(text = "Cancel")
                }
            }
        )
    }
}
