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
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Create
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.DoNotDisturb
import androidx.compose.material.icons.filled.Draw
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.GridOn
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Nightlight
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
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

@Composable
fun StarsScreen(
    state: SaathiUiState,
    viewModel: SaathiViewModel,
    modifier: Modifier = Modifier
) {
    var selectedSubTab by remember { mutableIntStateOf(0) } // 0: Sky & Card, 1: Numbers, 2: Signature, 3: Blueprint
    var showEditBirthDialog by remember { mutableStateOf(false) }

    val subTabs = listOf("Sky & Card", "Numbers", "Signature Studio", "Blueprint")

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(CosmicDark)
    ) {
        // Sub-tabs Row
        ScrollableTabRow(
            selectedTabIndex = selectedSubTab,
            containerColor = CosmicCard,
            contentColor = CelestialGold,
            edgePadding = 16.dp,
            indicator = { tabPositions ->
                TabRowDefaults.SecondaryIndicator(
                    Modifier.tabIndicatorOffset(tabPositions[selectedSubTab]),
                    color = CelestialGold,
                    height = 3.dp
                )
            }
        ) {
            subTabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedSubTab == index,
                    onClick = { selectedSubTab = index },
                    text = {
                        Text(
                            text = title,
                            fontWeight = if (selectedSubTab == index) FontWeight.Bold else FontWeight.Normal,
                            fontSize = 13.sp,
                            color = if (selectedSubTab == index) CelestialGold else TextSoft
                        )
                    }
                )
            }
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            when (selectedSubTab) {
                0 -> {
                    // SUBTAB 0: SKY & DEEP ASTRO DAY CARD
                    item {
                        // System Toggle & Birth Details Header
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(CosmicCard)
                                    .border(1.dp, CosmicBorder, RoundedCornerShape(12.dp))
                                    .padding(4.dp)
                            ) {
                                listOf("Vedic", "Western").forEach { sys ->
                                    val isSelected = state.profile.preferredSystem == sys
                                    Box(
                                        modifier = Modifier
                                            .clip(RoundedCornerShape(8.dp))
                                            .background(if (isSelected) CelestialGold else Color.Transparent)
                                            .clickable { viewModel.setAstrologySystem(sys) }
                                            .padding(horizontal = 12.dp, vertical = 6.dp)
                                    ) {
                                        Text(
                                            text = sys,
                                            fontSize = 12.sp,
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                            color = if (isSelected) CosmicDark else TextSoft
                                        )
                                    }
                                }
                            }

                            OutlinedButton(
                                onClick = { showEditBirthDialog = true },
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = CelestialLavender)
                            ) {
                                Icon(Icons.Default.Create, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Birth Chart Details", fontSize = 11.sp)
                            }
                        }
                    }

                    // Deep Astro Day Card
                    item {
                        Card(
                            shape = RoundedCornerShape(24.dp),
                            colors = CardDefaults.cardColors(containerColor = CosmicCard),
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, CelestialLavender.copy(alpha = 0.5f), RoundedCornerShape(24.dp))
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                // Card Top: Day Score & Moon Transit
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Column {
                                        Text(
                                            text = if (state.profile.preferredSystem == "Vedic")
                                                "Moon in ${state.dayCard.moonSignVedic} (Sidereal)"
                                            else
                                                "Moon in ${state.dayCard.moonSign} (Tropical)",
                                            fontSize = 17.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = TextWhite
                                        )
                                        Text(
                                            text = "${state.dayCard.nakshatra}  •  ${state.dayCard.tithi}",
                                            fontSize = 12.sp,
                                            color = CelestialGoldLight
                                        )
                                    }

                                    // Day Score Circle
                                    Box(
                                        modifier = Modifier
                                            .size(46.dp)
                                            .clip(CircleShape)
                                            .background(CelestialGold.copy(alpha = 0.2f))
                                            .border(1.5.dp, CelestialGold, CircleShape),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                            Text("${state.dayCard.dayScore}/10", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialGoldLight)
                                            Text("Harmony", fontSize = 8.sp, color = TextSoft)
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(18.dp))

                                // Planetary Auspicious Timings
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(14.dp))
                                            .background(CosmicCardElevated)
                                            .padding(12.dp)
                                    ) {
                                        Column {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(Icons.Default.WbSunny, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(16.dp))
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Text("Abhijit Muhurta", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = CelestialGold)
                                            }
                                            Spacer(modifier = Modifier.height(4.dp))
                                            Text(state.dayCard.abhijitMuhurta, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextWhite)
                                            Text("Golden action window", fontSize = 10.sp, color = TextMuted)
                                        }
                                    }

                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(14.dp))
                                            .background(CosmicCardElevated)
                                            .padding(12.dp)
                                    ) {
                                        Column {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(Icons.Default.Nightlight, contentDescription = null, tint = Color(0xFFFB7185), modifier = Modifier.size(16.dp))
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Text("Rahu Kaal", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFFFB7185))
                                            }
                                            Spacer(modifier = Modifier.height(4.dp))
                                            Text(state.dayCard.rahuKaal, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextWhite)
                                            Text("Avoid new ventures", fontSize = 10.sp, color = TextMuted)
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(14.dp))

                                // Lucky Planet, Color & Number
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(12.dp))
                                            .background(CosmicCardElevated)
                                            .padding(10.dp)
                                    ) {
                                        Text("Lord: ${state.dayCard.dayLord}", fontSize = 11.sp, color = TextSoft)
                                    }
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(12.dp))
                                            .background(CosmicCardElevated)
                                            .padding(10.dp)
                                    ) {
                                        Text("Color: ${state.dayCard.luckyColor}", fontSize = 11.sp, color = Color(state.dayCard.luckyColorHex))
                                    }
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(12.dp))
                                            .background(CosmicCardElevated)
                                            .padding(10.dp)
                                    ) {
                                        Text("Number: ${state.dayCard.luckyNumber}", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = CelestialGold)
                                    }
                                }

                                Spacer(modifier = Modifier.height(18.dp))

                                // Pro Tip
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(14.dp))
                                        .background(Color(0xFF201642))
                                        .padding(14.dp)
                                ) {
                                    Column {
                                        Text("Daily Cosmic Pro Tip", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialGoldLight)
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(state.dayCard.proTip, fontSize = 13.sp, color = TextWhite, lineHeight = 18.sp)
                                    }
                                }

                                Spacer(modifier = Modifier.height(14.dp))

                                // Do and Avoid
                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    state.dayCard.doItems.forEach { item ->
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = CelestialMint, modifier = Modifier.size(16.dp))
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text(item, fontSize = 12.sp, color = TextSoft)
                                        }
                                    }
                                    state.dayCard.avoidItems.forEach { item ->
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(Icons.Default.DoNotDisturb, contentDescription = null, tint = Color(0xFFFB7185), modifier = Modifier.size(16.dp))
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text(item, fontSize = 12.sp, color = TextSoft)
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                // Loving line
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(14.dp))
                                        .background(CelestialRose.copy(alpha = 0.12f))
                                        .border(1.dp, CelestialRose.copy(alpha = 0.3f), RoundedCornerShape(14.dp))
                                        .padding(14.dp)
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.Favorite, contentDescription = null, tint = CelestialRose, modifier = Modifier.size(18.dp))
                                        Spacer(modifier = Modifier.width(10.dp))
                                        Text(
                                            text = "“${state.dayCard.lovingLine}”",
                                            fontSize = 12.sp,
                                            fontFamily = FontFamily.Serif,
                                            color = Color(0xFFFCE7F3),
                                            lineHeight = 17.sp
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(14.dp))

                                OutlinedButton(
                                    onClick = { viewModel.showShareCard("DAY") },
                                    colors = ButtonDefaults.outlinedButtonColors(contentColor = CelestialGold),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Share Today's Sky Card")
                                }
                            }
                        }
                    }
                }

                1 -> {
                    // SUBTAB 1: NUMBERS (PYTHAGOREAN, CHALDEAN, VEDIC & LO SHU GRID)
                    item {
                        Card(
                            shape = RoundedCornerShape(24.dp),
                            colors = CardDefaults.cardColors(containerColor = CosmicCard),
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, CosmicBorder, RoundedCornerShape(24.dp))
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Text(
                                    text = "Your Sacred Numbers",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextWhite
                                )
                                Text(
                                    text = "Synthesized from Pythagorean, Chaldean & Vedic Ank Jyotish",
                                    fontSize = 12.sp,
                                    color = TextMuted
                                )

                                Spacer(modifier = Modifier.height(16.dp))

                                // 3 Core Numbers Pill Grid
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    NumberCard("Life Path", "${state.numerology.lifePath}", "Core Purpose", CelestialGold, Modifier.weight(1f))
                                    NumberCard("Moolank", "${state.numerology.moolank}", "Birth Day", CelestialLavender, Modifier.weight(1f))
                                    NumberCard("Bhagyank", "${state.numerology.bhagyank}", "Destiny", CelestialRose, Modifier.weight(1f))
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(14.dp))
                                        .background(CosmicCardElevated)
                                        .padding(14.dp)
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Column {
                                            Text("Naamank (Name Number)", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                            Text("Chaldean vibration for '${state.profile.name}'", fontSize = 11.sp, color = TextSoft)
                                        }
                                        Text(
                                            text = "${state.numerology.naamank} (${state.numerology.chaldeanCompound})",
                                            fontSize = 20.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = CelestialGold
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(20.dp))

                                // 3x3 Lo Shu Grid
                                Text(
                                    text = "3×3 Lo Shu Chinese Grid",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextWhite
                                )
                                Text(
                                    text = "Digits present in your birth date (${state.profile.birthDate})",
                                    fontSize = 11.sp,
                                    color = TextMuted
                                )

                                Spacer(modifier = Modifier.height(12.dp))

                                // Render Lo Shu Grid
                                Column(
                                    verticalArrangement = Arrangement.spacedBy(6.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    // Row 1: 4, 9, 2
                                    LoShuRow(listOf(4, 9, 2), state.numerology.loShuCounts)
                                    // Row 2: 3, 5, 7
                                    LoShuRow(listOf(3, 5, 7), state.numerology.loShuCounts)
                                    // Row 3: 8, 1, 6
                                    LoShuRow(listOf(8, 1, 6), state.numerology.loShuCounts)
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                // Arrows of Strength
                                Text("Arrows of Strength & Potential:", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = CelestialGoldLight)
                                Spacer(modifier = Modifier.height(6.dp))
                                state.numerology.arrowStrengths.forEach { arrow ->
                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 3.dp)
                                            .clip(RoundedCornerShape(8.dp))
                                            .background(CosmicCardElevated)
                                            .padding(10.dp)
                                    ) {
                                        Text(arrow, fontSize = 12.sp, color = TextSoft)
                                    }
                                }
                            }
                        }
                    }
                }

                2 -> {
                    // SUBTAB 2: SIGNATURE STUDIO (GRAPHOLOGY)
                    item {
                        Card(
                            shape = RoundedCornerShape(24.dp),
                            colors = CardDefaults.cardColors(containerColor = CosmicCard),
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, CosmicBorder, RoundedCornerShape(24.dp))
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Draw, contentDescription = null, tint = CelestialCyan, modifier = Modifier.size(24.dp))
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Column {
                                        Text("Signature Studio & Graphology", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                        Text("On-device stroke, slant & baseline metrics", fontSize = 11.sp, color = TextMuted)
                                    }
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                // Graphology Principles Box
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(14.dp))
                                        .background(CosmicCardElevated)
                                        .padding(14.dp)
                                ) {
                                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        GraphologyItem("Ascending Baseline", "Optimistic ambition, future-oriented drive, confidence in long-term goals.")
                                        GraphologyItem("Rightward Slant (15°-25°)", "Warmth, emotional expression, readiness to connect with community.")
                                        GraphologyItem("Balanced Middle Zone", "Presence in daily realities, healthy focus on relationships & hobbies.")
                                        GraphologyItem("Clean Stroke Clarity", "Transparency, clarity in commitments, avoidance of hidden motives.")
                                    }
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                Text("Empowering Signature Practice:", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = CelestialGoldLight)
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = "1. Always finish your signature with an upward flourish to invite progressive energy.\n2. Avoid crossing out your own name or drawing downward slashing lines.\n3. Keep the first letter confident, open, and slightly larger than the rest to anchor your personal identity.",
                                    fontSize = 12.sp,
                                    color = TextSoft,
                                    lineHeight = 18.sp
                                )
                            }
                        }
                    }
                }

                3 -> {
                    // SUBTAB 3: YOUR BLUEPRINT (SYNTHESIS)
                    item {
                        Card(
                            shape = RoundedCornerShape(24.dp),
                            colors = CardDefaults.cardColors(containerColor = CosmicCard),
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, CelestialGold.copy(alpha = 0.5f), RoundedCornerShape(24.dp))
                        ) {
                            Column(modifier = Modifier.padding(20.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(22.dp))
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Column {
                                        Text("Your Complete Blueprint", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                        Text("Unified synthesis of Sky, Numbers & Habit rhythm", fontSize = 11.sp, color = TextMuted)
                                    }
                                }

                                Spacer(modifier = Modifier.height(18.dp))

                                // Synthesis Badges
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    BlueprintBadge("Vedic Moon", state.dayCard.moonSignVedic, CelestialLavender, Modifier.weight(1f))
                                    BlueprintBadge("Life Path", "${state.numerology.lifePath}", CelestialGold, Modifier.weight(1f))
                                    BlueprintBadge("Nakshatra", state.dayCard.nakshatra.split(" ").first(), CelestialCyan, Modifier.weight(1f))
                                }

                                Spacer(modifier = Modifier.height(16.dp))

                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(14.dp))
                                        .background(CosmicCardElevated)
                                        .padding(14.dp)
                                ) {
                                    Column {
                                        Text("Core Life Superpower", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = CelestialGoldLight)
                                        Spacer(modifier = Modifier.height(6.dp))
                                        Text(
                                            text = "Your combination of Moolank ${state.numerology.moolank} and ${state.dayCard.moonSignVedic} Moon grants you sharp intuitive discernment paired with gentle emotional endurance. You thrive when balancing active creative projects with daily quiet solitude.",
                                            fontSize = 12.sp,
                                            color = TextWhite,
                                            lineHeight = 18.sp
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(14.dp))

                                Text("Key Resonances for ${state.profile.name}:", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                                Spacer(modifier = Modifier.height(6.dp))
                                state.numerology.coreQualities.forEach { q ->
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.padding(vertical = 2.dp)
                                    ) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(14.dp))
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(q, fontSize = 12.sp, color = TextSoft)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Edit Birth Details Dialog
    if (showEditBirthDialog) {
        EditBirthDialog(
            profile = state.profile,
            onSave = { updated ->
                viewModel.updateProfile(updated)
                showEditBirthDialog = false
            },
            onDismiss = { showEditBirthDialog = false }
        )
    }
}

@Composable
private fun NumberCard(label: String, value: String, subtitle: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(CosmicCardElevated)
            .border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(14.dp))
            .padding(12.dp)
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Text(value, fontSize = 22.sp, fontWeight = FontWeight.Bold, color = color)
            Text(label, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextWhite)
            Text(subtitle, fontSize = 9.sp, color = TextMuted)
        }
    }
}

