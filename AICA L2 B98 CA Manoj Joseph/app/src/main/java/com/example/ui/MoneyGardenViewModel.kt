package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.AppDatabase
import com.example.data.model.AccountType
import com.example.data.model.Achievement
import com.example.data.model.CategoryType
import com.example.data.model.CheckInActivity
import com.example.data.model.FinancialAccount
import com.example.data.model.FinancialTransaction
import com.example.data.model.Friend
import com.example.data.model.PlantType
import com.example.data.model.ReconciliationRecord
import com.example.data.model.SavingsGoal
import com.example.data.model.TransactionCategory
import com.example.data.model.TransactionType
import com.example.data.model.UserProfile
import com.example.data.repository.FinanceRepository
import com.example.domain.AccountingEngine
import com.example.domain.HealthScoreBreakdown
import com.example.domain.HealthScoreCalculator
import com.example.data.firebase.AuthService
import com.google.firebase.auth.FirebaseUser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.Calendar

data class DashboardUiState(
    val accounts: List<FinancialAccount> = emptyList(),
    val categories: List<TransactionCategory> = emptyList(),
    val friends: List<Friend> = emptyList(),
    val transactions: List<FinancialTransaction> = emptyList(),
    val savingsGoals: List<SavingsGoal> = emptyList(),
    val achievements: List<Achievement> = emptyList(),
    val checkIns: List<CheckInActivity> = emptyList(),
    val reconciliations: List<ReconciliationRecord> = emptyList(),
    val userProfile: UserProfile? = null,
    val totalCashAndBankPaise: Long = 0L,
    val totalReceivablesPaise: Long = 0L,
    val totalPayablesPaise: Long = 0L,
    val netFriendsPositionPaise: Long = 0L,
    val monthlyIncomePaise: Long = 0L,
    val monthlyPersonalExpensePaise: Long = 0L,
    val healthScore: HealthScoreBreakdown = HealthScoreCalculator.calculate(emptyList(), emptyList(), emptyList(), emptyList()),
    val isCheckedInToday: Boolean = false,
    val balanceSheet: AccountingEngine.BalanceSheetReport? = null
)

class MoneyGardenViewModel(application: Application) : AndroidViewModel(application) {

    private val db = AppDatabase.getInstance(application)
    val repository = FinanceRepository(db)

    private val _userMessage = MutableStateFlow<String?>(null)
    val userMessage: StateFlow<String?> = _userMessage

    init {
        viewModelScope.launch {
            try {
                // Clear out legacy default seeded friends so register starts empty for user customization
                repository.deleteExistingSeedFriends()
            } catch (e: Exception) {
                // Ignore initialization errors
            }
        }
    }

