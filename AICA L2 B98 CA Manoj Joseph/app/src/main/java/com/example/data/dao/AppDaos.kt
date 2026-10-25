package com.example.data.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.data.model.AccountType
import com.example.data.model.Achievement
import com.example.data.model.CheckInActivity
import com.example.data.model.FinancialAccount
import com.example.data.model.FinancialTransaction
import com.example.data.model.Friend
import com.example.data.model.JournalEntry
import com.example.data.model.JournalLine
import com.example.data.model.ReconciliationRecord
import com.example.data.model.SavingsGoal
import com.example.data.model.SavingsGoalMovement
import com.example.data.model.TransactionAllocation
import com.example.data.model.TransactionCategory
import com.example.data.model.UserProfile
import kotlinx.coroutines.flow.Flow

@Dao
interface AccountDao {
    @Query("SELECT * FROM financial_accounts WHERE isActive = 1 ORDER BY name ASC")
    fun getAllAccountsFlow(): Flow<List<FinancialAccount>>

    @Query("SELECT * FROM financial_accounts ORDER BY name ASC")
    suspend fun getAllAccounts(): List<FinancialAccount>

    @Query("SELECT * FROM financial_accounts WHERE id = :id")
    suspend fun getAccountById(id: Long): FinancialAccount?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAccount(account: FinancialAccount): Long

    @Update
    suspend fun updateAccount(account: FinancialAccount)

    @Query("UPDATE financial_accounts SET currentBalancePaise = :newBalance WHERE id = :id")
    suspend fun updateBalance(id: Long, newBalance: Long)

    @Query("UPDATE financial_accounts SET openingBalancePaise = :opening, currentBalancePaise = :opening, openingDate = :date WHERE id = :id")
    suspend fun setOpeningBalance(id: Long, opening: Long, date: Long)

    @Query("UPDATE financial_accounts SET openingBalancePaise = :opening, currentBalancePaise = :current, openingDate = :date WHERE id = :id")
    suspend fun setOpeningAndCurrentBalance(id: Long, opening: Long, current: Long, date: Long)

    @Query("UPDATE financial_accounts SET openingBalancePaise = 0, currentBalancePaise = 0")
    suspend fun nullifyAllAccountBalances()
}

@Dao
interface CategoryDao {
    @Query("SELECT * FROM transaction_categories ORDER BY isDefault DESC, name ASC")
    fun getAllCategoriesFlow(): Flow<List<TransactionCategory>>

    @Query("SELECT * FROM transaction_categories")
    suspend fun getAllCategories(): List<TransactionCategory>

    @Query("SELECT * FROM transaction_categories WHERE id = :id")
    suspend fun getCategoryById(id: Long): TransactionCategory?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCategory(category: TransactionCategory): Long

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertDefaultCategories(categories: List<TransactionCategory>)

    @Delete
    suspend fun deleteCategory(category: TransactionCategory)

    @Query("DELETE FROM transaction_categories WHERE id = :id")
    suspend fun deleteCategoryById(id: Long)
}

@Dao
interface FriendDao {
    @Query("SELECT * FROM friends WHERE isActive = 1 ORDER BY name ASC")
    fun getAllFriendsFlow(): Flow<List<Friend>>

    @Query("SELECT * FROM friends ORDER BY name ASC")
    suspend fun getAllFriends(): List<Friend>

    @Query("SELECT * FROM friends WHERE id = :id")
    suspend fun getFriendById(id: Long): Friend?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertFriend(friend: Friend): Long

    @Update
    suspend fun updateFriend(friend: Friend)

    @Query("UPDATE friends SET totalReceivablePaise = :rec, totalPayablePaise = :pay WHERE id = :id")
    suspend fun updateReceivablePayable(id: Long, rec: Long, pay: Long)

    @Query("UPDATE friends SET openingReceivablePaise = :rec, openingPayablePaise = :pay, totalReceivablePaise = :rec, totalPayablePaise = :pay, openingDate = :date WHERE id = :id")
    suspend fun setFriendOpeningBalances(id: Long, rec: Long, pay: Long, date: Long)

    @Query("UPDATE friends SET openingReceivablePaise = :openRec, openingPayablePaise = :openPay, totalReceivablePaise = :totRec, totalPayablePaise = :totPay, openingDate = :date WHERE id = :id")
    suspend fun setFriendOpeningAndCurrentBalances(id: Long, openRec: Long, openPay: Long, totRec: Long, totPay: Long, date: Long)

    @Query("UPDATE friends SET openingReceivablePaise = 0, openingPayablePaise = 0, totalReceivablePaise = 0, totalPayablePaise = 0")
    suspend fun nullifyAllFriendBalances()

    @Delete
    suspend fun deleteFriend(friend: Friend)

    @Query("DELETE FROM friends WHERE id = :id")
    suspend fun deleteFriendById(id: Long)

    @Query("DELETE FROM friends WHERE name IN (:names)")
    suspend fun deleteFriendsByNames(names: List<String>)

    @Query("DELETE FROM friends")
    suspend fun deleteAllFriends()
}

@Dao
interface TransactionDao {
    @Query("SELECT * FROM financial_transactions ORDER BY date DESC, id DESC")
    fun getAllTransactionsFlow(): Flow<List<FinancialTransaction>>

