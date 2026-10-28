package com.example.domain

import com.example.data.model.CheckInActivity
import com.example.data.model.Friend
import com.example.data.model.ReconciliationRecord
import com.example.data.model.SavingsGoal
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class HealthScoreBreakdown(
    val totalScore: Int, // 0 to 100
    val consistencyScore: Int, // max 30
    val reconciliationScore: Int, // max 25
    val friendsReviewScore: Int, // max 25
    val savingsProgressScore: Int, // max 20
    val gradeTitle: String,
    val feedbackTips: List<String>
)

object HealthScoreCalculator {

    fun calculate(
        activities: List<CheckInActivity>,
        reconciliations: List<ReconciliationRecord>,
        friends: List<Friend>,
        goals: List<SavingsGoal>
    ): HealthScoreBreakdown {
        val tips = mutableListOf<String>()

        // 1. Consistency Score (max 30 points)
        // Measured by active days in last 14 days (either transactions recorded or no-spend check-in)
        val activeDaysCount = activities.size.coerceAtMost(14)
        val consistencyScore = ((activeDaysCount.toFloat() / 14f) * 30f).toInt().coerceIn(0, 30)
        if (consistencyScore >= 24) {
            tips.add("🌱 Great consistency! You regularly track or check in.")
        } else {
            tips.add("💧 Tip: Check in daily or record expenses to boost your habit garden.")
        }

        // 2. Reconciliation Score (max 25 points)
        // Has Arpita reconciled any account balance recently?
        val reconciliationScore = if (reconciliations.isNotEmpty()) {
            val hasReconciled = reconciliations.any { it.isReconciled }
            if (hasReconciled) 25 else 15
        } else {
            5
        }
        if (reconciliationScore < 20) {
            tips.add("🔍 Tip: Verify your cash or bank balance once a month in the reconciliation tool.")
        } else {
            tips.add("⚖️ Ledger is balanced and matched against your bank statement.")
        }

        // 3. Friends & Splits Review Score (max 25 points)
        // Are outstanding balances actively maintained and settled up?
        val friendsWithDues = friends.filter { it.totalReceivablePaise > 0L || it.totalPayablePaise > 0L }
        val friendsReviewScore = if (friends.isEmpty()) {
            25
        } else if (friendsWithDues.size <= 2) {
            25
        } else if (friendsWithDues.size <= 4) {
            18
        } else {
            12
        }
        if (friendsWithDues.isNotEmpty()) {
            tips.add("🤝 Tip: You have ${friendsWithDues.size} friend(s) with pending split balances.")
        } else {
            tips.add("✨ All shared expenses with friends are settled up!")
        }

        // 4. Savings Progress Score (max 20 points)
        val savingsProgressScore = if (goals.isEmpty()) {
            10
        } else {
            val totalSaved = goals.sumOf { it.savedAmountPaise }
            val totalTarget = goals.sumOf { it.targetAmountPaise }
            if (totalTarget > 0) {
                val ratio = (totalSaved.toFloat() / totalTarget.toFloat()).coerceIn(0f, 1f)
                (ratio * 20f).toInt().coerceIn(5, 20)
            } else {
                15
            }
        }
        if (goals.any { it.isCompleted }) {
            tips.add("🏆 You've successfully completed a savings goal milestone!")
        } else if (goals.isEmpty()) {
            tips.add("🎯 Tip: Plant a new savings goal to grow your virtual garden.")
        }

        val totalScore = (consistencyScore + reconciliationScore + friendsReviewScore + savingsProgressScore).coerceIn(0, 100)

        val gradeTitle = when {
            totalScore >= 85 -> "Thriving Garden 🌿"
            totalScore >= 70 -> "Blooming Sprout 🌸"
            totalScore >= 50 -> "Growing Seedling 🌱"
            else -> "Sprouting Soil 🌰"
        }

        return HealthScoreBreakdown(
            totalScore = totalScore,
            consistencyScore = consistencyScore,
            reconciliationScore = reconciliationScore,
            friendsReviewScore = friendsReviewScore,
            savingsProgressScore = savingsProgressScore,
            gradeTitle = gradeTitle,
            feedbackTips = tips
        )
    }
}
