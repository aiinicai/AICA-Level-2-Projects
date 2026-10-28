package com.example

import com.example.domain.AccountingEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class AccountingEngineTest {

    @Test
    fun `indian number formatting formats rupees and paise correctly`() {
        assertEquals("₹250.00", AccountingEngine.formatPaise(25000L))
        assertEquals("₹12,500.00", AccountingEngine.formatPaise(1250000L))
        assertEquals("₹1,25,000.50", AccountingEngine.formatPaise(12500050L))
        assertEquals("-₹500.00", AccountingEngine.formatPaise(-50000L))
    }

    @Test
    fun `parsing rupees strings to paise handles decimals and commas`() {
        assertEquals(25000L, AccountingEngine.parseRupeesToPaise("250"))
        assertEquals(25050L, AccountingEngine.parseRupeesToPaise("250.50"))
        assertEquals(12500050L, AccountingEngine.parseRupeesToPaise("1,25,000.50"))
        assertEquals(-50000L, AccountingEngine.parseRupeesToPaise("-500"))
    }

    @Test
    fun `personal expense generates balanced journal with debit to expense and credit to cash bank`() {
        // Arpita spends ₹500 on meal
        val amount = 50000L
        val pkg = AccountingEngine.createExpenseJournal(
            transactionId = 1,
            date = 1000L,
            description = "Meal",
            accountId = 10,
            categoryId = 20,
            totalAmountPaise = amount,
            personalSharePaise = amount,
            friendAllocations = emptyMap()
        )

        assertTrue("Journal entry must be balanced", pkg.entry.isBalanced)
        assertEquals(amount, pkg.entry.totalDebitPaise)
        assertEquals(amount, pkg.entry.totalCreditPaise)
        assertTrue(AccountingEngine.validateJournalBalance(pkg.lines))
    }

    @Test
    fun `shared expense separates personal expenditure from receivables and balances debits and credits`() {
        // Arpita pays ₹1,000. Her share is ₹500, friend share is ₹500
        val total = 100000L
        val personal = 50000L
        val friendAlloc = mapOf(101L to 50000L)

        val pkg = AccountingEngine.createExpenseJournal(
            transactionId = 2,
            date = 1000L,
            description = "Shared Dinner",
            accountId = 10,
            categoryId = 20,
            totalAmountPaise = total,
            personalSharePaise = personal,
            friendAllocations = friendAlloc
        )

        assertTrue(pkg.entry.isBalanced)
        assertEquals(total, pkg.entry.totalDebitPaise)
        assertEquals(total, pkg.entry.totalCreditPaise)

        // Expense line must be only personal share
        val expenseLine = pkg.lines.find { it.lineType == com.example.data.model.JournalLineType.EXPENSE }
        assertNotNull(expenseLine)
        assertEquals(personal, expenseLine!!.debitPaise)

        // Receivable line for friend
        val recLine = pkg.lines.find { it.lineType == com.example.data.model.JournalLineType.ASSET_RECEIVABLE }
        assertNotNull(recLine)
        assertEquals(50000L, recLine!!.debitPaise)

        // Credit to bank must be total paid
        val bankLine = pkg.lines.find { it.lineType == com.example.data.model.JournalLineType.ASSET_CASH_BANK }
        assertNotNull(bankLine)
        assertEquals(total, bankLine!!.creditPaise)
    }

    @Test
    fun `unequal multi-friend split sums exactly to total amount and balances`() {
        // Arpita pays ₹1,200. Her share: ₹400, Friend A: ₹500, Friend B: ₹300
        val total = 120000L
        val personal = 40000L
        val friendAlloc = mapOf(101L to 50000L, 102L to 30000L)

        val pkg = AccountingEngine.createExpenseJournal(
            transactionId = 3,
            date = 1000L,
            description = "Concert tickets",
            accountId = 10,
            categoryId = 20,
            totalAmountPaise = total,
            personalSharePaise = personal,
            friendAllocations = friendAlloc
        )

        assertTrue(pkg.entry.isBalanced)
        assertEquals(total, pkg.entry.totalDebitPaise)
        assertEquals(total, pkg.entry.totalCreditPaise)
    }

    @Test
    fun `invalid allocation rejecting when shares do not sum to total`() {
        try {
            AccountingEngine.createExpenseJournal(
                transactionId = 4,
                date = 1000L,
                description = "Invalid",
                accountId = 10,
                categoryId = 20,
                totalAmountPaise = 100000L,
                personalSharePaise = 40000L,
                friendAllocations = mapOf(101L to 50000L) // Sum is 90,000, not 100,000!
            )
            fail("Should throw IllegalArgumentException when allocations do not sum to total")
        } catch (e: IllegalArgumentException) {
            // Expected
            assertTrue(e.message!!.contains("must equal total"))
        }
    }

    @Test
    fun `friend paid expense creates payable without reducing cash bank`() {
        // Friend pays ₹1,000 for meal. Arpita share: ₹500
        val arpitaShare = 50000L
        val pkg = AccountingEngine.createFriendPaidExpenseJournal(
            transactionId = 5,
            date = 1000L,
            description = "Lunch paid by Alex",
            friendId = 101L,
            categoryId = 20L,
            arpitaSharePaise = arpitaShare
        )

        assertTrue(pkg.entry.isBalanced)
        assertEquals(arpitaShare, pkg.entry.totalDebitPaise)
        assertEquals(arpitaShare, pkg.entry.totalCreditPaise)

        // No Cash/Bank line exists
        val bankLines = pkg.lines.filter { it.lineType == com.example.data.model.JournalLineType.ASSET_CASH_BANK }
        assertTrue("Cash/Bank should not be altered when friend pays", bankLines.isEmpty())

        // Payable exists
        val payableLine = pkg.lines.find { it.lineType == com.example.data.model.JournalLineType.LIABILITY_PAYABLE }
        assertNotNull(payableLine)
        assertEquals(arpitaShare, payableLine!!.creditPaise)
    }

    @Test
    fun `income increases cash bank and credits income category`() {
        val amount = 200000L // ₹2,000
        val pkg = AccountingEngine.createIncomeJournal(
            transactionId = 6,
            date = 1000L,
            description = "Pocket money",
            accountId = 10L,
            categoryId = 30L,
            amountPaise = amount
        )

        assertTrue(pkg.entry.isBalanced)
        assertEquals(amount, pkg.entry.totalDebitPaise)
        assertEquals(amount, pkg.entry.totalCreditPaise)
    }

    @Test
    fun `transfer changes two accounts without changing total funds or income expenditure`() {
        val amount = 50000L
        val pkg = AccountingEngine.createTransferJournal(
            transactionId = 7,
            date = 1000L,
            description = "Cash to Bank",
            fromAccountId = 1L,
            toAccountId = 2L,
            amountPaise = amount
        )

        assertTrue(pkg.entry.isBalanced)
        // No income or expense line
        assertTrue(pkg.lines.none { it.lineType == com.example.data.model.JournalLineType.EXPENSE })
        assertTrue(pkg.lines.none { it.lineType == com.example.data.model.JournalLineType.INCOME })
    }

    @Test
    fun `repayment of receivable is collection of asset and not income`() {
        val amount = 20000L // ₹200
        val pkg = AccountingEngine.createRepaymentReceivedJournal(
            transactionId = 8,
            date = 1000L,
            description = "Alex repaid",
            friendId = 101L,
            accountId = 10L,
            amountPaise = amount
        )

        assertTrue(pkg.entry.isBalanced)
        // Must NOT have income line
        assertTrue(pkg.lines.none { it.lineType == com.example.data.model.JournalLineType.INCOME })
        val recLine = pkg.lines.find { it.lineType == com.example.data.model.JournalLineType.ASSET_RECEIVABLE }
        assertNotNull(recLine)
        assertEquals(amount, recLine!!.creditPaise) // Credit to receivable reduces asset
    }

    @Test
    fun `repayment of payable is settlement of liability and not an expense`() {
        val amount = 30000L // ₹300
        val pkg = AccountingEngine.createRepaymentPaidJournal(
            transactionId = 9,
            date = 1000L,
            description = "Paid Alex",
            friendId = 101L,
            accountId = 10L,
            amountPaise = amount
        )

        assertTrue(pkg.entry.isBalanced)
        // Must NOT have expense line
        assertTrue(pkg.lines.none { it.lineType == com.example.data.model.JournalLineType.EXPENSE })
        val payLine = pkg.lines.find { it.lineType == com.example.data.model.JournalLineType.LIABILITY_PAYABLE }
        assertNotNull(payLine)
        assertEquals(amount, payLine!!.debitPaise) // Debit to payable reduces liability
    }

    @Test
    fun `reversal flips debits and credits and restores balance`() {
        val original = AccountingEngine.createIncomeJournal(
            transactionId = 10,
            date = 1000L,
            description = "Bonus",
            accountId = 1L,
            categoryId = 2L,
            amountPaise = 15000L
        )

        val reversal = AccountingEngine.createReversalJournal(
            newTransactionId = 11,
            date = 2000L,
            originalEntry = original.entry,
            originalLines = original.lines,
            reason = "Duplicate entry"
        )

        assertTrue(reversal.entry.isBalanced)
        assertTrue(reversal.entry.isReversal)
        // In the reversal, Cash/Bank must now be credited
        val revBankLine = reversal.lines.find { it.lineType == com.example.data.model.JournalLineType.ASSET_CASH_BANK }
        assertNotNull(revBankLine)
        assertEquals(15000L, revBankLine!!.creditPaise)
        assertEquals(0L, revBankLine.debitPaise)
    }

    @Test
    fun `balance sheet balances where assets equal liabilities plus equity`() {
        // Opening cash: ₹10,000. Income: ₹5,000.
        // Expenses: ₹2,000 total (₹1,500 paid in cash, ₹500 paid by friend as payable).
        // Shared paid for friend: ₹1,000 in cash (receivable).
        // Cash remaining: 10,000 + 5,000 - 1,500 - 1,000 = ₹12,500
        val cashAndBank = 1250000L
        val receivables = 100000L
        val payables = 50000L
        val income = 500000L
        val expense = 200000L
        val opening = 1000000L

        val report = AccountingEngine.computeBalanceSheet(
            cashAndBankTotalPaise = cashAndBank,
            receivablesTotalPaise = receivables,
            payablesTotalPaise = payables,
            totalHistoricalIncomePaise = income,
            totalHistoricalPersonalExpensePaise = expense,
            openingBalancesTotalPaise = opening
        )

        assertTrue("Balance sheet must balance", report.isBalanced)
        assertEquals(1350000L, report.totalAssetsPaise)
        assertEquals(50000L, report.totalLiabilitiesPaise)
        assertEquals(1300000L, report.totalEquityPaise)
        assertEquals(report.totalAssetsPaise, report.totalLiabilitiesPaise + report.totalEquityPaise)
    }
}
