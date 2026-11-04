package com.example.data.model

enum class UserRole {
    SENIOR,
    CHILD,
    PARENT
}

enum class MedStatus {
    PENDING,
    TAKEN,
    OVERDUE
}

data class Medication(
    val id: String,
    val name: String,
    val dosage: String,
    val scheduledTime: String,
    val mealInstructions: String,
    val status: MedStatus = MedStatus.PENDING,
    val takenAt: String? = null,
    val purpose: String = "",
    val reminderMinutesBefore: Int = 15
)

data class DiaryEntry(
    val id: String,
    val date: String,
    val moodEmoji: String,
    val moodLabel: String,
    val noteText: String,
    val prompt: String,
    val voiceNoteDurationSec: Int = 0,
    val isSharedWithBuddy: Boolean = true
)

data class SleepRecord(
    val id: String,
    val dayLabel: String,
    val date: String,
    val bedtime: String,
    val wakeTime: String,
    val durationHours: Float,
    val qualityStars: Int,
    val notes: String = ""
)

data class StoryChoice(
    val id: String,
    val text: String,
    val suggestedBy: String = ""
)

data class StoryTurn(
    val turnNumber: Int,
    val narratorText: String,
    val choices: List<StoryChoice>,
    val chosenChoice: String? = null,
    val speaker: String = "AI Storyteller"
)

data class InteractiveStory(
    val id: String,
    val title: String,
    val theme: String,
    val buddyName: String,
    val turns: List<StoryTurn>,
    val currentTurnIndex: Int = 0,
    val isComplete: Boolean = false
)

data class FriendRequest(
    val id: String,
    val seniorName: String,
    val childName: String,
    val ageSummary: String,
    val sharedInterests: List<String>,
    val bio: String,
    val status: FriendRequestStatus = FriendRequestStatus.PENDING,
    val requestDate: String = "Today",
    val safetyApprovedByParent: Boolean = false
)

enum class FriendRequestStatus {
    PENDING,
    APPROVED,
    DECLINED,
    BLOCKED
}

data class PhotoAnalysis(
    val id: String,
    val subjectTitle: String,
    val category: String,
    val iconKey: String,
    val summary: String,
    val medicinalProperties: String,
    val practicalUses: String,
    val originAndHistory: String,
    val generationalConversationPrompt: String,
    val triviaQuestion: String,
    val triviaOptions: List<String>,
    val triviaCorrectIndex: Int
)

data class BadgeItem(
    val id: String,
    val title: String,
    val description: String,
    val icon: String,
    val isUnlocked: Boolean = false
)

enum class SeniorMilestoneCategory {
    ALL,
    MEDICATIONS,
    DIARY,
    BREATHING,
    WELLNESS
}

data class SeniorMilestone(
    val id: String,
    val title: String,
    val category: SeniorMilestoneCategory,
    val description: String,
    val iconEmoji: String,
    val isUnlocked: Boolean = false,
    val currentProgress: Int = 0,
    val targetProgress: Int = 1,
    val progressUnit: String = "times",
    val unlockedDate: String? = null,
    val gentleAffirmation: String
)

data class DailyMission(
    val id: String,
    val title: String,
    val description: String,
    val pointsReward: Int,
    val isCompleted: Boolean = false
)

data class SeniorPreferences(
    val highContrast: Boolean = false,
    val largeText: Boolean = true,
    val autoReadAloud: Boolean = true,
    val voiceModeEnabled: Boolean = true,
    val speechRate: Float = 0.9f
)

enum class AuthLockType {
    PASSCODE,
    FACE_LOCK,
    PATTERN
}

data class AppUser(
    val mobileNumber: String,
    val displayName: String,
    val role: UserRole,
    val passcode: String = "1234",
    val patternCode: String = "0,1,2,5",
    val hasFaceRegistered: Boolean = true
)


