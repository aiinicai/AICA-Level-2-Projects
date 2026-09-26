package com.example.ui.components

import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Today
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/**
 * Interactive Material 3 Clock Dialog that displays a full circular Clock face
 * with hour and minute needles, interactive numbers, and 24h/12h support.
 * Pure Compose component that opens reliably inside any screen or dialog.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Material3ClockDialog(
    initialTime: String = "08:00",
    is24Hour: Boolean = true,
    title: String = "Select Medicine Time",
    onTimeSelected: (String) -> Unit,
    onDismissRequest: () -> Unit
) {
    val initialParts = initialTime.split(":")
    val initialHour = initialParts.getOrNull(0)?.trim()?.toIntOrNull() ?: 8
    val initialMinute = initialParts.getOrNull(1)?.trim()?.toIntOrNull() ?: 0

    val timePickerState = rememberTimePickerState(
        initialHour = initialHour.coerceIn(0, 23),
        initialMinute = initialMinute.coerceIn(0, 59),
        is24Hour = is24Hour
    )

    AlertDialog(
        onDismissRequest = onDismissRequest,
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(
                    imageVector = Icons.Default.Schedule,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                AccessibleText(
                    text = title,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Interactive Material 3 circular Clock
                TimePicker(
                    state = timePickerState,
                    modifier = Modifier.testTag("clock_time_picker")
                )

                // Large readable preview of the currently picked time
                val currentHour = timePickerState.hour
                val currentMinute = timePickerState.minute
                val amPmStr = if (currentHour < 12) "AM" else "PM"
                val display12Hour = when {
                    currentHour == 0 -> 12
                    currentHour > 12 -> currentHour - 12
                    else -> currentHour
                }
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f),
                    modifier = Modifier.padding(top = 4.dp)
                ) {
                    Text(
                        text = String.format(
                            Locale.getDefault(),
                            "🕒 Selected: %02d:%02d (%02d:%02d %s)",
                            currentHour, currentMinute, display12Hour, currentMinute, amPmStr
                        ),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                    )
                }

                // Quick preset row inside clock dialog for convenience
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AccessibleText(text = "Presets:", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    listOf(
                        "08:00" to "Morning 🌅",
                        "13:00" to "Noon ☀️",
                        "18:00" to "Evening 🌆",
                        "21:00" to "Night 🌙"
                    ).forEach { (presetTime, presetLabel) ->
                        AssistChip(
                            onClick = {
                                onTimeSelected(presetTime)
                                onDismissRequest()
                            },
                            label = { Text(presetLabel, fontSize = 11.sp) }
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val formatted = String.format(
                        Locale.getDefault(),
                        "%02d:%02d",
                        timePickerState.hour,
                        timePickerState.minute
                    )
                    onTimeSelected(formatted)
                    onDismissRequest()
                },
                modifier = Modifier.testTag("btn_confirm_clock_time")
            ) {
                Text("Set Time", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onDismissRequest,
                modifier = Modifier.testTag("btn_cancel_clock_time")
            ) {
                Text("Cancel")
            }
        }
    )
}

/**
 * Interactive Material 3 Calendar DatePicker Dialog.
 * Pure Compose component that opens reliably inside any screen or dialog.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Material3DatePickerDialog(
    initialDate: String = "",
    title: String = "Select Date",
    onDateSelected: (String) -> Unit,
    onDismissRequest: () -> Unit
) {
    val initialMillis = remember(initialDate) {
        if (initialDate.isNotBlank()) {
            com.example.util.DateUtils.parseDate(initialDate)?.time
        } else null
    }

    val datePickerState = rememberDatePickerState(
        initialSelectedDateMillis = initialMillis ?: System.currentTimeMillis()
    )

    DatePickerDialog(
        onDismissRequest = onDismissRequest,
        confirmButton = {
            Button(
                onClick = {
                    datePickerState.selectedDateMillis?.let { millis ->
                        val sdf = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault())
                        sdf.timeZone = java.util.TimeZone.getTimeZone("UTC")
                        onDateSelected(sdf.format(Date(millis)))
                    }
                    onDismissRequest()
                },
                modifier = Modifier.testTag("btn_confirm_calendar_date")
            ) {
                Text("Set Date", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismissRequest) {
                Text("Cancel")
            }
        }
    ) {
        DatePicker(state = datePickerState)
    }
}

/**
 * Utility helper to launch system calendar DatePickerDialog.
 */
