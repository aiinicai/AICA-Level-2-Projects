package com.example.ui.screens

import android.app.DatePickerDialog
import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Business
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.MonetizationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material.icons.filled.Today
import androidx.compose.material.icons.filled.Warning
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import com.example.core.repository.PartyWithBalance
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.FilterChip
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import java.util.Calendar
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.core.model.AccountEntity
import com.example.core.model.BusinessEntity
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionStatus
import com.example.core.model.TransactionType
import com.example.core.util.ReminderComposer
import com.example.core.util.ReminderLanguage
import com.example.ui.theme.CrimsonPrimary
import com.example.ui.theme.EmeraldPrimary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun AddPartyDialog(
    businessId: String,
    initialParty: PartyEntity? = null,
    onDismiss: () -> Unit,
    onSave: (PartyEntity) -> Unit,
    onDelete: (() -> Unit)? = null
) {
    var name by remember { mutableStateOf(initialParty?.name ?: "") }
    var phone by remember { mutableStateOf(initialParty?.phone ?: "") }
    var address by remember { mutableStateOf(initialParty?.address ?: "") }
    var gstin by remember { mutableStateOf(initialParty?.gstin ?: "") }
    
    // Role selection: "CUSTOMER", "SUPPLIER", or "BOTH"
    var selectedRoleType by remember {
        mutableStateOf(
            when {
                initialParty == null -> "CUSTOMER"
                initialParty.roles.contains("CUSTOMER") && initialParty.roles.contains("SUPPLIER") -> "BOTH"
                initialParty.roles.contains("SUPPLIER") -> "SUPPLIER"
                else -> "CUSTOMER"
            }
        )
    }

    // Opening balance sign: "RECEIVABLE" (Lena / +) or "PAYABLE" (Dena / -)
    var openingBalType by remember {
        mutableStateOf(
            if (initialParty != null) {
                if (initialParty.openingBalancePaise < 0) "PAYABLE" else "RECEIVABLE"
            } else {
                if (selectedRoleType == "SUPPLIER") "PAYABLE" else "RECEIVABLE"
            }
        )
    }

    var openingBalStr by remember {
        mutableStateOf(
            if (initialParty != null && initialParty.openingBalancePaise != 0L) {
                Money.paiseToRupees(kotlin.math.abs(initialParty.openingBalancePaise))
            } else ""
        )
    }

    var creditPeriodDaysStr by remember {
        mutableStateOf(initialParty?.paymentTermsDays?.toString() ?: "30")
    }
    var notes by remember { mutableStateOf(initialParty?.notes ?: "") }
    var nameError by remember { mutableStateOf(false) }
    var showDeleteConfirm by remember { mutableStateOf(false) }

    if (showDeleteConfirm && onDelete != null) {
        DeleteConfirmationDialog(
            title = "Delete Party?",
            message = "Are you sure you want to delete ${initialParty?.name}? All recorded transactions for this party will be permanently deleted and cannot be recovered.",
            onConfirm = {
                showDeleteConfirm = false
                onDelete()
            },
            onDismiss = { showDeleteConfirm = false }
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (initialParty == null) "Add New Party" else "Edit Party Details",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                if (initialParty != null && onDelete != null) {
                    TextButton(
                        onClick = { showDeleteConfirm = true },
                        colors = ButtonDefaults.textButtonColors(contentColor = CrimsonPrimary)
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete", modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Delete", fontWeight = FontWeight.Bold)
                    }
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = {
                        name = it
                        nameError = it.isBlank()
                    },
                    label = { Text("Party / Business Name *") },
                    leadingIcon = { Icon(Icons.Default.Person, contentDescription = null) },
                    isError = nameError,
                    supportingText = if (nameError) { { Text("Name is required") } } else null,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = phone,
                    onValueChange = { phone = it },
                    label = { Text("Mobile Number (for reminders/bills)") },
                    leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null) },
                    modifier = Modifier.fillMaxWidth()
                )

                // Party Type / Role Selection
                Text("Party Role / Type:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    FilterChip(
                        selected = selectedRoleType == "CUSTOMER",
                        onClick = {
                            selectedRoleType = "CUSTOMER"
                            if (openingBalStr.isBlank() || initialParty == null) {
                                openingBalType = "RECEIVABLE"
                            }
                        },
                        label = { Text("Customer (Grahak)", fontSize = 11.sp) }
                    )
                    FilterChip(
                        selected = selectedRoleType == "SUPPLIER",
                        onClick = {
                            selectedRoleType = "SUPPLIER"
                            if (openingBalStr.isBlank() || initialParty == null) {
                                openingBalType = "PAYABLE"
                            }
                        },
                        label = { Text("Supplier (Vyapari)", fontSize = 11.sp) }
                    )
                    FilterChip(
                        selected = selectedRoleType == "BOTH",
                        onClick = { selectedRoleType = "BOTH" },
                        label = { Text("Both", fontSize = 11.sp) }
                    )
                }

                // Opening Balance Section with Positive/Negative support
                Text("Opening Balance (Past Dues / Advances):", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = openingBalType == "RECEIVABLE",
                        onClick = { openingBalType = "RECEIVABLE" },
                        label = { Text("You'll Receive (Lena +)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp) },
                        colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                            selectedContainerColor = EmeraldPrimary.copy(alpha = 0.15f),
                            selectedLabelColor = EmeraldPrimary
                        ),
                        modifier = Modifier.weight(1f)
                    )

                    FilterChip(
                        selected = openingBalType == "PAYABLE",
                        onClick = { openingBalType = "PAYABLE" },
                        label = { Text("You'll Pay (Dena -)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp) },
                        colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                            selectedContainerColor = CrimsonPrimary.copy(alpha = 0.15f),
                            selectedLabelColor = CrimsonPrimary
                        ),
                        modifier = Modifier.weight(1f)
                    )
                }

                OutlinedTextField(
                    value = openingBalStr,
                    onValueChange = { openingBalStr = it },
                    label = { 
                        Text(if (openingBalType == "RECEIVABLE") "Opening Balance (₹ You'll Receive / +)" else "Opening Balance (₹ You'll Pay / -)") 
                    },
                    placeholder = { Text("e.g. 5000 (Leave blank if 0)") },
                    modifier = Modifier.fillMaxWidth()
                )

                // Credit Period Terms
                CreditPeriodCardSelector(
                    creditDaysStr = creditPeriodDaysStr,
                    onDaysChange = { creditPeriodDaysStr = it },
                    title = "Default Credit Terms (Due Days)",
                    accentColor = if (selectedRoleType == "SUPPLIER") CrimsonPrimary else EmeraldPrimary
                )

                OutlinedTextField(
                    value = address,
                    onValueChange = { address = it },
                    label = { Text("Shop / City / Address (Optional)") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = gstin,
                    onValueChange = { gstin = it },
                    label = { Text("GSTIN (Optional)") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Notes / Remarks (Optional)") },
                    modifier = Modifier.fillMaxWidth(),
                    maxLines = 2
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isBlank()) {
                        nameError = true
                        return@Button
                    }
                    val rolesList = when (selectedRoleType) {
                        "SUPPLIER" -> listOf("SUPPLIER")
                        "BOTH" -> listOf("CUSTOMER", "SUPPLIER")
                        else -> listOf("CUSTOMER")
                    }

                    val rawPaise = Money.rupeesToPaise(openingBalStr)
                    val finalOpeningPaise = if (openingBalType == "PAYABLE") -rawPaise else rawPaise

                    val party = (initialParty ?: PartyEntity(
                        businessId = businessId,
                        name = name.trim(),
                        openingBalancePaise = finalOpeningPaise
                    )).copy(
                        name = name.trim(),
                        phone = phone.trim().takeIf { it.isNotEmpty() },
                        address = address.trim().takeIf { it.isNotEmpty() },
                        gstin = gstin.trim().takeIf { it.isNotEmpty() },
                        roles = rolesList.joinToString(","),
                        openingBalancePaise = finalOpeningPaise,
                        paymentTermsDays = creditPeriodDaysStr.toIntOrNull(),
                        notes = notes.trim().takeIf { it.isNotEmpty() },
                        updatedAt = System.currentTimeMillis()
                    )

                    onSave(party)
                }
            ) {
                Text(if (initialParty == null) "Save Party" else "Update Party")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@Composable
fun EditAccountDialog(
    account: AccountEntity,
    canDelete: Boolean = true,
    onDismiss: () -> Unit,
    onSave: (AccountEntity) -> Unit,
    onDelete: () -> Unit
) {
    var accName by remember { mutableStateOf(account.name) }
    var accType by remember { mutableStateOf(account.type) }
    var accNum by remember { mutableStateOf(account.accountNumber ?: "") }
    var ifsc by remember { mutableStateOf(account.ifscCode ?: "") }
    var upiId by remember { mutableStateOf(account.upiId ?: "") }
    var openBal by remember { mutableStateOf(Money.paiseToRupees(account.openingBalancePaise)) }
    var showDeleteConfirm by remember { mutableStateOf(false) }

    if (showDeleteConfirm) {
        DeleteConfirmationDialog(
            title = "Delete Account?",
            message = "Are you sure you want to delete '${account.name}'? Existing transactions will retain their historical records.",
            onConfirm = {
                showDeleteConfirm = false
                onDelete()
            },
            onDismiss = { showDeleteConfirm = false }
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Edit Account / Ledger", fontWeight = FontWeight.Bold)
                if (canDelete) {
                    IconButton(onClick = { showDeleteConfirm = true }) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = CrimsonPrimary)
                    }
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                OutlinedTextField(
                    value = accName,
                    onValueChange = { accName = it },
                    label = { Text("Account Name *") },
                    placeholder = { Text("e.g. Cash in Hand / SBI Bank / Shop UPI") },
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
                        placeholder = { Text("shopname@upi / 9876543210@paytm") },
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
                    if (accName.isBlank()) return@Button
                    val updated = account.copy(
                        name = accName.trim(),
                        type = accType,
                        accountNumber = accNum.trim().takeIf { it.isNotEmpty() },
                        ifscCode = ifsc.trim().takeIf { it.isNotEmpty() },
                        upiId = upiId.trim().takeIf { it.isNotEmpty() },
                        openingBalancePaise = Money.rupeesToPaise(openBal),
                        updatedAt = System.currentTimeMillis()
                    )
                    onSave(updated)
                }
            ) {
                Text("Save Changes")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
fun CreditPeriodCardSelector(
    creditDaysStr: String,
    onDaysChange: (String) -> Unit,
    baseTimestamp: Long = System.currentTimeMillis(),
    title: String = "Credit Terms & Due Date",
    accentColor: Color = EmeraldPrimary,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val daysInt = creditDaysStr.toIntOrNull() ?: 0
    val dueTimestamp = if (daysInt > 0) baseTimestamp + (daysInt * 24L * 60 * 60 * 1000L) else null
    val dateFormat = remember { java.text.SimpleDateFormat("dd MMM yyyy", java.util.Locale.ENGLISH) }
    val standardPresets = listOf(
        "0" to "Immediate (0d)",
        "7" to "7 Days",
        "15" to "15 Days",
        "30" to "30 Days",
        "45" to "45 Days",
        "60" to "60 Days",
        "90" to "90 Days"
    )
    val isPreset = standardPresets.any { it.first == creditDaysStr }
    var isCustomMode by remember {
        mutableStateOf(!isPreset && creditDaysStr.isNotEmpty() && creditDaysStr != "0")
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f)
        )
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Header Row with Title and Dynamic Due Date Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Event,
                        contentDescription = null,
                        tint = if (daysInt > 0) accentColor else MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = title,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }

                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = if (daysInt > 0) accentColor.copy(alpha = 0.15f) else MaterialTheme.colorScheme.surfaceVariant
                ) {
                    Text(
                        text = if (dueTimestamp != null) {
                            "Due: ${dateFormat.format(java.util.Date(dueTimestamp))}"
                        } else {
                            "Immediate (0d)"
                        },
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (daysInt > 0) accentColor else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }

            // Horizontally Scrollable Preset Chips + Pick Exact Date Button
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                standardPresets.forEach { (presetDays, label) ->
                    val isSelected = !isCustomMode && creditDaysStr == presetDays
                    FilterChip(
                        selected = isSelected,
                        onClick = {
                            isCustomMode = false
                            onDaysChange(presetDays)
                        },
                        label = {
                            Text(
                                text = label,
                                fontSize = 11.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
                            )
                        },
                        colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                            selectedContainerColor = accentColor.copy(alpha = 0.2f),
                            selectedLabelColor = accentColor
                        )
                    )
                }

                FilterChip(
                    selected = isCustomMode,
                    onClick = {
                        isCustomMode = true
                    },
                    label = {
                        Text(
                            text = "Custom Days...",
                            fontSize = 11.sp,
                            fontWeight = if (isCustomMode) FontWeight.Bold else FontWeight.Medium
                        )
                    },
                    colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                        selectedContainerColor = accentColor.copy(alpha = 0.2f),
                        selectedLabelColor = accentColor
                    )
                )

                // Pick Specific Calendar Date Chip
                FilterChip(
                    selected = false,
                    onClick = {
                        val cal = Calendar.getInstance()
                        if (dueTimestamp != null) cal.timeInMillis = dueTimestamp
                        DatePickerDialog(
                            context,
                            { _, y, m, d ->
                                val pickedCal = Calendar.getInstance()
                                pickedCal.set(y, m, d, 23, 59, 59)
                                val diffMillis = pickedCal.timeInMillis - baseTimestamp
                                val calculatedDays = Math.round(diffMillis.toDouble() / (24.0 * 60 * 60 * 1000.0)).coerceAtLeast(0).toString()
                                isCustomMode = true
                                onDaysChange(calculatedDays)
                            },
                            cal.get(Calendar.YEAR),
                            cal.get(Calendar.MONTH),
                            cal.get(Calendar.DAY_OF_MONTH)
                        ).show()
                    },
                    leadingIcon = {
                        Icon(Icons.Default.CalendarMonth, contentDescription = null, modifier = Modifier.size(14.dp))
                    },
                    label = {
                        Text("Pick Date", fontSize = 11.sp)
                    }
                )
            }

            // Custom Days Input field
            if (isCustomMode) {
                OutlinedTextField(
                    value = creditDaysStr,
                    onValueChange = { input ->
                        val clean = input.filter { it.isDigit() }.take(4)
                        onDaysChange(clean)
                    },
                    label = { Text("Custom Credit Period (Days)") },
                    placeholder = { Text("e.g. 21") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    leadingIcon = {
                        Icon(Icons.Default.Schedule, contentDescription = null, modifier = Modifier.size(18.dp))
                    },
                    trailingIcon = {
                        Text(
                            text = if (daysInt > 0) "($daysInt days)" else "days",
                            style = MaterialTheme.typography.labelSmall,
                            modifier = Modifier.padding(end = 12.dp),
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

@Composable
fun EditTransactionDialog(
    tx: TransactionEntity,
    accounts: List<AccountEntity>,
    onDismiss: () -> Unit,
    onSave: (TransactionEntity) -> Unit,
    onDelete: () -> Unit
) {
    val context = LocalContext.current
    var amountRupees by remember { mutableStateOf(Money.paiseToRupees(tx.amountPaise)) }
    var txType by remember { mutableStateOf(tx.type) }
    var transactionDate by remember { mutableStateOf(tx.transactionDate) }
    var notes by remember { mutableStateOf(tx.notes ?: "") }
    var refNo by remember { mutableStateOf(tx.referenceNumber ?: "") }
    var selectedAccId by remember { mutableStateOf(tx.accountId ?: "") }
    var paymentMode by remember { mutableStateOf(tx.paymentMode) }
    var creditPeriodDaysStr by remember {
        val days = if (tx.dueDate != null && tx.dueDate >= tx.transactionDate) {
            val diff = (tx.dueDate - tx.transactionDate).toDouble() / (24.0 * 60 * 60 * 1000.0)
            Math.round(diff).toInt().coerceAtLeast(0).toString()
        } else "0"
        mutableStateOf(days)
    }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    val displayDateFormat = remember { java.text.SimpleDateFormat("dd MMM yyyy, hh:mm a", java.util.Locale.ENGLISH) }

    if (showDeleteConfirm) {
        DeleteConfirmationDialog(
            title = "Delete Transaction?",
            message = "Are you sure you want to permanently delete this entry of ${Money.formatIndianPaise(tx.amountPaise)}? Running balance and party ledger will be updated immediately.",
            onConfirm = {
                showDeleteConfirm = false
                onDelete()
            },
            onDismiss = { showDeleteConfirm = false }
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Edit Transaction Entry", fontWeight = FontWeight.Bold)
                IconButton(onClick = { showDeleteConfirm = true }) {
                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = CrimsonPrimary)
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
                // Transaction Date Picker Row
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            val cal = Calendar.getInstance()
                            cal.timeInMillis = transactionDate
                            DatePickerDialog(
                                context,
                                { _, y, m, d ->
                                    val newCal = Calendar.getInstance()
                                    newCal.set(y, m, d, cal.get(Calendar.HOUR_OF_DAY), cal.get(Calendar.MINUTE))
                                    transactionDate = newCal.timeInMillis
                                },
                                cal.get(Calendar.YEAR),
                                cal.get(Calendar.MONTH),
                                cal.get(Calendar.DAY_OF_MONTH)
                            ).show()
                        }
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Today,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text("Transaction Date", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(
                                    text = displayDateFormat.format(java.util.Date(transactionDate)),
                                    style = MaterialTheme.typography.bodySmall,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                        Text(
                            text = "Change",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }

                // Entry Type Switcher
                Text("Entry Type:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        FilterChip(
                            selected = txType in listOf("GAVE", "SALE"),
                            onClick = { txType = TransactionType.GAVE.name },
                            label = { Text("You Gave (Lena +)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp) },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = EmeraldPrimary.copy(alpha = 0.2f),
                                selectedLabelColor = EmeraldPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = txType in listOf("GOT", "RECEIPT"),
                            onClick = { txType = TransactionType.GOT.name },
                            label = { Text("You Got (Payment -)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp) },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = CrimsonPrimary.copy(alpha = 0.2f),
                                selectedLabelColor = CrimsonPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        FilterChip(
                            selected = txType == TransactionType.PURCHASE.name,
                            onClick = { txType = TransactionType.PURCHASE.name },
                            label = { Text("Credit from Supplier (-)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp) },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = CrimsonPrimary.copy(alpha = 0.2f),
                                selectedLabelColor = CrimsonPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = txType == TransactionType.PAYMENT_TO_SUPPLIER.name,
                            onClick = { txType = TransactionType.PAYMENT_TO_SUPPLIER.name },
                            label = { Text("Paid to Supplier (+)", fontWeight = FontWeight.SemiBold, fontSize = 11.sp) },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = EmeraldPrimary.copy(alpha = 0.2f),
                                selectedLabelColor = EmeraldPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                OutlinedTextField(
                    value = amountRupees,
                    onValueChange = { amountRupees = it },
                    label = { Text("Amount (₹) *") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Polished Credit Period Terms & Due Date (For Gave / Credit / Sale / Purchase entries)
                if (txType in listOf("GAVE", "SALE", "PURCHASE")) {
                    val activeColor = if (txType == TransactionType.PURCHASE.name) CrimsonPrimary else EmeraldPrimary
                    CreditPeriodCardSelector(
                        creditDaysStr = creditPeriodDaysStr,
                        onDaysChange = { creditPeriodDaysStr = it },
                        baseTimestamp = transactionDate,
                        title = "Credit Period & Due Date",
                        accentColor = activeColor
                    )
                }

                // Payment Mode Selection (Scrollable to prevent squishing)
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Payment Mode:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("CASH" to "Cash", "UPI" to "UPI", "BANK_TRANSFER" to "Bank Transfer", "CREDIT" to "Credit", "CHEQUE" to "Cheque").forEach { (modeKey, modeLabel) ->
                            FilterChip(
                                selected = paymentMode == modeKey,
                                onClick = { paymentMode = modeKey },
                                label = { Text(modeLabel, fontSize = 11.sp) }
                            )
                        }
                    }
                }

                // Account Selection (Scrollable)
                if (accounts.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Payment Account:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            accounts.forEach { acc ->
                                FilterChip(
                                    selected = selectedAccId == acc.id,
                                    onClick = { selectedAccId = acc.id },
                                    label = { Text(acc.name, fontSize = 11.sp) }
                                )
                            }
                        }
                    }
                }

                OutlinedTextField(
                    value = refNo,
                    onValueChange = { refNo = it },
                    label = { Text("Bill / Invoice / UTR No (Optional)") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Notes / Item Description (Optional)") },
                    modifier = Modifier.fillMaxWidth(),
                    maxLines = 2
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amountPaise = Money.rupeesToPaise(amountRupees)
                    if (amountPaise <= 0) return@Button
                    val days = creditPeriodDaysStr.toIntOrNull() ?: 0
                    val computedDueDate = if (days > 0) transactionDate + (days * 24L * 60 * 60 * 1000L) else null
                    val updated = tx.copy(
                        type = txType,
                        amountPaise = amountPaise,
                        transactionDate = transactionDate,
                        paymentMode = paymentMode,
                        accountId = selectedAccId.takeIf { it.isNotEmpty() },
                        dueDate = computedDueDate,
                        referenceNumber = refNo.trim().takeIf { it.isNotEmpty() },
                        notes = notes.trim().takeIf { it.isNotEmpty() },
                        updatedAt = System.currentTimeMillis()
                    )
                    onSave(updated)
                }
            ) {
                Text("Save Changes")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
fun TransactionOptionsDialog(
    tx: TransactionEntity,
    onDismiss: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onVoid: () -> Unit,
    onReverse: () -> Unit
) {
    val dateFormat = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.getDefault())
    val isDebit = tx.type in listOf("GAVE", "SALE", "PAYMENT_TO_SUPPLIER", "EXPENSE")
    val titleText = when (tx.type) {
        "PAYMENT_TO_SUPPLIER" -> "Paid to Supplier"
        "PURCHASE" -> "Credit from Supplier (Purchase)"
        "GAVE" -> "You Gave (Customer Udhar)"
        "GOT" -> "You Got (Customer Payment)"
        "SALE" -> "Sale Entry"
        "OPENING_BALANCE" -> "Opening Balance Entry"
        else -> tx.type
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .background(if (isDebit) EmeraldPrimary.copy(alpha = 0.15f) else CrimsonPrimary.copy(alpha = 0.15f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        Icons.Default.Receipt,
                        contentDescription = null,
                        tint = if (isDebit) EmeraldPrimary else CrimsonPrimary,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = titleText,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (isDebit) EmeraldPrimary else CrimsonPrimary
                    )
                    Text(
                        text = Money.formatIndianPaise(tx.amountPaise),
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.ExtraBold
                    )
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "Date: ${dateFormat.format(Date(tx.transactionDate))}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                if (!tx.referenceNumber.isNullOrEmpty()) {
                    Text(
                        text = "Ref/Bill No: ${tx.referenceNumber}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                if (!tx.notes.isNullOrEmpty()) {
                    Text(
                        text = "Notes: ${tx.notes}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Action Buttons
                Button(
                    onClick = {
                        onDismiss()
                        onEdit()
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Edit Transaction Entry", fontWeight = FontWeight.Bold)
                }

                OutlinedButton(
                    onClick = {
                        onDismiss()
                        onDelete()
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = CrimsonPrimary)
                ) {
                    Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Delete Permanently", fontWeight = FontWeight.Bold)
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            onDismiss()
                            onVoid()
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text("Void Entry", fontSize = 12.sp)
                    }

                    OutlinedButton(
                        onClick = {
                            onDismiss()
                            onReverse()
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text("Reverse Entry", fontSize = 12.sp)
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Close") }
        }
    )
}

@Composable
fun DeleteConfirmationDialog(
    title: String = "Delete Confirmation",
    message: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Warning, contentDescription = null, tint = CrimsonPrimary)
                Spacer(modifier = Modifier.width(8.dp))
                Text(title, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Text(message, style = MaterialTheme.typography.bodyMedium)
        },
        confirmButton = {
            Button(
                onClick = onConfirm,
                colors = ButtonDefaults.buttonColors(containerColor = CrimsonPrimary)
            ) {
                Text("Delete")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
fun CreateBusinessDialog(
    onDismiss: () -> Unit,
    onSave: (BusinessEntity) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var ownerName by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var upiId by remember { mutableStateOf("") }
    var gstin by remember { mutableStateOf("") }
    var isError by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Create New Book / Business", fontWeight = FontWeight.Bold) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = {
                        name = it
                        isError = it.isBlank()
                    },
                    label = { Text("Business Name *") },
                    isError = isError,
                    supportingText = if (isError) { { Text("Business name is required") } } else null,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = ownerName,
                    onValueChange = { ownerName = it },
                    label = { Text("Owner Name (Optional)") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = phone,
                    onValueChange = { phone = it },
                    label = { Text("Business Phone (Optional)") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = upiId,
                    onValueChange = { upiId = it },
                    label = { Text("Shop UPI ID (for Payment QR/Links)") },
                    placeholder = { Text("name@upi / 9876543210@paytm") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = gstin,
                    onValueChange = { gstin = it },
                    label = { Text("GSTIN (Optional)") },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isBlank()) {
                        isError = true
                        return@Button
                    }
                    val business = BusinessEntity(
                        name = name.trim(),
                        ownerName = ownerName.trim().takeIf { it.isNotEmpty() },
                        phone = phone.trim().takeIf { it.isNotEmpty() },
                        upiId = upiId.trim().takeIf { it.isNotEmpty() },
                        gstin = gstin.trim().takeIf { it.isNotEmpty() },
                        isDefault = true
                    )
                    onSave(business)
                }
            ) {
                Text("Create Book")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@Composable
fun SendReminderDialog(
    context: Context,
    business: BusinessEntity,
    party: PartyEntity,
    outstandingPaise: Long,
    onDismiss: () -> Unit
) {
    var selectedLanguage by remember { mutableStateOf(ReminderLanguage.ENGLISH) }
    val messageText = remember(selectedLanguage) {
        ReminderComposer.buildReminderText(
            language = selectedLanguage,
            business = business,
            party = party,
            outstandingPaise = outstandingPaise
        )
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Send Payment Reminder", fontWeight = FontWeight.Bold) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text("Choose Language:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    ReminderLanguage.values().forEach { lang ->
                        FilterChip(
                            selected = selectedLanguage == lang,
                            onClick = { selectedLanguage = lang },
                            label = { Text(lang.title) }
                        )
                    }
                }

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = messageText,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(12.dp)
                    )
                }

                Text(
                    text = "Sending to: ${party.name} (${party.phone ?: "No phone registered"})",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        },
        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = {
                        ReminderComposer.shareViaWhatsApp(context, party.phone, messageText)
                        onDismiss()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
                ) {
                    Text("WhatsApp")
                }
                OutlinedButton(
                    onClick = {
                        ReminderComposer.shareViaShareSheet(context, messageText, "Payment Reminder - ${party.name}")
                        onDismiss()
                    }
                ) {
                    Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.padding(end = 4.dp))
                    Text("Share")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

@Composable
fun VoidTransactionDialog(
    tx: TransactionEntity,
    onDismiss: () -> Unit,
    onConfirm: (reason: String) -> Unit
) {
    var reason by remember { mutableStateOf("") }
    var isError by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Void Financial Entry", fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "Voiding this entry will exclude its amount (${Money.formatIndianPaise(tx.amountPaise)}) from the party balance and reports while preserving the immutable audit log record.",
                    style = MaterialTheme.typography.bodyMedium
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = {
                        reason = it
                        isError = it.isBlank()
                    },
                    label = { Text("Reason for Voiding *") },
                    placeholder = { Text("e.g. Wrong party selected / duplicate bill") },
                    isError = isError,
                    supportingText = if (isError) { { Text("Audit reason is required") } } else null,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (reason.isBlank()) {
                        isError = true
                        return@Button
                    }
                    onConfirm(reason.trim())
                },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
            ) {
                Text("Confirm Void")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@Composable
fun SelectPartyDialog(
    parties: List<PartyWithBalance>,
    selectedPartyId: String?,
    onSelectParty: (PartyWithBalance) -> Unit,
    onAddNewParty: () -> Unit,
    onDismiss: () -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedRoleFilter by remember { mutableStateOf("ALL") }

    val filteredParties = remember(parties, searchQuery, selectedRoleFilter) {
        parties.filter { item ->
            val p = item.party
            val matchesQuery = searchQuery.isBlank() ||
                    p.name.contains(searchQuery, ignoreCase = true) ||
                    (p.phone?.contains(searchQuery, ignoreCase = true) == true) ||
                    (p.address?.contains(searchQuery, ignoreCase = true) == true)

            val matchesRole = when (selectedRoleFilter) {
                "CUSTOMER" -> p.roles.contains("CUSTOMER", ignoreCase = true)
                "SUPPLIER" -> p.roles.contains("SUPPLIER", ignoreCase = true)
                else -> true
            }

            matchesQuery && matchesRole
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Select Party / Khata",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "${parties.size} registered parties",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Button(
                    onClick = onAddNewParty,
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Icon(Icons.Default.PersonAdd, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("+ New", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(380.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Search Input Field
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    label = { Text("Search by name, phone...") },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, modifier = Modifier.size(20.dp)) },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Default.Clear, contentDescription = "Clear", modifier = Modifier.size(18.dp))
                            }
                        }
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                // Quick Role Filter Chips
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf("ALL" to "All (${parties.size})", "CUSTOMER" to "Customers", "SUPPLIER" to "Suppliers").forEach { (filterKey, label) ->
                        FilterChip(
                            selected = selectedRoleFilter == filterKey,
                            onClick = { selectedRoleFilter = filterKey },
                            label = { Text(label, fontSize = 11.sp, fontWeight = if (selectedRoleFilter == filterKey) FontWeight.Bold else FontWeight.Normal) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                // Party List Items
                if (filteredParties.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f)
                            .padding(16.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                text = if (searchQuery.isNotBlank()) "No party matching \"$searchQuery\"" else "No parties found",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            OutlinedButton(
                                onClick = onAddNewParty,
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Icon(Icons.Default.PersonAdd, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(if (searchQuery.isNotBlank()) "Add \"$searchQuery\"" else "Add New Party")
                            }
                        }
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        verticalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        items(filteredParties, key = { it.party.id }) { item ->
                            val isSelected = item.party.id == selectedPartyId
                            val isReceivable = item.netBalancePaise > 0
                            val isPayable = item.netBalancePaise < 0

                            val balanceColor = when {
                                isReceivable -> EmeraldPrimary
                                isPayable -> CrimsonPrimary
                                else -> MaterialTheme.colorScheme.onSurfaceVariant
                            }

                            val initials = item.party.name.split(" ")
                                .mapNotNull { it.firstOrNull()?.toString() }
                                .take(2)
                                .joinToString("")
                                .ifEmpty { "P" }

                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(10.dp))
                                    .clickable { onSelectParty(item) },
                                shape = RoundedCornerShape(10.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
                                    else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                                ),
                                border = if (isSelected) androidx.compose.foundation.BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary) else null
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = 10.dp, vertical = 8.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(36.dp)
                                                .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Text(
                                                text = initials.uppercase(),
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 13.sp,
                                                color = MaterialTheme.colorScheme.onPrimaryContainer
                                            )
                                        }

                                        Spacer(modifier = Modifier.width(10.dp))

                                        Column {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Text(
                                                    text = item.party.name,
                                                    style = MaterialTheme.typography.bodyMedium,
                                                    fontWeight = FontWeight.Bold,
                                                    maxLines = 1,
                                                    overflow = TextOverflow.Ellipsis
                                                )
                                                if (isSelected) {
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Icon(
                                                        imageVector = Icons.Default.CheckCircle,
                                                        contentDescription = "Selected",
                                                        tint = MaterialTheme.colorScheme.primary,
                                                        modifier = Modifier.size(16.dp)
                                                    )
                                                }
                                            }

                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                                            ) {
                                                if (!item.party.phone.isNullOrEmpty()) {
                                                    Text(
                                                        text = item.party.phone,
                                                        style = MaterialTheme.typography.labelSmall,
                                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                                    )
                                                }
                                                val isSupplier = item.party.roles.contains("SUPPLIER", ignoreCase = true)
                                                val isCustomer = item.party.roles.contains("CUSTOMER", ignoreCase = true)
                                                val roleBadgeText = if (isSupplier && isCustomer) "Cust & Supp" else if (isSupplier) "Supplier" else "Customer"
                                                Surface(
                                                    shape = RoundedCornerShape(4.dp),
                                                    color = if (isSupplier) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.secondaryContainer
                                                ) {
                                                    Text(
                                                        text = roleBadgeText,
                                                        fontSize = 9.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                                    )
                                                }
                                            }
                                        }
                                    }

                                    Spacer(modifier = Modifier.width(8.dp))

                                    Column(horizontalAlignment = Alignment.End) {
                                        Text(
                                            text = Money.formatIndianPaise(kotlin.math.abs(item.netBalancePaise)),
                                            style = MaterialTheme.typography.bodyMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = balanceColor
                                        )
                                        Text(
                                            text = when {
                                                isReceivable -> "Lena (+)"
                                                isPayable -> "Dena (-)"
                                                else -> "Settled"
                                            },
                                            style = MaterialTheme.typography.labelSmall,
                                            fontSize = 10.sp,
                                            color = balanceColor.copy(alpha = 0.85f)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}
