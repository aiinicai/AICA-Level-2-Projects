package com.example.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.example.data.model.AssetCategory
import com.example.data.model.ExpenseCategory
import com.example.data.model.GoalCategory
import com.example.data.model.IncomeCategory
import com.example.data.model.InsuranceType
import com.example.data.model.LiabilityCategory
import com.example.data.model.ReminderType
import com.example.data.model.RiskProfile
import com.example.data.model.TransactionType

@Entity(tableName = "user_profile")
data class UserProfileEntity(
    @PrimaryKey val id: Int = 1,
    val name: String = "Subhamjit Patra",
    val email: String = "subhamjitpatra@gmail.com",
    val profession: String = "Senior Software Architect",
    val familyMembersCount: Int = 3,
    val dependentsCount: Int = 2,
    val riskProfile: RiskProfile = RiskProfile.MODERATE,
    val monthlyIncome: Double = 225000.0,
    val currentAge: Int = 32,
    val retirementAge: Int = 55,
    val currencySymbol: String = "₹",
    val city: String = "Bengaluru",
    val taxRegime: String = "New Regime (Section 115BAC)"
)

@Entity(tableName = "assets")
data class AssetEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val category: AssetCategory,
    val amount: Double,
    val institution: String,
    val expectedReturnRate: Double = 8.0
)

@Entity(tableName = "liabilities")
data class LiabilityEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val category: LiabilityCategory,
    val outstandingAmount: Double,
    val interestRate: Double,
    val monthlyEmi: Double,
    val tenureMonthsRemaining: Int
)

@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    val amount: Double,
    val type: TransactionType,
    val expenseCategory: ExpenseCategory? = null,
    val incomeCategory: IncomeCategory? = null,
    val dateTimestamp: Long = System.currentTimeMillis()
)

@Entity(tableName = "goals")
data class GoalEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    val category: GoalCategory,
    val targetAmount: Double,
    val currentAmount: Double,
    val targetYears: Int,
    val expectedReturnRate: Double = 12.0,
    val inflationRate: Double = 6.0
)

@Entity(tableName = "insurance_policies")
data class InsurancePolicyEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val provider: String,
    val policyName: String,
    val type: InsuranceType,
    val sumAssured: Double,
    val annualPremium: Double,
    val renewalDate: String
)

@Entity(tableName = "notifications")
data class NotificationEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val title: String,
    val description: String,
    val type: ReminderType,
    val dueDateString: String,
    val isActioned: Boolean = false
)

@Entity(tableName = "chat_messages")
data class ChatMessageEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val sender: String, // "USER" or "AI_CFO"
    val message: String,
    val timestamp: Long = System.currentTimeMillis()
)
