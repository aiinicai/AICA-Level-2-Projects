package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Accessibility
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.ui.theme.CelestialAmber
import com.example.ui.theme.CelestialCyan
import com.example.ui.theme.CelestialGold
import com.example.ui.theme.CelestialMint
import com.example.ui.theme.CelestialRose
import com.example.ui.theme.CosmicBorder
import com.example.ui.theme.CosmicCard
import com.example.ui.theme.CosmicCardElevated
import com.example.ui.theme.CosmicDark
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextSoft
import com.example.ui.theme.TextWhite
import kotlinx.coroutines.delay

@Composable
fun RoutinesDialog(
    routineType: String,
    onComplete: (String) -> Unit,
    onDismiss: () -> Unit
) {
    val (title, icon, color, durationSeconds, steps) = when (routineType) {
        "EYE" -> RoutineDetails(
            "Eye Refresh (20-20-20)",
            Icons.Default.Visibility,
            CelestialCyan,
            20,
            listOf(
                "Step 1: Blink gently 10 times to naturally rehydrate cornea.",
                "Step 2: Look at an object 20 feet away to relax focusing muscles.",
                "Step 3: Rub palms together and cup warm hands softly over your eyes."
            )
        )
        "NECK" -> RoutineDetails(
            "Neck Relief Stretch",
            Icons.Default.Accessibility,
            CelestialRose,
            30,
            listOf(
                "Step 1: Lower your chin slowly towards your chest (hold 10s).",
                "Step 2: Gently tilt right ear towards right shoulder (hold 10s).",
                "Step 3: Slowly tilt left ear towards left shoulder (hold 10s)."
            )
        )
        "DESK" -> RoutineDetails(
            "Desk Mobility & Posture",
            Icons.Default.SelfImprovement,
            CelestialMint,
            30,
            listOf(
                "Step 1: Interlace fingers, push palms to the sky, deep inhale.",
                "Step 2: Gentle seated spinal twist to the right, then left.",
                "Step 3: Roll shoulders backwards 5 times with slow exhalations."
            )
        )
        else -> RoutineDetails(
            "7-Minute Quick Energiser",
            Icons.Default.FitnessCenter,
            CelestialAmber,
            45,
            listOf(
                "Step 1: Brisk march or gentle jumping jacks in place (15s).",
                "Step 2: Wall sit or air squats at comfortable depth (15s).",
                "Step 3: High knees and overhead reaching breath (15s)."
            )
        )
    }

    var timeLeft by remember { mutableIntStateOf(durationSeconds) }
    var isRunning by remember { mutableStateOf(true) }
    var isDone by remember { mutableStateOf(false) }

    LaunchedEffect(isRunning, timeLeft) {
        if (isRunning && timeLeft > 0) {
            delay(1000)
            timeLeft -= 1
            if (timeLeft == 0) {
                isDone = true
                isRunning = false
            }
        }
    }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = CosmicCard),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, color.copy(alpha = 0.5f), RoundedCornerShape(24.dp))
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(20.dp)
            ) {
                // Header
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
                                .background(color.copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(imageVector = icon, contentDescription = null, tint = color, modifier = Modifier.size(20.dp))
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(text = title, fontWeight = FontWeight.Bold, fontSize = 16.sp, color = TextWhite)
                    }
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextSoft)
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Timer Visualizer
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(120.dp)
                        .clip(CircleShape)
                        .background(CosmicCardElevated)
                        .border(2.dp, color, CircleShape)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = if (isDone) "Done!" else "${timeLeft}s",
                            fontSize = 28.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (isDone) CelestialMint else TextWhite
                        )
                        Text(
                            text = if (isDone) "Great job!" else "Remaining",
                            fontSize = 11.sp,
                            color = TextMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                LinearProgressIndicator(
                    progress = { (durationSeconds - timeLeft).toFloat() / durationSeconds.toFloat() },
                    color = color,
                    trackColor = CosmicCardElevated,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp))
                )

                Spacer(modifier = Modifier.height(18.dp))

                // Step Instructions
                Column(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    steps.forEach { step ->
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(10.dp))
                                .background(CosmicCardElevated)
                                .padding(10.dp)
                        ) {
                            Text(text = step, fontSize = 12.sp, color = TextSoft, lineHeight = 16.sp)
                        }
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Actions
                if (isDone) {
                    Button(
                        onClick = { onComplete(routineType) },
                        colors = ButtonDefaults.buttonColors(containerColor = CelestialMint, contentColor = CosmicDark),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Claim Routine Points", fontWeight = FontWeight.Bold)
                    }
                } else {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        OutlinedButton(
                            onClick = { isRunning = !isRunning },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(if (isRunning) "Pause" else "Resume", fontSize = 13.sp)
                        }

                        Button(
                            onClick = { onComplete(routineType) },
                            colors = ButtonDefaults.buttonColors(containerColor = color, contentColor = CosmicDark),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Mark Done", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        }
                    }
                }
            }
        }
    }
}

private data class RoutineDetails(
    val title: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
    val color: Color,
    val durationSeconds: Int,
    val steps: List<String>
)
