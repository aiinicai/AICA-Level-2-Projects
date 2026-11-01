package com.example.ui.screens.senior

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
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
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Bedtime
import androidx.compose.material.icons.filled.Nightlight
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.data.model.SleepRecord
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.ReadAloudButton
import com.example.ui.components.SeniorLargeButton

@Composable
fun SeniorSleepScreen(viewModel: GenerationsAppViewModel) {
    val sleepRecords by viewModel.sleepRecords.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()
    var showLogDialog by remember { mutableStateOf(false) }

    val avgHours = if (sleepRecords.isNotEmpty()) {
        sleepRecords.map { it.durationHours }.average().toFloat()
    } else 7.5f

    val latestRecord = sleepRecords.lastOrNull()
    val summaryText = "Your sleep health is looking wonderful, Eleanor! You averaged ${String.format("%.1f", avgHours)} hours of sleep over the past week. Last night you slept ${latestRecord?.durationHours ?: 8.0f} hours from ${latestRecord?.bedtime ?: "10:00 PM"} to ${latestRecord?.wakeTime ?: "7:00 AM"}."

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_sleep_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "Rest & Sleep Health",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Gentle nightly tracking for healthy days",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        item {
            ReadAloudButton(
                textToSpeak = summaryText,
                onSpeak = { viewModel.speakAloud(it) },
                onStop = { viewModel.stopSpeaking() },
                isSpeaking = isSpeaking,
                modifier = Modifier.fillMaxWidth()
            )
        }

        // Weekly Sleep Chart Card
        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "Weekly Sleep Pattern",
                                fontSize = 22.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Average: ${String.format("%.1f", avgHours)} hrs / night",
                                fontSize = 18.sp,
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.primaryContainer
                        ) {
                            Text(
                                text = "Goal: 8h",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    // Compose Canvas Weekly Bar Chart
                    SleepWeeklyBarChart(
                        records = sleepRecords,
                        targetHours = 8.0f,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceAround
                    ) {
                        sleepRecords.takeLast(7).forEach { rec ->
                            Text(
                                text = rec.dayLabel,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
        }

        // Log Today's Sleep Button (64dp)
        item {
            SeniorLargeButton(
                text = "Log Last Night's Sleep",
                icon = Icons.Default.Bedtime,
                onClick = { showLogDialog = true },
                testTag = "log_sleep_button"
            )
        }

        // Nightly Sleep Log History Header
        item {
            Text(
                text = "Recent Nights",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        items(sleepRecords.reversed(), key = { it.id }) { record ->
            SleepRecordCard(record = record)
        }
    }

    if (showLogDialog) {
        LogSleepDialog(
            onDismiss = { showLogDialog = false },
            onSave = { bedtime, wake, hours, stars, notes ->
                viewModel.addSleepRecord(bedtime, wake, hours, stars, notes)
                showLogDialog = false
            }
        )
    }
}

@Composable
fun SleepWeeklyBarChart(
    records: List<SleepRecord>,
    targetHours: Float,
    modifier: Modifier = Modifier
) {
    val barColor = MaterialTheme.colorScheme.primary
    val goalColor = Color(0xFFE76F51)

    Canvas(modifier = modifier) {
        val count = records.size.coerceAtLeast(1)
        val spacing = size.width / count
        val barWidth = spacing * 0.55f
        val maxScaleHours = 10.0f

        // Draw 8-hour target dotted line
        val targetY = size.height * (1f - (targetHours / maxScaleHours))
        drawLine(
            color = goalColor,
            start = Offset(0f, targetY),
            end = Offset(size.width, targetY),
            strokeWidth = 3f,
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(14f, 10f), 0f)
        )

        records.forEachIndexed { i, record ->
            val barHeight = size.height * (record.durationHours / maxScaleHours)
            val left = (i * spacing) + (spacing - barWidth) / 2
            val top = size.height - barHeight

            drawRoundRect(
                color = barColor,
                topLeft = Offset(left, top),
                size = Size(barWidth, barHeight),
                cornerRadius = CornerRadius(12f, 12f)
            )
        }
    }
}

@Composable
fun SleepRecordCard(record: SleepRecord) {
    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(46.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primaryContainer),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Nightlight,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(26.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "${record.dayLabel}, ${record.date}",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "${record.bedtime} – ${record.wakeTime}",
                            fontSize = 17.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "${String.format("%.1f", record.durationHours)} hrs",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Row {
                        repeat(record.qualityStars) {
                            Icon(
                                imageVector = Icons.Default.Star,
                                contentDescription = null,
                                tint = Color(0xFFFFB703),
                                modifier = Modifier.size(18.dp)
                            )
                        }
                    }
                }
            }

            if (record.notes.isNotBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "“${record.notes}”",
                    fontSize = 17.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun LogSleepDialog(
    onDismiss: () -> Unit,
    onSave: (bedtime: String, wake: String, hours: Float, quality: Int, notes: String) -> Unit
) {
    var bedtime by remember { mutableStateOf("10:15 PM") }
    var wakeTime by remember { mutableStateOf("7:00 AM") }
    var hours by remember { mutableFloatStateOf(8.0f) }
    var stars by remember { mutableIntStateOf(5) }
    var notes by remember { mutableStateOf("Felt calm and rested") }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 8.dp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp)
        ) {
            Column(modifier = Modifier.padding(22.dp)) {
                Text(
                    text = "Log Sleep",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(16.dp))

                OutlinedTextField(
                    value = bedtime,
                    onValueChange = { bedtime = it },
                    label = { Text("Bedtime (e.g. 10:00 PM)", fontSize = 17.sp) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)
                )
                Spacer(modifier = Modifier.height(10.dp))

                OutlinedTextField(
                    value = wakeTime,
                    onValueChange = { wakeTime = it },
                    label = { Text("Wake Time (e.g. 6:45 AM)", fontSize = 17.sp) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)
                )
                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = "Total Sleep: ${String.format("%.1f", hours)} hours",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf(6.5f, 7.0f, 7.5f, 8.0f, 8.5f).forEach { h ->
                        Surface(
                            onClick = { hours = h },
                            shape = RoundedCornerShape(10.dp),
                            color = if (hours == h) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(
                                text = "${h}h",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                textAlign = TextAlign.Center,
                                modifier = Modifier.padding(vertical = 8.dp),
                                color = if (hours == h) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                Text(
                    text = "Sleep Quality Rating:",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    (1..5).forEach { starIndex ->
                        Surface(
                            onClick = { stars = starIndex },
                            color = Color.Transparent,
                            modifier = Modifier.padding(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Star,
                                contentDescription = "$starIndex stars",
                                tint = if (starIndex <= stars) Color(0xFFFFB703) else MaterialTheme.colorScheme.surfaceVariant,
                                modifier = Modifier.size(36.dp)
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Notes (e.g. Listened to ocean sounds)", fontSize = 17.sp) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)
                )

                Spacer(modifier = Modifier.height(20.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.height(52.dp)
                    ) {
                        Text("Cancel", fontSize = 18.sp)
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Button(
                        onClick = { onSave(bedtime, wakeTime, hours, stars, notes) },
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.height(52.dp)
                    ) {
                        Text("Save Record", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
