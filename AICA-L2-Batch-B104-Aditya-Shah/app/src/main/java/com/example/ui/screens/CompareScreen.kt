package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
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
import androidx.compose.material.icons.automirrored.filled.CompareArrows
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.ViewColumn
import androidx.compose.material.icons.filled.ViewStream
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.model.TaxSection
import com.example.model.TaxSource
import com.example.model.TextVerificationStatus
import com.example.ui.components.AiGeneratedBadge
import com.example.ui.components.CategoryBadge
import com.example.ui.components.MappingTypeBadge
import com.example.ui.components.StatusBadge
import com.example.ui.components.StatutoryDisclaimerCard
import com.example.ui.components.TextVerificationBadge
import com.example.ui.theme.EmeraldContainer
import com.example.ui.theme.EmeraldGreen
import com.example.ui.theme.PurpleAi
import com.example.ui.theme.SaffronAmber
import com.example.viewmodel.CompareTab
import com.example.viewmodel.TaxBridgeUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CompareScreen(
    uiState: TaxBridgeUiState,
    onSelectSection: (TaxSection) -> Unit,
    onToggleSideBySide: (Boolean) -> Unit,
    onSelectCompareTab: (CompareTab) -> Unit,
    onAskInAi: (TaxSection) -> Unit,
    modifier: Modifier = Modifier
) {
    val currentSection = uiState.compareSection ?: uiState.allSections.firstOrNull()
    var isDropdownExpanded by remember { mutableStateOf(false) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .testTag("compare_screen")
    ) {
        // App Bar
        TopAppBar(
            title = {
                Column {
                    Text(
                        text = "Concordance Comparator",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "Income-tax Act, 1961 ⇄ Income-tax Act, 2025",
                        style = MaterialTheme.typography.bodySmall.copy(
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    )
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.background
            )
        )

        // Section Selector Dropdown + View Toggle
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 4.dp),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
        ) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                // Section Picker Dropdown
                ExposedDropdownMenuBox(
                    expanded = isDropdownExpanded,
                    onExpandedChange = { isDropdownExpanded = !isDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = if (currentSection != null) "Sec ${currentSection.oldSectionNumber} → ${currentSection.displayNewSection}" else "Select provision",
                        onValueChange = {},
                        readOnly = true,
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = isDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth()
                            .testTag("compare_section_selector"),
                        label = { Text("Selected Provision") },
                        shape = RoundedCornerShape(10.dp)
                    )

                    ExposedDropdownMenu(
                        expanded = isDropdownExpanded,
                        onDismissRequest = { isDropdownExpanded = false }
                    ) {
                        uiState.allSections.forEach { section ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text(
                                            text = "Sec ${section.oldSectionNumber} → ${section.displayNewSection}",
                                            fontWeight = FontWeight.Bold
                                        )
                                        Text(
                                            text = "${section.displayOldHeading} [${section.mappingStatus.label}]",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                },
                                onClick = {
                                    onSelectSection(section)
                                    isDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Layout Switch (Side-by-Side vs Stacked)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(
                            imageVector = if (uiState.isSideBySideView) Icons.Default.ViewColumn else Icons.Default.ViewStream,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp)
                        )
                        Text(
                            text = if (uiState.isSideBySideView) "Side-by-Side View" else "Stacked View",
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium)
                        )
                    }

                    Switch(
                        checked = uiState.isSideBySideView,
                        onCheckedChange = onToggleSideBySide,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = MaterialTheme.colorScheme.primary,
                            checkedTrackColor = MaterialTheme.colorScheme.primaryContainer
                        ),
                        modifier = Modifier.testTag("side_by_side_switch")
                    )
                }
            }
        }

        if (currentSection == null) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text("Please select a provision to compare.")
            }
        } else {
            // Tabs
            TabRow(
                selectedTabIndex = uiState.activeCompareTab.ordinal,
                containerColor = MaterialTheme.colorScheme.surface,
                contentColor = MaterialTheme.colorScheme.primary,
                indicator = { tabPositions ->
                    TabRowDefaults.SecondaryIndicator(
                        Modifier.tabIndicatorOffset(tabPositions[uiState.activeCompareTab.ordinal]),
                        color = MaterialTheme.colorScheme.primary
                    )
                },
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
            ) {
                CompareTab.values().forEach { tab ->
                    Tab(
                        selected = uiState.activeCompareTab == tab,
                        onClick = { onSelectCompareTab(tab) },
                        text = {
                            Text(
                                text = tab.title,
                                fontSize = 12.sp,
                                fontWeight = if (uiState.activeCompareTab == tab) FontWeight.Bold else FontWeight.Normal
                            )
                        }
                    )
                }
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 96.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // Section Summary Header
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
                    ) {
                        Column(
                            modifier = Modifier.padding(14.dp),
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    MappingTypeBadge(type = currentSection.mappingType)
                                    CategoryBadge(category = currentSection.category)
                                }
                                StatusBadge(status = currentSection.mappingStatus)
                            }
                            Text(
                                text = "1961 Sec ${currentSection.oldSectionNumber} → 2025 ${currentSection.displayNewSection}",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                            Text(
                                text = "Source: ${currentSection.displaySource}",
                                style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                            )
                        }
                    }
                }

                // Tab Content Rendering
                when (uiState.activeCompareTab) {
                    CompareTab.STATUTORY_TEXT -> {
                        item {
                            if (uiState.isSideBySideView) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    // 1961 Act Column
                                    ProvisionTextPanel(
                                        title = "1961 Act — Sec ${currentSection.oldSectionNumber}",
                                        heading = currentSection.displayOldHeading,
                                        statutoryText = currentSection.displayOldText,
                                        textStatus = currentSection.oldTextStatus,
                                        source = currentSection.oldActSource,
                                        isOld = true,
                                        modifier = Modifier.weight(1f)
                                    )

                                    // 2025 Act Column (Can have multiple provisions, e.g. Sec 123 + Sch XV)
                                    Column(
                                        modifier = Modifier.weight(1f),
                                        verticalArrangement = Arrangement.spacedBy(10.dp)
                                    ) {
                                        if (currentSection.effectiveCorrespondingProvisions.isEmpty()) {
                                            ProvisionTextPanel(
                                                title = "2025 Act — ${currentSection.displayNewSection}",
                                                heading = currentSection.displayNewHeading,
                                                statutoryText = currentSection.displayNewText,
                                                textStatus = currentSection.newTextStatus,
                                                source = currentSection.newActSource,
                                                isOld = false,
                                                modifier = Modifier.fillMaxWidth()
                                            )
                                        } else {
                                            currentSection.effectiveCorrespondingProvisions.forEach { prov ->
                                                val provTitle = "2025 Act — ${prov.displayLabel}"
                                                val provHeading = prov.displayHeading ?: currentSection.displayNewHeading
                                                val provText = prov.displayText
                                                val provStatus = prov.textStatus
                                                val provSource = prov.source ?: currentSection.newActSource

                                                ProvisionTextPanel(
                                                    title = provTitle,
                                                    heading = provHeading,
                                                    statutoryText = provText,
                                                    textStatus = provStatus,
                                                    source = provSource,
                                                    relationship = prov.relationship,
                                                    isOld = false,
                                                    modifier = Modifier.fillMaxWidth()
                                                )
                                            }
                                        }
                                    }
                                }
                            } else {
                                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                    ProvisionTextPanel(
                                        title = "Income-tax Act, 1961 — Section ${currentSection.oldSectionNumber}",
                                        heading = currentSection.displayOldHeading,
                                        statutoryText = currentSection.displayOldText,
                                        textStatus = currentSection.oldTextStatus,
                                        source = currentSection.oldActSource,
                                        isOld = true,
                                        modifier = Modifier.fillMaxWidth()
                                    )

                                    if (currentSection.effectiveCorrespondingProvisions.isEmpty()) {
                                        ProvisionTextPanel(
                                            title = "Income-tax Act, 2025 — ${currentSection.displayNewSection}",
                                            heading = currentSection.displayNewHeading,
                                            statutoryText = currentSection.displayNewText,
                                            textStatus = currentSection.newTextStatus,
                                            source = currentSection.newActSource,
                                            isOld = false,
                                            modifier = Modifier.fillMaxWidth()
                                        )
                                    } else {
                                        currentSection.effectiveCorrespondingProvisions.forEach { prov ->
                                            val provTitle = "Income-tax Act, 2025 — ${prov.displayLabel}"
                                            val provHeading = prov.displayHeading ?: currentSection.displayNewHeading
                                            val provText = prov.displayText
                                            val provStatus = prov.textStatus
                                            val provSource = prov.source ?: currentSection.newActSource

                                            ProvisionTextPanel(
                                                title = provTitle,
                                                heading = provHeading,
                                                statutoryText = provText,
                                                textStatus = provStatus,
                                                source = provSource,
                                                relationship = prov.relationship,
                                                isOld = false,
                                                modifier = Modifier.fillMaxWidth()
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    CompareTab.SUMMARY -> {
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                border = androidx.compose.foundation.BorderStroke(1.5.dp, PurpleAi.copy(alpha = 0.3f))
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = "Transitional Summary",
                                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                                        )
                                        AiGeneratedBadge()
                                    }

                                    Text(
                                        text = currentSection.aiSummary ?: currentSection.notes ?: "Official data not yet loaded. Transitional commentary will be synthesized upon official Gazette ratification.",
                                        style = MaterialTheme.typography.bodySmall.copy(
                                            lineHeight = 18.sp,
                                            color = MaterialTheme.colorScheme.onSurface
                                        )
                                    )
                                }
                            }
                        }
                    }

                    CompareTab.WHATS_CHANGED -> {
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Text(
                                        text = "Concordance Specification & Structural Changes",
                                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                                    )

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text("Mapping Type:", style = MaterialTheme.typography.bodySmall)
                                        MappingTypeBadge(type = currentSection.mappingType)
                                    }

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text("Database Status:", style = MaterialTheme.typography.bodySmall)
                                        StatusBadge(status = currentSection.mappingStatus)
                                    }

                                    if (!currentSection.notes.isNullOrBlank()) {
                                        Text(
                                            text = "Notes: ${currentSection.notes}",
                                            style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        )
                                    }
                                }
                            }
                        }
                    }

                    CompareTab.PRACTICAL_IMPACT -> {
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Text(
                                        text = "Practical Compliance & Taxpayer Impact",
                                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                                    )

                                    Text(
                                        text = if (currentSection.isDataLoaded) {
                                            "Review restructured numbering for ERP, return filing forms, and statutory audit references."
                                        } else {
                                            "Official data not yet loaded. Practical compliance checklists will be populated upon official gazetted publication."
                                        },
                                        style = MaterialTheme.typography.bodySmall.copy(
                                            lineHeight = 18.sp,
                                            color = MaterialTheme.colorScheme.onSurface
                                        )
                                    )
                                }
                            }
                        }
                    }
                }

                // Ask AI Button
                item {
                    Button(
                        onClick = { onAskInAi(currentSection) },
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = PurpleAi),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("compare_ask_gemini_btn")
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Ask Gemini about Section ${currentSection.oldSectionNumber} Concordance")
                    }
                }

                item {
                    StatutoryDisclaimerCard(compact = true)
                }
            }
        }
    }
}

