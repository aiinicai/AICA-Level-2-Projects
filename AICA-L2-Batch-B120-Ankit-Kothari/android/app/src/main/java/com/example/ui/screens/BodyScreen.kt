package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.filled.Accessibility
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.DirectionsWalk
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.MonitorWeight
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.engine.BmiEngine
import com.example.model.BmiRecord
import com.example.ui.theme.CelestialAmber
import com.example.ui.theme.CelestialCyan
import com.example.ui.theme.CelestialGold
import com.example.ui.theme.CelestialGoldLight
import com.example.ui.theme.CelestialLavender
import com.example.ui.theme.CelestialMint
import com.example.ui.theme.CelestialRose
import com.example.ui.theme.CosmicBorder
import com.example.ui.theme.CosmicCard
import com.example.ui.theme.CosmicCardElevated
import com.example.ui.theme.CosmicDark
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextSoft
import com.example.ui.theme.TextWhite
import com.example.viewmodel.SaathiUiState
import com.example.viewmodel.SaathiViewModel
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

@Composable
fun BodyScreen(
    state: SaathiUiState,
    viewModel: SaathiViewModel,
    modifier: Modifier = Modifier
) {
    var showBmiDialog by remember { mutableStateOf(false) }
    var useAsianCutoffs by remember { mutableStateOf(true) }

    // Walk Tracker Timer State
    var isWalking by remember { mutableStateOf(false) }
    var walkTimerSeconds by remember { mutableIntStateOf(0) }

    LaunchedEffect(isWalking) {
        while (isWalking) {
            delay(1000)
            walkTimerSeconds += 1
        }
    }

    val latestBmi = state.bmiRecords.firstOrNull() ?: BmiRecord(
        dateString = "Initial",
        weightKg = 64.5f,
        heightCm = 168f,
        waistCm = 72f,
        bmi = 22.9f,
        category = "Optimal Harmony (Healthy)",
        kindAdvice = "Your weight is in a balanced, healthy range. Keep honoring your movement, water, and rest."
    )

    val bmiAnalysis = BmiEngine.analyze(
        latestBmi.weightKg,
        latestBmi.heightCm,
        latestBmi.waistCm,
        useAsianCutoffs
    )

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(CosmicDark),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Steps & Walk Session Card
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(CelestialMint.copy(alpha = 0.2f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.DirectionsWalk, contentDescription = null, tint = CelestialMint, modifier = Modifier.size(20.dp))
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("Walk & Step Session", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("Daily Goal: ${state.profile.stepGoal} steps", fontSize = 11.sp, color = TextSoft)
                            }
                        }

                        // Walk Session Controller
                        Button(
                            onClick = {
                                if (isWalking) {
                                    isWalking = false
                                    // Log steps based on walk time (~100 steps per min)
                                    val estimatedSteps = (walkTimerSeconds / 60) * 110 + 50
                                    viewModel.logSteps(estimatedSteps.coerceAtLeast(100))
                                    walkTimerSeconds = 0
                                } else {
                                    isWalking = true
                                }
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isWalking) Color(0xFFFB7185) else CelestialMint,
                                contentColor = CosmicDark
                            ),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Icon(if (isWalking) Icons.Default.Stop else Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(if (isWalking) "Stop Walk (${walkTimerSeconds}s)" else "Start Walk", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Progress Details
                    Row(
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column {
                            Text(
                                text = "${state.dailyActivity.stepsWalked}",
                                fontSize = 28.sp,
                                fontWeight = FontWeight.Bold,
                                color = CelestialMint
                            )
                            Text("Steps Completed", fontSize = 11.sp, color = TextMuted)
                        }

                        Column(horizontalAlignment = Alignment.End) {
                            val km = ((state.dailyActivity.stepsWalked * 0.75f) / 1000f * 10f).roundToInt() / 10f
                            val calories = (state.dailyActivity.stepsWalked * 0.04f).roundToInt()
                            Text(
                                text = "$km km  •  $calories kcal",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TextWhite
                            )
                            Text("Estimated Distance", fontSize = 11.sp, color = TextMuted)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    LinearProgressIndicator(
                        progress = { (state.dailyActivity.stepsWalked.toFloat() / state.profile.stepGoal.toFloat()).coerceIn(0.05f, 1f) },
                        color = CelestialMint,
                        trackColor = CosmicCardElevated,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp))
                    )
                }
            }
        }

        // Guided Mobility & Movement Routines
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text("Guided Wellness Routines", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                    Text("Timed micro-exercises designed for desk workers & healthy living", fontSize = 12.sp, color = TextMuted)

                    Spacer(modifier = Modifier.height(14.dp))

                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        RoutineRow(
                            title = "Eye Refresh (20-20-20 Rule)",
                            subtitle = "Relieve digital screen strain in 20 seconds",
                            icon = Icons.Default.Visibility,
                            color = CelestialCyan,
                            points = "+5 pts",
                            onClick = { viewModel.openRoutine("EYE") }
                        )

                        RoutineRow(
                            title = "Neck & Upper Back Relief",
                            subtitle = "Release cervical tension and restore posture in 30s",
                            icon = Icons.Default.Accessibility,
                            color = CelestialRose,
                            points = "+10 pts",
                            onClick = { viewModel.openRoutine("NECK") }
                        )

                        RoutineRow(
                            title = "Desk Mobility & Spinal Stretch",
                            subtitle = "Gentle seated twists and chest expansion in 30s",
                            icon = Icons.Default.SelfImprovement,
                            color = CelestialMint,
                            points = "+10 pts",
                            onClick = { viewModel.openRoutine("DESK") }
                        )

                        RoutineRow(
                            title = "7-Minute Quick Energiser",
                            subtitle = "Full-body brisk movement to banish afternoon slumps",
                            icon = Icons.Default.FitnessCenter,
                            color = CelestialAmber,
                            points = "+25 pts",
                            onClick = { viewModel.openRoutine("ENERGISER") }
                        )
                    }
                }
            }
        }

        // BMI & Body Health Metrics Card
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(CelestialGold.copy(alpha = 0.2f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.MonitorWeight, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(20.dp))
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("BMI & Body Composition", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("Evidence-based body health awareness", fontSize = 11.sp, color = TextSoft)
                            }
                        }

                        Button(
                            onClick = { showBmiDialog = true },
                            colors = ButtonDefaults.buttonColors(containerColor = CelestialGold, contentColor = CosmicDark),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Log Weight", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Asian vs WHO Cutoff Switch
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(CosmicCardElevated)
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                    ) {
                        Text(
                            text = if (useAsianCutoffs) "Asian / Middle-Eastern Cut-offs (18.5 - 22.9)" else "WHO Standard Cut-offs (18.5 - 24.9)",
                            fontSize = 11.sp,
                            color = TextWhite
                        )
                        Switch(
                            checked = useAsianCutoffs,
                            onCheckedChange = { useAsianCutoffs = it },
                            colors = SwitchDefaults.colors(checkedThumbColor = CelestialGold, checkedTrackColor = CelestialAmber.copy(alpha = 0.4f))
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Current BMI Display Box
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(14.dp))
                            .background(CosmicCardElevated)
                            .padding(16.dp)
                    ) {
                        Column {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column {
                                    Text("Current BMI", fontSize = 11.sp, color = TextMuted)
                                    Text(
                                        text = "${bmiAnalysis.bmi}",
                                        fontSize = 28.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = CelestialGoldLight
                                    )
                                }
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(20.dp))
                                        .background(CelestialMint.copy(alpha = 0.2f))
                                        .border(1.dp, CelestialMint.copy(alpha = 0.5f), RoundedCornerShape(20.dp))
                                        .padding(horizontal = 10.dp, vertical = 5.dp)
                                ) {
                                    Text(bmiAnalysis.category, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = CelestialMint)
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            Text(
                                text = "Healthy Weight Range: ${bmiAnalysis.healthyMinWeight} kg - ${bmiAnalysis.healthyMaxWeight} kg",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = TextWhite
                            )

                            if (bmiAnalysis.waistToHeightRatio != null) {
                                Text(
                                    text = "Waist-to-Height Ratio: ${bmiAnalysis.waistToHeightRatio} (Healthy: < 0.5)",
                                    fontSize = 11.sp,
                                    color = TextSoft
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            Text(
                                text = "“${bmiAnalysis.kindAdvice}”",
                                fontSize = 12.sp,
                                color = CelestialLavender,
                                lineHeight = 16.sp
                            )
                        }
                    }
                }
            }
        }
    }

    // Log BMI Dialog
    if (showBmiDialog) {
        LogBmiDialog(
            initialWeight = latestBmi.weightKg,
            initialHeight = latestBmi.heightCm,
            initialWaist = latestBmi.waistCm,
            onSave = { w, h, waist ->
                viewModel.addBmiRecord(w, h, waist)
                showBmiDialog = false
            },
            onDismiss = { showBmiDialog = false }
        )
    }
}

