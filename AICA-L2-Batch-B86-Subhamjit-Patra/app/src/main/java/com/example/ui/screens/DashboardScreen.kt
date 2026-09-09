package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.TrendingUp
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Psychology
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.local.UserProfileEntity
import com.example.data.model.AssetCategory
import com.example.data.model.GoalCategory
import com.example.ui.FinPilotUiState
import com.example.ui.components.AddAssetDialog
import com.example.ui.components.AddGoalDialog
import com.example.ui.components.FetchAssessmentDialog
import com.example.ui.components.GradientProgressBar
import com.example.ui.components.PillBadge
import com.example.ui.components.ProfileDialog
import com.example.ui.components.SophisticatedCard
import com.example.ui.theme.BlueAccent
import com.example.ui.theme.CoralExpense
import com.example.ui.theme.DarkBackground
import com.example.ui.theme.DarkBorder
import com.example.ui.theme.DarkBorderLight
import com.example.ui.theme.DarkSurface
import com.example.ui.theme.DarkSurfaceVariant
import com.example.ui.theme.InsightBg
import com.example.ui.theme.InsightBorder
import com.example.ui.theme.InsightTextPrimary
import com.example.ui.theme.LavenderAccent
import com.example.ui.theme.MintSuccess
import com.example.ui.theme.TextPrimary
import com.example.ui.theme.TextSecondary
import com.example.util.CurrencyFormatter

