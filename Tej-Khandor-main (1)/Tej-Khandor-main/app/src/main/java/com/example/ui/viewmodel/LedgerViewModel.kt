package com.example.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.core.database.AppDatabase
import com.example.core.model.AccountEntity
import com.example.core.model.BusinessEntity
import com.example.core.model.CategoryEntity
import com.example.core.model.PartyEntity
import com.example.core.model.PartyFilter
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionStatus
import com.example.core.model.TransactionType
import com.example.core.repository.AgeingSummary
import com.example.core.repository.DashboardSummary
import com.example.core.repository.LedgerItem
import com.example.core.repository.LedgerRepository
import com.example.core.repository.PartyWithBalance
import com.example.core.security.BackupMetadata
import com.example.core.security.SecurityManager
import com.example.core.util.SeedData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Calendar

@OptIn(ExperimentalCoroutinesApi::class)
class LedgerViewModel(application: Application) : AndroidViewModel(application) {
    private val db = AppDatabase.getDatabase(application)
    val repository = LedgerRepository(db)
    val securityManager = SecurityManager(application)

    private val _activeBusinessId = MutableStateFlow<String?>(null)
    val activeBusinessId: StateFlow<String?> = _activeBusinessId.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _partyFilter = MutableStateFlow(PartyFilter.ALL)
    val partyFilter: StateFlow<PartyFilter> = _partyFilter.asStateFlow()

    private val _isAppLocked = MutableStateFlow(false)
    val isAppLocked: StateFlow<Boolean> = _isAppLocked.asStateFlow()

