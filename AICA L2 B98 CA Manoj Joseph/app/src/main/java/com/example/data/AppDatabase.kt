package com.example.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.data.dao.AccountDao
import com.example.data.dao.AchievementDao
import com.example.data.dao.CategoryDao
import com.example.data.dao.CheckInDao
import com.example.data.dao.FriendDao
import com.example.data.dao.JournalDao
import com.example.data.dao.ReconciliationDao
import com.example.data.dao.SavingsGoalDao
import com.example.data.dao.TransactionDao
import com.example.data.dao.UserProfileDao
import com.example.data.model.AccountType
import com.example.data.model.Achievement
import com.example.data.model.CategoryType
import com.example.data.model.CheckInActivity
import com.example.data.model.FinancialAccount
import com.example.data.model.FinancialTransaction
import com.example.data.model.Friend
import com.example.data.model.JournalEntry
import com.example.data.model.JournalLine
import com.example.data.model.PlantType
import com.example.data.model.ReconciliationRecord
import com.example.data.model.SavingsGoal
import com.example.data.model.SavingsGoalMovement
import com.example.data.model.TransactionAllocation
import com.example.data.model.TransactionCategory
import com.example.data.model.UserProfile
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@Database(
    entities = [
        UserProfile::class,
        FinancialAccount::class,
        TransactionCategory::class,
        Friend::class,
        FinancialTransaction::class,
        TransactionAllocation::class,
        JournalEntry::class,
        JournalLine::class,
        SavingsGoal::class,
        SavingsGoalMovement::class,
        Achievement::class,
        CheckInActivity::class,
        ReconciliationRecord::class
    ],
    version = 4,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun userProfileDao(): UserProfileDao
    abstract fun accountDao(): AccountDao
    abstract fun categoryDao(): CategoryDao
    abstract fun friendDao(): FriendDao
    abstract fun transactionDao(): TransactionDao
    abstract fun journalDao(): JournalDao
    abstract fun savingsGoalDao(): SavingsGoalDao
    abstract fun achievementDao(): AchievementDao
    abstract fun checkInDao(): CheckInDao
    abstract fun reconciliationDao(): ReconciliationDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "money_garden_db_v3"
                )
                    .fallbackToDestructiveMigration()
                    .addCallback(object : Callback() {
                        override fun onCreate(db: SupportSQLiteDatabase) {
                            super.onCreate(db)
                            // Populate default data on background thread
                            CoroutineScope(Dispatchers.IO).launch {
                                getInstance(context).prepopulateDefaults()
                            }
                        }
                    })
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }

    suspend fun prepopulateDefaults() {
        // User profile
        userProfileDao().saveUserProfile(
            UserProfile(
                id = "user_default",
                displayName = "",
                hasSetPreferredName = false,
                currencySymbol = "₹",
                isPinProtectionEnabled = false,
                gamificationEnabled = true,
                showHealthScore = true
            )
        )

        // Default accounts (Start completely at 0 until user sets opening balance)
        val cashWallet = FinancialAccount(
            name = "Cash Wallet",
            accountType = AccountType.CASH,
            openingBalancePaise = 0L,
            currentBalancePaise = 0L,
            iconName = "payments",
            colorHex = "#10B981"
        )
        val savingsBank = FinancialAccount(
            name = "Savings Bank Account",
            accountType = AccountType.BANK,
            openingBalancePaise = 0L,
            currentBalancePaise = 0L,
            iconName = "account_balance",
            colorHex = "#3B82F6"
        )
        accountDao().insertAccount(cashWallet)
        accountDao().insertAccount(savingsBank)

        // Default categories
        val defaultCategories = listOf(
            TransactionCategory(name = "Food & Dining", type = CategoryType.EXPENSE, iconName = "restaurant", colorHex = "#F97316", isDefault = true),
            TransactionCategory(name = "Transport & Commute", type = CategoryType.EXPENSE, iconName = "directions_bus", colorHex = "#3B82F6", isDefault = true),
            TransactionCategory(name = "Education & Books", type = CategoryType.EXPENSE, iconName = "school", colorHex = "#8B5CF6", isDefault = true),
            TransactionCategory(name = "Shopping & Clothing", type = CategoryType.EXPENSE, iconName = "shopping_bag", colorHex = "#EC4899", isDefault = true),
            TransactionCategory(name = "Entertainment & Hobbies", type = CategoryType.EXPENSE, iconName = "sports_esports", colorHex = "#06B6D4", isDefault = true),
            TransactionCategory(name = "Personal Care", type = CategoryType.EXPENSE, iconName = "spa", colorHex = "#10B981", isDefault = true),
            TransactionCategory(name = "Gifts & Treats", type = CategoryType.EXPENSE, iconName = "card_giftcard", colorHex = "#EAB308", isDefault = true),
            TransactionCategory(name = "Other Expenses", type = CategoryType.EXPENSE, iconName = "more_horiz", colorHex = "#6B7280", isDefault = true),

            TransactionCategory(name = "Pocket Money", type = CategoryType.INCOME, iconName = "savings", colorHex = "#10B981", isDefault = true),
            TransactionCategory(name = "Allowance", type = CategoryType.INCOME, iconName = "account_balance_wallet", colorHex = "#059669", isDefault = true),
            TransactionCategory(name = "Gifts Received", type = CategoryType.INCOME, iconName = "redeem", colorHex = "#EC4899", isDefault = true),
            TransactionCategory(name = "Internship / Work", type = CategoryType.INCOME, iconName = "work", colorHex = "#6366F1", isDefault = true),
            TransactionCategory(name = "Refunds", type = CategoryType.INCOME, iconName = "replay", colorHex = "#0284C7", isDefault = true),
            TransactionCategory(name = "Other Income", type = CategoryType.INCOME, iconName = "paid", colorHex = "#14B8A6", isDefault = true)
        )
        categoryDao().insertDefaultCategories(defaultCategories)

        // Initial Savings Goal with 0 saved
        savingsGoalDao().insertGoal(
            SavingsGoal(
                name = "New Drawing Tablet",
                targetAmountPaise = 500000L, // ₹5,000.00
                savedAmountPaise = 0L,       // ₹0 saved initially
                plantType = PlantType.SPROUT,
                plantStage = 1,
                notes = "For digital art illustrations"
            )
        )

        // Achievements
        val achievements = listOf(
            Achievement(code = "FIRST_SEED", title = "First Seed", description = "Recorded your very first transaction", iconName = "eco"),
            Achievement(code = "GETTING_ORGANISED", title = "Getting Organised", description = "Recorded transactions on 5 different days", iconName = "date_range", maxProgress = 5),
            Achievement(code = "CONSISTENCY_CHAMP", title = "Consistency Champion", description = "Maintained a 7-day recording routine", iconName = "verified", maxProgress = 7),
            Achievement(code = "RECEIPT_READY", title = "Receipt Ready", description = "Attached a supporting receipt photo", iconName = "receipt_long"),
            Achievement(code = "BALANCE_CHECKER", title = "Balance Checker", description = "Completed an account balance reconciliation", iconName = "task_alt"),
            Achievement(code = "SETTLEMENT_STAR", title = "Settlement Star", description = "Settled a split expense with a friend", iconName = "handshake"),
            Achievement(code = "SAVINGS_STARTER", title = "Savings Starter", description = "Created your first savings goal", iconName = "park"),
            Achievement(code = "GOAL_GETTER", title = "Goal Getter", description = "Reached a savings goal milestone", iconName = "emoji_events"),
            Achievement(code = "MONEY_DETECTIVE", title = "Money Detective", description = "Reviewed a monthly spending report", iconName = "insights"),
            Achievement(code = "FINANCIALLY_ORGANISED", title = "Financially Organised", description = "Completed a full monthly money review", iconName = "auto_stories")
        )
        achievementDao().insertDefaultAchievements(achievements)
    }

    suspend fun clearAllTransactionsAndNullifyData() {
        transactionDao().deleteAllTransactions()
        transactionDao().deleteAllAllocations()
        journalDao().deleteAllJournalEntries()
        journalDao().deleteAllJournalLines()
        savingsGoalDao().deleteAllMovements()
        savingsGoalDao().resetGoalsSaved()
        checkInDao().deleteAllCheckIns()
        reconciliationDao().deleteAllReconciliations()
        accountDao().nullifyAllAccountBalances()
        friendDao().nullifyAllFriendBalances()
    }
}
