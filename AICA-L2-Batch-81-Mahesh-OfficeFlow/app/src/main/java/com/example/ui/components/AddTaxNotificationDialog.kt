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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Campaign
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import com.example.data.model.TaxDepartment
import com.example.data.model.TaxSeverity
import com.example.ui.theme.AmberTax
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun AddTaxNotificationDialog(
    onDismiss: () -> Unit,
    onBroadcastNotification: (
        title: String,
        department: TaxDepartment,
        circularNumber: String,
        summary: String,
        keyActions: String,
        deadlineMillis: Long,
        severity: TaxSeverity,
        source: String
    ) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var department by remember { mutableStateOf(TaxDepartment.GST) }
    var circularNumber by remember { mutableStateOf("") }
    var summary by remember { mutableStateOf("") }
    var keyActions by remember { mutableStateOf("1. Check compliance eligibility\n2. Prepare reconciliation sheet\n3. File required forms") }
    var severity by remember { mutableStateOf(TaxSeverity.CRITICAL_ACTION_REQUIRED) }
    var source by remember { mutableStateOf("Central Board of Indirect Taxes & Customs (CBIC)") }
    var deadlineMillis by remember { mutableLongStateOf(System.currentTimeMillis() + (7L * 24 * 60 * 60 * 1000)) }

    val dateFormat = SimpleDateFormat("dd MMM yyyy", Locale.getDefault())

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("add_tax_notification_dialog"),
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
                        imageVector = Icons.Default.Campaign,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Column {
                    Text(
                        text = "Broadcast Tax Circular / Notice",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "Statutory GST & Income Tax Advisory",
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
                // Department Picker
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    TaxDepartment.values().forEach { dept ->
                        val isSelected = department == dept
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (isSelected) {
                                if (dept == TaxDepartment.GST) SapphirePrimary else AmberTax
                            } else MaterialTheme.colorScheme.surfaceVariant,
                            modifier = Modifier
                                .weight(1f)
                                .clickable {
                                    department = dept
                                    source = if (dept == TaxDepartment.GST) {
                                        "Central Board of Indirect Taxes & Customs (CBIC)"
                                    } else {
                                        "Central Board of Direct Taxes (CBDT)"
                                    }
                                }
                                .testTag("dept_chip_${dept.name}")
                        ) {
                            Box(
                                modifier = Modifier.padding(vertical = 8.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = if (dept == TaxDepartment.GST) "GST Compliance" else "Income Tax",
                                    color = if (isSelected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }
                }

                // Notification Title
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Circular / Subject Title *") },
                    placeholder = { Text("E.g. Extension of GSTR-3B deadline or Sec 43B(h) clarification") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("tax_title_input"),
                    singleLine = true
                )

                // Circular Number & Source
                OutlinedTextField(
                    value = circularNumber,
                    onValueChange = { circularNumber = it },
                    label = { Text("Notification / Circular No. *") },
                    placeholder = { Text("E.g. Notification No. 24/2026 - Central Tax") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("circular_no_input"),
                    singleLine = true
                )

                // Severity
                Column {
                    Text("Severity Level", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold))
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        TaxSeverity.values().forEach { sev ->
                            FilterChip(
                                selected = severity == sev,
                                onClick = { severity = sev },
                                label = {
                                    Text(
                                        text = sev.name.replace("_", " "),
                                        fontSize = 10.sp,
                                        fontWeight = if (severity == sev) FontWeight.Bold else FontWeight.Normal
                                    )
                                },
                                modifier = Modifier.testTag("severity_chip_${sev.name}")
                            )
                        }
                    }
                }

                // Deadline Presets
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Compliance Deadline", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold))
                        Text(dateFormat.format(Date(deadlineMillis)), fontWeight = FontWeight.Bold, color = AmberTax)
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        val day = 24L * 60 * 60 * 1000
                        val now = System.currentTimeMillis()
                        listOf("+3 Days" to now + 3 * day, "+7 Days" to now + 7 * day, "+15 Days" to now + 15 * day, "+30 Days" to now + 30 * day).forEach { (label, time) ->
                            FilterChip(
                                selected = (deadlineMillis / day) == (time / day),
                                onClick = { deadlineMillis = time },
                                label = { Text(label, fontSize = 10.sp) }
                            )
                        }
                    }
                }

                // Summary
                OutlinedTextField(
                    value = summary,
                    onValueChange = { summary = it },
                    label = { Text("Notification Summary & Legal Impact") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("tax_summary_input"),
                    minLines = 3,
                    maxLines = 5
                )

                // Key Action Items
                OutlinedTextField(
                    value = keyActions,
                    onValueChange = { keyActions = it },
                    label = { Text("Required Office Action Items") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("tax_actions_input"),
                    minLines = 2,
                    maxLines = 4
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (title.isNotBlank() && circularNumber.isNotBlank()) {
                        onBroadcastNotification(
                            title.trim(),
                            department,
                            circularNumber.trim(),
                            summary.trim().ifEmpty { "Statutory tax circular issued for immediate office compliance." },
                            keyActions.trim(),
                            deadlineMillis,
                            severity,
                            source.trim()
                        )
                        onDismiss()
                    }
                },
                enabled = title.isNotBlank() && circularNumber.isNotBlank(),
                modifier = Modifier.testTag("submit_broadcast_tax_btn"),
                colors = ButtonDefaults.buttonColors(containerColor = AmberTax)
            ) {
                Icon(
                    imageVector = Icons.Default.Campaign,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text("Broadcast Alert")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                modifier = Modifier.testTag("cancel_tax_broadcast_btn")
            ) {
                Text("Cancel")
            }
        }
    )
}