    val businesses: StateFlow<List<BusinessEntity>> = repository.getAllBusinesses()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val activeBusiness: StateFlow<BusinessEntity?> = combine(businesses, _activeBusinessId) { list, activeId ->
        if (activeId != null) {
            list.find { it.id == activeId } ?: list.firstOrNull()
        } else {
            list.find { it.isDefault } ?: list.firstOrNull()
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    // Parties strictly scoped to active business
    val parties: StateFlow<List<PartyEntity>> = activeBusiness
        .flatMapLatest { bus ->
            if (bus != null) repository.getAllPartiesIncludingArchived(bus.id)
            else flowOf(emptyList())
        }
        .flowOn(Dispatchers.Default)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Transactions strictly scoped to active business
    val recentTransactions: StateFlow<List<TransactionEntity>> = activeBusiness
        .flatMapLatest { bus ->
            if (bus != null) repository.getTransactionsByBusiness(bus.id)
            else flowOf(emptyList())
        }
        .flowOn(Dispatchers.Default)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Accounts strictly scoped to active business
    val accounts: StateFlow<List<AccountEntity>> = activeBusiness
        .flatMapLatest { bus ->
            if (bus != null) repository.getAccountsByBusiness(bus.id)
            else flowOf(emptyList())
        }
        .flowOn(Dispatchers.Default)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val categories: StateFlow<List<CategoryEntity>> = activeBusiness
        .flatMapLatest { bus ->
            if (bus != null) repository.getCategoriesByBusiness(bus.id)
            else flowOf(emptyList())
        }
        .flowOn(Dispatchers.Default)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Parties with computed balances (instant in-memory computation)
    val partiesWithBalances: StateFlow<List<PartyWithBalance>> = combine(
        parties,
        recentTransactions,
        _searchQuery,
        _partyFilter
    ) { partiesList, transactionsList, query, filter ->
        val txsByParty = transactionsList.groupBy { it.partyId ?: "" }

        val withBalances = partiesList.map { party ->
            val partyTxs = txsByParty[party.id] ?: emptyList()
            val netPaise = repository.calculatePartyNetBalance(party, partyTxs)
            val lastDate = partyTxs.maxOfOrNull { it.transactionDate } ?: party.createdAt
            PartyWithBalance(party, netPaise, lastDate)
        }

        // Apply filters & search
        withBalances.filter { item ->
            val matchesQuery = query.isBlank() ||
                    item.party.name.contains(query, ignoreCase = true) ||
                    (item.party.phone?.contains(query) == true) ||
                    (item.party.address?.contains(query, ignoreCase = true) == true)

            val matchesFilter = when (filter) {
                PartyFilter.ALL -> !item.party.isArchived
                PartyFilter.CUSTOMERS -> !item.party.isArchived && item.party.roles.contains("CUSTOMER", ignoreCase = true)
                PartyFilter.SUPPLIERS -> !item.party.isArchived && item.party.roles.contains("SUPPLIER", ignoreCase = true)
                PartyFilter.RECEIVABLE -> !item.party.isArchived && item.netBalancePaise > 0
                PartyFilter.PAYABLE -> !item.party.isArchived && item.netBalancePaise < 0
                PartyFilter.SETTLED -> !item.party.isArchived && item.netBalancePaise == 0L
                PartyFilter.ARCHIVED -> item.party.isArchived
            }

            matchesQuery && matchesFilter
        }.sortedByDescending { it.lastTransactionDate }
    }
    .flowOn(Dispatchers.Default)
    .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Dashboard metrics (instant in-memory computation)
    val dashboardSummary: StateFlow<DashboardSummary> = combine(
        parties,
        recentTransactions,
        accounts
    ) { partiesList, transactionsList, accountsList ->
        val txsByParty = transactionsList.groupBy { it.partyId ?: "" }

        var totalReceivable = 0L
        var totalPayable = 0L

        for (p in partiesList) {
            if (p.isArchived) continue
            val bal = repository.calculatePartyNetBalance(p, txsByParty[p.id] ?: emptyList())
            if (bal > 0) totalReceivable += bal
            else if (bal < 0) totalPayable += kotlin.math.abs(bal)
        }

        val startOfToday = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis

        val startOfMonth = Calendar.getInstance().apply {
            set(Calendar.DAY_OF_MONTH, 1)
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis

        var todayGot = 0L
        var todayGave = 0L
        var monthExpenses = 0L

        for (tx in transactionsList) {
            if (tx.status == TransactionStatus.VOIDED.name) continue
            if (tx.transactionDate >= startOfToday) {
                if (tx.type == TransactionType.GOT.name) todayGot += tx.amountPaise
                if (tx.type == TransactionType.GAVE.name || tx.type == TransactionType.PAYMENT_TO_SUPPLIER.name) todayGave += tx.amountPaise
            }
            if (tx.transactionDate >= startOfMonth && tx.type == TransactionType.EXPENSE.name) {
                monthExpenses += tx.amountPaise
            }
        }

        // Account balances
        var cashTotal = 0L
        var bankTotal = 0L
        var upiTotal = 0L

        for (acc in accountsList) {
            val bal = repository.calculateAccountBalance(acc, transactionsList)
            when (acc.type) {
                "CASH" -> cashTotal += bal
                "BANK" -> bankTotal += bal
                "UPI" -> upiTotal += bal
                else -> cashTotal += bal
            }
        }

        DashboardSummary(
            totalReceivablePaise = totalReceivable,
            totalPayablePaise = totalPayable,
            netBalancePaise = totalReceivable - totalPayable,
            todayGotPaise = todayGot,
            todayGavePaise = todayGave,
            thisMonthExpensesPaise = monthExpenses,
            totalCashInHandPaise = cashTotal,
            totalBankPaise = bankTotal,
            totalUpiPaise = upiTotal
        )
    }
    .flowOn(Dispatchers.Default)
    .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DashboardSummary(0, 0, 0, 0, 0, 0, 0, 0, 0))

    init {
        viewModelScope.launch {
            // Seed initial data if first launch
            SeedData.populateInitialData(db)

            // Setup lock state
            if (securityManager.isLockEnabled() && securityManager.hasPinSet()) {
                _isAppLocked.value = true
            }
        }
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun setPartyFilter(filter: PartyFilter) {
        _partyFilter.value = filter
    }

    fun selectBusiness(id: String) {
        _activeBusinessId.value = id
        viewModelScope.launch {
            repository.setDefaultBusiness(id)
        }
    }

    fun createBusiness(business: BusinessEntity) {
        viewModelScope.launch {
            repository.createBusiness(business)
            _activeBusinessId.value = business.id
        }
    }

    fun saveParty(party: PartyEntity) {
        viewModelScope.launch {
            repository.saveParty(party)
        }
    }

    fun saveAccount(account: AccountEntity) {
        viewModelScope.launch {
            repository.saveAccount(account)
        }
    }

    fun deleteAccount(accountId: String) {
        val bId = activeBusiness.value?.id ?: return
        viewModelScope.launch {
            repository.deleteAccount(accountId, bId)
        }
    }

    fun deleteParty(partyId: String, onComplete: () -> Unit = {}) {
        val bId = activeBusiness.value?.id ?: return
        viewModelScope.launch {
            repository.deleteParty(partyId, bId)
            withContext(Dispatchers.Main) { onComplete() }
        }
    }

    fun deleteTransaction(txId: String, onComplete: () -> Unit = {}) {
        val bId = activeBusiness.value?.id ?: return
        viewModelScope.launch {
            repository.deleteTransaction(txId, bId)
            withContext(Dispatchers.Main) { onComplete() }
        }
    }

    fun updateTransaction(tx: TransactionEntity, onComplete: () -> Unit = {}) {
        viewModelScope.launch {
            repository.updateTransaction(tx)
            withContext(Dispatchers.Main) { onComplete() }
        }
    }

    fun archiveParty(partyId: String, isArchived: Boolean) {
        val bId = activeBusiness.value?.id ?: return
        viewModelScope.launch {
            repository.archiveParty(partyId, bId, isArchived)
        }
    }

    fun postTransaction(tx: TransactionEntity, onComplete: () -> Unit = {}) {
        viewModelScope.launch {
            repository.postTransaction(tx)
            withContext(Dispatchers.Main) { onComplete() }
        }
    }

    fun voidTransaction(txId: String, reason: String) {
        val bId = activeBusiness.value?.id ?: return
        viewModelScope.launch {
            repository.voidTransaction(txId, bId, reason)
        }
    }

    fun reverseTransaction(tx: TransactionEntity, reason: String) {
        viewModelScope.launch {
            repository.reverseTransaction(tx, reason)
        }
    }

    fun transferBetweenAccounts(sourceId: String, targetId: String, amountPaise: Long, notes: String?) {
        val bId = activeBusiness.value?.id ?: return
        viewModelScope.launch {
            repository.transferBetweenAccounts(bId, sourceId, targetId, amountPaise, notes)
        }
    }

    suspend fun getPartyLedgerItems(party: PartyEntity): List<LedgerItem> {
        val txs = repository.getTransactionsForParty(party.id).first()
        return repository.calculatePartyLedger(party, txs)
    }

    suspend fun getAgeingSummary(): AgeingSummary {
        val partiesList = partiesWithBalances.value
        val txsByParty = recentTransactions.value.groupBy { it.partyId ?: "" }
        return repository.calculateAgeing(partiesList, txsByParty)
    }

    // Security
    fun unlockWithPin(pin: String): Boolean {
        val success = securityManager.verifyPin(pin)
        if (success) {
            _isAppLocked.value = false
            securityManager.recordUserActivity()
        }
        return success
    }

    fun setAppPin(pin: String) {
        securityManager.setPin(pin)
        _isAppLocked.value = false
    }

    fun disableAppLock() {
        securityManager.disableLock()
        _isAppLocked.value = false
    }

    fun lockNow() {
        if (securityManager.isLockEnabled()) {
            _isAppLocked.value = true
        }
    }

    // Backup & Restore
    suspend fun createBackup(password: String): File {
        val bId = activeBusiness.value?.id ?: throw IllegalStateException("No active business")
        return securityManager.createEncryptedBackup(db, bId, password)
    }

    suspend fun inspectBackup(file: File, password: String): BackupMetadata {
        return securityManager.inspectBackup(file, password)
    }

    suspend fun restoreBackup(file: File, password: String) {
        securityManager.restoreBackup(db, file, password)
    }
}
