package com.example.domain

import com.example.data.model.AccountType
import com.example.data.model.JournalEntry
import com.example.data.model.JournalLine
import com.example.data.model.JournalLineType
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale
import kotlin.math.abs

/**
 * Double-entry accounting engine for Money Garden.
 * Guarantees that every transaction produces balanced debits and credits,
 * and maintains reconcilable ledger balances with integer minor units (paise).
 */
object AccountingEngine {

    /**
     * Formats integer paise into Indian currency representation.
     * E.g. 12500050L -> "₹1,25,000.50"
     *      25000L    -> "₹250.00"
     *      -50000L   -> "-₹500.00"
     */
    fun formatPaise(paise: Long, includeSymbol: Boolean = true): String {
        val isNegative = paise < 0
        val absPaise = abs(paise)
        val rupees = absPaise / 100
        val remainderPaise = absPaise % 100

        val rupeeString = formatIndianNumbering(rupees)
        val formattedNumber = "$rupeeString.${String.format(Locale.US, "%02d", remainderPaise)}"

        val prefix = if (isNegative) "-" else ""
        val symbol = if (includeSymbol) "₹" else ""
        return "$prefix$symbol$formattedNumber"
    }

    /**
     * Parses an Indian Rupee string into paise (Long).
     * Handles inputs like "250", "250.50", "1,250.00".
     */
    fun parseRupeesToPaise(input: String): Long {
        val sanitized = input.replace("₹", "").replace(",", "").trim()
        if (sanitized.isEmpty()) return 0L
        val parts = sanitized.split(".")
        val rupees = parts[0].toLongOrNull() ?: 0L
        val paisePart = if (parts.size > 1) {
            val decimalStr = parts[1].padEnd(2, '0').take(2)
            decimalStr.toLongOrNull() ?: 0L
        } else {
            0L
        }
        val sign = if (sanitized.startsWith("-")) -1L else 1L
        return (abs(rupees) * 100L + paisePart) * sign
    }

    /**
     * Indian numbering system comma separation (e.g., 1,25,000)
     */
    private fun formatIndianNumbering(number: Long): String {
        val s = number.toString()
        if (s.length <= 3) return s
        val lastThree = s.substring(s.length - 3)
        val rest = s.substring(0, s.length - 3)
        val sb = StringBuilder()
        var count = 0
        for (i in rest.length - 1 downTo 0) {
            sb.append(rest[i])
            count++
            if (count % 2 == 0 && i > 0) {
                sb.append(',')
            }
        }
        return sb.reverse().toString() + "," + lastThree
    }

    /**
     * Validates that journal lines balance: Sum(Debits) == Sum(Credits).
     */
    fun validateJournalBalance(lines: List<JournalLine>): Boolean {
        var totalDebit = 0L
        var totalCredit = 0L
        for (line in lines) {
            totalDebit += line.debitPaise
            totalCredit += line.creditPaise
        }
        return totalDebit == totalCredit && totalDebit > 0L
    }

    data class JournalPackage(
        val entry: JournalEntry,
        val lines: List<JournalLine>
    )

    /**
     * Creates journal lines for a Personal Expense or Shared Expense paid by Arpita.
     * Arpita pays [totalAmountPaise] from [accountId].
     * Arpita's personal share [personalSharePaise] is debited to Expense Category [categoryId].
     * Friends' shares [friendAllocations] are debited to Asset Receivables.
     */
    fun createExpenseJournal(
        transactionId: Long,
        date: Long,
        description: String,
        accountId: Long,
        categoryId: Long,
        totalAmountPaise: Long,
        personalSharePaise: Long,
        friendAllocations: Map<Long, Long> // FriendId -> AmountPaise
    ): JournalPackage {
        val friendTotal = friendAllocations.values.sum()
        require(personalSharePaise + friendTotal == totalAmountPaise) {
            "Personal share ($personalSharePaise) + Friend allocations ($friendTotal) must equal total ($totalAmountPaise)"
        }

        val lines = mutableListOf<JournalLine>()

        // 1. Debit Expense Category (Arpita's personal expense)
        if (personalSharePaise > 0L) {
            lines.add(
                JournalLine(
                    journalEntryId = 0,
                    lineType = JournalLineType.EXPENSE,
                    categoryId = categoryId,
                    debitPaise = personalSharePaise,
                    creditPaise = 0L,
                    description = "Personal share: $description"
                )
            )
        }

        // 2. Debit Asset Receivable for each friend
        for ((friendId, amount) in friendAllocations) {
            if (amount > 0L) {
                lines.add(
                    JournalLine(
                        journalEntryId = 0,
                        lineType = JournalLineType.ASSET_RECEIVABLE,
                        friendId = friendId,
                        debitPaise = amount,
                        creditPaise = 0L,
                        description = "Receivable from friend: $description"
                    )
                )
            }
        }

        // 3. Credit Payment Account (Cash/Bank)
        lines.add(
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_CASH_BANK,
                accountId = accountId,
                debitPaise = 0L,
                creditPaise = totalAmountPaise,
                description = "Payment via account: $description"
            )
        )

