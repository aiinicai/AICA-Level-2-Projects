package com.example.data.plaid

import com.example.data.local.AssetEntity
import com.example.data.local.FinPilotDao
import com.example.data.local.TransactionEntity
import com.example.data.model.AssetCategory
import com.example.data.model.ExpenseCategory
import com.example.data.model.IncomeCategory
import com.example.data.model.TransactionType
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class ConnectedBank(
    val id: String,
    val institutionName: String,
    val accountType: String,
    val accountNumberMask: String,
    val balance: Double,
    val lastSynced: String,
    val logoEmoji: String
)

object PlaidManager {
    val supportedInstitutions = listOf(
        "Chase Bank" to "🏦",
        "Bank of America" to "🏛️",
        "Wells Fargo" to "🪙",
        "Citibank" to "💳",
        "Fidelity Investments" to "📈",
        "Capital One" to "🛡️",
        "HDFC Bank" to "🇮🇳",
        "ICICI Bank" to "🏢"
    )

    private val _connectedAccounts = MutableStateFlow<List<ConnectedBank>>(
        listOf(
            ConnectedBank(
                id = "plaid_chase_1",
                institutionName = "Chase Bank",
                accountType = "Premier Checking",
                accountNumberMask = "••4821",
                balance = 28450.0,
                lastSynced = "Just now",
                logoEmoji = "🏦"
            ),
            ConnectedBank(
                id = "plaid_fidelity_1",
                institutionName = "Fidelity Investments",
                accountType = "Brokerage & Mutual Funds",
                accountNumberMask = "••9012",
                balance = 145000.0,
                lastSynced = "10 mins ago",
                logoEmoji = "📈"
            )
        )
    )
    val connectedAccounts: StateFlow<List<ConnectedBank>> = _connectedAccounts.asStateFlow()

    suspend fun linkNewBank(
        institutionName: String,
        accountType: String,
        initialBalance: Double,
        dao: FinPilotDao
    ): ConnectedBank {
        val mask = "••" + (1000..9999).random()
        val logo = supportedInstitutions.find { it.first == institutionName }?.second ?: "🏦"
        val newBank = ConnectedBank(
            id = "plaid_${System.currentTimeMillis()}",
            institutionName = institutionName,
            accountType = accountType,
            accountNumberMask = mask,
            balance = initialBalance,
            lastSynced = "Just now",
            logoEmoji = logo
        )
        _connectedAccounts.value = _connectedAccounts.value + newBank

        // Automatically sync as Asset in Room Database
        dao.insertAsset(
            AssetEntity(
                name = "$institutionName ($accountType)",
                category = if (accountType.contains("Brokerage", ignoreCase = true) || accountType.contains("Mutual", ignoreCase = true)) {
                    AssetCategory.MUTUAL_FUNDS
                } else {
                    AssetCategory.BANK
                },
                amount = initialBalance,
                institution = institutionName,
                expectedReturnRate = if (accountType.contains("Checking", ignoreCase = true)) 2.5 else 10.0
            )
        )

        // Seed recent imported transactions
        dao.insertTransaction(
            TransactionEntity(
                title = "Plaid Sync: $institutionName Opening Balance",
                amount = initialBalance,
                type = TransactionType.INCOME,
                incomeCategory = IncomeCategory.OTHER,
                dateTimestamp = System.currentTimeMillis()
            )
        )

        return newBank
    }
}
