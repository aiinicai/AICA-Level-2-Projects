package com.example.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.ai.GeminiCfoAdvisor
import com.example.data.local.AssetEntity
import com.example.data.local.ChatMessageEntity
import com.example.data.local.FinPilotDatabase
import com.example.data.local.GoalEntity
import com.example.data.local.InsurancePolicyEntity
import com.example.data.local.LiabilityEntity
import com.example.data.local.NotificationEntity
import com.example.data.local.TransactionEntity
import com.example.data.local.UserProfileEntity
import com.example.data.model.AssetCategory
import com.example.data.model.GoalCategory
import com.example.data.repository.FinPilotRepository
import com.example.domain.engine.FinancialHealthEngine
import com.example.domain.engine.FinancialHealthResult
import com.example.domain.engine.InsuranceAnalysisResult
import com.example.domain.engine.RetirementAndInsuranceEngine
import com.example.domain.engine.RetirementPlanResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class FinPilotUiState(
    val profile: UserProfileEntity = UserProfileEntity(
        name = "Subhamjit Patra",
        email = "subhamjitpatra@gmail.com",
        profession = "Senior Software Architect",
        monthlyIncome = 225000.0,
        currencySymbol = "₹",
        city = "Bengaluru",
        taxRegime = "New Regime (Section 115BAC)"
    ),
    val assets: List<AssetEntity> = emptyList(),
    val liabilities: List<LiabilityEntity> = emptyList(),
    val goals: List<GoalEntity> = emptyList(),
    val transactions: List<TransactionEntity> = emptyList(),
    val insurancePolicies: List<InsurancePolicyEntity> = emptyList(),
    val cfoChatHistory: List<ChatMessageEntity> = emptyList(),
    val notifications: List<NotificationEntity> = emptyList(),
    val healthResult: FinancialHealthResult? = null,
    val retirementResult: RetirementPlanResult? = null,
    val insuranceAudit: InsuranceAnalysisResult? = null,
    val isGeneratingAdvice: Boolean = false,
    val isSyncing: Boolean = false
) {
    val totalAssets: Double get() = assets.sumOf { it.amount }
    val totalLiabilities: Double get() = liabilities.sumOf { it.outstandingAmount }
    val netWorth: Double get() = totalAssets - totalLiabilities
    val monthlyIncome: Double get() = profile.monthlyIncome
    val totalMonthlyEmi: Double get() = liabilities.sumOf { it.monthlyEmi }
    val monthlyExpenses: Double get() {
        val txExp = transactions.filter { it.type == com.example.data.model.TransactionType.EXPENSE }.sumOf { it.amount }
        return if (txExp > 0.0) txExp else 65000.0
    }
    val netCashFlow: Double get() = monthlyIncome - (monthlyExpenses + totalMonthlyEmi)
    val savingsRate: Double get() = if (monthlyIncome > 0) (netCashFlow / monthlyIncome) * 100.0 else 0.0
}

class FinPilotViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: FinPilotRepository
    private val _uiState = MutableStateFlow(FinPilotUiState())
    val uiState: StateFlow<FinPilotUiState> = _uiState.asStateFlow()

    init {
        val database = FinPilotDatabase.getDatabase(application)
        repository = FinPilotRepository(database.finPilotDao())

        viewModelScope.launch {
            repository.userProfile.collectLatest { prof ->
                if (prof != null) {
                    if (prof.currencySymbol == "$" || prof.name == "James Sterling") {
                        // Migrate legacy seed to Indian context
                        repository.seedIndianData()
                    } else {
                        _uiState.value = _uiState.value.copy(profile = prof)
                        recalculateFinances()
                    }
                } else {
                    repository.seedIndianData()
                }
            }
        }

        viewModelScope.launch {
            repository.assets.collectLatest { list ->
                if (list.isEmpty()) {
                    repository.seedIndianData()
                } else {
                    _uiState.value = _uiState.value.copy(assets = list)
                    recalculateFinances()
                }
            }
        }

        viewModelScope.launch {
            repository.liabilities.collectLatest { list ->
                _uiState.value = _uiState.value.copy(liabilities = list)
                recalculateFinances()
            }
        }

        viewModelScope.launch {
            repository.transactions.collectLatest { list ->
                _uiState.value = _uiState.value.copy(transactions = list)
                recalculateFinances()
            }
        }

        viewModelScope.launch {
            repository.insurancePolicies.collectLatest { list ->
                _uiState.value = _uiState.value.copy(insurancePolicies = list)
                recalculateFinances()
            }
        }

        viewModelScope.launch {
            repository.goals.collectLatest { list ->
                _uiState.value = _uiState.value.copy(goals = list)
                recalculateFinances()
            }
        }

        viewModelScope.launch {
            repository.chatMessages.collectLatest { list ->
                _uiState.value = _uiState.value.copy(cfoChatHistory = list)
            }
        }

        viewModelScope.launch {
            repository.notifications.collectLatest { list ->
                _uiState.value = _uiState.value.copy(notifications = list)
            }
        }
    }

    fun recalculateFinances() {
        val current = _uiState.value
        val health = FinancialHealthEngine.calculate(
            profile = current.profile,
            assets = current.assets,
            liabilities = current.liabilities,
            transactions = current.transactions,
            insurance = current.insurancePolicies
        )

        val retirement = RetirementAndInsuranceEngine.calculateRetirement(
            currentAge = current.profile.currentAge,
            retirementAge = current.profile.retirementAge,
            lifeExpectancyAge = 85,
            currentMonthlyExpense = current.monthlyExpenses,
            currentRetirementSavings = current.totalAssets * 0.55,
            currentMonthlyInvestment = current.netCashFlow.coerceAtLeast(15000.0)
        )

        val insurance = RetirementAndInsuranceEngine.analyzeInsurance(
            monthlyIncome = current.monthlyIncome,
            totalLiabilities = current.totalLiabilities,
            liquidAssets = current.assets.filter { it.category == AssetCategory.BANK || it.category == AssetCategory.CASH || it.category == AssetCategory.FIXED_DEPOSIT }.sumOf { it.amount },
            existingLifeCover = current.insurancePolicies.filter { it.type == com.example.data.model.InsuranceType.TERM_LIFE }.sumOf { it.sumAssured },
            existingHealthCover = current.insurancePolicies.filter { it.type == com.example.data.model.InsuranceType.HEALTH }.sumOf { it.sumAssured },
            familyDependentsCount = current.profile.dependentsCount
        )

        _uiState.value = current.copy(
            healthResult = health,
            retirementResult = retirement,
            insuranceAudit = insurance
        )
    }

    fun updateProfile(profile: UserProfileEntity) {
        viewModelScope.launch {
            repository.updateProfile(profile)
            _uiState.value = _uiState.value.copy(profile = profile)
            recalculateFinances()
        }
    }

    fun fetchAndSyncAllIndianDetails(onComplete: () -> Unit = {}) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSyncing = true)
            repository.seedIndianData()
            recalculateFinances()
            _uiState.value = _uiState.value.copy(isSyncing = false)
            onComplete()
        }
    }

    fun sendCfoQuery(query: String) {
        viewModelScope.launch {
            repository.addChatMessage(
                ChatMessageEntity(
                    sender = "USER",
                    message = query,
                    timestamp = System.currentTimeMillis()
                )
            )

            _uiState.value = _uiState.value.copy(isGeneratingAdvice = true)

            val current = _uiState.value
            val health = current.healthResult ?: FinancialHealthEngine.calculate(
                current.profile, current.assets, current.liabilities, current.transactions, current.insurancePolicies
            )

            val advice = GeminiCfoAdvisor.consultCfo(
                userQuery = query,
                profile = current.profile,
                netWorth = current.netWorth,
                totalAssets = current.totalAssets,
                totalLiabilities = current.totalLiabilities,
                monthlyIncome = current.monthlyIncome,
                healthResult = health,
                assets = current.assets,
                liabilities = current.liabilities
            )

            repository.addChatMessage(
                ChatMessageEntity(
                    sender = "AI_CFO",
                    message = advice,
                    timestamp = System.currentTimeMillis()
                )
            )

            _uiState.value = _uiState.value.copy(isGeneratingAdvice = false)
        }
    }

    fun addAsset(name: String, category: AssetCategory, amount: Double, institution: String) {
        viewModelScope.launch {
            repository.addAsset(
                AssetEntity(
                    name = name,
                    category = category,
                    amount = amount,
                    institution = institution
                )
            )
            recalculateFinances()
        }
    }

    fun deleteAsset(asset: AssetEntity) {
        viewModelScope.launch {
            repository.deleteAsset(asset)
            recalculateFinances()
        }
    }

    fun deleteLiability(liability: LiabilityEntity) {
        viewModelScope.launch {
            repository.deleteLiability(liability)
            recalculateFinances()
        }
    }

    fun addGoal(title: String, category: GoalCategory, targetAmount: Double, currentAmount: Double, targetYears: Int) {
        viewModelScope.launch {
            repository.addGoal(
                GoalEntity(
                    title = title,
                    category = category,
                    targetAmount = targetAmount,
                    currentAmount = currentAmount,
                    targetYears = targetYears
                )
            )
            recalculateFinances()
        }
    }

    fun deleteGoal(goal: GoalEntity) {
        viewModelScope.launch {
            repository.deleteGoal(goal)
            recalculateFinances()
        }
    }

    fun markNotificationActioned(id: Long) {
        viewModelScope.launch {
            repository.markNotificationActioned(id)
        }
    }
}
