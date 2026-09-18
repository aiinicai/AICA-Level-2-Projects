package com.example.core.repository

import com.example.core.database.AppDatabase
import com.example.core.model.AccountEntity
import com.example.core.model.AuditLogEntity
import com.example.core.model.BusinessEntity
import com.example.core.model.CategoryEntity
import com.example.core.model.PartyEntity
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionStatus
import com.example.core.model.TransactionType
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import java.util.UUID

data class PartyWithBalance(
    val party: PartyEntity,
    val netBalancePaise: Long, // Positive = You'll receive (Lena), Negative = You'll pay (Dena)
    val lastTransactionDate: Long?
)

data class LedgerItem(
    val transaction: TransactionEntity,
    val debitPaise: Long, // Money given / debit to party (Lena +)
    val creditPaise: Long, // Money received / credit to party (Lena -)
    val runningBalancePaise: Long
)

data class DashboardSummary(
    val totalReceivablePaise: Long, // Total Lena (+)
    val totalPayablePaise: Long,    // Total Dena (-)
    val netBalancePaise: Long,
    val todayGotPaise: Long,
    val todayGavePaise: Long,
    val thisMonthExpensesPaise: Long,
    val totalCashInHandPaise: Long,
    val totalBankPaise: Long,
    val totalUpiPaise: Long
)

data class AgeingSummary(
    val currentPaise: Long,      // 0 - 30 days
    val days31To60Paise: Long,   // 31 - 60 days
    val days61To90Paise: Long,   // 61 - 90 days
    val over90Paise: Long,       // 90+ days
    val totalOutstandingPaise: Long,
    val parties0To30: List<PartyWithBalance> = emptyList(),
    val parties31To60: List<PartyWithBalance> = emptyList(),
    val parties61To90: List<PartyWithBalance> = emptyList(),
    val parties90Plus: List<PartyWithBalance> = emptyList()
)

class LedgerRepository(private val db: AppDatabase) {
    private val businessDao = db.businessDao()
    private val partyDao = db.partyDao()
    private val txDao = db.transactionDao()
    private val accountDao = db.accountDao()
    private val categoryDao = db.categoryDao()
    private val auditDao = db.auditLogDao()

