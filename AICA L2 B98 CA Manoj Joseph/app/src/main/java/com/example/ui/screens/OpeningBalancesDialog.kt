package com.example.ui.screens

import android.app.DatePickerDialog
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.example.data.model.FinancialAccount
import com.example.data.model.Friend
import com.example.domain.AccountingEngine
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

@Composable
fun OpeningBalancesDialog(
    accounts: List<FinancialAccount>,
    friends: List<Friend>,
    userName: String = "You",
    onDismiss: () -> Unit,
    onSaveOpeningBalances: (
        asOfDate: Long,
        accountBalances: Map<Long, Long>,
        friendReceivables: Map<Long, Long>,
        friendPayables: Map<Long, Long>
    ) -> Unit,
    onNullifyAllData: () -> Unit,
    onAddFriend: (String) -> Unit = {}
) {
    val context = LocalContext.current
    val sdf = remember { SimpleDateFormat("dd MMMM yyyy", Locale.US) }

    val initialDate = remember(accounts) {
        accounts.firstOrNull { it.openingDate > 0L }?.openingDate ?: System.currentTimeMillis()
    }
    var asOfDateMillis by remember(initialDate) { mutableLongStateOf(initialDate) }
    var showNullifyConfirm by remember { mutableStateOf(false) }
    var showAddFriendDialog by remember { mutableStateOf(false) }
    var newFriendName by remember { mutableStateOf("") }

    // Account inputs (accountId -> text)
    val accountInputs = remember {
        mutableStateMapOf<Long, String>().apply {
            accounts.forEach { acc ->
                this[acc.id] = if (acc.openingBalancePaise > 0L) (acc.openingBalancePaise / 100.0).toString() else ""
            }
        }
    }

    // Friend inputs (friendId -> receivableText / payableText)
    val friendRecInputs = remember {
        mutableStateMapOf<Long, String>().apply {
            friends.forEach { f ->
                this[f.id] = if (f.openingReceivablePaise > 0L) (f.openingReceivablePaise / 100.0).toString() else ""
            }
        }
    }

    val friendPayInputs = remember {
        mutableStateMapOf<Long, String>().apply {
            friends.forEach { f ->
                this[f.id] = if (f.openingPayablePaise > 0L) (f.openingPayablePaise / 100.0).toString() else ""
            }
        }
    }

    androidx.compose.runtime.LaunchedEffect(friends) {
        friends.forEach { f ->
            if (!friendRecInputs.containsKey(f.id)) {
                friendRecInputs[f.id] = if (f.openingReceivablePaise > 0L) (f.openingReceivablePaise / 100.0).toString() else ""
            }
            if (!friendPayInputs.containsKey(f.id)) {
                friendPayInputs[f.id] = if (f.openingPayablePaise > 0L) (f.openingPayablePaise / 100.0).toString() else ""
            }
        }
    }

    androidx.compose.runtime.LaunchedEffect(accounts) {
        accounts.forEach { acc ->
            accountInputs[acc.id] = if (acc.openingBalancePaise > 0L) (acc.openingBalancePaise / 100.0).toString() else ""
        }
    }

    // Date picker dialog
    val calendar = remember(asOfDateMillis) {
        Calendar.getInstance().apply { timeInMillis = asOfDateMillis }
    }
    val datePickerDialog = remember(context, asOfDateMillis) {
        DatePickerDialog(
            context,
            { _, year, month, dayOfMonth ->
                val newCal = Calendar.getInstance().apply {
                    set(Calendar.YEAR, year)
                    set(Calendar.MONTH, month)
                    set(Calendar.DAY_OF_MONTH, dayOfMonth)
                    set(Calendar.HOUR_OF_DAY, 0)
                    set(Calendar.MINUTE, 0)
                    set(Calendar.SECOND, 0)
                }
                asOfDateMillis = newCal.timeInMillis
            },
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH),
            calendar.get(Calendar.DAY_OF_MONTH)
        )
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            shape = RoundedCornerShape(24.dp),
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 6.dp,
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .padding(vertical = 16.dp)
                .testTag("opening_balances_dialog")
        ) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                // Header
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column {
                        Text(
                            text = "Opening Balances Setup",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Establish or change initial Cash, Bank & Friend dues",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close")
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Date Picker for As of Date
                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { datePickerDialog.show() }
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp)
                    ) {
                        Column {
                            Text("As of Date:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = sdf.format(Date(asOfDateMillis)),
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }

                        Button(
                            onClick = { datePickerDialog.show() },
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.testTag("btn_pick_opening_date")
                        ) {
                            Icon(Icons.Default.DateRange, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Select Date")
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // 1. CASH & BANK ACCOUNTS
                Text(
                    text = "1. Cash & Bank Opening Balances",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.height(6.dp))

                accounts.forEach { acc ->
                    OutlinedTextField(
                        value = accountInputs[acc.id] ?: "",
                        onValueChange = { accountInputs[acc.id] = it },
                        label = { Text("${acc.name} (₹)") },
                        placeholder = { Text("0.00") },
                        leadingIcon = { Text("₹", fontWeight = FontWeight.Bold) },
                        singleLine = true,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                            .testTag("input_opening_account_${acc.id}")
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // 2. FRIENDS RECEIVABLES & PAYABLES
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "2. Friends Opening Dues (As of Date)",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.secondary
                        )
                        Text(
                            text = "Did any friends owe $userName money, or did $userName owe them?",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    TextButton(
                        onClick = { showAddFriendDialog = true },
                        modifier = Modifier.testTag("btn_opening_add_friend")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Add Friend")
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))

                friends.forEach { f ->
                    Card(
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(f.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(6.dp))

                            Row(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                OutlinedTextField(
                                    value = friendRecInputs[f.id] ?: "",
                                    onValueChange = { friendRecInputs[f.id] = it },
                                    label = { Text("Owed to $userName (₹)") },
                                    placeholder = { Text("0") },
                                    singleLine = true,
                                    modifier = Modifier.weight(1f).testTag("input_opening_rec_${f.id}")
                                )

                                OutlinedTextField(
                                    value = friendPayInputs[f.id] ?: "",
                                    onValueChange = { friendPayInputs[f.id] = it },
                                    label = { Text("$userName Owes (₹)") },
                                    placeholder = { Text("0") },
                                    singleLine = true,
                                    modifier = Modifier.weight(1f).testTag("input_opening_pay_${f.id}")
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Save Opening Balances Button
                Button(
                    onClick = {
                        val accBalances = mutableMapOf<Long, Long>()
                        for ((accId, text) in accountInputs) {
                            accBalances[accId] = AccountingEngine.parseRupeesToPaise(text)
                        }

                        val friendRec = mutableMapOf<Long, Long>()
                        for ((fId, text) in friendRecInputs) {
                            friendRec[fId] = AccountingEngine.parseRupeesToPaise(text)
                        }

                        val friendPay = mutableMapOf<Long, Long>()
                        for ((fId, text) in friendPayInputs) {
                            friendPay[fId] = AccountingEngine.parseRupeesToPaise(text)
                        }

                        onSaveOpeningBalances(asOfDateMillis, accBalances, friendRec, friendPay)
                        onDismiss()
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp)
                        .testTag("btn_save_opening_balances")
                ) {
                    Text("Save & Post Opening Balances", fontWeight = FontWeight.Bold)
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Nullify / Reset All Existing Data Button
                OutlinedButton(
                    onClick = { showNullifyConfirm = true },
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("btn_nullify_all_data")
                ) {
                    Icon(Icons.Default.DeleteSweep, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Nullify / Wipe All Existing Data to Zero")
                }
            }
        }
    }

    // Confirmation dialog for nullifying data
    if (showNullifyConfirm) {
        AlertDialog(
            onDismissRequest = { showNullifyConfirm = false },
            icon = { Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = { Text("Nullify All Data?") },
            text = {
                Text("This will wipe all existing transactions, journal entries, and reset all account and friend balances to ₹0.00 so you can enter fresh opening balances.")
            },
            confirmButton = {
                Button(
                    onClick = {
                        onNullifyAllData()
                        showNullifyConfirm = false
                        onDismiss()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Yes, Nullify All Data")
                }
            },
            dismissButton = {
                TextButton(onClick = { showNullifyConfirm = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Add Friend Dialog
    if (showAddFriendDialog) {
        AlertDialog(
            onDismissRequest = {
                showAddFriendDialog = false
                newFriendName = ""
            },
            title = { Text("Add Friend to Register") },
            text = {
                Column {
                    Text("Enter your friend's name to set up their opening balance dues:", style = MaterialTheme.typography.bodySmall)
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = newFriendName,
                        onValueChange = { newFriendName = it },
                        label = { Text("Friend's Name") },
                        placeholder = { Text("e.g. Rahul, Maya") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().testTag("input_new_friend_name")
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val trimmed = newFriendName.trim()
                        if (trimmed.isNotEmpty()) {
                            onAddFriend(trimmed)
                            newFriendName = ""
                            showAddFriendDialog = false
                        }
                    },
                    enabled = newFriendName.isNotBlank()
                ) {
                    Text("Add")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    showAddFriendDialog = false
                    newFriendName = ""
                }) {
                    Text("Cancel")
                }
            }
        )
    }
}
