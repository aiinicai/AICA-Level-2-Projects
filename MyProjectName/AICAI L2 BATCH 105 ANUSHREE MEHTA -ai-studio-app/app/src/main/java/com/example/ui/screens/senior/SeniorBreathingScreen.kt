package com.example.ui.screens.senior

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.ReadAloudButton
import com.example.ui.components.SeniorLargeButton
import kotlinx.coroutines.delay

enum class BreathingPhase {
    IDLE,
    INHALE,
    HOLD,
    EXHALE,
    COMPLETED
}

@Composable
fun SeniorBreathingScreen(viewModel: GenerationsAppViewModel) {
    val isSpeaking by viewModel.isSpeaking.collectAsState()

    var isRunning by remember { mutableStateOf(false) }
    var phase by remember { mutableStateOf(BreathingPhase.IDLE) }
    var remainingSeconds by remember { mutableIntStateOf(60) }
    var currentCycle by remember { mutableIntStateOf(1) }
    var voiceGuidanceEnabled by remember { mutableStateOf(true) }

    // Target animation scale for breathing orb
    val targetScale = when (phase) {
        BreathingPhase.INHALE -> 1.0f
        BreathingPhase.HOLD -> 0.96f
        BreathingPhase.EXHALE -> 0.52f
        BreathingPhase.COMPLETED -> 0.75f
        BreathingPhase.IDLE -> 0.65f
    }

    val animatedScale by animateFloatAsState(
        targetValue = targetScale,
        animationSpec = when (phase) {
            BreathingPhase.INHALE -> tween(durationMillis = 4000, easing = FastOutSlowInEasing)
            BreathingPhase.HOLD -> tween(durationMillis = 2000, easing = LinearEasing)
            BreathingPhase.EXHALE -> tween(durationMillis = 4000, easing = FastOutSlowInEasing)
            else -> tween(durationMillis = 800)
        },
        label = "breathingScale"
    )

    // Breathing Coroutine Controller: 6 cycles of (4s Inhale, 2s Hold, 4s Exhale) = 60s
    LaunchedEffect(isRunning, phase) {
        if (!isRunning) return@LaunchedEffect

        when (phase) {
            BreathingPhase.IDLE -> {
                phase = BreathingPhase.INHALE
                remainingSeconds = 60
                currentCycle = 1
                if (voiceGuidanceEnabled) viewModel.speakAloud("Breathe in slowly through your nose...")
            }
            BreathingPhase.INHALE -> {
                delay(4000)
                if (isRunning) {
                    phase = BreathingPhase.HOLD
                    if (voiceGuidanceEnabled) viewModel.speakAloud("Hold gently...")
                }
            }
            BreathingPhase.HOLD -> {
                delay(2000)
                if (isRunning) {
                    phase = BreathingPhase.EXHALE
                    if (voiceGuidanceEnabled) viewModel.speakAloud("Breathe out softly through your mouth...")
                }
            }
            BreathingPhase.EXHALE -> {
                delay(4000)
                if (isRunning) {
                    if (currentCycle >= 6 || remainingSeconds <= 0) {
                        phase = BreathingPhase.COMPLETED
                        isRunning = false
                        viewModel.awardChildPoints(15)
                        viewModel.recordBreathingCompleted()
                        if (voiceGuidanceEnabled) viewModel.speakAloud("Wonderful job. Your heart and mind are calm and relaxed.")
                    } else {
                        currentCycle += 1
                        phase = BreathingPhase.INHALE
                        if (voiceGuidanceEnabled) viewModel.speakAloud("Breathe in slowly...")
                    }
                }
            }
            BreathingPhase.COMPLETED -> {}
        }
    }

    // 1-second countdown clock ticker
    LaunchedEffect(isRunning) {
        while (isRunning && remainingSeconds > 0) {
            delay(1000)
            remainingSeconds -= 1
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_breathing_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        item {
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Calm Breathing",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    text = "1-minute guided deep breathing to reduce anxiety & ease heart rhythm",
                    fontSize = 18.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        // Voice Guidance Switch Card
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.VolumeUp,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(26.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Spoken Guidance",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = if (voiceGuidanceEnabled) "Voice cues active for each breath" else "Visual cues only",
                                fontSize = 14.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    Switch(
                        checked = voiceGuidanceEnabled,
                        onCheckedChange = {
                            voiceGuidanceEnabled = it
                            if (!it) viewModel.stopSpeaking()
                        },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = Color.White,
                            checkedTrackColor = MaterialTheme.colorScheme.primary
                        )
                    )
                }
            }
        }

        // Animated Breathing Visual Canvas Card
        item {
            Card(
                shape = RoundedCornerShape(26.dp),
                colors = CardDefaults.cardColors(
                    containerColor = when (phase) {
                        BreathingPhase.INHALE -> Color(0xFFE0F2F1)
                        BreathingPhase.HOLD -> Color(0xFFFEF3C7)
                        BreathingPhase.EXHALE -> Color(0xFFF1F5F9)
                        BreathingPhase.COMPLETED -> Color(0xFFDCFCE7)
                        BreathingPhase.IDLE -> MaterialTheme.colorScheme.surface
                    }
                ),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .defaultMinSize(minHeight = 360.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.SpaceBetween
                ) {
                    // Header Status & Cycle Count
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.surface
                        ) {
                            Text(
                                text = "0:${if (remainingSeconds < 10) "0$remainingSeconds" else "$remainingSeconds"}",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp)
                            )
                        }

                        Text(
                            text = if (phase == BreathingPhase.COMPLETED) "Complete! 🌟" else "Cycle $currentCycle of 6",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    // The Animated Glowing Breathing Orb (Canvas)
                    Box(
                        modifier = Modifier
                            .size(220.dp)
                            .testTag("breathing_animated_orb"),
                        contentAlignment = Alignment.Center
                    ) {
                        Canvas(modifier = Modifier.fillMaxSize()) {
                            val center = Offset(size.width / 2, size.height / 2)
                            val maxRadius = (size.minDimension / 2) * animatedScale

                            // Outer gentle ripple ring
                            drawCircle(
                                color = Color(0xFF14535C).copy(alpha = 0.12f * animatedScale),
                                radius = maxRadius * 1.18f,
                                center = center
                            )
                            // Middle soft wave ring
                            drawCircle(
                                color = Color(0xFF2A7C8A).copy(alpha = 0.22f * animatedScale),
                                radius = maxRadius * 1.08f,
                                center = center
                            )
                            // Core soothing orb gradient
                            drawCircle(
                                brush = Brush.radialGradient(
                                    colors = listOf(
                                        Color(0xFF80CBC4),
                                        Color(0xFF14535C),
                                        Color(0xFF0E383F)
                                    ),
                                    center = center,
                                    radius = maxRadius
                                ),
                                radius = maxRadius,
                                center = center
                            )
                        }

                        // Central gentle phase icon / prompt
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.padding(16.dp)
                        ) {
                            Icon(
                                imageVector = when (phase) {
                                    BreathingPhase.COMPLETED -> Icons.Default.Check
                                    BreathingPhase.INHALE -> Icons.Default.SelfImprovement
                                    BreathingPhase.HOLD -> Icons.Default.Favorite
                                    else -> Icons.Default.SelfImprovement
                                },
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(42.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    // Phase Text Instructions (24sp+, accessible high contrast)
                    Text(
                        text = when (phase) {
                            BreathingPhase.INHALE -> "🌿 Breathe In Slowly..."
                            BreathingPhase.HOLD -> "✨ Hold Gently..."
                            BreathingPhase.EXHALE -> "🍃 Breathe Out Slowly..."
                            BreathingPhase.COMPLETED -> "🎉 Feeling Calm & Refreshed"
                            BreathingPhase.IDLE -> "Ready to find your calm?"
                        },
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurface
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = when (phase) {
                            BreathingPhase.INHALE -> "Inhale through your nose, expanding your belly"
                            BreathingPhase.HOLD -> "Pause comfortably, letting your shoulders drop"
                            BreathingPhase.EXHALE -> "Exhale softly through your mouth, letting go of tension"
                            BreathingPhase.COMPLETED -> "Your heart rate has slowed and muscles relaxed"
                            BreathingPhase.IDLE -> "Sit comfortably and follow the soothing circle"
                        },
                        fontSize = 18.sp,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Action Buttons (64dp button heights)
        item {
            when {
                phase == BreathingPhase.COMPLETED -> {
                    SeniorLargeButton(
                        text = "Breathe Again (1 Minute)",
                        icon = Icons.Default.Refresh,
                        onClick = {
                            phase = BreathingPhase.INHALE
                            remainingSeconds = 60
                            currentCycle = 1
                            isRunning = true
                            if (voiceGuidanceEnabled) viewModel.speakAloud("Starting another relaxing 1-minute breathing session. Breathe in slowly...")
                        },
                        testTag = "breathe_again_button"
                    )
                }
                !isRunning -> {
                    SeniorLargeButton(
                        text = if (phase == BreathingPhase.IDLE) "Begin 1-Minute Calm Exercise" else "Resume Exercise",
                        icon = Icons.Default.PlayArrow,
                        onClick = {
                            isRunning = true
                            if (phase == BreathingPhase.IDLE) {
                                phase = BreathingPhase.INHALE
                            }
                        },
                        testTag = "start_breathing_button"
                    )
                }
                else -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Button(
                            onClick = {
                                isRunning = false
                                viewModel.stopSpeaking()
                            },
                            shape = RoundedCornerShape(18.dp),
                            modifier = Modifier
                                .weight(1f)
                                .defaultMinSize(minHeight = 64.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                                contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        ) {
                            Icon(Icons.Default.Pause, contentDescription = null, modifier = Modifier.size(28.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Pause", fontSize = 19.sp, fontWeight = FontWeight.Bold)
                        }

                        Button(
                            onClick = {
                                isRunning = false
                                phase = BreathingPhase.IDLE
                                remainingSeconds = 60
                                currentCycle = 1
                                viewModel.stopSpeaking()
                            },
                            shape = RoundedCornerShape(18.dp),
                            modifier = Modifier
                                .weight(1f)
                                .defaultMinSize(minHeight = 64.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color(0xFFF1F5F9),
                                contentColor = Color(0xFF475569)
                            )
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(28.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Reset", fontSize = 19.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // Anxiety Reduction Tip Card
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.SelfImprovement,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(28.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "Why 1-Minute Breathing Works",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Taking 6 slow, conscious breaths activates your vagus nerve and parasympathetic system. In just 60 seconds, it gently lowers systolic blood pressure, slows your pulse, and clears feelings of anxiety.",
                        fontSize = 17.sp,
                        lineHeight = 25.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
