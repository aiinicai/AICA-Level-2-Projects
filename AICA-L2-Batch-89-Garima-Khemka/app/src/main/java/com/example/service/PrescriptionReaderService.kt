package com.example.service

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import android.util.Log
import com.example.BuildConfig
import com.example.ui.viewmodel.AutofillMedInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

data class ExtractedPrescription(
    val doctorName: String,
    val clinicOrHospital: String,
    val diseaseOrDiagnosis: String,
    val startDate: String,
    val endDate: String?,
    val dischargeAdvice: String,
    val notes: String,
    val medicines: List<AutofillMedInfo>,
    val source: String = "GEMINI_AI",
    val statusMessage: String = "Prescription read successfully"
)

object PrescriptionReaderService {

    private const val TAG = "PrescriptionReader"
    private const val PRIMARY_MODEL = "gemini-2.5-flash"
    private const val SECONDARY_MODEL = "gemini-3.5-flash"

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    suspend fun readPrescriptionImage(context: Context, imageUri: Uri): ExtractedPrescription = withContext(Dispatchers.IO) {
        val apiKey = try {
            BuildConfig.GEMINI_API_KEY
        } catch (_: Exception) {
            ""
        }

        val bitmap = loadAndScaleBitmap(context, imageUri)
        val todayStr = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date())

        if (bitmap == null) {
            return@withContext ExtractedPrescription(
                doctorName = "",
                clinicOrHospital = "",
                diseaseOrDiagnosis = "",
                startDate = todayStr,
                endDate = null,
                dischargeAdvice = "",
                notes = "",
                medicines = emptyList(),
                source = "ERROR",
                statusMessage = "Unable to open or load prescription image. Please try another photo."
            )
        }

        if (apiKey.isBlank() || apiKey == "MY_GEMINI_API_KEY") {
            // Do NOT hallucinate or return fake medicines!
            return@withContext ExtractedPrescription(
                doctorName = "",
                clinicOrHospital = "",
                diseaseOrDiagnosis = "",
                startDate = todayStr,
                endDate = null,
                dischargeAdvice = "",
                notes = "Gemini API key is not configured in Secrets. Photo is attached.",
                medicines = emptyList(),
                source = "NO_API_KEY",
                statusMessage = "Photo attached. Gemini API key is not set in Secrets. Please type medicine details below or test sample presets."
            )
        }

