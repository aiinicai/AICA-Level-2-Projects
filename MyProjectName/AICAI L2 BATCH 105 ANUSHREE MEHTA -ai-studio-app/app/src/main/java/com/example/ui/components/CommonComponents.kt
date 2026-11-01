package com.example.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material.icons.filled.RecordVoiceOver
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog

/** Top-bar button that opens a menu of colour palettes (Mustard, Salmon, Greyish Blue, Pearl, Sage, Original). */
@Composable
fun PalettePickerButton(
    current: com.example.ui.theme.AppPalette?,
    onSelect: (com.example.ui.theme.AppPalette?) -> Unit,
    tint: Color = Color.White
) {
    var open by remember { mutableStateOf(false) }
    Box {
        IconButton(onClick = { open = true }, modifier = Modifier.testTag("palette_picker_btn")) {
            Icon(
                imageVector = Icons.Default.Palette,
                contentDescription = "Choose app colours",
                tint = tint,
                modifier = Modifier.size(28.dp)
            )
        }
        androidx.compose.material3.DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            val options: List<com.example.ui.theme.AppPalette?> = com.example.ui.theme.AppPalette.values().toList() + null
            options.forEach { p ->
                androidx.compose.material3.DropdownMenuItem(
                    text = {
                        Text(
                            text = (p?.label ?: "Original (per profile)") + if (p == current) "  ✓" else "",
                            fontSize = 17.sp,
                            fontWeight = if (p == current) FontWeight.Bold else FontWeight.Normal
                        )
                    },
                    leadingIcon = {
                        Box(
                            modifier = Modifier
                                .size(26.dp)
                                .clip(CircleShape)
                                .background(p?.swatch ?: Color(0xFF4A6B53))
                                .border(1.5.dp, Color(0x55000000), CircleShape)
                        )
                    },
                    onClick = { onSelect(p); open = false }
                )
            }
        }
    }
}
@Composable
fun SeniorLargeButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    isPrimary: Boolean = true,
    testTag: String = "senior_large_button"
) {
    if (isPrimary) {
        Button(
            onClick = onClick,
            modifier = modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = 64.dp)
                .testTag(testTag),
            shape = RoundedCornerShape(20.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            ),
            contentPadding = PaddingValues(horizontal = 24.dp, vertical = 16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                if (icon != null) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        modifier = Modifier.size(30.dp)
                    )
                    Spacer(modifier = Modifier.width(14.dp))
                }
                Text(
                    text = text,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
            }
        }
    } else {
        OutlinedButton(
            onClick = onClick,
            modifier = modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = 64.dp)
                .testTag(testTag),
            shape = RoundedCornerShape(20.dp),
            border = ButtonDefaults.outlinedButtonBorder.copy(width = 2.dp),
            contentPadding = PaddingValues(horizontal = 24.dp, vertical = 16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                if (icon != null) {
                    Icon(
                        imageVector = icon,
                        contentDescription = null,
                        modifier = Modifier.size(28.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                }
                Text(
                    text = text,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
fun ReadAloudButton(
    textToSpeak: String,
    onSpeak: (String) -> Unit,
    onStop: () -> Unit,
    isSpeaking: Boolean,
    modifier: Modifier = Modifier,
    label: String = "Read this aloud"
) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 1.0f,
        targetValue = if (isSpeaking) 1.08f else 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(600, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )

    Surface(
        onClick = {
            if (isSpeaking) onStop() else onSpeak(textToSpeak)
        },
        modifier = modifier
            .scale(if (isSpeaking) scale else 1.0f)
            .defaultMinSize(minHeight = 52.dp)
            .testTag("read_aloud_button"),
        shape = RoundedCornerShape(16.dp),
        color = if (isSpeaking) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.primaryContainer,
        shadowElevation = 2.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = if (isSpeaking) Icons.Default.Stop else Icons.Default.VolumeUp,
                contentDescription = label,
                tint = if (isSpeaking) Color.White else MaterialTheme.colorScheme.onPrimaryContainer,
                modifier = Modifier.size(26.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = if (isSpeaking) "Stop reading" else label,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = if (isSpeaking) Color.White else MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}

@Composable
fun MicrophoneInputButton(
    onTranscribed: (String) -> Unit,
    sampleSuggestions: List<String> = listOf("I am feeling joyful today", "The morning garden smells lovely", "I enjoyed our phone call yesterday"),
    modifier: Modifier = Modifier
) {
    var isListening by remember { mutableStateOf(false) }
    var showDialog by remember { mutableStateOf(false) }

    IconButton(
        onClick = { showDialog = true },
        modifier = modifier
            .size(56.dp)
            .clip(CircleShape)
            .background(MaterialTheme.colorScheme.primaryContainer)
            .testTag("mic_input_button")
    ) {
        Icon(
            imageVector = Icons.Default.Mic,
            contentDescription = "Speak aloud using microphone",
            tint = MaterialTheme.colorScheme.onPrimaryContainer,
            modifier = Modifier.size(30.dp)
        )
    }

    if (showDialog) {
        Dialog(onDismissRequest = { showDialog = false }) {
            Surface(
                shape = RoundedCornerShape(24.dp),
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 8.dp,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        imageVector = Icons.Default.RecordVoiceOver,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Voice Assistant",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Speak clearly into your microphone, or tap a quick idea below to fill in your thought:",
                        fontSize = 18.sp,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(16.dp))

                    sampleSuggestions.forEach { suggestion ->
                        Surface(
                            onClick = {
                                onTranscribed(suggestion)
                                showDialog = false
                            },
                            shape = RoundedCornerShape(12.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp)
                        ) {
                            Text(
                                text = "“$suggestion”",
                                fontSize = 17.sp,
                                modifier = Modifier.padding(14.dp),
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))
                    Button(
                        onClick = { showDialog = false },
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.defaultMinSize(minHeight = 50.dp)
                    ) {
                        Text("Done", fontSize = 18.sp)
                    }
                }
            }
        }
    }
}

@Composable
fun MedicineProgressRing(
    takenCount: Int,
    totalCount: Int,
    modifier: Modifier = Modifier
) {
    val progress = if (totalCount > 0) takenCount.toFloat() / totalCount else 0f
    val isComplete = takenCount >= totalCount && totalCount > 0

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 3.dp
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Today's Medicine Progress",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = if (isComplete) "All caught up! Wonderful job." else "$takenCount of $totalCount doses taken today",
                    fontSize = 18.sp,
                    color = if (isComplete) Color(0xFF1B6C48) else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(80.dp)
                    .padding(4.dp)
            ) {
                CircularProgressIndicator(
                    progress = { 1.0f },
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    strokeWidth = 9.dp,
                    modifier = Modifier.fillMaxSize()
                )
                CircularProgressIndicator(
                    progress = { progress },
                    color = if (isComplete) Color(0xFF1B6C48) else MaterialTheme.colorScheme.primary,
                    strokeWidth = 9.dp,
                    modifier = Modifier.fillMaxSize()
                )
                if (isComplete) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = "Completed",
                        tint = Color(0xFF1B6C48),
                        modifier = Modifier.size(36.dp)
                    )
                } else {
                    Text(
                        text = "${(progress * 100).toInt()}%",
                        fontWeight = FontWeight.Bold,
                        fontSize = 17.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}
