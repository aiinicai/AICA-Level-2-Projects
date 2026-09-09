package com.example.ui.screens

import android.content.Intent
import android.widget.Toast
import androidx.activity.compose.BackHandler
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
import androidx.compose.material.icons.filled.Archive
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowDownward
import androidx.compose.material.icons.filled.ArrowUpward
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.QrCode
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.SyncAlt
import androidx.compose.material.icons.filled.TableChart
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
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
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.core.model.Money
import com.example.core.model.PartyEntity
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionStatus
import com.example.core.repository.LedgerItem
import com.example.core.util.CsvExporter
import com.example.core.util.PdfStatementGenerator
import com.example.ui.components.LedgerItemRow
import com.example.ui.components.UpiQrDialog
import com.example.ui.theme.CrimsonPrimary
import com.example.ui.theme.EmeraldPrimary
import com.example.ui.viewmodel.LedgerViewModel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PartyDetailScreen(
    partyId: String,
    viewModel: LedgerViewModel,
    onNavigateBack: () -> Unit,
    onAddTransaction: (partyId: String, isGave: Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val activeBusiness by viewModel.activeBusiness.collectAsStateWithLifecycle()
    val parties by viewModel.parties.collectAsStateWithLifecycle()
    val partiesWithBalances by viewModel.partiesWithBalances.collectAsStateWithLifecycle()
    val recentTxs by viewModel.recentTransactions.collectAsStateWithLifecycle()

    val party = remember(parties, partyId) { parties.find { it.id == partyId } }
    val partyTxs = remember(partyId, recentTxs) {
        recentTxs.filter { it.partyId == partyId }
            .sortedWith(compareBy({ it.transactionDate }, { it.createdAt }))
    }
    val ledgerItems = remember(party, partyTxs) {
        if (party != null) viewModel.repository.calculatePartyLedger(party, partyTxs) else emptyList()
    }
    val partyItem = partiesWithBalances.find { it.party.id == partyId }
    val netBalancePaise = partyItem?.netBalancePaise ?: if (party != null) viewModel.repository.calculatePartyNetBalance(party, partyTxs) else 0L

    val accounts by viewModel.accounts.collectAsStateWithLifecycle()

    var selectedTxForAction by remember { mutableStateOf<TransactionEntity?>(null) }
    var showOptionsDialog by remember { mutableStateOf(false) }
    var showEditTxDialog by remember { mutableStateOf(false) }
    var showDeleteTxConfirm by remember { mutableStateOf(false) }
    var showDeletePartyConfirm by remember { mutableStateOf(false) }
    var showEditPartyDialog by remember { mutableStateOf(false) }
    var showSendReminderDialog by remember { mutableStateOf(false) }
    var showQrDialog by remember { mutableStateOf(false) }
    var showVoidDialog by remember { mutableStateOf(false) }
    var showReverseDialog by remember { mutableStateOf(false) }
    var showMenu by remember { mutableStateOf(false) }

    if (party == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Party not found")
        }
        return
    }

    // Delete Party Confirmation Dialog
    if (showDeletePartyConfirm) {
        DeleteConfirmationDialog(
            title = "Delete Party?",
            message = "Are you sure you want to permanently delete '${party.name}' and all associated ledger entries? This cannot be undone.",
            onConfirm = {
                showDeletePartyConfirm = false
                viewModel.deleteParty(party.id) {
                    Toast.makeText(context, "Party deleted", Toast.LENGTH_SHORT).show()
                    onNavigateBack()
                }
            },
            onDismiss = { showDeletePartyConfirm = false }
        )
    }

    // Delete Single Transaction Confirmation Dialog
    if (showDeleteTxConfirm && selectedTxForAction != null) {
        DeleteConfirmationDialog(
            title = "Delete Transaction Entry?",
            message = "Are you sure you want to permanently delete this entry of ${Money.formatIndianPaise(selectedTxForAction!!.amountPaise)}? Running balance and reports will be recalculated immediately.",
            onConfirm = {
                val txToDelete = selectedTxForAction!!
                showDeleteTxConfirm = false
                selectedTxForAction = null
                viewModel.deleteTransaction(txToDelete.id) {
                    Toast.makeText(context, "Transaction deleted", Toast.LENGTH_SHORT).show()
                }
            },
            onDismiss = {
                showDeleteTxConfirm = false
                selectedTxForAction = null
            }
        )
    }

    // Transaction Options Dialog (Click on Ledger Row)
    if (showOptionsDialog && selectedTxForAction != null) {
        TransactionOptionsDialog(
            tx = selectedTxForAction!!,
            onDismiss = {
                showOptionsDialog = false
            },
            onEdit = {
                showOptionsDialog = false
                showEditTxDialog = true
            },
            onDelete = {
                showOptionsDialog = false
                showDeleteTxConfirm = true
            },
            onVoid = {
                showOptionsDialog = false
                showVoidDialog = true
            },
            onReverse = {
                showOptionsDialog = false
                showReverseDialog = true
            }
        )
    }

    // Edit Transaction Dialog
    if (showEditTxDialog && selectedTxForAction != null) {
        EditTransactionDialog(
            tx = selectedTxForAction!!,
            accounts = accounts,
            onDismiss = {
                showEditTxDialog = false
                selectedTxForAction = null
            },
            onSave = { updatedTx ->
                viewModel.updateTransaction(updatedTx) {
                    showEditTxDialog = false
                    selectedTxForAction = null
                    Toast.makeText(context, "Transaction updated", Toast.LENGTH_SHORT).show()
                }
            },
            onDelete = {
                val txToDelete = selectedTxForAction!!
                showEditTxDialog = false
                selectedTxForAction = null
                viewModel.deleteTransaction(txToDelete.id) {
                    Toast.makeText(context, "Transaction deleted", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    // Edit Party Dialog
    if (showEditPartyDialog && activeBusiness != null) {
        AddPartyDialog(
            businessId = activeBusiness!!.id,
            initialParty = party,
            onDismiss = { showEditPartyDialog = false },
            onSave = { updatedParty ->
                viewModel.saveParty(updatedParty)
                showEditPartyDialog = false
                Toast.makeText(context, "Party updated", Toast.LENGTH_SHORT).show()
            },
            onDelete = {
                showEditPartyDialog = false
                viewModel.deleteParty(party.id) {
                    Toast.makeText(context, "Party deleted", Toast.LENGTH_SHORT).show()
                    onNavigateBack()
                }
            }
        )
    }

    if (showSendReminderDialog && activeBusiness != null) {
        SendReminderDialog(
            context = context,
            business = activeBusiness!!,
            party = party,
            outstandingPaise = netBalancePaise,
            onDismiss = { showSendReminderDialog = false }
        )
    }

    if (showQrDialog && activeBusiness != null) {
        UpiQrDialog(
            business = activeBusiness!!,
            party = party,
            initialAmountRupees = if (netBalancePaise > 0) netBalancePaise / 100.0 else null,
            onDismiss = { showQrDialog = false }
        )
    }

    if (showVoidDialog && selectedTxForAction != null) {
        VoidTransactionDialog(
            tx = selectedTxForAction!!,
            onDismiss = {
                showVoidDialog = false
                selectedTxForAction = null
            },
            onConfirm = { reason ->
                viewModel.voidTransaction(selectedTxForAction!!.id, reason)
                showVoidDialog = false
                selectedTxForAction = null
                Toast.makeText(context, "Transaction voided", Toast.LENGTH_SHORT).show()
            }
        )
    }

    // Transaction Details & Reversal Dialog
    if (showReverseDialog && selectedTxForAction != null) {
        var reverseReason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = {
                showReverseDialog = false
                selectedTxForAction = null
            },
            title = { Text("Create Reversal Entry", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        "Creating an offsetting reversal entry will automatically negate this ${Money.formatIndianPaise(selectedTxForAction!!.amountPaise)} entry with full audit trail."
                    )
                    OutlinedTextField(
                        value = reverseReason,
                        onValueChange = { reverseReason = it },
                        label = { Text("Reversal Reason *") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (reverseReason.isNotBlank()) {
                            viewModel.reverseTransaction(selectedTxForAction!!, reverseReason)
                            showReverseDialog = false
                            selectedTxForAction = null
                            Toast.makeText(context, "Reversal entry posted", Toast.LENGTH_SHORT).show()
                        }
                    }
                ) {
                    Text("Post Reversal")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    showReverseDialog = false
                    selectedTxForAction = null
                }) {
                    Text("Cancel")
                }
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(party.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        if (!party.phone.isNullOrEmpty()) {
                            Text(party.phone, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { showQrDialog = true }) {
                        Icon(Icons.Default.QrCode, contentDescription = "UPI QR Code", tint = MaterialTheme.colorScheme.primary)
                    }
                    IconButton(onClick = { showSendReminderDialog = true }) {
                        Icon(Icons.Default.Notifications, contentDescription = "Send Reminder", tint = EmeraldPrimary)
                    }
                    IconButton(onClick = { showMenu = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "More Options")
                    }
                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Receive Payment via QR") },
                            leadingIcon = { Icon(Icons.Default.QrCode, contentDescription = null) },
                            onClick = {
                                showMenu = false
                                showQrDialog = true
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Edit Party Info") },
                            leadingIcon = { Icon(Icons.Default.Edit, contentDescription = null) },
                            onClick = {
                                showMenu = false
                                showEditPartyDialog = true
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Download PDF Statement") },
                            leadingIcon = { Icon(Icons.Default.PictureAsPdf, contentDescription = null) },
                            onClick = {
                                showMenu = false
                                if (activeBusiness != null) {
                                    val pdfFile = PdfStatementGenerator.generatePartyStatementPdf(
                                        context = context,
                                        business = activeBusiness!!,
                                        party = party,
                                        ledgerItems = ledgerItems,
                                        netBalancePaise = netBalancePaise
                                    )
                                    if (pdfFile != null) {
                                        val uri = FileProvider.getUriForFile(
                                            context,
                                            "${context.packageName}.fileprovider",
                                            pdfFile
                                        )
                                        val intent = Intent(Intent.ACTION_SEND).apply {
                                            type = "application/pdf"
                                            putExtra(Intent.EXTRA_STREAM, uri)
                                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                        }
                                        context.startActivity(Intent.createChooser(intent, "Share PDF Statement"))
                                    } else {
                                        Toast.makeText(context, "Error creating PDF", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Export CSV Ledger") },
                            leadingIcon = { Icon(Icons.Default.TableChart, contentDescription = null) },
                            onClick = {
                                showMenu = false
                                val csvFile = CsvExporter.exportPartyLedgerCsv(context, party, ledgerItems)
                                if (csvFile != null) {
                                    val uri = FileProvider.getUriForFile(
                                        context,
                                        "${context.packageName}.fileprovider",
                                        csvFile
                                    )
                                    val intent = Intent(Intent.ACTION_SEND).apply {
                                        type = "text/csv"
                                        putExtra(Intent.EXTRA_STREAM, uri)
                                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                    }
                                    context.startActivity(Intent.createChooser(intent, "Share CSV Ledger"))
                                }
                            }
                        )
                        DropdownMenuItem(
                            text = { Text(if (party.isArchived) "Unarchive Party" else "Archive Party") },
                            leadingIcon = { Icon(Icons.Default.Archive, contentDescription = null) },
                            onClick = {
                                showMenu = false
                                viewModel.archiveParty(party.id, !party.isArchived)
                                onNavigateBack()
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Delete Party", color = CrimsonPrimary, fontWeight = FontWeight.Bold) },
                            leadingIcon = { Icon(Icons.Default.Delete, contentDescription = null, tint = CrimsonPrimary) },
                            onClick = {
                                showMenu = false
                                showDeletePartyConfirm = true
                            }
                        )
                    }
                }
            )
        },
        bottomBar = {
            // High-Speed Action Bar (Role-Aware)
            val isSupplierOnly = party.roles.contains("SUPPLIER") && !party.roles.contains("CUSTOMER")
            Surface(
                tonalElevation = 8.dp,
                shadowElevation = 8.dp,
                color = MaterialTheme.colorScheme.surface
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Button(
                        onClick = { onAddTransaction(party.id, true) },
                        modifier = Modifier
                            .weight(1f)
                            .height(52.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = EmeraldPrimary)
                    ) {
                        Icon(Icons.Default.ArrowUpward, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isSupplierOnly) "Paid to Supplier" else "You Gave (Udhar)",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                    }

                    Button(
                        onClick = { onAddTransaction(party.id, false) },
                        modifier = Modifier
                            .weight(1f)
                            .height(52.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = CrimsonPrimary)
                    ) {
                        Icon(Icons.Default.ArrowDownward, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isSupplierOnly) "Credit / Purchase" else "You Got (Payment)",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Spacer(modifier = Modifier.height(4.dp))
                // Summary KPI Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (netBalancePaise >= 0) EmeraldPrimary.copy(alpha = 0.12f)
                        else CrimsonPrimary.copy(alpha = 0.12f)
                    )
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(18.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = if (netBalancePaise >= 0) "Net You'll Receive (Lena)" else "Net You'll Pay (Dena)",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = if (netBalancePaise >= 0) EmeraldPrimary else CrimsonPrimary
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = Money.formatIndianPaise(kotlin.math.abs(netBalancePaise)),
                                fontSize = 28.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = if (netBalancePaise >= 0) EmeraldPrimary else CrimsonPrimary
                            )
                            if (party.paymentTermsDays != null && party.paymentTermsDays > 0) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Surface(
                                    shape = RoundedCornerShape(4.dp),
                                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.8f)
                                ) {
                                    Text(
                                        text = "Credit Terms: ${party.paymentTermsDays} Days",
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                            }
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            IconButton(
                                onClick = { showQrDialog = true },
                                modifier = Modifier
                                    .background(MaterialTheme.colorScheme.surface, CircleShape)
                                    .size(46.dp)
                            ) {
                                Icon(Icons.Default.QrCode, contentDescription = "Receive via QR", tint = MaterialTheme.colorScheme.primary)
                            }

                            IconButton(
                                onClick = { showSendReminderDialog = true },
                                modifier = Modifier
                                    .background(MaterialTheme.colorScheme.surface, CircleShape)
                                    .size(46.dp)
                            ) {
                                Icon(Icons.Default.Share, contentDescription = "Reminder", tint = EmeraldPrimary)
                            }
                        }
                    }
                }
            }

            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp, bottom = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Transactions (${ledgerItems.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Running Balance",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (ledgerItems.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 40.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No transactions recorded yet.\nUse the buttons below to record credit or payment.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                }
            } else {
                items(ledgerItems.reversed()) { item ->
                    LedgerItemRow(
                        item = item,
                        onClick = {
                            selectedTxForAction = item.transaction
                            showOptionsDialog = true
                        }
                    )
                }
            }

            item {
                Spacer(modifier = Modifier.height(24.dp))
            }
        }
    }
}
