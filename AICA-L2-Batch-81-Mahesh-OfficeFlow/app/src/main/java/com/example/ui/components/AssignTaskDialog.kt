package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AssignmentInd
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
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
import com.example.data.model.TaskCategory
import com.example.data.model.TaskPriority
import com.example.data.model.TeamMember
import com.example.ui.theme.AmberTax
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun AssignTaskDialog(
    teamMembers: List<TeamMember>,
    projects: List<Project>,
    initialDueDateMillis: Long = System.currentTimeMillis() + (3L * 24 * 60 * 60 * 1000),
    prefilledCategory: TaskCategory? = null,
    assignedBy: String = "Mahesh",
    onDismiss: () -> Unit,
    onAssignTask: (
        title: String,
        description: String,
        member: TeamMember,
        project: Project?,
        priority: TaskPriority,
        dueDateMillis: Long,
        category: TaskCategory,
        checklist: String,
        tags: String,
        assignedBy: String
    ) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var selectedMember by remember { mutableStateOf(teamMembers.firstOrNull()) }
    var selectedProject by remember { mutableStateOf(projects.firstOrNull()) }
    var selectedPriority by remember { mutableStateOf(TaskPriority.HIGH) }
    var selectedCategory by remember { mutableStateOf(prefilledCategory ?: TaskCategory.GST_COMPLIANCE) }
    var dueDateMillis by remember { mutableLongStateOf(initialDueDateMillis) }
    var checklistText by remember { mutableStateOf("1. Collect source invoices\n2. Verify ledger entries\n3. Finalize review & DSC signoff") }
    var assignedByName by remember { mutableStateOf(assignedBy) }

    // Tags state
    var customTags by remember { mutableStateOf(listOf("Compliance", "Audit2024")) }
    var tagInput by remember { mutableStateOf("") }

    val suggestedTags = listOf(
        "GST-Refund", "AdvanceTax", "TDS-26Q", "MSME-43Bh",
        "Rule37A", "ITR-Filing", "Statutory", "MonthlyClose"
    )

    var memberDropdownExpanded by remember { mutableStateOf(false) }
    var projectDropdownExpanded by remember { mutableStateOf(false) }

    val dateFormat = SimpleDateFormat("dd MMM yyyy", Locale.getDefault())

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("assign_task_dialog"),
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(SapphirePrimary),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.AssignmentInd,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Column {
                    Text(
                        text = "Assign New Office Task",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "Role-based dispatch, priority & custom tagging",
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
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
                // Task Title
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Task Title *") },
                    placeholder = { Text("E.g. File GSTR-3B for August, MSME 43B(h) Audit") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("task_title_input"),
                    singleLine = true
                )

                // Category Selection Chips
                Column {
                    Text(
                        text = "Category / Domain",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        TaskCategory.values().forEach { cat ->
                            val isSelected = selectedCategory == cat
                            FilterChip(
                                selected = isSelected,
                                onClick = { selectedCategory = cat },
                                label = {
                                    Text(
                                        text = cat.name.replace("_", " "),
                                        fontSize = 11.sp,
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                    )
                                },
                                modifier = Modifier.testTag("category_chip_${cat.name}")
                            )
                        }
                    }
                }

                // Priority Selection (Urgent, High, Medium, Low)
                Column {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Flag,
                            contentDescription = null,
                            tint = SapphirePrimary,
                            modifier = Modifier.size(16.dp)
                        )
                        Text(
                            text = "Priority Level *",
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        TaskPriority.values().forEach { prio ->
                            val isSelected = selectedPriority == prio
                            val color = when (prio) {
                                TaskPriority.LOW -> EmeraldSuccess
                                TaskPriority.MEDIUM -> SapphirePrimary
                                TaskPriority.HIGH -> AmberTax
                                TaskPriority.URGENT -> RoseUrgent
                            }
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = if (isSelected) color else MaterialTheme.colorScheme.surfaceVariant,
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable { selectedPriority = prio }
                                    .testTag("priority_chip_${prio.name}")
                            ) {
                                Box(
                                    modifier = Modifier.padding(vertical = 8.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = prio.name,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = if (isSelected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    }
                }

                // Custom Tagging System
                Column {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.LocalOffer,
                            contentDescription = null,
                            tint = SapphirePrimary,
                            modifier = Modifier.size(16.dp)
                        )
                        Text(
                            text = "Custom Tags (Categorization & Filtering)",
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))

                    // Input row for new tag
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        OutlinedTextField(
                            value = tagInput,
                            onValueChange = { tagInput = it },
                            placeholder = { Text("Enter custom tag (e.g. Audit2024)", fontSize = 12.sp) },
                            modifier = Modifier
                                .weight(1f)
                                .height(50.dp)
                                .testTag("tag_input_field"),
                            singleLine = true
                        )
                        Button(
                            onClick = {
                                val clean = tagInput.trim().replace("#", "").replace(",", "")
                                if (clean.isNotBlank() && !customTags.contains(clean)) {
                                    customTags = customTags + clean
                                    tagInput = ""
                                }
                            },
                            enabled = tagInput.isNotBlank(),
                            modifier = Modifier
                                .height(50.dp)
                                .testTag("add_tag_btn"),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = "Add Tag", modifier = Modifier.size(16.dp))
                        }
                    }

                    // Active tags chips
                    if (customTags.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(6.dp))
                        FlowRow(
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            customTags.forEach { tag ->
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = SapphirePrimary.copy(alpha = 0.18f),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, SapphirePrimary.copy(alpha = 0.4f))
                                ) {
                                    Row(
                                        modifier = Modifier.padding(start = 8.dp, end = 4.dp, top = 3.dp, bottom = 3.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = "#$tag",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                        Spacer(modifier = Modifier.width(4.dp))
                                        IconButton(
                                            onClick = { customTags = customTags.filter { it != tag } },
                                            modifier = Modifier.size(18.dp)
                                        ) {
                                            Icon(
                                                imageVector = Icons.Default.Close,
                                                contentDescription = "Remove tag $tag",
                                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                                modifier = Modifier.size(12.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Suggested quick tags
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Suggested Tags:",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        suggestedTags.forEach { sug ->
                            val alreadyAdded = customTags.contains(sug)
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = if (alreadyAdded) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                                modifier = Modifier.clickable {
                                    if (alreadyAdded) {
                                        customTags = customTags.filter { it != sug }
                                    } else {
                                        customTags = customTags + sug
                                    }
                                }
                            ) {
                                Text(
                                    text = "+ #$sug",
                                    fontSize = 10.sp,
                                    fontWeight = if (alreadyAdded) FontWeight.Bold else FontWeight.Normal,
                                    color = if (alreadyAdded) SapphirePrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }
                }

                // Assignee Selection Dropdown
                ExposedDropdownMenuBox(
                    expanded = memberDropdownExpanded,
                    onExpandedChange = { memberDropdownExpanded = !memberDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedMember?.let { "${it.name} (${it.userRole.displayName} • ${it.role})" } ?: "Select Team Member",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Assign To Member *") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = memberDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("assignee_dropdown")
                    )
                    ExposedDropdownMenu(
                        expanded = memberDropdownExpanded,
                        onDismissRequest = { memberDropdownExpanded = false }
                    ) {
                        teamMembers.forEach { member ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Text(member.name, fontWeight = FontWeight.SemiBold)
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Surface(
                                                shape = RoundedCornerShape(4.dp),
                                                color = when (member.userRole) {
                                                    com.example.data.model.UserRole.ADMIN -> RoseUrgent.copy(alpha = 0.2f)
                                                    com.example.data.model.UserRole.PARTNER -> SapphirePrimary.copy(alpha = 0.2f)
                                                    com.example.data.model.UserRole.MANAGER -> AmberTax.copy(alpha = 0.2f)
                                                    com.example.data.model.UserRole.TEAM_MEMBER -> EmeraldSuccess.copy(alpha = 0.2f)
                                                }
                                            ) {
                                                Text(
                                                    text = member.userRole.displayName,
                                                    fontSize = 9.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                                )
                                            }
                                        }
                                        Text(member.role, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                },
                                onClick = {
                                    selectedMember = member
                                    memberDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Project Selection Dropdown
                ExposedDropdownMenuBox(
                    expanded = projectDropdownExpanded,
                    onExpandedChange = { projectDropdownExpanded = !projectDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedProject?.let { "${it.name} [${it.code}]" } ?: "General Office / None",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Link to Project (Optional)") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = projectDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("project_dropdown")
                    )
                    ExposedDropdownMenu(
                        expanded = projectDropdownExpanded,
                        onDismissRequest = { projectDropdownExpanded = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("General Office / Standalone Task") },
                            onClick = {
                                selectedProject = null
                                projectDropdownExpanded = false
                            }
                        )
                        projects.forEach { proj ->
                            DropdownMenuItem(
                                text = {
                                    Column {
                                        Text(proj.name, fontWeight = FontWeight.SemiBold)
                                        Text("${proj.clientName} • ${proj.code}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                },
                                onClick = {
                                    selectedProject = proj
                                    projectDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Due Date Presets
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Due Date",
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold)
                        )
                        Text(
                            text = dateFormat.format(Date(dueDateMillis)),
                            style = MaterialTheme.typography.bodySmall.copy(
                                fontWeight = FontWeight.Bold,
                                color = SapphirePrimary
                            )
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        val day = 24L * 60 * 60 * 1000
                        val now = System.currentTimeMillis()
                        listOf(
                            "Today" to now,
                            "+2 Days" to now + 2 * day,
                            "+5 Days" to now + 5 * day,
                            "+15 Days" to now + 15 * day
                        ).forEach { (label, time) ->
                            FilterChip(
                                selected = (dueDateMillis / day) == (time / day),
                                onClick = { dueDateMillis = time },
                                label = { Text(label, fontSize = 10.sp) },
                                modifier = Modifier.testTag("due_date_preset_${label.replace(" ", "_")}")
                            )
                        }
                    }
                }

                // Milestone Checklist
                OutlinedTextField(
                    value = checklistText,
                    onValueChange = { checklistText = it },
                    label = { Text("Action Items / Checklist (1 per line)") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("checklist_input"),
                    minLines = 3,
                    maxLines = 6
                )

                // Description
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Detailed Scope / Instructions") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("task_description_input"),
                    minLines = 2,
                    maxLines = 4
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val member = selectedMember ?: teamMembers.firstOrNull()
                    if (title.isNotBlank() && member != null) {
                        onAssignTask(
                            title.trim(),
                            description.trim(),
                            member,
                            selectedProject,
                            selectedPriority,
                            dueDateMillis,
                            selectedCategory,
                            checklistText.trim(),
                            customTags.joinToString(","),
                            assignedByName.trim()
                        )
                        onDismiss()
                    }
                },
                enabled = title.isNotBlank(),
                modifier = Modifier.testTag("confirm_assign_task_btn"),
                colors = ButtonDefaults.buttonColors(containerColor = SapphirePrimary)
            ) {
                Text("Assign & Notify")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("cancel_assign_task_btn")
            ) {
                Text("Cancel")
            }
        }
    )
}

