package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Handshake
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Park
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.TaskAlt
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.data.model.Achievement
import com.example.data.model.CategoryType
import com.example.data.model.TransactionType
import com.example.domain.AccountingEngine
import com.example.ui.DashboardUiState
import kotlinx.coroutines.launch

@Composable
fun ReportsScreen(
    state: DashboardUiState,
    onExportCsvClick: suspend () -> String,
    onOpenMonthlyReview: () -> Unit,
    onOpenReconciliation: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var selectedReportTab by remember { mutableStateOf(0) } // 0: Income/Expense, 1: Balance Sheet, 2: Cash & Bank, 3: Achievements

    val categoryTotals = remember(state.transactions, state.categories) {
        val map = mutableMapOf<Long, Long>()
        for (tx in state.transactions) {
            if (!tx.isReversed && tx.type == TransactionType.EXPENSE && tx.categoryId != null) {
                map[tx.categoryId] = (map[tx.categoryId] ?: 0L) + tx.personalAmountPaise
            }
        }
        map
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
            .testTag("reports_screen"),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column {
                    Text(
                        text = "Financial Reports & Audit",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Accounting-grade balance sheets & habit milestones",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Action tools: CSV Export, Monthly Review, Reconcile
        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Button(
                    onClick = {
                        scope.launch {
                            val csv = onExportCsvClick()
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                            clipboard.setPrimaryClip(ClipData.newPlainText("Money Garden Ledger CSV", csv))
                            Toast.makeText(context, "Ledger CSV copied to clipboard!", Toast.LENGTH_LONG).show()
                        }
                    },
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier.weight(1f).testTag("btn_export_csv")
                ) {
                    Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Export CSV")
                }

                OutlinedButton(
                    onClick = onOpenMonthlyReview,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.weight(1f).testTag("btn_start_monthly_review")
                ) {
                    Icon(Icons.Default.AutoStories, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Review")
                }

                OutlinedButton(
                    onClick = onOpenReconciliation,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.weight(1f).testTag("btn_open_reconciliation")
                ) {
                    Icon(Icons.Default.TaskAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Reconcile")
                }
            }
        }

        // Segmented Tabs
        item {
            ScrollableTabRow(
                selectedTabIndex = selectedReportTab,
                edgePadding = 0.dp,
                containerColor = MaterialTheme.colorScheme.surfaceVariant,
                modifier = Modifier.clip(RoundedCornerShape(12.dp))
            ) {
                Tab(
                    selected = selectedReportTab == 0,
                    onClick = { selectedReportTab = 0 },
                    text = { Text("Income & Expense") }
                )
                Tab(
                    selected = selectedReportTab == 1,
                    onClick = { selectedReportTab = 1 },
                    text = { Text("Balance Sheet") }
                )
                Tab(
                    selected = selectedReportTab == 2,
                    onClick = { selectedReportTab = 2 },
                    text = { Text("Cash & Bank") }
                )
                Tab(
                    selected = selectedReportTab == 3,
                    onClick = { selectedReportTab = 3 },
                    text = { Text("Achievements") }
                )
            }
        }

        when (selectedReportTab) {
            0 -> { // INCOME & EXPENSE REPORT
                item {
                    val surplus = state.monthlyIncomePaise - state.monthlyPersonalExpensePaise
                    Card(
                        shape = RoundedCornerShape(20.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(18.dp)) {
                            Text(
                                text = "Current Month Summary",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(12.dp))

                            ReportLine(label = "Total Income", value = AccountingEngine.formatPaise(state.monthlyIncomePaise), isPositive = true)
                            Spacer(modifier = Modifier.height(8.dp))
                            ReportLine(label = "Total Personal Expenditure", value = AccountingEngine.formatPaise(state.monthlyPersonalExpensePaise), isPositive = false)
                            Spacer(modifier = Modifier.height(10.dp))
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = if (surplus >= 0) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    modifier = Modifier.padding(12.dp)
                                ) {
                                    Text("Net Monthly Surplus / (Deficit):", fontWeight = FontWeight.Bold)
                                    Text(AccountingEngine.formatPaise(surplus), fontWeight = FontWeight.ExtraBold)
                                }
                            }
                        }
                    }
                }

                // Category Breakdown
                item {
                    Text("Expenses by Category (Personal Share)", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                }

                if (categoryTotals.isEmpty()) {
                    item {
                        Text("No categorized expenses recorded yet.", style = MaterialTheme.typography.bodySmall)
                    }
                } else {
                    items(categoryTotals.entries.toList().sortedByDescending { it.value }) { entry ->
                        val cat = state.categories.find { it.id == entry.key }
                        Card(
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.padding(14.dp)
                            ) {
                                Text(cat?.name ?: "Other", fontWeight = FontWeight.SemiBold)
                                Text(AccountingEngine.formatPaise(entry.value), fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            1 -> { // BALANCE SHEET REPORT
                val bs = state.balanceSheet
                item {
                    Card(
                        shape = RoundedCornerShape(20.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                        modifier = Modifier.fillMaxWidth().testTag("card_balance_sheet")
                    ) {
                        Column(modifier = Modifier.padding(20.dp)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    text = "Balance Sheet",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold
                                )

                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = if (bs?.isBalanced == true) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.CheckCircle,
                                            contentDescription = null,
                                            tint = if (bs?.isBalanced == true) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                                            modifier = Modifier.size(14.dp)
                                        )
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text(
                                            text = if (bs?.isBalanced == true) "Balanced Ledger ✓" else "Unbalanced!",
                                            style = MaterialTheme.typography.labelSmall,
                                            fontWeight = FontWeight.Bold
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(14.dp))
                            Text("1. ASSETS", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.height(6.dp))
                            ReportLine(label = "Cash & Bank Accounts", value = AccountingEngine.formatPaise(bs?.cashAndBankPaise ?: 0L))
                            ReportLine(label = "Receivables (Friends Owe You)", value = AccountingEngine.formatPaise(bs?.receivablesPaise ?: 0L))
                            Spacer(modifier = Modifier.height(4.dp))
                            ReportLine(label = "TOTAL ASSETS", value = AccountingEngine.formatPaise(bs?.totalAssetsPaise ?: 0L), isBold = true)

                            Spacer(modifier = Modifier.height(16.dp))
                            Text("2. LIABILITIES", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.error)
                            Spacer(modifier = Modifier.height(6.dp))
                            ReportLine(label = "Payables (You Owe Friends)", value = AccountingEngine.formatPaise(bs?.payablesPaise ?: 0L))
                            ReportLine(label = "TOTAL LIABILITIES", value = AccountingEngine.formatPaise(bs?.totalLiabilitiesPaise ?: 0L), isBold = true)

                            Spacer(modifier = Modifier.height(16.dp))
                            Text("3. EQUITY & ACCUMULATED SURPLUS", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.secondary)
                            Spacer(modifier = Modifier.height(6.dp))
                            ReportLine(label = "Opening Balances / Initial Equity", value = AccountingEngine.formatPaise(bs?.openingEquityPaise ?: 0L))
                            ReportLine(label = "Historical Accumulated Surplus", value = AccountingEngine.formatPaise(bs?.accumulatedSurplusPaise ?: 0L))
                            Spacer(modifier = Modifier.height(4.dp))
                            ReportLine(label = "TOTAL EQUITY", value = AccountingEngine.formatPaise(bs?.totalEquityPaise ?: 0L), isBold = true)

                            Spacer(modifier = Modifier.height(14.dp))
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    modifier = Modifier.padding(12.dp)
                                ) {
                                    Text("LIABILITIES + EQUITY:", fontWeight = FontWeight.Bold)
                                    val sumLiabEquity = (bs?.totalLiabilitiesPaise ?: 0L) + (bs?.totalEquityPaise ?: 0L)
                                    Text(AccountingEngine.formatPaise(sumLiabEquity), fontWeight = FontWeight.ExtraBold)
                                }
                            }
                        }
                    }
                }
            }

            2 -> { // CASH & BANK MOVEMENTS
                item {
                    Text("Cash & Bank Account Ledger", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                }

                items(state.accounts) { acc ->
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(acc.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                                Text(AccountingEngine.formatPaise(acc.currentBalancePaise), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                            }
                            Spacer(modifier = Modifier.height(6.dp))
                            Text("Type: ${acc.accountType.name} • Opening Balance: ${AccountingEngine.formatPaise(acc.openingBalancePaise)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            3 -> { // ACHIEVEMENTS GALLERY
                item {
                    Text(
                        text = "Habit Achievements Gallery (${state.achievements.count { it.isUnlocked }}/${state.achievements.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }

                items(state.achievements) { ach ->
                    AchievementCard(achievement = ach)
                }
            }
        }

        item {
            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}

@Composable
fun ReportLine(label: String, value: String, isPositive: Boolean? = null, isBold: Boolean = false) {
    Row(
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
    ) {
        Text(
            text = label,
            style = if (isBold) MaterialTheme.typography.bodyMedium else MaterialTheme.typography.bodySmall,
            fontWeight = if (isBold) FontWeight.Bold else FontWeight.Normal
        )
        Text(
            text = value,
            style = if (isBold) MaterialTheme.typography.bodyMedium else MaterialTheme.typography.bodySmall,
            fontWeight = if (isBold) FontWeight.Bold else FontWeight.SemiBold,
            color = when (isPositive) {
                true -> MaterialTheme.colorScheme.primary
                false -> MaterialTheme.colorScheme.onSurface
                null -> MaterialTheme.colorScheme.onSurface
            }
        )
    }
}

@Composable
fun AchievementCard(achievement: Achievement) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (achievement.isUnlocked) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f) else MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth().testTag("ach_${achievement.code}")
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(14.dp)
        ) {
            Surface(
                shape = CircleShape,
                color = if (achievement.isUnlocked) MaterialTheme.colorScheme.primary else Color.LightGray,
                modifier = Modifier.size(44.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = getAchievementIcon(achievement.iconName),
                        contentDescription = null,
                        tint = if (achievement.isUnlocked) Color.White else Color.DarkGray,
                        modifier = Modifier.size(24.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.width(14.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = achievement.title,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    if (achievement.isUnlocked) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Icon(
                            Icons.Default.Verified,
                            contentDescription = "Unlocked",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
                Text(
                    text = achievement.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

private fun getAchievementIcon(name: String): ImageVector {
    return when (name) {
        "eco" -> Icons.Default.Eco
        "date_range" -> Icons.Default.DateRange
        "verified" -> Icons.Default.Verified
        "receipt_long" -> Icons.Default.ReceiptLong
        "task_alt" -> Icons.Default.TaskAlt
        "handshake" -> Icons.Default.Handshake
        "park" -> Icons.Default.Park
        "emoji_events" -> Icons.Default.EmojiEvents
        "insights" -> Icons.Default.Insights
        "auto_stories" -> Icons.Default.AutoStories
        else -> Icons.Default.EmojiEvents
    }
}
