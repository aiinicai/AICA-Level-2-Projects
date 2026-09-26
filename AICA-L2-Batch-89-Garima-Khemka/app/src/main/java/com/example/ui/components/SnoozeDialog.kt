package com.example.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.IntakeLog
import com.example.data.model.Medicine

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun SnoozeDialog(
    log: IntakeLog,
    medicine: Medicine?,
    onDismiss: () -> Unit,
    onConfirmSnooze: (snoozeMinutes: Int, snoozeEntireSchedule: Boolean) -> Unit
) {
    var selectedMinutes by remember { mutableIntStateOf(5) }
    var customMinutesInput by remember { mutableStateOf("") }
    var isCustomSelected by remember { mutableStateOf(false) }
    var snoozeScheduleWindow by remember { mutableStateOf(true) }

    val quickOptions = listOf(5, 10, 15, 20, 30, 45, 60)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Alarm,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(end = 8.dp)
                )
                AccessibleText(
                    text = "Snooze Reminder",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                AccessibleText(
                    text = "Medicine: ${medicine?.name ?: "Scheduled Medicine"}",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.primary
                )
                AccessibleText(
                    text = "Current Time: ${log.scheduledTime}",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(16.dp))

                AccessibleText(
                    text = "Select Snooze Duration:",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium
                )

                Spacer(modifier = Modifier.height(8.dp))

                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    quickOptions.forEach { mins ->
                        val isSelected = !isCustomSelected && selectedMinutes == mins
                        FilterChip(
                            selected = isSelected,
                            onClick = {
                                isCustomSelected = false
                                selectedMinutes = mins
                            },
                            label = { Text("$mins min") },
                            modifier = Modifier.testTag("snooze_chip_$mins")
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = customMinutesInput,
                    onValueChange = {
                        customMinutesInput = it.filter { char -> char.isDigit() }
                        if (customMinutesInput.isNotEmpty()) {
                            isCustomSelected = true
                            selectedMinutes = customMinutesInput.toIntOrNull() ?: 5
                        }
                    },
                    label = { Text("Or enter custom minutes") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("custom_snooze_input"),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(14.dp))

                // Schedule Window Snooze (Rule 1c: Move all remaining medicines within 30 min schedule)
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                ) {
                    Checkbox(
                        checked = snoozeScheduleWindow,
                        onCheckedChange = { snoozeScheduleWindow = it },
                        modifier = Modifier.testTag("checkbox_snooze_schedule")
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Column {
                        AccessibleText(
                            text = "Shift entire schedule together",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                        AccessibleText(
                            text = "Moves all medicines scheduled within 30 mins forward by $selectedMinutes mins",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val finalMinutes = if (isCustomSelected) {
                        customMinutesInput.toIntOrNull()?.coerceAtLeast(1) ?: 5
                    } else {
                        selectedMinutes
                    }
                    onConfirmSnooze(finalMinutes, snoozeScheduleWindow)
                },
                modifier = Modifier.testTag("btn_confirm_snooze"),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                AccessibleText(
                    text = "Snooze for $selectedMinutes min",
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("btn_cancel_snooze")
            ) {
                AccessibleText(text = "Cancel")
            }
        },
        shape = RoundedCornerShape(20.dp)
    )
}
