package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.AssetEntity
import com.example.data.local.LiabilityEntity
import com.example.data.model.AssetCategory
import com.example.ui.FinPilotUiState
import com.example.ui.components.AddAssetDialog
import com.example.ui.components.PillBadge
import com.example.ui.components.SophisticatedCard
import com.example.ui.theme.CoralExpense
import com.example.ui.theme.DarkBackground
import com.example.ui.theme.DarkBorder
import com.example.ui.theme.DarkBorderLight
import com.example.ui.theme.DarkSurface
import com.example.ui.theme.DarkSurfaceVariant
import com.example.ui.theme.LavenderAccent
import com.example.ui.theme.MintSuccess
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.util.CurrencyFormatter

@Composable
fun NetWorthScreen(
    state: FinPilotUiState,
    onAddAsset: (name: String, category: AssetCategory, amount: Double, institution: String) -> Unit,
    onDeleteAsset: (AssetEntity) -> Unit,
    onDeleteLiability: (LiabilityEntity) -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    var showAddAssetDialog by remember { mutableStateOf(false) }

    if (showAddAssetDialog) {
        AddAssetDialog(
            onDismiss = { showAddAssetDialog = false },
            onAdd = { name, cat, amount, inst ->
                onAddAsset(name, cat, amount, inst)
                showAddAssetDialog = false
            }
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
    ) {
        // Screen Header
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 14.dp)
        ) {
            Text(
                text = "INDIAN CONSOLIDATED BALANCE SHEET",
                fontSize = 10.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 1.sp,
                color = TextSecondary
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Portfolio & Net Worth",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                PillBadge(
                    text = "AUDITED (INR)",
                    textColor = MintSuccess,
                    backgroundColor = DarkSurfaceVariant,
                    borderColor = DarkBorderLight
                )
            }
        }

        // Tab Navigation
        TabRow(
            selectedTabIndex = selectedTab,
            containerColor = DarkBackground,
            contentColor = LavenderAccent,
            indicator = { tabPositions ->
                TabRowDefaults.SecondaryIndicator(
                    Modifier.tabIndicatorOffset(tabPositions[selectedTab]),
                    color = LavenderAccent,
                    height = 2.dp
                )
            },
            divider = {
                Box(modifier = Modifier.fillMaxWidth().height(1.dp).background(DarkBorder))
            }
        ) {
            Tab(
                selected = selectedTab == 0,
                onClick = { selectedTab = 0 },
                text = { Text("Overview", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) }
            )
            Tab(
                selected = selectedTab == 1,
                onClick = { selectedTab = 1 },
                text = { Text("Assets (${state.assets.size})", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) }
            )
            Tab(
                selected = selectedTab == 2,
                onClick = { selectedTab = 2 },
                text = { Text("Debts (${state.liabilities.size})", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) }
            )
        }

        when (selectedTab) {
            0 -> NetWorthOverviewTab(state = state)
            1 -> AssetsListTab(
                state = state,
                onAddClick = { showAddAssetDialog = true },
                onDeleteAsset = onDeleteAsset
            )
            2 -> LiabilitiesListTab(
                state = state,
                onDeleteLiability = onDeleteLiability
            )
        }
    }
}

@Composable
private fun NetWorthOverviewTab(state: FinPilotUiState) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 14.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 26,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(
                        text = "Net Worth Statement",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = TextSecondary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = CurrencyFormatter.formatInr(state.netWorth),
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "${CurrencyFormatter.formatInr(state.netWorth, compact = true)} across Bank, EPF, PPF, NPS, Zerodha & Real Estate",
                        fontSize = 11.sp,
                        color = LavenderAccent,
                        modifier = Modifier.padding(top = 2.dp)
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text("Total Assets", fontSize = 11.sp, color = TextSecondary)
                            Text(CurrencyFormatter.formatInr(state.totalAssets, compact = true), fontSize = 16.sp, fontWeight = FontWeight.Bold, color = MintSuccess)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Total Liabilities", fontSize = 11.sp, color = TextSecondary)
                            Text(CurrencyFormatter.formatInr(state.totalLiabilities, compact = true), fontSize = 16.sp, fontWeight = FontWeight.Bold, color = CoralExpense)
                        }
                    }
                }
            }
        }

        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 24,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text("Asset Class Allocation (India)", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(12.dp))

                    val groupedAssets = state.assets.groupBy { it.category }
                    groupedAssets.forEach { (cat, list) ->
                        val catTotal = list.sumOf { it.amount }
                        val pct = if (state.totalAssets > 0) (catTotal / state.totalAssets * 100).toInt() else 0
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("${cat.displayName} ($pct%)", color = TextSecondary, fontSize = 12.sp)
                            Text(CurrencyFormatter.formatInr(catTotal), color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 12.sp)
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}

@Composable
private fun AssetsListTab(
    state: FinPilotUiState,
    onAddClick: () -> Unit,
    onDeleteAsset: (AssetEntity) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Button(
                onClick = onAddClick,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
            ) {
                Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.size(8.dp))
                Text("Add New Asset (FD, MF, Gold, Stock)", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }

        items(state.assets) { asset ->
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 20,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(asset.name, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                        Text("${asset.category.displayName} • ${asset.institution}", color = TextSecondary, fontSize = 11.sp)
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        Text(CurrencyFormatter.formatInr(asset.amount), color = MintSuccess, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        IconButton(onClick = { onDeleteAsset(asset) }, modifier = Modifier.size(28.dp)) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete", tint = TextMuted, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}

@Composable
private fun LiabilitiesListTab(
    state: FinPilotUiState,
    onDeleteLiability: (LiabilityEntity) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        items(state.liabilities) { liab ->
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 20,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(liab.name, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                        Text("${liab.category.displayName} • ${liab.interestRate}% APR • ${liab.tenureMonthsRemaining} mos left", color = TextSecondary, fontSize = 11.sp)
                        Spacer(modifier = Modifier.height(2.dp))
                        Text("EMI: ${CurrencyFormatter.formatInr(liab.monthlyEmi)}/mo", color = CoralExpense, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        Text(CurrencyFormatter.formatInr(liab.outstandingAmount), color = CoralExpense, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        IconButton(onClick = { onDeleteLiability(liab) }, modifier = Modifier.size(28.dp)) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete", tint = TextMuted, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}
