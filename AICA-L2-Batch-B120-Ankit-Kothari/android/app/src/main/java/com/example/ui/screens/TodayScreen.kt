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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DirectionsWalk
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.EmojiEmotions
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Nightlight
import androidx.compose.material.icons.filled.SelfImprovement
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.components.FortuneCookieComponent
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
import com.example.ui.theme.CosmicSurfaceLight
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextSoft
import com.example.ui.theme.TextWhite
import com.example.viewmodel.SaathiUiState
import com.example.viewmodel.SaathiViewModel

@Composable
fun TodayScreen(
    state: SaathiUiState,
    viewModel: SaathiViewModel,
    modifier: Modifier = Modifier
) {
    var showMoodSelector by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(CosmicDark),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // App / Web Download Quick Banner
        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        Brush.horizontalGradient(
                            listOf(Color(0xFF23174F), Color(0xFF130C2E))
                        )
                    )
                    .border(1.dp, CelestialGold.copy(alpha = 0.35f), RoundedCornerShape(16.dp))
                    .clickable { viewModel.showDownloadAppDialog() }
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .background(CelestialGold.copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.Download, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(18.dp))
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text("Website & App Download Options", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                            Text("Use in browser or download APK package", fontSize = 11.sp, color = TextSoft)
                        }
                    }
                    Text("View", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialGold)
                }
            }
        }

        // Daily Greeting & Level Ring
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
                        Column {
                            Text(
                                text = "Namaste, ${state.profile.name} ✨",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextWhite
                            )
                            Text(
                                text = state.dayCard.dateDisplay,
                                fontSize = 12.sp,
                                color = TextSoft
                            )
                        }

                        // Streak Pill
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(20.dp))
                                .background(Color(0xFFE11D48).copy(alpha = 0.2f))
                                .border(1.dp, Color(0xFFFB7185).copy(alpha = 0.5f), RoundedCornerShape(20.dp))
                                .padding(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.LocalFireDepartment, contentDescription = null, tint = Color(0xFFFB7185), modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "${state.gamification.streakDays} Day Streak",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFFECDD3)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Points Progress
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "Level: ${state.gamification.levelName}",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = CelestialGold
                        )
                        Text(
                            text = "${state.gamification.pointsToday} pts today  |  ${state.gamification.totalPoints} total",
                            fontSize = 12.sp,
                            color = TextSoft
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    LinearProgressIndicator(
                        progress = { ((state.gamification.totalPoints % 1000) / 1000f).coerceIn(0.05f, 1f) },
                        color = CelestialGold,
                        trackColor = CosmicCardElevated,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp))
                    )
                }
            }
        }

        // Daily Fortune Cookie
        item {
            FortuneCookieComponent(
                isCracked = state.dailyActivity.fortuneCracked,
                isGolden = state.dailyActivity.isGoldenCookie,
                fortuneText = state.dailyActivity.fortuneText,
                onCrack = { viewModel.crackFortune() },
                onShare = { viewModel.showShareCard("FORTUNE") }
            )
        }

        // Glow Plan: Daily Habits & Hydration
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        text = "Daily Glow Plan",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextWhite
                    )
                    Text(
                        text = "Complete core wellness habits to power up your daily streak",
                        fontSize = 12.sp,
                        color = TextMuted
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    // 1. Water Tracker
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(CosmicCardElevated)
                            .padding(12.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(CelestialCyan.copy(alpha = 0.2f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.WaterDrop, contentDescription = null, tint = CelestialCyan, modifier = Modifier.size(20.dp))
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("Water Hydration", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("${state.dailyActivity.waterGlasses} of ${state.profile.waterGoalGlasses} glasses (250ml)", fontSize = 11.sp, color = TextSoft)
                            }
                        }

                        Button(
                            onClick = { viewModel.logWater() },
                            colors = ButtonDefaults.buttonColors(containerColor = CelestialCyan, contentColor = CosmicDark),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("+1 Glass", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // 2. Steps Tracker
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(CosmicCardElevated)
                            .padding(12.dp)
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
                                Text("Daily Movement", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("${state.dailyActivity.stepsWalked} / ${state.profile.stepGoal} steps", fontSize = 11.sp, color = TextSoft)
                            }
                        }

                        Button(
                            onClick = { viewModel.logSteps(500) },
                            colors = ButtonDefaults.buttonColors(containerColor = CelestialMint, contentColor = CosmicDark),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("+500", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // 3. Skincare Habits (AM & PM)
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(12.dp))
                                .background(CosmicCardElevated)
                                .clickable { viewModel.toggleAmSkincare() }
                                .padding(12.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(
                                    checked = state.dailyActivity.amSkincareDone,
                                    onCheckedChange = { viewModel.toggleAmSkincare() },
                                    colors = CheckboxDefaults.colors(checkedColor = CelestialRose)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Column {
                                    Text("AM Glow", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                    Text("+5 pts", fontSize = 10.sp, color = CelestialRose)
                                }
                            }
                        }

                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(12.dp))
                                .background(CosmicCardElevated)
                                .clickable { viewModel.togglePmSkincare() }
                                .padding(12.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(
                                    checked = state.dailyActivity.pmSkincareDone,
                                    onCheckedChange = { viewModel.togglePmSkincare() },
                                    colors = CheckboxDefaults.colors(checkedColor = CelestialLavender)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Column {
                                    Text("PM Glow", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                    Text("+5 pts", fontSize = 10.sp, color = CelestialLavender)
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // 4. Mood Check-in
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(CosmicCardElevated)
                            .padding(12.dp)
                    ) {
                        Column {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    text = if (state.dailyActivity.mood.isNotEmpty()) "Today's Mood: ${state.dailyActivity.mood}" else "Daily Mood Check-in",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextWhite
                                )
                                Text(
                                    text = if (state.dailyActivity.mood.isNotEmpty()) "Logged (+5 pts)" else "Tap to log",
                                    fontSize = 11.sp,
                                    color = CelestialGold
                                )
                            }
                            Spacer(modifier = Modifier.height(8.dp))
                            Row(
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                listOf("Radiant \uD83D\uDE04", "Calm \uD83D\uDE0C", "Grounded \uD83E\uDDD8", "Tired \uD83D\uDE34", "Low \uD83C\uDF27\uFE0F").forEach { moodItem ->
                                    val moodName = moodItem.split(" ").first()
                                    val isSelected = state.dailyActivity.mood == moodName
                                    Box(
                                        modifier = Modifier
                                            .clip(RoundedCornerShape(8.dp))
                                            .background(if (isSelected) CelestialGold.copy(alpha = 0.3f) else CosmicDark)
                                            .border(1.dp, if (isSelected) CelestialGold else CosmicBorder, RoundedCornerShape(8.dp))
                                            .clickable { viewModel.logMood(moodName) }
                                            .padding(horizontal = 8.dp, vertical = 6.dp)
                                    ) {
                                        Text(moodItem, fontSize = 11.sp, color = if (isSelected) CelestialGoldLight else TextSoft)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Quick Movement Breaks
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        text = "Mindful Movement & Screen Breaks",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextWhite
                    )
                    Text(
                        text = "Guided 20 to 45-second micro-routines to relieve strain",
                        fontSize = 12.sp,
                        color = TextMuted
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        // Eye Refresh
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(CosmicCardElevated)
                                .clickable { viewModel.openRoutine("EYE") }
                                .padding(12.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Icon(Icons.Default.Visibility, contentDescription = null, tint = CelestialCyan, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("Eye Refresh", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("20s | +5 pts", fontSize = 10.sp, color = CelestialCyan)
                            }
                        }

                        // Neck Relief
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(CosmicCardElevated)
                                .clickable { viewModel.openRoutine("NECK") }
                                .padding(12.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Icon(Icons.Default.SelfImprovement, contentDescription = null, tint = CelestialRose, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("Neck Relief", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("30s | +10 pts", fontSize = 10.sp, color = CelestialRose)
                            }
                        }

                        // Desk Stretch
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(CosmicCardElevated)
                                .clickable { viewModel.openRoutine("DESK") }
                                .padding(12.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = CelestialMint, modifier = Modifier.size(24.dp))
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("Desk Zen", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Text("30s | +10 pts", fontSize = 10.sp, color = CelestialMint)
                            }
                        }
                    }
                }
            }
        }

        // Today's Stars Quick Card
        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(20.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(Color(0xFF1B143F), Color(0xFF120C2D))
                        )
                    )
                    .border(1.dp, CelestialLavender.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
                    .clickable { viewModel.selectTab(com.example.viewmodel.SaathiTab.STARS) }
                    .padding(18.dp)
            ) {
                Column {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Nightlight, contentDescription = null, tint = CelestialLavender, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Today's Cosmic Sky", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                        }
                        Text("Deep Card →", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialLavender)
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Text(
                        text = "Moon in ${state.dayCard.moonSignVedic}  •  ${state.dayCard.nakshatra}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = CelestialGoldLight
                    )

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = "Rahu Kaal: ${state.dayCard.rahuKaal}  |  Lucky Color: ${state.dayCard.luckyColor}  |  Number: ${state.dayCard.luckyNumber}",
                        fontSize = 11.sp,
                        color = TextSoft
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Text(
                        text = "“${state.dayCard.proTip}”",
                        fontSize = 12.sp,
                        color = TextSoft,
                        lineHeight = 17.sp
                    )
                }
            }
        }
    }
}
