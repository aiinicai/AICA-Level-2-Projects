package com.example.ui.components

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ElectricBolt
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
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
import com.example.data.model.Project
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.SapphirePrimary
import kotlin.math.roundToInt

@Composable
fun PushProjectProgressDialog(
    project: Project,
    defaultActorName: String? = null,
    onDismiss: () -> Unit,
    onPushProgress: (newProgress: Int, remark: String, actorName: String) -> Unit
) {
    var progressVal by remember { mutableFloatStateOf(project.progressPercentage.toFloat()) }
    var remarkText by remember { mutableStateOf(project.lastUpdateRemark.ifEmpty { "Milestone completed; data validated." }) }
    var actorNameText by remember { mutableStateOf(defaultActorName ?: project.leadMemberName.ifEmpty { "Mahesh" }) }

    val parsedColor = try {
        Color(android.graphics.Color.parseColor(project.colorHex))
    } catch (e: Exception) {
        SapphirePrimary
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("push_project_progress_dialog"),
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(parsedColor.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Speed,
                        contentDescription = null,
                        tint = parsedColor,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Column {
                    Text(
                        text = "Push Project Progress",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "${project.name} [${project.code}]",
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
                verticalArrangement = Arrangement.spacedBy(14.dp)
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
                                text = "Project Completion Status",
                                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                            )
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = if (progressVal.roundToInt() == 100) EmeraldSuccess else parsedColor
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
                            onValueChange = { progressVal = it },
                            valueRange = 0f..100f,
                            steps = 19,
                            modifier = Modifier.testTag("project_progress_slider"),
                            colors = SliderDefaults.colors(
                                thumbColor = parsedColor,
                                activeTrackColor = parsedColor
                            )
                        )

                        // Quick Snap buttons
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            listOf(0, 25, 50, 75, 100).forEach { pct ->
                                TextButton(
                                    onClick = { progressVal = pct.toFloat() },
                                    modifier = Modifier.testTag("project_snap_${pct}")
                                ) {
                                    Text("$pct%", fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }

                // Remark
                OutlinedTextField(
                    value = remarkText,
                    onValueChange = { remarkText = it },
                    label = { Text("Milestone Update / Executive Remark") },
                    placeholder = { Text("E.g. Phase 2 audit complete, client signed off on financials") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("project_remark_input"),
                    minLines = 2,
                    maxLines = 4
                )

                // Actor Name
                OutlinedTextField(
                    value = actorNameText,
                    onValueChange = { actorNameText = it },
                    label = { Text("Updated By (Lead / Manager)") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("project_actor_input"),
                    singleLine = true
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onPushProgress(
                        progressVal.roundToInt(),
                        remarkText.trim(),
                        actorNameText.trim().ifEmpty { "Project Lead" }
                    )
                    onDismiss()
                },
                modifier = Modifier.testTag("confirm_push_project_progress_btn"),
                colors = ButtonDefaults.buttonColors(containerColor = parsedColor)
            ) {
                Icon(Icons.Default.ElectricBolt, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("Broadcast Milestone")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("cancel_push_project_progress_btn")
            ) {
                Text("Cancel")
            }
        }
    )
}
