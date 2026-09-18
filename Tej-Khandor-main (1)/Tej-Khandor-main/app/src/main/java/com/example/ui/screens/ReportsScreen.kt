package com.example.ui.screens

import android.content.Intent
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.PieChart
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.core.model.Money
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionStatus
import com.example.core.model.TransactionType
import com.example.core.repository.AgeingSummary
import com.example.core.repository.PartyWithBalance
import com.example.core.util.CsvExporter
import com.example.core.util.PdfStatementGenerator
import com.example.ui.components.PartyItemRow
import com.example.ui.theme.AmberContainer
import com.example.ui.theme.AmberPrimary
import com.example.ui.theme.BlueAccent
import com.example.ui.theme.BlueContainer
import com.example.ui.theme.CrimsonAccent
import com.example.ui.theme.CrimsonContainer
import com.example.ui.theme.CrimsonPrimary
import com.example.ui.theme.EmeraldAccent
import com.example.ui.theme.EmeraldContainer
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.theme.SlateNavy900
import com.example.ui.viewmodel.LedgerViewModel
import kotlinx.coroutines.launch
import java.io.File
import java.util.Calendar

data class AgeingBucket(
    val label: String,
    val amountPaise: Long,
    val parties: List<PartyWithBalance>
)

enum class AnalyticsTimePeriod(val title: String) {
    ALL_TIME("All Time"),
    THIS_MONTH("This Month"),
    LAST_30_DAYS("30 Days"),
    LAST_7_DAYS("7 Days"),
    TODAY("Today")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportsScreen(
    viewModel: LedgerViewModel,
    onNavigateToPartyDetail: (partyId: String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val activeBusiness by viewModel.activeBusiness.collectAsStateWithLifecycle()
    val partiesWithBalances by viewModel.partiesWithBalances.collectAsStateWithLifecycle()
    val recentTxs by viewModel.recentTransactions.collectAsStateWithLifecycle()

    var selectedTab by remember { mutableIntStateOf(0) }
    var selectedPeriod by remember { mutableStateOf(AnalyticsTimePeriod.ALL_TIME) }
    var selectedBucketIndex by remember { mutableStateOf<Int?>(null) }

    var showBackupDialog by remember { mutableStateOf(false) }
    var backupPassword by remember { mutableStateOf("") }

    val ageingSummary = remember(partiesWithBalances, recentTxs) {
        val txsByParty = recentTxs.groupBy { it.partyId ?: "" }
        viewModel.repository.calculateAgeing(partiesWithBalances, txsByParty)
    }

    // Filter transactions by selected time period
    val filteredTxs = remember(recentTxs, selectedPeriod) {
        val cal = Calendar.getInstance()
        val now = cal.timeInMillis
        when (selectedPeriod) {
            AnalyticsTimePeriod.ALL_TIME -> recentTxs
            AnalyticsTimePeriod.TODAY -> {
                cal.set(Calendar.HOUR_OF_DAY, 0)
                cal.set(Calendar.MINUTE, 0)
                cal.set(Calendar.SECOND, 0)
                cal.set(Calendar.MILLISECOND, 0)
                val startOfToday = cal.timeInMillis
                recentTxs.filter { it.transactionDate >= startOfToday }
            }
            AnalyticsTimePeriod.LAST_7_DAYS -> {
                val sevenDaysAgo = now - (7L * 24 * 60 * 60 * 1000)
                recentTxs.filter { it.transactionDate >= sevenDaysAgo }
            }
            AnalyticsTimePeriod.LAST_30_DAYS -> {
                val thirtyDaysAgo = now - (30L * 24 * 60 * 60 * 1000)
                recentTxs.filter { it.transactionDate >= thirtyDaysAgo }
            }
            AnalyticsTimePeriod.THIS_MONTH -> {
                cal.set(Calendar.DAY_OF_MONTH, 1)
                cal.set(Calendar.HOUR_OF_DAY, 0)
                cal.set(Calendar.MINUTE, 0)
                cal.set(Calendar.SECOND, 0)
                cal.set(Calendar.MILLISECOND, 0)
                val startOfMonth = cal.timeInMillis
                recentTxs.filter { it.transactionDate >= startOfMonth }
            }
        }
    }

    // Analytics Inflow / Outflow metrics in filtered period
    val periodMetrics = remember(filteredTxs) {
        var totalInflow = 0L // Got payments, income
        var totalOutflow = 0L // Gave credit, supplier payments, expenses
        var customerGot = 0L
        var customerGave = 0L
        var supplierCredit = 0L
        var supplierPaid = 0L
        var directExpenses = 0L
        var directIncome = 0L

        var upiPaise = 0L
        var cashPaise = 0L
        var bankPaise = 0L
        var chequePaise = 0L

        for (tx in filteredTxs) {
            if (tx.status == TransactionStatus.VOIDED.name) continue

            when (tx.type) {
                TransactionType.GOT.name -> {
                    totalInflow += tx.amountPaise
                    customerGot += tx.amountPaise
                }
                TransactionType.INCOME.name -> {
                    totalInflow += tx.amountPaise
                    directIncome += tx.amountPaise
                }
                TransactionType.GAVE.name -> {
                    totalOutflow += tx.amountPaise
                    customerGave += tx.amountPaise
                }
                TransactionType.PAYMENT_TO_SUPPLIER.name -> {
                    totalOutflow += tx.amountPaise
                    supplierPaid += tx.amountPaise
                }
                TransactionType.PURCHASE.name -> {
                    supplierCredit += tx.amountPaise
                }
                TransactionType.EXPENSE.name -> {
                    totalOutflow += tx.amountPaise
                    directExpenses += tx.amountPaise
                }
            }

            when (tx.paymentMode) {
                "UPI" -> upiPaise += tx.amountPaise
                "CASH" -> cashPaise += tx.amountPaise
                "BANK", "NETBANKING" -> bankPaise += tx.amountPaise
                "CHEQUE" -> chequePaise += tx.amountPaise
                else -> cashPaise += tx.amountPaise
            }
        }

        val totalModes = (upiPaise + cashPaise + bankPaise + chequePaise).coerceAtLeast(1L)

        AnalyticsPeriodData(
            totalInflowPaise = totalInflow,
            totalOutflowPaise = totalOutflow,
            netCashflowPaise = totalInflow - totalOutflow,
            customerGotPaise = customerGot,
            customerGavePaise = customerGave,
            supplierCreditPaise = supplierCredit,
            supplierPaidPaise = supplierPaid,
            directExpensesPaise = directExpenses,
            directIncomePaise = directIncome,
            upiPaise = upiPaise,
            cashPaise = cashPaise,
            bankPaise = bankPaise,
            chequePaise = chequePaise,
            upiPercent = (upiPaise.toFloat() / totalModes),
            cashPercent = (cashPaise.toFloat() / totalModes),
            bankPercent = (bankPaise.toFloat() / totalModes),
            chequePercent = (chequePaise.toFloat() / totalModes)
        )
    }

    // Top Debtors (Lena) & Top Creditors (Dena)
    val topDebtors = remember(partiesWithBalances) {
        partiesWithBalances.filter { it.netBalancePaise > 0 }
            .sortedByDescending { it.netBalancePaise }
            .take(5)
    }
    val topCreditors = remember(partiesWithBalances) {
        partiesWithBalances.filter { it.netBalancePaise < 0 }
            .sortedBy { it.netBalancePaise }
            .take(5)
    }

    val totalReceivablePaise = remember(partiesWithBalances) {
        partiesWithBalances.filter { it.netBalancePaise > 0 }.sumOf { it.netBalancePaise }
    }
    val totalPayablePaise = remember(partiesWithBalances) {
        partiesWithBalances.filter { it.netBalancePaise < 0 }.sumOf { kotlin.math.abs(it.netBalancePaise) }
    }

    if (showBackupDialog && activeBusiness != null) {
        AlertDialog(
            onDismissRequest = { showBackupDialog = false },
            title = { Text("Generate Encrypted Backup", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Enter a password to encrypt your entire LedgerPro database with military-grade AES-GCM encryption.")
                    OutlinedTextField(
                        value = backupPassword,
                        onValueChange = { backupPassword = it },
                        label = { Text("Backup Encryption Password *") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (backupPassword.length < 4) {
                            Toast.makeText(context, "Password must be at least 4 characters", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        coroutineScope.launch {
                            try {
                                val backupFile = viewModel.createBackup(backupPassword)
                                showBackupDialog = false
                                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", backupFile)
                                val intent = Intent(Intent.ACTION_SEND).apply {
                                    type = "application/octet-stream"
                                    putExtra(Intent.EXTRA_STREAM, uri)
                                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                }
                                context.startActivity(Intent.createChooser(intent, "Share Encrypted Backup"))
                            } catch (e: Exception) {
                                Toast.makeText(context, "Backup failed: ${e.message}", Toast.LENGTH_LONG).show()
                            }
                        }
                    }
                ) {
                    Text("Export Encrypted File")
                }
            },
            dismissButton = {
                TextButton(onClick = { showBackupDialog = false }) { Text("Cancel") }
            }
        )
    }

    Scaffold { innerPadding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            ScrollableTabRow(
                selectedTabIndex = selectedTab,
                edgePadding = 16.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Analytics, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Visual Analytics", fontWeight = FontWeight.Bold)
                        }
                    }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Assessment, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Credit Ageing", fontWeight = FontWeight.Bold)
                        }
                    }
                )
                Tab(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Reports & Downloads", fontWeight = FontWeight.Bold)
                        }
                    }
                )
            }

            when (selectedTab) {
                0 -> {
                    // TAB 1: VISUAL ANALYTICS DASHBOARD
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        // Time filter row
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                AnalyticsTimePeriod.values().forEach { period ->
                                    FilterChip(
                                        selected = selectedPeriod == period,
                                        onClick = { selectedPeriod = period },
                                        label = { Text(period.title, fontSize = 12.sp) },
                                        colors = FilterChipDefaults.filterChipColors(
                                            selectedContainerColor = MaterialTheme.colorScheme.primary,
                                            selectedLabelColor = MaterialTheme.colorScheme.onPrimary
                                        )
                                    )
                                }
                            }
                        }

                        // Executive Net Market Position Banner
                        item {
                            ElevatedCard(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(16.dp),
                                colors = CardDefaults.elevatedCardColors(containerColor = SlateNavy900)
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Column {
                                            Text(
                                                "Net Market Position (Market Capital)",
                                                style = MaterialTheme.typography.labelMedium,
                                                color = Color.White.copy(alpha = 0.7f)
                                            )
                                            val netPosition = totalReceivablePaise - totalPayablePaise
                                            Text(
                                                text = Money.formatIndianPaise(netPosition),
                                                style = MaterialTheme.typography.headlineMedium,
                                                fontWeight = FontWeight.ExtraBold,
                                                color = if (netPosition >= 0) EmeraldAccent else CrimsonAccent
                                            )
                                        }

                                        Surface(
                                            color = Color.White.copy(alpha = 0.1f),
                                            shape = RoundedCornerShape(8.dp)
                                        ) {
                                            Text(
                                                text = if (totalReceivablePaise >= totalPayablePaise) "NET SURPLUS" else "NET DEFICIT",
                                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                                style = MaterialTheme.typography.labelSmall,
                                                fontWeight = FontWeight.Bold,
                                                color = Color.White
                                            )
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(14.dp))
                                    HorizontalDivider(color = Color.White.copy(alpha = 0.15f))
                                    Spacer(modifier = Modifier.height(14.dp))

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Column {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Box(modifier = Modifier.size(8.dp).background(EmeraldAccent, CircleShape))
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Text("Receivables (Lena)", color = Color.White.copy(alpha = 0.8f), fontSize = 12.sp)
                                            }
                                            Text(
                                                Money.formatIndianPaise(totalReceivablePaise),
                                                color = Color.White,
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 15.sp
                                            )
                                            Text(
                                                "${topDebtors.size} Top Debtors",
                                                color = Color.White.copy(alpha = 0.6f),
                                                fontSize = 10.sp
                                            )
                                        }

                                        Column(horizontalAlignment = Alignment.End) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Box(modifier = Modifier.size(8.dp).background(CrimsonAccent, CircleShape))
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Text("Payables (Dena)", color = Color.White.copy(alpha = 0.8f), fontSize = 12.sp)
                                            }
                                            Text(
                                                Money.formatIndianPaise(totalPayablePaise),
                                                color = Color.White,
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 15.sp
                                            )
                                            Text(
                                                "${topCreditors.size} Top Creditors",
                                                color = Color.White.copy(alpha = 0.6f),
                                                fontSize = 10.sp
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // Period Inflow vs Outflow Cashflow Card
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(14.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(Icons.Default.TrendingUp, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                            Spacer(modifier = Modifier.width(8.dp))
                                            Text("Cashflow Dynamics (${selectedPeriod.title})", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(14.dp))

                                    // Visual Inflow vs Outflow progress gauge
                                    val sumFlow = (periodMetrics.totalInflowPaise + periodMetrics.totalOutflowPaise).coerceAtLeast(1L)
                                    val inflowRatio = periodMetrics.totalInflowPaise.toFloat() / sumFlow

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text("Inflow: ${Money.formatIndianPaise(periodMetrics.totalInflowPaise)}", color = EmeraldPrimary, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                        Text("Outflow: ${Money.formatIndianPaise(periodMetrics.totalOutflowPaise)}", color = CrimsonPrimary, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                    }

                                    Spacer(modifier = Modifier.height(6.dp))

                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(12.dp)
                                            .clip(RoundedCornerShape(6.dp))
                                            .background(CrimsonContainer)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .fillMaxWidth(inflowRatio.coerceIn(0.01f, 1f))
                                                .height(12.dp)
                                                .background(EmeraldPrimary)
                                        )
                                    }

                                    Spacer(modifier = Modifier.height(12.dp))

                                    // 4 Sub-metrics grid
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Column(modifier = Modifier.weight(1f)) {
                                            Text("Customer Payments (Got)", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            Text(Money.formatIndianPaise(periodMetrics.customerGotPaise), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = EmeraldPrimary)
                                        }
                                        Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                                            Text("Credit Sales (Gave)", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            Text(Money.formatIndianPaise(periodMetrics.customerGavePaise), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = CrimsonPrimary)
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(8.dp))

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Column(modifier = Modifier.weight(1f)) {
                                            Text("Supplier Settlements", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            Text(Money.formatIndianPaise(periodMetrics.supplierPaidPaise), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = BlueAccent)
                                        }
                                        Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                                            Text("Operating Expenses", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            Text(Money.formatIndianPaise(periodMetrics.directExpensesPaise), fontWeight = FontWeight.Bold, fontSize = 13.sp, color = AmberPrimary)
                                        }
                                    }
                                }
                            }
                        }

                        // Payment Channel Split
                        item {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(14.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.PieChart, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("Payment Channels Distribution", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                    }

                                    Spacer(modifier = Modifier.height(12.dp))

                                    PaymentChannelRow(
                                        channelName = "UPI / QR / Instant",
                                        amountPaise = periodMetrics.upiPaise,
                                        percentage = periodMetrics.upiPercent,
                                        barColor = EmeraldPrimary
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    PaymentChannelRow(
                                        channelName = "Cash in Hand",
                                        amountPaise = periodMetrics.cashPaise,
                                        percentage = periodMetrics.cashPercent,
                                        barColor = AmberPrimary
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    PaymentChannelRow(
                                        channelName = "Bank Transfer / NEFT / IMPS",
                                        amountPaise = periodMetrics.bankPaise,
                                        percentage = periodMetrics.bankPercent,
                                        barColor = BlueAccent
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    PaymentChannelRow(
                                        channelName = "Cheque / Drafts",
                                        amountPaise = periodMetrics.chequePaise,
                                        percentage = periodMetrics.chequePercent,
                                        barColor = Color.Gray
                                    )
                                }
                            }
                        }

                        // Top 5 Debtors (Lena) Leaderboard
                        if (topDebtors.isNotEmpty()) {
                            item {
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(14.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                                ) {
                                    Column(modifier = Modifier.padding(16.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(Icons.Default.TrendingDown, contentDescription = null, tint = EmeraldPrimary, modifier = Modifier.size(20.dp))
                                                Spacer(modifier = Modifier.width(8.dp))
                                                Text("Top Customers to Collect From (Lena)", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                            }
                                        }

                                        Spacer(modifier = Modifier.height(10.dp))

                                        topDebtors.forEach { debtor ->
                                            val maxDebt = topDebtors.first().netBalancePaise.coerceAtLeast(1L)
                                            val progress = debtor.netBalancePaise.toFloat() / maxDebt

                                            Row(
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .clip(RoundedCornerShape(8.dp))
                                                    .clickable { onNavigateToPartyDetail(debtor.party.id) }
                                                    .padding(vertical = 6.dp, horizontal = 4.dp),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Column(modifier = Modifier.weight(1f)) {
                                                    Text(debtor.party.name, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                                    Text("Phone: ${debtor.party.phone ?: "-"}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                                    Spacer(modifier = Modifier.height(4.dp))
                                                    LinearProgressIndicator(
                                                        progress = { progress },
                                                        modifier = Modifier.fillMaxWidth(0.9f).height(4.dp).clip(RoundedCornerShape(2.dp)),
                                                        color = EmeraldPrimary,
                                                        trackColor = EmeraldContainer
                                                    )
                                                }

                                                Text(
                                                    Money.formatIndianPaise(debtor.netBalancePaise),
                                                    color = EmeraldPrimary,
                                                    fontWeight = FontWeight.Bold,
                                                    fontSize = 14.sp
                                                )
                                            }
                                            HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                                        }
                                    }
                                }
                            }
                        }

                        // Top 5 Creditors (Dena) Leaderboard
                        if (topCreditors.isNotEmpty()) {
                            item {
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(14.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                                ) {
                                    Column(modifier = Modifier.padding(16.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(Icons.Default.Payments, contentDescription = null, tint = CrimsonPrimary, modifier = Modifier.size(20.dp))
                                                Spacer(modifier = Modifier.width(8.dp))
                                                Text("Top Suppliers to Pay (Dena)", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                            }
                                        }

                                        Spacer(modifier = Modifier.height(10.dp))

                                        topCreditors.forEach { creditor ->
                                            val maxPayable = kotlin.math.abs(topCreditors.first().netBalancePaise).coerceAtLeast(1L)
                                            val payable = kotlin.math.abs(creditor.netBalancePaise)
                                            val progress = payable.toFloat() / maxPayable

                                            Row(
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .clip(RoundedCornerShape(8.dp))
                                                    .clickable { onNavigateToPartyDetail(creditor.party.id) }
                                                    .padding(vertical = 6.dp, horizontal = 4.dp),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Column(modifier = Modifier.weight(1f)) {
                                                    Text(creditor.party.name, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                                    Text("Phone: ${creditor.party.phone ?: "-"}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                                    Spacer(modifier = Modifier.height(4.dp))
                                                    LinearProgressIndicator(
                                                        progress = { progress },
                                                        modifier = Modifier.fillMaxWidth(0.9f).height(4.dp).clip(RoundedCornerShape(2.dp)),
                                                        color = CrimsonPrimary,
                                                        trackColor = CrimsonContainer
                                                    )
                                                }

                                                Text(
                                                    Money.formatIndianPaise(payable),
                                                    color = CrimsonPrimary,
                                                    fontWeight = FontWeight.Bold,
                                                    fontSize = 14.sp
                                                )
                                            }
                                            HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                                        }
                                    }
                                }
                            }
                        }

                        item {
                            Spacer(modifier = Modifier.height(24.dp))
                        }
                    }
                }

                1 -> {
                    // TAB 2: CREDIT AGEING SCREEN
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        item {
                            Text(
                                text = "Receivables Ageing Analysis",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Track overdue credit brackets to identify collection risks and overdue balances.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }

                        if (ageingSummary != null) {
                            val summary = ageingSummary
                            val buckets = listOf(
                                AgeingBucket("0 - 30 Days (Current)", summary.currentPaise, summary.parties0To30),
                                AgeingBucket("31 - 60 Days (Watch)", summary.days31To60Paise, summary.parties31To60),
                                AgeingBucket("61 - 90 Days (Overdue)", summary.days61To90Paise, summary.parties61To90),
                                AgeingBucket("90+ Days (High Risk)", summary.over90Paise, summary.parties90Plus)
                            )

                            item {
                                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    buckets.forEachIndexed { index, bucket ->
                                        val isOverdue = index >= 2
                                        val isSelected = selectedBucketIndex == index

                                        Card(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clip(RoundedCornerShape(12.dp))
                                                .clickable {
                                                    selectedBucketIndex = if (isSelected) null else index
                                                },
                                            shape = RoundedCornerShape(12.dp),
                                            colors = CardDefaults.cardColors(
                                                containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer
                                                else if (isOverdue && bucket.amountPaise > 0) CrimsonContainer.copy(alpha = 0.4f)
                                                else MaterialTheme.colorScheme.surface
                                            ),
                                            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                                        ) {
                                            Row(
                                                modifier = Modifier
                                                    .fillMaxWidth()
                                                    .padding(14.dp),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Row(verticalAlignment = Alignment.CenterVertically) {
                                                    if (isOverdue && bucket.amountPaise > 0) {
                                                        Icon(Icons.Default.Warning, contentDescription = null, tint = CrimsonPrimary, modifier = Modifier.size(20.dp))
                                                        Spacer(modifier = Modifier.width(8.dp))
                                                    }
                                                    Column {
                                                        Text(bucket.label, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                                        Text("${bucket.parties.size} Parties", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                                    }
                                                }

                                                Text(
                                                    text = Money.formatIndianPaise(bucket.amountPaise),
                                                    fontSize = 16.sp,
                                                    fontWeight = FontWeight.ExtraBold,
                                                    color = if (isOverdue && bucket.amountPaise > 0) CrimsonPrimary else EmeraldPrimary
                                                )
                                            }
                                        }
                                    }
                                }
                            }

                            // Filtered Parties in selected bucket
                            if (selectedBucketIndex != null) {
                                val selectedBucket = buckets[selectedBucketIndex!!]
                                item {
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "Parties in ${selectedBucket.label} (${selectedBucket.parties.size})",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.Bold
                                    )
                                }

                                items(selectedBucket.parties) { partyItem ->
                                    PartyItemRow(
                                        item = partyItem,
                                        onClick = { onNavigateToPartyDetail(partyItem.party.id) }
                                    )
                                }
                            }
                        }

                        item {
                            Spacer(modifier = Modifier.height(20.dp))
                        }
                    }
                }

                2 -> {
                    // TAB 3: REPORTS & DOWNLOAD HUB
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        item {
                            Text("Financial Statements & Audit Hub", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Generate audit-ready PDF summaries, daybooks, Tally/Excel spreadsheets, and encrypted backups.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }

                        // 1. Executive Business Audit PDF Report
                        item {
                            ReportActionCard(
                                title = "Executive Business Audit Report (PDF)",
                                description = "Comprehensive A4 report with Financial KPIs, Net Market Capital, Ageing Brackets, and Top Debtors/Creditors.",
                                icon = Icons.Default.Assessment,
                                iconColor = SlateNavy900,
                                primaryActionText = "Download & Share Audit PDF",
                                onPrimaryAction = {
                                    if (activeBusiness != null) {
                                        val pdf = PdfStatementGenerator.generateComprehensiveBusinessAuditPdf(
                                            context = context,
                                            business = activeBusiness!!,
                                            totalReceivablePaise = totalReceivablePaise,
                                            totalPayablePaise = totalPayablePaise,
                                            todayInflowPaise = periodMetrics.totalInflowPaise,
                                            todayOutflowPaise = periodMetrics.totalOutflowPaise,
                                            topDebtors = topDebtors,
                                            topCreditors = topCreditors,
                                            ageingSummary = ageingSummary
                                        )
                                        if (pdf != null) {
                                            sharePdf(context, pdf, "Business Audit Report")
                                        } else {
                                            Toast.makeText(context, "Failed to generate PDF", Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                }
                            )
                        }

                        // 2. Outstanding Receivables & Payables Summary PDF
                        item {
                            ReportActionCard(
                                title = "Outstanding Summary Statement (PDF)",
                                description = "Clean printable directory listing every party with their net receivable (Lena) or payable (Dena) status.",
                                icon = Icons.Default.PictureAsPdf,
                                iconColor = CrimsonPrimary,
                                primaryActionText = "Generate Outstanding PDF",
                                onPrimaryAction = {
                                    if (activeBusiness != null) {
                                        val pdf = PdfStatementGenerator.generateOutstandingSummaryPdf(
                                            context = context,
                                            business = activeBusiness!!,
                                            parties = partiesWithBalances
                                        )
                                        if (pdf != null) {
                                            sharePdf(context, pdf, "Outstanding Summary PDF")
                                        } else {
                                            Toast.makeText(context, "Failed to generate PDF", Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                }
                            )
                        }

                        // 3. Chronological Daybook Register PDF
                        item {
                            ReportActionCard(
                                title = "Daybook & Transaction Register (PDF)",
                                description = "Audit trail listing chronological transactions with dates, party references, and payment modes.",
                                icon = Icons.Default.DateRange,
                                iconColor = BlueAccent,
                                primaryActionText = "Export Daybook PDF",
                                onPrimaryAction = {
                                    if (activeBusiness != null) {
                                        val partiesMap = partiesWithBalances.associate { it.party.id to it.party.name }
                                        val pdf = PdfStatementGenerator.generateDaybookPdf(
                                            context = context,
                                            business = activeBusiness!!,
                                            transactions = recentTxs,
                                            partiesMap = partiesMap
                                        )
                                        if (pdf != null) {
                                            sharePdf(context, pdf, "Daybook Register PDF")
                                        } else {
                                            Toast.makeText(context, "Failed to generate PDF", Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                }
                            )
                        }

                        // 4. Excel & Tally CSV Export
                        item {
                            ReportActionCard(
                                title = "Export All Transactions (Excel / CSV)",
                                description = "Standard comma-separated spreadsheet format ready for import into Microsoft Excel, Google Sheets, or Tally.",
                                icon = Icons.Default.TableChart,
                                iconColor = EmeraldPrimary,
                                primaryActionText = "Download CSV File",
                                onPrimaryAction = {
                                    val partiesMap = partiesWithBalances.associate { it.party.id to it.party.name }
                                    val csv = CsvExporter.exportAllTransactionsCsv(context, recentTxs, partiesMap)
                                    if (csv != null) {
                                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", csv)
                                        val intent = Intent(Intent.ACTION_SEND).apply {
                                            type = "text/csv"
                                            putExtra(Intent.EXTRA_STREAM, uri)
                                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                        }
                                        context.startActivity(Intent.createChooser(intent, "Share Transactions CSV"))
                                    } else {
                                        Toast.makeText(context, "Failed to generate CSV", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            )
                        }

                        // 5. Encrypted Database Backup
                        item {
                            ReportActionCard(
                                title = "Encrypted Offline Backup (.json)",
                                description = "Password-protected AES-256 GCM encrypted snapshot of all businesses, parties, accounts, and transactions.",
                                icon = Icons.Default.Lock,
                                iconColor = AmberPrimary,
                                primaryActionText = "Create Secure Backup",
                                onPrimaryAction = { showBackupDialog = true }
                            )
                        }

                        item {
                            Spacer(modifier = Modifier.height(24.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PaymentChannelRow(
    channelName: String,
    amountPaise: Long,
    percentage: Float,
    barColor: Color
) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(channelName, fontSize = 13.sp, fontWeight = FontWeight.Medium)
            Text(
                "${Money.formatIndianPaise(amountPaise)} (${(percentage * 100).toInt()}%)",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { percentage.coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp)),
            color = barColor,
            trackColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    }
}

@Composable
private fun ReportActionCard(
    title: String,
    description: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    iconColor: Color,
    primaryActionText: String,
    onPrimaryAction: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    color = iconColor.copy(alpha = 0.12f),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.size(40.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(icon, contentDescription = null, tint = iconColor, modifier = Modifier.size(22.dp))
                    }
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(title, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        description,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 11.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Button(
                onClick = onPrimaryAction,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp)
            ) {
                Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(primaryActionText, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

private fun sharePdf(context: android.content.Context, file: File, chooserTitle: String) {
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    context.startActivity(Intent.createChooser(intent, chooserTitle))
}

data class AnalyticsPeriodData(
    val totalInflowPaise: Long,
    val totalOutflowPaise: Long,
    val netCashflowPaise: Long,
    val customerGotPaise: Long,
    val customerGavePaise: Long,
    val supplierCreditPaise: Long,
    val supplierPaidPaise: Long,
    val directExpensesPaise: Long,
    val directIncomePaise: Long,
    val upiPaise: Long,
    val cashPaise: Long,
    val bankPaise: Long,
    val chequePaise: Long,
    val upiPercent: Float,
    val cashPercent: Float,
    val bankPercent: Float,
    val chequePercent: Float
)
