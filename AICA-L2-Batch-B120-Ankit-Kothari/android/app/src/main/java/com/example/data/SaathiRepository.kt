package com.example.data

import android.content.Context
import android.content.SharedPreferences
import com.example.engine.AstrologyEngine
import com.example.engine.FortuneEngine
import com.example.engine.PointsEngine
import com.example.model.Badge
import com.example.model.BmiRecord
import com.example.model.DailyActivity
import com.example.model.DayCardData
import com.example.model.GamificationState
import com.example.model.GlowScanRecord
import com.example.model.UserProfile
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SaathiRepository(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences("saathi_data", Context.MODE_PRIVATE)
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    fun getTodayString(): String = dateFormat.format(Date())

    fun loadProfile(): UserProfile {
        val name = prefs.getString("user_name", "Friend") ?: "Friend"
        val city = prefs.getString("user_city", "Dubai") ?: "Dubai"
        val birthDate = prefs.getString("user_birth_date", "1998-05-15") ?: "1998-05-15"
        val birthTime = prefs.getString("user_birth_time", "08:30") ?: "08:30"
        val birthCity = prefs.getString("user_birth_city", "Dubai") ?: "Dubai"
        val stepGoal = prefs.getInt("user_step_goal", 8000)
        val waterGoal = prefs.getInt("user_water_goal", 8)
        val is18 = prefs.getBoolean("user_is_18", true)
        val consent = prefs.getBoolean("user_consent", true)
        val system = prefs.getString("user_system", "Vedic") ?: "Vedic"

        return UserProfile(
            name = name,
            city = city,
            birthDate = birthDate,
            birthTime = birthTime,
            birthCity = birthCity,
            stepGoal = stepGoal,
            waterGoalGlasses = waterGoal,
            is18Plus = is18,
            consentGlow = consent,
            preferredSystem = system
        )
    }

    fun saveProfile(profile: UserProfile) {
        prefs.edit()
            .putString("user_name", profile.name)
            .putString("user_city", profile.city)
            .putString("user_birth_date", profile.birthDate)
            .putString("user_birth_time", profile.birthTime)
            .putString("user_birth_city", profile.birthCity)
            .putInt("user_step_goal", profile.stepGoal)
            .putInt("user_water_goal", profile.waterGoalGlasses)
            .putBoolean("user_is_18", profile.is18Plus)
            .putBoolean("user_consent", profile.consentGlow)
            .putString("user_system", profile.preferredSystem)
            .apply()
    }

    fun loadDailyActivity(date: String = getTodayString()): DailyActivity {
        val savedDate = prefs.getString("daily_date", "") ?: ""
        if (savedDate != date) {
            // New day reset
            return DailyActivity(dateString = date)
        }

        return DailyActivity(
            dateString = date,
            waterGlasses = prefs.getInt("daily_water", 0),
            stepsWalked = prefs.getInt("daily_steps", 0),
            activeMinutes = prefs.getInt("daily_active_mins", 0),
            eyeBreaksDone = prefs.getInt("daily_eye_breaks", 0),
            neckBreaksDone = prefs.getInt("daily_neck_breaks", 0),
            deskStretchesDone = prefs.getInt("daily_desk_stretches", 0),
            energisersDone = prefs.getInt("daily_energisers", 0),
            mood = prefs.getString("daily_mood", "") ?: "",
            journalNote = prefs.getString("daily_journal", "") ?: "",
            amSkincareDone = prefs.getBoolean("daily_am_skin", false),
            pmSkincareDone = prefs.getBoolean("daily_pm_skin", false),
            fortuneCracked = prefs.getBoolean("daily_fortune_cracked", false),
            isGoldenCookie = prefs.getBoolean("daily_fortune_golden", false),
            fortuneText = prefs.getString("daily_fortune_text", "") ?: ""
        )
    }

    fun saveDailyActivity(activity: DailyActivity) {
        prefs.edit()
            .putString("daily_date", activity.dateString)
            .putInt("daily_water", activity.waterGlasses)
            .putInt("daily_steps", activity.stepsWalked)
            .putInt("daily_active_mins", activity.activeMinutes)
            .putInt("daily_eye_breaks", activity.eyeBreaksDone)
            .putInt("daily_neck_breaks", activity.neckBreaksDone)
            .putInt("daily_desk_stretches", activity.deskStretchesDone)
            .putInt("daily_energisers", activity.energisersDone)
            .putString("daily_mood", activity.mood)
            .putString("daily_journal", activity.journalNote)
            .putBoolean("daily_am_skin", activity.amSkincareDone)
            .putBoolean("daily_pm_skin", activity.pmSkincareDone)
            .putBoolean("daily_fortune_cracked", activity.fortuneCracked)
            .putBoolean("daily_fortune_golden", activity.isGoldenCookie)
            .putString("daily_fortune_text", activity.fortuneText)
            .apply()
    }

    fun loadGamification(): GamificationState {
        val totalPoints = prefs.getInt("total_points", 120)
        val pointsToday = prefs.getInt("points_today", 35)
        val streak = prefs.getInt("streak_days", 3)
        val freezes = prefs.getInt("freezes_count", 1)
        val badgeSet = prefs.getStringSet("unlocked_badges", setOf("first_sip", "star_child")) ?: setOf("first_sip")
        val level = PointsEngine.calculateLevel(totalPoints).first

        return GamificationState(
            pointsToday = pointsToday,
            totalPoints = totalPoints,
            levelName = level,
            streakDays = streak,
            freezesAvailable = freezes,
            unlockedBadgeIds = badgeSet
        )
    }

    fun saveGamification(state: GamificationState) {
        prefs.edit()
            .putInt("total_points", state.totalPoints)
            .putInt("points_today", state.pointsToday)
            .putInt("streak_days", state.streakDays)
            .putInt("freezes_count", state.freezesAvailable)
            .putStringSet("unlocked_badges", state.unlockedBadgeIds)
            .apply()
    }

    fun loadBmiRecords(): List<BmiRecord> {
        val raw = prefs.getString("bmi_records_json", null) ?: return listOf(
            BmiRecord(
                id = 1L,
                dateString = "Yesterday",
                weightKg = 64.5f,
                heightCm = 168f,
                waistCm = 72f,
                bmi = 22.9f,
                category = "Optimal Harmony (Healthy)",
                kindAdvice = "Balanced vitality. Keep moving with joy!"
            )
        )
        val list = mutableListOf<BmiRecord>()
        try {
            val array = JSONArray(raw)
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                list.add(
                    BmiRecord(
                        id = obj.optLong("id", System.currentTimeMillis()),
                        dateString = obj.optString("dateString", ""),
                        weightKg = obj.optDouble("weightKg", 65.0).toFloat(),
                        heightCm = obj.optDouble("heightCm", 168.0).toFloat(),
                        waistCm = obj.optDouble("waistCm", 0.0).toFloat(),
                        bmi = obj.optDouble("bmi", 22.0).toFloat(),
                        category = obj.optString("category", "Healthy"),
                        kindAdvice = obj.optString("kindAdvice", "")
                    )
                )
            }
        } catch (_: Exception) {}
        return list
    }

    fun saveBmiRecords(records: List<BmiRecord>) {
        val array = JSONArray()
        records.forEach { r ->
            val obj = JSONObject()
            obj.put("id", r.id)
            obj.put("dateString", r.dateString)
            obj.put("weightKg", r.weightKg.toDouble())
            obj.put("heightCm", r.heightCm.toDouble())
            obj.put("waistCm", r.waistCm.toDouble())
            obj.put("bmi", r.bmi.toDouble())
            obj.put("category", r.category)
            obj.put("kindAdvice", r.kindAdvice)
            array.put(obj)
        }
        prefs.edit().putString("bmi_records_json", array.toString()).apply()
    }

    fun loadGlowRecords(): List<GlowScanRecord> {
        return listOf(
            GlowScanRecord(
                id = 1L,
                dateString = "Today",
                mode = "Face & Skin",
                summary = "Hydrated, balanced skin barrier. Minor sensitivity near cheeks.",
                routineAM = "1. Gentle hydrating cleanser\n2. Hyaluronic acid on damp skin\n3. Niacinamide 2% serum\n4. Ceramide barrier balm & SPF 50+",
                routinePM = "1. Double cleanse with warm water\n2. Peptide smoothing essence\n3. Squalane night repair cream",
                ingredientsGood = listOf("Centella Asiatica (Cica)", "Hyaluronic Acid", "Ceramide NP", "Peptides"),
                ingredientsAvoid = listOf("High-percentage alcohol", "Synthetic perfume", "Aggressive physical scrubs"),
                safetyNote = "Cosmetic & wellness advice only. Consult a board-certified dermatologist for persistent irritation."
            ),
            GlowScanRecord(
                id = 2L,
                dateString = "3 days ago",
                mode = "Hair & Scalp",
                summary = "Healthy scalp condition with mild tension near temples.",
                routineAM = "Light scalp massage with fingers for 3 minutes before shower.",
                routinePM = "Rosemary infused hair oil on ends before sleep.",
                ingredientsGood = listOf("Rosemary extract", "Biotin", "Argan oil"),
                ingredientsAvoid = listOf("Harsh sulfates", "Hot blow-drying on scalp"),
                safetyNote = "Wellness advice. Enjoy gentle daily rituals."
            )
        )
    }
}
