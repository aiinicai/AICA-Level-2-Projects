package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Calculate
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
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
import com.example.ui.components.NumericDaysInput
import com.example.ui.theme.GoldAccent
import com.example.ui.theme.PrimaryNavy
import com.example.ui.theme.SlateBorder
import com.example.ui.theme.SlateMuted
import com.example.ui.theme.StatusNrBlue
import com.example.ui.theme.StatusRnorAmber
import com.example.ui.theme.StatusRorGreen

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DaysSimulatorScreen(modifier: Modifier = Modifier) {
    var plannedDays by remember { mutableIntStateOf(105) }
    var past4YearsStay by remember { mutableIntStateOf(400) }
    val scrollState = rememberScrollState()

    val safeDays182 = (181 - plannedDays).coerceAtLeast(0)
    val safeDays120 = (119 - plannedDays).coerceAtLeast(0)
    val safeDays60 = (59 - plannedDays).coerceAtLeast(0)

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("simulator_screen"),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- Header Intro Card ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Calculate,
                        contentDescription = null,
                        tint = PrimaryNavy,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Days Threshold & Safe-Stay Simulator",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "Simulate current year stay to identify critical tipping points across Income Tax (182d, 120d, 60d) and FEMA (>182d) regimes.",
                    style = MaterialTheme.typography.bodySmall,
                    color = SlateMuted
                )
            }
        }

        // --- Interactive Planned Days Input ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Planned Stay in Current FY",
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                    Text(
                        text = "$plannedDays Days",
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.ExtraBold,
                            color = PrimaryNavy
                        )
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Slider(
                    value = plannedDays.toFloat(),
                    onValueChange = { plannedDays = it.toInt() },
                    valueRange = 0f..365f,
                    colors = SliderDefaults.colors(
                        thumbColor = PrimaryNavy,
                        activeTrackColor = PrimaryNavy,
                        inactiveTrackColor = SlateBorder
                    ),
                    modifier = Modifier.testTag("simulator_slider")
                )

                NumericDaysInput(
                    label = "Fine-tune planned days:",
                    value = plannedDays,
                    onValueChange = { plannedDays = it },
                    maxLimit = 366,
                    testTagPrefix = "sim_days"
                )

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = "Quick Persona Scenarios:",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    color = SlateMuted
                )
                Spacer(modifier = Modifier.height(6.dp))

                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf(
                        "Short Vacation (45d)" to 45,
                        "Under 60d Limit (59d)" to 59,
                        "High Income NRI (115d)" to 115,
                        "120d Boundary (120d)" to 120,
                        "Near 182d Safe (180d)" to 180,
                        "182d Resident (182d)" to 182,
                        "FEMA PRI Threshold (183d)" to 183
                    ).forEach { (label, days) ->
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = if (plannedDays == days) PrimaryNavy else MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .clickable { plannedDays = days }
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = label,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 11.sp
                                ),
                                color = if (plannedDays == days) Color.White else PrimaryNavy
                            )
                        }
                    }
                }
            }
        }

        // --- Safe Stay Remaining Meters ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Threshold Safe-Zone Analysis",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Text(
                    text = "Calculates buffer days remaining before crossing each statutory line:",
                    style = MaterialTheme.typography.bodySmall,
                    color = SlateMuted
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Threshold 1: 182 Days (Universal Resident Threshold)
                ThresholdItem(
                    title = "182-Day Universal Rule (Sec 6(1)(a))",
                    currentDays = plannedDays,
                    threshold = 182,
                    remainingSafe = safeDays182,
                    impact = if (plannedDays >= 182) {
                        "⚠️ Crossed! Assessee is definitively RESIDENT for tax purposes."
                    } else {
                        "✓ Safe: Assessee can spend $safeDays182 more days in India before triggering the 182-day resident rule."
                    },
                    isBreached = plannedDays >= 182
                )

                Spacer(modifier = Modifier.height(14.dp))
                HorizontalDivider(color = SlateBorder)
                Spacer(modifier = Modifier.height(14.dp))

                // Threshold 2: 120 Days (Visiting NRI with Income > 15L)
                ThresholdItem(
                    title = "120-Day Rule for Visiting NRI (Income > ₹15L)",
                    currentDays = plannedDays,
                    threshold = 120,
                    remainingSafe = safeDays120,
                    impact = if (plannedDays >= 120) {
                        "⚠️ 120-day line crossed. If past 4 years stay was >= 365 days, assessee becomes RNOR!"
                    } else {
                        "✓ Safe: $safeDays120 more days before triggering amended visiting NRI threshold."
                    },
                    isBreached = plannedDays >= 120
                )

                Spacer(modifier = Modifier.height(14.dp))
                HorizontalDivider(color = SlateBorder)
                Spacer(modifier = Modifier.height(14.dp))

                // Threshold 3: 60 Days (Standard Individuals)
                ThresholdItem(
                    title = "60-Day Standard Secondary Rule (Sec 6(1)(c))",
                    currentDays = plannedDays,
                    threshold = 60,
                    remainingSafe = safeDays60,
                    impact = if (plannedDays >= 60) {
                        "⚠️ 60-day line crossed. If past 4 years stay was >= 365 days, standard assessee becomes Resident."
                    } else {
                        "✓ Safe: $safeDays60 more days before 60-day rule activates."
                    },
                    isBreached = plannedDays >= 60
                )
            }
        }

        // --- Regime Comparison Card ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Security,
                        contentDescription = null,
                        tint = GoldAccent,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Statutory Comparison: IT Act vs FEMA",
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = "Income Tax Act, 1961:",
                            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                        Text(
                            text = "• Tests stay in the CURRENT Financial Year (e.g. FY 2025-26)\n• Threshold is >= 182 days (or 120d / 60d + 365d in 4 years)\n• Status impacts taxability of worldwide income and filing ITR.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        Text(
                            text = "FEMA, 1999:",
                            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                        Text(
                            text = "• Tests stay in the PRECEDING Financial Year\n• Threshold is strictly MORE THAN 182 days (> 182, i.e. 183+ days)\n• Intent of leaving or arriving (employment / business / indefinite stay) overrides physical stay immediately\n• Status impacts bank accounts (NRE/NRO/FCNR/RFC) and foreign exchange transactions.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
private fun ThresholdItem(
    title: String,
    currentDays: Int,
    threshold: Int,
    remainingSafe: Int,
    impact: String,
    isBreached: Boolean
) {
    val progress = (currentDays.toFloat() / threshold).coerceIn(0f, 1f)

    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = PrimaryNavy
            )
            Text(
                text = "$currentDays / $threshold d",
                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
                color = if (isBreached) StatusRnorAmber else StatusRorGreen
            )
        }

        Spacer(modifier = Modifier.height(6.dp))

        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp)),
            color = if (isBreached) StatusRnorAmber else StatusRorGreen,
            trackColor = SlateBorder
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = impact,
            style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
            color = if (isBreached) StatusRnorAmber else MaterialTheme.colorScheme.onSurface
        )
    }
}
