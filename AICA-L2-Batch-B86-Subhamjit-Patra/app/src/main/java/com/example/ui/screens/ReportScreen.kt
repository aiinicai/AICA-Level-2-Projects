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
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CheckCircleOutline
import androidx.compose.material.icons.filled.Download
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
import com.example.ui.FinPilotUiState
import com.example.ui.components.PillBadge
import com.example.ui.components.SophisticatedCard
import com.example.ui.theme.CoralExpense
import com.example.ui.theme.DarkBackground
import com.example.ui.theme.DarkBorder
import com.example.ui.theme.DarkBorderLight
import com.example.ui.theme.DarkSurface
import com.example.ui.theme.DarkSurfaceVariant
import com.example.ui.theme.GoldWarning
import com.example.ui.theme.LavenderAccent
import com.example.ui.theme.MintSuccess
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.util.CurrencyFormatter

@Composable
fun ReportScreen(
    state: FinPilotUiState,
    onMarkNotificationActioned: (Long) -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    var reportDownloaded by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 14.dp)
        ) {
            Text(
                text = "INDIAN FIDUCIARY AUDIT",
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
                    text = "Personal CFO Report",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                PillBadge(
                    text = "INR MONTHLY AUDIT",
                    textColor = MintSuccess,
                    backgroundColor = DarkSurfaceVariant,
                    borderColor = DarkBorderLight
                )
            }
        }

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
            Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("CFO Statement", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) })
            val pendingCount = state.notifications.count { !it.isActioned }
            Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Reminders & Tax ($pendingCount)", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) })
        }

        when (selectedTab) {
            0 -> CfoReportTab(state = state, reportDownloaded = reportDownloaded, onDownload = { reportDownloaded = true })
            1 -> RemindersTab(state = state, onMarkActioned = onMarkNotificationActioned)
        }
    }
}

@Composable
private fun CfoReportTab(
    state: FinPilotUiState,
    reportDownloaded: Boolean,
    onDownload: () -> Unit
) {
    val health = state.healthResult

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 26,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Pocket CFO Personal Audit (India)", color = LavenderAccent, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            Text("Client: ${state.profile.name} • ${state.profile.profession} (${state.profile.city})", color = TextSecondary, fontSize = 11.sp)
                        }
                        PillBadge(text = "${health?.totalScore ?: 88}/100", textColor = MintSuccess)
                    }
                    Spacer(modifier = Modifier.height(14.dp))

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Consolidated Net Worth", color = TextSecondary, fontSize = 11.sp)
                            Text(CurrencyFormatter.formatInr(state.netWorth, compact = true), color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Monthly Savings / SIP Rate", color = TextSecondary, fontSize = 11.sp)
                            Text("${String.format("%.1f", state.savingsRate)}%", color = MintSuccess, fontWeight = FontWeight.Bold, fontSize = 18.sp)
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
                    Text("Six Core Financial Pillars (Indian Benchmarks)", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(12.dp))

                    PillarRow("1. Emergency Buffer (Liquid)", "${health?.emergencyFundScore ?: 20}/20 pts", "${String.format("%.1f", health?.emergencyFundMonths ?: 6.8)} mo liquid buffer")
                    PillarRow("2. Debt-to-Income (SBI/HDFC EMI)", "${health?.debtRatioScore ?: 20}/20 pts", "${String.format("%.1f", health?.debtToIncomePercent ?: 26.2)}% servicing ratio (< 40% safe)")
                    PillarRow("3. Savings & Equity SIP", "${health?.savingsRateScore ?: 15}/15 pts", "${String.format("%.1f", health?.savingsRatePercent ?: 50.8)}% monthly surplus")
                    PillarRow("4. Term & Health Insurance", "${health?.insuranceScore ?: 15}/15 pts", "₹2.50 Cr cover (11.1x annual salary)")
                    PillarRow("5. Diversification (EPF/NPS/Gold)", "${health?.diversificationScore ?: 14}/15 pts", "Multi-asset balance across Indian asset classes")
                    PillarRow("6. Retirement Horizon (FIRE @ ${state.profile.retirementAge})", "${health?.retirementScore ?: 14}/15 pts", "Projected ₹7.20 Cr corpus vs ₹6.50 Cr target")
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
                    Text("Indian Portfolio Strengths", color = MintSuccess, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(6.dp))
                    Text("✔ Emergency buffer covers > 6 months in liquid bank FDs and MaxiGain accounts.", color = TextPrimary, fontSize = 12.sp, lineHeight = 17.sp)
                    Text("✔ Healthy home loan debt-to-income servicing ratio of ~26%, well within RBI's 40% threshold.", color = TextPrimary, fontSize = 12.sp, lineHeight = 17.sp)
                    Text("✔ High equity and EPF/PPF compounding velocity toward financial independence (FIRE).", color = TextPrimary, fontSize = 12.sp, lineHeight = 17.sp)

                    Spacer(modifier = Modifier.height(12.dp))
                    Text("CFO Action Items", color = LavenderAccent, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(6.dp))
                    Text("• Prepay HDFC Car Loan (8.75%) with annual bonus to save interest.", color = TextSecondary, fontSize = 12.sp, lineHeight = 17.sp)
                    Text("• Keep EPF + PPF contributions active for guaranteed EEE tax-free compounding.", color = TextSecondary, fontSize = 12.sp, lineHeight = 17.sp)
                    Text("• Maintain 10% annual step-up in Zerodha Nifty 50 and Flexi Cap SIPs.", color = TextSecondary, fontSize = 12.sp, lineHeight = 17.sp)
                }
            }
        }

        item {
            Button(
                onClick = onDownload,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
            ) {
                Icon(if (reportDownloaded) Icons.Default.CheckCircle else Icons.Default.Download, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.size(8.dp))
                Text(if (reportDownloaded) "Executive Report Exported (PDF / CSV)" else "Export Indian CFO Report (PDF)", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}

@Composable
private fun PillarRow(name: String, score: String, detail: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column {
            Text(name, color = TextPrimary, fontWeight = FontWeight.Medium, fontSize = 12.sp)
            Text(detail, color = TextSecondary, fontSize = 10.sp)
        }
        Text(score, color = LavenderAccent, fontWeight = FontWeight.Bold, fontSize = 12.sp)
    }
}

@Composable
private fun RemindersTab(
    state: FinPilotUiState,
    onMarkActioned: (Long) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        items(state.notifications) { item ->
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 20,
                backgroundColor = if (item.isActioned) DarkSurfaceVariant.copy(alpha = 0.5f) else DarkSurface,
                borderColor = if (item.isActioned) DarkBorder else LavenderAccent.copy(alpha = 0.5f)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(item.title, color = if (item.isActioned) TextSecondary else TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        Text(item.description, color = TextSecondary, fontSize = 11.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text("Due: ${item.dueDateString} • ${item.type.displayName}", color = if (item.isActioned) TextMuted else GoldWarning, fontSize = 10.sp)
                    }

                    IconButton(onClick = { onMarkActioned(item.id) }) {
                        Icon(
                            imageVector = if (item.isActioned) Icons.Default.CheckCircle else Icons.Default.CheckCircleOutline,
                            contentDescription = "Actioned",
                            tint = if (item.isActioned) MintSuccess else LavenderAccent
                        )
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}
