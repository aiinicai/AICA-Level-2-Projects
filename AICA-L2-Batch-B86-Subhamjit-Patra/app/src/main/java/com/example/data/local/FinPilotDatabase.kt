package com.example.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.data.model.AssetCategory
import com.example.data.model.ExpenseCategory
import com.example.data.model.GoalCategory
import com.example.data.model.IncomeCategory
import com.example.data.model.InsuranceType
import com.example.data.model.LiabilityCategory
import com.example.data.model.ReminderType
import com.example.data.model.RiskProfile
import com.example.data.model.TransactionType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class Converters {
    @TypeConverter fun fromAssetCat(v: AssetCategory?): String? = v?.name
    @TypeConverter fun toAssetCat(v: String?): AssetCategory? = v?.let { AssetCategory.valueOf(it) }

    @TypeConverter fun fromLiabCat(v: LiabilityCategory?): String? = v?.name
    @TypeConverter fun toLiabCat(v: String?): LiabilityCategory? = v?.let { LiabilityCategory.valueOf(it) }

    @TypeConverter fun fromTxType(v: TransactionType?): String? = v?.name
    @TypeConverter fun toTxType(v: String?): TransactionType? = v?.let { TransactionType.valueOf(it) }

    @TypeConverter fun fromExpCat(v: ExpenseCategory?): String? = v?.name
    @TypeConverter fun toExpCat(v: String?): ExpenseCategory? = v?.let { ExpenseCategory.valueOf(it) }

    @TypeConverter fun fromIncCat(v: IncomeCategory?): String? = v?.name
    @TypeConverter fun toIncCat(v: String?): IncomeCategory? = v?.let { IncomeCategory.valueOf(it) }

    @TypeConverter fun fromRisk(v: RiskProfile?): String? = v?.name
    @TypeConverter fun toRisk(v: String?): RiskProfile? = v?.let { RiskProfile.valueOf(it) }

    @TypeConverter fun fromGoalCat(v: GoalCategory?): String? = v?.name
    @TypeConverter fun toGoalCat(v: String?): GoalCategory? = v?.let { GoalCategory.valueOf(it) }

    @TypeConverter fun fromInsType(v: InsuranceType?): String? = v?.name
    @TypeConverter fun toInsType(v: String?): InsuranceType? = v?.let { InsuranceType.valueOf(it) }

    @TypeConverter fun fromRemType(v: ReminderType?): String? = v?.name
    @TypeConverter fun toRemType(v: String?): ReminderType? = v?.let { ReminderType.valueOf(it) }
}

