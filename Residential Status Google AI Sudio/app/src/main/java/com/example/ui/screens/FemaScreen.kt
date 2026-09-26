package com.example.ui.screens

import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.FlightLand
import androidx.compose.material.icons.filled.FlightTakeoff
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.RestartAlt
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.FemaArrivalPurpose
import com.example.model.FemaDeparturePurpose
import com.example.ui.components.FemaResultCard
import com.example.ui.components.NumericDaysInput
import com.example.ui.components.SelectableYearDropdown
import com.example.ui.theme.PrimaryNavy
import com.example.ui.theme.SlateBorder
import com.example.ui.theme.SlateMuted
import com.example.viewmodel.MainViewModel

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun FemaScreen(
    viewModel: MainViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val input by viewModel.femaInput.collectAsState()
    val result by viewModel.femaResult.collectAsState()
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("fema_screen"),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- Card 1: Client & Financial Year ---
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
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.AccountCircle,
                            contentDescription = null,
                            tint = PrimaryNavy,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Assessee & Relevant Period",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                    }

                    IconButton(
                        onClick = {
                            viewModel.updateFemaInput {
                                it.copy(
                                    assesseeName = "Mr. Rahul Sharma",
                                    pan = "ABCPS1234F",
                                    precedingYearDays = 183,
                                    hasGoneOutsideIndia = false,
                                    departurePurpose = FemaDeparturePurpose.TEMPORARY_OTHER,
                                    hasComeToIndia = false,
                                    arrivalPurpose = FemaArrivalPurpose.TEMPORARY_VISIT
                                )
                            }
                            Toast.makeText(context, "FEMA form reset", Toast.LENGTH_SHORT).show()
                        },
                        modifier = Modifier.testTag("fema_reset_btn")
                    ) {
                        Icon(
                            imageVector = Icons.Default.RestartAlt,
                            contentDescription = "Reset Form",
                            tint = SlateMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = input.assesseeName,
                    onValueChange = { newName ->
                        viewModel.updateFemaInput { it.copy(assesseeName = newName) }
                    },
                    label = { Text("Client / Assessee Name") },
                    placeholder = { Text("e.g., Mr. Rahul Sharma") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("fema_assessee_name_input"),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = PrimaryNavy,
                        unfocusedBorderColor = SlateBorder
                    )
                )

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    OutlinedTextField(
                        value = input.pan,
                        onValueChange = { newPan ->
                            viewModel.updateFemaInput { it.copy(pan = newPan.take(10)) }
                        },
                        label = { Text("PAN (Optional)") },
                        placeholder = { Text("ABCDE1234F") },
                        modifier = Modifier
                            .weight(1f)
                            .testTag("fema_pan_input"),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = PrimaryNavy,
                            unfocusedBorderColor = SlateBorder
                        )
                    )

                    // Financial Year Selector Dropdown
                    SelectableYearDropdown(
                        label = "Relevant Period",
                        selectedYear = input.financialYear,
                        yearsList = com.example.model.TaxYears.FEMA_FINANCIAL_YEARS,
                        onYearSelected = { year ->
                            viewModel.updateFemaInput { it.copy(financialYear = year) }
                        },
                        testTagPrefix = "fema_year_dropdown",
                        modifier = Modifier.weight(1.3f)
                    )
                }
            }
        }

        // --- Card 2: Physical Stay in Preceding Financial Year ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "1. Preceding FY Physical Stay Guidelines",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Text(
                    text = "FEMA tests stay in the PRECEDING financial year (must be strictly > 182 days, i.e., 183+ days).",
                    style = MaterialTheme.typography.bodySmall,
                    color = SlateMuted
                )

                Spacer(modifier = Modifier.height(12.dp))

                NumericDaysInput(
                    label = "Stay in India during Preceding FY",
                    value = input.precedingYearDays,
                    onValueChange = { days ->
                        viewModel.updateFemaInput { it.copy(precedingYearDays = days) }
                    },
                    maxLimit = 366,
                    helperText = if (input.precedingYearDays > 182) {
                        "✓ Exceeds 182 days (meets initial statutory physical threshold)."
                    } else {
                        "⚠️ 182 days or less (does not meet > 182 days threshold; intent test applies)."
                    },
                    testTagPrefix = "fema_prec_days"
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Presets for FEMA
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf(
                        183 to "183d (> 182 Threshold)",
                        182 to "182d (Boundary <= 182)",
                        120 to "120d",
                        60 to "60d",
                        0 to "0d (Abroad)"
                    ).forEach { (presetDays, label) ->
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = if (input.precedingYearDays == presetDays) PrimaryNavy else MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .clickable {
                                    viewModel.updateFemaInput { it.copy(precedingYearDays = presetDays) }
                                }
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                                .testTag("fema_preset_$presetDays")
                        ) {
                            Text(
                                text = label,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 11.sp
                                ),
                                color = if (input.precedingYearDays == presetDays) Color.White else PrimaryNavy
                            )
                        }
                    }
                }
            }
        }

        // --- Card 3: Conditional Branch Based on Preceding Year Stay ---
        if (input.precedingYearDays > 182) {
            // BRANCH A: Stay > 182 days -> Test Overseas Departure (Exclusion A)
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.FlightTakeoff,
                            contentDescription = null,
                            tint = PrimaryNavy,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "2. Overseas Departure Test [Exclusion (A)]",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                    }

                    Text(
                        text = "Even with > 182 days stay, departing for employment, business, or indefinite stay triggers PROI.",
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Has individual gone / stays outside India?",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Did the person depart from India or reside outside India during the current FY?",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = SlateMuted
                            )
                        }
                        Switch(
                            checked = input.hasGoneOutsideIndia,
                            onCheckedChange = { checked ->
                                viewModel.updateFemaInput { it.copy(hasGoneOutsideIndia = checked) }
                            },
                            modifier = Modifier.testTag("fema_departure_switch")
                        )
                    }

                    AnimatedVisibility(visible = input.hasGoneOutsideIndia) {
                        Column(modifier = Modifier.padding(top = 14.dp)) {
                            Text(
                                text = "Purpose of Going / Staying Outside India:",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = PrimaryNavy
                            )
                            Spacer(modifier = Modifier.height(8.dp))

                            FemaDeparturePurpose.values().forEach { purpose ->
                                val isSelected = input.departurePurpose == purpose
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                        .border(
                                            width = if (isSelected) 2.dp else 1.dp,
                                            color = if (isSelected) PrimaryNavy else SlateBorder,
                                            shape = RoundedCornerShape(8.dp)
                                        )
                                        .clickable {
                                            viewModel.updateFemaInput { it.copy(departurePurpose = purpose) }
                                        }
                                        .testTag("fema_departure_${purpose.name}"),
                                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f) else MaterialTheme.colorScheme.surface
                                ) {
                                    Row(
                                        modifier = Modifier.padding(10.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(18.dp)
                                                .clip(RoundedCornerShape(9.dp))
                                                .background(if (isSelected) PrimaryNavy else Color.Transparent)
                                                .border(2.dp, if (isSelected) PrimaryNavy else SlateMuted, RoundedCornerShape(9.dp)),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            if (isSelected) {
                                                Icon(
                                                    imageVector = Icons.Default.Check,
                                                    contentDescription = null,
                                                    tint = Color.White,
                                                    modifier = Modifier.size(10.dp)
                                                )
                                            }
                                        }

                                        Spacer(modifier = Modifier.width(10.dp))

                                        Text(
                                            text = purpose.label,
                                            style = MaterialTheme.typography.bodySmall.copy(
                                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                            ),
                                            color = if (isSelected) PrimaryNavy else MaterialTheme.colorScheme.onSurface
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            // BRANCH B: Stay <= 182 days -> Test Arrival in India (Inclusion B)
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.FlightLand,
                            contentDescription = null,
                            tint = PrimaryNavy,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "2. Arrival in India Test [Inclusion (B)]",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                    }

                    Text(
                        text = "Individual did not stay > 182 days in preceding FY. Arriving for employment, business, or indefinite stay confers PRI.",
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Has individual come to or stays in India?",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Has the person arrived or taken up residence in India in the current FY?",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = SlateMuted
                            )
                        }
                        Switch(
                            checked = input.hasComeToIndia,
                            onCheckedChange = { checked ->
                                viewModel.updateFemaInput { it.copy(hasComeToIndia = checked) }
                            },
                            modifier = Modifier.testTag("fema_arrival_switch")
                        )
                    }

                    AnimatedVisibility(visible = input.hasComeToIndia) {
                        Column(modifier = Modifier.padding(top = 14.dp)) {
                            Text(
                                text = "Purpose of Coming to / Staying in India:",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = PrimaryNavy
                            )
                            Spacer(modifier = Modifier.height(8.dp))

                            FemaArrivalPurpose.values().forEach { purpose ->
                                val isSelected = input.arrivalPurpose == purpose
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                        .border(
                                            width = if (isSelected) 2.dp else 1.dp,
                                            color = if (isSelected) PrimaryNavy else SlateBorder,
                                            shape = RoundedCornerShape(8.dp)
                                        )
                                        .clickable {
                                            viewModel.updateFemaInput { it.copy(arrivalPurpose = purpose) }
                                        }
                                        .testTag("fema_arrival_${purpose.name}"),
                                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f) else MaterialTheme.colorScheme.surface
                                ) {
                                    Row(
                                        modifier = Modifier.padding(10.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(18.dp)
                                                .clip(RoundedCornerShape(9.dp))
                                                .background(if (isSelected) PrimaryNavy else Color.Transparent)
                                                .border(2.dp, if (isSelected) PrimaryNavy else SlateMuted, RoundedCornerShape(9.dp)),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            if (isSelected) {
                                                Icon(
                                                    imageVector = Icons.Default.Check,
                                                    contentDescription = null,
                                                    tint = Color.White,
                                                    modifier = Modifier.size(10.dp)
                                                )
                                            }
                                        }

                                        Spacer(modifier = Modifier.width(10.dp))

                                        Text(
                                            text = purpose.label,
                                            style = MaterialTheme.typography.bodySmall.copy(
                                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                            ),
                                            color = if (isSelected) PrimaryNavy else MaterialTheme.colorScheme.onSurface
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // --- FEMA Determination Result Card ---
        FemaResultCard(
            result = result,
            onSaveToHistory = {
                viewModel.saveFemaAssessment {
                    Toast.makeText(context, "FEMA assessment saved to History!", Toast.LENGTH_SHORT).show()
                }
            }
        )

        Spacer(modifier = Modifier.height(32.dp))
    }
}