@Composable
fun ProvisionTextPanel(
    title: String,
    heading: String,
    statutoryText: String,
    textStatus: TextVerificationStatus = TextVerificationStatus.TEXT_NOT_LOADED,
    source: TaxSource? = null,
    relationship: String? = null,
    isOld: Boolean,
    modifier: Modifier = Modifier
) {
    val borderColor = if (isOld) MaterialTheme.colorScheme.primary.copy(alpha = 0.4f) else SaffronAmber.copy(alpha = 0.5f)
    val titleColor = if (isOld) MaterialTheme.colorScheme.primary else SaffronAmber

    Card(
        modifier = modifier.testTag(if (isOld) "provision_panel_old" else "provision_panel_new"),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = androidx.compose.foundation.BorderStroke(1.dp, borderColor)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        color = titleColor
                    )
                )

                TextVerificationBadge(status = textStatus)
            }

            if (relationship != null) {
                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
                ) {
                    Text(
                        text = "Relationship: $relationship",
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        style = MaterialTheme.typography.labelSmall.copy(
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    )
                }
            }

            Text(
                text = heading,
                style = MaterialTheme.typography.bodySmall.copy(
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                ),
                maxLines = 3
            )

            if (source != null) {
                Text(
                    text = "Source: ${source.publisher} (${source.authorityLevel.name}) • ${source.actName ?: (if (isOld) "Income-tax Act, 1961" else "Income-tax Act, 2025")}",
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontSize = 9.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    ),
                    maxLines = 1
                )
            }

            Surface(
                shape = RoundedCornerShape(6.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = if (statutoryText.isBlank() || statutoryText.startsWith("Statutory text for Section") && statutoryText.endsWith("not yet loaded.")) {
                        "Official statutory text not yet loaded from Primary Authority."
                    } else {
                        statutoryText
                    },
                    modifier = Modifier.padding(8.dp),
                    style = MaterialTheme.typography.bodySmall.copy(
                        fontSize = 11.sp,
                        lineHeight = 16.sp,
                        fontFamily = FontFamily.Default,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                )
            }
        }
    }
}
