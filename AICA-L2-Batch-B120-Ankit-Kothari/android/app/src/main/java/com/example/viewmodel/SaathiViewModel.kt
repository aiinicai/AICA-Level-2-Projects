package com.example.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.SaathiRepository
import com.example.engine.AstrologyEngine
import com.example.engine.BmiEngine
import com.example.engine.FortuneEngine
import com.example.engine.NumerologyEngine
import com.example.engine.PointsEngine
import com.example.model.Badge
import com.example.model.BmiRecord
import com.example.model.DailyActivity
import com.example.model.DayCardData
import com.example.model.GamificationState
import com.example.model.GlowScanRecord
import com.example.model.NumerologyReport
import com.example.model.UserProfile
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class SaathiTab {
    TODAY, STARS, BODY, GLOW, ME
}

data class SaathiUiState(
    val currentTab: SaathiTab = SaathiTab.TODAY,
    val profile: UserProfile = UserProfile(),
    val dailyActivity: DailyActivity = DailyActivity(),
    val gamification: GamificationState = GamificationState(),
    val dayCard: DayCardData = AstrologyEngine.calculateDayCard(),
    val numerology: NumerologyReport = NumerologyEngine.calculateReport("1998-05-15", "Friend"),
    val bmiRecords: List<BmiRecord> = emptyList(),
    val glowRecords: List<GlowScanRecord> = emptyList(),
    val activeRoutineType: String? = null, // "EYE", "NECK", "DESK", "ENERGISER"
    val showShareCardDialog: Boolean = false,
    val shareCardType: String = "FORTUNE", // "FORTUNE", "DAY", "STREAK", "BADGE"
    val showDownloadAppDialog: Boolean = false,
    val isWalkTracking: Boolean = false,
    val walkSeconds: Int = 0,
    val notificationMessage: String? = null
)

class SaathiViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = SaathiRepository(application)

    private val _uiState = MutableStateFlow(SaathiUiState())
    val uiState: StateFlow<SaathiUiState> = _uiState.asStateFlow()

    init {
        loadInitialData()
    }

    private fun loadInitialData() {
        val profile = repository.loadProfile()
        val daily = repository.loadDailyActivity()
        val gamification = repository.loadGamification()
        val dayCard = AstrologyEngine.calculateDayCard(city = profile.city)
        val numerology = NumerologyEngine.calculateReport(profile.birthDate, profile.name)
        val bmiRecords = repository.loadBmiRecords()
        val glowRecords = repository.loadGlowRecords()

        _uiState.value = _uiState.value.copy(
            profile = profile,
            dailyActivity = daily,
            gamification = gamification,
            dayCard = dayCard,
            numerology = numerology,
            bmiRecords = bmiRecords,
            glowRecords = glowRecords
        )
    }

    fun selectTab(tab: SaathiTab) {
        _uiState.value = _uiState.value.copy(currentTab = tab)
    }

    fun logWater() {
        val current = _uiState.value.dailyActivity
        if (current.waterGlasses < 14) {
            val updated = current.copy(waterGlasses = current.waterGlasses + 1)
            addPoints(5, "water_drop")
            unlockBadge("first_sip")
            if (updated.waterGlasses >= _uiState.value.profile.waterGoalGlasses) {
                unlockBadge("hydration_hero")
            }
            _uiState.value = _uiState.value.copy(dailyActivity = updated)
            repository.saveDailyActivity(updated)
        }
    }

    fun logSteps(count: Int) {
        val current = _uiState.value.dailyActivity
        val updated = current.copy(stepsWalked = current.stepsWalked + count)
        val pts = (count / 100).coerceAtMost(50)
        if (pts > 0) addPoints(pts, "steps")
        if (updated.stepsWalked >= 10000) {
            unlockBadge("ten_k_club")
        }
        _uiState.value = _uiState.value.copy(dailyActivity = updated)
        repository.saveDailyActivity(updated)
    }

    fun crackFortune() {
        val current = _uiState.value.dailyActivity
        if (!current.fortuneCracked) {
            val (text, isGolden) = FortuneEngine.getDailyFortune(
                repository.getTodayString(),
                _uiState.value.profile.name
            )
            val updated = current.copy(
                fortuneCracked = true,
                isGoldenCookie = isGolden,
                fortuneText = text
            )
            val pts = if (isGolden) 25 else 5
            addPoints(pts, "fortune")
            unlockBadge("fortune_finder")
            if (isGolden) unlockBadge("golden_touch")

            _uiState.value = _uiState.value.copy(dailyActivity = updated)
            repository.saveDailyActivity(updated)
        }
    }

    fun toggleAmSkincare() {
        val current = _uiState.value.dailyActivity
        val updated = current.copy(amSkincareDone = !current.amSkincareDone)
        if (updated.amSkincareDone) addPoints(5, "glow")
        _uiState.value = _uiState.value.copy(dailyActivity = updated)
        repository.saveDailyActivity(updated)
    }

    fun togglePmSkincare() {
        val current = _uiState.value.dailyActivity
        val updated = current.copy(pmSkincareDone = !current.pmSkincareDone)
        if (updated.pmSkincareDone) addPoints(5, "glow")
        _uiState.value = _uiState.value.copy(dailyActivity = updated)
        repository.saveDailyActivity(updated)
    }

    fun logMood(mood: String, note: String = "") {
        val current = _uiState.value.dailyActivity
        val updated = current.copy(mood = mood, journalNote = note)
        addPoints(5, "mood")
        _uiState.value = _uiState.value.copy(dailyActivity = updated)
        repository.saveDailyActivity(updated)
    }

    fun completeRoutine(type: String) {
        val current = _uiState.value.dailyActivity
        val updated = when (type) {
            "EYE" -> {
                unlockBadge("eagle_eyes")
                addPoints(5, "routine")
                current.copy(eyeBreaksDone = current.eyeBreaksDone + 1)
            }
            "NECK" -> {
                unlockBadge("neck_saver")
                addPoints(10, "routine")
                current.copy(neckBreaksDone = current.neckBreaksDone + 1)
            }
            "DESK" -> {
                unlockBadge("desk_zen")
                addPoints(10, "routine")
                current.copy(deskStretchesDone = current.deskStretchesDone + 1)
            }
            "ENERGISER" -> {
                addPoints(25, "routine")
                current.copy(energisersDone = current.energisersDone + 1)
            }
            else -> current
        }
        _uiState.value = _uiState.value.copy(
            dailyActivity = updated,
            activeRoutineType = null
        )
        repository.saveDailyActivity(updated)
    }

    fun openRoutine(type: String) {
        _uiState.value = _uiState.value.copy(activeRoutineType = type)
    }

    fun closeRoutine() {
        _uiState.value = _uiState.value.copy(activeRoutineType = null)
    }

    fun addBmiRecord(weightKg: Float, heightCm: Float, waistCm: Float) {
        val analysis = BmiEngine.analyze(weightKg, heightCm, waistCm)
        val newRecord = BmiRecord(
            dateString = "Today",
            weightKg = weightKg,
            heightCm = heightCm,
            waistCm = waistCm,
            bmi = analysis.bmi,
            category = analysis.category,
            kindAdvice = analysis.kindAdvice
        )
        val updatedList = listOf(newRecord) + _uiState.value.bmiRecords
        addPoints(15, "bmi")
        unlockBadge("body_aware")
        _uiState.value = _uiState.value.copy(bmiRecords = updatedList)
        repository.saveBmiRecords(updatedList)
    }

    fun updateProfile(profile: UserProfile) {
        repository.saveProfile(profile)
        val dayCard = AstrologyEngine.calculateDayCard(city = profile.city)
        val numerology = NumerologyEngine.calculateReport(profile.birthDate, profile.name)
        _uiState.value = _uiState.value.copy(
            profile = profile,
            dayCard = dayCard,
            numerology = numerology
        )
        unlockBadge("star_child")
    }

    fun setAstrologySystem(system: String) {
        val profile = _uiState.value.profile.copy(preferredSystem = system)
        updateProfile(profile)
    }

    fun showShareCard(type: String) {
        _uiState.value = _uiState.value.copy(
            showShareCardDialog = true,
            shareCardType = type
        )
    }

    fun dismissShareCard() {
        _uiState.value = _uiState.value.copy(showShareCardDialog = false)
    }

    fun showDownloadAppDialog() {
        _uiState.value = _uiState.value.copy(showDownloadAppDialog = true)
    }

    fun dismissDownloadAppDialog() {
        _uiState.value = _uiState.value.copy(showDownloadAppDialog = false)
    }

    private fun addPoints(amount: Int, category: String) {
        val game = _uiState.value.gamification
        val newTotal = game.totalPoints + amount
        val newToday = game.pointsToday + amount
        val newLevel = PointsEngine.calculateLevel(newTotal).first

        val updated = game.copy(
            pointsToday = newToday,
            totalPoints = newTotal,
            levelName = newLevel
        )
        _uiState.value = _uiState.value.copy(gamification = updated)
        repository.saveGamification(updated)
    }

    private fun unlockBadge(badgeId: String) {
        val game = _uiState.value.gamification
        if (!game.unlockedBadgeIds.contains(badgeId)) {
            val updatedBadges = game.unlockedBadgeIds + badgeId
            val updated = game.copy(unlockedBadgeIds = updatedBadges)
            _uiState.value = _uiState.value.copy(gamification = updated)
            repository.saveGamification(updated)
        }
    }
}
