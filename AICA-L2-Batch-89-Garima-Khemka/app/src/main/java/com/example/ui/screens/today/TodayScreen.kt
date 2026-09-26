package com.example.ui.screens.today

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Snooze
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.data.model.IntakeLog
import com.example.data.model.Medicine
import com.example.ui.components.AccessibleText
import com.example.ui.components.SnoozeDialog

@Composable
fun TodayScreen(
    todayDateStr: String,
    logs: List<IntakeLog>,
    medicines: List<Medicine>,
    onMarkTaken: (IntakeLog) -> Unit,
    onMarkSkipped: (IntakeLog) -> Unit,
    onSnoozeMedicine: (IntakeLog, Int, Boolean) -> Unit,
    onTriggerAlarmSim: (IntakeLog) -> Unit,
    onTaperMedicineFromToday: (Long) -> Unit = {}
) {
    var logToSnooze by remember { mutableStateOf<IntakeLog?>(null) }
    var medicineToTaper by remember { mutableStateOf<Medicine?>(null) }

    val totalDoses = logs.size
    val takenDoses = logs.count { it.status == "TAKEN" }
    val pendingDoses = logs.count { it.status == "PENDING" || it.status == "SNOOZED" }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 14.dp)
    ) {
        // Today Summary Banner
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
            ),
            shape = RoundedCornerShape(16.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    AccessibleText(
                        text = "TODAY'S SCHEDULE",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    AccessibleText(
                        text = com.example.util.DateUtils.formatDisplayDate(todayDateStr),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = Color(0xFFD1FAE5)
                    ) {
                        Column(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            AccessibleText(
                                text = "$takenDoses",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF047857)
                            )
                            AccessibleText(text = "Taken", fontSize = 11.sp, color = Color(0xFF047857))
                        }
                    }

                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = Color(0xFFE0F2FE)
                    ) {
                        Column(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            AccessibleText(
                                text = "$pendingDoses",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF0284C7)
                            )
                            AccessibleText(text = "Pending", fontSize = 11.sp, color = Color(0xFF0284C7))
                        }
                    }
                }
            }
        }

        if (logs.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(32.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    AccessibleText(
                        text = "No medicines scheduled for today",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    AccessibleText(
                        text = "Add medicines or upload a prescription to set up reminder schedules.",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(logs, key = { it.id }) { log ->
                    val medicine = medicines.firstOrNull { it.id == log.medicineId }
                    TodayMedicineCard(
                        log = log,
                        medicine = medicine,
                        onTake = { onMarkTaken(log) },
                        onSkip = { onMarkSkipped(log) },
                        onSnoozeClick = { logToSnooze = log },
                        onTriggerAlarm = { onTriggerAlarmSim(log) },
                        onTaperClick = { medicine?.let { onTaperMedicineFromToday(it.id) } }
                    )
                }
            }
        }
    }

    logToSnooze?.let { log ->
        val med = medicines.firstOrNull { it.id == log.medicineId }
        SnoozeDialog(
            log = log,
            medicine = med,
            onDismiss = { logToSnooze = null },
            onConfirmSnooze = { minutes, snoozeEntireSchedule ->
                onSnoozeMedicine(log, minutes, snoozeEntireSchedule)
                logToSnooze = null
            }
        )
    }
}

