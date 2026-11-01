package com.example.ui.screens.senior

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
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.Book
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.ChatBubble
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Games
import androidx.compose.material.icons.filled.Medication
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Nightlight
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import com.example.ui.components.MandalaDecor


import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Security
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.MedStatus
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.MedicineProgressRing
import com.example.ui.components.ReadAloudButton

@Composable
fun SeniorHomeScreen(
    viewModel: GenerationsAppViewModel,
    onNavigateTab: (Int) -> Unit,
    onLogOff: () -> Unit = {}
) {
    val medications by viewModel.medications.collectAsState()
    val seniorMilestones by viewModel.seniorMilestones.collectAsState()
    val preferences by viewModel.seniorPreferences.collectAsState()
    val isSpeaking by viewModel.isSpeaking.collectAsState()
    var hasAutoSpoken by remember { mutableStateOf(false) }

    val takenMeds = medications.count { it.status == MedStatus.TAKEN }
    val totalMeds = medications.size
    val overdueMeds = medications.filter { it.status == MedStatus.OVERDUE }
    val unlockedBadges = seniorMilestones.count { it.isUnlocked }

    val welcomeSummary = "Good afternoon, Eleanor! You have taken $takenMeds of $totalMeds medicines today and celebrated $unlockedBadges wellness milestones. Your buddy Leo sent a sweet story idea about the time-traveling bicycle. All options are stacked in rows of 3 below."

    androidx.compose.runtime.LaunchedEffect(preferences.voiceModeEnabled) {
        if (preferences.voiceModeEnabled && !hasAutoSpoken) {
            hasAutoSpoken = true
            viewModel.speakAloud("Good afternoon, Eleanor! Voice mode is active. Tap any of the 3-in-a-row shortcuts below.")
        }
    }


    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_home_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Greeting & Read Aloud banner
        item {
            Card(
                shape = RoundedCornerShape(26.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = BorderStroke(2.5.dp, MaterialTheme.colorScheme.outline),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(modifier = Modifier.fillMaxWidth()) {
                    MandalaDecor(
                        size = 110.dp,
                        tint = Color(0xFFD4AF37),
                        alpha = 0.22f,
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(top = 4.dp, end = 4.dp)
                    )

                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "Good Afternoon, Eleanor! 🌸",
                                    fontSize = 26.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF18261D)
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Connected with Leo (Age 8) • Willow Creek",
                                    fontSize = 17.sp,
                                    color = Color(0xFF425447)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(14.dp))

                        ReadAloudButton(
                            textToSpeak = welcomeSummary,
                            onSpeak = { viewModel.speakAloud(it) },
                            onStop = { viewModel.stopSpeaking() },
                            isSpeaking = isSpeaking,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }
        }

        // Overdue warning if any
        if (overdueMeds.isNotEmpty()) {
            item {
                Card(
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF3C7)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = "Attention",
                            tint = Color(0xFFB45309),
                            modifier = Modifier.size(36.dp)
                        )
                        Spacer(modifier = Modifier.width(14.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Reminder: Afternoon Dose",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF78350F)
                            )
                            Text(
                                text = "${overdueMeds.first().name} (${overdueMeds.first().scheduledTime}) is ready to take.",
                                fontSize = 18.sp,
                                color = Color(0xFF92400E)
                            )
                        }
                    }
                }
            }
        }

        // Medicine Progress Ring
        item {
            MedicineProgressRing(
                takenCount = takenMeds,
                totalCount = totalMeds
            )
        }

        // Big Shortcut Tiles Header
        item {
            Text(
                text = "Quick Shortcuts",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.padding(top = 8.dp)
            )
        }

        // Big Shortcut Tiles Grid - 3 in a Row, Stacked with Thick Borders (Urban Clap / ISKCON Inspired)
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                // Row 1 (3 in a row)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    ShortcutTile(
                        title = "Medicines",
                        subtitle = "$takenMeds of $totalMeds taken",
                        icon = Icons.Default.Medication,
                        iconColor = Color(0xFF4A6B53),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(1) }
                    )
                    ShortcutTile(
                        title = "Milestones",
                        subtitle = "$unlockedBadges Badges",
                        icon = Icons.Default.EmojiEvents,
                        iconColor = Color(0xFFC29B38),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(8) }
                    )
                    ShortcutTile(
                        title = "Diary",
                        subtitle = "Daily memoirs",
                        icon = Icons.Default.Book,
                        iconColor = Color(0xFFC86446),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(2) }
                    )
                }

                // Row 2 (3 in a row)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    ShortcutTile(
                        title = "Breathe",
                        subtitle = "1-min calm",
                        icon = Icons.Default.SelfImprovement,
                        iconColor = Color(0xFF2A9D8F),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(7) }
                    )
                    ShortcutTile(
                        title = "Sleep Log",
                        subtitle = "Rest health",
                        icon = Icons.Default.Nightlight,
                        iconColor = Color(0xFF457B9D),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(3) }
                    )
                    ShortcutTile(
                        title = "Stories",
                        subtitle = "With Leo",
                        icon = Icons.Default.AutoStories,
                        iconColor = Color(0xFF8B5CF6),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(4) }
                    )
                }

                // Row 3 (3 in a row)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    ShortcutTile(
                        title = "Games",
                        subtitle = "Memory play",
                        icon = Icons.Default.Games,
                        iconColor = Color(0xFF10B981),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(5) }
                    )
                    ShortcutTile(
                        title = "Photo Studio",
                        subtitle = "Plant origins",
                        icon = Icons.Default.CameraAlt,
                        iconColor = Color(0xFFD97706),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(6) }
                    )
                    ShortcutTile(
                        title = "Music Hub",
                        subtitle = "Sitar & Tabla",
                        icon = Icons.Default.MusicNote,
                        iconColor = Color(0xFFD4AF37),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(9) }
                    )
                }

                // Row 4 (3 in a row - continuing below)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    ShortcutTile(
                        title = "Security",
                        subtitle = "Face & Pattern",
                        icon = Icons.Default.Lock,
                        iconColor = Color(0xFF4A6B53),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(10) }
                    )
                    ShortcutTile(
                        title = "Safety Hub",
                        subtitle = "Guardian status",
                        icon = Icons.Default.Security,
                        iconColor = Color(0xFF1E40AF),
                        modifier = Modifier.weight(1f),
                        onClick = { onNavigateTab(11) }
                    )
                    ShortcutTile(
                        title = "Log Off",
                        subtitle = "Switch account",
                        icon = Icons.Default.ExitToApp,
                        iconColor = Color(0xFFC86446),
                        modifier = Modifier.weight(1f),
                        onClick = onLogOff
                    )
                }
            }
        }

        // Senior Milestones Positive Reinforcement Card
        item {
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFBEB)),
                border = BorderStroke(1.5.dp, Color(0xFFFDE68A)),
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onNavigateTab(8) }
                    .testTag("home_milestones_card")
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
                                    .size(46.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFFFEF3C7)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(text = "🌟", fontSize = 24.sp)
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = "Senior Milestones & Encouragement",
                                    fontSize = 19.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF78350F)
                                )
                                Text(
                                    text = "$unlockedBadges of ${seniorMilestones.size} Badges • 7-Day Consistency",
                                    fontSize = 15.sp,
                                    color = Color(0xFFB45309)
                                )
                            }
                        }
                        Text(
                            text = "View ❯",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFD97706)
                        )
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "“Consistency is a quiet form of self-love. Eleanor, your steady rhythm of taking your medicines, writing your memories, and breathing calmly inspires Leo every day.”",
                        fontSize = 16.sp,
                        lineHeight = 22.sp,
                        color = Color(0xFF92400E)
                    )
                }
            }
        }


        // Intergenerational Connection Spotlight
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(44.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.secondary),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.ChildCare,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(28.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "Message from Leo",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "10 minutes ago",
                                fontSize = 16.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "“Grandma Eleanor! I unlocked the next turn of our Flying Bicycle story. What should happen when we reach 1965? Look in the Stories tab!”",
                        fontSize = 19.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

@Composable
private fun ShortcutTile(
    title: String,
    subtitle: String,
    icon: ImageVector,
    iconColor: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(2.5.dp, MaterialTheme.colorScheme.outline),
        shadowElevation = 2.dp,
        modifier = modifier.defaultMinSize(minHeight = 118.dp)
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.SpaceBetween,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(46.dp)
                    .clip(CircleShape)
                    .background(iconColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = iconColor,
                    modifier = Modifier.size(28.dp)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = title,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )
            Text(
                text = subtitle,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )
        }
    }
}

