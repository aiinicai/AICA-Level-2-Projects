package com.example.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.service.DoseScheduleAiService
import kotlinx.coroutines.launch

/**
 * Interactive, accessible Time Slot Editor component.
 * Supports multi-dose scheduling where every single dose (1st, 2nd, 3rd, etc.) has its own
 * clock input. Also provides AI-based automatic calculation of subsequent doses based on prescription instructions.
 */
@Composable
fun TimeSlotEditor(
    times: List<String>,
    onTimesChanged: (List<String>) -> Unit,
    modifier: Modifier = Modifier,
    label: String = "Reminder Alarm Times",
    medicineName: String = "",
    dosage: String = "",
    instructions: String = "",
    prescriptionAdvice: String = "",
    timesPerDay: Int? = null
) {
    var showClockDialog by remember { mutableStateOf(false) }
    var editingIndex by remember { mutableStateOf<Int?>(null) }
    var clockInitialTime by remember { mutableStateOf("08:00") }

    val coroutineScope = rememberCoroutineScope()
    var isCalculatingAi by remember { mutableStateOf(false) }
    var aiExplanation by remember { mutableStateOf<String?>(null) }

    if (showClockDialog) {
        val dialogTitle = if (editingIndex != null) "Edit Dose ${(editingIndex ?: 0) + 1} Time" else "Set Dose Time"
        Material3ClockDialog(
            initialTime = clockInitialTime,
            title = dialogTitle,
            onTimeSelected = { selectedTime ->
                val currentEditingIdx = editingIndex
                if (currentEditingIdx != null && currentEditingIdx in times.indices) {
                    val mutable = times.toMutableList()
                    mutable[currentEditingIdx] = selectedTime
                    onTimesChanged(mutable.distinct().sorted())
                } else {
                    if (!times.contains(selectedTime)) {
                        val updated = (times + selectedTime).sorted()
                        onTimesChanged(updated)
                    }
                }
                showClockDialog = false
                editingIndex = null
            },
            onDismissRequest = {
                showClockDialog = false
                editingIndex = null
            }
        )
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF8FAFC)),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE2E8F0))
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            // Header Row: Label & Clock Picker Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Schedule,
                        contentDescription = null,
                        tint = Color(0xFF2563EB),
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    AccessibleText(
                        text = "$label (${times.size} doses)",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1E293B)
                    )
                }

                // Add time button (launches Material 3 Clock)
                Button(
                    onClick = {
                        val lastTime = times.lastOrNull() ?: "08:00"
                        val parts = lastTime.split(":")
                        val h = ((parts.getOrNull(0)?.toIntOrNull() ?: 8) + 4) % 24
                        val m = parts.getOrNull(1)?.toIntOrNull() ?: 0
                        clockInitialTime = String.format(java.util.Locale.US, "%02d:%02d", h, m)
                        editingIndex = null
                        showClockDialog = true
                    },
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB)),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier
                        .height(34.dp)
                        .testTag("btn_pick_time_clock")
                ) {
                    Icon(Icons.Default.AccessTime, contentDescription = null, modifier = Modifier.size(15.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Add Clock Time 🕒", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // AI Next Doses Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                AccessibleText(
                    text = "Dose Times:",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF64748B)
                )

                OutlinedButton(
                    onClick = {
                        coroutineScope.launch {
                            isCalculatingAi = true
                            val firstTime = times.firstOrNull() ?: "08:00"
                            val result = DoseScheduleAiService.generateNextDoses(
                                medicineName = medicineName,
                                dosage = dosage,
                                instructions = instructions,
                                prescriptionAdvice = prescriptionAdvice,
                                firstDoseTime = firstTime,
                                timesPerDay = timesPerDay,
                                existingScheduledTimes = times.joinToString(",")
                            )
                            onTimesChanged(result.doseTimes)
                            aiExplanation = result.explanation
                            isCalculatingAi = false
                        }
                    },
                    enabled = !isCalculatingAi,
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                    modifier = Modifier.height(30.dp)
                ) {
                    if (isCalculatingAi) {
                        CircularProgressIndicator(modifier = Modifier.size(12.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Calculating...", fontSize = 11.sp)
                    } else {
                        Icon(
                            Icons.Default.AutoAwesome,
                            contentDescription = null,
                            modifier = Modifier.size(13.dp),
                            tint = Color(0xFF2563EB)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("AI Next Doses ✨", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF2563EB))
                    }
                }
            }

            aiExplanation?.let { exp ->
                Spacer(modifier = Modifier.height(4.dp))
                Surface(
                    color = Color(0xFFEFF6FF),
                    shape = RoundedCornerShape(6.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBFDBFE)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "💡 $exp",
                        fontSize = 11.sp,
                        color = Color(0xFF1D4ED8),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Current Time Slots: Every dose (1st, 2nd, 3rd, etc.) has its own Clock button
            if (times.isEmpty()) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFFEF3C7),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(10.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        AccessibleText(
                            text = "⚠️ No reminder times set yet.",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF92400E)
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        OutlinedButton(
                            onClick = {
                                clockInitialTime = "08:00"
                                editingIndex = null
                                showClockDialog = true
                            },
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.Schedule, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Open Clock to Set 1st Dose 🕒", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }
                }
            } else {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    times.forEachIndexed { index, timeStr ->
                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color(0xFFEFF6FF),
                            border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBFDBFE)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 10.dp, vertical = 6.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Surface(
                                        color = Color(0xFF2563EB),
                                        shape = RoundedCornerShape(4.dp)
                                    ) {
                                        Text(
                                            text = "Dose ${index + 1}",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color.White,
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                    Spacer(modifier = Modifier.width(8.dp))
                                    AccessibleText(
                                        text = "⏰ $timeStr",
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF1D4ED8)
                                    )
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    // Clock button explicitly provided post-1st input as well!
                                    Button(
                                        onClick = {
                                            clockInitialTime = timeStr
                                            editingIndex = index
                                            showClockDialog = true
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDBEAFE)),
                                        shape = RoundedCornerShape(6.dp),
                                        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                        modifier = Modifier.height(28.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.AccessTime,
                                            contentDescription = "Clock for Dose ${index + 1}",
                                            tint = Color(0xFF1D4ED8),
                                            modifier = Modifier.size(13.dp)
                                        )
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("Clock 🕒", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1D4ED8))
                                    }

                                    Spacer(modifier = Modifier.width(4.dp))

                                    // Delete button for this specific time
                                    IconButton(
                                        onClick = {
                                            val mutable = times.toMutableList()
                                            mutable.removeAt(index)
                                            onTimesChanged(mutable)
                                        },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.Close,
                                            contentDescription = "Remove Dose ${index + 1}",
                                            tint = Color(0xFFDC2626),
                                            modifier = Modifier.size(16.dp)
                                        )
                                    }
                                }
                            }
                        }
                    }

                    // Button to add another dose time using clock
                    OutlinedButton(
                        onClick = {
                            val lastTime = times.lastOrNull() ?: "08:00"
                            val parts = lastTime.split(":")
                            val h = ((parts.getOrNull(0)?.toIntOrNull() ?: 8) + 4) % 24
                            val m = parts.getOrNull(1)?.toIntOrNull() ?: 0
                            clockInitialTime = String.format(java.util.Locale.US, "%02d:%02d", h, m)
                            editingIndex = null
                            showClockDialog = true
                        },
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("btn_add_another_dose_clock")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(15.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("+ Add Another Dose (Clock 🕒)", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Frequency presets for quick spacing
            AccessibleText(
                text = "Regimen Presets (auto-spaced from 1st dose):",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF64748B)
            )
            Spacer(modifier = Modifier.height(4.dp))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                listOf(
                    1 to "Once Daily",
                    2 to "Twice Daily (BID)",
                    3 to "Thrice Daily (TID)",
                    4 to "4 Times Daily (QID)"
                ).forEach { (freq, freqLabel) ->
                    FilterChip(
                        selected = times.size == freq,
                        onClick = {
                            val first = times.firstOrNull() ?: "08:00"
                            val calc = DoseScheduleAiService.calculateClinicalSchedule(
                                medicineName = medicineName,
                                instructions = "$freqLabel instructions",
                                prescriptionAdvice = prescriptionAdvice,
                                firstDoseTime = first,
                                timesPerDay = freq
                            )
                            onTimesChanged(calc.doseTimes)
                            aiExplanation = calc.explanation
                        },
                        label = { Text(freqLabel, fontSize = 11.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(0xFFDBEAFE),
                            selectedLabelColor = Color(0xFF1D4ED8)
                        )
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Quick clinical presets for fast 1-tap scheduling
            AccessibleText(
                text = "Quick Time Presets:",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF64748B)
            )
            Spacer(modifier = Modifier.height(4.dp))

            val presets = listOf(
                "08:00" to "🌅 Morning (08:00)",
                "13:00" to "☀️ Noon (13:00)",
                "18:00" to "🌤️ Evening (18:00)",
                "20:00" to "🌙 Night (20:00)",
                "22:00" to "🛌 Bedtime (22:00)"
            )

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                presets.forEach { (presetTime, presetLabel) ->
                    val isPresent = times.contains(presetTime)
                    FilterChip(
                        selected = isPresent,
                        onClick = {
                            val updated = if (isPresent) {
                                times.filter { it != presetTime }
                            } else {
                                (times + presetTime).sorted()
                            }
                            onTimesChanged(updated)
                        },
                        label = { Text(presetLabel, fontSize = 11.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(0xFFDBEAFE),
                            selectedLabelColor = Color(0xFF1D4ED8)
                        )
                    )
                }
            }
        }
    }
}
