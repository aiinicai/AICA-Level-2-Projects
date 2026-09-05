package com.example.ui.screens

import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PersonSearch
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
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
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import com.example.core.model.PaymentMode
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionType
import com.example.core.repository.PartyWithBalance
import com.example.ui.components.QuickKeypad
import com.example.ui.theme.CrimsonContainer
import com.example.ui.theme.CrimsonPrimary
import com.example.ui.theme.EmeraldContainer
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.viewmodel.LedgerViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddTransactionScreen(
    viewModel: LedgerViewModel,
    preselectedPartyId: String? = null,
    initialIsGave: Boolean = true,
    onNavigateBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val activeBusiness by viewModel.activeBusiness.collectAsStateWithLifecycle()
    val partiesWithBalances by viewModel.partiesWithBalances.collectAsStateWithLifecycle()
    val accounts by viewModel.accounts.collectAsStateWithLifecycle()

    var selectedPartyId by remember { mutableStateOf(preselectedPartyId ?: "") }
    val selectedPartyItem = partiesWithBalances.find { it.party.id == selectedPartyId }
    val isSupplierParty = selectedPartyItem?.party?.roles?.contains("SUPPLIER") == true && selectedPartyItem.party.roles.contains("CUSTOMER") != true

    var selectedTxType by remember {
        mutableStateOf(
            if (isSupplierParty) {
                if (initialIsGave) TransactionType.PAYMENT_TO_SUPPLIER else TransactionType.PURCHASE
            } else {
                if (initialIsGave) TransactionType.GAVE else TransactionType.GOT
            }
        )
    }

    var amountInputStr by remember { mutableStateOf("") }
    var referenceNo by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var selectedPaymentMode by remember { mutableStateOf(PaymentMode.CASH) }
    var selectedAccountId by remember { mutableStateOf("") }
    var creditPeriodDaysStr by remember { mutableStateOf("30") }
    var selectedDateOffsetDays by remember { mutableStateOf(0) } // 0 = Today, 1 = Yesterday, etc.
    var showMoreFields by remember { mutableStateOf(true) }
    var showAddPartyDialog by remember { mutableStateOf(false) }
    var showPartyPickerDialog by remember { mutableStateOf(false) }
    var showDuplicateWarning by remember { mutableStateOf(false) }
    var pendingSaveTx by remember { mutableStateOf<TransactionEntity?>(null) }

    // Auto-select first account if available
    LaunchedEffect(accounts) {
        if (selectedAccountId.isEmpty() && accounts.isNotEmpty()) {
            selectedAccountId = accounts.first().id
        }
    }

    // Update defaults when selected party changes
    LaunchedEffect(selectedPartyItem) {
        if (selectedPartyItem?.party?.paymentTermsDays != null && selectedPartyItem.party.paymentTermsDays > 0) {
            creditPeriodDaysStr = selectedPartyItem.party.paymentTermsDays.toString()
        }
        val isSupp = selectedPartyItem?.party?.roles?.contains("SUPPLIER") == true && selectedPartyItem.party.roles.contains("CUSTOMER") != true
        if (isSupp && (selectedTxType == TransactionType.GAVE || selectedTxType == TransactionType.GOT)) {
            selectedTxType = if (selectedTxType == TransactionType.GAVE) TransactionType.PAYMENT_TO_SUPPLIER else TransactionType.PURCHASE
        }
    }

    val currentPartyBalance = selectedPartyItem?.netBalancePaise ?: 0L
    val enteredPaise = Money.rupeesToPaise(amountInputStr)

    // Projected new balance calculation
    val isDebitType = selectedTxType in listOf(TransactionType.GAVE, TransactionType.PAYMENT_TO_SUPPLIER, TransactionType.SALE)
    val projectedBalancePaise = if (isDebitType) {
        currentPartyBalance + enteredPaise
    } else {
        currentPartyBalance - enteredPaise
    }

    val primaryTypeColor = if (isDebitType) EmeraldPrimary else CrimsonPrimary
    val primaryContainerColor = if (isDebitType) EmeraldContainer else CrimsonContainer

    if (showAddPartyDialog && activeBusiness != null) {
        AddPartyDialog(
            businessId = activeBusiness!!.id,
            onDismiss = { showAddPartyDialog = false },
            onSave = { newParty ->
                viewModel.saveParty(newParty)
                selectedPartyId = newParty.id
                showAddPartyDialog = false
            }
        )
    }

    if (showPartyPickerDialog) {
        SelectPartyDialog(
            parties = partiesWithBalances,
            selectedPartyId = selectedPartyId.takeIf { it.isNotEmpty() },
            onSelectParty = { item ->
                selectedPartyId = item.party.id
                showPartyPickerDialog = false
            },
            onAddNewParty = {
                showPartyPickerDialog = false
                showAddPartyDialog = true
            },
            onDismiss = { showPartyPickerDialog = false }
        )
    }

    // Duplicate Warning Dialog
    if (showDuplicateWarning && pendingSaveTx != null) {
        AlertDialog(
            onDismissRequest = { showDuplicateWarning = false },
            icon = { Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = { Text("Potential Duplicate Entry", fontWeight = FontWeight.Bold) },
            text = {
                Text("A similar transaction of ${Money.formatIndianPaise(pendingSaveTx!!.amountPaise)} was recorded for ${selectedPartyItem?.party?.name ?: "this party"} in the last 10 minutes. Do you want to save it anyway?")
            },
            confirmButton = {
                Button(
                    onClick = {
                        showDuplicateWarning = false
                        viewModel.postTransaction(pendingSaveTx!!) {
                            Toast.makeText(context, "Entry saved successfully", Toast.LENGTH_SHORT).show()
                            onNavigateBack()
                        }
                    }
                ) {
                    Text("Save Anyway")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDuplicateWarning = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = when (selectedTxType) {
                            TransactionType.GAVE -> "You Gave (Customer Udhar)"
                            TransactionType.GOT -> "You Got (Customer Payment)"
                            TransactionType.PURCHASE -> "Got Credit from Supplier"
                            TransactionType.PAYMENT_TO_SUPPLIER -> "Paid to Supplier"
                            else -> "Add Transaction Entry"
                        },
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
        ) {
            // Mode Switcher Grid/Tabs
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
                    Text(
                        text = "Transaction Type:",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(6.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = selectedTxType == TransactionType.GAVE,
                            onClick = { selectedTxType = TransactionType.GAVE },
                            label = { Text("You Gave (Lena +)", fontWeight = FontWeight.Bold, fontSize = 11.sp) },
                            leadingIcon = {
                                Icon(Icons.Default.ArrowUpward, contentDescription = null, modifier = Modifier.size(14.dp), tint = EmeraldPrimary)
                            },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = EmeraldContainer,
                                selectedLabelColor = EmeraldPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )

                        FilterChip(
                            selected = selectedTxType == TransactionType.GOT,
                            onClick = { selectedTxType = TransactionType.GOT },
                            label = { Text("You Got (Jama -)", fontWeight = FontWeight.Bold, fontSize = 11.sp) },
                            leadingIcon = {
                                Icon(Icons.Default.ArrowDownward, contentDescription = null, modifier = Modifier.size(14.dp), tint = CrimsonPrimary)
                            },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = CrimsonContainer,
                                selectedLabelColor = CrimsonPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = selectedTxType == TransactionType.PURCHASE,
                            onClick = { selectedTxType = TransactionType.PURCHASE },
                            label = { Text("Credit from Supplier (-)", fontWeight = FontWeight.Bold, fontSize = 11.sp) },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = CrimsonContainer,
                                selectedLabelColor = CrimsonPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )

                        FilterChip(
                            selected = selectedTxType == TransactionType.PAYMENT_TO_SUPPLIER,
                            onClick = { selectedTxType = TransactionType.PAYMENT_TO_SUPPLIER },
                            label = { Text("Paid to Supplier (+)", fontWeight = FontWeight.Bold, fontSize = 11.sp) },
                            colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
                                selectedContainerColor = EmeraldContainer,
                                selectedLabelColor = EmeraldPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Party Selector Card
            Column(modifier = Modifier.padding(horizontal = 16.dp)) {
                if (selectedPartyItem != null) {
                    val initials = selectedPartyItem.party.name.split(" ")
                        .mapNotNull { it.firstOrNull()?.toString() }
                        .take(2)
                        .joinToString("")
                        .ifEmpty { "P" }
                    val isSupp = selectedPartyItem.party.roles.contains("SUPPLIER", ignoreCase = true)
                    val isCust = selectedPartyItem.party.roles.contains("CUSTOMER", ignoreCase = true)
                    val roleTag = if (isSupp && isCust) "Cust & Supp" else if (isSupp) "Supplier" else "Customer"

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .clickable { showPartyPickerDialog = true },
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.weight(1f)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(42.dp)
                                        .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = initials.uppercase(),
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 15.sp,
                                        color = MaterialTheme.colorScheme.onPrimaryContainer
                                    )
                                }

                                Spacer(modifier = Modifier.width(12.dp))

                                Column {
                                    Text(
                                        text = selectedPartyItem.party.name,
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1,
                                        overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        if (!selectedPartyItem.party.phone.isNullOrEmpty()) {
                                            Text(
                                                text = selectedPartyItem.party.phone,
                                                style = MaterialTheme.typography.labelSmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                        Surface(
                                            shape = RoundedCornerShape(4.dp),
                                            color = if (isSupp) MaterialTheme.colorScheme.tertiaryContainer else MaterialTheme.colorScheme.secondaryContainer
                                        ) {
                                            Text(
                                                text = roleTag,
                                                fontSize = 9.sp,
                                                fontWeight = FontWeight.Bold,
                                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                            )
                                        }
                                    }
                                }
                            }

                            OutlinedButton(
                                onClick = { showPartyPickerDialog = true },
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                            ) {
                                Icon(Icons.Default.SwapHoriz, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Change", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                } else {
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .clickable { showPartyPickerDialog = true },
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f)),
                        border = BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.6f))
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.weight(1f)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(40.dp)
                                        .background(MaterialTheme.colorScheme.primary, CircleShape),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.PersonSearch,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.onPrimary,
                                        modifier = Modifier.size(22.dp)
                                    )
                                }

                                Spacer(modifier = Modifier.width(12.dp))

                                Column {
                                    Text(
                                        text = "Select Party / Khata *",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                    Text(
                                        text = if (partiesWithBalances.isEmpty()) "Tap to add your first party" else "Tap to choose customer or supplier",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }

                            Button(
                                onClick = { showPartyPickerDialog = true },
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Text("Select", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                            }
                        }
                    }
                }

                // Balance Projection Card
                if (selectedPartyItem != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 12.dp, vertical = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text("Current Balance", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(
                                    text = Money.formatIndianPaise(currentPartyBalance),
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text("Projected Balance", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(
                                    text = Money.formatIndianPaise(projectedBalancePaise),
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = if (projectedBalancePaise >= 0) EmeraldPrimary else CrimsonPrimary
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Big Amount Input Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .background(
                        color = primaryContainerColor.copy(alpha = 0.35f),
                        shape = RoundedCornerShape(16.dp)
                    )
                    .padding(16.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    val inputHeading = when (selectedTxType) {
                        TransactionType.GAVE -> "Amount Given / Lena (₹)"
                        TransactionType.GOT -> "Amount Received / Jama (₹)"
                        TransactionType.PURCHASE -> "Credit from Supplier (₹)"
                        TransactionType.PAYMENT_TO_SUPPLIER -> "Payment to Supplier (₹)"
                        else -> "Amount (₹)"
                    }
                    Text(
                        text = inputHeading,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = primaryTypeColor
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedTextField(
                        value = amountInputStr,
                        onValueChange = { amountInputStr = it.filter { char -> char.isDigit() || char == '.' } },
                        placeholder = { Text("0", fontSize = 32.sp, fontWeight = FontWeight.Bold, textAlign = androidx.compose.ui.text.style.TextAlign.Center, modifier = Modifier.fillMaxWidth()) },
                        textStyle = androidx.compose.ui.text.TextStyle(
                            fontSize = 32.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = primaryTypeColor,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        ),
                        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                            keyboardType = androidx.compose.ui.text.input.KeyboardType.Number
                        ),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(0.85f),
                        shape = RoundedCornerShape(12.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Transaction Date Selector
            Column(modifier = Modifier.padding(horizontal = 16.dp)) {
                Text("Transaction Date:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf(0 to "Today", 1 to "Yesterday", 2 to "2 Days Ago").forEach { (offset, label) ->
                        FilterChip(
                            selected = selectedDateOffsetDays == offset,
                            onClick = { selectedDateOffsetDays = offset },
                            label = { Text(label, fontSize = 11.sp) }
                        )
                    }
                }
            }

            // Credit Period Selection (For Gave / Udhar / Purchase credit entries)
            if (selectedTxType == TransactionType.GAVE || selectedTxType == TransactionType.PURCHASE) {
                Spacer(modifier = Modifier.height(8.dp))
                Column(modifier = Modifier.padding(horizontal = 16.dp)) {
                    val txDate = System.currentTimeMillis() - (selectedDateOffsetDays * 24 * 60 * 60 * 1000L)
                    CreditPeriodCardSelector(
                        creditDaysStr = creditPeriodDaysStr,
                        onDaysChange = { creditPeriodDaysStr = it },
                        baseTimestamp = txDate,
                        title = "Credit Period & Due Date",
                        accentColor = primaryTypeColor
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Progressive Disclosure: Payment mode, account & notes
            Column(modifier = Modifier.padding(horizontal = 16.dp)) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { showMoreFields = !showMoreFields }
                        .padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (showMoreFields) "Payment Mode & Bill Details" else "Add Mode, Bill No, Notes & Account",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Icon(
                        imageVector = if (showMoreFields) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                }

                if (showMoreFields) {
                    Spacer(modifier = Modifier.height(8.dp))
                    // Payment Modes
                    Text("Payment Mode:", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf(PaymentMode.CASH, PaymentMode.UPI, PaymentMode.BANK_TRANSFER, PaymentMode.CREDIT).forEach { mode ->
                            FilterChip(
                                selected = selectedPaymentMode == mode,
                                onClick = { selectedPaymentMode = mode },
                                label = { Text(mode.label.take(12), fontSize = 11.sp) }
                            )
                        }
                    }

                    if (accounts.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Text("Account (Cash / Bank):", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            accounts.forEach { acc ->
                                FilterChip(
                                    selected = selectedAccountId == acc.id,
                                    onClick = { selectedAccountId = acc.id },
                                    label = { Text(acc.name.take(12), fontSize = 11.sp) }
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = referenceNo,
                            onValueChange = { referenceNo = it },
                            label = { Text("Bill / Invoice / UTR No") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                        OutlinedTextField(
                            value = notes,
                            onValueChange = { notes = it },
                            label = { Text("Item Details / Remarks") },
                            modifier = Modifier.weight(1f),
                            singleLine = true
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Numeric Keypad
            QuickKeypad(
                amountInputStr = amountInputStr,
                onAmountChange = { amountInputStr = it }
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Save Buttons
            val isFormValid = selectedPartyId.isNotEmpty() && enteredPaise > 0

            fun performSave(saveAndAddAnother: Boolean) {
                if (!isFormValid) {
                    Toast.makeText(context, "Please select a party and enter an amount", Toast.LENGTH_SHORT).show()
                    return
                }

                val bId = activeBusiness?.id ?: return
                val txDate = System.currentTimeMillis() - (selectedDateOffsetDays * 24 * 60 * 60 * 1000L)
                val daysInt = creditPeriodDaysStr.toIntOrNull() ?: 0
                val computedDueDate = if ((selectedTxType == TransactionType.GAVE || selectedTxType == TransactionType.PURCHASE) && daysInt > 0) {
                    txDate + (daysInt * 24 * 60 * 60 * 1000L)
                } else null

                val tx = TransactionEntity(
                    businessId = bId,
                    partyId = selectedPartyId,
                    accountId = selectedAccountId.takeIf { it.isNotEmpty() },
                    type = selectedTxType.name,
                    amountPaise = enteredPaise,
                    paymentMode = selectedPaymentMode.name,
                    transactionDate = txDate,
                    dueDate = computedDueDate,
                    referenceNumber = referenceNo.trim().takeIf { it.isNotEmpty() },
                    notes = notes.trim().takeIf { it.isNotEmpty() }
                )

                coroutineScope.launch {
                    val duplicate = viewModel.repository.findPotentialDuplicate(bId, selectedPartyId, enteredPaise)
                    if (duplicate != null) {
                        pendingSaveTx = tx
                        showDuplicateWarning = true
                    } else {
                        viewModel.postTransaction(tx) {
                            Toast.makeText(context, "Transaction recorded", Toast.LENGTH_SHORT).show()
                            if (saveAndAddAnother) {
                                amountInputStr = ""
                                referenceNo = ""
                                notes = ""
                            } else {
                                onNavigateBack()
                            }
                        }
                    }
                }
            }

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                OutlinedButton(
                    onClick = { performSave(saveAndAddAnother = true) },
                    enabled = isFormValid,
                    modifier = Modifier
                        .weight(1f)
                        .height(50.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Save & Add Another", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                }

                Button(
                    onClick = { performSave(saveAndAddAnother = false) },
                    enabled = isFormValid,
                    modifier = Modifier
                        .weight(1f)
                        .height(50.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = primaryTypeColor
                    )
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Save Entry", fontSize = 15.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}
