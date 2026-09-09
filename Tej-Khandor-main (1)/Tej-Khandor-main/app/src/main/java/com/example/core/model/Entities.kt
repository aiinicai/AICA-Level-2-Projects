package com.example.core.model

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(
    tableName = "businesses",
    indices = [Index("isDefault")]
)
data class BusinessEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val name: String,
    val ownerName: String? = null,
    val businessType: String = "Retail",
    val phone: String? = null,
    val gstin: String? = null,
    val pan: String? = null,
    val currencyCode: String = "INR",
    val upiId: String? = null,
    val address: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val isDefault: Boolean = false
)

@Entity(
    tableName = "parties",
    foreignKeys = [
        ForeignKey(
            entity = BusinessEntity::class,
            parentColumns = ["id"],
            childColumns = ["businessId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index("businessId"),
        Index(value = ["businessId", "phone"]),
        Index("name")
    ]
)
data class PartyEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val businessId: String,
    val name: String,
    val phone: String? = null,
    val email: String? = null,
    val address: String? = null,
    val gstin: String? = null,
    val pan: String? = null,
    // Positive opening balance = Party owes business (Receivable/Lena)
    // Negative opening balance = Business owes party (Payable/Dena)
    val openingBalancePaise: Long = 0L,
    val creditLimitPaise: Long? = null,
    val paymentTermsDays: Int? = null,
    val notes: String? = null,
    val tags: String? = null, // e.g. "VIP,Wholesale"
    val roles: String = "CUSTOMER", // e.g. "CUSTOMER,SUPPLIER"
    val isArchived: Boolean = false,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(
    tableName = "accounts",
    foreignKeys = [
        ForeignKey(
            entity = BusinessEntity::class,
            parentColumns = ["id"],
            childColumns = ["businessId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("businessId")]
)
data class AccountEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val businessId: String,
    val name: String, // e.g., "Cash Register", "HDFC Current A/C", "Business UPI"
    val type: String = "CASH", // CASH, BANK, UPI
    val accountNumber: String? = null,
    val ifscCode: String? = null,
    val upiId: String? = null,
    val openingBalancePaise: Long = 0L,
    val isArchived: Boolean = false,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(
    tableName = "transactions",
    foreignKeys = [
        ForeignKey(
            entity = BusinessEntity::class,
            parentColumns = ["id"],
            childColumns = ["businessId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index("businessId"),
        Index("partyId"),
        Index("accountId"),
        Index("transactionDate"),
        Index("status"),
        Index(value = ["businessId", "partyId", "transactionDate"])
    ]
)
data class TransactionEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val businessId: String,
    val partyId: String? = null, // Null for pure general expense or transfer
    val accountId: String? = null, // Linked payment account (Cash, Bank, UPI)
    val destinationAccountId: String? = null, // Used for internal account transfers
    val type: String, // GAVE, GOT, SALE, PURCHASE, EXPENSE, INCOME, TRANSFER, OPENING_BALANCE, ADJUSTMENT
    val amountPaise: Long, // Positive integer in paise
    val transactionDate: Long = System.currentTimeMillis(),
    val dueDate: Long? = null,
    val referenceNumber: String? = null, // Bill no, Invoice no, UTR, Cheque no
    val paymentMode: String = "CASH", // CASH, BANK_TRANSFER, UPI, CHEQUE, CREDIT
    val categoryId: String? = null,
    val notes: String? = null,
    val billImagePath: String? = null,
    val status: String = "POSTED", // POSTED, VOIDED, REVERSED
    val reversalTransactionId: String? = null,
    val voidReason: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(
    tableName = "categories",
    foreignKeys = [
        ForeignKey(
            entity = BusinessEntity::class,
            parentColumns = ["id"],
            childColumns = ["businessId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("businessId")]
)
data class CategoryEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val businessId: String,
    val name: String,
    val iconName: String = "receipt",
    val isExpense: Boolean = true,
    val isDefault: Boolean = false
)

@Entity(
    tableName = "audit_logs",
    indices = [Index("businessId"), Index("timestamp")]
)
data class AuditLogEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val businessId: String,
    val action: String, // CREATE_TX, VOID_TX, REVERSE_TX, TRANSFER, BACKUP_EXPORT, RESTORE
    val entityType: String,
    val entityId: String,
    val details: String,
    val timestamp: Long = System.currentTimeMillis()
)