@Composable
private fun LoShuRow(numbers: List<Int>, counts: Map<Int, Int>) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        numbers.forEach { num ->
            val count = counts[num] ?: 0
            val hasNum = count > 0
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(54.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (hasNum) CelestialGold.copy(alpha = 0.2f) else CosmicCardElevated)
                    .border(1.dp, if (hasNum) CelestialGold else CosmicBorder, RoundedCornerShape(10.dp)),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "$num",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (hasNum) CelestialGoldLight else TextMuted
                    )
                    Text(
                        text = if (hasNum) "×$count" else "—",
                        fontSize = 10.sp,
                        color = if (hasNum) CelestialGold else TextMuted
                    )
                }
            }
        }
    }
}

@Composable
private fun GraphologyItem(title: String, desc: String) {
    Column {
        Text(title, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = CelestialCyan)
        Text(desc, fontSize = 11.sp, color = TextSoft, lineHeight = 16.sp)
    }
}

@Composable
private fun BlueprintBadge(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(CosmicCardElevated)
            .border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
            .padding(10.dp)
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Text(label, fontSize = 10.sp, color = TextMuted)
            Text(value, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = color)
        }
    }
}

@Composable
fun EditBirthDialog(
    profile: com.example.model.UserProfile,
    onSave: (com.example.model.UserProfile) -> Unit,
    onDismiss: () -> Unit
) {
    var name by remember { mutableStateOf(profile.name) }
    var city by remember { mutableStateOf(profile.city) }
    var birthDate by remember { mutableStateOf(profile.birthDate) }
    var birthTime by remember { mutableStateOf(profile.birthTime) }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = CosmicCard),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, CosmicBorder, RoundedCornerShape(20.dp))
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text("Edit Birth & Astrological Details", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextWhite)

                TextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Your Name") },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CosmicCardElevated,
                        unfocusedContainerColor = CosmicCardElevated,
                        focusedTextColor = TextWhite,
                        unfocusedTextColor = TextWhite
                    ),
                    modifier = Modifier.fillMaxWidth()
                )

                TextField(
                    value = city,
                    onValueChange = { city = it },
                    label = { Text("Current City (for Rahu Kaal & Sunrise)") },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CosmicCardElevated,
                        unfocusedContainerColor = CosmicCardElevated,
                        focusedTextColor = TextWhite,
                        unfocusedTextColor = TextWhite
                    ),
                    modifier = Modifier.fillMaxWidth()
                )

                TextField(
                    value = birthDate,
                    onValueChange = { birthDate = it },
                    label = { Text("Birth Date (YYYY-MM-DD)") },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CosmicCardElevated,
                        unfocusedContainerColor = CosmicCardElevated,
                        focusedTextColor = TextWhite,
                        unfocusedTextColor = TextWhite
                    ),
                    modifier = Modifier.fillMaxWidth()
                )

                TextField(
                    value = birthTime,
                    onValueChange = { birthTime = it },
                    label = { Text("Birth Time (HH:MM)") },
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = CosmicCardElevated,
                        unfocusedContainerColor = CosmicCardElevated,
                        focusedTextColor = TextWhite,
                        unfocusedTextColor = TextWhite
                    ),
                    modifier = Modifier.fillMaxWidth()
                )

                Spacer(modifier = Modifier.height(6.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(onClick = onDismiss, modifier = Modifier.weight(1f)) {
                        Text("Cancel")
                    }
                    Button(
                        onClick = {
                            onSave(
                                profile.copy(
                                    name = name.ifBlank { "Friend" },
                                    city = city.ifBlank { "Dubai" },
                                    birthDate = birthDate.ifBlank { "1998-05-15" },
                                    birthTime = birthTime.ifBlank { "08:30" }
                                )
                            )
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = CelestialGold, contentColor = CosmicDark),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Save Details", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
