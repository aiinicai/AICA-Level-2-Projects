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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.Project
import com.example.data.model.TaxNotification
import com.example.data.model.TeamMember
import com.example.ui.theme.AmberTax
import com.example.ui.theme.SapphirePrimary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConvertNoticeToTaskDialog(
    notification: TaxNotification,
    teamMembers: List<TeamMember>,
    projects: List<Project>,
    onDismiss: () -> Unit,
    onConvert: (TaxNotification, TeamMember, Project?) -> Unit
) {
    var selectedMember by remember { mutableStateOf(teamMembers.firstOrNull()) }
    var selectedProject by remember { mutableStateOf(projects.firstOrNull()) }

    var memberDropdownExpanded by remember { mutableStateOf(false) }
    var projectDropdownExpanded by remember { mutableStateOf(false) }

    val dateFormat = SimpleDateFormat("dd MMM yyyy", Locale.getDefault())

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("convert_notice_dialog"),
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(AmberTax),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.AssignmentTurnedIn,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Column {
                    Text(
                        text = "Create Task from Notice",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = notification.circularOrNotificationNo,
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                    )
                }
            }
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text(
                            text = notification.title,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Statutory Deadline: ${dateFormat.format(Date(notification.deadlineDateMillis))}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = AmberTax
                        )
                    }
                }

                // Member Dropdown
                ExposedDropdownMenuBox(
                    expanded = memberDropdownExpanded,
                    onExpandedChange = { memberDropdownExpanded = !memberDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedMember?.let { "${it.name} (${it.role})" } ?: "Select Member",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Assign Compliance To *") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = memberDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("convert_assignee_dropdown")
                    )
                    ExposedDropdownMenu(
                        expanded = memberDropdownExpanded,
                        onDismissRequest = { memberDropdownExpanded = false }
                    ) {
                        teamMembers.forEach { member ->
                            DropdownMenuItem(
                                text = { Text("${member.name} (${member.role})") },
                                onClick = {
                                    selectedMember = member
                                    memberDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Project Dropdown
                ExposedDropdownMenuBox(
                    expanded = projectDropdownExpanded,
                    onExpandedChange = { projectDropdownExpanded = !projectDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedProject?.let { "${it.name} [${it.code}]" } ?: "Standalone Tax Compliance",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Link to Client Project") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = projectDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("convert_project_dropdown")
                    )
                    ExposedDropdownMenu(
                        expanded = projectDropdownExpanded,
                        onDismissRequest = { projectDropdownExpanded = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Standalone Tax Compliance") },
                            onClick = {
                                selectedProject = null
                                projectDropdownExpanded = false
                            }
                        )
                        projects.forEach { proj ->
                            DropdownMenuItem(
                                text = { Text("${proj.name} [${proj.code}]") },
                                onClick = {
                                    selectedProject = proj
                                    projectDropdownExpanded = false
                                }
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val member = selectedMember ?: teamMembers.firstOrNull()
                    if (member != null) {
                        onConvert(notification, member, selectedProject)
                        onDismiss()
                    }
                },
                modifier = Modifier.testTag("confirm_convert_notice_btn"),
                colors = ButtonDefaults.buttonColors(containerColor = AmberTax)
            ) {
                Text("Create & Assign Task")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("cancel_convert_notice_btn")
            ) {
                Text("Cancel")
            }
        }
    )
}
