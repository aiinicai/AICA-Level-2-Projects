package com.example.viewmodel

import android.app.Application
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.data.JsonTaxSectionRepository
import com.example.data.TaxSectionRepository
import com.example.data.SectionFilterOption
import com.example.model.ChatMessage
import com.example.model.ExplanationMode
import com.example.model.MappingStatus
import com.example.model.MappingType
import com.example.model.MessageSender
import com.example.model.TaxImportAudit
import com.example.model.TaxSection
import com.example.model.TaxSourceDocument
import com.example.network.GeminiService
import com.example.network.GeminiTaxService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID

enum class AppTab(val title: String) {
    HOME("Home"),
    SECTIONS("Sections"),
    COMPARE("Compare"),
    AI("AI"),
    SOURCE_IMPORT("Source Import")
}

enum class CompareTab(val title: String) {
    SUMMARY("AI Summary"),
    WHATS_CHANGED("What's Changed?"),
    PRACTICAL_IMPACT("Practical Impact"),
    STATUTORY_TEXT("Statutory Text")
}

data class TaxBridgeUiState(
    val currentTab: AppTab = AppTab.HOME,
    val searchQuery: String = "",
    val selectedCategory: String = "All",
    val selectedStatusFilter: MappingStatus? = null,
    val selectedFilterOption: SectionFilterOption = SectionFilterOption.ALL,
    val filteredSections: List<TaxSection> = emptyList(),
    val allSections: List<TaxSection> = emptyList(),
    val categories: List<String> = emptyList(),
    val selectedDetailSection: TaxSection? = null,
    val detailExplanationMode: ExplanationMode = ExplanationMode.PROFESSIONAL,
    val detailExplanationText: String = "",
    val isDetailAiLoading: Boolean = false,
    
    // Database Source info
    val databaseVersion: String = "2.0",
    val databaseSource: String = "",

    // Compare Screen State
    val compareSection: TaxSection? = null,
    val isSideBySideView: Boolean = true,
    val activeCompareTab: CompareTab = CompareTab.STATUTORY_TEXT,
    
    // AI Assistant State
    val aiContextSection: TaxSection? = null,
    val aiExplanationMode: ExplanationMode = ExplanationMode.PROFESSIONAL,
    val chatInputText: String = "",
    val chatMessages: List<ChatMessage> = emptyList(),
    val isAiThinking: Boolean = false,

    // Official Source Ingestion Pipeline State
    val availableImportDocuments: List<TaxSourceDocument> = emptyList(),
    val selectedImportDocument: TaxSourceDocument? = null,
    val candidateImportSections: List<TaxSection> = emptyList(),
    val latestImportAudit: TaxImportAudit? = null,
    val ingestionStats: com.example.model.IngestionStats = com.example.model.IngestionStats(),
    val isImporting: Boolean = false,
    val isValidating: Boolean = false
) {
    // Stat metrics across whole catalogue
    val totalSectionsCount: Int get() = allSections.size
    val mappedSectionsCount: Int get() = allSections.count { 
        it.effectiveCorrespondingProvisions.isNotEmpty() &&
        it.mappingType != MappingType.NO_CORRESPONDING_PROVISION &&
        it.mappingType != MappingType.REPEALED
    }
    val noCorrespondenceCount: Int get() = allSections.count { 
        it.mappingType == MappingType.NO_CORRESPONDING_PROVISION ||
        it.mappingType == MappingType.REPEALED ||
        it.effectiveCorrespondingProvisions.isEmpty()
    }
    val pendingReviewCount: Int get() = allSections.count { it.mappingStatus == MappingStatus.PENDING_REVIEW }
    val verifiedCount: Int get() = allSections.count { it.mappingStatus == MappingStatus.VERIFIED }
    val textLoadedCount: Int get() = allSections.count { it.statutoryTextLoaded || !it.oldText.isNullOrBlank() || !it.newText.isNullOrBlank() }
    val textNotLoadedCount: Int get() = allSections.count { !it.statutoryTextLoaded && it.oldText.isNullOrBlank() && it.newText.isNullOrBlank() }
}