    val uiState: StateFlow<DashboardUiState> = combine(
        repository.accountsFlow,
        repository.categoriesFlow,
        repository.friendsFlow,
        repository.transactionsFlow,
        repository.savingsGoalsFlow,
        repository.achievementsFlow,
        repository.checkInsFlow,
        repository.reconciliationsFlow,
        repository.userProfileFlow
    ) { params ->
        val accounts = params[0] as List<FinancialAccount>
        val categories = params[1] as List<TransactionCategory>
        val friends = params[2] as List<Friend>
        val transactions = params[3] as List<FinancialTransaction>
        val savingsGoals = params[4] as List<SavingsGoal>
        val achievements = params[5] as List<Achievement>
        val checkIns = params[6] as List<CheckInActivity>
        val reconciliations = params[7] as List<ReconciliationRecord>
        val userProfile = params[8] as UserProfile?

        val totalCashAndBank = accounts.filter { it.isActive }.sumOf { it.currentBalancePaise }
        val totalReceivables = friends.filter { it.isActive }.sumOf { it.totalReceivablePaise }
        val totalPayables = friends.filter { it.isActive }.sumOf { it.totalPayablePaise }
        val netFriendsPos = totalReceivables - totalPayables

        // Monthly calculations (current calendar month)
        val cal = Calendar.getInstance()
        val currentMonth = cal.get(Calendar.MONTH)
        val currentYear = cal.get(Calendar.YEAR)

        val txCal = Calendar.getInstance()
        var monthIncome = 0L
        var monthExpense = 0L
        var totalHistoricalIncome = 0L
        var totalHistoricalPersonalExpense = 0L

        for (tx in transactions) {
            if (tx.isReversed) continue
            txCal.timeInMillis = tx.date
            val isCurrentMonth = (txCal.get(Calendar.MONTH) == currentMonth && txCal.get(Calendar.YEAR) == currentYear)

            when (tx.type) {
                TransactionType.INCOME -> {
                    totalHistoricalIncome += tx.personalAmountPaise
                    if (isCurrentMonth) monthIncome += tx.personalAmountPaise
                }
                TransactionType.EXPENSE -> {
                    totalHistoricalPersonalExpense += tx.personalAmountPaise
                    if (isCurrentMonth) monthExpense += tx.personalAmountPaise
                }
                else -> {}
            }
        }

        val openingBalancesTotal = accounts.sumOf { it.openingBalancePaise }
        val balanceSheet = AccountingEngine.computeBalanceSheet(
            cashAndBankTotalPaise = totalCashAndBank,
            receivablesTotalPaise = totalReceivables,
            payablesTotalPaise = totalPayables,
            totalHistoricalIncomePaise = totalHistoricalIncome,
            totalHistoricalPersonalExpensePaise = totalHistoricalPersonalExpense,
            openingBalancesTotalPaise = openingBalancesTotal
        )

        val healthScore = HealthScoreCalculator.calculate(
            activities = checkIns,
            reconciliations = reconciliations,
            friends = friends,
            goals = savingsGoals
        )

        val todayIso = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date())
        val checkedInToday = checkIns.any { it.dateIso == todayIso }

        DashboardUiState(
            accounts = accounts,
            categories = categories,
            friends = friends,
            transactions = transactions,
            savingsGoals = savingsGoals,
            achievements = achievements,
            checkIns = checkIns,
            reconciliations = reconciliations,
            userProfile = userProfile,
            totalCashAndBankPaise = totalCashAndBank,
            totalReceivablesPaise = totalReceivables,
            totalPayablesPaise = totalPayables,
            netFriendsPositionPaise = netFriendsPos,
            monthlyIncomePaise = monthIncome,
            monthlyPersonalExpensePaise = monthExpense,
            healthScore = healthScore,
            isCheckedInToday = checkedInToday,
            balanceSheet = balanceSheet
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = DashboardUiState()
    )

    fun clearUserMessage() {
        _userMessage.value = null
    }

