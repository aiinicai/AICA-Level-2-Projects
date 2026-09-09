package com.example.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.MonetizationOn
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.core.model.AccountEntity
import com.example.core.model.AccountType
import com.example.core.model.Money
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionType
import com.example.ui.theme.AmberPrimary
import com.example.ui.theme.BlueAccent
import com.example.ui.theme.CrimsonPrimary
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.viewmodel.LedgerViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CashAccountsScreen(
    viewModel: LedgerViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val activeBusiness by viewModel.activeBusiness.collectAsStateWithLifecycle()
    val accounts by viewModel.accounts.collectAsStateWithLifecycle()
    val recentTxs by viewModel.recentTransactions.collectAsStateWithLifecycle()

    var showTransferDialog by remember { mutableStateOf(false) }
    var showAddAccountDialog by remember { mutableStateOf(false) }
    var showExpenseDialog by remember { mutableStateOf(false) }
    var selectedAccountForEdit by remember { mutableStateOf<AccountEntity?>(null) }

    // Edit Account Dialog
    if (selectedAccountForEdit != null) {
        EditAccountDialog(
            account = selectedAccountForEdit!!,
            canDelete = accounts.size > 1,
            onDismiss = { selectedAccountForEdit = null },
            onSave = { updatedAccount ->
                viewModel.saveAccount(updatedAccount)
                selectedAccountForEdit = null
                Toast.makeText(context, "Account updated successfully", Toast.LENGTH_SHORT).show()
            },
            onDelete = {
                viewModel.deleteAccount(selectedAccountForEdit!!.id)
                selectedAccountForEdit = null
                Toast.makeText(context, "Account deleted", Toast.LENGTH_SHORT).show()
            }
        )
    }

    // Account Transfer Dialog
    if (showTransferDialog && activeBusiness != null && accounts.size >= 2) {
        var sourceAccId by remember { mutableStateOf(accounts[0].id) }
        var targetAccId by remember { mutableStateOf(accounts[1].id) }
        var transferAmountStr by remember { mutableStateOf("") }
        var transferNotes by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showTransferDialog = false },
            title = { Text("Transfer Between Accounts", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("From Account (Source):", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        accounts.forEach { acc ->
                            FilterChip(
                                selected = sourceAccId == acc.id,
                                onClick = { sourceAccId = acc.id },
                                label = { Text(acc.name.take(14), fontSize = 11.sp) }
                            )
                        }
                    }

                    Text("To Account (Destination):", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        accounts.forEach { acc ->
                            FilterChip(
                                selected = targetAccId == acc.id,
                                onClick = { targetAccId = acc.id },
                                label = { Text(acc.name.take(14), fontSize = 11.sp) }
                            )
                        }
                    }

                    OutlinedTextField(
                        value = transferAmountStr,
                        onValueChange = { transferAmountStr = it },
                        label = { Text("Transfer Amount (₹) *") },
                        placeholder = { Text("e.g. 5000") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = transferNotes,
                        onValueChange = { transferNotes = it },
                        label = { Text("Notes / Reason (Optional)") },
                        placeholder = { Text("e.g. Cash deposit to bank") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val amountPaise = Money.rupeesToPaise(transferAmountStr)
                        if (amountPaise <= 0) {
                            Toast.makeText(context, "Please enter a valid transfer amount", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        if (sourceAccId == targetAccId) {
                            Toast.makeText(context, "Source and destination accounts must be different", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        viewModel.transferBetweenAccounts(sourceAccId, targetAccId, amountPaise, transferNotes.trim().takeIf { it.isNotEmpty() })
                        showTransferDialog = false
                        Toast.makeText(context, "Transfer completed successfully", Toast.LENGTH_SHORT).show()
                    }
                ) {
                    Text("Confirm Transfer")
                }
            },
            dismissButton = {
                TextButton(onClick = { showTransferDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Add Direct Expense Dialog
    if (showExpenseDialog && activeBusiness != null) {
        var expenseAmountStr by remember { mutableStateOf("") }
        var expenseDesc by remember { mutableStateOf("") }
        var expenseAccId by remember { mutableStateOf(accounts.firstOrNull()?.id ?: "") }

        AlertDialog(
            onDismissRequest = { showExpenseDialog = false },
            title = { Text("Record Business Expense", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = expenseAmountStr,
                        onValueChange = { expenseAmountStr = it },
                        label = { Text("Expense Amount (₹) *") },
                        placeholder = { Text("e.g. 1500") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = expenseDesc,
                        onValueChange = { expenseDesc = it },
                        label = { Text("Expense Description *") },
                        placeholder = { Text("e.g. Shop electricity / Tea & Snacks") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    Text("Paid From Account:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        accounts.forEach { acc ->
                            FilterChip(
                                selected = expenseAccId == acc.id,
                                onClick = { expenseAccId = acc.id },
                                label = { Text(acc.name.take(14), fontSize = 11.sp) }
                            )
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val amountPaise = Money.rupeesToPaise(expenseAmountStr)
                        if (amountPaise <= 0 || expenseDesc.isBlank()) {
                            Toast.makeText(context, "Please enter amount and description", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        val tx = TransactionEntity(
                            businessId = activeBusiness!!.id,
                            partyId = null,
                            accountId = expenseAccId.takeIf { it.isNotEmpty() },
                            type = TransactionType.EXPENSE.name,
                            amountPaise = amountPaise,
                            notes = expenseDesc.trim()
                        )
                        viewModel.postTransaction(tx) {
                            Toast.makeText(context, "Expense recorded", Toast.LENGTH_SHORT).show()
                            showExpenseDialog = false
                        }
                    }
                ) {
                    Text("Save Expense")
                }
            },
            dismissButton = {
                TextButton(onClick = { showExpenseDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Add Account Dialog
    if (showAddAccountDialog && activeBusiness != null) {
        var accName by remember { mutableStateOf("") }
        var accType by remember { mutableStateOf("BANK") }
        var accNum by remember { mutableStateOf("") }
        var ifsc by remember { mutableStateOf("") }
        var upiId by remember { mutableStateOf("") }
        var openBal by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showAddAccountDialog = false },
            title = { Text("Add Payment Account", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = accName,
                        onValueChange = { accName = it },
                        label = { Text("Account Name *") },
                        placeholder = { Text("e.g. SBI Current A/C / Paytm Wallet") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    Text("Account Type:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf("CASH" to "Cash", "BANK" to "Bank", "UPI" to "UPI").forEach { (typeKey, typeLabel) ->
                            FilterChip(
                                selected = accType == typeKey,
                                onClick = { accType = typeKey },
                                label = { Text(typeLabel) }
                            )
                        }
                    }

                    if (accType == "BANK") {
                        OutlinedTextField(
                            value = accNum,
                            onValueChange = { accNum = it },
                            label = { Text("Account Number (Optional)") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        OutlinedTextField(
                            value = ifsc,
                            onValueChange = { ifsc = it },
                            label = { Text("IFSC Code (Optional)") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    } else if (accType == "UPI") {
                        OutlinedTextField(
                            value = upiId,
                            onValueChange = { upiId = it },
                            label = { Text("UPI ID (Optional)") },
                            placeholder = { Text("shopname@upi") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    OutlinedTextField(
                        value = openBal,
                        onValueChange = { openBal = it },
                        label = { Text("Opening Balance (₹)") },
                        placeholder = { Text("0") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (accName.isBlank()) {
                            Toast.makeText(context, "Account name is required", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        val acc = AccountEntity(
                            businessId = activeBusiness!!.id,
                            name = accName.trim(),
                            type = accType,
                            accountNumber = accNum.trim().takeIf { it.isNotEmpty() },
                            ifscCode = ifsc.trim().takeIf { it.isNotEmpty() },
                            upiId = upiId.trim().takeIf { it.isNotEmpty() },
                            openingBalancePaise = Money.rupeesToPaise(openBal)
                        )
                        viewModel.saveAccount(acc)
                        showAddAccountDialog = false
                        Toast.makeText(context, "Account created", Toast.LENGTH_SHORT).show()
                    }
                ) {
                    Text("Save Account")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddAccountDialog = false }) { Text("Cancel") }
            }
        )
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showExpenseDialog = true },
                containerColor = CrimsonPrimary,
                contentColor = Color.White
            ) {
                Row(modifier = Modifier.padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Receipt, contentDescription = null)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Record Expense", fontWeight = FontWeight.Bold)
                }
            }
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Spacer(modifier = Modifier.height(4.dp))
                // Quick Action Bar: Transfer & Add Account
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    OutlinedButton(
                        onClick = { showTransferDialog = true },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.SwapHoriz, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Transfer", fontWeight = FontWeight.Bold)
                    }

                    Button(
                        onClick = { showAddAccountDialog = true },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Add Account", fontWeight = FontWeight.Bold)
                    }
                }
            }

            item {
                Text(
                    text = "Cash & Bank Accounts",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }

            items(accounts) { account ->
                val calculatedBalance = viewModel.repository.calculateAccountBalance(account, recentTxs)
                val icon = when (account.type) {
                    "CASH" -> Icons.Default.MonetizationOn
                    "BANK" -> Icons.Default.AccountBalance
                    "UPI" -> Icons.Default.QrCode
                    else -> Icons.Default.MonetizationOn
                }

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { selectedAccountForEdit = account },
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.weight(1f)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer)
                            }

                            Spacer(modifier = Modifier.width(12.dp))

                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(account.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                }
                                if (!account.accountNumber.isNullOrEmpty()) {
                                    Text("A/C: ${account.accountNumber}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                } else if (!account.upiId.isNullOrEmpty()) {
                                    Text("UPI: ${account.upiId}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                } else {
                                    Text(account.type, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                Text("Tap to edit details", fontSize = 10.sp, color = MaterialTheme.colorScheme.primary)
                            }
                        }

                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                text = Money.formatIndianPaise(calculatedBalance),
                                fontSize = 18.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = if (calculatedBalance >= 0) EmeraldPrimary else CrimsonPrimary
                            )
                            Text(
                                text = "Current Balance",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }

            item {
                Spacer(modifier = Modifier.height(80.dp))
            }
        }
    }
}