    @Query("SELECT * FROM financial_transactions ORDER BY date DESC, id DESC")
    suspend fun getAllTransactions(): List<FinancialTransaction>

    @Query("SELECT * FROM financial_transactions WHERE id = :id")
    suspend fun getTransactionById(id: Long): FinancialTransaction?

    @Query("SELECT * FROM financial_transactions WHERE idempotencyKey = :key LIMIT 1")
    suspend fun getByIdempotencyKey(key: String): FinancialTransaction?

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertTransaction(transaction: FinancialTransaction): Long

    @Update
    suspend fun updateTransaction(transaction: FinancialTransaction)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAllocations(allocations: List<TransactionAllocation>)

    @Query("SELECT * FROM transaction_allocations WHERE transactionId = :txId")
    suspend fun getAllocationsForTransaction(txId: Long): List<TransactionAllocation>

    @Query("SELECT * FROM transaction_allocations WHERE friendId = :friendId")
    suspend fun getAllocationsForFriend(friendId: Long): List<TransactionAllocation>

    @Query("DELETE FROM financial_transactions")
    suspend fun deleteAllTransactions()

    @Query("DELETE FROM transaction_allocations")
    suspend fun deleteAllAllocations()
}

@Dao
interface JournalDao {
    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertJournalEntry(entry: JournalEntry): Long

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertJournalLines(lines: List<JournalLine>)

    @Query("SELECT * FROM journal_entries WHERE transactionId = :txId")
    suspend fun getEntriesForTransaction(txId: Long): List<JournalEntry>

    @Query("SELECT * FROM journal_lines WHERE journalEntryId = :entryId")
    suspend fun getLinesForEntry(entryId: Long): List<JournalLine>

    @Query("SELECT * FROM journal_lines")
    suspend fun getAllJournalLines(): List<JournalLine>

    @Query("DELETE FROM journal_entries")
    suspend fun deleteAllJournalEntries()

    @Query("DELETE FROM journal_lines")
    suspend fun deleteAllJournalLines()
}

@Dao
interface SavingsGoalDao {
    @Query("SELECT * FROM savings_goals ORDER BY isCompleted ASC, targetDate ASC")
    fun getAllGoalsFlow(): Flow<List<SavingsGoal>>

    @Query("SELECT * FROM savings_goals WHERE id = :id")
    suspend fun getGoalById(id: Long): SavingsGoal?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertGoal(goal: SavingsGoal): Long

    @Update
    suspend fun updateGoal(goal: SavingsGoal)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMovement(movement: SavingsGoalMovement): Long

    @Query("SELECT * FROM savings_goal_movements WHERE goalId = :goalId ORDER BY date DESC")
    suspend fun getMovementsForGoal(goalId: Long): List<SavingsGoalMovement>

    @Query("DELETE FROM savings_goal_movements")
    suspend fun deleteAllMovements()

    @Query("UPDATE savings_goals SET savedAmountPaise = 0, plantStage = 1, isCompleted = 0")
    suspend fun resetGoalsSaved()
}

@Dao
interface AchievementDao {
    @Query("SELECT * FROM achievements ORDER BY isUnlocked DESC, code ASC")
    fun getAllAchievementsFlow(): Flow<List<Achievement>>

    @Query("SELECT * FROM achievements")
    suspend fun getAllAchievements(): List<Achievement>

    @Query("SELECT * FROM achievements WHERE code = :code")
    suspend fun getAchievementByCode(code: String): Achievement?

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertDefaultAchievements(achievements: List<Achievement>)

    @Update
    suspend fun updateAchievement(achievement: Achievement)
}

@Dao
interface CheckInDao {
    @Query("SELECT * FROM check_in_activities ORDER BY dateIso DESC")
    fun getAllActivitiesFlow(): Flow<List<CheckInActivity>>

    @Query("SELECT * FROM check_in_activities WHERE dateIso = :dateIso LIMIT 1")
    suspend fun getByDate(dateIso: String): CheckInActivity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun recordCheckIn(activity: CheckInActivity)

    @Query("DELETE FROM check_in_activities")
    suspend fun deleteAllCheckIns()
}

@Dao
interface ReconciliationDao {
    @Query("SELECT * FROM reconciliation_records ORDER BY date DESC")
    fun getAllReconciliationsFlow(): Flow<List<ReconciliationRecord>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRecord(record: ReconciliationRecord): Long

    @Query("DELETE FROM reconciliation_records")
    suspend fun deleteAllReconciliations()
}

@Dao
interface UserProfileDao {
    @Query("SELECT * FROM user_profiles LIMIT 1")
    fun getUserProfileFlow(): Flow<UserProfile?>

    @Query("SELECT * FROM user_profiles LIMIT 1")
    suspend fun getUserProfile(): UserProfile?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveUserProfile(profile: UserProfile)

    @Query("UPDATE user_profiles SET displayName = :displayName, hasSetPreferredName = 1")
    suspend fun updateDisplayName(displayName: String)

    @Query("DELETE FROM user_profiles")
    suspend fun deleteAllProfiles()
}
