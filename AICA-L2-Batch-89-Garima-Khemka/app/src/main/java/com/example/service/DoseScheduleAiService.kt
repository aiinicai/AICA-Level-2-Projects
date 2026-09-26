package com.example.service

import android.util.Log
import com.example.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class DoseScheduleRecommendation(
    val doseTimes: List<String>,
    val explanation: String,
    val source: String // "GEMINI_AI" or "PRESCRIPTION_RULES"
)

object DoseScheduleAiService {

    private const val TAG = "DoseScheduleAi"
    private const val MODEL_NAME = "gemini-3.5-flash"

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    /**
     * Calculates recommended daily dose times based on medicine name, dosage, prescription instructions,
     * and the patient's chosen first dose time.
     * Uses Gemini 3.5 Flash when API key is available, and falls back to deterministic clinical pharmacologic rules.
     */
    suspend fun generateNextDoses(
        medicineName: String,
        dosage: String = "",
        instructions: String = "",
        prescriptionAdvice: String = "",
        firstDoseTime: String = "08:00",
        timesPerDay: Int? = null,
        existingScheduledTimes: String = ""
    ): DoseScheduleRecommendation = withContext(Dispatchers.IO) {
        val normalizedFirstTime = normalizeTime(firstDoseTime)
        val apiKey = BuildConfig.GEMINI_API_KEY

        // Check if Gemini API key is configured
        if (!apiKey.isNullOrBlank() && apiKey != "PLACEHOLDER_KEY" && apiKey != "MY_GEMINI_API_KEY") {
            try {
                val aiResult = callGeminiScheduleApi(
                    apiKey = apiKey,
                    medicineName = medicineName,
                    dosage = dosage,
                    instructions = instructions,
                    prescriptionAdvice = prescriptionAdvice,
                    firstDoseTime = normalizedFirstTime,
                    timesPerDay = timesPerDay
                )
                if (aiResult != null && aiResult.doseTimes.isNotEmpty()) {
                    return@withContext aiResult
                }
            } catch (e: Exception) {
                Log.w(TAG, "Gemini dose calculation failed, falling back to clinical rules", e)
            }
        }

        // Deterministic Clinical Pharmacologic Fallback
        return@withContext calculateClinicalSchedule(
            medicineName = medicineName,
            instructions = instructions,
            prescriptionAdvice = prescriptionAdvice,
            firstDoseTime = normalizedFirstTime,
            timesPerDay = timesPerDay,
            existingScheduledTimes = existingScheduledTimes
        )
    }

    private fun callGeminiScheduleApi(
        apiKey: String,
        medicineName: String,
        dosage: String,
        instructions: String,
        prescriptionAdvice: String,
        firstDoseTime: String,
        timesPerDay: Int?
    ): DoseScheduleRecommendation? {
        val prompt = """
            You are a clinical pharmacology medication scheduling assistant.
            Given the medication and the patient's chosen 1st dose time, generate the complete daily dose schedule in 24-hour HH:mm format.
            Ensure therapeutic spacing between doses (e.g. twice daily = 10-12 hours apart, 3 times daily = 5-7 hours apart, 4 times daily = 4-6 hours apart).
            
            Medication: $medicineName ($dosage)
            Instructions: $instructions
            Doctor Advice / Prescription: $prescriptionAdvice
            First Dose Time: $firstDoseTime
            Desired Freq/Day: ${timesPerDay ?: "Determine automatically from instructions"}

            Respond with ONLY a JSON object:
            {
              "explanation": "e.g. Twice daily regimen spaced 12 hours apart after breakfast and dinner",
              "doseTimes": ["$firstDoseTime", "20:00"]
            }
        """.trimIndent()

        val jsonRequest = JSONObject().apply {
            val contentsArray = JSONArray().apply {
                val contentObj = JSONObject().apply {
                    val partsArray = JSONArray().apply {
                        put(JSONObject().apply { put("text", prompt) })
                    }
                    put("parts", partsArray)
                }
                put(contentObj)
            }
            put("contents", contentsArray)

            val genConfig = JSONObject().apply {
                put("responseMimeType", "application/json")
                put("temperature", 0.1)
            }
            put("generationConfig", genConfig)
        }

        val requestBody = jsonRequest.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val url = "https://generativelanguage.googleapis.com/v1beta/models/$MODEL_NAME:generateContent?key=$apiKey"

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()

        val response = okHttpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            Log.e(TAG, "Gemini API error: ${response.code}")
            return null
        }

