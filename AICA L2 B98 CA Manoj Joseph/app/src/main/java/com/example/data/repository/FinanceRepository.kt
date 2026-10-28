package com.example.data.repository

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
import com.example.data.model.SavingsGoalMovement
import com.example.data.model.TransactionAllocation
import com.example.data.model.TransactionCategory
import com.example.data.model.TransactionType
import com.example.data.model.UserProfile
import com.example.domain.AccountingEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class FinanceRepository(private val db: AppDatabase) {

    val accountsFlow: Flow<List<FinancialAccount>> = db.accountDao().getAllAccountsFlow()
    val categoriesFlow: Flow<List<TransactionCategory>> = db.categoryDao().getAllCategoriesFlow()
    val friendsFlow: Flow<List<Friend>> = db.friendDao().getAllFriendsFlow()
    val transactionsFlow: Flow<List<FinancialTransaction>> = db.transactionDao().getAllTransactionsFlow()
    val savingsGoalsFlow: Flow<List<SavingsGoal>> = db.savingsGoalDao().getAllGoalsFlow()
    val achievementsFlow: Flow<List<Achievement>> = db.achievementDao().getAllAchievementsFlow()
    val checkInsFlow: Flow<List<CheckInActivity>> = db.checkInDao().getAllActivitiesFlow()
    val reconciliationsFlow: Flow<List<ReconciliationRecord>> = db.reconciliationDao().getAllReconciliationsFlow()
    val userProfileFlow: Flow<UserProfile?> = db.userProfileDao().getUserProfileFlow()

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    suspend fun getTodayIso(): String = withContext(Dispatchers.IO) {
        dateFormat.format(Date())
    }

    /**
     * Posts a personal or shared expense where Arpita pays.
     */
    suspend fun postExpense(
        date: Long,
        totalAmountPaise: Long,
        personalSharePaise: Long,
        description: String,
        accountId: Long,
        categoryId: Long,
        friendAllocations: Map<Long, Long> = emptyMap(), // friendId -> amount
        receiptUri: String? = null,
        notes: String? = null,
        idempotencyKey: String? = null
    ): Long = withContext(Dispatchers.IO) {
        if (idempotencyKey != null) {
            val existing = db.transactionDao().getByIdempotencyKey(idempotencyKey)
            if (existing != null) return@withContext existing.id
        }

        val account = db.accountDao().getAccountById(accountId)
            ?: throw IllegalArgumentException("Payment account $accountId not found")

        // 1. Insert transaction
        val tx = FinancialTransaction(
            date = date,
            totalAmountPaise = totalAmountPaise,
            personalAmountPaise = personalSharePaise,
            type = TransactionType.EXPENSE,
            description = description,
            sourceAccountId = accountId,
            destinationAccountId = null,
            categoryId = categoryId,
            friendId = if (friendAllocations.size == 1) friendAllocations.keys.first() else null,
            receiptUri = receiptUri,
            notes = notes,
            idempotencyKey = idempotencyKey
        )
        val txId = db.transactionDao().insertTransaction(tx)

        // 2. Insert allocations
        val allocations = mutableListOf<TransactionAllocation>()
        if (personalSharePaise > 0L) {
            allocations.add(
                TransactionAllocation(
                    transactionId = txId,
                    friendId = null,
                    amountPaise = personalSharePaise,
                    isArpitaShare = true
                )
            )
        }
        for ((friendId, amount) in friendAllocations) {
            allocations.add(
                TransactionAllocation(
                    transactionId = txId,
                    friendId = friendId,
                    amountPaise = amount,
                    isArpitaShare = false
                )
            )
            // Update friend's receivable (they owe Arpita)
            val friend = db.friendDao().getFriendById(friendId)
            if (friend != null) {
                db.friendDao().updateReceivablePayable(
                    id = friendId,
                    rec = friend.totalReceivablePaise + amount,
                    pay = friend.totalPayablePaise
                )
            }
        }
        db.transactionDao().insertAllocations(allocations)

        // 3. Update account balance (Deduction)
        db.accountDao().updateBalance(accountId, account.currentBalancePaise - totalAmountPaise)

        // 4. Create and post balanced double-entry journal
        val journalPackage = AccountingEngine.createExpenseJournal(
            transactionId = txId,
            date = date,
            description = description,
            accountId = accountId,
            categoryId = categoryId,
            totalAmountPaise = totalAmountPaise,
            personalSharePaise = personalSharePaise,
            friendAllocations = friendAllocations
        )
        val journalEntryId = db.journalDao().insertJournalEntry(journalPackage.entry)
        val linesWithEntryId = journalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        // 5. Update daily check-in activity
        recordActivityForDate(date)

        // 6. Check achievements
        checkExpenseAchievements(receiptUri != null)

        return@withContext txId
    }

    /**
     * Friend pays for Arpita's share in a shared expense.
     * Cash/Bank is NOT altered. A liability payable to friend is created.
     */
    suspend fun postFriendPaidExpense(
        date: Long,
        totalPurchaseAmountPaise: Long,
        arpitaSharePaise: Long,
        description: String,
        friendId: Long,
        categoryId: Long,
        notes: String? = null
    ): Long = withContext(Dispatchers.IO) {
        val friend = db.friendDao().getFriendById(friendId)
            ?: throw IllegalArgumentException("Friend $friendId not found")

        val tx = FinancialTransaction(
            date = date,
            totalAmountPaise = totalPurchaseAmountPaise,
            personalAmountPaise = arpitaSharePaise,
            type = TransactionType.EXPENSE,
            description = "$description (Paid by ${friend.name})",
            sourceAccountId = null, // No bank or cash reduced!
            destinationAccountId = null,
            categoryId = categoryId,
            friendId = friendId,
            notes = notes
        )
        val txId = db.transactionDao().insertTransaction(tx)

        // Record allocation
        db.transactionDao().insertAllocations(
            listOf(
                TransactionAllocation(
                    transactionId = txId,
                    friendId = friendId,
                    amountPaise = arpitaSharePaise,
                    isArpitaShare = true
                )
            )
        )

        // Increase payable to friend (Arpita owes friend)
        db.friendDao().updateReceivablePayable(
            id = friendId,
            rec = friend.totalReceivablePaise,
            pay = friend.totalPayablePaise + arpitaSharePaise
        )

        // Post journal lines: Debit Expense, Credit Payable to Friend
        val journalPackage = AccountingEngine.createFriendPaidExpenseJournal(
            transactionId = txId,
            date = date,
            description = description,
            friendId = friendId,
            categoryId = categoryId,
            arpitaSharePaise = arpitaSharePaise
        )
        val journalEntryId = db.journalDao().insertJournalEntry(journalPackage.entry)
        val linesWithEntryId = journalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        recordActivityForDate(date)
        checkExpenseAchievements(false)

        return@withContext txId
    }

    /**
     * Posts income (Pocket money, gift, allowance, etc.)
     */
    suspend fun postIncome(
        date: Long,
        amountPaise: Long,
        description: String,
        destinationAccountId: Long,
        categoryId: Long,
        notes: String? = null
    ): Long = withContext(Dispatchers.IO) {
        val account = db.accountDao().getAccountById(destinationAccountId)
            ?: throw IllegalArgumentException("Account $destinationAccountId not found")

        val tx = FinancialTransaction(
            date = date,
            totalAmountPaise = amountPaise,
            personalAmountPaise = amountPaise,
            type = TransactionType.INCOME,
            description = description,
            sourceAccountId = null,
            destinationAccountId = destinationAccountId,
            categoryId = categoryId,
            notes = notes
        )
        val txId = db.transactionDao().insertTransaction(tx)

        // Increase account balance
        db.accountDao().updateBalance(destinationAccountId, account.currentBalancePaise + amountPaise)

        // Double-entry journal: Debit Cash/Bank, Credit Income
        val journalPackage = AccountingEngine.createIncomeJournal(
            transactionId = txId,
            date = date,
            description = description,
            accountId = destinationAccountId,
            categoryId = categoryId,
            amountPaise = amountPaise
        )
        val journalEntryId = db.journalDao().insertJournalEntry(journalPackage.entry)
        val linesWithEntryId = journalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        recordActivityForDate(date)
        unlockAchievement("FIRST_SEED")

        return@withContext txId
    }

    /**
     * Transfer between accounts (e.g., Cash to Bank).
     * Zero income, zero expense.
     */
    suspend fun postTransfer(
        date: Long,
        amountPaise: Long,
        fromAccountId: Long,
        toAccountId: Long,
        description: String = "Account Transfer"
    ): Long = withContext(Dispatchers.IO) {
        val fromAccount = db.accountDao().getAccountById(fromAccountId)
            ?: throw IllegalArgumentException("Source account not found")
        val toAccount = db.accountDao().getAccountById(toAccountId)
            ?: throw IllegalArgumentException("Destination account not found")

        val tx = FinancialTransaction(
            date = date,
            totalAmountPaise = amountPaise,
            personalAmountPaise = 0L,
            type = TransactionType.TRANSFER,
            description = description,
            sourceAccountId = fromAccountId,
            destinationAccountId = toAccountId
        )
        val txId = db.transactionDao().insertTransaction(tx)

        db.accountDao().updateBalance(fromAccountId, fromAccount.currentBalancePaise - amountPaise)
        db.accountDao().updateBalance(toAccountId, toAccount.currentBalancePaise + amountPaise)

        val journalPackage = AccountingEngine.createTransferJournal(
            transactionId = txId,
            date = date,
            description = description,
            fromAccountId = fromAccountId,
            toAccountId = toAccountId,
            amountPaise = amountPaise
        )
        val journalEntryId = db.journalDao().insertJournalEntry(journalPackage.entry)
        val linesWithEntryId = journalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        recordActivityForDate(date)
        return@withContext txId
    }

    /**
     * Friend repays Arpita money owed (Collection of receivable).
     * Increases cash/bank, decreases receivable. NOT income!
     */
    suspend fun postRepaymentReceived(
        date: Long,
        amountPaise: Long,
        friendId: Long,
        accountId: Long,
        notes: String? = null
    ): Long = withContext(Dispatchers.IO) {
        val friend = db.friendDao().getFriendById(friendId)
            ?: throw IllegalArgumentException("Friend not found")
        val account = db.accountDao().getAccountById(accountId)
            ?: throw IllegalArgumentException("Account not found")

        val tx = FinancialTransaction(
            date = date,
            totalAmountPaise = amountPaise,
            personalAmountPaise = 0L, // Not income!
            type = TransactionType.REPAYMENT_RECEIVED,
            description = "Repayment from ${friend.name}",
            sourceAccountId = null,
            destinationAccountId = accountId,
            friendId = friendId,
            notes = notes
        )
        val txId = db.transactionDao().insertTransaction(tx)

        // Update friend balance
        val newRec = (friend.totalReceivablePaise - amountPaise).coerceAtLeast(0L)
        db.friendDao().updateReceivablePayable(friendId, newRec, friend.totalPayablePaise)

        // Update account balance
        db.accountDao().updateBalance(accountId, account.currentBalancePaise + amountPaise)

        // Journal: Debit Cash/Bank, Credit Receivable
        val journalPackage = AccountingEngine.createRepaymentReceivedJournal(
            transactionId = txId,
            date = date,
            description = "Repayment from ${friend.name}",
            friendId = friendId,
            accountId = accountId,
            amountPaise = amountPaise
        )
        val journalEntryId = db.journalDao().insertJournalEntry(journalPackage.entry)
        val linesWithEntryId = journalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        unlockAchievement("SETTLEMENT_STAR")
        recordActivityForDate(date)
        return@withContext txId
    }

    /**
     * Arpita pays friend back money owed (Settlement of liability).
     * Decreases cash/bank, decreases payable. NOT an expense!
     */
    suspend fun postRepaymentPaid(
        date: Long,
        amountPaise: Long,
        friendId: Long,
        accountId: Long,
        notes: String? = null
    ): Long = withContext(Dispatchers.IO) {
        val friend = db.friendDao().getFriendById(friendId)
            ?: throw IllegalArgumentException("Friend not found")
        val account = db.accountDao().getAccountById(accountId)
            ?: throw IllegalArgumentException("Account not found")

        val tx = FinancialTransaction(
            date = date,
            totalAmountPaise = amountPaise,
            personalAmountPaise = 0L, // Not a new expense!
            type = TransactionType.REPAYMENT_PAID,
            description = "Repayment to ${friend.name}",
            sourceAccountId = accountId,
            destinationAccountId = null,
            friendId = friendId,
            notes = notes
        )
        val txId = db.transactionDao().insertTransaction(tx)

        val newPay = (friend.totalPayablePaise - amountPaise).coerceAtLeast(0L)
        db.friendDao().updateReceivablePayable(friendId, friend.totalReceivablePaise, newPay)

        db.accountDao().updateBalance(accountId, account.currentBalancePaise - amountPaise)

        val journalPackage = AccountingEngine.createRepaymentPaidJournal(
            transactionId = txId,
            date = date,
            description = "Repayment to ${friend.name}",
            friendId = friendId,
            accountId = accountId,
            amountPaise = amountPaise
        )
        val journalEntryId = db.journalDao().insertJournalEntry(journalPackage.entry)
        val linesWithEntryId = journalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        unlockAchievement("SETTLEMENT_STAR")
        recordActivityForDate(date)
        return@withContext txId
    }

    /**
     * Auditable reversal of a posted transaction.
     * Restores accounts and friend balances without silently overwriting history.
     */
    suspend fun reverseTransaction(txId: Long, reason: String): Long = withContext(Dispatchers.IO) {
        val originalTx = db.transactionDao().getTransactionById(txId)
            ?: throw IllegalArgumentException("Transaction $txId not found")
        if (originalTx.isReversed) {
            throw IllegalStateException("Transaction $txId is already reversed")
        }

        val entries = db.journalDao().getEntriesForTransaction(txId)
        if (entries.isEmpty()) {
            throw IllegalStateException("No journal entry found for transaction $txId")
        }
        val originalEntry = entries.first()
        val originalLines = db.journalDao().getLinesForEntry(originalEntry.id)

        // 1. Insert Reversal Transaction
        val reversalTx = FinancialTransaction(
            date = System.currentTimeMillis(),
            totalAmountPaise = originalTx.totalAmountPaise,
            personalAmountPaise = originalTx.personalAmountPaise,
            type = originalTx.type,
            description = "REVERSAL: ${originalTx.description} ($reason)",
            sourceAccountId = originalTx.destinationAccountId, // Inverted
            destinationAccountId = originalTx.sourceAccountId, // Inverted
            categoryId = originalTx.categoryId,
            friendId = originalTx.friendId,
            reversalOfTransactionId = txId
        )
        val reversalTxId = db.transactionDao().insertTransaction(reversalTx)

        // 2. Mark original transaction as reversed
        db.transactionDao().updateTransaction(
            originalTx.copy(isReversed = true, reversedByTransactionId = reversalTxId)
        )

        // 3. Reverse account balances
        if (originalTx.sourceAccountId != null) {
            val src = db.accountDao().getAccountById(originalTx.sourceAccountId)
            if (src != null) {
                // Return money back to source
                db.accountDao().updateBalance(src.id, src.currentBalancePaise + originalTx.totalAmountPaise)
            }
        }
        if (originalTx.destinationAccountId != null) {
            val dst = db.accountDao().getAccountById(originalTx.destinationAccountId)
            if (dst != null) {
                // Deduct money from destination
                db.accountDao().updateBalance(dst.id, dst.currentBalancePaise - originalTx.totalAmountPaise)
            }
        }

        // 4. Reverse friend allocations
        val allocations = db.transactionDao().getAllocationsForTransaction(txId)
        for (alloc in allocations) {
            if (alloc.friendId != null) {
                val friend = db.friendDao().getFriendById(alloc.friendId)
                if (friend != null) {
                    val newRec = (friend.totalReceivablePaise - alloc.amountPaise).coerceAtLeast(0L)
                    db.friendDao().updateReceivablePayable(friend.id, newRec, friend.totalPayablePaise)
                }
            }
        }

        // 5. Post Reversal Journal Entry
        val reversalPackage = AccountingEngine.createReversalJournal(
            newTransactionId = reversalTxId,
            date = System.currentTimeMillis(),
            originalEntry = originalEntry,
            originalLines = originalLines,
            reason = reason
        )
        val journalEntryId = db.journalDao().insertJournalEntry(reversalPackage.entry)
        val linesWithEntryId = reversalPackage.lines.map { it.copy(journalEntryId = journalEntryId) }
        db.journalDao().insertJournalLines(linesWithEntryId)

        return@withContext reversalTxId
    }

    /**
     * Account Reconciliation Check
     */
    suspend fun recordReconciliation(
        accountId: Long,
        statementBalancePaise: Long,
        notes: String? = null
    ): Boolean = withContext(Dispatchers.IO) {
        val account = db.accountDao().getAccountById(accountId) ?: return@withContext false
        val isMatch = account.currentBalancePaise == statementBalancePaise
        val record = ReconciliationRecord(
            accountId = accountId,
            statementBalancePaise = statementBalancePaise,
            ledgerBalancePaise = account.currentBalancePaise,
            isReconciled = isMatch,
            notes = notes
        )
        db.reconciliationDao().insertRecord(record)
        if (isMatch) {
            unlockAchievement("BALANCE_CHECKER")
        }
        return@withContext isMatch
    }

    /**
     * Add new savings goal
     */
    suspend fun createSavingsGoal(
        name: String,
        targetAmountPaise: Long,
        targetDate: Long? = null,
        plantType: PlantType = PlantType.SPROUT,
        notes: String? = null
    ): Long = withContext(Dispatchers.IO) {
        val goal = SavingsGoal(
            name = name,
            targetAmountPaise = targetAmountPaise,
            savedAmountPaise = 0L,
            targetDate = targetDate,
            plantType = plantType,
            plantStage = 1,
            notes = notes
        )
        val id = db.savingsGoalDao().insertGoal(goal)
        unlockAchievement("SAVINGS_STARTER")
        return@withContext id
    }

    /**
     * Contribute money to savings goal
     */
    suspend fun contributeToGoal(
        goalId: Long,
        amountPaise: Long,
        notes: String? = null
    ) = withContext(Dispatchers.IO) {
        val goal = db.savingsGoalDao().getGoalById(goalId) ?: return@withContext
        val newSaved = goal.savedAmountPaise + amountPaise
        val isCompleted = newSaved >= goal.targetAmountPaise
        val progressRatio = if (goal.targetAmountPaise > 0) newSaved.toFloat() / goal.targetAmountPaise.toFloat() else 0f
        val newStage = when {
            progressRatio >= 1.0f -> 5 // Blooming Flower / Fruit Tree
            progressRatio >= 0.75f -> 4 // Budding
            progressRatio >= 0.50f -> 3 // Young Bush
            progressRatio >= 0.25f -> 2 // Sprout
            else -> 1 // Seed
        }

        db.savingsGoalDao().updateGoal(
            goal.copy(
                savedAmountPaise = newSaved,
                plantStage = newStage,
                isCompleted = isCompleted
            )
        )
        db.savingsGoalDao().insertMovement(
            SavingsGoalMovement(
                goalId = goalId,
                amountPaise = amountPaise,
                isContribution = true,
                notes = notes
            )
        )
        if (isCompleted) {
            unlockAchievement("GOAL_GETTER")
        }
    }

    /**
     * Withdraw from savings goal
     */
    suspend fun withdrawFromGoal(
        goalId: Long,
        amountPaise: Long,
        notes: String? = null
    ) = withContext(Dispatchers.IO) {
        val goal = db.savingsGoalDao().getGoalById(goalId) ?: return@withContext
        val newSaved = (goal.savedAmountPaise - amountPaise).coerceAtLeast(0L)
        val progressRatio = if (goal.targetAmountPaise > 0) newSaved.toFloat() / goal.targetAmountPaise.toFloat() else 0f
        val newStage = when {
            progressRatio >= 1.0f -> 5
            progressRatio >= 0.75f -> 4
            progressRatio >= 0.50f -> 3
            progressRatio >= 0.25f -> 2
            else -> 1
        }

        db.savingsGoalDao().updateGoal(
            goal.copy(
                savedAmountPaise = newSaved,
                plantStage = newStage,
                isCompleted = newSaved >= goal.targetAmountPaise
            )
        )
        db.savingsGoalDao().insertMovement(
            SavingsGoalMovement(
                goalId = goalId,
                amountPaise = amountPaise,
                isContribution = false,
                notes = notes
            )
        )
    }

    /**
     * Record a "No-Spend Day" check-in without creating any artificial financial transaction!
     */
    suspend fun recordNoSpendCheckIn() = withContext(Dispatchers.IO) {
        val todayIso = getTodayIso()
        val existing = db.checkInDao().getByDate(todayIso)
        val updated = existing?.copy(isNoSpendDay = true)
            ?: CheckInActivity(dateIso = todayIso, isNoSpendDay = true, transactionCount = 0)
        db.checkInDao().recordCheckIn(updated)
        checkStreakAchievements()
    }

    private suspend fun recordActivityForDate(date: Long) {
        val iso = dateFormat.format(Date(date))
        val existing = db.checkInDao().getByDate(iso)
        val updated = existing?.copy(transactionCount = existing.transactionCount + 1)
            ?: CheckInActivity(dateIso = iso, isNoSpendDay = false, transactionCount = 1)
        db.checkInDao().recordCheckIn(updated)
        checkStreakAchievements()
    }

    private suspend fun checkStreakAchievements() {
        val activities = db.checkInDao().getAllActivitiesFlow() // or list
        // Update days count
        val allDays = db.checkInDao().getByDate(getTodayIso()) // quick check
        // Check 5 days
        val distinctDays = db.transactionDao().getAllTransactions()
            .filter { !it.isReversed }
            .map { dateFormat.format(Date(it.date)) }
            .distinct()
            .size

        if (distinctDays >= 5) {
            unlockAchievement("GETTING_ORGANISED")
        }
        if (distinctDays >= 7) {
            unlockAchievement("CONSISTENCY_CHAMP")
        }
    }

    private suspend fun checkExpenseAchievements(hasReceipt: Boolean) {
        unlockAchievement("FIRST_SEED")
        if (hasReceipt) {
            unlockAchievement("RECEIPT_READY")
        }
    }

    suspend fun unlockAchievement(code: String) = withContext(Dispatchers.IO) {
        val ach = db.achievementDao().getAchievementByCode(code)
        if (ach != null && !ach.isUnlocked) {
            db.achievementDao().updateAchievement(
                ach.copy(
                    isUnlocked = true,
                    unlockedDate = System.currentTimeMillis(),
                    currentProgress = ach.maxProgress
                )
            )
        }
    }

    suspend fun saveFriend(friend: Friend): Long = withContext(Dispatchers.IO) {
        db.friendDao().insertFriend(friend)
    }

    suspend fun deleteFriend(friendId: Long): Unit = withContext(Dispatchers.IO) {
        db.friendDao().deleteFriendById(friendId)
    }

    suspend fun deleteAllFriends(): Unit = withContext(Dispatchers.IO) {
        db.friendDao().deleteAllFriends()
    }

    suspend fun deleteExistingSeedFriends(): Unit = withContext(Dispatchers.IO) {
        db.friendDao().deleteFriendsByNames(listOf("Alex", "Priya"))
    }

    suspend fun saveAccount(account: FinancialAccount): Long = withContext(Dispatchers.IO) {
        db.accountDao().insertAccount(account)
    }

    suspend fun saveCategory(category: TransactionCategory): Long = withContext(Dispatchers.IO) {
        db.categoryDao().insertCategory(category)
    }

    suspend fun deleteCategory(categoryId: Long): Unit = withContext(Dispatchers.IO) {
        db.categoryDao().deleteCategoryById(categoryId)
    }

    suspend fun updateUserProfile(profile: UserProfile) = withContext(Dispatchers.IO) {
        db.userProfileDao().saveUserProfile(profile)
    }

    /**
     * Generates standard CSV export of transaction ledger.
     */
    suspend fun exportTransactionsCsv(): String = withContext(Dispatchers.IO) {
        val transactions = db.transactionDao().getAllTransactions()
        val accountsMap = db.accountDao().getAllAccounts().associateBy { it.id }
        val categoriesMap = db.categoryDao().getAllCategories().associateBy { it.id }
        val friendsMap = db.friendDao().getAllFriends().associateBy { it.id }

        val sb = StringBuilder()
        sb.append("ID,Date,Type,Description,Category,Payment/Source Account,Destination Account,Friend,Total Amount (Paise),Total Amount (INR),Personal Share (INR),Status\n")

        val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US)
        for (tx in transactions) {
            val dateStr = sdf.format(Date(tx.date))
            val catName = categoriesMap[tx.categoryId]?.name ?: ""
            val srcName = accountsMap[tx.sourceAccountId]?.name ?: ""
            val dstName = accountsMap[tx.destinationAccountId]?.name ?: ""
            val friendName = friendsMap[tx.friendId]?.name ?: ""
            val status = if (tx.isReversed) "REVERSED" else "ACTIVE"

            val escapedDesc = "\"" + tx.description.replace("\"", "\"\"") + "\""
            val totalInr = AccountingEngine.formatPaise(tx.totalAmountPaise, includeSymbol = false)
            val shareInr = AccountingEngine.formatPaise(tx.personalAmountPaise, includeSymbol = false)

            sb.append("${tx.id},$dateStr,${tx.type.name},$escapedDesc,\"$catName\",\"$srcName\",\"$dstName\",\"$friendName\",${tx.totalAmountPaise},$totalInr,$shareInr,$status\n")
        }
        return@withContext sb.toString()
    }

    /**
     * Wipes all existing transactions, allocations, journal entries, check-ins, and resets all balances to 0.
     */
    suspend fun nullifyAllData() = withContext(Dispatchers.IO) {
        db.clearAllTransactionsAndNullifyData()
    }

    /**
     * Establishes initial opening balances for cash, bank accounts, and friend receivables/payables as of a specific date.
     */
    suspend fun recordOpeningBalances(
        asOfDate: Long,
        accountBalances: Map<Long, Long>, // accountId -> amountPaise
        friendReceivables: Map<Long, Long>, // friendId -> amountPaise
        friendPayables: Map<Long, Long> // friendId -> amountPaise
    ) = withContext(Dispatchers.IO) {
        // 1. Update accounts opening & current balances (safely applying delta if changing opening balance)
        for ((accId, balance) in accountBalances) {
            val oldAccount = db.accountDao().getAccountById(accId)
            if (oldAccount != null) {
                val delta = balance - oldAccount.openingBalancePaise
                val newCurrent = oldAccount.currentBalancePaise + delta
                db.accountDao().setOpeningAndCurrentBalance(accId, balance, newCurrent, asOfDate)
            } else {
                db.accountDao().setOpeningBalance(accId, balance, asOfDate)
            }
        }

        // 2. Update friends opening receivables & payables (safely applying delta if changing opening balance)
        val allFriends = db.friendDao().getAllFriends()
        for (f in allFriends) {
            val rec = friendReceivables[f.id] ?: 0L
            val pay = friendPayables[f.id] ?: 0L
            val deltaRec = rec - f.openingReceivablePaise
            val deltaPay = pay - f.openingPayablePaise
            val newTotRec = (f.totalReceivablePaise + deltaRec).coerceAtLeast(0L)
            val newTotPay = (f.totalPayablePaise + deltaPay).coerceAtLeast(0L)
            db.friendDao().setFriendOpeningAndCurrentBalances(f.id, rec, pay, newTotRec, newTotPay, asOfDate)
        }

        // 3. Post a balanced Opening Balance journal entry
        val lines = mutableListOf<com.example.data.model.JournalLine>()
        var totalDebits = 0L
        var totalCredits = 0L

        // Assets: Cash and Bank balances (Debits)
        for ((accId, balance) in accountBalances) {
            if (balance > 0L) {
                val acc = db.accountDao().getAccountById(accId)
                lines.add(
                    com.example.data.model.JournalLine(
                        journalEntryId = 0,
                        lineType = com.example.data.model.JournalLineType.ASSET_CASH_BANK,
                        accountId = accId,
                        debitPaise = balance,
                        creditPaise = 0L,
                        description = "Opening balance: ${acc?.name ?: "Account"}"
                    )
                )
                totalDebits += balance
            }
        }

        // Assets: Receivables from friends (Debits)
        for ((fId, rec) in friendReceivables) {
            if (rec > 0L) {
                val friend = db.friendDao().getFriendById(fId)
                lines.add(
                    com.example.data.model.JournalLine(
                        journalEntryId = 0,
                        lineType = com.example.data.model.JournalLineType.ASSET_RECEIVABLE,
                        friendId = fId,
                        debitPaise = rec,
                        creditPaise = 0L,
                        description = "Opening receivable: ${friend?.name ?: "Friend"}"
                    )
                )
                totalDebits += rec
            }
        }

        // Liabilities: Payables to friends (Credits)
        for ((fId, pay) in friendPayables) {
            if (pay > 0L) {
                val friend = db.friendDao().getFriendById(fId)
                lines.add(
                    com.example.data.model.JournalLine(
                        journalEntryId = 0,
                        lineType = com.example.data.model.JournalLineType.LIABILITY_PAYABLE,
                        friendId = fId,
                        debitPaise = 0L,
                        creditPaise = pay,
                        description = "Opening payable: ${friend?.name ?: "Friend"}"
                    )
                )
                totalCredits += pay
            }
        }

        val entry = com.example.data.model.JournalEntry(
            transactionId = 0L,
            entryDate = asOfDate,
            description = "Opening Balances as of ${SimpleDateFormat("dd MMM yyyy", Locale.US).format(Date(asOfDate))}",
            totalDebitPaise = totalDebits,
            totalCreditPaise = totalDebits,
            isBalanced = true
        )
        val entryId = db.journalDao().insertJournalEntry(entry)
        val linesWithId = lines.map { it.copy(journalEntryId = entryId) }
        db.journalDao().insertJournalLines(linesWithId)
    }

    suspend fun updateUserProfileDisplayName(displayName: String, markAsPreferred: Boolean = true) = withContext(Dispatchers.IO) {
        val existing = db.userProfileDao().getUserProfile() ?: UserProfile()
        if (!markAsPreferred && existing.hasSetPreferredName && existing.displayName.isNotBlank()) {
            // User already set their preferred address name; preserve it
            return@withContext
        }
        db.userProfileDao().saveUserProfile(
            existing.copy(
                displayName = displayName,
                hasSetPreferredName = if (markAsPreferred) true else existing.hasSetPreferredName
            )
        )
    }
}
