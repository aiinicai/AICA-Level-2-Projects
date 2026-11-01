package com.example.ui.screens.senior

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
import com.example.data.model.StoryChoice
import com.example.data.model.StoryTurn
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.MicrophoneInputButton
import com.example.ui.components.ReadAloudButton

@Composable
fun SeniorStoriesScreen(viewModel: GenerationsAppViewModel) {
    val currentStory by viewModel.currentStory.collectAsState()
    val isGenerating by viewModel.isGeneratingStory.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()

    var customIdeaText by remember { mutableStateOf("") }

    val themes = listOf(
        "The Time-Traveling Bicycle of Willow Creek",
        "Grandma's Secret Starlight Garden",
        "The Mystery of the Whispering Oak",
        "The Moon Cat and the Compass",
        "The Great Blueberry Pie Bake-Off"
    )

    val currentTurn = currentStory.turns.lastOrNull()
    val fullStoryText = currentStory.turns.joinToString("\n\n") { "Chapter ${it.turnNumber}: ${it.narratorText}" }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_stories_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Generations Storybook",
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Text(
                        text = "Co-writing with Leo • Turn-based adventure",
                        fontSize = 18.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Theme Chips Carousel
        item {
            Column {
                Text(
                    text = "Story Themes:",
                    fontSize = 19.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(themes) { theme ->
                        val isSelected = theme == currentStory.theme
                        Surface(
                            onClick = { viewModel.changeStoryTheme(theme) },
                            shape = RoundedCornerShape(16.dp),
                            color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                            border = if (isSelected) ButtonDefaults.outlinedButtonBorder.copy(width = 2.dp) else null,
                            modifier = Modifier.defaultMinSize(minHeight = 44.dp)
                        ) {
                            Text(
                                text = theme,
                                fontSize = 16.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)
                            )
                        }
                    }
                }
            }
        }

        // Read entire story aloud button
        item {
            ReadAloudButton(
                textToSpeak = fullStoryText,
                onSpeak = { viewModel.speakAloud(it) },
                onStop = { viewModel.stopSpeaking() },
                isSpeaking = isSpeaking,
                modifier = Modifier.fillMaxWidth(),
                label = "Read whole story aloud"
            )
        }

        // Story Chapters Timeline
        items(currentStory.turns) { turn ->
            StoryTurnCard(
                turn = turn,
                onSpeakTurn = { viewModel.speakAloud(turn.narratorText) },
                isSpeaking = isSpeaking
            )
        }

        // Active Turn: 3 Big Choices or Custom Idea
        if (currentTurn != null && !currentStory.isComplete) {
            item {
                Card(
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.AutoStories,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(28.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = "What should happen next?",
                                fontSize = 22.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }

                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Tap a choice for Chapter ${currentTurn.turnNumber + 1}, or type your own idea below:",
                            fontSize = 18.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(16.dp))

                        if (isGenerating) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 24.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    CircularProgressIndicator(
                                        color = MaterialTheme.colorScheme.primary,
                                        strokeWidth = 4.dp
                                    )
                                    Spacer(modifier = Modifier.height(12.dp))
                                    Text(
                                        text = "Weaving the next heartwarming chapter...",
                                        fontSize = 18.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
                            }
                        } else {
                            // 3 Tappable Big Choices
                            currentTurn.choices.forEachIndexed { idx, choice ->
                                Button(
                                    onClick = { viewModel.advanceStoryWithChoice(choice.text) },
                                    shape = RoundedCornerShape(18.dp),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = when (idx) {
                                            0 -> MaterialTheme.colorScheme.primary
                                            1 -> Color(0xFFE76F51)
                                            else -> Color(0xFF7C3AED)
                                        },
                                        contentColor = Color.White
                                    ),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .defaultMinSize(minHeight = 64.dp)
                                        .padding(vertical = 5.dp)
                                        .testTag("story_choice_$idx")
                                ) {
                                    Text(
                                        text = "${idx + 1}.  ${choice.text}",
                                        fontSize = 19.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            // Custom Idea Input with Microphone
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedTextField(
                                    value = customIdeaText,
                                    onValueChange = { customIdeaText = it },
                                    placeholder = { Text("Or write your own twist...", fontSize = 18.sp) },
                                    shape = RoundedCornerShape(16.dp),
                                    modifier = Modifier
                                        .weight(1f)
                                        .defaultMinSize(minHeight = 60.dp),
                                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 18.sp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                MicrophoneInputButton(
                                    onTranscribed = { transcribed ->
                                        customIdeaText = transcribed
                                    },
                                    sampleSuggestions = listOf(
                                        "They discover a hidden secret recipe book.",
                                        "The friendly owl reveals he can talk!",
                                        "Leo and Eleanor build a stargazing telescope."
                                    )
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Button(
                                    onClick = {
                                        if (customIdeaText.isNotBlank()) {
                                            viewModel.advanceStoryWithCustomIdea(customIdeaText)
                                            customIdeaText = ""
                                        }
                                    },
                                    shape = RoundedCornerShape(16.dp),
                                    modifier = Modifier.size(56.dp),
                                    contentPadding = PaddingValues(0.dp),
                                    enabled = customIdeaText.isNotBlank()
                                ) {
                                    Icon(Icons.Default.Send, contentDescription = "Submit idea")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun StoryTurnCard(
    turn: StoryTurn,
    onSpeakTurn: () -> Unit,
    isSpeaking: Boolean
) {
    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primaryContainer),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "${turn.turnNumber}",
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "Chapter ${turn.turnNumber}",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Surface(
                    onClick = onSpeakTurn,
                    shape = RoundedCornerShape(12.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.defaultMinSize(minHeight = 40.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.VolumeUp,
                            contentDescription = "Read chapter",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "Listen",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = turn.narratorText,
                fontSize = 20.sp,
                lineHeight = 30.sp,
                color = MaterialTheme.colorScheme.onSurface
            )

            if (turn.chosenChoice != null) {
                Spacer(modifier = Modifier.height(12.dp))
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Text(
                        text = "Co-author choice: “${turn.chosenChoice}”",
                        fontSize = 17.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
                    )
                }
            }
        }
    }
}
