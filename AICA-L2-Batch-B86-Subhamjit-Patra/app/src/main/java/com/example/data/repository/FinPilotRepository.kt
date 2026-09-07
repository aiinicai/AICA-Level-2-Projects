package com.example.data.repository

import com.example.data.local.AssetEntity
import com.example.data.local.ChatMessageEntity
import com.example.data.local.FinPilotDao
import com.example.data.local.FinPilotDatabase
import com.example.data.local.GoalEntity
import com.example.data.local.InsurancePolicyEntity
import com.example.data.local.LiabilityEntity
import com.example.data.local.NotificationEntity
import com.example.data.local.TransactionEntity
import com.example.data.local.UserProfileEntity
import kotlinx.coroutines.flow.Flow

class FinPilotRepository(private val dao: FinPilotDao) {
    val userProfile: Flow<UserProfileEntity?> = dao.getUserProfile()
    val assets: Flow<List<AssetEntity>> = dao.getAllAssets()
    val liabilities: Flow<List<LiabilityEntity>> = dao.getAllLiabilities()
    val transactions: Flow<List<TransactionEntity>> = dao.getAllTransactions()
    val goals: Flow<List<GoalEntity>> = dao.getAllGoals()
    val insurancePolicies: Flow<List<InsurancePolicyEntity>> = dao.getAllInsurancePolicies()
    val notifications: Flow<List<NotificationEntity>> = dao.getAllNotifications()
    val chatMessages: Flow<List<ChatMessageEntity>> = dao.getAllChatMessages()

    suspend fun updateProfile(profile: UserProfileEntity) = dao.insertOrUpdateProfile(profile)
    suspend fun addAsset(asset: AssetEntity) = dao.insertAsset(asset)
    suspend fun deleteAsset(asset: AssetEntity) = dao.deleteAsset(asset)

    suspend fun addLiability(liability: LiabilityEntity) = dao.insertLiability(liability)
    suspend fun deleteLiability(liability: LiabilityEntity) = dao.deleteLiability(liability)

    suspend fun addTransaction(transaction: TransactionEntity) = dao.insertTransaction(transaction)
    suspend fun deleteTransaction(transaction: TransactionEntity) = dao.deleteTransaction(transaction)

    suspend fun addGoal(goal: GoalEntity) = dao.insertGoal(goal)
    suspend fun updateGoal(goal: GoalEntity) = dao.updateGoal(goal)
    suspend fun deleteGoal(goal: GoalEntity) = dao.deleteGoal(goal)

    suspend fun addInsurancePolicy(policy: InsurancePolicyEntity) = dao.insertInsurancePolicy(policy)
    suspend fun deleteInsurancePolicy(policy: InsurancePolicyEntity) = dao.deleteInsurancePolicy(policy)

    suspend fun addNotification(notification: NotificationEntity) = dao.insertNotification(notification)
    suspend fun markNotificationActioned(id: Long) = dao.markNotificationActioned(id)

    suspend fun addChatMessage(message: ChatMessageEntity) = dao.insertChatMessage(message)
    suspend fun clearChat() = dao.clearChatHistory()

    suspend fun seedIndianData(customProfile: UserProfileEntity? = null) {
        FinPilotDatabase.seedIndianFinancialData(dao, customProfile)
    }
}
