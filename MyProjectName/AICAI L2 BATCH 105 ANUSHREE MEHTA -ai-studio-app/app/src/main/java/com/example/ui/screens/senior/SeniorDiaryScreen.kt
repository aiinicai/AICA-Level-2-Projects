package com.example.ui.screens.senior

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.DiaryEntry
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.MicrophoneInputButton
import com.example.ui.components.ReadAloudButton
import com.example.ui.components.SeniorLargeButton

data class MoodOption(val emoji: String, val label: String)

@Composable
fun SeniorDiaryScreen(viewModel: GenerationsAppViewModel) {
    val diaryEntries by viewModel.diaryEntries.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()

    val moods = listOf(
        MoodOption("😊", "Joyful"),
        MoodOption("😌", "Peaceful"),
        MoodOption("😐", "Neutral"),
        MoodOption("😔", "Gentle Care"),
        MoodOption("🤒", "Resting")
    )

    var selectedMoodIndex by remember { mutableIntStateOf(0) }
    var diaryText by remember { mutableStateOf("") }
    var isRecordingVoice by remember { mutableStateOf(false) }
    var recordedVoiceDuration by remember { mutableIntStateOf(0) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_diary_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "Daily Reflection Diary",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Share today's thoughts and feelings with your buddy Leo",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // New Diary Entry Card
        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = "How are you feeling right now?",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    // Mood selector row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        moods.forEachIndexed { index, mood ->
                            val isSelected = selectedMoodIndex == index
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                modifier = Modifier
                                    .clip(RoundedCornerShape(16.dp))
                                    .clickable { selectedMoodIndex = index }
                                    .background(
                                        if (isSelected) MaterialTheme.colorScheme.primaryContainer
                                        else Color.Transparent
                                    )
                                    .border(
                                        width = if (isSelected) 2.dp else 1.dp,
                                        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                                        shape = RoundedCornerShape(16.dp)
                                    )
                                    .padding(vertical = 10.dp, horizontal = 8.dp)
                                    .defaultMinSize(minWidth = 56.dp)
                            ) {
                                Text(text = mood.emoji, fontSize = 32.sp)
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = mood.label,
                                    fontSize = 14.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    // Prompt question
                    Surface(
                        shape = RoundedCornerShape(16.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.ChatBubbleOutline,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(26.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = "Today's Prompt: What is something beautiful or funny you noticed today?",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Text Field with Mic Affordance
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.Bottom
                    ) {
                        OutlinedTextField(
                            value = diaryText,
                            onValueChange = { diaryText = it },
                            placeholder = { Text("Type your note, or tap the mic to speak...", fontSize = 19.sp) },
                            modifier = Modifier
                                .weight(1f)
                                .defaultMinSize(minHeight = 110.dp),
                            shape = RoundedCornerShape(16.dp),
                            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 19.sp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        MicrophoneInputButton(
                            onTranscribed = { transcribed ->
                                diaryText = if (diaryText.isBlank()) transcribed else "$diaryText $transcribed"
                            },
                            sampleSuggestions = listOf(
                                "I enjoyed sitting in the warm morning sun watching the birds.",
                                "Leo's story idea about the carousel made me laugh happily.",
                                "Had a refreshing walk and my knee feels much better today."
                            )
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Voice Note Recording Affordance
                    Surface(
                        shape = RoundedCornerShape(16.dp),
                        color = if (isRecordingVoice) Color(0xFFFEE2E2) else MaterialTheme.colorScheme.surfaceVariant,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = if (isRecordingVoice) Icons.Default.Stop else Icons.Default.Mic,
                                    contentDescription = null,
                                    tint = if (isRecordingVoice) Color(0xFFDC2626) else MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(28.dp)
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Text(
                                    text = if (isRecordingVoice) "Recording Voice Note... (0:24)" else if (recordedVoiceDuration > 0) "Voice Note Ready (0:$recordedVoiceDuration)" else "Optional Voice Note for Leo",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = if (isRecordingVoice) Color(0xFFDC2626) else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            Button(
                                onClick = {
                                    if (isRecordingVoice) {
                                        isRecordingVoice = false
                                        recordedVoiceDuration = 32
                                    } else {
                                        isRecordingVoice = true
                                    }
                                },
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (isRecordingVoice) Color(0xFFDC2626) else MaterialTheme.colorScheme.primary
                                )
                            ) {
                                Text(if (isRecordingVoice) "Stop" else "Record", fontSize = 16.sp)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    // 64dp Primary Action Button
                    SeniorLargeButton(
                        text = "Save & Share with Leo",
                        icon = Icons.Default.Send,
                        onClick = {
                            val textToSave = if (diaryText.isBlank()) "Felt ${moods[selectedMoodIndex].label.lowercase()} today while enjoying quiet moments." else diaryText
                            viewModel.addDiaryEntry(
                                moodEmoji = moods[selectedMoodIndex].emoji,
                                moodLabel = moods[selectedMoodIndex].label,
                                noteText = textToSave,
                                voiceSec = recordedVoiceDuration
                            )
                            diaryText = ""
                            recordedVoiceDuration = 0
                        },
                        testTag = "save_diary_button"
                    )
                }
            }
        }

        // Previous Entries Header
        item {
            Text(
                text = "Past Reflections",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        items(diaryEntries, key = { it.id }) { entry ->
            PastDiaryCard(
                entry = entry,
                onReadAloud = { viewModel.speakAloud(entry.noteText) },
                isSpeaking = isSpeaking
            )
        }
    }
}

@Composable
fun PastDiaryCard(
    entry: DiaryEntry,
    onReadAloud: () -> Unit,
    isSpeaking: Boolean
) {
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
                    Text(text = entry.moodEmoji, fontSize = 28.sp)
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = entry.moodLabel,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = entry.date,
                            fontSize = 16.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Surface(
                    onClick = onReadAloud,
                    shape = RoundedCornerShape(12.dp),
                    color = MaterialTheme.colorScheme.primaryContainer,
                    modifier = Modifier.defaultMinSize(minHeight = 44.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.VolumeUp,
                            contentDescription = "Read aloud",
                            tint = MaterialTheme.colorScheme.onPrimaryContainer,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Listen",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = entry.noteText,
                fontSize = 19.sp,
                lineHeight = 27.sp,
                color = MaterialTheme.colorScheme.onSurface
            )

            if (entry.voiceNoteDurationSec > 0) {
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .clip(RoundedCornerShape(10.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = "Play voice note",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(22.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Voice message recorded (${entry.voiceNoteDurationSec}s)",
                        fontSize = 15.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}