        val totalDebit = lines.sumOf { it.debitPaise }
        val totalCredit = lines.sumOf { it.creditPaise }
        val isBalanced = totalDebit == totalCredit

        val entry = JournalEntry(
            transactionId = transactionId,
            entryDate = date,
            description = description,
            totalDebitPaise = totalDebit,
            totalCreditPaise = totalCredit,
            isBalanced = isBalanced
        )

        return JournalPackage(entry, lines)
    }

    /**
     * Creates journal lines when a Friend pays for a shared purchase, and Arpita owes her share.
     * Cash/Bank is not touched!
     * Debit Expense Category: Arpita's personal share.
     * Credit Payable to Friend: Arpita's personal share.
     */
    fun createFriendPaidExpenseJournal(
        transactionId: Long,
        date: Long,
        description: String,
        friendId: Long,
        categoryId: Long,
        arpitaSharePaise: Long
    ): JournalPackage {
        require(arpitaSharePaise > 0L) { "Arpita share must be > 0" }

        val lines = listOf(
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.EXPENSE,
                categoryId = categoryId,
                debitPaise = arpitaSharePaise,
                creditPaise = 0L,
                description = "Friend paid expense share: $description"
            ),
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.LIABILITY_PAYABLE,
                friendId = friendId,
                debitPaise = 0L,
                creditPaise = arpitaSharePaise,
                description = "Payable to friend for: $description"
            )
        )

        val entry = JournalEntry(
            transactionId = transactionId,
            entryDate = date,
            description = description,
            totalDebitPaise = arpitaSharePaise,
            totalCreditPaise = arpitaSharePaise,
            isBalanced = true
        )

        return JournalPackage(entry, lines)
    }

    /**
     * Creates journal lines for Income.
     * Debit Cash/Bank Account: [amountPaise]
     * Credit Income Category: [amountPaise]
     */
    fun createIncomeJournal(
        transactionId: Long,
        date: Long,
        description: String,
        accountId: Long,
        categoryId: Long,
        amountPaise: Long
    ): JournalPackage {
        require(amountPaise > 0L) { "Income amount must be > 0" }

        val lines = listOf(
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_CASH_BANK,
                accountId = accountId,
                debitPaise = amountPaise,
                creditPaise = 0L,
                description = "Received income into account: $description"
            ),
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.INCOME,
                categoryId = categoryId,
                debitPaise = 0L,
                creditPaise = amountPaise,
                description = "Income earned: $description"
            )
        )

        val entry = JournalEntry(
            transactionId = transactionId,
            entryDate = date,
            description = description,
            totalDebitPaise = amountPaise,
            totalCreditPaise = amountPaise,
            isBalanced = true
        )

        return JournalPackage(entry, lines)
    }

    /**
     * Creates journal lines for Account Transfer (e.g. Cash -> Bank).
     * Debit Destination Account: [amountPaise]
     * Credit Source Account: [amountPaise]
     * Net effect on income/expense is ZERO.
     */
    fun createTransferJournal(
        transactionId: Long,
        date: Long,
        description: String,
        fromAccountId: Long,
        toAccountId: Long,
        amountPaise: Long
    ): JournalPackage {
        require(amountPaise > 0L) { "Transfer amount must be > 0" }
        require(fromAccountId != toAccountId) { "From and To accounts must be different" }

        val lines = listOf(
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_CASH_BANK,
                accountId = toAccountId,
                debitPaise = amountPaise,
                creditPaise = 0L,
                description = "Transfer in: $description"
            ),
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_CASH_BANK,
                accountId = fromAccountId,
                debitPaise = 0L,
                creditPaise = amountPaise,
                description = "Transfer out: $description"
            )
        )

        val entry = JournalEntry(
            transactionId = transactionId,
            entryDate = date,
            description = description,
            totalDebitPaise = amountPaise,
            totalCreditPaise = amountPaise,
            isBalanced = true
        )

        return JournalPackage(entry, lines)
    }

    /**
     * Creates journal lines when Friend repays money owed to Arpita.
     * Debit Cash/Bank Account: [amountPaise]
     * Credit Asset Receivable from Friend: [amountPaise]
     * NOT income! This is collection of an asset.
     */
    fun createRepaymentReceivedJournal(
        transactionId: Long,
        date: Long,
        description: String,
        friendId: Long,
        accountId: Long,
        amountPaise: Long
    ): JournalPackage {
        require(amountPaise > 0L) { "Repayment amount must be > 0" }

        val lines = listOf(
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_CASH_BANK,
                accountId = accountId,
                debitPaise = amountPaise,
                creditPaise = 0L,
                description = "Repayment received into account: $description"
            ),
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_RECEIVABLE,
                friendId = friendId,
                debitPaise = 0L,
                creditPaise = amountPaise,
                description = "Reduction in receivable from friend: $description"
            )
        )

        val entry = JournalEntry(
            transactionId = transactionId,
            entryDate = date,
            description = description,
            totalDebitPaise = amountPaise,
            totalCreditPaise = amountPaise,
            isBalanced = true
        )

        return JournalPackage(entry, lines)
    }

    /**
     * Creates journal lines when Arpita pays back money owed to a friend.
     * Debit Liability Payable to Friend: [amountPaise]
     * Credit Cash/Bank Account: [amountPaise]
     * NOT a new expense! This is settlement of a liability.
     */
    fun createRepaymentPaidJournal(
        transactionId: Long,
        date: Long,
        description: String,
        friendId: Long,
        accountId: Long,
        amountPaise: Long
    ): JournalPackage {
        require(amountPaise > 0L) { "Repayment amount must be > 0" }

        val lines = listOf(
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.LIABILITY_PAYABLE,
                friendId = friendId,
                debitPaise = amountPaise,
                creditPaise = 0L,
                description = "Repayment of liability to friend: $description"
            ),
            JournalLine(
                journalEntryId = 0,
                lineType = JournalLineType.ASSET_CASH_BANK,
                accountId = accountId,
                debitPaise = 0L,
                creditPaise = amountPaise,
                description = "Paid from account: $description"
            )
        )

        val entry = JournalEntry(
            transactionId = transactionId,
            entryDate = date,
            description = description,
            totalDebitPaise = amountPaise,
            totalCreditPaise = amountPaise,
            isBalanced = true
        )

        return JournalPackage(entry, lines)
    }

    /**
     * Creates a reversal journal entry that exactly inverts the original journal lines.
     * Reversal entry flips debits to credits and vice-versa.
     */
    fun createReversalJournal(
        newTransactionId: Long,
        date: Long,
        originalEntry: JournalEntry,
        originalLines: List<JournalLine>,
        reason: String
    ): JournalPackage {
        val reversedLines = originalLines.map { line ->
            JournalLine(
                journalEntryId = 0,
                lineType = line.lineType,
                accountId = line.accountId,
                friendId = line.friendId,
                categoryId = line.categoryId,
                debitPaise = line.creditPaise,   // Swapped
                creditPaise = line.debitPaise,   // Swapped
                description = "REVERSAL: ${line.description} ($reason)"
            )
        }

        val totalDebit = reversedLines.sumOf { it.debitPaise }
        val totalCredit = reversedLines.sumOf { it.creditPaise }

        val entry = JournalEntry(
            transactionId = newTransactionId,
            entryDate = date,
            description = "REVERSAL: ${originalEntry.description} ($reason)",
            totalDebitPaise = totalDebit,
            totalCreditPaise = totalCredit,
            isBalanced = totalDebit == totalCredit,
            isReversal = true
        )

        return JournalPackage(entry, reversedLines)
    }

    /**
     * Balance Sheet verification model.
     */
    data class BalanceSheetReport(
        val cashAndBankPaise: Long,
        val receivablesPaise: Long,
        val totalAssetsPaise: Long,
        val payablesPaise: Long,
        val totalLiabilitiesPaise: Long,
        val totalIncomePaise: Long,
        val totalPersonalExpensePaise: Long,
        val openingEquityPaise: Long,
        val accumulatedSurplusPaise: Long,
        val totalEquityPaise: Long,
        val isBalanced: Boolean
    )

    fun computeBalanceSheet(
        cashAndBankTotalPaise: Long,
        receivablesTotalPaise: Long,
        payablesTotalPaise: Long,
        totalHistoricalIncomePaise: Long,
        totalHistoricalPersonalExpensePaise: Long,
        openingBalancesTotalPaise: Long
    ): BalanceSheetReport {
        val totalAssets = cashAndBankTotalPaise + receivablesTotalPaise
        val totalLiabilities = payablesTotalPaise
        val netSurplus = totalHistoricalIncomePaise - totalHistoricalPersonalExpensePaise
        val totalEquity = openingBalancesTotalPaise + netSurplus
        val isBalanced = totalAssets == (totalLiabilities + totalEquity)

        return BalanceSheetReport(
            cashAndBankPaise = cashAndBankTotalPaise,
            receivablesPaise = receivablesTotalPaise,
            totalAssetsPaise = totalAssets,
            payablesPaise = payablesTotalPaise,
            totalLiabilitiesPaise = totalLiabilities,
            totalIncomePaise = totalHistoricalIncomePaise,
            totalPersonalExpensePaise = totalHistoricalPersonalExpensePaise,
            openingEquityPaise = openingBalancesTotalPaise,
            accumulatedSurplusPaise = netSurplus,
            totalEquityPaise = totalEquity,
            isBalanced = isBalanced
        )
    }
}
