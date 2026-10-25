package com.example.ui.screens

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Park
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.data.model.PlantType
import com.example.data.model.SavingsGoal
import com.example.domain.AccountingEngine
import com.example.ui.DashboardUiState
import com.example.ui.components.GardenPlantView

@Composable
fun SavingsGoalsScreen(
    state: DashboardUiState,
    onCreateGoal: (name: String, targetAmountPaise: Long, targetDate: Long?, plantType: PlantType, notes: String?) -> Unit,
    onContribute: (goalId: Long, amountPaise: Long, notes: String?) -> Unit,
    onWithdraw: (goalId: Long, amountPaise: Long, notes: String?) -> Unit
) {
    var showCreateGoalDialog by remember { mutableStateOf(false) }
    var selectedGoalForMovement by remember { mutableStateOf<SavingsGoal?>(null) }
    var isMovementContribution by remember { mutableStateOf(true) }
    var movementAmountText by remember { mutableStateOf("") }

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp)
                .testTag("savings_goals_screen"),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Savings Goals & Virtual Garden",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Each rupee saved nurtures your virtual plants into full bloom",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            // Accounting notice card
            item {
                Surface(
                    shape = RoundedCornerShape(14.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(14.dp)
                    ) {
                        Text("💡", style = MaterialTheme.typography.titleMedium)
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "Accounting Rule: Savings goals track your intended allocations within your real bank/cash funds without creating duplicate financial assets.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            if (state.savingsGoals.isEmpty()) {
                item {
                    Surface(
                        shape = RoundedCornerShape(20.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 24.dp)
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.padding(28.dp)
                        ) {
                            Text("🌱", style = MaterialTheme.typography.displayMedium)
                            Spacer(modifier = Modifier.height(10.dp))
                            Text(
                                "No savings goals planted yet",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                "Plant your first goal (e.g. Drawing tablet, Course, Trip) to grow your virtual garden!",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            } else {
                items(state.savingsGoals) { goal ->
                    GoalCardItem(
                        goal = goal,
                        onContributeClick = {
                            selectedGoalForMovement = goal
                            isMovementContribution = true
                            movementAmountText = ""
                        },
                        onWithdrawClick = {
                            selectedGoalForMovement = goal
                            isMovementContribution = false
                            movementAmountText = ""
                        }
                    )
                }
            }

            item {
                Spacer(modifier = Modifier.height(80.dp))
            }
        }

        FloatingActionButton(
            onClick = { showCreateGoalDialog = true },
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(20.dp)
                .testTag("fab_add_goal")
        ) {
            Icon(Icons.Default.Add, contentDescription = "Plant New Goal")
        }
    }

    // Plant New Goal Dialog
    if (showCreateGoalDialog) {
        var goalName by remember { mutableStateOf("") }
        var targetAmountText by remember { mutableStateOf("") }
        var goalNotes by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showCreateGoalDialog = false },
            title = { Text("Plant a New Savings Goal") },
            text = {
                Column {
                    OutlinedTextField(
                        value = goalName,
                        onValueChange = { goalName = it },
                        label = { Text("Goal Name *") },
                        placeholder = { Text("e.g. New Tablet, Guitar, Trip") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().testTag("input_goal_name")
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = targetAmountText,
                        onValueChange = { targetAmountText = it },
                        label = { Text("Target Amount (₹) *") },
                        leadingIcon = { Text("₹", fontWeight = FontWeight.Bold) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().testTag("input_goal_target")
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = goalNotes,
                        onValueChange = { goalNotes = it },
                        label = { Text("Notes (Optional)") },
                        placeholder = { Text("Why this goal matters to you") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val targetPaise = AccountingEngine.parseRupeesToPaise(targetAmountText)
                        if (goalName.isNotBlank() && targetPaise > 0L) {
                            onCreateGoal(
                                goalName.trim(),
                                targetPaise,
                                null,
                                PlantType.SPROUT,
                                goalNotes.ifBlank { null }
                            )
                            showCreateGoalDialog = false
                        }
                    },
                    enabled = goalName.isNotBlank() && targetAmountText.isNotBlank()
                ) {
                    Text("Plant Seed")
                }
            },
            dismissButton = {
                TextButton(onClick = { showCreateGoalDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Contribute / Withdraw Movement Dialog
    if (selectedGoalForMovement != null) {
        val goal = selectedGoalForMovement!!

        AlertDialog(
            onDismissRequest = { selectedGoalForMovement = null },
            title = {
                Text(if (isMovementContribution) "Water & Grow Goal" else "Withdraw from Goal")
            },
            text = {
                Column {
                    Text(
                        text = "Goal: ${goal.name}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "Current saved: ${AccountingEngine.formatPaise(goal.savedAmountPaise)} of ${AccountingEngine.formatPaise(goal.targetAmountPaise)}",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    OutlinedTextField(
                        value = movementAmountText,
                        onValueChange = { movementAmountText = it },
                        label = { Text(if (isMovementContribution) "Contribution Amount (₹)" else "Withdrawal Amount (₹)") },
                        leadingIcon = { Text("₹", fontWeight = FontWeight.Bold) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().testTag("input_goal_movement_amount")
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val amountPaise = AccountingEngine.parseRupeesToPaise(movementAmountText)
                        if (amountPaise > 0L) {
                            if (isMovementContribution) {
                                onContribute(goal.id, amountPaise, null)
                            } else {
                                onWithdraw(goal.id, amountPaise, null)
                            }
                            selectedGoalForMovement = null
                        }
                    },
                    enabled = movementAmountText.isNotBlank()
                ) {
                    Text(if (isMovementContribution) "Contribute" else "Withdraw")
                }
            },
            dismissButton = {
                TextButton(onClick = { selectedGoalForMovement = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun GoalCardItem(
    goal: SavingsGoal,
    onContributeClick: () -> Unit,
    onWithdrawClick: () -> Unit
) {
    val ratio = if (goal.targetAmountPaise > 0) {
        goal.savedAmountPaise.toFloat() / goal.targetAmountPaise.toFloat()
    } else 0f
    val percent = (ratio * 100).toInt().coerceIn(0, 100)

    val stageLabel = when (goal.plantStage) {
        1 -> "Stage 1: Seed in Soil 🌰"
        2 -> "Stage 2: Tender Sprout 🌱"
        3 -> "Stage 3: Growing Bush 🌿"
        4 -> "Stage 4: Budding Flower 🌸"
        else -> "Stage 5: Money Tree in Bloom! 🌳"
    }

    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier
            .fillMaxWidth()
            .testTag("goal_card_${goal.id}")
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = goal.name,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = stageLabel,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold
                    )
                }

                if (goal.isCompleted) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = MaterialTheme.colorScheme.primaryContainer
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Icon(Icons.Default.EmojiEvents, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(14.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Achieved!", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                // Interactive Plant Canvas
                GardenPlantView(
                    stage = goal.plantStage,
                    size = 84.dp
                )

                Column(modifier = Modifier.weight(1f)) {
                    LinearProgressIndicator(
                        progress = { ratio.coerceIn(0f, 1f) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(10.dp)
                            .clip(RoundedCornerShape(5.dp))
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Row(
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = AccountingEngine.formatPaise(goal.savedAmountPaise),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "$percent%",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    Text(
                        text = "Target: ${AccountingEngine.formatPaise(goal.targetAmountPaise)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Action Buttons
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Button(
                    onClick = onContributeClick,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier
                        .weight(1f)
                        .testTag("btn_contribute_${goal.id}")
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Contribute")
                }

                OutlinedButton(
                    onClick = onWithdrawClick,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Default.Remove, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Withdraw")
                }
            }
        }
    }
}
