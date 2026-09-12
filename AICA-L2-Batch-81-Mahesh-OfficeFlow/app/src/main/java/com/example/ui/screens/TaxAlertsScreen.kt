package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Campaign
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TaxDepartment
import com.example.data.model.TaxNotification
import com.example.data.model.TaxSeverity
import com.example.ui.components.TaxNotificationCard
import com.example.ui.theme.AmberTax
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary

@Composable
fun TaxAlertsScreen(
    taxNotifications: List<TaxNotification>,
    selectedDepartmentFilter: TaxDepartment?,
    onDepartmentFilterChange: (TaxDepartment?) -> Unit,
    onBroadcastAlert: (TaxNotification) -> Unit,
    onConvertToTask: (TaxNotification) -> Unit,
    onAddCustomTaxNotice: () -> Unit,
    onTaxNoticeClick: (TaxNotification) -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }

    val departmentTabs = listOf(
        "All Statutory" to null,
        "GST Compliance" to TaxDepartment.GST,
        "Income Tax" to TaxDepartment.INCOME_TAX
    )

    val currentTabIndex = departmentTabs.indexOfFirst { it.second == selectedDepartmentFilter }.coerceAtLeast(0)

    val filteredNotifications = taxNotifications.filter { notif ->
        val matchesDept = selectedDepartmentFilter == null || notif.department == selectedDepartmentFilter
        val matchesSearch = searchQuery.isBlank() ||
            notif.title.contains(searchQuery, ignoreCase = true) ||
            notif.circularOrNotificationNo.contains(searchQuery, ignoreCase = true) ||
            notif.summary.contains(searchQuery, ignoreCase = true) ||
            notif.keyActionItems.contains(searchQuery, ignoreCase = true)
        matchesDept && matchesSearch
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .testTag("tax_alerts_screen")
        ) {
            // Header Search & Tabs
            Surface(
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 2.dp
            ) {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "GST & Income Tax Statutory Desk",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                            Text(
                                text = "Live circulars, return schedules & team push alerts",
                                style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = { searchQuery = it },
                        placeholder = { Text("Search GST circulars, Sec 43B(h), TDS, ITR...", fontSize = 13.sp) },
                        leadingIcon = {
                            Icon(Icons.Default.Search, contentDescription = null, modifier = Modifier.size(18.dp))
                        },
                        trailingIcon = {
                            if (searchQuery.isNotBlank()) {
                                IconButton(onClick = { searchQuery = "" }) {
                                    Icon(Icons.Default.Clear, contentDescription = "Clear", modifier = Modifier.size(18.dp))
                                }
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                            .testTag("tax_search_input"),
                        shape = RoundedCornerShape(12.dp),
                        singleLine = true
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    ScrollableTabRow(
                        selectedTabIndex = currentTabIndex,
                        edgePadding = 0.dp,
                        containerColor = Color.Transparent,
                        indicator = { tabPositions ->
                            TabRowDefaults.SecondaryIndicator(
                                Modifier.tabIndicatorOffset(tabPositions[currentTabIndex]),
                                color = if (selectedDepartmentFilter == TaxDepartment.INCOME_TAX) AmberTax else SapphirePrimary,
                                height = 3.dp
                            )
                        },
                        divider = {}
                    ) {
                        departmentTabs.forEachIndexed { index, (label, dept) ->
                            val isSelected = currentTabIndex == index
                            val count = if (dept == null) taxNotifications.size else taxNotifications.count { it.department == dept }
                            Tab(
                                selected = isSelected,
                                onClick = { onDepartmentFilterChange(dept) },
                                modifier = Modifier.testTag("tax_tab_${label.replace(" ", "_")}"),
                                text = {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                                    ) {
                                        Text(
                                            text = label,
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                            color = if (isSelected) {
                                                if (dept == TaxDepartment.INCOME_TAX) AmberTax else SapphirePrimary
                                            } else MaterialTheme.colorScheme.onSurfaceVariant,
                                            fontSize = 12.sp
                                        )
                                        Surface(
                                            shape = RoundedCornerShape(10.dp),
                                            color = MaterialTheme.colorScheme.surfaceVariant
                                        ) {
                                            Text(
                                                text = "$count",
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.Bold,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 1.dp)
                                            )
                                        }
                                    }
                                }
                            )
                        }
                    }
                }
            }

            // Quick Statutory Calendar Guide Summary Card
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 80.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f)),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Icon(Icons.Default.Info, contentDescription = null, tint = SapphirePrimary, modifier = Modifier.size(16.dp))
                                Text(
                                    text = "Monthly Statutory Key Dates Cheat Sheet",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 13.sp,
                                    color = SapphirePrimary
                                )
                            }
                            Text(
                                text = "• 11th: GSTR-1 (Outward B2B Supplies)\n• 13th: GSTR-6 / IFF (QRMP Invoices)\n• 15th: Advance Tax Installments (15% Jun, 45% Sep, 75% Dec, 100% Mar)\n• 20th: GSTR-3B (Summary Return & Tax Payment)\n• 31st (Quarterly): TDS Form 26Q & 24Q Filing",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurface,
                                lineHeight = 16.sp
                            )
                        }
                    }
                }

                if (filteredNotifications.isEmpty()) {
                    item {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(32.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("No statutory notices match the current filter.")
                        }
                    }
                } else {
                    items(filteredNotifications, key = { it.id }) { notif ->
                        TaxNotificationCard(
                            notification = notif,
                            onBroadcastAlert = { onBroadcastAlert(notif) },
                            onConvertToTask = { onConvertToTask(notif) },
                            onClick = { onTaxNoticeClick(notif) }
                        )
                    }
                }
            }
        }

        // FAB to create custom tax advisory / circular
        FloatingActionButton(
            onClick = onAddCustomTaxNotice,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(20.dp)
                .testTag("fab_add_tax_notice"),
            containerColor = AmberTax,
            contentColor = Color.White
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(Icons.Default.Campaign, contentDescription = "Broadcast Tax Notice")
                Spacer(modifier = Modifier.width(6.dp))
                Text("Broadcast Circular", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }
    }
}
