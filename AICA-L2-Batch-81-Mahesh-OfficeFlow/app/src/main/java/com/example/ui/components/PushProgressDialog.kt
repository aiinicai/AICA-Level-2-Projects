package com.example.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Campaign
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ElectricBolt
import androidx.compose.material.icons.filled.PendingActions
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
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
import com.example.data.model.TaskItem
import com.example.data.model.TaskStatus
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.SapphirePrimary
import kotlin.math.roundToInt

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun PushProgressDialog(
    task: TaskItem,
    defaultActorName: String? = null,
    onDismiss: () -> Unit,
    onPushProgress: (progress: Int, remark: String, status: TaskStatus, completedChecklist: Int, actorName: String) -> Unit
) {
    var progressVal by remember { mutableFloatStateOf(task.progressPercentage.toFloat()) }
    var selectedStatus by remember { mutableStateOf(task.status) }
    var remarkText by remember { mutableStateOf(task.lastProgressRemark.ifEmpty { "Work milestone reached and verified." }) }
    var actorNameText by remember { mutableStateOf(defaultActorName ?: task.assignedMemberName.ifEmpty { "Mahesh" }) }
    var completedChecklist by remember { mutableIntStateOf(task.completedChecklistCount) }

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("push_progress_dialog"),
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Speed,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Column {
                    Text(
                        text = "Push Progress Update",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = task.title,
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant),
                        maxLines = 1
                    )
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Progress Slider Card
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Current Completion",
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                            )
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = if (progressVal.roundToInt() == 100) EmeraldSuccess else SapphirePrimary
                            ) {
                                Text(
                                    text = "${progressVal.roundToInt()}%",
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 12.sp,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        Slider(
                            value = progressVal,
                            onValueChange = { newVal ->
                                progressVal = newVal
                                if (newVal >= 100f) {
                                    selectedStatus = TaskStatus.COMPLETED
                                } else if (newVal > 0f && selectedStatus == TaskStatus.TODO) {
                                    selectedStatus = TaskStatus.IN_PROGRESS
                                }
                            },
                            valueRange = 0f..100f,
                            steps = 19,
                            modifier = Modifier.testTag("progress_slider"),
                            colors = SliderDefaults.colors(
                                thumbColor = SapphirePrimary,
                                activeTrackColor = SapphirePrimary
                            )
                        )

                        // Quick Snap buttons (0%, 25%, 50%, 75%, 100%)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            listOf(0, 25, 50, 75, 100).forEach { pct ->
                                TextButton(
                                    onClick = {
                                        progressVal = pct.toFloat()
                                        if (pct == 100) selectedStatus = TaskStatus.COMPLETED
                                        else if (pct > 0 && selectedStatus == TaskStatus.TODO) selectedStatus = TaskStatus.IN_PROGRESS
                                    },
                                    modifier = Modifier.testTag("quick_snap_${pct}")
                                ) {
                                    Text("$pct%", fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }

                // Status Chips
                Column {
                    Text(
                        text = "Workflow Stage",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        TaskStatus.values().forEach { status ->
                            val isSelected = selectedStatus == status
                            FilterChip(
                                selected = isSelected,
                                onClick = {
                                    selectedStatus = status
                                    if (status == TaskStatus.COMPLETED && progressVal < 100f) {
                                        progressVal = 100f
                                    }
                                },
                                label = {
                                    Text(
                                        text = status.name.replace("_", " "),
                                        fontSize = 11.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                    )
                                },
                                leadingIcon = if (isSelected) {
                                    {
                                        Icon(
                                            imageVector = Icons.Default.CheckCircle,
                                            contentDescription = null,
                                            modifier = Modifier.size(14.dp)
                                        )
                                    }
                                } else null,
                                modifier = Modifier.testTag("status_chip_${status.name}")
                            )
                        }
                    }
                }

                // Checklists completed if available
                if (task.totalChecklistCount > 0) {
                    Column {
                        Text(
                            text = "Checklist Milestones Cleared ($completedChecklist / ${task.totalChecklistCount})",
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            TextButton(
                                onClick = { if (completedChecklist > 0) completedChecklist-- }
                            ) { Text("-1") }
                            Text(
                                text = "$completedChecklist of ${task.totalChecklistCount}",
                                fontWeight = FontWeight.Bold
                            )
                            TextButton(
                                onClick = { if (completedChecklist < task.totalChecklistCount) completedChecklist++ }
                            ) { Text("+1") }
                        }
                    }
                }

                // Progress Remark
                OutlinedTextField(
                    value = remarkText,
                    onValueChange = { remarkText = it },
                    label = { Text("Progress Remark / Milestone Update") },
                    placeholder = { Text("E.g. Uploaded JSON, 95% ITC matched, draft sent to client") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("progress_remark_input"),
                    minLines = 2,
                    maxLines = 4
                )

                // Actor Name (who is pushing)
                OutlinedTextField(
                    value = actorNameText,
                    onValueChange = { actorNameText = it },
                    label = { Text("Updated By (Team Member)") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("actor_name_input"),
                    singleLine = true
                )

                // Real-time Push Notice Banner
                Surface(
                    color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.5f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Campaign,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.tertiary,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Pushing will broadcast live notification and update project dashboards instantly.",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onTertiaryContainer
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onPushProgress(
                        progressVal.roundToInt(),
                        remarkText.trim(),
                        selectedStatus,
                        completedChecklist,
                        actorNameText.trim().ifEmpty { "Team Member" }
                    )
                    onDismiss()
                },
                modifier = Modifier.testTag("submit_push_progress_btn"),
                colors = ButtonDefaults.buttonColors(containerColor = SapphirePrimary)
            ) {
                Icon(
                    imageVector = Icons.Default.ElectricBolt,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text("Push & Broadcast")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("cancel_push_progress_btn")
            ) {
                Text("Cancel")
            }
        }
    )
}
