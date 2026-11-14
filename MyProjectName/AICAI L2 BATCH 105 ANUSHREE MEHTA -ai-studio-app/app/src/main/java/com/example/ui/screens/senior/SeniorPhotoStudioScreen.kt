package com.example.ui.screens.senior

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.HistoryEdu
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.LocalFlorist
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.QuestionMark
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
import com.example.data.model.PhotoAnalysis
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.ReadAloudButton
import com.example.ui.components.SeniorLargeButton

data class SpecimenSample(
    val name: String,
    val emoji: String,
    val category: String
)

@Composable
fun SeniorPhotoStudioScreen(viewModel: GenerationsAppViewModel) {
    val analyzedPhotos by viewModel.analyzedPhotos.collectAsState()
    val isAnalyzing by viewModel.isAnalyzingPhoto.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()

    var customPhotoTitle by remember { mutableStateOf("") }
    var selectedAnalysis by remember { mutableStateOf<PhotoAnalysis?>(analyzedPhotos.firstOrNull()) }

    // Keep active selection fresh if list changes
    if (selectedAnalysis == null && analyzedPhotos.isNotEmpty()) {
        selectedAnalysis = analyzedPhotos.first()
    }

    val specimens = listOf(
        SpecimenSample("Chamomile Flower", "🌼", "Medicinal Flora"),
        SpecimenSample("English Lavender", "🪻", "Aromatherapy"),
        SpecimenSample("Aloe Vera Plant", "🪴", "Healing Succulent"),
        SpecimenSample("Antique Brass Compass", "🧭", "Heritage Artifact"),
        SpecimenSample("Monarch Butterfly", "🦋", "Pollinator Ecology"),
        SpecimenSample("Wild Mint & Sage", "🌿", "Culinary & Digestion")
    )

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_photo_studio_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "Intergenerational Photo Studio",
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Snap or choose a photo — AI uncovers its medicinal properties, historical uses, and origin for shared learning with your buddy!",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Camera / Sample Specimen Selector Card
        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = "Choose or Snap a Discovery:",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(specimens) { item ->
                            Surface(
                                onClick = {
                                    viewModel.analyzeNewPhoto(item.name, item.category)
                                },
                                shape = RoundedCornerShape(18.dp),
                                color = MaterialTheme.colorScheme.primaryContainer,
                                modifier = Modifier.defaultMinSize(minHeight = 84.dp)
                            ) {
                                Column(
                                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Text(text = item.emoji, fontSize = 32.sp)
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = item.name,
                                        fontSize = 16.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onPrimaryContainer
                                    )
                                    Text(
                                        text = item.category,
                                        fontSize = 13.sp,
                                        color = MaterialTheme.colorScheme.onPrimaryContainer
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            value = customPhotoTitle,
                            onValueChange = { customPhotoTitle = it },
                            placeholder = { Text("Or enter item name (e.g. Grandma's Teapot)", fontSize = 17.sp) },
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.weight(1f),
                            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 18.sp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Button(
                            onClick = {
                                if (customPhotoTitle.isNotBlank()) {
                                    viewModel.analyzeNewPhoto(customPhotoTitle, "User Item")
                                    customPhotoTitle = ""
                                }
                            },
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.size(56.dp),
                            contentPadding = PaddingValues(0.dp),
                            enabled = customPhotoTitle.isNotBlank()
                        ) {
                            Icon(Icons.Default.CameraAlt, contentDescription = "Analyze")
                        }
                    }
                }
            }
        }

        if (isAnalyzing) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 30.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator(color = MaterialTheme.colorScheme.primary, strokeWidth = 4.dp)
                        Spacer(modifier = Modifier.height(14.dp))
                        Text(
                            text = "Analyzing medicinal properties, origins, and folklore...",
                            fontSize = 19.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
        }

        // Active Analysis Details
        val analysis = selectedAnalysis ?: analyzedPhotos.firstOrNull()
        if (analysis != null) {
            val fullReadout = "${analysis.subjectTitle}. ${analysis.summary} Medicinal benefits: ${analysis.medicinalProperties} Practical uses: ${analysis.practicalUses} Origin: ${analysis.originAndHistory} Conversation prompt for you and your buddy: ${analysis.generationalConversationPrompt}"

            item {
                ReadAloudButton(
                    textToSpeak = fullReadout,
                    onSpeak = { viewModel.speakAloud(it) },
                    onStop = { viewModel.stopSpeaking() },
                    isSpeaking = isSpeaking,
                    modifier = Modifier.fillMaxWidth(),
                    label = "Read plant & heritage facts aloud"
                )
            }

            item {
                Card(
                    shape = RoundedCornerShape(24.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(22.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(54.dp)
                                    .clip(CircleShape)
                                    .background(MaterialTheme.colorScheme.primaryContainer),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.LocalFlorist,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(32.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(14.dp))
                            Column {
                                Text(
                                    text = analysis.subjectTitle,
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = analysis.category,
                                    fontSize = 17.sp,
                                    color = MaterialTheme.colorScheme.primary,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(14.dp))
                        Text(
                            text = analysis.summary,
                            fontSize = 19.sp,
                            lineHeight = 28.sp,
                            color = MaterialTheme.colorScheme.onSurface
                        )

                        Spacer(modifier = Modifier.height(18.dp))

                        // Medicinal Properties Section
                        KnowledgeDetailBlock(
                            title = "🌿 Medicinal Properties & Health Uses",
                            detail = analysis.medicinalProperties,
                            highlightColor = Color(0xFF14535C)
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        // Practical Uses Section
                        KnowledgeDetailBlock(
                            title = "🍵 Everyday & Household Applications",
                            detail = analysis.practicalUses,
                            highlightColor = Color(0xFFE76F51)
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        // Origin & History Section
                        KnowledgeDetailBlock(
                            title = "📜 Origin & Cultural Heritage",
                            detail = analysis.originAndHistory,
                            highlightColor = Color(0xFF7C3AED)
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        // Intergenerational Conversation Prompt
                        Surface(
                            shape = RoundedCornerShape(16.dp),
                            color = MaterialTheme.colorScheme.primaryContainer,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(
                                        imageVector = Icons.Default.Favorite,
                                        contentDescription = null,
                                        tint = Color(0xFFE76F51),
                                        modifier = Modifier.size(24.dp)
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = "Conversation Spark for You & Leo:",
                                        fontSize = 18.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onPrimaryContainer
                                    )
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = analysis.generationalConversationPrompt,
                                    fontSize = 18.sp,
                                    lineHeight = 26.sp,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(20.dp))

                        // Interactive Trivia Quiz
                        TriviaQuizSection(
                            analysis = analysis,
                            onCorrect = { viewModel.awardChildPoints(20) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun KnowledgeDetailBlock(
    title: String,
    detail: String,
    highlightColor: Color
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = title,
                fontSize = 19.sp,
                fontWeight = FontWeight.Bold,
                color = highlightColor
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = detail,
                fontSize = 18.sp,
                lineHeight = 26.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
fun TriviaQuizSection(
    analysis: PhotoAnalysis,
    onCorrect: () -> Unit
) {
    var selectedAnswerIndex by remember(analysis.id) { mutableIntStateOf(-1) }
    val isCorrect = selectedAnswerIndex == analysis.triviaCorrectIndex

    Card(
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF3C7)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Lightbulb,
                    contentDescription = null,
                    tint = Color(0xFFB45309),
                    modifier = Modifier.size(26.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Generational Learning Quiz",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF78350F)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = analysis.triviaQuestion,
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF92400E)
            )
            Spacer(modifier = Modifier.height(12.dp))

            analysis.triviaOptions.forEachIndexed { i, option ->
                val isSelected = selectedAnswerIndex == i
                Surface(
                    onClick = {
                        selectedAnswerIndex = i
                        if (i == analysis.triviaCorrectIndex) {
                            onCorrect()
                        }
                    },
                    shape = RoundedCornerShape(12.dp),
                    color = when {
                        isSelected && isCorrect -> Color(0xFFDCFCE7)
                        isSelected && !isCorrect -> Color(0xFFFEE2E2)
                        else -> Color.White
                    },
                    border = ButtonDefaults.outlinedButtonBorder.copy(width = 1.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 4.dp)
                        .defaultMinSize(minHeight = 48.dp)
                ) {
                    Text(
                        text = option,
                        fontSize = 18.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                        color = Color.Black,
                        modifier = Modifier.padding(12.dp)
                    )
                }
            }

            if (selectedAnswerIndex != -1) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = if (isCorrect) "🎉 Correct! You and Leo earned +20 trivia points." else "Close! Try thinking about traditional remedies.",
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (isCorrect) Color(0xFF15803D) else Color(0xFFB91C1C)
                )
            }
        }
    }
}