@Composable
fun DashboardScreen(
    state: FinPilotUiState,
    onNavigateToTab: (Int) -> Unit,
    onAddAsset: (name: String, category: AssetCategory, amount: Double, institution: String) -> Unit,
    onAddGoal: (title: String, category: GoalCategory, targetAmount: Double, currentAmount: Double, targetYears: Int) -> Unit,
    onUpdateProfile: (UserProfileEntity) -> Unit,
    onFetchAllDetails: () -> Unit
) {
    var showAddAssetDialog by remember { mutableStateOf(false) }
    var showAddGoalDialog by remember { mutableStateOf(false) }
    var showProfileDialog by remember { mutableStateOf(false) }
    var showFetchDialog by remember { mutableStateOf(false) }

    if (showProfileDialog) {
        ProfileDialog(
            initialProfile = state.profile,
            onDismiss = { showProfileDialog = false },
            onSaveProfile = {
                onUpdateProfile(it)
                showProfileDialog = false
            }
        )
    }

    if (showFetchDialog) {
        FetchAssessmentDialog(
            state = state,
            onDismiss = { showFetchDialog = false },
            onFetchConfirmed = {
                onFetchAllDetails()
            }
        )
    }

    if (showAddAssetDialog) {
        AddAssetDialog(
            onDismiss = { showAddAssetDialog = false },
            onAdd = { name, cat, amount, inst ->
                onAddAsset(name, cat, amount, inst)
                showAddAssetDialog = false
            }
        )
    }

    if (showAddGoalDialog) {
        AddGoalDialog(
            onDismiss = { showAddGoalDialog = false },
            onAdd = { title, cat, target, current, years ->
                onAddGoal(title, cat, target, current, years)
                showAddGoalDialog = false
            }
        )
    }

    val health = state.healthResult
    val score = health?.totalScore ?: 88
    val grade = health?.grade ?: "OPTIMAL (GRADE A)"

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item { Spacer(modifier = Modifier.height(8.dp)) }

        // 1. Executive Top Bar with Profile Switcher / Editor
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(
                    modifier = Modifier.clickable { showProfileDialog = true }
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "FINPILOT AI • PERSONAL CFO (INR)",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            letterSpacing = 1.sp,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Icon(Icons.Default.Edit, contentDescription = "Edit Profile", tint = LavenderAccent, modifier = Modifier.size(13.dp))
                    }
                    Text(
                        text = state.profile.name,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    Text(
                        text = "${state.profile.city} • ${state.profile.taxRegime}",
                        fontSize = 11.sp,
                        color = TextSecondary
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(
                        onClick = { onNavigateToTab(4) },
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(DarkSurfaceVariant)
                            .border(1.dp, DarkBorderLight, CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Notifications,
                            contentDescription = "Reminders",
                            tint = LavenderAccent,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Box(
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(Brush.linearGradient(listOf(LavenderAccent, BlueAccent)))
                            .clickable { showProfileDialog = true },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = state.profile.name.take(2).uppercase(),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = DarkBackground
                        )
                    }
                }
            }
        }

        // 2. Fetch All Details & Account Aggregator Banner
        item {
            SophisticatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { showFetchDialog = true },
                cornerRadius = 24,
                backgroundColor = DarkSurfaceVariant,
                borderColor = LavenderAccent.copy(alpha = 0.4f)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(CircleShape)
                            .background(LavenderAccent.copy(alpha = 0.2f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.AccountBalance,
                            contentDescription = "Sync",
                            tint = LavenderAccent,
                            modifier = Modifier.size(22.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Fetch Details & Refresh Assessment",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Sync Indian bank, EPF, NPS, Zerodha & loan details via RBI AA framework.",
                            fontSize = 11.sp,
                            color = TextSecondary,
                            lineHeight = 15.sp
                        )
                    }
                    Icon(
                        imageVector = Icons.Default.Sync,
                        contentDescription = "Sync",
                        tint = LavenderAccent,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
        }

        // 3. Financial Health Score Hero Card (Fiduciary Assessment)
        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 28,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(
                    modifier = Modifier.padding(20.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(LavenderAccent.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Shield,
                                    contentDescription = null,
                                    tint = LavenderAccent,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "Financial Health Score",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "Indian 6-Pillar Fiduciary Model",
                                    fontSize = 11.sp,
                                    color = TextSecondary
                                )
                            }
                        }

                        PillBadge(
                            text = grade,
                            textColor = MintSuccess,
                            backgroundColor = DarkSurfaceVariant,
                            borderColor = DarkBorderLight
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.Bottom,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.Bottom) {
                            Text(
                                text = "$score",
                                fontSize = 48.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                            Text(
                                text = "/100",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Medium,
                                color = TextSecondary,
                                modifier = Modifier.padding(bottom = 8.dp, start = 4.dp)
                            )
                        }

                        Text(
                            text = "Strong Resilience",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = LavenderAccent,
                            modifier = Modifier.padding(bottom = 10.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    GradientProgressBar(progress = score / 100f, height = 8)

                    Spacer(modifier = Modifier.height(14.dp))

                    Text(
                        text = health?.summaryText ?: "Your 6-pillar financial profile reflects top-decile emergency reserves in liquid FDs and disciplined equity SIP compounding.",
                        fontSize = 12.sp,
                        color = TextSecondary,
                        lineHeight = 17.sp
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text("Emergency Buffer", fontSize = 10.sp, color = TextSecondary)
                            Text("${String.format("%.1f", health?.emergencyFundMonths ?: 6.2)} Months", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = MintSuccess)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("Debt-to-Income", fontSize = 10.sp, color = TextSecondary)
                            Text("${String.format("%.1f", health?.debtToIncomePercent ?: 27.4)}%", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = LavenderAccent)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Life Term Cover", fontSize = 10.sp, color = TextSecondary)
                            Text("${String.format("%.1f", health?.lifeCoverMultiplier ?: 11.1)}x Income", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = MintSuccess)
                        }
                    }
                }
            }
        }

        // 4. AI CFO Smart Advisory Banner
        item {
            SophisticatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onNavigateToTab(2) },
                cornerRadius = 24,
                backgroundColor = InsightBg,
                borderColor = InsightBorder
            ) {
                Row(
                    modifier = Modifier.padding(18.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(LavenderAccent),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Psychology,
                            contentDescription = "AI CFO",
                            tint = DarkBackground,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Pocket CFO AI Advisory",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = InsightTextPrimary
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Ask complex Indian life decisions (Buy vs Rent, Home loan prepayment vs Nifty SIP, New vs Old Tax regime).",
                            fontSize = 11.sp,
                            color = TextSecondary,
                            lineHeight = 15.sp
                        )
                    }
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                        contentDescription = "Open CFO",
                        tint = LavenderAccent,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }

        // 5. Consolidated Balance Sheet Snapshot: Net Worth, Cash Flow
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Net Worth Card
                SophisticatedCard(
                    modifier = Modifier
                        .weight(1f)
                        .clickable { onNavigateToTab(1) },
                    cornerRadius = 20,
                    backgroundColor = DarkSurface,
                    borderColor = DarkBorder
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Net Worth (INR)",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = CurrencyFormatter.formatInr(state.netWorth, compact = true),
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Assets: ${CurrencyFormatter.formatInr(state.totalAssets, compact = true)}",
                            fontSize = 10.sp,
                            color = MintSuccess
                        )
                    }
                }

                // Monthly Free Cash Flow Card
                SophisticatedCard(
                    modifier = Modifier.weight(1f),
                    cornerRadius = 20,
                    backgroundColor = DarkSurface,
                    borderColor = DarkBorder
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Monthly Free Cash Flow",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = CurrencyFormatter.formatInr(state.netCashFlow),
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (state.netCashFlow >= 0) MintSuccess else CoralExpense
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "${String.format("%.1f", state.savingsRate)}% Savings Rate",
                            fontSize = 10.sp,
                            color = LavenderAccent
                        )
                    }
                }
            }
        }

        // 6. Active Goals & Horizon Section
        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 24,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.TrendingUp,
                                contentDescription = null,
                                tint = LavenderAccent,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Milestones & Retirement Horizon",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                        }

                        Text(
                            text = "View All",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = LavenderAccent,
                            modifier = Modifier.clickable { onNavigateToTab(3) }
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    if (state.goals.isEmpty()) {
                        Text(
                            text = "No active goals set yet. Add a retirement or wealth creation target in INR.",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    } else {
                        state.goals.take(3).forEach { goal ->
                            val progress = if (goal.targetAmount > 0) (goal.currentAmount / goal.targetAmount).toFloat() else 0f
                            val pct = (progress * 100).toInt()

                            Column(modifier = Modifier.padding(vertical = 6.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = goal.title,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Medium,
                                        color = TextPrimary
                                    )
                                    Text(
                                        text = "$pct% (${CurrencyFormatter.formatInr(goal.currentAmount, compact = true)} / ${CurrencyFormatter.formatInr(goal.targetAmount, compact = true)})",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = LavenderAccent
                                    )
                                }
                                Spacer(modifier = Modifier.height(6.dp))
                                GradientProgressBar(progress = progress, height = 5)
                            }
                        }
                    }
                }
            }
        }

        // 7. Quick Action Buttons
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 80.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    onClick = { showProfileDialog = true },
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = DarkSurfaceVariant,
                        contentColor = TextPrimary
                    ),
                    border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorderLight)
                ) {
                    Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Profile", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }

                Button(
                    onClick = { showFetchDialog = true },
                    modifier = Modifier.weight(1.3f).height(48.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = LavenderAccent,
                        contentColor = DarkBackground
                    )
                ) {
                    Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Fetch & Assess", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }

                Button(
                    onClick = { showAddAssetDialog = true },
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = DarkSurfaceVariant,
                        contentColor = TextPrimary
                    ),
                    border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorderLight)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Asset", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
