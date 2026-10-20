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
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
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
import com.example.engine.PointsEngine
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
import kotlin.math.roundToInt

@Composable
fun MeScreen(
    state: SaathiUiState,
    viewModel: SaathiViewModel,
    modifier: Modifier = Modifier
) {
    var showPersonalityDialog by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(CosmicDark),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // User Profile & Level Header
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CelestialGold.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(54.dp)
                                    .clip(CircleShape)
                                    .background(CelestialGold.copy(alpha = 0.2f))
                                    .border(1.5.dp, CelestialGold, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = state.profile.name.take(1).uppercase(),
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = CelestialGoldLight
                                )
                            }
                            Spacer(modifier = Modifier.width(14.dp))
                            Column {
                                Text(
                                    text = state.profile.name,
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextWhite
                                )
                                Text(
                                    text = "${state.profile.city}  •  Level: ${state.gamification.levelName}",
                                    fontSize = 12.sp,
                                    color = CelestialGold
                                )
                            }
                        }

                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(12.dp))
                                .background(CosmicCardElevated)
                                .padding(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text = "${state.gamification.totalPoints} pts",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextWhite
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        ProfileMetric("Streak", "${state.gamification.streakDays} Days", CelestialAmber, Modifier.weight(1f))
                        ProfileMetric("Freezes", "${state.gamification.freezesAvailable} Saved", CelestialCyan, Modifier.weight(1f))
                        ProfileMetric("Badges", "${state.gamification.unlockedBadgeIds.size}/16", CelestialMint, Modifier.weight(1f))
                    }
                }
            }
        }

        // Website & App Download Action Card
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CelestialGold.copy(alpha = 0.5f), RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Download, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(24.dp))
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("Download App & Website Options", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("Online web companion & APK installation instructions", fontSize = 11.sp, color = TextSoft)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                        Button(
                            onClick = { viewModel.showDownloadAppDialog() },
                            colors = ButtonDefaults.buttonColors(containerColor = CelestialGold, contentColor = CosmicDark),
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Download APK Guide", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }

                        OutlinedButton(
                            onClick = { viewModel.showDownloadAppDialog() },
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = CelestialCyan),
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Language, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Web App Link", fontSize = 12.sp)
                        }
                    }
                }
            }
        }

        // Big Five Personality Test (IPIP-50)
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CelestialLavender.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Psychology, contentDescription = null, tint = CelestialLavender, modifier = Modifier.size(24.dp))
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("Big Five Personality (IPIP)", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("Validated trait assessment & strengths", fontSize = 11.sp, color = TextSoft)
                            }
                        }

                        Button(
                            onClick = { showPersonalityDialog = true },
                            colors = ButtonDefaults.buttonColors(containerColor = CelestialLavender, contentColor = CosmicDark),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Text("Take Quiz", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Trait Visualizer
                    PersonalityTraitBar("Openness to Experience", 78, CelestialCyan)
                    PersonalityTraitBar("Conscientiousness", 84, CelestialMint)
                    PersonalityTraitBar("Extraversion", 62, CelestialAmber)
                    PersonalityTraitBar("Agreeableness", 88, CelestialRose)
                    PersonalityTraitBar("Emotional Stability", 74, CelestialLavender)
                }
            }
        }

        // 16 Badges Gallery
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
                        Text("16 Milestone Badges", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                        Text("${state.gamification.unlockedBadgeIds.size} of 16 Unlocked", fontSize = 11.sp, color = CelestialGold)
                    }
                    Text("Earn badges through hydration, steps, routines, and star charts", fontSize = 11.sp, color = TextMuted)

                    Spacer(modifier = Modifier.height(14.dp))

                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        PointsEngine.allBadges.chunked(2).forEach { pair ->
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                pair.forEach { badge ->
                                    val isUnlocked = state.gamification.unlockedBadgeIds.contains(badge.id)
                                    BadgeCard(badge.title, badge.description, isUnlocked, Modifier.weight(1f))
                                }
                                if (pair.size == 1) {
                                    Spacer(modifier = Modifier.weight(1f))
                                }
                            }
                        }
                    }
                }
            }
        }

        // Privacy & Disclaimers
        item {
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCardElevated),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Security, contentDescription = null, tint = CelestialMint, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Privacy by Design", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "All personal metrics, birth dates, weights, and glow check-ins are stored locally on your device. Saathi is built as a healthy daily wellness, beauty, and entertainment companion (18+). No medical diagnosis provided.",
                        fontSize = 11.sp,
                        color = TextSoft,
                        lineHeight = 15.sp
                    )
                }
            }
        }
    }

    if (showPersonalityDialog) {
        PersonalityQuizDialog(
            onDismiss = { showPersonalityDialog = false }
        )
    }
}

@Composable
private fun ProfileMetric(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(CosmicCardElevated)
            .padding(10.dp)
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Text(value, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = color)
            Text(label, fontSize = 10.sp, color = TextMuted)
        }
    }
}

@Composable
private fun PersonalityTraitBar(name: String, score: Int, color: Color) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text(name, fontSize = 11.sp, color = TextWhite)
            Text("$score%", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = color)
        }
        Spacer(modifier = Modifier.height(3.dp))
        LinearProgressIndicator(
            progress = { score / 100f },
            color = color,
            trackColor = CosmicCardElevated,
            modifier = Modifier
                .fillMaxWidth()
                .height(5.dp)
                .clip(RoundedCornerShape(3.dp))
        )
    }
}

@Composable
private fun BadgeCard(title: String, desc: String, isUnlocked: Boolean, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(if (isUnlocked) CosmicCardElevated else CosmicDark.copy(alpha = 0.5f))
            .border(1.dp, if (isUnlocked) CelestialGold.copy(alpha = 0.4f) else CosmicBorder, RoundedCornerShape(12.dp))
            .padding(10.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = if (isUnlocked) Icons.Default.EmojiEvents else Icons.Default.Lock,
                contentDescription = null,
                tint = if (isUnlocked) CelestialGold else TextMuted,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Column {
                Text(
                    text = title,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (isUnlocked) TextWhite else TextMuted
                )
                Text(
                    text = desc,
                    fontSize = 9.sp,
                    color = TextMuted,
                    lineHeight = 12.sp
                )
            }
        }
    }
}

@Composable
fun PersonalityQuizDialog(onDismiss: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = CosmicCard),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, CelestialLavender.copy(alpha = 0.5f), RoundedCornerShape(20.dp))
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text("Big Five Personality Quiz (IPIP)", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                Text(
                    text = "Your answers highlight your natural psychological strengths and communication style.",
                    fontSize = 12.sp,
                    color = TextSoft,
                    lineHeight = 16.sp
                )

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(CosmicCardElevated)
                        .padding(12.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("✨ Dominant Trait: High Agreeableness & Openness", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialGoldLight)
                        Text("• Strengths: Deep empathy, artistic appreciation, active listener", fontSize = 11.sp, color = TextSoft)
                        Text("• Growth Tip: Guard your peace against emotional fatigue by setting clear boundary windows.", fontSize = 11.sp, color = CelestialLavender)
                    }
                }

                Button(
                    onClick = onDismiss,
                    colors = ButtonDefaults.buttonColors(containerColor = CelestialLavender, contentColor = CosmicDark),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Close Results", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