        // Try primary model first, fallback to secondary
        val modelsToTry = listOf(PRIMARY_MODEL, SECONDARY_MODEL)
        for (model in modelsToTry) {
            try {
                val extracted = callGeminiVisionApi(apiKey, bitmap, model)
                if (extracted != null) {
                    if (extracted.medicines.isNotEmpty() || extracted.doctorName.isNotBlank()) {
                        return@withContext extracted
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Gemini vision call failed on model $model", e)
            }
        }

        // If Gemini was called but could not identify any medicines from the user's photo,
        // inform the user honestly without inventing fake medicines!
        ExtractedPrescription(
            doctorName = "",
            clinicOrHospital = "",
            diseaseOrDiagnosis = "",
            startDate = todayStr,
            endDate = null,
            dischargeAdvice = "",
            notes = "Could not decipher legible medicines from this image.",
            medicines = emptyList(),
            source = "UNREADABLE",
            statusMessage = "Could not decipher clear medicine names from this photo. Please review the image or enter medicine details manually below."
        )
    }

    private fun loadAndScaleBitmap(context: Context, uri: Uri): Bitmap? {
        return try {
            var inputStream: InputStream? = null
            if (uri.scheme == "file") {
                val file = File(uri.path ?: "")
                if (file.exists()) {
                    inputStream = file.inputStream()
                }
            }
            if (inputStream == null) {
                inputStream = context.contentResolver.openInputStream(uri)
            }

            inputStream?.use { stream ->
                val original = BitmapFactory.decodeStream(stream) ?: return null
                val maxDim = 1024
                val width = original.width
                val height = original.height
                if (width <= maxDim && height <= maxDim) {
                    return original
                }
                val ratio = width.toFloat() / height.toFloat()
                val targetW = if (width > height) maxDim else (maxDim * ratio).toInt()
                val targetH = if (width > height) (maxDim / ratio).toInt() else maxDim
                Bitmap.createScaledBitmap(original, targetW, targetH, true)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error loading bitmap", e)
            null
        }
    }

    private fun bitmapToBase64(bitmap: Bitmap): String {
        val outputStream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 85, outputStream)
        return Base64.encodeToString(outputStream.toByteArray(), Base64.NO_WRAP)
    }

    private fun callGeminiVisionApi(apiKey: String, bitmap: Bitmap, modelName: String): ExtractedPrescription? {
        val base64Image = bitmapToBase64(bitmap)

        val promptText = """
            You are a licensed medical transcriptionist and clinical prescription analyzer.
            Your task is to extract information from the provided prescription photo with STRICT ACCURACY.

            CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
            1. ONLY extract medicines, dosages, instructions, doctor name, and hospital that are VISIBLY WRITTEN or PRINTED in this exact image.
            2. DO NOT GUESS, assume, or hallucinate any medication name, brand, strength, or condition not clearly visible.
            3. If handwriting is illegible or ambiguous, write only what you are confident about, or omit it. DO NOT invent placeholder drugs (e.g. do NOT invent Telmisartan, Atorvastatin, Paracetamol unless explicitly written).
            4. If no prescription or medications are found in the image (e.g. blurry, blank, or not a prescription), return "medicines": [], and set "doctorName": "", "clinicOrHospital": "", "diseaseOrDiagnosis": "".
            5. For reminder times, assign logical times (in 24-hour HH:mm format) strictly matching the prescribed dosage frequency:
               - Once daily (OD / 1 daily) -> "08:00"
               - Twice daily (BD / BID / 2 daily) -> "08:00, 20:00"
               - Thrice daily (TDS / TID / 3 daily) -> "08:00, 14:00, 20:00"
               - 4 times daily (QID) -> "08:00, 12:00, 16:00, 20:00"
               - Bedtime / Night only (HS) -> "21:30"
               - Morning before food -> "07:30"

            6. DETECT DOSE TAPERING / STEP-DOWN SCHEDULES:
               Prescriptions often specify tapering dosages (e.g. 'Take 2 tabs for 7 days until 24 Sept, then taper down to 1 tab daily from today / 25 Sept', or 'Prednisolone 20mg BD for 7 days, then taper to 10mg OD').
               If any tapering, step-down, dose reduction, or transition is indicated:
               - "hasTapering": true
               - "taperStartDate": "Date when tapering begins (YYYY-MM-DD or DD-MM-YYYY)"
               - "taperDosage": "Tapered dose strength, e.g. 1 Tablet or 10 mg"
               - "taperTimesPerDay": 1
               - "taperScheduledTimes": "24-hour HH:mm reminder times for tapered dose, e.g. '08:00'"
               - "taperInstructions": "Instructions during tapering phase, e.g. Tapered dose with breakfast"
               - "taperEndDate": "End date of tapered course or blank if ongoing"

            Return a valid, pure JSON object with these EXACT keys (no markdown formatting, only JSON):
            {
              "doctorName": "Doctor name if written, otherwise \"\"",
              "clinicOrHospital": "Clinic or hospital if written, otherwise \"\"",
              "diseaseOrDiagnosis": "Diagnosis or condition if written, otherwise \"\"",
              "startDate": "Date in YYYY-MM-DD or today's date",
              "endDate": "End date or duration if written, otherwise \"\"",
              "dischargeAdvice": "Dietary or lifestyle advice if written, otherwise \"\"",
              "notes": "Doctor's notes or precautions if written, otherwise \"\"",
              "medicines": [
                {
                  "name": "Exact medicine name as written",
                  "dosage": "Initial strength or dosage, e.g. 500 mg, 2 tablets",
                  "form": "Tablet / Capsule / Syrup / Drops / Injection / Inhaler",
                  "instructions": "Specific instructions as written, e.g. After meals",
                  "timesPerDay": 2,
                  "scheduledTimes": "24-hour HH:mm reminder times, e.g. '08:00, 20:00'",
                  "hasTapering": false,
                  "taperStartDate": "",
                  "taperDosage": "",
                  "taperTimesPerDay": 1,
                  "taperScheduledTimes": "08:00",
                  "taperInstructions": "",
                  "taperEndDate": ""
                }
              ]
            }
        """.trimIndent()

        val jsonRequest = JSONObject().apply {
            val contentsArray = JSONArray().apply {
                val contentObj = JSONObject().apply {
                    val partsArray = JSONArray().apply {
                        put(JSONObject().apply { put("text", promptText) })
                        put(JSONObject().apply {
                            val inlineData = JSONObject().apply {
                                put("mimeType", "image/jpeg")
                                put("data", base64Image)
                            }
                            put("inlineData", inlineData)
                        })
                    }
                    put("parts", partsArray)
                }
                put(contentObj)
            }
            put("contents", contentsArray)

            val genConfig = JSONObject().apply {
                put("responseMimeType", "application/json")
                put("temperature", 0.0) // Zero temperature for deterministic, strictly grounded extraction
            }
            put("generationConfig", genConfig)
        }

        val requestBody = jsonRequest.toString().toRequestBody("application/json; charset=utf-8".toMediaType())
        val url = "https://generativelanguage.googleapis.com/v1beta/models/$modelName:generateContent?key=$apiKey"

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()

        val response = okHttpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            val errBody = response.body?.string() ?: ""
            Log.e(TAG, "Gemini API error on $modelName: ${response.code} $errBody")
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

        val extractedText = parts.getJSONObject(0).optString("text")
        if (extractedText.isBlank()) return null

        return parseExtractedJson(extractedText, "GEMINI_AI")
    }

    private fun parseExtractedJson(rawJson: String, source: String): ExtractedPrescription? {
        return try {
            val cleaned = rawJson.trim()
                .removePrefix("```json")
                .removePrefix("```")
                .removeSuffix("```")
                .trim()

            val obj = JSONObject(cleaned)
            val doctor = obj.optString("doctorName", "")
            val clinic = obj.optString("clinicOrHospital", "")
            val disease = obj.optString("diseaseOrDiagnosis", "")
            val todayStr = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date())
            val rawStart = obj.optString("startDate", todayStr)
            val start = com.example.util.DateUtils.formatDisplayDate(rawStart).ifBlank { todayStr }
            val rawEnd = obj.optString("endDate", "").takeIf { it.isNotBlank() }
            val end = rawEnd?.let { com.example.util.DateUtils.formatDisplayDate(it) }?.takeIf { it.isNotBlank() }
            val advice = obj.optString("dischargeAdvice", "")
            val notes = obj.optString("notes", "")

            val medicines = mutableListOf<AutofillMedInfo>()
            val medArray = obj.optJSONArray("medicines")
            if (medArray != null) {
                for (i in 0 until medArray.length()) {
                    val medObj = medArray.getJSONObject(i)
                    val medName = medObj.optString("name", "").trim()
                    if (medName.isBlank()) continue

                    val dosage = medObj.optString("dosage", "1 Dose").trim()
                    val form = medObj.optString("form", "Tablet").trim()
                    val instructions = medObj.optString("instructions", "As prescribed").trim()
                    val timesPerDay = medObj.optInt("timesPerDay", 1).coerceAtLeast(1)
                    val defaultTimes = when (timesPerDay) {
                        2 -> "08:00, 20:00"
                        3 -> "08:00, 14:00, 20:00"
                        4 -> "08:00, 12:00, 16:00, 20:00"
                        else -> "08:00"
                    }
                    val scheduledTimes = medObj.optString("scheduledTimes", defaultTimes).trim()

                    // Check explicit tapering fields or detect from text
                    var hasTapering = medObj.optBoolean("hasTapering", false)
                    val rawTaperStart = medObj.optString("taperStartDate", "").trim()
                    var taperStartDate = if (rawTaperStart.isNotBlank()) com.example.util.DateUtils.formatDisplayDate(rawTaperStart) else ""
                    var taperDosage = medObj.optString("taperDosage", "").trim()
                    var taperTimesPerDay = medObj.optInt("taperTimesPerDay", 1).coerceAtLeast(1)
                    var taperScheduledTimes = medObj.optString("taperScheduledTimes", "08:00").trim()
                    var taperInstructions = medObj.optString("taperInstructions", "").trim()
                    val taperEndDate = medObj.optString("taperEndDate", "").trim()

                    // Auto-detect tapering if mentioned in instructions or prescription notes
                    val combinedText = "$instructions $notes $advice".lowercase()
                    if (!hasTapering && (combinedText.contains("taper") || combinedText.contains("step down") || combinedText.contains("reduce dose"))) {
                        hasTapering = true
                        if (taperStartDate.isBlank()) {
                            taperStartDate = todayStr
                        }
                        if (taperDosage.isBlank()) {
                            taperDosage = if (dosage.contains("2")) "1 Tablet" else "Tapered Dose (Reduced)"
                        }
                        if (taperScheduledTimes.isBlank()) {
                            taperScheduledTimes = "08:00"
                        }
                        if (taperInstructions.isBlank()) {
                            taperInstructions = "Taper down dose from $taperStartDate as prescribed"
                        }
                    }

                    medicines.add(
                        AutofillMedInfo(
                            name = medName,
                            dosage = dosage,
                            form = form,
                            instructions = instructions,
                            timesPerDay = timesPerDay,
                            scheduledTimes = scheduledTimes,
                            hasTapering = hasTapering,
                            taperStartDate = taperStartDate,
                            taperDosage = taperDosage,
                            taperTimesPerDay = taperTimesPerDay,
                            taperScheduledTimes = taperScheduledTimes,
                            taperInstructions = taperInstructions,
                            taperEndDate = taperEndDate
                        )
                    )
                }
            }

            val status = if (medicines.isNotEmpty()) {
                val taperCount = medicines.count { it.hasTapering }
                if (taperCount > 0) {
                    "✓ Read ${medicines.size} medicine(s) with $taperCount automated dose tapering schedule(s)"
                } else {
                    "✓ Successfully read ${medicines.size} medicine(s) from prescription via AI"
                }
            } else {
                "No medicines were detected in the photo. Please enter details manually."
            }

            ExtractedPrescription(
                doctorName = doctor,
                clinicOrHospital = clinic,
                diseaseOrDiagnosis = disease,
                startDate = start,
                endDate = end,
                dischargeAdvice = advice,
                notes = notes,
                medicines = medicines,
                source = source,
                statusMessage = status
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse extracted JSON: $rawJson", e)
            null
        }
    }

    /**
     * Explicitly loads sample clinical prescriptions for demonstration purposes.
     * This is ONLY called when the user taps sample preset buttons, NEVER on uploaded images.
     */
    fun fallbackSmartExtraction(hasCustomImage: Boolean = false, sampleType: String = "CARDIO"): ExtractedPrescription {
        val todayStr = SimpleDateFormat("dd-MM-yyyy", Locale.getDefault()).format(Date())

        return when (sampleType) {
            "TAPER" -> ExtractedPrescription(
                doctorName = "Dr. Sanjeev Kapoor, MD (Internal Medicine & Rheumatology)",
                clinicOrHospital = "Max Super Specialty Hospital",
                diseaseOrDiagnosis = "Acute Inflammatory Flare & Reactive Bronchospasm",
                startDate = "17-09-2026",
                endDate = null,
                dischargeAdvice = "Strict tapering schedule: 16mg BD for first 8 days (17th Sept - 24th Sept), then taper down to 8mg OD starting from today (25th Sept) with breakfast. Do not stop abruptly.",
                notes = "Tapering schedule: Day 1-8: 16mg twice daily. Day 9 onwards (from 25-09-2026): Taper to 8mg once daily in morning. Check blood glucose and BP regularly.",
                medicines = listOf(
                    AutofillMedInfo(
                        name = "Methylprednisolone (Medrol)",
                        dosage = "16 mg (2 Tablets)",
                        form = "Tablet",
                        instructions = "Take after breakfast and dinner (17th to 24th Sept)",
                        timesPerDay = 2,
                        scheduledTimes = "08:00, 20:00",
                        hasTapering = true,
                        taperStartDate = todayStr,
                        taperDosage = "8 mg (1 Tablet)",
                        taperTimesPerDay = 1,
                        taperScheduledTimes = "08:00",
                        taperInstructions = "Taper down dose from today: Take 1 tablet (8mg) once daily after breakfast",
                        taperEndDate = ""
                    ),
                    AutofillMedInfo(
                        name = "Pantoprazole 40mg",
                        dosage = "1 Capsule",
                        form = "Capsule",
                        instructions = "Take once daily in morning on empty stomach",
                        timesPerDay = 1,
                        scheduledTimes = "07:30",
                        hasTapering = false
                    )
                ),
                source = "SAMPLE_PRESET",
                statusMessage = "✓ Loaded Prescription dated 17th Sept 2026 with Dose Tapering from Today"
            )
            "DIABETES" -> ExtractedPrescription(
                doctorName = "Dr. Ananya Roy, MD (Endocrinology)",
                clinicOrHospital = "Fortis Diabetes & Endocrine Center",
                diseaseOrDiagnosis = "Type 2 Diabetes Mellitus",
                startDate = todayStr,
                endDate = null,
                dischargeAdvice = "Strict diabetic diet: limit carbohydrates, avoid refined sugar, monitor fasting blood glucose daily.",
                notes = "Check HbA1c in 3 months. Next review on 20th next month.",
                medicines = listOf(
                    AutofillMedInfo("Metformin", "500 mg", "Tablet", "Take with meals (breakfast & dinner)", 2, "08:00, 20:00"),
                    AutofillMedInfo("Glimepiride", "1 mg", "Tablet", "Take 15 mins before breakfast", 1, "07:45"),
                    AutofillMedInfo("Vitamin B-Complex & Methylcobalamin", "1 Cap", "Capsule", "After lunch", 1, "13:30")
                ),
                source = "SAMPLE_PRESET",
                statusMessage = "✓ Sample Diabetes & Endocrine Prescription loaded"
            )
            "INFECTION" -> ExtractedPrescription(
                doctorName = "Dr. Vikram Mehta, MD (Internal Medicine)",
                clinicOrHospital = "Max Super Specialty Hospital",
                diseaseOrDiagnosis = "Acute Bronchitis & Upper Respiratory Infection",
                startDate = todayStr,
                endDate = "7 Days Course",
                dischargeAdvice = "Steam inhalation twice daily, drink plenty of warm fluids, rest well, complete full antibiotic course.",
                notes = "Do not stop antibiotics early even if symptoms improve.",
                medicines = listOf(
                    AutofillMedInfo("Amoxicillin + Clavulanic Acid", "625 mg", "Tablet", "After meals every 12 hours", 2, "08:00, 20:00"),
                    AutofillMedInfo("Montelukast + Levocetirizine", "10 mg", "Tablet", "At night before bedtime", 1, "21:30"),
                    AutofillMedInfo("Paracetamol", "650 mg", "Tablet", "After food if fever or pain exceeds 99°F", 3, "08:00, 14:00, 20:00"),
                    AutofillMedInfo("Ambroxol Cough Syrup", "10 ml", "Syrup", "After food three times a day", 3, "08:30, 14:30, 20:30")
                ),
                source = "SAMPLE_PRESET",
                statusMessage = "✓ Sample Infection & Respiratory Prescription loaded"
            )
            else -> ExtractedPrescription(
                doctorName = "Dr. Ramesh Verma, MD, DM (Cardiology)",
                clinicOrHospital = "Apollo Heart & Vascular Institute",
                diseaseOrDiagnosis = "Hypertension & Cardiovascular Risk Management",
                startDate = todayStr,
                endDate = null,
                dischargeAdvice = "Low sodium/salt diet (< 5g/day), 30 minutes brisk walking daily, maintain blood pressure log every morning.",
                notes = "Review in OPD after 4 weeks with lipid profile and kidney function test.",
                medicines = listOf(
                    AutofillMedInfo("Telmisartan", "40 mg", "Tablet", "Take after breakfast with water", 1, "08:00"),
                    AutofillMedInfo("Atorvastatin", "20 mg", "Tablet", "Take after dinner at bedtime", 1, "20:30"),
                    AutofillMedInfo("Amlodipine", "5 mg", "Tablet", "Take in the morning", 1, "08:00"),
                    AutofillMedInfo("Aspirin (Ecosprin)", "75 mg", "Tablet", "Take strictly after heavy lunch", 1, "13:30")
                ),
                source = "SAMPLE_PRESET",
                statusMessage = "✓ Sample Cardiology Prescription loaded"
            )
        }
    }
}
