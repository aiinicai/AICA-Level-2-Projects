package com.example.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.example.ui.FinPilotUiState
import com.example.ui.theme.DarkBackground
import com.example.ui.theme.DarkBorder
import com.example.ui.theme.DarkBorderLight
import com.example.ui.theme.DarkSurface
import com.example.ui.theme.DarkSurfaceVariant
import com.example.ui.theme.LavenderAccent
import com.example.ui.theme.MintSuccess
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.util.CurrencyFormatter
import kotlinx.coroutines.delay

@Composable
fun FetchAssessmentDialog(
    state: FinPilotUiState,
    onDismiss: () -> Unit,
    onFetchConfirmed: () -> Unit
) {
    var step by remember { mutableIntStateOf(0) }
    // step 0: Ready to fetch
    // step 1: Fetching simulated data from Indian Account Aggregator
    // step 2: Financial Assessment & Executive Summary ready

    LaunchedEffect(step) {
        if (step == 1) {
            delay(1400)
            onFetchConfirmed()
            delay(400)
            step = 2
        }
    }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(26.dp),
            color = DarkSurface,
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder),
            modifier = Modifier.fillMaxWidth().padding(vertical = 16.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(22.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(LavenderAccent.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = if (step == 2) Icons.Default.CheckCircle else Icons.Default.AccountBalance,
                                contentDescription = null,
                                tint = if (step == 2) MintSuccess else LavenderAccent,
                                modifier = Modifier.size(22.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = if (step == 2) "Executive Financial Assessment" else "RBI Account Aggregator Sync",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Text(
                                text = if (step == 2) "Fiduciary Assessment Completed" else "Consolidated Indian Financial Data",
                                fontSize = 11.sp,
                                color = TextSecondary
                            )
                        }
                    }

                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = TextSecondary)
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                if (step == 0) {
                    // Ready to fetch explanation
                    Text(
                        text = "Fetch and ingest all financial details securely across your Indian accounts under RBI's Account Aggregator (AA) framework:",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        lineHeight = 17.sp
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    ProviderItem("HDFC Bank & State Bank of India", "Savings, FDs, & Home Loan Schedule")
                    ProviderItem("Zerodha Kite & Groww", "Mutual Fund SIPs & Nifty/Midcap Demat Holdings")
                    ProviderItem("EPFO & NSDL Protean", "EPF UAN Passbook (8.25%) & NPS Tier-1")
                    ProviderItem("Insurance Repositories (CAMS/KFin)", "HDFC Life Term & Care Supreme Health")

                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(DarkSurfaceVariant)
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Security, contentDescription = null, tint = MintSuccess, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "256-bit End-to-End Encrypted. No banking credentials stored on device.",
                            fontSize = 10.sp,
                            color = TextSecondary
                        )
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    Button(
                        onClick = { step = 1 },
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
                    ) {
                        Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Fetch All Details & Run Assessment", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    }
                } else if (step == 1) {
                    // In-progress state
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        CircularProgressIndicator(
                            color = LavenderAccent,
                            strokeWidth = 3.dp,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("Connecting to RBI Account Aggregator...", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                        Spacer(modifier = Modifier.height(6.dp))
                        Text("Ingesting HDFC, SBI, Zerodha, EPFO & CAMS records...", fontSize = 11.sp, color = TextSecondary)
                    }
                } else {
                    // Step 2: Assessment and Executive Summary
                    val health = state.healthResult
                    val score = health?.totalScore ?: 88
                    val grade = health?.grade ?: "OPTIMAL (GRADE A)"

                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(16.dp))
                            .background(LavenderAccent.copy(alpha = 0.12f))
                            .border(1.dp, LavenderAccent.copy(alpha = 0.3f), RoundedCornerShape(16.dp))
                            .padding(16.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text("FINANCIAL RESILIENCE SCORE", fontSize = 10.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.sp, color = LavenderAccent)
                                Spacer(modifier = Modifier.height(2.dp))
                                Row(verticalAlignment = Alignment.Bottom) {
                                    Text("$score", fontSize = 36.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                                    Text("/100", fontSize = 14.sp, color = TextSecondary, modifier = Modifier.padding(bottom = 6.dp, start = 2.dp))
                                }
                            }
                            PillBadge(text = grade, textColor = MintSuccess, backgroundColor = DarkSurfaceVariant)
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Text("Consolidated Balance Sheet", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    Spacer(modifier = Modifier.height(8.dp))

                    MetricRow("Total Net Worth", CurrencyFormatter.formatInr(state.netWorth, compact = true), MintSuccess)
                    MetricRow("Gross Assets (Equity, EPF, Gold, Real Estate)", CurrencyFormatter.formatInr(state.totalAssets, compact = true), TextPrimary)
                    MetricRow("Total Liabilities (Home & Auto Loans)", CurrencyFormatter.formatInr(state.totalLiabilities, compact = true), TextSecondary)
                    MetricRow("Monthly Savings Rate", "${String.format("%.1f", state.savingsRate)}%", LavenderAccent)
                    MetricRow("Emergency Runway", "${String.format("%.1f", health?.emergencyFundMonths ?: 6.2)} Months", MintSuccess)
                    MetricRow("Debt-to-Income (EMI/Salary)", "${String.format("%.1f", health?.debtToIncomePercent ?: 27.4)}%", LavenderAccent)

                    Spacer(modifier = Modifier.height(14.dp))

                    Text("Personal CFO Key Takeaways", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    Spacer(modifier = Modifier.height(6.dp))

                    health?.strengths?.take(3)?.forEach { s ->
                        Text("✔ $s", fontSize = 11.sp, color = TextPrimary, lineHeight = 16.sp, modifier = Modifier.padding(vertical = 2.dp))
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = onDismiss,
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent, contentColor = DarkBackground)
                    ) {
                        Text("View Full Financial Dashboard", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun ProviderItem(name: String, detail: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier.size(8.dp).clip(CircleShape).background(MintSuccess)
        )
        Spacer(modifier = Modifier.width(10.dp))
        Column {
            Text(name, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
            Text(detail, fontSize = 10.sp, color = TextSecondary)
        }
    }
}

@Composable
private fun MetricRow(label: String, value: String, valueColor: androidx.compose.ui.graphics.Color) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 11.sp, color = TextSecondary)
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = valueColor)
    }
}