fun showCalendarDatePicker(
    context: Context,
    currentDate: String = "",
    onDateSelected: (String) -> Unit
) {
    val cal = Calendar.getInstance()
    if (currentDate.isNotBlank()) {
        com.example.util.DateUtils.parseDate(currentDate)?.let {
            cal.time = it
        }
    }

    DatePickerDialog(
        context,
        { _, year, month, dayOfMonth ->
            val formatted = String.format(Locale.getDefault(), "%02d-%02d-%04d", dayOfMonth, month + 1, year)
            onDateSelected(formatted)
        },
        cal.get(Calendar.YEAR),
        cal.get(Calendar.MONTH),
        cal.get(Calendar.DAY_OF_MONTH)
    ).show()
}

/**
 * Utility helper to launch system clock TimePickerDialog.
 */
fun showClockTimePicker(
    context: Context,
    currentTime: String = "",
    is24Hour: Boolean = true,
    onTimeSelected: (String) -> Unit
) {
    val cal = Calendar.getInstance()
    var hour = cal.get(Calendar.HOUR_OF_DAY)
    var minute = cal.get(Calendar.MINUTE)
    if (currentTime.isNotBlank()) {
        try {
            val parts = currentTime.split(":")
            if (parts.size >= 2) {
                hour = parts[0].trim().toIntOrNull() ?: hour
                minute = parts[1].trim().toIntOrNull() ?: minute
            }
        } catch (_: Exception) {
            // fallback to current time
        }
    }

    TimePickerDialog(
        context,
        { _, h, m ->
            val formatted = String.format(Locale.getDefault(), "%02d:%02d", h, m)
            onTimeSelected(formatted)
        },
        hour,
        minute,
        is24Hour
    ).show()
}

/**
 * Calendar-based Date Input Component.
 * Features:
 * - Direct tap to open Calendar Picker dialog.
 * - Prominent Calendar icon trailing button.
 * - Quick presets for "Today", "Yesterday", and "Tomorrow".
 * - Visual date chip and accessibility support.
 */
@Composable
fun CalendarDatePickerField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String = "Date",
    modifier: Modifier = Modifier,
    placeholder: String = "DD-MM-YYYY",
    showQuickPresets: Boolean = true,
    tag: String = "calendar_date_picker_field"
) {
    var showDateDialog by remember { mutableStateOf(false) }

    if (showDateDialog) {
        Material3DatePickerDialog(
            initialDate = value,
            title = "Pick $label",
            onDateSelected = { selectedDate ->
                onValueChange(selectedDate)
                showDateDialog = false
            },
            onDismissRequest = {
                showDateDialog = false
            }
        )
    }

    val todayStr = remember {
        SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date())
    }
    val yesterdayStr = remember {
        val cal = Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -1) }
        SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(cal.time)
    }
    val tomorrowStr = remember {
        val cal = Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, 1) }
        SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(cal.time)
    }

    Column(modifier = modifier) {
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            label = { Text(label) },
            placeholder = { Text(placeholder) },
            leadingIcon = {
                IconButton(
                    onClick = { showDateDialog = true },
                    modifier = Modifier.testTag("${tag}_leading_calendar")
                ) {
                    Icon(
                        imageVector = Icons.Default.CalendarMonth,
                        contentDescription = "Calendar",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            },
            trailingIcon = {
                IconButton(
                    onClick = { showDateDialog = true },
                    modifier = Modifier.testTag("${tag}_btn_calendar")
                ) {
                    Icon(
                        imageVector = Icons.Default.Today,
                        contentDescription = "Open Calendar",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            },
            singleLine = true,
            modifier = Modifier
                .fillMaxWidth()
                .testTag(tag)
        )

        if (showQuickPresets) {
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Quick Date:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                AssistChip(
                    onClick = { onValueChange(todayStr) },
                    label = { Text("Today", fontSize = 11.sp) },
                    leadingIcon = if (value == todayStr) {
                        { Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(12.dp)) }
                    } else null,
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (value == todayStr) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                    ),
                    border = BorderStroke(1.dp, if (value == todayStr) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant)
                )
                AssistChip(
                    onClick = { onValueChange(yesterdayStr) },
                    label = { Text("Yesterday", fontSize = 11.sp) },
                    leadingIcon = if (value == yesterdayStr) {
                        { Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(12.dp)) }
                    } else null,
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (value == yesterdayStr) MaterialTheme.colorScheme.primaryContainer else Color.Transparent
                    ),
                    border = BorderStroke(1.dp, if (value == yesterdayStr) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant)
                )
                AssistChip(
                    onClick = { showDateDialog = true },
                    label = { Text("Pick on Calendar 📅", fontSize = 11.sp) },
                    colors = AssistChipDefaults.assistChipColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                )
            }
        }
    }
}