@Composable
fun TodayMedicineCard(
    log: IntakeLog,
    medicine: Medicine?,
    onTake: () -> Unit,
    onSkip: () -> Unit,
    onSnoozeClick: () -> Unit,
    onTriggerAlarm: () -> Unit,
    onTaperClick: (() -> Unit)? = null
) {
    val isTaken = log.status == "TAKEN"
    val isSnoozed = log.status == "SNOOZED"
    val isSkipped = log.status == "SKIPPED"
    val isTapered = log.isTapered || (medicine?.hasTapering == true && com.example.util.DateUtils.isOnOrAfter(log.scheduledDate, medicine.taperStartDate))

    val effectiveDose = log.dosage.ifBlank {
        if (isTapered && !medicine?.taperDosage.isNullOrBlank()) medicine?.taperDosage!! else medicine?.dosage ?: "1 Dose"
    }
    val effectiveNotes = if (isTapered && !medicine?.taperInstructions.isNullOrBlank()) {
        medicine?.taperInstructions!!
    } else {
        medicine?.instructions ?: log.notes.ifEmpty { "Take as prescribed" }
    }

    val statusBg = when {
        isTaken -> Color(0xFFD1FAE5)
        isSnoozed -> Color(0xFFFEF3C7)
        isSkipped -> Color(0xFFF1F5F9)
        isTapered -> Color(0xFFFFFBEB)
        else -> MaterialTheme.colorScheme.surface
    }

    val borderColor = when {
        isTaken -> Color(0xFF059669)
        isSnoozed -> Color(0xFFD97706)
        isTapered -> Color(0xFFF59E0B)
        else -> MaterialTheme.colorScheme.outlineVariant
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(
                width = if (isTaken || isSnoozed) 2.dp else 1.dp,
                color = borderColor,
                shape = RoundedCornerShape(18.dp)
            )
            .testTag("today_card_${log.id}"),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = statusBg),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header: Time & Status Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(34.dp)
                            .clip(CircleShape)
                            .background(
                                if (isTaken) Color(0xFF059669)
                                else if (isSnoozed) Color(0xFFD97706)
                                else MaterialTheme.colorScheme.primary
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = if (isTaken) Icons.Default.Check
                            else if (isSnoozed) Icons.Default.Snooze
                            else Icons.Default.Schedule,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(18.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        AccessibleText(
                            text = log.scheduledTime,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Black,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        if (log.originalTime.isNotEmpty() && log.originalTime != log.scheduledTime) {
                            AccessibleText(
                                text = "Original: ${log.originalTime}",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                // Status Pill
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = when {
                        isTaken -> Color(0xFF047857)
                        isSnoozed -> Color(0xFFB45309)
                        isSkipped -> Color(0xFF64748B)
                        else -> MaterialTheme.colorScheme.primary
                    }
                ) {
                    AccessibleText(
                        text = when {
                            isTaken -> "✓ TAKEN"
                            isSnoozed -> "⏰ SNOOZED (+${log.snoozeMinutes}m)"
                            isSkipped -> "SKIPPED"
                            else -> "PENDING"
                        },
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Body: Medicine Image + Name + Dosage + Instructions
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Medicine photo thumbnail
                if (!medicine?.imageUri.isNullOrEmpty()) {
                    AsyncImage(
                        model = medicine?.imageUri,
                        contentDescription = "Medicine Photo",
                        modifier = Modifier
                            .size(64.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(12.dp)),
                        contentScale = ContentScale.Crop
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                } else {
                    Box(
                        modifier = Modifier
                            .size(54.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Medication,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(32.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                }

                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        AccessibleText(
                            text = medicine?.name ?: "Prescribed Medicine",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        if (isTapered) {
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
                        text = "Dose: $effectiveDose • ${medicine?.form ?: "Tablet"}",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = if (isTapered) Color(0xFFB45309) else MaterialTheme.colorScheme.primary
                    )
                    AccessibleText(
                        text = "Instructions: $effectiveNotes",
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (!medicine?.diseaseName.isNullOrEmpty()) {
                        AccessibleText(
                            text = "Condition: ${medicine.diseaseName}",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.tertiary
                        )
                    }

                    if (medicine != null && !medicine.hasTapering && onTaperClick != null) {
                        Spacer(modifier = Modifier.height(4.dp))
                        OutlinedButton(
                            onClick = onTaperClick,
                            shape = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                            modifier = Modifier.testTag("btn_taper_today_${log.id}")
                        ) {
                            Text("📉 Taper Down Dose From Today", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Low Stock Alert
            val stock = medicine?.stockQuantity ?: 10
            if (stock <= 3) {
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFFEE2E2),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    AccessibleText(
                        text = "⚠️ Low Stock: Only $stock pills left in inventory! Refill soon.",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFDC2626),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Action Buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (!isTaken) {
                    // TAKE BUTTON (Min 48dp height)
                    Button(
                        onClick = onTake,
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp)
                            .testTag("btn_take_${log.id}"),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF047857)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color.White)
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(
                            text = "TAKE",
                            fontWeight = FontWeight.Bold,
                            color = Color.White,
                            fontSize = 15.sp
                        )
                    }

                    // SNOOZE BUTTON
                    OutlinedButton(
                        onClick = onSnoozeClick,
                        modifier = Modifier
                            .height(48.dp)
                            .testTag("btn_snooze_${log.id}"),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.Snooze, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        AccessibleText(text = "Snooze", fontSize = 13.sp)
                    }

                    // TEST ALARM PREVIEW BUTTON
                    IconButton(
                        onClick = onTriggerAlarm,
                        modifier = Modifier.size(48.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Default.NotificationsActive,
                            contentDescription = "Test Alarm Screen",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                } else {
                    AccessibleText(
                        text = "✓ Taken at ${log.takenTimestamp?.let { 
                            java.text.SimpleDateFormat("hh:mm a", java.util.Locale.getDefault()).format(java.util.Date(it)) 
                        } ?: "Recorded"}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF047857)
                    )
                }
            }
        }
    }
}