@Database(
    entities = [
        UserProfileEntity::class,
        AssetEntity::class,
        LiabilityEntity::class,
        TransactionEntity::class,
        GoalEntity::class,
        InsurancePolicyEntity::class,
        NotificationEntity::class,
        ChatMessageEntity::class
    ],
    version = 2,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class FinPilotDatabase : RoomDatabase() {
    abstract fun finPilotDao(): FinPilotDao

    companion object {
        @Volatile
        private var INSTANCE: FinPilotDatabase? = null

        fun getDatabase(context: Context): FinPilotDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    FinPilotDatabase::class.java,
                    "finpilot_database"
                )
                .fallbackToDestructiveMigration()
                .addCallback(object : Callback() {
                    override fun onCreate(db: SupportSQLiteDatabase) {
                        super.onCreate(db)
                        CoroutineScope(Dispatchers.IO).launch {
                            INSTANCE?.finPilotDao()?.let { seedIndianFinancialData(it, null) }
                        }
                    }
                }).build()
                INSTANCE = instance
                instance
            }
        }

        suspend fun seedIndianFinancialData(dao: FinPilotDao, customProfile: UserProfileEntity? = null) {
            val profile = customProfile ?: UserProfileEntity(
                id = 1,
                name = "Subhamjit Patra",
                email = "subhamjitpatra@gmail.com",
                profession = "Principal Software Architect",
                familyMembersCount = 3,
                dependentsCount = 2,
                riskProfile = RiskProfile.MODERATE,
                monthlyIncome = 225000.0,
                currentAge = 32,
                retirementAge = 55,
                currencySymbol = "₹",
                city = "Bengaluru",
                taxRegime = "New Regime (Section 115BAC)"
            )

            dao.insertOrUpdateProfile(profile)

            // Clear old records to guarantee clean Indian portfolio
            dao.deleteAllAssets()
            dao.deleteAllLiabilities()
            dao.deleteAllTransactions()
            dao.deleteAllGoals()
            dao.deleteAllInsurancePolicies()
            dao.deleteAllNotifications()

            // Indian Assets (~₹2.06 Crore gross assets)
            dao.insertAsset(AssetEntity(name = "HDFC Salary & Emergency Savings", category = AssetCategory.BANK, amount = 450000.0, institution = "HDFC Bank (Whitefield)", expectedReturnRate = 4.0))
            dao.insertAsset(AssetEntity(name = "SBI MaxiGain Liquid Reserve", category = AssetCategory.CASH, amount = 250000.0, institution = "State Bank of India", expectedReturnRate = 6.5))
            dao.insertAsset(AssetEntity(name = "Employee Provident Fund (EPF)", category = AssetCategory.EPF, amount = 1680000.0, institution = "EPFO India (8.25%)", expectedReturnRate = 8.25))
            dao.insertAsset(AssetEntity(name = "Public Provident Fund (PPF)", category = AssetCategory.PPF, amount = 850000.0, institution = "SBI PPF (7.1% EEE)", expectedReturnRate = 7.1))
            dao.insertAsset(AssetEntity(name = "National Pension System (NPS Tier-1)", category = AssetCategory.NPS, amount = 720000.0, institution = "NSDL / HDFC Pension", expectedReturnRate = 10.5))
            dao.insertAsset(AssetEntity(name = "Zerodha Direct Equity (Nifty 50 & Midcaps)", category = AssetCategory.SHARES, amount = 3450000.0, institution = "Zerodha Kite", expectedReturnRate = 13.5))
            dao.insertAsset(AssetEntity(name = "Groww Mutual Fund SIPs (Flexicap & Index)", category = AssetCategory.MUTUAL_FUNDS, amount = 2650000.0, institution = "Groww / Parag Parikh & UTI", expectedReturnRate = 12.8))
            dao.insertAsset(AssetEntity(name = "RBI Sovereign Gold Bonds (SGB)", category = AssetCategory.GOLD, amount = 650000.0, institution = "RBI SGB Tranches", expectedReturnRate = 10.0))
            dao.insertAsset(AssetEntity(name = "Bengaluru 3BHK Apartment", category = AssetCategory.REAL_ESTATE, amount = 9800000.0, institution = "Prestige Tranquility", expectedReturnRate = 7.5))

            // Indian Liabilities (~₹47.2 Lakhs total) -> Net Worth = ~₹1.59 Crore
            dao.insertLiability(LiabilityEntity(name = "SBI Home Loan (MaxiGain)", category = LiabilityCategory.HOME_LOAN, outstandingAmount = 4150000.0, interestRate = 8.4, monthlyEmi = 43200.0, tenureMonthsRemaining = 168))
            dao.insertLiability(LiabilityEntity(name = "HDFC Auto Loan (EV SUV)", category = LiabilityCategory.VEHICLE_LOAN, outstandingAmount = 525000.0, interestRate = 8.7, monthlyEmi = 15800.0, tenureMonthsRemaining = 38))
            dao.insertLiability(LiabilityEntity(name = "ICICI Coral & Amazon Pay Credit Card", category = LiabilityCategory.CREDIT_CARD, outstandingAmount = 45000.0, interestRate = 0.0, monthlyEmi = 45000.0, tenureMonthsRemaining = 1))

            // Monthly Inflows & Outflows in INR (Income: ₹2,25,000, Expenses: ₹68,000, EMIs: ₹59,000 -> Monthly Surplus: ~₹98,000)
            dao.insertTransaction(TransactionEntity(title = "Monthly In-Hand Salary Credit", amount = 225000.0, type = TransactionType.INCOME, incomeCategory = IncomeCategory.SALARY))
            dao.insertTransaction(TransactionEntity(title = "SBI Home Loan EMI Auto-Debit", amount = 43200.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.EMI))
            dao.insertTransaction(TransactionEntity(title = "HDFC Car Loan EMI", amount = 15800.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.EMI))
            dao.insertTransaction(TransactionEntity(title = "Household Groceries & BigBasket", amount = 24000.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.HOUSEHOLD))
            dao.insertTransaction(TransactionEntity(title = "Bengaluru Apartment Society Maintenance", amount = 7500.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.UTILITIES))
            dao.insertTransaction(TransactionEntity(title = "BESCOM Electricity & ACT Fibernet", amount = 4800.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.UTILITIES))
            dao.insertTransaction(TransactionEntity(title = "Child International School Fee", amount = 18000.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.EDUCATION))
            dao.insertTransaction(TransactionEntity(title = "Family Health & Term Insurance Provision", amount = 4500.0, type = TransactionType.EXPENSE, expenseCategory = ExpenseCategory.INSURANCE))

            // Goals in INR
            dao.insertGoal(GoalEntity(title = "Retirement Corpus (FIRE @ 55)", category = GoalCategory.RETIREMENT, targetAmount = 65000000.0, currentAmount = 9450000.0, targetYears = 23, expectedReturnRate = 12.0, inflationRate = 6.0))
            dao.insertGoal(GoalEntity(title = "Child Higher Education Fund", category = GoalCategory.EDUCATION, targetAmount = 5000000.0, currentAmount = 1450000.0, targetYears = 12, expectedReturnRate = 11.5, inflationRate = 7.0))
            dao.insertGoal(GoalEntity(title = "Home Loan Early Prepayment", category = GoalCategory.WEALTH, targetAmount = 4150000.0, currentAmount = 1200000.0, targetYears = 4, expectedReturnRate = 8.5, inflationRate = 5.0))
            dao.insertGoal(GoalEntity(title = "Annual International Vacation", category = GoalCategory.VACATION, targetAmount = 450000.0, currentAmount = 320000.0, targetYears = 1, expectedReturnRate = 6.5, inflationRate = 5.0))

            // Insurance Policies in INR
            dao.insertInsurancePolicy(InsurancePolicyEntity(provider = "HDFC Life", policyName = "Click 2 Protect Super (Pure Term)", type = InsuranceType.TERM_LIFE, sumAssured = 25000000.0, annualPremium = 28500.0, renewalDate = "15 Nov 2026"))
            dao.insertInsurancePolicy(InsurancePolicyEntity(provider = "Care Health", policyName = "Care Supreme + ₹50L Super Top-Up", type = InsuranceType.HEALTH, sumAssured = 3000000.0, annualPremium = 19200.0, renewalDate = "20 Jan 2027"))
            dao.insertInsurancePolicy(InsurancePolicyEntity(provider = "Tata AIG", policyName = "Comprehensive Personal Accident Cover", type = InsuranceType.ACCIDENT, sumAssured = 10000000.0, annualPremium = 6800.0, renewalDate = "05 Mar 2027"))

            // Notifications & Statutory Reminders in Indian Context
            dao.insertNotification(NotificationEntity(title = "Advance Tax Q2 Installment (Section 208)", description = "Advance tax due on Sept 15. Check TDS credit in Form 26AS/AIS to avoid 234B/234C interest.", type = ReminderType.BUDGET_ALERT, dueDateString = "Sep 15, 2026"))
            dao.insertNotification(NotificationEntity(title = "Zerodha & Groww Monthly SIP Auto-Debit", description = "₹65,000 monthly SIP scheduled for Nifty 50 Index & Flexi Cap funds on 10th.", type = ReminderType.SIP_DUE, dueDateString = "Sep 10, 2026"))
            dao.insertNotification(NotificationEntity(title = "SBI MaxiGain Home Loan EMI", description = "₹43,200 auto-debit scheduled from HDFC salary account.", type = ReminderType.EMI_DUE, dueDateString = "Sep 05, 2026"))
            dao.insertNotification(NotificationEntity(title = "PPF Annual ₹1.5 Lakh Section 80C Deposit", description = "Deposit ₹1,50,000 before 5th of the month to maximize compound tax-free interest.", type = ReminderType.GOAL_REVIEW, dueDateString = "Apr 05, 2027"))

            // AI CFO Initial Message in Indian Context
            dao.insertChatMessage(ChatMessageEntity(
                sender = "AI_CFO",
                message = "Namaste ${profile.name}! I am your Pocket CFO Personal AI. Your portfolio has been consolidated across HDFC, SBI, Zerodha, and EPFO. Your audited net worth is ₹1.59 Crore with a strong Financial Health Score of 88/100 (Grade A). How can I assist your wealth strategy or tax planning today?"
            ))
        }
    }
}