        val responseBodyStr = response.body?.string() ?: return null
        val responseJson = JSONObject(responseBodyStr)
        val candidates = responseJson.optJSONArray("candidates") ?: return null
        if (candidates.length() == 0) return null

        val firstCandidate = candidates.getJSONObject(0)
        val content = firstCandidate.optJSONObject("content") ?: return null
        val parts = content.optJSONArray("parts") ?: return null
        if (parts.length() == 0) return null

        val text = parts.getJSONObject(0).optString("text")
        if (text.isBlank()) return null

        return try {
            val parsed = JSONObject(text)
            val timesArray = parsed.optJSONArray("doseTimes")
            val timesList = mutableListOf<String>()
            if (timesArray != null) {
                for (i in 0 until timesArray.length()) {
                    val raw = timesArray.optString(i).trim()
                    val normalized = normalizeTime(raw)
                    if (normalized.isNotBlank() && !timesList.contains(normalized)) {
                        timesList.add(normalized)
                    }
                }
            }
            if (timesList.isEmpty() || !timesList.contains(firstDoseTime)) {
                if (!timesList.contains(firstDoseTime)) {
                    timesList.add(0, firstDoseTime)
                }
            }
            val explanation = parsed.optString("explanation", "AI calculated dose times based on prescription instructions.")
            DoseScheduleRecommendation(
                doseTimes = timesList.sorted(),
                explanation = explanation,
                source = "GEMINI_AI"
            )
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing Gemini response JSON", e)
            null
        }
    }

    /**
     * Deterministic clinical scheduler:
     * Analyzes medical terminology (BID, TID, QID, frequency keywords) and spaces doses realistically from first dose time.
     */
    fun calculateClinicalSchedule(
        medicineName: String,
        instructions: String,
        prescriptionAdvice: String,
        firstDoseTime: String,
        timesPerDay: Int?,
        existingScheduledTimes: String = ""
    ): DoseScheduleRecommendation {
        val normFirst = normalizeTime(firstDoseTime)
        val combinedText = "$instructions $prescriptionAdvice".lowercase()

        // 1. If existing scheduled times have multiple slots, preserve the relative spacing
        if (existingScheduledTimes.isNotBlank() && existingScheduledTimes.contains(",")) {
            val existing = existingScheduledTimes.split(",").map { normalizeTime(it.trim()) }.filter { it.isNotBlank() }
            if (existing.size > 1) {
                // If the first time matches existing[0], keep existing
                if (existing[0] == normFirst) {
                    return DoseScheduleRecommendation(
                        doseTimes = existing,
                        explanation = "Prescription schedule: ${existing.size} doses per day (${existing.joinToString(", ")}).",
                        source = "PRESCRIPTION_RULES"
                    )
                } else {
                    // Shift all subsequent doses by the delta
                    val deltaMinutes = timeToMinutes(normFirst) - timeToMinutes(existing[0])
                    val shifted = existing.map { minutesToTime((timeToMinutes(it) + deltaMinutes + 1440) % 1440) }.distinct().sorted()
                    return DoseScheduleRecommendation(
                        doseTimes = shifted,
                        explanation = "Shifted ${shifted.size} doses according to updated 1st dose time.",
                        source = "PRESCRIPTION_RULES"
                    )
                }
            }
        }

        // 2. Detect frequency from instructions or timesPerDay
        val frequency: Int = when {
            timesPerDay != null && timesPerDay > 0 -> timesPerDay
            combinedText.contains("4 times") || combinedText.contains("qid") || combinedText.contains("four times") || combinedText.contains("every 6 hours") -> 4
            combinedText.contains("3 times") || combinedText.contains("thrice") || combinedText.contains("tid") || combinedText.contains("tds") || combinedText.contains("three times") || combinedText.contains("every 8 hours") || (combinedText.contains("morning") && combinedText.contains("afternoon") && combinedText.contains("night")) -> 3
            combinedText.contains("2 times") || combinedText.contains("twice") || combinedText.contains("bid") || combinedText.contains("bd") || combinedText.contains("two times") || combinedText.contains("every 12 hours") || (combinedText.contains("morning") && (combinedText.contains("night") || combinedText.contains("evening"))) -> 2
            combinedText.contains("once") || combinedText.contains("od") || combinedText.contains("bedtime") || combinedText.contains("hs") -> 1
            else -> {
                // Default: if first dose is in the morning, default to twice daily (standard for most chronic meds)
                val firstMins = timeToMinutes(normFirst)
                if (firstMins in 360..660) 2 else 1
            }
        }

        val firstMinutes = timeToMinutes(normFirst)
        val resultTimes = mutableListOf(normFirst)

        when (frequency) {
            1 -> {
                // Single dose
            }
            2 -> {
                // Twice daily: typically 12 hours apart, e.g., 08:00 -> 20:00
                val secondMins = (firstMinutes + 720) % 1440
                resultTimes.add(minutesToTime(secondMins))
            }
            3 -> {
                // 3 times daily: spaced by 6 hours, e.g. 08:00 -> 14:00 -> 20:00
                val secondMins = (firstMinutes + 360) % 1440
                val thirdMins = (firstMinutes + 720) % 1440
                resultTimes.add(minutesToTime(secondMins))
                resultTimes.add(minutesToTime(thirdMins))
            }
            4 -> {
                // 4 times daily: spaced by 4.5 - 5 hours
                val secondMins = (firstMinutes + 270) % 1440
                val thirdMins = (firstMinutes + 540) % 1440
                val fourthMins = (firstMinutes + 810) % 1440
                resultTimes.add(minutesToTime(secondMins))
                resultTimes.add(minutesToTime(thirdMins))
                resultTimes.add(minutesToTime(fourthMins))
            }
            else -> {
                val intervalMins = 1440 / frequency
                for (i in 1 until frequency) {
                    val m = (firstMinutes + (i * intervalMins)) % 1440
                    resultTimes.add(minutesToTime(m))
                }
            }
        }

        val sorted = resultTimes.distinct().sorted()
        val freqLabel = when (frequency) {
            1 -> "Once daily"
            2 -> "Twice daily (12h spacing)"
            3 -> "Three times daily (6h spacing)"
            4 -> "Four times daily"
            else -> "$frequency doses daily"
        }

        return DoseScheduleRecommendation(
            doseTimes = sorted,
            explanation = "Calculated $freqLabel based on prescription instructions.",
            source = "PRESCRIPTION_RULES"
        )
    }

    private fun normalizeTime(raw: String): String {
        val trimmed = raw.trim()
        val parts = trimmed.split(":")
        if (parts.size >= 2) {
            val h = parts[0].toIntOrNull() ?: 8
            val m = parts[1].toIntOrNull() ?: 0
            return String.format(java.util.Locale.US, "%02d:%02d", h.coerceIn(0, 23), m.coerceIn(0, 59))
        }
        return "08:00"
    }

    private fun timeToMinutes(timeStr: String): Int {
        val parts = timeStr.split(":")
        val h = parts.getOrNull(0)?.toIntOrNull() ?: 8
        val m = parts.getOrNull(1)?.toIntOrNull() ?: 0
        return (h * 60) + m
    }

    private fun minutesToTime(totalMinutes: Int): String {
        val normalized = (totalMinutes % 1440 + 1440) % 1440
        val h = normalized / 60
        val m = normalized % 60
        return String.format(java.util.Locale.US, "%02d:%02d", h, m)
    }
}