/**
 * Clock-based Time Input Component.
 * Features:
 * - Direct tap on Clock icon button opens native Clock TimePickerDialog.
 * - Prominent clock leading & trailing icon buttons.
 * - Quick presets for "Now", "08:00 (Morning)", "13:00 (Noon)", "18:00 (Evening)", "21:00 (Night)".
 */
@Composable
fun ClockTimePickerField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String = "Time",
    modifier: Modifier = Modifier,
    placeholder: String = "HH:mm",
    showQuickPresets: Boolean = true,
    tag: String = "clock_time_picker_field"
) {
    var showClockDialog by remember { mutableStateOf(false) }

    if (showClockDialog) {
        Material3ClockDialog(
            initialTime = value.ifBlank { "08:00" },
            title = "Pick $label",
            onTimeSelected = { selectedTime ->
                onValueChange(selectedTime)
                showClockDialog = false
            },
            onDismissRequest = {
                showClockDialog = false
            }
        )
    }

    Column(modifier = modifier) {
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            label = { Text(label) },
            placeholder = { Text(placeholder) },
            leadingIcon = {
                IconButton(
                    onClick = { showClockDialog = true },
                    modifier = Modifier.testTag("${tag}_leading_clock")
                ) {
                    Icon(
                        imageVector = Icons.Default.Schedule,
                        contentDescription = "Clock",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
            },
            trailingIcon = {
                IconButton(
                    onClick = { showClockDialog = true },
                    modifier = Modifier.testTag("${tag}_btn_clock")
                ) {
                    Icon(
                        imageVector = Icons.Default.AccessTime,
                        contentDescription = "Open Clock",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            },
            singleLine = true,
            modifier = Modifier
                .fillMaxWidth()
                .testTag(tag)
        )

        if (showQuickPresets) {
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Quick Time:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                AssistChip(
                    onClick = {
                        val nowStr = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
                        onValueChange(nowStr)
                    },
                    label = { Text("Now ⏱️", fontSize = 11.sp) }
                )
                AssistChip(
                    onClick = { onValueChange("08:00") },
                    label = { Text("08:00 Morning", fontSize = 11.sp) }
                )
                AssistChip(
                    onClick = { onValueChange("13:00") },
                    label = { Text("13:00 Noon", fontSize = 11.sp) }
                )
                AssistChip(
                    onClick = { onValueChange("20:00") },
                    label = { Text("20:00 Night", fontSize = 11.sp) }
                )
                AssistChip(
                    onClick = { showClockDialog = true },
                    label = { Text("Pick Clock 🕒", fontSize = 11.sp) },
                    colors = AssistChipDefaults.assistChipColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                )
            }
        }
    }
}