    fun postPersonalExpense(
        date: Long,
        amountPaise: Long,
        description: String,
        accountId: Long,
        categoryId: Long,
        receiptUri: String? = null,
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.postExpense(
                    date = date,
                    totalAmountPaise = amountPaise,
                    personalSharePaise = amountPaise,
                    description = description,
                    accountId = accountId,
                    categoryId = categoryId,
                    receiptUri = receiptUri,
                    notes = notes
                )
                _userMessage.value = "🌱 Recorded expense of ${AccountingEngine.formatPaise(amountPaise)}"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun postSharedExpense(
        date: Long,
        totalAmountPaise: Long,
        personalSharePaise: Long,
        friendAllocations: Map<Long, Long>,
        description: String,
        accountId: Long,
        categoryId: Long,
        receiptUri: String? = null,
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.postExpense(
                    date = date,
                    totalAmountPaise = totalAmountPaise,
                    personalSharePaise = personalSharePaise,
                    description = description,
                    accountId = accountId,
                    categoryId = categoryId,
                    friendAllocations = friendAllocations,
                    receiptUri = receiptUri,
                    notes = notes
                )
                _userMessage.value = "🤝 Shared expense recorded! Friends owe: ${AccountingEngine.formatPaise(totalAmountPaise - personalSharePaise)}"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun postFriendPaidExpense(
        date: Long,
        totalPurchaseAmountPaise: Long,
        arpitaSharePaise: Long,
        description: String,
        friendId: Long,
        categoryId: Long,
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.postFriendPaidExpense(
                    date = date,
                    totalPurchaseAmountPaise = totalPurchaseAmountPaise,
                    arpitaSharePaise = arpitaSharePaise,
                    description = description,
                    friendId = friendId,
                    categoryId = categoryId,
                    notes = notes
                )
                _userMessage.value = "📝 Recorded shared expense. Payable to friend: ${AccountingEngine.formatPaise(arpitaSharePaise)}"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun postIncome(
        date: Long,
        amountPaise: Long,
        description: String,
        destinationAccountId: Long,
        categoryId: Long,
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.postIncome(
                    date = date,
                    amountPaise = amountPaise,
                    description = description,
                    destinationAccountId = destinationAccountId,
                    categoryId = categoryId,
                    notes = notes
                )
                _userMessage.value = "✨ Income of ${AccountingEngine.formatPaise(amountPaise)} added to your garden!"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun postTransfer(
        date: Long,
        amountPaise: Long,
        fromAccountId: Long,
        toAccountId: Long,
        description: String
    ) {
        viewModelScope.launch {
            try {
                repository.postTransfer(
                    date = date,
                    amountPaise = amountPaise,
                    fromAccountId = fromAccountId,
                    toAccountId = toAccountId,
                    description = description
                )
                _userMessage.value = "🔄 Transferred ${AccountingEngine.formatPaise(amountPaise)} between accounts"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun recordRepaymentFromFriend(
        amountPaise: Long,
        friendId: Long,
        accountId: Long,
        date: Long = System.currentTimeMillis(),
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.postRepaymentReceived(
                    date = date,
                    amountPaise = amountPaise,
                    friendId = friendId,
                    accountId = accountId,
                    notes = notes
                )
                _userMessage.value = "🎉 Repayment of ${AccountingEngine.formatPaise(amountPaise)} recorded!"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun recordRepaymentToFriend(
        amountPaise: Long,
        friendId: Long,
        accountId: Long,
        date: Long = System.currentTimeMillis(),
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.postRepaymentPaid(
                    date = date,
                    amountPaise = amountPaise,
                    friendId = friendId,
                    accountId = accountId,
                    notes = notes
                )
                _userMessage.value = "✅ Paid friend ${AccountingEngine.formatPaise(amountPaise)}. Settled up!"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun recordOpeningBalances(
        asOfDate: Long,
        accountBalances: Map<Long, Long>,
        friendReceivables: Map<Long, Long>,
        friendPayables: Map<Long, Long>
    ) {
        viewModelScope.launch {
            try {
                repository.recordOpeningBalances(
                    asOfDate = asOfDate,
                    accountBalances = accountBalances,
                    friendReceivables = friendReceivables,
                    friendPayables = friendPayables
                )
                _userMessage.value = "⚖️ Opening balances established as of selected date!"
            } catch (e: Exception) {
                _userMessage.value = "Opening Balance Error: ${e.message}"
            }
        }
    }

    fun nullifyAllExistingData() {
        viewModelScope.launch {
            try {
                repository.nullifyAllData()
                _userMessage.value = "🧹 All existing transactions and balances have been nullified. Ready for fresh opening balances!"
            } catch (e: Exception) {
                _userMessage.value = "Nullify Error: ${e.message}"
            }
        }
    }

    fun reverseTransaction(txId: Long, reason: String) {
        viewModelScope.launch {
            try {
                repository.reverseTransaction(txId, reason)
                _userMessage.value = "🔄 Transaction #$txId safely reversed in audit ledger"
            } catch (e: Exception) {
                _userMessage.value = "Reversal error: ${e.message}"
            }
        }
    }

    fun reconcileAccount(accountId: Long, statementBalancePaise: Long, notes: String? = null) {
        viewModelScope.launch {
            try {
                val isMatch = repository.recordReconciliation(accountId, statementBalancePaise, notes)
                if (isMatch) {
                    _userMessage.value = "⚖️ Statement matches ledger perfectly! Balanced."
                } else {
                    _userMessage.value = "⚠️ Balance difference noted in audit log."
                }
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun contributeToGoal(goalId: Long, amountPaise: Long, notes: String? = null) {
        viewModelScope.launch {
            try {
                repository.contributeToGoal(goalId, amountPaise, notes)
                _userMessage.value = "🌿 Added ${AccountingEngine.formatPaise(amountPaise)} to savings goal! Virtual plant grew!"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun withdrawFromGoal(goalId: Long, amountPaise: Long, notes: String? = null) {
        viewModelScope.launch {
            try {
                repository.withdrawFromGoal(goalId, amountPaise, notes)
                _userMessage.value = "Withdrew ${AccountingEngine.formatPaise(amountPaise)} from goal"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun createSavingsGoal(
        name: String,
        targetAmountPaise: Long,
        targetDate: Long? = null,
        plantType: PlantType = PlantType.SPROUT,
        notes: String? = null
    ) {
        viewModelScope.launch {
            try {
                repository.createSavingsGoal(name, targetAmountPaise, targetDate, plantType, notes)
                _userMessage.value = "🌱 New savings seed planted: $name"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun recordNoSpendCheckIn() {
        viewModelScope.launch {
            try {
                repository.recordNoSpendCheckIn()
                _userMessage.value = "🌟 Great job! Recorded 'No-Spend Day' check-in!"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun addFriend(name: String, nickname: String?, contact: String?, notes: String?) {
        viewModelScope.launch {
            try {
                repository.saveFriend(
                    Friend(
                        name = name,
                        nickname = nickname,
                        contactInfo = contact,
                        notes = notes
                    )
                )
                _userMessage.value = "Added $name to friends register"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun deleteFriend(friendId: Long) {
        viewModelScope.launch {
            try {
                repository.deleteFriend(friendId)
                _userMessage.value = "Friend removed from register"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun deleteAllFriends() {
        viewModelScope.launch {
            try {
                repository.deleteAllFriends()
                _userMessage.value = "All friends removed from register"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun addAccount(name: String, type: AccountType, openingBalancePaise: Long) {
        viewModelScope.launch {
            try {
                repository.saveAccount(
                    FinancialAccount(
                        name = name,
                        accountType = type,
                        openingBalancePaise = openingBalancePaise,
                        currentBalancePaise = openingBalancePaise
                    )
                )
                _userMessage.value = "Added $name account"
            } catch (e: Exception) {
                _userMessage.value = "Error: ${e.message}"
            }
        }
    }

    fun markMonthlyReviewCompleted() {
        viewModelScope.launch {
            repository.unlockAchievement("FINANCIALLY_ORGANISED")
            _userMessage.value = "🎉 Monthly Review completed! Achievement unlocked!"
        }
    }

    fun markReportReviewed() {
        viewModelScope.launch {
            repository.unlockAchievement("MONEY_DETECTIVE")
        }
    }

    fun setPreferredDisplayName(displayName: String, firebaseUser: FirebaseUser? = null) {
        viewModelScope.launch {
            try {
                repository.updateUserProfileDisplayName(displayName, markAsPreferred = true)
                firebaseUser?.let { user ->
                    AuthService.updateRemoteDisplayName(getApplication(), user, displayName)
                }
                _userMessage.value = "Welcome, $displayName! 🌿"
            } catch (e: Exception) {
                _userMessage.value = "Error updating name: ${e.message}"
            }
        }
    }

    fun updateUserDisplayName(displayName: String) {
        viewModelScope.launch {
            val current = repository.userProfileFlow
            repository.updateUserProfileDisplayName(displayName, markAsPreferred = false)
        }
    }

    fun addCategory(
        name: String,
        type: CategoryType,
        iconName: String = "category",
        colorHex: String = "#10B981",
        onCreated: (Long) -> Unit = {}
    ) {
        viewModelScope.launch {
            try {
                val newCategory = TransactionCategory(
                    name = name.trim(),
                    type = type,
                    iconName = iconName,
                    colorHex = colorHex,
                    isDefault = false
                )
                val id = repository.saveCategory(newCategory)
                _userMessage.value = "Category \"${name.trim()}\" added successfully! 🏷️"
                onCreated(id)
            } catch (e: Exception) {
                _userMessage.value = "Failed to add category: ${e.message}"
            }
        }
    }

    fun deleteCategory(categoryId: Long) {
        viewModelScope.launch {
            try {
                repository.deleteCategory(categoryId)
                _userMessage.value = "Category deleted"
            } catch (e: Exception) {
                _userMessage.value = "Failed to delete category: ${e.message}"
            }
        }
    }
}
