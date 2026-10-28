package com.example.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import java.util.Date
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
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
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil.compose.AsyncImage
import com.example.data.model.CategoryType
import com.example.data.model.FinancialAccount
import com.example.data.model.Friend
import com.example.data.model.TransactionCategory
import com.example.domain.AccountingEngine
import com.example.ui.components.CategoryIconHelper

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun AddTransactionDialog(
    initialTab: Int = 0, // 0: Expense, 1: Income, 2: Transfer
    accounts: List<FinancialAccount>,
    categories: List<TransactionCategory>,
    friends: List<Friend>,
    userName: String = "You",
    onDismiss: () -> Unit,
    onSavePersonalExpense: (date: Long, amountPaise: Long, desc: String, accountId: Long, categoryId: Long, receiptUri: String?, notes: String?) -> Unit,
    onSaveSharedExpense: (date: Long, totalPaise: Long, arpitaPaise: Long, friendAllocations: Map<Long, Long>, desc: String, accountId: Long, categoryId: Long, receiptUri: String?, notes: String?) -> Unit,
    onSaveFriendPaidExpense: (date: Long, totalPaise: Long, arpitaPaise: Long, desc: String, friendId: Long, categoryId: Long, notes: String?) -> Unit,
    onSaveIncome: (date: Long, amountPaise: Long, desc: String, destinationAccountId: Long, categoryId: Long, notes: String?) -> Unit,
    onSaveTransfer: (date: Long, amountPaise: Long, fromAccountId: Long, toAccountId: Long, desc: String) -> Unit,
    onAddCategory: ((name: String, type: CategoryType, iconName: String, colorHex: String, onCreated: (Long) -> Unit) -> Unit)? = null
) {
    var selectedTab by remember { mutableStateOf(initialTab) }
    var showAddCategoryForType by remember { mutableStateOf<CategoryType?>(null) }
    var selectedDateMillis by remember { androidx.compose.runtime.mutableLongStateOf(System.currentTimeMillis()) }
    val context = androidx.compose.ui.platform.LocalContext.current
    val sdf = remember { java.text.SimpleDateFormat("dd MMM yyyy", java.util.Locale.US) }

    val calendar = remember(selectedDateMillis) {
        java.util.Calendar.getInstance().apply { timeInMillis = selectedDateMillis }
    }
    val datePickerDialog = remember(context, selectedDateMillis) {
        android.app.DatePickerDialog(
            context,
            { _, year, month, dayOfMonth ->
                val newCal = java.util.Calendar.getInstance().apply {
                    set(java.util.Calendar.YEAR, year)
                    set(java.util.Calendar.MONTH, month)
                    set(java.util.Calendar.DAY_OF_MONTH, dayOfMonth)
                }
                selectedDateMillis = newCal.timeInMillis
            },
            calendar.get(java.util.Calendar.YEAR),
            calendar.get(java.util.Calendar.MONTH),
            calendar.get(java.util.Calendar.DAY_OF_MONTH)
        )
    }

    // Shared input states
    var amountText by remember { mutableStateOf("") }
    var descriptionText by remember { mutableStateOf("") }
    var notesText by remember { mutableStateOf("") }
    var receiptUri by remember { mutableStateOf<String?>(null) }

    // Photo picker launcher (zero permission, modern Android standard)
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            receiptUri = uri.toString()
        }
    }

    // Expense-specific states
    var isSharedExpense by remember { mutableStateOf(false) }
    var whoPaid by remember { mutableStateOf("ARPITA") } // "ARPITA" or "FRIEND"
    var selectedPayingFriendId by remember { mutableStateOf<Long?>(friends.firstOrNull()?.id) }
    var selectedAccountId by remember { mutableStateOf<Long?>(accounts.firstOrNull()?.id) }
    var selectedDestinationAccountId by remember { mutableStateOf<Long?>(accounts.getOrNull(1)?.id ?: accounts.firstOrNull()?.id) }

    val expenseCategories = remember(categories) { categories.filter { it.type == CategoryType.EXPENSE } }
    val incomeCategories = remember(categories) { categories.filter { it.type == CategoryType.INCOME } }
    var selectedCategoryId by remember { mutableStateOf<Long?>(expenseCategories.firstOrNull()?.id) }

    // Shared split friend allocations (friendId -> amount text)
    val selectedFriendIds = remember { mutableStateMapOf<Long, Boolean>() }
    val friendAmounts = remember { mutableStateMapOf<Long, String>() }
    var arpitaShareText by remember { mutableStateOf("") }

    val totalAmountPaise = remember(amountText) { AccountingEngine.parseRupeesToPaise(amountText) }

    // Split equally helper
    fun recalculateEqualSplit() {
        val activeFriendIds = selectedFriendIds.filter { it.value }.keys.toList()
        if (activeFriendIds.isNotEmpty() && totalAmountPaise > 0L) {
            val totalPeople = activeFriendIds.size + 1
            val equalShare = totalAmountPaise / totalPeople
            val arpitaShare = totalAmountPaise - (equalShare * activeFriendIds.size) // Absorbs remainder paise
            arpitaShareText = (arpitaShare / 100.0).toString()
            for (fId in activeFriendIds) {
                friendAmounts[fId] = (equalShare / 100.0).toString()
            }
        }
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
                .testTag("add_transaction_dialog")
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
                    Text(
                        text = "Record Financial Event",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close")
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Tabs: Expense, Income, Transfer
                TabRow(
                    selectedTabIndex = selectedTab,
                    containerColor = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.clip(RoundedCornerShape(12.dp))
                ) {
                    Tab(
                        selected = selectedTab == 0,
                        onClick = {
                            selectedTab = 0
                            selectedCategoryId = expenseCategories.firstOrNull()?.id
                        },
                        text = { Text("Expense") },
                        modifier = Modifier.testTag("tab_expense")
                    )
                    Tab(
                        selected = selectedTab == 1,
                        onClick = {
                            selectedTab = 1
                            selectedCategoryId = incomeCategories.firstOrNull()?.id
                        },
                        text = { Text("Income") },
                        modifier = Modifier.testTag("tab_income")
                    )
                    Tab(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        text = { Text("Transfer") },
                        modifier = Modifier.testTag("tab_transfer")
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Transaction Date Picker
                Card(
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { datePickerDialog.show() }
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 14.dp, vertical = 6.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Default.DateRange,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Date: ${sdf.format(Date(selectedDateMillis))}",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        TextButton(
                            onClick = { datePickerDialog.show() },
                            modifier = Modifier.testTag("btn_select_tx_date")
                        ) {
                            Text("Change Date")
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Amount Input
                OutlinedTextField(
                    value = amountText,
                    onValueChange = {
                        amountText = it
                        if (isSharedExpense) recalculateEqualSplit()
                    },
                    label = { Text("Total Amount (₹)") },
                    placeholder = { Text("e.g. 500 or 1250.50") },
                    leadingIcon = { Text("₹", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold) },
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("input_amount")
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Description
                OutlinedTextField(
                    value = descriptionText,
                    onValueChange = { descriptionText = it },
                    label = { Text("Description") },
                    placeholder = {
                        Text(
                            when (selectedTab) {
                                0 -> "e.g. Lunch at Cafe, Bus pass, Books"
                                1 -> "e.g. Weekly pocket money, Birthday gift"
                                else -> "e.g. Bank transfer to cash"
                            }
                        )
                    },
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("input_description")
                )

                Spacer(modifier = Modifier.height(16.dp))

                when (selectedTab) {
                    0 -> { // EXPENSE WORKFLOW
                        // Category Selection
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Category", style = MaterialTheme.typography.labelMedium)
                            if (onAddCategory != null) {
                                TextButton(
                                    onClick = { showAddCategoryForType = CategoryType.EXPENSE },
                                    modifier = Modifier.testTag("btn_add_expense_category")
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Add Category", style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        FlowRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            expenseCategories.forEach { cat ->
                                FilterChip(
                                    selected = selectedCategoryId == cat.id,
                                    onClick = { selectedCategoryId = cat.id },
                                    label = { Text(cat.name) },
                                    leadingIcon = {
                                        Icon(
                                            CategoryIconHelper.getIcon(cat.iconName),
                                            contentDescription = null,
                                            modifier = Modifier.size(16.dp)
                                        )
                                    }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Shared Expense Toggle
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(12.dp))
                                .padding(horizontal = 14.dp, vertical = 8.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Group, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Spacer(modifier = Modifier.width(10.dp))
                                Column {
                                    Text("Shared with Friends", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                                    Text("Split expense & track receivables", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                            Switch(
                                checked = isSharedExpense,
                                onCheckedChange = {
                                    isSharedExpense = it
                                    if (it) recalculateEqualSplit()
                                },
                                modifier = Modifier.testTag("switch_shared_expense")
                            )
                        }

                        if (!isSharedExpense) {
                            // Simple Personal Expense: Select payment account
                            Spacer(modifier = Modifier.height(12.dp))
                            Text("Paid from Account", style = MaterialTheme.typography.labelMedium)
                            Spacer(modifier = Modifier.height(6.dp))
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                accounts.forEach { acc ->
                                    FilterChip(
                                        selected = selectedAccountId == acc.id,
                                        onClick = { selectedAccountId = acc.id },
                                        label = { Text("${acc.name} (${AccountingEngine.formatPaise(acc.currentBalancePaise)})") }
                                    )
                                }
                            }
                        } else {
                            // SHARED EXPENSE CONFIGURATION
                            Spacer(modifier = Modifier.height(12.dp))
                            Text("Who Paid?", style = MaterialTheme.typography.labelMedium)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                FilterChip(
                                    selected = whoPaid == "ARPITA",
                                    onClick = { whoPaid = "ARPITA" },
                                    label = { Text("$userName Paid") }
                                )
                                FilterChip(
                                    selected = whoPaid == "FRIEND",
                                    onClick = { whoPaid = "FRIEND" },
                                    label = { Text("Friend Paid for $userName") }
                                )
                            }

                            if (whoPaid == "ARPITA") {
                                Spacer(modifier = Modifier.height(8.dp))
                                Text("Payment Account", style = MaterialTheme.typography.labelSmall)
                                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    accounts.forEach { acc ->
                                        FilterChip(
                                            selected = selectedAccountId == acc.id,
                                            onClick = { selectedAccountId = acc.id },
                                            label = { Text(acc.name) }
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(10.dp))
                                Text("Select Friends to Split With", style = MaterialTheme.typography.labelMedium)
                                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    friends.forEach { f ->
                                        val isChecked = selectedFriendIds[f.id] == true
                                        FilterChip(
                                            selected = isChecked,
                                            onClick = {
                                                selectedFriendIds[f.id] = !isChecked
                                                recalculateEqualSplit()
                                            },
                                            label = { Text(f.name) }
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedButton(
                                    onClick = { recalculateEqualSplit() },
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Split Equally Between All")
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = arpitaShareText,
                                    onValueChange = { arpitaShareText = it },
                                    label = { Text("$userName's Personal Share (₹)") },
                                    modifier = Modifier.fillMaxWidth()
                                )

                                selectedFriendIds.filter { it.value }.keys.forEach { fId ->
                                    val fName = friends.find { it.id == fId }?.name ?: "Friend"
                                    Spacer(modifier = Modifier.height(6.dp))
                                    OutlinedTextField(
                                        value = friendAmounts[fId] ?: "",
                                        onValueChange = { friendAmounts[fId] = it },
                                        label = { Text("$fName's Share (Owes $userName ₹)") },
                                        modifier = Modifier.fillMaxWidth()
                                    )
                                }
                            } else {
                                // FRIEND PAID
                                Spacer(modifier = Modifier.height(8.dp))
                                Text("Which friend paid?", style = MaterialTheme.typography.labelMedium)
                                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    friends.forEach { f ->
                                        FilterChip(
                                            selected = selectedPayingFriendId == f.id,
                                            onClick = { selectedPayingFriendId = f.id },
                                            label = { Text(f.name) }
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))
                                OutlinedTextField(
                                    value = arpitaShareText,
                                    onValueChange = { arpitaShareText = it },
                                    label = { Text("$userName's Share ($userName Owes Friend ₹)") },
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }
                        }

                        // Receipt Attachment
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            OutlinedButton(
                                onClick = { photoPickerLauncher.launch("image/*") }
                            ) {
                                Icon(Icons.Default.AttachFile, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(if (receiptUri == null) "Attach Receipt Photo" else "Change Receipt")
                            }
                            if (receiptUri != null) {
                                TextButton(onClick = { receiptUri = null }) {
                                    Text("Remove", color = MaterialTheme.colorScheme.error)
                                }
                            }
                        }

                        if (receiptUri != null) {
                            Spacer(modifier = Modifier.height(8.dp))
                            AsyncImage(
                                model = receiptUri,
                                contentDescription = "Receipt preview",
                                modifier = Modifier
                                    .size(100.dp)
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(Color.LightGray)
                            )
                        }
                    }

                    1 -> { // INCOME WORKFLOW
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Income Category", style = MaterialTheme.typography.labelMedium)
                            if (onAddCategory != null) {
                                TextButton(
                                    onClick = { showAddCategoryForType = CategoryType.INCOME },
                                    modifier = Modifier.testTag("btn_add_income_category")
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Add Category", style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            incomeCategories.forEach { cat ->
                                FilterChip(
                                    selected = selectedCategoryId == cat.id,
                                    onClick = { selectedCategoryId = cat.id },
                                    label = { Text(cat.name) },
                                    leadingIcon = {
                                        Icon(
                                            CategoryIconHelper.getIcon(cat.iconName),
                                            contentDescription = null,
                                            modifier = Modifier.size(16.dp)
                                        )
                                    }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Deposit into Account", style = MaterialTheme.typography.labelMedium)
                        Spacer(modifier = Modifier.height(6.dp))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            accounts.forEach { acc ->
                                FilterChip(
                                    selected = selectedAccountId == acc.id,
                                    onClick = { selectedAccountId = acc.id },
                                    label = { Text("${acc.name} (${AccountingEngine.formatPaise(acc.currentBalancePaise)})") }
                                )
                            }
                        }
                    }

                    2 -> { // TRANSFER WORKFLOW
                        Text("From Account", style = MaterialTheme.typography.labelMedium)
                        Spacer(modifier = Modifier.height(6.dp))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            accounts.forEach { acc ->
                                FilterChip(
                                    selected = selectedAccountId == acc.id,
                                    onClick = { selectedAccountId = acc.id },
                                    label = { Text(acc.name) }
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))
                        Text("To Account", style = MaterialTheme.typography.labelMedium)
                        Spacer(modifier = Modifier.height(6.dp))
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            accounts.forEach { acc ->
                                FilterChip(
                                    selected = selectedDestinationAccountId == acc.id,
                                    onClick = { selectedDestinationAccountId = acc.id },
                                    label = { Text(acc.name) }
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Save Button
                Button(
                    onClick = {
                        val amountPaise = AccountingEngine.parseRupeesToPaise(amountText)
                        if (amountPaise <= 0L) return@Button

                        when (selectedTab) {
                            0 -> { // Expense
                                val catId = selectedCategoryId ?: expenseCategories.firstOrNull()?.id ?: 1L
                                if (!isSharedExpense) {
                                    val accId = selectedAccountId ?: accounts.firstOrNull()?.id ?: 1L
                                    onSavePersonalExpense(
                                        selectedDateMillis,
                                        amountPaise,
                                        descriptionText.ifBlank { "Personal Expense" },
                                        accId,
                                        catId,
                                        receiptUri,
                                        notesText.ifBlank { null }
                                    )
                                } else {
                                    if (whoPaid == "ARPITA") {
                                        val accId = selectedAccountId ?: accounts.firstOrNull()?.id ?: 1L
                                        val arpitaSharePaise = if (arpitaShareText.isNotBlank()) {
                                            AccountingEngine.parseRupeesToPaise(arpitaShareText)
                                        } else {
                                            amountPaise
                                        }
                                        val allocations = mutableMapOf<Long, Long>()
                                        selectedFriendIds.filter { it.value }.keys.forEach { fId ->
                                            val text = friendAmounts[fId] ?: "0"
                                            val fPaise = AccountingEngine.parseRupeesToPaise(text)
                                            if (fPaise > 0L) allocations[fId] = fPaise
                                        }
                                        onSaveSharedExpense(
                                            selectedDateMillis,
                                            amountPaise,
                                            arpitaSharePaise,
                                            allocations,
                                            descriptionText.ifBlank { "Shared Expense" },
                                            accId,
                                            catId,
                                            receiptUri,
                                            notesText.ifBlank { null }
                                        )
                                    } else {
                                        // Friend paid
                                        val fId = selectedPayingFriendId ?: friends.firstOrNull()?.id ?: 1L
                                        val arpitaSharePaise = if (arpitaShareText.isNotBlank()) {
                                            AccountingEngine.parseRupeesToPaise(arpitaShareText)
                                        } else {
                                            amountPaise
                                        }
                                        onSaveFriendPaidExpense(
                                            selectedDateMillis,
                                            amountPaise,
                                            arpitaSharePaise,
                                            descriptionText.ifBlank { "Shared Purchase" },
                                            fId,
                                            catId,
                                            notesText.ifBlank { null }
                                        )
                                    }
                                }
                            }
                            1 -> { // Income
                                val accId = selectedAccountId ?: accounts.firstOrNull()?.id ?: 1L
                                val catId = selectedCategoryId ?: incomeCategories.firstOrNull()?.id ?: 1L
                                onSaveIncome(
                                    selectedDateMillis,
                                    amountPaise,
                                    descriptionText.ifBlank { "Income" },
                                    accId,
                                    catId,
                                    notesText.ifBlank { null }
                                )
                            }
                            2 -> { // Transfer
                                val fromId = selectedAccountId ?: accounts.firstOrNull()?.id ?: 1L
                                val toId = selectedDestinationAccountId ?: accounts.getOrNull(1)?.id ?: 2L
                                onSaveTransfer(
                                    selectedDateMillis,
                                    amountPaise,
                                    fromId,
                                    toId,
                                    descriptionText.ifBlank { "Account Transfer" }
                                )
                            }
                        }
                        onDismiss()
                    },
                    enabled = totalAmountPaise > 0L,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp)
                        .testTag("button_save_transaction")
                ) {
                    Text("Post Transaction to Ledger", fontWeight = FontWeight.Bold)
                }
            }
        }
    }

    if (showAddCategoryForType != null) {
        val catType = showAddCategoryForType!!
        AddCategoryDialog(
            initialType = catType,
            onDismiss = { showAddCategoryForType = null },
            onCategoryAdded = { name, type, iconName, colorHex ->
                onAddCategory?.invoke(name, type, iconName, colorHex) { newId ->
                    selectedCategoryId = newId
                }
                showAddCategoryForType = null
            }
        )
    }
}
