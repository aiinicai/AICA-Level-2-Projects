package com.example.core.database

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.core.model.AccountEntity
import com.example.core.model.AuditLogEntity
import com.example.core.model.BusinessEntity
import com.example.core.model.CategoryEntity
import com.example.core.model.PartyEntity
import com.example.core.model.TransactionEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface BusinessDao {
    @Query("SELECT * FROM businesses ORDER BY isDefault DESC, createdAt ASC")
    fun getAllBusinesses(): Flow<List<BusinessEntity>>

    @Query("SELECT * FROM businesses WHERE id = :id LIMIT 1")
    suspend fun getBusinessById(id: String): BusinessEntity?

    @Query("SELECT * FROM businesses WHERE isDefault = 1 LIMIT 1")
    suspend fun getDefaultBusiness(): BusinessEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBusiness(business: BusinessEntity)

    @Update
    suspend fun updateBusiness(business: BusinessEntity)

    @Query("UPDATE businesses SET isDefault = 0")
    suspend fun clearDefault()

    @Query("UPDATE businesses SET isDefault = 1 WHERE id = :id")
    suspend fun setDefault(id: String)
}

@Dao
interface PartyDao {
    @Query("SELECT * FROM parties WHERE businessId = :businessId AND isArchived = 0 ORDER BY updatedAt DESC")
    fun getPartiesByBusiness(businessId: String): Flow<List<PartyEntity>>

    @Query("SELECT * FROM parties WHERE businessId = :businessId ORDER BY updatedAt DESC")
    fun getAllPartiesIncludingArchived(businessId: String): Flow<List<PartyEntity>>

    @Query("SELECT * FROM parties WHERE id = :id LIMIT 1")
    suspend fun getPartyById(id: String): PartyEntity?

    @Query("SELECT * FROM parties WHERE id = :id LIMIT 1")
    fun observePartyById(id: String): Flow<PartyEntity?>

    @Query("""
        SELECT * FROM parties 
        WHERE businessId = :businessId 
        AND (name LIKE '%' || :query || '%' OR phone LIKE '%' || :query || '%' OR address LIKE '%' || :query || '%')
        ORDER BY name ASC
    """)
    fun searchParties(businessId: String, query: String): Flow<List<PartyEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertParty(party: PartyEntity)

    @Update
    suspend fun updateParty(party: PartyEntity)

    @Query("UPDATE parties SET isArchived = :isArchived, updatedAt = :timestamp WHERE id = :partyId")
    suspend fun setArchived(partyId: String, isArchived: Boolean, timestamp: Long = System.currentTimeMillis())

    @Query("DELETE FROM parties WHERE id = :id")
    suspend fun deletePartyById(id: String)
}

@Dao
interface TransactionDao {
    @Query("""
        SELECT * FROM transactions 
        WHERE businessId = :businessId 
        ORDER BY transactionDate DESC, createdAt DESC
    """)
    fun getTransactionsByBusiness(businessId: String): Flow<List<TransactionEntity>>

    @Query("""
        SELECT * FROM transactions 
        WHERE partyId = :partyId 
        ORDER BY transactionDate ASC, createdAt ASC
    """)
    fun getTransactionsForParty(partyId: String): Flow<List<TransactionEntity>>

    @Query("""
        SELECT * FROM transactions 
        WHERE partyId = :partyId 
        ORDER BY transactionDate ASC, createdAt ASC
    """)
    suspend fun getTransactionsForPartySync(partyId: String): List<TransactionEntity>

    @Query("""
        SELECT * FROM transactions 
        WHERE businessId = :businessId AND (accountId = :accountId OR destinationAccountId = :accountId)
        ORDER BY transactionDate DESC, createdAt DESC
    """)
    fun getTransactionsForAccount(businessId: String, accountId: String): Flow<List<TransactionEntity>>

    @Query("""
        SELECT * FROM transactions 
        WHERE businessId = :businessId AND type = 'EXPENSE' AND status = 'POSTED'
        ORDER BY transactionDate DESC
    """)
    fun getExpenses(businessId: String): Flow<List<TransactionEntity>>

    @Query("SELECT * FROM transactions WHERE id = :id LIMIT 1")
    suspend fun getTransactionById(id: String): TransactionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTransaction(transaction: TransactionEntity)

    @Update
    suspend fun updateTransaction(transaction: TransactionEntity)

    @Query("UPDATE transactions SET status = 'VOIDED', voidReason = :reason, updatedAt = :timestamp WHERE id = :id")
    suspend fun voidTransaction(id: String, reason: String, timestamp: Long = System.currentTimeMillis())

    @Query("""
        SELECT * FROM transactions 
        WHERE businessId = :businessId AND partyId = :partyId AND amountPaise = :amountPaise 
        AND transactionDate >= :sinceTimestamp AND status = 'POSTED'
        LIMIT 1
    """)
    suspend fun findPotentialDuplicate(businessId: String, partyId: String, amountPaise: Long, sinceTimestamp: Long): TransactionEntity?

    @Query("DELETE FROM transactions WHERE id = :id")
    suspend fun deleteTransactionById(id: String)

    @Query("DELETE FROM transactions WHERE partyId = :partyId")
    suspend fun deleteTransactionsForParty(partyId: String)

    @Query("DELETE FROM transactions WHERE accountId = :accountId OR destinationAccountId = :accountId")
    suspend fun deleteTransactionsForAccount(accountId: String)
}

@Dao
interface AccountDao {
    @Query("SELECT * FROM accounts WHERE businessId = :businessId AND isArchived = 0 ORDER BY createdAt ASC")
    fun getAccountsByBusiness(businessId: String): Flow<List<AccountEntity>>

    @Query("SELECT * FROM accounts WHERE id = :id LIMIT 1")
    suspend fun getAccountById(id: String): AccountEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAccount(account: AccountEntity)

    @Update
    suspend fun updateAccount(account: AccountEntity)

    @Query("DELETE FROM accounts WHERE id = :id")
    suspend fun deleteAccountById(id: String)
}

@Dao
interface CategoryDao {
    @Query("SELECT * FROM categories WHERE businessId = :businessId ORDER BY name ASC")
    fun getCategoriesByBusiness(businessId: String): Flow<List<CategoryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCategory(category: CategoryEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCategories(categories: List<CategoryEntity>)
}

@Dao
interface AuditLogDao {
    @Query("SELECT * FROM audit_logs WHERE businessId = :businessId ORDER BY timestamp DESC LIMIT 100")
    fun getAuditLogs(businessId: String): Flow<List<AuditLogEntity>>

    @Insert
    suspend fun insertAuditLog(log: AuditLogEntity)
}
