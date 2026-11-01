package com.example.ui.screens.senior

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.MedStatus
import com.example.data.model.SeniorMilestone
import com.example.data.model.SeniorMilestoneCategory
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.ReadAloudButton

@Composable
fun SeniorMilestonesScreen(
    viewModel: GenerationsAppViewModel,
    onNavigateTab: (Int) -> Unit = {}
) {
    val milestones by viewModel.seniorMilestones.collectAsState()
    val medications by viewModel.medications.collectAsState()
    val diaryEntries by viewModel.diaryEntries.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()

    var selectedCategory by remember { mutableStateOf(SeniorMilestoneCategory.ALL) }
    var selectedMilestoneForDialog by remember { mutableStateOf<SeniorMilestone?>(null) }

    val unlockedCount = milestones.count { it.isUnlocked }
    val totalCount = milestones.size
    val completionPercent = if (totalCount > 0) ((unlockedCount.toFloat() / totalCount) * 100).toInt() else 0

    val takenMeds = medications.count { it.status == MedStatus.TAKEN }
    val totalMeds = medications.size
    val diaryDoneToday = diaryEntries.isNotEmpty()
    val breathingMilestone = milestones.find { it.id == "sm_breath_first" }
    val breathingDoneToday = breathingMilestone?.isUnlocked == true

    val dailyEncouragementSummary = "Welcome to your Milestones, Eleanor! You have celebrated $unlockedCount of $totalCount wellness badges. Your steady care taking your medicines, sharing wisdom, and breathing deeply brings great health to you and joy to your buddy Leo."

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_milestones_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Daily Gentle Encouragement Hero Card
        item {
            Card(
                shape = RoundedCornerShape(26.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("hero_encouragement_card")
            ) {
                Column(modifier = Modifier.padding(22.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(52.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFFFEF3C7)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(text = "🏆", fontSize = 28.sp)
                            }
                            Spacer(modifier = Modifier.width(14.dp))
                            Column {
                                Text(
                                    text = "Senior Milestones",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                                Text(
                                    text = "Celebrating your daily wellness & care",
                                    fontSize = 16.sp,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.85f)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    Text(
                        text = "“Consistency is a quiet form of self-love. Eleanor, your steady rhythm of taking your medicines, writing your memories, and breathing with calm intention inspires everyone in your family.”",
                        fontSize = 18.sp,
                        lineHeight = 26.sp,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    // Progress bar and badges count
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "$unlockedCount of $totalCount Badges Celebrated",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color(0xFFFEF3C7)
                        ) {
                            Text(
                                text = "7-Day Streak ✨",
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF78350F),
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    LinearProgressIndicator(
                        progress = { unlockedCount.toFloat() / totalCount },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(14.dp)
                            .clip(RoundedCornerShape(7.dp)),
                        color = MaterialTheme.colorScheme.primary,
                        trackColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.4f)
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    ReadAloudButton(
                        textToSpeak = dailyEncouragementSummary,
                        isSpeaking = isSpeaking,
                        onSpeak = { viewModel.speakAloud(dailyEncouragementSummary) },
                        onStop = { viewModel.stopSpeaking() },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        // Today's Core Positive Reinforcement Trio (Medication, Diary, Breathing)
        item {
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        text = "Today's Wellness Habits",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = "Complete all three to nurture body, mind, and calm",
                        fontSize = 16.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    // Habit 1: Medication
                    HabitCheckRow(
                        title = "Daily Medicines",
                        subtitle = "$takenMeds of $totalMeds doses taken today",
                        isCompleted = takenMeds >= totalMeds && totalMeds > 0,
                        iconEmoji = "💊",
                        buttonText = if (takenMeds >= totalMeds) "All Taken" else "Review",
                        onButtonClick = { onNavigateTab(1) }
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    // Habit 2: Diary
                    HabitCheckRow(
                        title = "Diary Reflection",
                        subtitle = if (diaryDoneToday) "Today's entry saved with Leo" else "Express a thought or gratitude",
                        isCompleted = diaryDoneToday,
                        iconEmoji = "📖",
                        buttonText = if (diaryDoneToday) "Recorded" else "Write Entry",
                        onButtonClick = { onNavigateTab(2) }
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    // Habit 3: Calm Breathing
                    HabitCheckRow(
                        title = "1-Min Calm Breathing",
                        subtitle = if (breathingDoneToday) "Relaxation exercise completed" else "One quiet minute to center yourself",
                        isCompleted = breathingDoneToday,
                        iconEmoji = "🧘",
                        buttonText = if (breathingDoneToday) "Refreshed" else "Start Breath",
                        onButtonClick = { onNavigateTab(7) }
                    )
                }
            }
        }

        // Intergenerational Encouragement Note from Buddy
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF3E8FF)),
                border = BorderStroke(1.dp, Color(0xFFD8B4FE)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(18.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(50.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF7C3AED)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.ChildCare,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(30.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Cheer from Leo (Age 8) 💝",
                            fontSize = 19.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF581C87)
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "“Grandma Eleanor, every time you earn a wellness badge, my adventure star lights up too! I'm so proud of you!”",
                            fontSize = 16.sp,
                            lineHeight = 22.sp,
                            color = Color(0xFF6B21A8)
                        )
                    }
                }
            }
        }

        // Category Filter Chips
        item {
            Column {
                Text(
                    text = "Milestone Badges",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Spacer(modifier = Modifier.height(8.dp))
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(vertical = 4.dp)
                ) {
                    item {
                        FilterChip(
                            selected = selectedCategory == SeniorMilestoneCategory.ALL,
                            onClick = { selectedCategory = SeniorMilestoneCategory.ALL },
                            label = { Text("All (${milestones.size})", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primary,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                            ),
                            modifier = Modifier.testTag("filter_all")
                        )
                    }
                    item {
                        FilterChip(
                            selected = selectedCategory == SeniorMilestoneCategory.MEDICATIONS,
                            onClick = { selectedCategory = SeniorMilestoneCategory.MEDICATIONS },
                            label = { Text("💊 Medications", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primary,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                            ),
                            modifier = Modifier.testTag("filter_medications")
                        )
                    }
                    item {
                        FilterChip(
                            selected = selectedCategory == SeniorMilestoneCategory.DIARY,
                            onClick = { selectedCategory = SeniorMilestoneCategory.DIARY },
                            label = { Text("📖 Diary & Wisdom", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primary,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                            ),
                            modifier = Modifier.testTag("filter_diary")
                        )
                    }
                    item {
                        FilterChip(
                            selected = selectedCategory == SeniorMilestoneCategory.BREATHING,
                            onClick = { selectedCategory = SeniorMilestoneCategory.BREATHING },
                            label = { Text("🧘 Calm Breathing", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primary,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                            ),
                            modifier = Modifier.testTag("filter_breathing")
                        )
                    }
                    item {
                        FilterChip(
                            selected = selectedCategory == SeniorMilestoneCategory.WELLNESS,
                            onClick = { selectedCategory = SeniorMilestoneCategory.WELLNESS },
                            label = { Text("🌺 Daily Rhythm", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primary,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                            ),
                            modifier = Modifier.testTag("filter_wellness")
                        )
                    }
                }
            }
        }

        // Filtered Milestones List
        val filteredMilestones = milestones.filter {
            selectedCategory == SeniorMilestoneCategory.ALL || it.category == selectedCategory
        }

        items(filteredMilestones) { milestone ->
            SeniorMilestoneCard(
                milestone = milestone,
                onClick = {
                    selectedMilestoneForDialog = milestone
                    viewModel.celebrateMilestone(milestone)
                }
            )
        }
    }

    // Modal celebration / details dialog
    selectedMilestoneForDialog?.let { milestone ->
        MilestoneCelebrationDialog(
            milestone = milestone,
            isSpeaking = isSpeaking,
            onSpeak = { viewModel.speakAloud("${milestone.title}. ${milestone.gentleAffirmation}") },
            onStop = { viewModel.stopSpeaking() },
            onDismiss = { selectedMilestoneForDialog = null }
        )
    }
}

@Composable
private fun HabitCheckRow(
    title: String,
    subtitle: String,
    isCompleted: Boolean,
    iconEmoji: String,
    buttonText: String,
    onButtonClick: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = if (isCompleted) Color(0xFFDCFCE7) else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
        border = BorderStroke(1.dp, if (isCompleted) Color(0xFF86EFAC) else Color.Transparent),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(14.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Box(
                    modifier = Modifier
                        .size(44.dp)
                        .clip(CircleShape)
                        .background(if (isCompleted) Color(0xFF16A34A) else MaterialTheme.colorScheme.surface),
                    contentAlignment = Alignment.Center
                ) {
                    if (isCompleted) {
                        Icon(
                            imageVector = Icons.Default.Check,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(26.dp)
                        )
                    } else {
                        Text(text = iconEmoji, fontSize = 22.sp)
                    }
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = title,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (isCompleted) Color(0xFF14532D) else MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = subtitle,
                        fontSize = 15.sp,
                        color = if (isCompleted) Color(0xFF166534) else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Button(
                onClick = onButtonClick,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isCompleted) Color(0xFF15803D) else MaterialTheme.colorScheme.primary
                ),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp)
            ) {
                Text(
                    text = buttonText,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
fun SeniorMilestoneCard(
    milestone: SeniorMilestone,
    onClick: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (milestone.isUnlocked) Color(0xFFFFFBEB) else MaterialTheme.colorScheme.surface
        ),
        border = BorderStroke(
            1.5.dp,
            if (milestone.isUnlocked) Color(0xFFFDE68A) else MaterialTheme.colorScheme.outlineVariant
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = if (milestone.isUnlocked) 3.dp else 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .testTag("badge_card_${milestone.id}")
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Box(
                        modifier = Modifier
                            .size(54.dp)
                            .clip(CircleShape)
                            .background(
                                if (milestone.isUnlocked) Color(0xFFFEF3C7) else MaterialTheme.colorScheme.surfaceVariant
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = if (milestone.isUnlocked) milestone.iconEmoji else "🔒",
                            fontSize = 28.sp
                        )
                    }

                    Spacer(modifier = Modifier.width(14.dp))

                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = milestone.title,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (milestone.isUnlocked) Color(0xFF78350F) else MaterialTheme.colorScheme.onSurface
                            )
                            if (milestone.isUnlocked) {
                                Spacer(modifier = Modifier.width(6.dp))
                                Icon(
                                    imageVector = Icons.Default.CheckCircle,
                                    contentDescription = "Unlocked",
                                    tint = Color(0xFFD97706),
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }

                        Text(
                            text = milestone.description,
                            fontSize = 16.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = if (milestone.isUnlocked) Color(0xFFFEF3C7) else MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Text(
                        text = if (milestone.isUnlocked) "Celebrated" else "${milestone.currentProgress}/${milestone.targetProgress}",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (milestone.isUnlocked) Color(0xFFB45309) else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Gentle encouragement note
            Text(
                text = "“${milestone.gentleAffirmation}”",
                fontSize = 15.sp,
                lineHeight = 22.sp,
                color = if (milestone.isUnlocked) Color(0xFF92400E) else MaterialTheme.colorScheme.onSurfaceVariant
            )

            if (!milestone.isUnlocked) {
                Spacer(modifier = Modifier.height(10.dp))
                LinearProgressIndicator(
                    progress = { milestone.currentProgress.toFloat() / milestone.targetProgress },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                        .clip(RoundedCornerShape(4.dp)),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.surfaceVariant
                )
            } else if (milestone.unlockedDate != null) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Achieved: ${milestone.unlockedDate}",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color(0xFFB45309)
                )
            }
        }
    }
}

@Composable
fun MilestoneCelebrationDialog(
    milestone: SeniorMilestone,
    isSpeaking: Boolean,
    onSpeak: () -> Unit,
    onStop: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(text = milestone.iconEmoji, fontSize = 32.sp)
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = milestone.title,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                IconButton(onClick = onDismiss) {
                    Icon(imageVector = Icons.Default.Close, contentDescription = "Close")
                }
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = if (milestone.isUnlocked) Color(0xFFFEF3C7) else MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = if (milestone.isUnlocked) "Milestone Celebrated! 🌟" else "Milestone In Progress",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (milestone.isUnlocked) Color(0xFF78350F) else MaterialTheme.colorScheme.onSurface
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = milestone.description,
                            fontSize = 16.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Text(
                    text = "Gentle Encouragement:",
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )

                Text(
                    text = "“${milestone.gentleAffirmation}”",
                    fontSize = 18.sp,
                    lineHeight = 26.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )

                if (milestone.unlockedDate != null) {
                    Text(
                        text = "Recorded on ${milestone.unlockedDate}",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (isSpeaking) onStop() else onSpeak()
                },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.defaultMinSize(minHeight = 52.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (isSpeaking) "Stop Voice" else "Read Aloud",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onDismiss,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.defaultMinSize(minHeight = 52.dp)
            ) {
                Text(text = "Close", fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        },
        shape = RoundedCornerShape(26.dp),
        containerColor = MaterialTheme.colorScheme.surface
    )
}