@Composable
private fun RoutineRow(
    title: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: Color,
    points: String,
    onClick: () -> Unit
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(CosmicCardElevated)
            .clickable { onClick() }
            .padding(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .clip(CircleShape)
                    .background(color.copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text(title, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                Text(subtitle, fontSize = 10.sp, color = TextSoft)
            }
        }

        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(color.copy(alpha = 0.2f))
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            Text(points, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = color)
        }
    }
}

@Composable
fun LogBmiDialog(
    initialWeight: Float,
    initialHeight: Float,
    initialWaist: Float,
    onSave: (Float, Float, Float) -> Unit,
    onDismiss: () -> Unit
) {
    var weight by remember { mutableFloatStateOf(initialWeight) }
    var height by remember { mutableFloatStateOf(initialHeight) }
    var waist by remember { mutableFloatStateOf(if (initialWaist > 0) initialWaist else 72f) }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = CosmicCard),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text("Log Body Health Metrics", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = TextWhite)

                // Weight Slider
                Column {
                    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                        Text("Weight", fontSize = 12.sp, color = TextSoft)
                        Text("${(weight * 10f).roundToInt() / 10f} kg", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = CelestialGold)
                    }
                    Slider(
                        value = weight,
                        onValueChange = { weight = it },
                        valueRange = 35f..150f,
                        colors = SliderDefaults.colors(thumbColor = CelestialGold, activeTrackColor = CelestialGold)
                    )
                }

                // Height Slider
                Column {
                    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                        Text("Height", fontSize = 12.sp, color = TextSoft)
                        Text("${height.roundToInt()} cm", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = CelestialCyan)
                    }
                    Slider(
                        value = height,
                        onValueChange = { height = it },
                        valueRange = 120f..220f,
                        colors = SliderDefaults.colors(thumbColor = CelestialCyan, activeTrackColor = CelestialCyan)
                    )
                }

                // Waist Slider (Optional)
                Column {
                    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                        Text("Waist Circumference", fontSize = 12.sp, color = TextSoft)
                        Text("${waist.roundToInt()} cm", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = CelestialRose)
                    }
                    Slider(
                        value = waist,
                        onValueChange = { waist = it },
                        valueRange = 50f..140f,
                        colors = SliderDefaults.colors(thumbColor = CelestialRose, activeTrackColor = CelestialRose)
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(onClick = onDismiss, modifier = Modifier.weight(1f)) {
                        Text("Cancel")
                    }
                    Button(
                        onClick = { onSave(weight, height, waist) },
                        colors = ButtonDefaults.buttonColors(containerColor = CelestialGold, contentColor = CosmicDark),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Save (+15 Pts)", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
