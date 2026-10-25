package com.example.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * User profile configuration.
 */
@Entity(tableName = "user_profiles")
data class UserProfile(
    @PrimaryKey val id: String = "user_default",
    val displayName: String = "",
    val hasSetPreferredName: Boolean = false,
    val currencySymbol: String = "₹",
    val isPinProtectionEnabled: Boolean = false,
    val pinHash: String = "",
    val gamificationEnabled: Boolean = true,
    val showHealthScore: Boolean = true,
    val createdAt: Long = System.currentTimeMillis()
)

/**
 * Financial account types: Cash Wallet, Savings Bank, etc.
 */
enum class AccountType {
    CASH,
    BANK,
    OTHER
}

@Entity(tableName = "financial_accounts")
data class FinancialAccount(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val accountType: AccountType,
    val openingBalancePaise: Long = 0L,
    val openingDate: Long = System.currentTimeMillis(),
    val currentBalancePaise: Long = 0L,
    val isActive: Boolean = true,
    val iconName: String = "wallet",
    val colorHex: String = "#10B981"
)

enum class CategoryType {
    EXPENSE,
    INCOME
}

@Entity(tableName = "transaction_categories")
data class TransactionCategory(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val type: CategoryType,
    val iconName: String,
    val colorHex: String,
    val isDefault: Boolean = false
)

@Entity(tableName = "friends")
data class Friend(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val nickname: String? = null,
    val contactInfo: String? = null,
    val notes: String? = null,
    val isActive: Boolean = true,
    val openingReceivablePaise: Long = 0L, // How much friend owed as of opening date
    val openingPayablePaise: Long = 0L,    // How much Arpita owed friend as of opening date
    val openingDate: Long = System.currentTimeMillis(),
    val totalReceivablePaise: Long = 0L,   // Current total friend owes Arpita
    val totalPayablePaise: Long = 0L       // Current total Arpita owes friend
) {
    val netPositionPaise: Long
        get() = totalReceivablePaise - totalPayablePaise
}

enum class TransactionType {
    EXPENSE,
    INCOME,
    TRANSFER,
    REPAYMENT_RECEIVED, // Friend pays back Arpita
    REPAYMENT_PAID,     // Arpita pays friend back
    SETTLEMENT          // Mutual settlement
}

@Entity(tableName = "financial_transactions")
data class FinancialTransaction(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val date: Long,
    val totalAmountPaise: Long,
    val personalAmountPaise: Long, // Arpita's personal expense/income
    val type: TransactionType,
    val description: String,
    val sourceAccountId: Long? = null,       // From account (Cash/Bank)
    val destinationAccountId: Long? = null,  // To account (Cash/Bank)
    val categoryId: Long? = null,
    val friendId: Long? = null,              // Primary friend if repayment or single friend split
    val receiptUri: String? = null,
    val isReversed: Boolean = false,
    val reversedByTransactionId: Long? = null,
    val reversalOfTransactionId: Long? = null,
    val notes: String? = null,
    val idempotencyKey: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "transaction_allocations")
data class TransactionAllocation(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val transactionId: Long,
    val friendId: Long?, // null for Arpita's share
    val amountPaise: Long,
    val isArpitaShare: Boolean = false
)

enum class JournalLineType {
    ASSET_CASH_BANK,
    ASSET_RECEIVABLE,
    LIABILITY_PAYABLE,
    EXPENSE,
    INCOME
}

@Entity(tableName = "journal_entries")
data class JournalEntry(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val transactionId: Long,
    val entryDate: Long,
    val description: String,
    val totalDebitPaise: Long,
    val totalCreditPaise: Long,
    val isBalanced: Boolean,
    val isReversal: Boolean = false
)

@Entity(tableName = "journal_lines")
data class JournalLine(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val journalEntryId: Long,
    val lineType: JournalLineType,
    val accountId: Long? = null,
    val friendId: Long? = null,
    val categoryId: Long? = null,
    val debitPaise: Long = 0L,
    val creditPaise: Long = 0L,
    val description: String = ""
)

enum class PlantType {
    SPROUT,
    MINT_HERB,
    LAVENDER_BUSH,
    SUNFLOWER,
    MONEY_TREE
}

@Entity(tableName = "savings_goals")
data class SavingsGoal(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val targetAmountPaise: Long,
    val savedAmountPaise: Long = 0L,
    val targetDate: Long? = null,
    val plantType: PlantType = PlantType.SPROUT,
    val plantStage: Int = 1, // 1 to 5
    val isCompleted: Boolean = false,
    val notes: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "savings_goal_movements")
data class SavingsGoalMovement(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val goalId: Long,
    val amountPaise: Long,
    val isContribution: Boolean, // true = contribute, false = withdraw
    val date: Long = System.currentTimeMillis(),
    val notes: String? = null
)

@Entity(tableName = "achievements")
data class Achievement(
    @PrimaryKey val code: String,
    val title: String,
    val description: String,
    val iconName: String,
    val isUnlocked: Boolean = false,
    val unlockedDate: Long? = null,
    val currentProgress: Int = 0,
    val maxProgress: Int = 1
)

@Entity(tableName = "check_in_activities")
data class CheckInActivity(
    @PrimaryKey val dateIso: String, // YYYY-MM-DD
    val timestamp: Long = System.currentTimeMillis(),
    val isNoSpendDay: Boolean = false,
    val transactionCount: Int = 0
)

@Entity(tableName = "reconciliation_records")
data class ReconciliationRecord(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val accountId: Long,
    val date: Long = System.currentTimeMillis(),
    val statementBalancePaise: Long,
    val ledgerBalancePaise: Long,
    val isReconciled: Boolean,
    val notes: String? = null
)