class TaxBridgeViewModel(
    private val repository: TaxSectionRepository,
    private val geminiService: GeminiService = GeminiTaxService(),
    private val rawAssetsReader: (() -> String)? = null
) : ViewModel() {

    private val _uiState = MutableStateFlow(TaxBridgeUiState())
    val uiState: StateFlow<TaxBridgeUiState> = _uiState.asStateFlow()

    init {
        loadData()
    }

    fun loadData() {
        val all = repository.getAllSections()
        val cats = repository.getCategories()
        val defaultSection = all.firstOrNull()
        val docs = repository.getAvailableDocuments()
        val defaultDoc = docs.firstOrNull()
        
        val initialMessages = listOf(
            ChatMessage(
                id = UUID.randomUUID().toString(),
                sender = MessageSender.AI,
                text = "Welcome to TaxBridge AI V1.2.\n\nYou can search, compare, and inspect statutory provisions between the Income-tax Act, 1961 and the Income-tax Act, 2025. Data marked 'DATA NOT YET LOADED' will be populated upon official Gazette verification.",
                attachedSectionNumber = null,
                isStatutoryQuote = false
            )
        )

        _uiState.update {
            it.copy(
                allSections = all,
                filteredSections = all,
                categories = cats,
                selectedDetailSection = defaultSection,
                compareSection = defaultSection,
                aiContextSection = defaultSection,
                databaseVersion = repository.getVersion(),
                databaseSource = repository.getSource(),
                chatMessages = initialMessages,
                availableImportDocuments = docs,
                selectedImportDocument = defaultDoc,
                candidateImportSections = all,
                ingestionStats = repository.getIngestionStats()
            )
        }
        
        defaultSection?.let {
            loadDetailExplanation(it, ExplanationMode.PROFESSIONAL)
        }
    }

    fun selectTab(tab: AppTab) {
        _uiState.update { it.copy(currentTab = tab) }
    }

    fun updateSearchQuery(query: String) {
        _uiState.update { state ->
            val filtered = repository.searchSections(
                query = query,
                category = state.selectedCategory,
                status = state.selectedStatusFilter,
                filterOption = state.selectedFilterOption
            )
            state.copy(searchQuery = query, filteredSections = filtered)
        }
    }

    fun selectCategoryFilter(category: String) {
        _uiState.update { state ->
            val filtered = repository.searchSections(
                query = state.searchQuery,
                category = category,
                status = state.selectedStatusFilter,
                filterOption = state.selectedFilterOption
            )
            state.copy(selectedCategory = category, filteredSections = filtered)
        }
    }

    fun selectStatusFilter(status: MappingStatus?) {
        _uiState.update { state ->
            val filtered = repository.searchSections(
                query = state.searchQuery,
                category = state.selectedCategory,
                status = status,
                filterOption = state.selectedFilterOption
            )
            state.copy(selectedStatusFilter = status, filteredSections = filtered)
        }
    }

    fun selectFilterOption(option: SectionFilterOption) {
        _uiState.update { state ->
            val filtered = repository.searchSections(
                query = state.searchQuery,
                category = state.selectedCategory,
                status = state.selectedStatusFilter,
                filterOption = option
            )
            state.copy(selectedFilterOption = option, filteredSections = filtered)
        }
    }

    fun openSectionDetail(section: TaxSection) {
        _uiState.update {
            it.copy(
                selectedDetailSection = section,
                compareSection = section,
                aiContextSection = section
            )
        }
        loadDetailExplanation(section, _uiState.value.detailExplanationMode)
    }

    fun openSectionByOldNumber(oldNumber: String) {
        val found = repository.getSectionByOldNumber(oldNumber)
        if (found != null) {
            openSectionDetail(found)
        }
    }

    fun setDetailExplanationMode(mode: ExplanationMode) {
        _uiState.update { it.copy(detailExplanationMode = mode) }
        _uiState.value.selectedDetailSection?.let { section ->
            loadDetailExplanation(section, mode)
        }
    }

    private fun loadDetailExplanation(section: TaxSection, mode: ExplanationMode) {
        _uiState.update { it.copy(isDetailAiLoading = true) }
        viewModelScope.launch {
            val result = geminiService.generateSectionExplanation(section, mode)
            val explanation = result.getOrElse { "Statutory analysis unavailable: ${it.message}" }
            _uiState.update {
                it.copy(
                    detailExplanationText = explanation,
                    isDetailAiLoading = false
                )
            }
        }
    }

    fun selectCompareSection(section: TaxSection) {
        _uiState.update { it.copy(compareSection = section) }
    }

    fun toggleSideBySide(enabled: Boolean) {
        _uiState.update { it.copy(isSideBySideView = enabled) }
    }

    fun setCompareTab(tab: CompareTab) {
        _uiState.update { it.copy(activeCompareTab = tab) }
    }

    fun setAiContextSection(section: TaxSection?) {
        _uiState.update { it.copy(aiContextSection = section) }
    }

    fun setAiExplanationMode(mode: ExplanationMode) {
        _uiState.update { it.copy(aiExplanationMode = mode) }
    }

    fun updateChatInput(text: String) {
        _uiState.update { it.copy(chatInputText = text) }
    }

    fun sendChatMessage(presetQuery: String? = null) {
        val messageText = presetQuery ?: _uiState.value.chatInputText.trim()
        if (messageText.isBlank()) return

        val attached = _uiState.value.aiContextSection
        val mode = _uiState.value.aiExplanationMode

        val userMsg = ChatMessage(
            id = UUID.randomUUID().toString(),
            sender = MessageSender.USER,
            text = messageText,
            attachedSectionNumber = attached?.oldSectionNumber,
            explanationMode = mode
        )

        val updatedMessages = _uiState.value.chatMessages + userMsg
        _uiState.update {
            it.copy(
                chatMessages = updatedMessages,
                chatInputText = "",
                isAiThinking = true
            )
        }

        viewModelScope.launch {
            val historyPairs = updatedMessages
                .filter { it.sender != MessageSender.SYSTEM }
                .takeLast(6)
                .map {
                    (if (it.sender == MessageSender.USER) "user" else "model") to it.text
                }

            val result = geminiService.askQuestion(
                userQuestion = messageText,
                attachedSection = attached,
                mode = mode,
                history = historyPairs
            )

            val replyText = result.getOrElse { "Unable to generate response: ${it.message}" }

            val aiMsg = ChatMessage(
                id = UUID.randomUUID().toString(),
                sender = MessageSender.AI,
                text = replyText,
                attachedSectionNumber = attached?.oldSectionNumber,
                explanationMode = mode
            )

            _uiState.update {
                it.copy(
                    chatMessages = it.chatMessages + aiMsg,
                    isAiThinking = false
                )
            }
        }
    }

    fun askAboutSectionInAiTab(section: TaxSection, prompt: String = "What is the concordance status for this section?") {
        _uiState.update {
            it.copy(
                aiContextSection = section,
                currentTab = AppTab.AI
            )
        }
        sendChatMessage(prompt)
    }

    fun compareSectionInCompareTab(section: TaxSection) {
        _uiState.update {
            it.copy(
                compareSection = section,
                currentTab = AppTab.COMPARE
            )
        }
    }

    // Ingestion pipeline methods
    fun selectImportDocument(document: TaxSourceDocument) {
        _uiState.update { it.copy(selectedImportDocument = document) }
    }

    fun importFromDocument(document: TaxSourceDocument) {
        _uiState.update { it.copy(isImporting = true) }
        viewModelScope.launch {
            val rawContent = rawAssetsReader?.invoke() ?: ""
            val result = repository.importDocument(document, rawContent)
            _uiState.update {
                it.copy(
                    isImporting = false,
                    selectedImportDocument = result.document,
                    candidateImportSections = result.candidateSections.ifEmpty { it.allSections },
                    latestImportAudit = result.auditLog
                )
            }
        }
    }

    fun validateCandidateSections(document: TaxSourceDocument) {
        _uiState.update { it.copy(isValidating = true) }
        val candidates = _uiState.value.candidateImportSections
        val batchResult = repository.validateCandidateSections(candidates, document)
        _uiState.update {
            it.copy(
                isValidating = false,
                latestImportAudit = batchResult.audit,
                candidateImportSections = batchResult.validSections + batchResult.rejectedSections
            )
        }
    }

    companion object {
        fun provideFactory(application: Application): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    val rawJson = try {
                        application.applicationContext.assets.open("tax_sections.json").bufferedReader().use { it.readText() }
                    } catch (e: Exception) {
                        ""
                    }
                    val repo = JsonTaxSectionRepository.fromAssets(application.applicationContext)
                    return TaxBridgeViewModel(
                        repository = repo,
                        geminiService = GeminiTaxService(),
                        rawAssetsReader = { rawJson }
                    ) as T
                }
            }
    }
}
