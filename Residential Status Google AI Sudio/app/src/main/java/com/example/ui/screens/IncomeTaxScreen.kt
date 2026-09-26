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
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Pin
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
import androidx.compose.material3.SwitchDefaults
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.ITCategory
import com.example.ui.components.IncomeTaxResultCard
import com.example.ui.components.NumericDaysInput
import com.example.ui.components.SelectableYearDropdown
import com.example.ui.theme.GoldAccent
import com.example.ui.theme.PrimaryNavy
import com.example.ui.theme.PrimaryNavyDark
import com.example.ui.theme.SlateBorder
import com.example.ui.theme.SlateMuted
import com.example.viewmodel.MainViewModel

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun IncomeTaxScreen(
    viewModel: MainViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val input by viewModel.itInput.collectAsState()
    val result by viewModel.itResult.collectAsState()
    val scrollState = rememberScrollState()

    val assessmentYears = listOf(
        "AY 2026-27 (FY 2025-26)",
        "AY 2025-26 (FY 2024-25)",
        "AY 2024-25 (FY 2023-24)"
    )

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp)
            .testTag("it_screen"),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- Card 1: Assessee Information ---
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
                            text = if (com.example.model.TaxYears.isIta2025(input.assessmentYear)) "Assessee & Tax Year (ITA 2025)" else "Assessee & Assessment Year (ITA 1961)",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                    }

                    IconButton(
                        onClick = {
                            viewModel.updateItInput {
                                it.copy(
                                    assesseeName = "Mr. Rahul Sharma",
                                    pan = "ABCPS1234F",
                                    daysInFY = 182,
                                    category = ITCategory.STANDARD,
                                    indianIncomeExceeds15L = false,
                                    daysInPreceding4Years = 365,
                                    residentIn2Of10Years = true,
                                    daysInPreceding7Years = 730
                                )
                            }
                            Toast.makeText(context, "Reset to standard assessee", Toast.LENGTH_SHORT).show()
                        },
                        modifier = Modifier.testTag("it_reset_btn")
                    ) {
                        Icon(
                            imageVector = Icons.Default.RestartAlt,
                            contentDescription = "Reset Form",
                            tint = SlateMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Assessee Name
                OutlinedTextField(
                    value = input.assesseeName,
                    onValueChange = { newName ->
                        viewModel.updateItInput { it.copy(assesseeName = newName) }
                    },
                    label = { Text("Client / Assessee Name") },
                    placeholder = { Text("e.g., Mr. Rahul Sharma") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("it_assessee_name_input"),
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
                    // PAN (Optional)
                    OutlinedTextField(
                        value = input.pan,
                        onValueChange = { newPan ->
                            viewModel.updateItInput { it.copy(pan = newPan.take(10)) }
                        },
                        label = { Text("PAN (Optional)") },
                        placeholder = { Text("ABCDE1234F") },
                        modifier = Modifier
                            .weight(1f)
                            .testTag("it_pan_input"),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = PrimaryNavy,
                            unfocusedBorderColor = SlateBorder
                        )
                    )

                    // Tax / Assessment Year Selector Dropdown
                    SelectableYearDropdown(
                        label = if (com.example.model.TaxYears.isIta2025(input.assessmentYear)) "Tax Year (ITA 2025)" else "Assessment Year (ITA 1961)",
                        selectedYear = input.assessmentYear,
                        yearsList = com.example.model.TaxYears.INCOME_TAX_YEARS,
                        onYearSelected = { year ->
                            viewModel.updateItInput { it.copy(assessmentYear = year) }
                        },
                        testTagPrefix = "it_year_dropdown",
                        modifier = Modifier.weight(1.3f)
                    )
                }
            }
        }

        // --- Card 2: Assessee Category & Physical Presence ---
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "1. Assessee Category & Exceptions",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Text(
                    text = "Select applicable statutory classification under the Act",
                    style = MaterialTheme.typography.bodySmall,
                    color = SlateMuted
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Category Selection Cards
                ITCategory.values().forEach { cat ->
                    val isSelected = input.category == cat
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
                                viewModel.updateItInput { it.copy(category = cat) }
                            }
                            .testTag("it_category_${cat.name}"),
                        color = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f) else MaterialTheme.colorScheme.surface
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(20.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(if (isSelected) PrimaryNavy else Color.Transparent)
                                    .border(2.dp, if (isSelected) PrimaryNavy else SlateMuted, RoundedCornerShape(10.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                if (isSelected) {
                                    Icon(
                                        imageVector = Icons.Default.Check,
                                        contentDescription = null,
                                        tint = Color.White,
                                        modifier = Modifier.size(12.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.width(12.dp))

                            Column {
                                Text(
                                    text = cat.label,
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                    color = if (isSelected) PrimaryNavy else MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = cat.subtitle,
                                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                    color = SlateMuted
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))
                HorizontalDivider(color = SlateBorder)
                Spacer(modifier = Modifier.height(16.dp))

                // Days in FY
                Text(
                    text = "2. Stay in India during Relevant FY (1-Apr to 31-Mar)",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = PrimaryNavy
                )
                Spacer(modifier = Modifier.height(8.dp))

                NumericDaysInput(
                    label = "Total Days of Physical Presence in FY",
                    value = input.daysInFY,
                    onValueChange = { days ->
                        viewModel.updateItInput { it.copy(daysInFY = days) }
                    },
                    maxLimit = 366,
                    helperText = "Both arrival and departure dates are counted as days in India.",
                    testTagPrefix = "it_fy_days"
                )

                // Quick Presets
                Spacer(modifier = Modifier.height(8.dp))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf(182 to "182d (Threshold)", 183 to "183d (>182)", 120 to "120d (Amended)", 60 to "60d (Standard)", 0 to "0d (Abroad)").forEach { (presetDays, label) ->
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = if (input.daysInFY == presetDays) PrimaryNavy else MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .clickable {
                                    viewModel.updateItInput { it.copy(daysInFY = presetDays) }
                                }
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                                .testTag("it_preset_$presetDays")
                        ) {
                            Text(
                                text = label,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 11.sp
                                ),
                                color = if (input.daysInFY == presetDays) Color.White else PrimaryNavy
                            )
                        }
                    }
                }

                // Conditional: Visiting Citizen/PIO Income > 15L
                AnimatedVisibility(visible = input.category == ITCategory.VISITING_CITIZEN_OR_PIO) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 16.dp)
                            .background(Color(0xFFF9F5EC), RoundedCornerShape(8.dp))
                            .border(1.dp, GoldAccent.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                            .padding(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "Indian-Sourced Income > ₹15 Lakhs?",
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                    color = PrimaryNavy
                                )
                                Text(
                                    text = "Total income other than foreign source income exceeds Rs. 15 Lakhs during FY.",
                                    style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                    color = SlateMuted
                                )
                            }
                            Switch(
                                checked = input.indianIncomeExceeds15L,
                                onCheckedChange = { checked ->
                                    viewModel.updateItInput { it.copy(indianIncomeExceeds15L = checked) }
                                },
                                colors = SwitchDefaults.colors(checkedThumbColor = PrimaryNavy, checkedTrackColor = GoldAccent),
                                modifier = Modifier.testTag("it_income_15l_switch")
                            )
                        }
                    }
                }

                // Conditional: Preceding 4 Years Stay (Required if daysInFY < 182 and not citizen leaving, or if visiting with income > 15L)
                val needsPreceding4Years = input.daysInFY < 182 && (
                    input.category == ITCategory.STANDARD ||
                    (input.category == ITCategory.VISITING_CITIZEN_OR_PIO && input.indianIncomeExceeds15L)
                )

                AnimatedVisibility(visible = needsPreceding4Years) {
                    Column(modifier = Modifier.padding(top = 16.dp)) {
                        HorizontalDivider(color = SlateBorder)
                        Spacer(modifier = Modifier.height(14.dp))
                        Text(
                            text = "3. Secondary Condition: Preceding 4 Financial Years",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = PrimaryNavy
                        )
                        Text(
                            text = "Sum of physical presence in India during the 4 preceding FYs (threshold is >= 365 days)",
                            style = MaterialTheme.typography.bodySmall,
                            color = SlateMuted
                        )
                        Spacer(modifier = Modifier.height(8.dp))

                        NumericDaysInput(
                            label = "Cumulative Days in Preceding 4 FYs",
                            value = input.daysInPreceding4Years,
                            onValueChange = { days ->
                                viewModel.updateItInput { it.copy(daysInPreceding4Years = days) }
                            },
                            maxLimit = 1464,
                            helperText = "Maximum 1,464 days across 4 financial years (approx 365 x 4).",
                            testTagPrefix = "it_prec4_days"
                        )
                    }
                }
            }
        }

        // --- Card 3: Deemed Residency Check (if not qualifying via physical stay) ---
        val showDeemedResidentCard = !result.primaryConditionMet && !result.secondaryConditionMet
        AnimatedVisibility(visible = showDeemedResidentCard) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Deemed Residency Test Guidelines",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                    Text(
                        text = "Physical presence thresholds not met. Check statutory deemed residence criteria.",
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    // Citizen of India Toggle
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Citizen of India?",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Deemed residency applies strictly to Indian citizens (not foreign passport holders).",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = SlateMuted
                            )
                        }
                        Switch(
                            checked = input.isIndianCitizen,
                            onCheckedChange = { checked ->
                                viewModel.updateItInput { it.copy(isIndianCitizen = checked) }
                            },
                            modifier = Modifier.testTag("it_citizen_switch")
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Income > 15L Toggle
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Indian Income > ₹15 Lakhs?",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Total income other than foreign sources exceeds Rs. 15 Lakhs during the FY.",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = SlateMuted
                            )
                        }
                        Switch(
                            checked = input.indianIncomeExceeds15L,
                            onCheckedChange = { checked ->
                                viewModel.updateItInput { it.copy(indianIncomeExceeds15L = checked) }
                            },
                            modifier = Modifier.testTag("it_deemed_income_switch")
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Not Liable to Tax Elsewhere
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Not Liable to Tax Elsewhere?",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Not liable to tax in any other country or territory by reason of domicile/residence.",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = SlateMuted
                            )
                        }
                        Switch(
                            checked = input.notLiableToTaxElsewhere,
                            onCheckedChange = { checked ->
                                viewModel.updateItInput { it.copy(notLiableToTaxElsewhere = checked) }
                            },
                            modifier = Modifier.testTag("it_not_taxable_switch")
                        )
                    }
                }
            }
        }

        // --- Card 4: ROR vs RNOR Test (if Resident and not mandatory RNOR) ---
        val showRorTests = (result.primaryConditionMet || (result.secondaryConditionMet && !result.isMandatoryRNOR))
        AnimatedVisibility(visible = showRorTests) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Ordinarily Resident (ROR) Tests Guidelines",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = PrimaryNavy
                    )
                    Text(
                        text = "Both conditions must be satisfied to qualify as ROR; otherwise RNOR.",
                        style = MaterialTheme.typography.bodySmall,
                        color = SlateMuted
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    // Condition 1: Resident in 2 of 10 years
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Resident in >= 2 of 10 Preceding FYs?",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Was resident in India in at least 2 out of 10 financial years preceding the relevant FY.",
                                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.sp),
                                color = SlateMuted
                            )
                        }
                        Switch(
                            checked = input.residentIn2Of10Years,
                            onCheckedChange = { checked ->
                                viewModel.updateItInput { it.copy(residentIn2Of10Years = checked) }
                            },
                            modifier = Modifier.testTag("it_2of10_switch")
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    HorizontalDivider(color = SlateBorder)
                    Spacer(modifier = Modifier.height(14.dp))

                    // Condition 2: Stay in 7 years >= 730 days
                    NumericDaysInput(
                        label = "Stay in India during 7 Preceding FYs",
                        value = input.daysInPreceding7Years,
                        onValueChange = { days ->
                            viewModel.updateItInput { it.copy(daysInPreceding7Years = days) }
                        },
                        maxLimit = 2562,
                        helperText = "Statutory threshold is >= 730 days across the 7 preceding FYs.",
                        testTagPrefix = "it_prec7_days"
                    )
                }
            }
        }

        // --- Determination Result Card ---
        IncomeTaxResultCard(
            result = result,
            onSaveToHistory = {
                viewModel.saveItAssessment {
                    Toast.makeText(context, "Assessment saved to History!", Toast.LENGTH_SHORT).show()
                }
            }
        )

        Spacer(modifier = Modifier.height(32.dp))
    }
}
