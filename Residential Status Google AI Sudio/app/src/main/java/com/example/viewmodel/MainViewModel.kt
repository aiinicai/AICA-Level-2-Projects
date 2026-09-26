package com.example.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.AppDatabase
import com.example.data.AssessmentEntity
import com.example.data.AssessmentRepository
import com.example.engine.FemaEngine
import com.example.engine.IncomeTaxEngine
import com.example.model.FemaArrivalPurpose
import com.example.model.FemaDeparturePurpose
import com.example.model.FemaInput
import com.example.model.FemaResult
import com.example.model.ITCategory
import com.example.model.IncomeTaxInput
import com.example.model.IncomeTaxResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val repository: AssessmentRepository

    init {
        val db = AppDatabase.getDatabase(application)
        repository = AssessmentRepository(db.assessmentDao())
    }

    // Active Tab Navigation: 0 = Income Tax, 1 = FEMA, 2 = Simulator, 3 = History, 4 = Guide
    private val _selectedTab = MutableStateFlow(0)
    val selectedTab: StateFlow<Int> = _selectedTab.asStateFlow()

    fun selectTab(tabIndex: Int) {
        _selectedTab.value = tabIndex
    }

    // --- Income Tax State ---
    private val _itInput = MutableStateFlow(
        IncomeTaxInput(
            assesseeName = "Mr. Rahul Sharma",
            pan = "ABCPS1234F",
            assessmentYear = "AY 2026-27 (FY 2025-26)",
            daysInFY = 182,
            category = ITCategory.STANDARD,
            indianIncomeExceeds15L = false,
            daysInPreceding4Years = 365,
            residentIn2Of10Years = true,
            daysInPreceding7Years = 730,
            isIndianCitizen = true,
            notLiableToTaxElsewhere = false
        )
    )
    val itInput: StateFlow<IncomeTaxInput> = _itInput.asStateFlow()

    private val _itResult = MutableStateFlow(IncomeTaxEngine.determine(_itInput.value))
    val itResult: StateFlow<IncomeTaxResult> = _itResult.asStateFlow()

    fun updateItInput(update: (IncomeTaxInput) -> IncomeTaxInput) {
        val newInput = update(_itInput.value)
        _itInput.value = newInput
        _itResult.value = IncomeTaxEngine.determine(newInput)
    }

    fun saveItAssessment(notes: String = "", onSaved: () -> Unit = {}) {
        val currentInput = _itInput.value
        val currentResult = _itResult.value

        val entity = AssessmentEntity(
            clientName = currentInput.assesseeName.ifBlank { "Client Assessee" },
            pan = currentInput.pan.uppercase(),
            period = currentInput.assessmentYear,
            regime = "INCOME_TAX",
            statusCode = currentResult.status.code,
            statusTitle = currentResult.status.title,
            statutoryProvision = currentResult.statutoryProvision,
            summary = currentResult.executiveSummary,
            rationaleBullets = currentResult.rationale.joinToString("\n"),
            keyFactorsSummary = currentResult.keyFactors.entries.joinToString("; ") { "${it.key}: ${it.value}" },
            notes = notes
        )

        viewModelScope.launch {
            repository.saveAssessment(entity)
            onSaved()
        }
    }

    // --- FEMA State ---
    private val _femaInput = MutableStateFlow(
        FemaInput(
            assesseeName = "Mr. Rahul Sharma",
            pan = "ABCPS1234F",
            financialYear = "FY 2025-26",
            precedingYearDays = 183,
            hasGoneOutsideIndia = false,
            departurePurpose = FemaDeparturePurpose.TEMPORARY_OTHER,
            hasComeToIndia = false,
            arrivalPurpose = FemaArrivalPurpose.TEMPORARY_VISIT
        )
    )
    val femaInput: StateFlow<FemaInput> = _femaInput.asStateFlow()

    private val _femaResult = MutableStateFlow(FemaEngine.determine(_femaInput.value))
    val femaResult: StateFlow<FemaResult> = _femaResult.asStateFlow()

    fun updateFemaInput(update: (FemaInput) -> FemaInput) {
        val newInput = update(_femaInput.value)
        _femaInput.value = newInput
        _femaResult.value = FemaEngine.determine(newInput)
    }

    fun saveFemaAssessment(notes: String = "", onSaved: () -> Unit = {}) {
        val currentInput = _femaInput.value
        val currentResult = _femaResult.value

        val entity = AssessmentEntity(
            clientName = currentInput.assesseeName.ifBlank { "Client Assessee" },
            pan = currentInput.pan.uppercase(),
            period = currentInput.financialYear,
            regime = "FEMA",
            statusCode = currentResult.status.code,
            statusTitle = currentResult.status.title,
            statutoryProvision = currentResult.statutoryProvision,
            summary = currentResult.executiveSummary,
            rationaleBullets = currentResult.rationale.joinToString("\n"),
            keyFactorsSummary = currentResult.keyFactors.entries.joinToString("; ") { "${it.key}: ${it.value}" },
            notes = notes
        )

        viewModelScope.launch {
            repository.saveAssessment(entity)
            onSaved()
        }
    }

    // --- History State ---
    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _regimeFilter = MutableStateFlow("ALL") // "ALL", "INCOME_TAX", "FEMA"
    val regimeFilter: StateFlow<String> = _regimeFilter.asStateFlow()

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun setRegimeFilter(filter: String) {
        _regimeFilter.value = filter
    }

    val filteredHistory: StateFlow<List<AssessmentEntity>> = combine(
        repository.allAssessments,
        _searchQuery,
        _regimeFilter
    ) { all, query, filter ->
        all.filter { item ->
            val matchesFilter = when (filter) {
                "INCOME_TAX" -> item.regime == "INCOME_TAX"
                "FEMA" -> item.regime == "FEMA"
                else -> true
            }
            val matchesSearch = query.isBlank() ||
                item.clientName.contains(query, ignoreCase = true) ||
                item.pan.contains(query, ignoreCase = true) ||
                item.statusCode.contains(query, ignoreCase = true) ||
                item.period.contains(query, ignoreCase = true)

            matchesFilter && matchesSearch
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun deleteAssessment(id: Long) {
        viewModelScope.launch {
            repository.deleteAssessment(id)
        }
    }

    fun clearAllHistory() {
        viewModelScope.launch {
            repository.clearHistory()
        }
    }
}
