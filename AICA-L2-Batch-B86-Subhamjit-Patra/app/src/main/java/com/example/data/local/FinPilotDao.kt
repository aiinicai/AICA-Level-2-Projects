package com.example.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface FinPilotDao {
    // User Profile
    @Query("SELECT * FROM user_profile WHERE id = 1 LIMIT 1")
    fun getUserProfile(): Flow<UserProfileEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOrUpdateProfile(profile: UserProfileEntity)

    // Assets
    @Query("SELECT * FROM assets ORDER BY amount DESC")
    fun getAllAssets(): Flow<List<AssetEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAsset(asset: AssetEntity)

    @Delete
    suspend fun deleteAsset(asset: AssetEntity)

    @Query("DELETE FROM assets")
    suspend fun deleteAllAssets()

    // Liabilities
    @Query("SELECT * FROM liabilities ORDER BY outstandingAmount DESC")
    fun getAllLiabilities(): Flow<List<LiabilityEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLiability(liability: LiabilityEntity)

    @Delete
    suspend fun deleteLiability(liability: LiabilityEntity)

    @Query("DELETE FROM liabilities")
    suspend fun deleteAllLiabilities()

    // Transactions
    @Query("SELECT * FROM transactions ORDER BY dateTimestamp DESC")
    fun getAllTransactions(): Flow<List<TransactionEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTransaction(transaction: TransactionEntity)

    @Delete
    suspend fun deleteTransaction(transaction: TransactionEntity)

    @Query("DELETE FROM transactions")
    suspend fun deleteAllTransactions()

    // Goals
    @Query("SELECT * FROM goals ORDER BY id ASC")
    fun getAllGoals(): Flow<List<GoalEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertGoal(goal: GoalEntity)

    @Update
    suspend fun updateGoal(goal: GoalEntity)

    @Delete
    suspend fun deleteGoal(goal: GoalEntity)

    @Query("DELETE FROM goals")
    suspend fun deleteAllGoals()

    // Insurance
    @Query("SELECT * FROM insurance_policies ORDER BY sumAssured DESC")
    fun getAllInsurancePolicies(): Flow<List<InsurancePolicyEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertInsurancePolicy(policy: InsurancePolicyEntity)

    @Delete
    suspend fun deleteInsurancePolicy(policy: InsurancePolicyEntity)

    @Query("DELETE FROM insurance_policies")
    suspend fun deleteAllInsurancePolicies()

    // Notifications
    @Query("SELECT * FROM notifications ORDER BY id DESC")
    fun getAllNotifications(): Flow<List<NotificationEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNotification(notification: NotificationEntity)

    @Query("UPDATE notifications SET isActioned = 1 WHERE id = :id")
    suspend fun markNotificationActioned(id: Long)

    @Query("DELETE FROM notifications")
    suspend fun deleteAllNotifications()

    // Chat
    @Query("SELECT * FROM chat_messages ORDER BY timestamp ASC")
    fun getAllChatMessages(): Flow<List<ChatMessageEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertChatMessage(message: ChatMessageEntity)

    @Query("DELETE FROM chat_messages")
    suspend fun clearChatHistory()
}
