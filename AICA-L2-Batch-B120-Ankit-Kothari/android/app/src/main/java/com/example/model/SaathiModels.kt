package com.example.model

data class UserProfile(
    val name: String = "Friend",
    val city: String = "Dubai",
    val birthDate: String = "1998-05-15", // YYYY-MM-DD
    val birthTime: String = "08:30",
    val birthCity: String = "Dubai",
    val stepGoal: Int = 8000,
    val waterGoalGlasses: Int = 8,
    val is18Plus: Boolean = true,
    val consentGlow: Boolean = true,
    val preferredSystem: String = "Vedic" // "Vedic" or "Western"
)

data class DailyActivity(
    val dateString: String = "",
    val waterGlasses: Int = 0,
    val stepsWalked: Int = 0,
    val activeMinutes: Int = 0,
    val eyeBreaksDone: Int = 0,
    val neckBreaksDone: Int = 0,
    val deskStretchesDone: Int = 0,
    val energisersDone: Int = 0,
    val mood: String = "", // "Great", "Good", "Calm", "Low", "Tired"
    val journalNote: String = "",
    val amSkincareDone: Boolean = false,
    val pmSkincareDone: Boolean = false,
    val fortuneCracked: Boolean = false,
    val isGoldenCookie: Boolean = false,
    val fortuneText: String = "",
    val fortuneAuthor: String = "Saathi"
)

data class GamificationState(
    val pointsToday: Int = 0,
    val totalPoints: Int = 0,
    val levelName: String = "Spark",
    val streakDays: Int = 1,
    val freezesAvailable: Int = 1,
    val unlockedBadgeIds: Set<String> = setOf("first_sip")
)

data class Badge(
    val id: String,
    val title: String,
    val description: String,
    val iconName: String,
    val isUnlocked: Boolean = false
)

data class BmiRecord(
    val id: Long = System.currentTimeMillis(),
    val dateString: String,
    val weightKg: Float,
    val heightCm: Float,
    val waistCm: Float = 0f,
    val bmi: Float,
    val category: String,
    val kindAdvice: String
)

data class GlowScanRecord(
    val id: Long = System.currentTimeMillis(),
    val dateString: String,
    val mode: String, // "Face & Skin", "Hair & Scalp", "Nails & Hands"
    val summary: String,
    val routineAM: String,
    val routinePM: String,
    val ingredientsGood: List<String>,
    val ingredientsAvoid: List<String>,
    val safetyNote: String
)

data class DayCardData(
    val dateDisplay: String,
    val moonSign: String,
    val moonSignVedic: String,
    val nakshatra: String,
    val tithi: String,
    val dayLord: String,
    val rahuKaal: String,
    val abhijitMuhurta: String,
    val dayScore: Int, // 3 to 10
    val luckyColor: String,
    val luckyColorHex: Long,
    val luckyNumber: Int,
    val proTip: String,
    val doItems: List<String>,
    val avoidItems: List<String>,
    val lovingLine: String,
    val motivationLine: String
)

data class NumerologyReport(
    val lifePath: Int,
    val moolank: Int, // Birth Day
    val bhagyank: Int, // Destiny
    val naamank: Int, // Name Number
    val chaldeanCompound: Int,
    val loShuCounts: Map<Int, Int>, // Digits 1-9
    val arrowStrengths: List<String>,
    val coreQualities: List<String>
)
