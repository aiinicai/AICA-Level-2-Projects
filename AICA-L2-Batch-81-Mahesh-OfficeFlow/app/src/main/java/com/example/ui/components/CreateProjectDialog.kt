package com.example.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.filled.CreateNewFolder
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
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
import com.example.data.model.TeamMember
import com.example.ui.theme.SapphirePrimary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateProjectDialog(
    teamMembers: List<TeamMember>,
    onDismiss: () -> Unit,
    onCreateProject: (
        name: String,
        code: String,
        clientName: String,
        description: String,
        leadName: String,
        targetDateMillis: Long,
        category: String,
        colorHex: String
    ) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var clientName by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var selectedLead by remember { mutableStateOf(teamMembers.firstOrNull()?.name ?: "Mahesh") }
    var targetDateMillis by remember { mutableLongStateOf(System.currentTimeMillis() + (30L * 24 * 60 * 60 * 1000)) }
    var selectedCategory by remember { mutableStateOf("Tax & Audit") }
    var selectedColorHex by remember { mutableStateOf("#2563EB") }

    var leadDropdownExpanded by remember { mutableStateOf(false) }
    val dateFormat = SimpleDateFormat("dd MMM yyyy", Locale.getDefault())

    val colors = listOf(
        "#2563EB" to "Sapphire",
        "#0D9488" to "Teal",
        "#D97706" to "Amber",
        "#7C3AED" to "Purple",
        "#DC2626" to "Rose",
        "#059669" to "Emerald"
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("create_project_dialog"),
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
                        imageVector = Icons.Default.CreateNewFolder,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Column {
                    Text(
                        text = "New Office Project",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "Track deliverables, milestones & progress",
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
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = {
                        name = it
                        if (code.isEmpty() && it.length >= 3) {
                            code = "PRJ-" + it.take(3).uppercase() + "-${(10..99).random()}"
                        }
                    },
                    label = { Text("Project Title *") },
                    placeholder = { Text("E.g. Q3 Statutory Audit & Tax Return") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("project_name_input"),
                    singleLine = true
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = code,
                        onValueChange = { code = it },
                        label = { Text("Code *") },
                        modifier = Modifier
                            .weight(1f)
                            .testTag("project_code_input"),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = clientName,
                        onValueChange = { clientName = it },
                        label = { Text("Client / Entity *") },
                        modifier = Modifier
                            .weight(1.5f)
                            .testTag("client_name_input"),
                        singleLine = true
                    )
                }

                // Lead Member Selector
                ExposedDropdownMenuBox(
                    expanded = leadDropdownExpanded,
                    onExpandedChange = { leadDropdownExpanded = !leadDropdownExpanded }
                ) {
                    OutlinedTextField(
                        value = selectedLead,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Project Lead *") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = leadDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("lead_dropdown")
                    )
                    ExposedDropdownMenu(
                        expanded = leadDropdownExpanded,
                        onDismissRequest = { leadDropdownExpanded = false }
                    ) {
                        teamMembers.forEach { member ->
                            DropdownMenuItem(
                                text = { Text("${member.name} (${member.role})") },
                                onClick = {
                                    selectedLead = member.name
                                    leadDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Domain Category
                Column {
                    Text("Domain", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold))
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("GST Compliance", "Income Tax", "Internal Audit", "Corporate").forEach { cat ->
                            FilterChip(
                                selected = selectedCategory == cat,
                                onClick = { selectedCategory = cat },
                                label = { Text(cat, fontSize = 10.sp) }
                            )
                        }
                    }
                }

                // Accent Color
                Column {
                    Text("Theme Accent", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold))
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        colors.forEach { (hex, _) ->
                            val color = try {
                                Color(android.graphics.Color.parseColor(hex))
                            } catch (e: Exception) {
                                SapphirePrimary
                            }
                            val isSelected = selectedColorHex == hex
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .clip(CircleShape)
                                    .background(color)
                                    .clickable { selectedColorHex = hex }
                                    .padding(4.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                if (isSelected) {
                                    Box(
                                        modifier = Modifier
                                            .size(10.dp)
                                            .clip(CircleShape)
                                            .background(Color.White)
                                    )
                                }
                            }
                        }
                    }
                }

                // Description
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Scope & Objectives") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("project_desc_input"),
                    minLines = 2,
                    maxLines = 4
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank() && code.isNotBlank()) {
                        onCreateProject(
                            name.trim(),
                            code.trim(),
                            clientName.trim().ifEmpty { "Internal Office" },
                            description.trim(),
                            selectedLead,
                            targetDateMillis,
                            selectedCategory,
                            selectedColorHex
                        )
                        onDismiss()
                    }
                },
                enabled = name.isNotBlank() && code.isNotBlank(),
                modifier = Modifier.testTag("submit_create_project_btn"),
                colors = ButtonDefaults.buttonColors(containerColor = SapphirePrimary)
            ) {
                Text("Create Project")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("cancel_create_project_btn")
            ) {
                Text("Cancel")
            }
        }
    )
}
