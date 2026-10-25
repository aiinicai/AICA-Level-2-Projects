package com.example.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.data.model.FinancialAccount
import com.example.domain.AccountingEngine

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ReconciliationDialog(
    accounts: List<FinancialAccount>,
    onDismiss: () -> Unit,
    onConfirmReconcile: (accountId: Long, statementPaise: Long, notes: String?) -> Unit
) {
    var selectedAccountId by remember { mutableStateOf<Long?>(accounts.firstOrNull()?.id) }
    var statementBalanceText by remember { mutableStateOf("") }
    var notesText by remember { mutableStateOf("") }

    val account = accounts.find { it.id == selectedAccountId }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Account Balance Reconciliation") },
        text = {
            Column {
                Text(
                    text = "Verify that your app's ledger balance matches your real bank statement or cash in wallet.",
                    style = MaterialTheme.typography.bodySmall
                )

                Spacer(modifier = Modifier.height(10.dp))
                Text("Select Account:", style = MaterialTheme.typography.labelMedium)
                Spacer(modifier = Modifier.height(4.dp))
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    accounts.forEach { acc ->
                        FilterChip(
                            selected = selectedAccountId == acc.id,
                            onClick = { selectedAccountId = acc.id },
                            label = { Text(acc.name) }
                        )
                    }
                }

                if (account != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Ledger Balance: ${AccountingEngine.formatPaise(account.currentBalancePaise)}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = statementBalanceText,
                    onValueChange = { statementBalanceText = it },
                    label = { Text("Actual Statement / Cash Balance (₹)") },
                    leadingIcon = { Text("₹", fontWeight = FontWeight.Bold) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth().testTag("input_reconcile_balance")
                )

                Spacer(modifier = Modifier.height(10.dp))
                OutlinedTextField(
                    value = notesText,
                    onValueChange = { notesText = it },
                    label = { Text("Reconciliation Notes (Optional)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val stmtPaise = AccountingEngine.parseRupeesToPaise(statementBalanceText)
                    val accId = selectedAccountId ?: accounts.firstOrNull()?.id ?: 1L
                    onConfirmReconcile(accId, stmtPaise, notesText.ifBlank { null })
                    onDismiss()
                },
                enabled = statementBalanceText.isNotBlank()
            ) {
                Text("Verify & Reconcile")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