    // Businesses
    fun getAllBusinesses(): Flow<List<BusinessEntity>> = businessDao.getAllBusinesses()
    suspend fun getBusinessById(id: String) = businessDao.getBusinessById(id)
    suspend fun getDefaultBusiness() = businessDao.getDefaultBusiness()
    suspend fun createBusiness(business: BusinessEntity) {
        businessDao.insertBusiness(business)
        // Create default accounts
        accountDao.insertAccount(
            AccountEntity(
                businessId = business.id,
                name = "Cash in Hand",
                type = "CASH",
                openingBalancePaise = 0L
            )
        )
        accountDao.insertAccount(
            AccountEntity(
                businessId = business.id,
                name = "Primary Bank A/C",
                type = "BANK",
                openingBalancePaise = 0L
            )
        )
        accountDao.insertAccount(
            AccountEntity(
                businessId = business.id,
                name = "Shop UPI",
                type = "UPI",
                openingBalancePaise = 0L
            )
        )
        // Default categories
        val defaultCats = listOf(
            CategoryEntity(businessId = business.id, name = "Shop Rent", iconName = "store", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Staff Salary", iconName = "badge", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Electricity & Utility", iconName = "bolt", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Transport & Delivery", iconName = "local_shipping", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Inventory / Goods", iconName = "inventory", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Tea & Refreshment", iconName = "coffee", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Repairs & Maintenance", iconName = "build", isExpense = true, isDefault = true),
            CategoryEntity(businessId = business.id, name = "Miscellaneous", iconName = "more_horiz", isExpense = true, isDefault = true)
        )
        categoryDao.insertCategories(defaultCats)

        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = business.id,
                action = "CREATE_BUSINESS",
                entityType = "Business",
                entityId = business.id,
                details = "Created business: ${business.name}"
            )
        )
    }

    suspend fun updateBusiness(business: BusinessEntity) = businessDao.updateBusiness(business)
    suspend fun setDefaultBusiness(id: String) {
        businessDao.clearDefault()
        businessDao.setDefault(id)
    }

    // Parties
    fun getPartiesByBusiness(businessId: String) = partyDao.getPartiesByBusiness(businessId)
    fun getAllPartiesIncludingArchived(businessId: String) = partyDao.getAllPartiesIncludingArchived(businessId)
    suspend fun getPartyById(id: String) = partyDao.getPartyById(id)
    fun observePartyById(id: String) = partyDao.observePartyById(id)
    fun searchParties(businessId: String, query: String) = partyDao.searchParties(businessId, query)

    suspend fun saveParty(party: PartyEntity) {
        partyDao.insertParty(party)
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = party.businessId,
                action = "SAVE_PARTY",
                entityType = "Party",
                entityId = party.id,
                details = "Saved party: ${party.name} (${party.phone ?: "no phone"})"
            )
        )
    }

    suspend fun archiveParty(partyId: String, businessId: String, isArchived: Boolean) {
        partyDao.setArchived(partyId, isArchived)
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = businessId,
                action = if (isArchived) "ARCHIVE_PARTY" else "RESTORE_PARTY",
                entityType = "Party",
                entityId = partyId,
                details = if (isArchived) "Archived party ID $partyId" else "Restored party ID $partyId"
            )
        )
    }

    suspend fun deleteParty(partyId: String, businessId: String) {
        txDao.deleteTransactionsForParty(partyId)
        partyDao.deletePartyById(partyId)
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = businessId,
                action = "DELETE_PARTY",
                entityType = "Party",
                entityId = partyId,
                details = "Deleted party $partyId and all associated transactions"
            )
        )
    }

    // Transactions
    fun getTransactionsByBusiness(businessId: String) = txDao.getTransactionsByBusiness(businessId)
    fun getTransactionsForParty(partyId: String) = txDao.getTransactionsForParty(partyId)
    fun getExpenses(businessId: String) = txDao.getExpenses(businessId)
    fun getTransactionsForAccount(businessId: String, accountId: String) = txDao.getTransactionsForAccount(businessId, accountId)

    suspend fun findPotentialDuplicate(businessId: String, partyId: String, amountPaise: Long): TransactionEntity? {
        val tenMinutesAgo = System.currentTimeMillis() - (10 * 60 * 1000)
        return txDao.findPotentialDuplicate(businessId, partyId, amountPaise, tenMinutesAgo)
    }

    suspend fun postTransaction(tx: TransactionEntity) {
        txDao.insertTransaction(tx)
        partyDao.getPartyById(tx.partyId ?: "")?.let {
            partyDao.updateParty(it.copy(updatedAt = System.currentTimeMillis()))
        }
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = tx.businessId,
                action = "POST_TRANSACTION",
                entityType = "Transaction",
                entityId = tx.id,
                details = "Posted ${tx.type} of amount ${tx.amountPaise} paise (Party: ${tx.partyId ?: "N/A"})"
            )
        )
    }

    suspend fun voidTransaction(txId: String, businessId: String, reason: String) {
        txDao.voidTransaction(txId, reason)
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = businessId,
                action = "VOID_TRANSACTION",
                entityType = "Transaction",
                entityId = txId,
                details = "Voided transaction $txId. Reason: $reason"
            )
        )
    }

    suspend fun reverseTransaction(originalTx: TransactionEntity, reason: String) {
        // Mark original as REVERSED
        val reversalId = UUID.randomUUID().toString()
        val updatedOriginal = originalTx.copy(
            status = TransactionStatus.REVERSED.name,
            reversalTransactionId = reversalId,
            updatedAt = System.currentTimeMillis()
        )
        txDao.updateTransaction(updatedOriginal)

        // Determine opposite type
        val oppositeType = when (originalTx.type) {
            TransactionType.GAVE.name -> TransactionType.GOT.name
            TransactionType.GOT.name -> TransactionType.GAVE.name
            TransactionType.SALE.name -> TransactionType.GOT.name
            TransactionType.PURCHASE.name -> TransactionType.GAVE.name
            TransactionType.EXPENSE.name -> TransactionType.INCOME.name
            TransactionType.INCOME.name -> TransactionType.EXPENSE.name
            else -> TransactionType.ADJUSTMENT.name
        }

        val reversalTx = TransactionEntity(
            id = reversalId,
            businessId = originalTx.businessId,
            partyId = originalTx.partyId,
            accountId = originalTx.accountId,
            type = oppositeType,
            amountPaise = originalTx.amountPaise,
            transactionDate = System.currentTimeMillis(),
            paymentMode = originalTx.paymentMode,
            notes = "Reversal for Tx #${originalTx.id.take(6)}: $reason",
            status = TransactionStatus.POSTED.name,
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis()
        )
        txDao.insertTransaction(reversalTx)

        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = originalTx.businessId,
                action = "REVERSE_TRANSACTION",
                entityType = "Transaction",
                entityId = originalTx.id,
                details = "Reversed transaction ${originalTx.id} with new Tx $reversalId. Reason: $reason"
            )
        )
    }

    suspend fun updateTransaction(tx: TransactionEntity) {
        txDao.updateTransaction(tx)
        tx.partyId?.let { pId ->
            partyDao.getPartyById(pId)?.let {
                partyDao.updateParty(it.copy(updatedAt = System.currentTimeMillis()))
            }
        }
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = tx.businessId,
                action = "UPDATE_TRANSACTION",
                entityType = "Transaction",
                entityId = tx.id,
                details = "Updated transaction ${tx.id} (${tx.type}, ${tx.amountPaise} paise)"
            )
        )
    }

    suspend fun deleteTransaction(txId: String, businessId: String) {
        val tx = txDao.getTransactionById(txId)
        val partyId = tx?.partyId
        txDao.deleteTransactionById(txId)
        if (partyId != null) {
            partyDao.getPartyById(partyId)?.let {
                partyDao.updateParty(it.copy(updatedAt = System.currentTimeMillis()))
            }
        }
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = businessId,
                action = "DELETE_TRANSACTION",
                entityType = "Transaction",
                entityId = txId,
                details = "Permanently deleted transaction $txId"
            )
        )
    }

    suspend fun transferBetweenAccounts(
        businessId: String,
        sourceAccountId: String,
        targetAccountId: String,
        amountPaise: Long,
        notes: String?
    ) {
        val transferTx = TransactionEntity(
            businessId = businessId,
            partyId = null,
            accountId = sourceAccountId,
            destinationAccountId = targetAccountId,
            type = TransactionType.TRANSFER.name,
            amountPaise = amountPaise,
            paymentMode = "BANK_TRANSFER",
            notes = notes ?: "Internal account transfer",
            status = TransactionStatus.POSTED.name
        )
        txDao.insertTransaction(transferTx)

        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = businessId,
                action = "ACCOUNT_TRANSFER",
                entityType = "Transaction",
                entityId = transferTx.id,
                details = "Transferred ${amountPaise} paise from account $sourceAccountId to $targetAccountId"
            )
        )
    }

    // Accounts
    fun getAccountsByBusiness(businessId: String) = accountDao.getAccountsByBusiness(businessId)
    suspend fun saveAccount(account: AccountEntity) {
        accountDao.insertAccount(account)
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = account.businessId,
                action = "SAVE_ACCOUNT",
                entityType = "Account",
                entityId = account.id,
                details = "Saved account: ${account.name} (${account.type})"
            )
        )
    }
    suspend fun deleteAccount(accountId: String, businessId: String) {
        accountDao.deleteAccountById(accountId)
        auditDao.insertAuditLog(
            AuditLogEntity(
                businessId = businessId,
                action = "DELETE_ACCOUNT",
                entityType = "Account",
                entityId = accountId,
                details = "Deleted account $accountId"
            )
        )
    }

    // Categories
    fun getCategoriesByBusiness(businessId: String) = categoryDao.getCategoriesByBusiness(businessId)
    suspend fun saveCategory(category: CategoryEntity) = categoryDao.insertCategory(category)

    // Audit logs
    fun getAuditLogs(businessId: String) = auditDao.getAuditLogs(businessId)

    // Calculations: Party Ledger Running Balance
    fun calculatePartyLedger(party: PartyEntity, transactions: List<TransactionEntity>): List<LedgerItem> {
        var currentBalance = party.openingBalancePaise
        val ledgerItems = mutableListOf<LedgerItem>()

        // Add opening balance row if non-zero
        if (party.openingBalancePaise != 0L) {
            val isDebit = party.openingBalancePaise > 0
            ledgerItems.add(
                LedgerItem(
                    transaction = TransactionEntity(
                        id = "opening-bal-${party.id}",
                        businessId = party.businessId,
                        partyId = party.id,
                        type = TransactionType.OPENING_BALANCE.name,
                        amountPaise = kotlin.math.abs(party.openingBalancePaise),
                        transactionDate = party.createdAt,
                        notes = "Opening Balance",
                        status = TransactionStatus.POSTED.name
                    ),
                    debitPaise = if (isDebit) party.openingBalancePaise else 0L,
                    creditPaise = if (!isDebit) kotlin.math.abs(party.openingBalancePaise) else 0L,
                    runningBalancePaise = currentBalance
                )
            )
        }

        // Process transactions (POSTED, REVERSED, and include VOIDED for transparent audit trail)
        for (tx in transactions) {
            val isVoided = tx.status == TransactionStatus.VOIDED.name
            var debit = 0L
            var credit = 0L

            if (!isVoided) {
                when (tx.type) {
                    TransactionType.GAVE.name, TransactionType.SALE.name, TransactionType.PAYMENT_TO_SUPPLIER.name, "EXPENSE", "DEBIT", "PAYMENT_OUT", "PAID_TO_SUPPLIER" -> {
                        debit = tx.amountPaise
                        currentBalance += tx.amountPaise
                    }
                    TransactionType.GOT.name, TransactionType.PURCHASE.name, "GOT_CREDIT", "CREDIT_FROM_SUPPLIER", "INCOME", "CREDIT", "PAYMENT_IN", "RECEIPT" -> {
                        credit = tx.amountPaise
                        currentBalance -= tx.amountPaise
                    }
                    TransactionType.ADJUSTMENT.name -> {
                        if (tx.amountPaise >= 0) {
                            debit = tx.amountPaise
                            currentBalance += tx.amountPaise
                        } else {
                            credit = kotlin.math.abs(tx.amountPaise)
                            currentBalance += tx.amountPaise
                        }
                    }
                    else -> {
                        if (tx.type.contains("GAVE", ignoreCase = true) || tx.type.contains("SALE", ignoreCase = true)) {
                            debit = tx.amountPaise
                            currentBalance += tx.amountPaise
                        } else {
                            credit = tx.amountPaise
                            currentBalance -= tx.amountPaise
                        }
                    }
                }
            }

            ledgerItems.add(
                LedgerItem(
                    transaction = tx,
                    debitPaise = if (isVoided) 0L else debit,
                    creditPaise = if (isVoided) 0L else credit,
                    runningBalancePaise = currentBalance
                )
            )
        }

        return ledgerItems
    }

    // Party net balance calculation
    fun calculatePartyNetBalance(party: PartyEntity, transactions: List<TransactionEntity>): Long {
        var balance = party.openingBalancePaise
        for (tx in transactions) {
            if (tx.status == TransactionStatus.VOIDED.name) continue
            when (tx.type) {
                TransactionType.GAVE.name, TransactionType.SALE.name, TransactionType.PAYMENT_TO_SUPPLIER.name, TransactionType.OPENING_BALANCE.name, "EXPENSE", "DEBIT", "PAYMENT_OUT", "PAID_TO_SUPPLIER" -> {
                    balance += tx.amountPaise
                }
                TransactionType.GOT.name, TransactionType.PURCHASE.name, "GOT_CREDIT", "CREDIT_FROM_SUPPLIER", "INCOME", "CREDIT", "PAYMENT_IN", "RECEIPT" -> {
                    balance -= tx.amountPaise
                }
                TransactionType.ADJUSTMENT.name -> {
                    balance += tx.amountPaise
                }
                else -> {
                    if (tx.type.contains("GAVE", ignoreCase = true) || tx.type.contains("SALE", ignoreCase = true) || tx.type.contains("PAYMENT_TO_SUPPLIER", ignoreCase = true)) {
                        balance += tx.amountPaise
                    } else {
                        balance -= tx.amountPaise
                    }
                }
            }
        }
        return balance
    }

    // Account Balance Calculation
    fun calculateAccountBalance(account: AccountEntity, allTransactions: List<TransactionEntity>): Long {
        var balance = account.openingBalancePaise
        for (tx in allTransactions) {
            if (tx.status == TransactionStatus.VOIDED.name) continue

            // Account is source
            if (tx.accountId == account.id) {
                when (tx.type) {
                    TransactionType.GOT.name, TransactionType.INCOME.name -> {
                        balance += tx.amountPaise // Money in
                    }
                    TransactionType.GAVE.name, TransactionType.EXPENSE.name, TransactionType.PURCHASE.name, TransactionType.PAYMENT_TO_SUPPLIER.name, TransactionType.TRANSFER.name -> {
                        balance -= tx.amountPaise // Money out
                    }
                }
            }

            // Account is destination for transfers
            if (tx.destinationAccountId == account.id && tx.type == TransactionType.TRANSFER.name) {
                balance += tx.amountPaise // Money transferred in
            }
        }
        return balance
    }

    // Ageing Analysis for Receivables
    fun calculateAgeing(partiesWithBalances: List<PartyWithBalance>, transactionsByParty: Map<String, List<TransactionEntity>>): AgeingSummary {
        var current = 0L
        var days31To60 = 0L
        var days61To90 = 0L
        var over90 = 0L
        var totalOutstanding = 0L

        val now = System.currentTimeMillis()
        val dayMillis = 24 * 60 * 60 * 1000L

        val list0To30 = mutableListOf<PartyWithBalance>()
        val list31To60 = mutableListOf<PartyWithBalance>()
        val list61To90 = mutableListOf<PartyWithBalance>()
        val list90Plus = mutableListOf<PartyWithBalance>()

        for (item in partiesWithBalances) {
            if (item.netBalancePaise <= 0) continue // Only analyse receivables (Lena)

            totalOutstanding += item.netBalancePaise
            val txs = transactionsByParty[item.party.id] ?: emptyList()
            val oldestUnpaidTx = txs.filter { it.status == TransactionStatus.POSTED.name && (it.type == TransactionType.GAVE.name || it.type == TransactionType.SALE.name) }
                .minByOrNull { it.transactionDate }

            val ageDays = if (oldestUnpaidTx != null) {
                ((now - oldestUnpaidTx.transactionDate) / dayMillis).coerceAtLeast(0)
            } else {
                ((now - item.party.createdAt) / dayMillis).coerceAtLeast(0)
            }

            when {
                ageDays <= 30 -> {
                    current += item.netBalancePaise
                    list0To30.add(item)
                }
                ageDays <= 60 -> {
                    days31To60 += item.netBalancePaise
                    list31To60.add(item)
                }
                ageDays <= 90 -> {
                    days61To90 += item.netBalancePaise
                    list61To90.add(item)
                }
                else -> {
                    over90 += item.netBalancePaise
                    list90Plus.add(item)
                }
            }
        }

        return AgeingSummary(
            currentPaise = current,
            days31To60Paise = days31To60,
            days61To90Paise = days61To90,
            over90Paise = over90,
            totalOutstandingPaise = totalOutstanding,
            parties0To30 = list0To30,
            parties31To60 = list31To60,
            parties61To90 = list61To90,
            parties90Plus = list90Plus
        )
    }
}
