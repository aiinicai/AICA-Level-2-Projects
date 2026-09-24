package com.example.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Http
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Public
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.IntegrationType
import com.example.data.model.PortalIntegration

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConfigurePortalDialog(
    portalToEdit: PortalIntegration? = null,
    onDismiss: () -> Unit,
    onSave: (portal: PortalIntegration) -> Unit
) {
    val isEditMode = portalToEdit != null

    var name by remember { mutableStateOf(portalToEdit?.name ?: "") }
    var selectedType by remember { mutableStateOf(portalToEdit?.type ?: IntegrationType.GST) }
    var portalUrl by remember { mutableStateOf(portalToEdit?.portalUrl ?: "https://") }
    var webhookUrl by remember { mutableStateOf(portalToEdit?.webhookUrl ?: "") }
    var apiKeyOrClientId by remember { mutableStateOf(portalToEdit?.apiKeyOrClientId ?: "") }
    var description by remember { mutableStateOf(portalToEdit?.description ?: "") }
    var isEnabled by remember { mutableStateOf(portalToEdit?.isEnabled ?: true) }

    var typeDropdownExpanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.testTag("configure_portal_dialog"),
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Public,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(28.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = if (isEditMode) "Edit Portal Integration" else "Connect Website or Portal",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "Configures external portal access, webhooks, and API keys",
                        style = MaterialTheme.typography.bodySmall.copy(
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 11.sp
                        )
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
                // Portal Name
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Portal / Service Name *") },
                    placeholder = { Text("e.g. GST Common Portal, State Tax Desk") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("portal_name_input"),
                    singleLine = true
                )

                // Integration Type Dropdown
                ExposedDropdownMenuBox(
                    expanded = typeDropdownExpanded,
                    onExpandedChange = { typeDropdownExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedType.displayName,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Integration Category *") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = typeDropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                            .testTag("portal_type_dropdown")
                    )

                    ExposedDropdownMenu(
                        expanded = typeDropdownExpanded,
                        onDismissRequest = { typeDropdownExpanded = false }
                    ) {
                        IntegrationType.entries.forEach { typeOption ->
                            DropdownMenuItem(
                                text = { Text(typeOption.displayName, fontSize = 13.sp) },
                                onClick = {
                                    selectedType = typeOption
                                    typeDropdownExpanded = false
                                }
                            )
                        }
                    }
                }

                // Portal Website URL
                OutlinedTextField(
                    value = portalUrl,
                    onValueChange = { portalUrl = it },
                    label = { Text("Website / Portal Access URL *") },
                    placeholder = { Text("https://www.gst.gov.in") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("portal_url_input"),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Language, contentDescription = null) }
                )

                // Webhook / API Endpoint
                OutlinedTextField(
                    value = webhookUrl,
                    onValueChange = { webhookUrl = it },
                    label = { Text("API Webhook / Dispatch Endpoint") },
                    placeholder = { Text("https://api.yourdomain.com/webhook") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("portal_webhook_input"),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Http, contentDescription = null) }
                )

                // API Key / Client ID / Token
                OutlinedTextField(
                    value = apiKeyOrClientId,
                    onValueChange = { apiKeyOrClientId = it },
                    label = { Text("Client ID / API Auth Token") },
                    placeholder = { Text("e.g. AUTH_KEY_SEC_992") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("portal_apikey_input"),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Key, contentDescription = null) }
                )

                // Description
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Purpose & Instructions") },
                    placeholder = { Text("e.g. Used for monthly GSTR-1 filings and ITC reconciliation") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(85.dp),
                    maxLines = 3
                )

                // Enable toggle
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(
                            text = "Enable Integration Gateway",
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold)
                        )
                        Text(
                            text = "Allows quick-launch and automatic compliance sync",
                            style = MaterialTheme.typography.bodySmall.copy(
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 11.sp
                            )
                        )
                    }
                    Switch(
                        checked = isEnabled,
                        onCheckedChange = { isEnabled = it },
                        modifier = Modifier.testTag("portal_enable_switch")
                    )
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank() && portalUrl.isNotBlank()) {
                        val portal = PortalIntegration(
                            id = portalToEdit?.id ?: 0,
                            name = name.trim(),
                            type = selectedType,
                            portalUrl = portalUrl.trim(),
                            webhookUrl = webhookUrl.trim(),
                            apiKeyOrClientId = apiKeyOrClientId.trim(),
                            isEnabled = isEnabled,
                            statusText = if (isEnabled) "Active Gateway" else "Disabled",
                            description = description.trim()
                        )
                        onSave(portal)
                    }
                },
                enabled = name.isNotBlank() && portalUrl.isNotBlank(),
                modifier = Modifier.testTag("save_portal_btn")
            ) {
                Text(if (isEditMode) "Save Configuration" else "Connect Portal")
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
