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
import com.example.data.local.GoalEntity
import com.example.data.model.GoalCategory
import com.example.ui.FinPilotUiState
import com.example.ui.components.AddGoalDialog
import com.example.ui.components.GradientProgressBar
import com.example.ui.components.PillBadge
import com.example.ui.components.SophisticatedCard
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

@Composable
fun GoalsScreen(
    state: FinPilotUiState,
    onAddGoal: (title: String, category: GoalCategory, targetAmount: Double, currentAmount: Double, targetYears: Int) -> Unit,
    onDeleteGoal: (GoalEntity) -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    var showAddGoalDialog by remember { mutableStateOf(false) }

    if (showAddGoalDialog) {
        AddGoalDialog(
            onDismiss = { showAddGoalDialog = false },
            onAdd = { title, cat, target, current, years ->
                onAddGoal(title, cat, target, current, years)
                showAddGoalDialog = false
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
                text = "INDIAN WEALTH & RETIREMENT HORIZONS",
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
                    text = "Goals & FIRE Plan",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                PillBadge(
                    text = "RETIRE AT ${state.profile.retirementAge}",
                    textColor = LavenderAccent,
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
            Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Active Goals", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) })
            Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Retirement (FIRE)", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) })
            Tab(selected = selectedTab == 2, onClick = { selectedTab = 2 }, text = { Text("Insurance (HLV)", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) })
        }

        when (selectedTab) {
            0 -> ActiveGoalsTab(
                state = state,
                onAddClick = { showAddGoalDialog = true },
                onDeleteGoal = onDeleteGoal
            )
            1 -> RetirementPlanTab(state = state)
            2 -> InsurancePlanTab(state = state)
        }
    }
}

@Composable
private fun ActiveGoalsTab(
    state: FinPilotUiState,
    onAddClick: () -> Unit,
    onDeleteGoal: (GoalEntity) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
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
                Text("Set New Financial Goal (INR)", fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        }

        items(state.goals) { goal ->
            val progress = if (goal.targetAmount > 0) (goal.currentAmount / goal.targetAmount).toFloat() else 0f
            val pct = (progress * 100).toInt()

            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 20,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(goal.title, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text("${goal.category.displayName} • ${goal.targetYears} yrs target (${goal.expectedReturnRate}% CAGR)", color = TextSecondary, fontSize = 11.sp)
                        }
                        IconButton(onClick = { onDeleteGoal(goal) }) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete", tint = TextSecondary.copy(alpha = 0.5f), modifier = Modifier.size(18.dp))
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    GradientProgressBar(progress = progress, height = 6)
                    Spacer(modifier = Modifier.height(10.dp))

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("${CurrencyFormatter.formatInr(goal.currentAmount, compact = true)} of ${CurrencyFormatter.formatInr(goal.targetAmount, compact = true)}", color = TextSecondary, fontSize = 11.sp)
                        Text("$pct% Complete", color = LavenderAccent, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}

@Composable
private fun RetirementPlanTab(state: FinPilotUiState) {
    val ret = state.retirementResult
    val isOnTrack = (ret?.corpusGap ?: 0.0) <= 0.0
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 24,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text("Indian Retirement Corpus (FIRE Model)", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(6.dp))
                    Text("Computed with 6.0% Indian inflation & 12.0% equity compounding.", color = TextSecondary, fontSize = 11.sp)
                    Spacer(modifier = Modifier.height(14.dp))

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Target Corpus (at age ${state.profile.retirementAge})", color = TextSecondary, fontSize = 11.sp)
                            Text(CurrencyFormatter.formatInr(ret?.requiredRetirementCorpus ?: 65000000.0, compact = true), color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Projected Corpus", color = TextSecondary, fontSize = 11.sp)
                            Text(CurrencyFormatter.formatInr(ret?.projectedCorpusFromCurrentSavings ?: 72000000.0, compact = true), color = MintSuccess, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    PillBadge(
                        text = if (isOnTrack) "ON TRACK TO RETIRE IN INDIA" else "REQUIRES STEP-UP SIP IN NIFTY 50",
                        textColor = if (isOnTrack) MintSuccess else LavenderAccent
                    )
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}

@Composable
private fun InsurancePlanTab(state: FinPilotUiState) {
    val ins = state.insuranceAudit
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            SophisticatedCard(
                modifier = Modifier.fillMaxWidth(),
                cornerRadius = 24,
                backgroundColor = DarkSurface,
                borderColor = DarkBorder
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text("Term & Health Insurance Audit (HLV)", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Spacer(modifier = Modifier.height(14.dp))

                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column {
                            Text("Existing Term Cover", color = TextSecondary, fontSize = 11.sp)
                            Text(CurrencyFormatter.formatInr(ins?.existingLifeCover ?: 25000000.0, compact = true), color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Human Life Value (HLV)", color = TextSecondary, fontSize = 11.sp)
                            Text(CurrencyFormatter.formatInr(ins?.requiredLifeCoverHLV ?: 22500000.0, compact = true), color = LavenderAccent, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    Text(
                        text = if ((ins?.lifeCoverGap ?: 0.0) <= 0.0) "Your pure term life insurance provides full fiduciary safety for your family in India (~11.1x annual income)." else "Consider adding pure term life cover of ${CurrencyFormatter.formatInr(ins?.lifeCoverGap ?: 0.0, compact = true)} to secure your dependents.",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        lineHeight = 18.sp
                    )
                }
            }
        }

        item { Spacer(modifier = Modifier.height(80.dp)) }
    }
}
