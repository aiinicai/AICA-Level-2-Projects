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
import androidx.compose.material.icons.filled.AddAPhoto
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.PanTool
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Spa
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.model.GlowScanRecord
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
fun GlowScreen(
    state: SaathiUiState,
    viewModel: SaathiViewModel,
    modifier: Modifier = Modifier
) {
    var selectedModeIndex by remember { mutableIntStateOf(0) } // 0: Face & Skin, 1: Hair & Scalp, 2: Nails & Hands
    var showNewCheckinDialog by remember { mutableStateOf(false) }

    val modes = listOf("Face & Skin", "Hair & Scalp", "Nails & Hands")

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(CosmicDark),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Mode Selector Pills
        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                modes.forEachIndexed { index, modeName ->
                    val isSelected = selectedModeIndex == index
                    val (icon, color) = when (index) {
                        0 -> Pair(Icons.Default.Face, CelestialRose)
                        1 -> Pair(Icons.Default.Spa, CelestialMint)
                        else -> Pair(Icons.Default.PanTool, CelestialLavender)
                    }

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(14.dp))
                            .background(if (isSelected) color.copy(alpha = 0.2f) else CosmicCard)
                            .border(1.dp, if (isSelected) color else CosmicBorder, RoundedCornerShape(14.dp))
                            .clickable { selectedModeIndex = index }
                            .padding(vertical = 12.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(icon, contentDescription = null, tint = if (isSelected) color else TextSoft, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = modeName,
                                fontSize = 11.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                color = if (isSelected) TextWhite else TextSoft
                            )
                        }
                    }
                }
            }
        }

        // Active Mode Spotlight & Action
        item {
            val (modeTitle, modeDesc, modeColor) = when (selectedModeIndex) {
                0 -> Triple("Face & Skin Glow Check-in", "Personalized AM/PM routine, barrier support & ingredient analysis", CelestialRose)
                1 -> Triple("Hair & Scalp Vitality", "Roots health, gentle density care, hair oiling tips & scalp massage", CelestialMint)
                else -> Triple("Nails & Hand Care", "Cuticle hydration, nail strength, and hand nourishment rituals", CelestialLavender)
            }

            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = CosmicCard),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, modeColor.copy(alpha = 0.4f), RoundedCornerShape(20.dp))
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(modeTitle, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = TextWhite)
                            Text(modeDesc, fontSize = 11.sp, color = TextSoft)
                        }

                        Button(
                            onClick = { showNewCheckinDialog = true },
                            colors = ButtonDefaults.buttonColors(containerColor = modeColor, contentColor = CosmicDark),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Icon(Icons.Default.AddAPhoto, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Check In", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Safety Notice Pill
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(CosmicCardElevated)
                            .padding(10.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Shield, contentDescription = null, tint = CelestialGold, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Wellness & Cosmetic Care only. We never provide medical diagnoses or prescribe medications.",
                                fontSize = 11.sp,
                                color = TextSoft,
                                lineHeight = 15.sp
                            )
                        }
                    }
                }
            }
        }

        // Recent Routine & Ingredient Guidance
        items(state.glowRecords) { record ->
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
                        Text(
                            text = "${record.mode}  •  ${record.dateString}",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = CelestialGoldLight
                        )
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(CelestialMint.copy(alpha = 0.2f))
                                .padding(horizontal = 8.dp, vertical = 3.dp)
                        ) {
                            Text("Verified", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = CelestialMint)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Text(record.summary, fontSize = 13.sp, color = TextWhite, lineHeight = 18.sp)

                    Spacer(modifier = Modifier.height(14.dp))

                    // Morning Routine
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(CosmicCardElevated)
                            .padding(12.dp)
                    ) {
                        Column {
                            Text("☀️ Morning Routine", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialAmber)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(record.routineAM, fontSize = 12.sp, color = TextSoft, lineHeight = 17.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Night Routine
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(CosmicCardElevated)
                            .padding(12.dp)
                    ) {
                        Column {
                            Text("🌙 Night Routine", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = CelestialLavender)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(record.routinePM, fontSize = 12.sp, color = TextSoft, lineHeight = 17.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Ingredients Good vs Avoid
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Ingredients to Look For:", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = CelestialMint)
                            Spacer(modifier = Modifier.height(4.dp))
                            record.ingredientsGood.forEach { ing ->
                                Text("• $ing", fontSize = 11.sp, color = TextSoft)
                            }
                        }

                        Column(modifier = Modifier.weight(1f)) {
                            Text("Ingredients to Avoid:", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFFFB7185))
                            Spacer(modifier = Modifier.height(4.dp))
                            record.ingredientsAvoid.forEach { ing ->
                                Text("• $ing", fontSize = 11.sp, color = TextSoft)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "⚕️ Signpost: ${record.safetyNote}",
                        fontSize = 10.sp,
                        color = TextMuted,
                        lineHeight = 14.sp
                    )
                }
            }
        }
    }

    // New Glow Check-in Dialog
    if (showNewCheckinDialog) {
        NewGlowCheckinDialog(
            mode = modes[selectedModeIndex],
            onDismiss = { showNewCheckinDialog = false }
        )
    }
}

@Composable
fun NewGlowCheckinDialog(
    mode: String,
    onDismiss: () -> Unit
) {
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
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Text("New $mode Check-in", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = TextWhite)

                Text(
                    text = "Ensure your face, hair or hands are in clean daylight without heavy artificial filters. Saathi inspects visible brightness and clarity directly on your device.",
                    fontSize = 12.sp,
                    color = TextSoft,
                    lineHeight = 17.sp
                )

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(CosmicCardElevated)
                        .border(1.dp, CelestialRose.copy(alpha = 0.5f), RoundedCornerShape(14.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.AddAPhoto, contentDescription = null, tint = CelestialRose, modifier = Modifier.size(36.dp))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Capture Photo or Select from Gallery", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextWhite)
                        Text("Private & stays on device", fontSize = 10.sp, color = TextMuted)
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(onClick = onDismiss, modifier = Modifier.weight(1f)) {
                        Text("Cancel")
                    }
                    Button(
                        onClick = onDismiss,
                        colors = ButtonDefaults.buttonColors(containerColor = CelestialRose, contentColor = CosmicDark),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Save Routine (+15 Pts)", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}
