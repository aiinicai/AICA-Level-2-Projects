package com.example.network

import com.example.BuildConfig
import com.example.model.ExplanationMode
import com.example.model.MappingStatus
import com.example.model.TaxSection
import com.example.model.buildGeminiContext
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

// Moshi data models for Gemini REST API
@JsonClass(generateAdapter = true)
data class GeminiRequest(
    val contents: List<GeminiContent>,
    val systemInstruction: GeminiContent? = null,
    val generationConfig: GeminiGenConfig? = null
)

@JsonClass(generateAdapter = true)
data class GeminiContent(
    val role: String? = null,
    val parts: List<GeminiPart>
)

@JsonClass(generateAdapter = true)
data class GeminiPart(
    val text: String? = null
)

@JsonClass(generateAdapter = true)
data class GeminiGenConfig(
    val temperature: Float? = 0.2f,
    val topP: Float? = 0.95f,
    val topK: Int? = 40
)

@JsonClass(generateAdapter = true)
data class GeminiResponse(
    val candidates: List<GeminiCandidate>? = null
)

@JsonClass(generateAdapter = true)
data class GeminiCandidate(
    val content: GeminiContent? = null
)

interface GeminiApi {
    @POST("v1beta/models/gemini-3.5-flash:generateContent")
    suspend fun generateContent(
        @Query("key") apiKey: String,
        @Body request: GeminiRequest
    ): GeminiResponse
}

object GeminiClient {
    private const val BASE_URL = "https://generativelanguage.googleapis.com/"

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    val service: GeminiApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(GeminiApi::class.java)
    }
}

interface GeminiService {
    suspend fun generateSectionExplanation(
        section: TaxSection,
        mode: ExplanationMode
    ): Result<String>

    suspend fun askQuestion(
        userQuestion: String,
        attachedSection: TaxSection?,
        mode: ExplanationMode,
        history: List<Pair<String, String>> = emptyList()
    ): Result<String>
}

class GeminiTaxService : GeminiService {

    companion object {
        const val UNVERIFIED_PROVISION_BLOCK_MSG = "Verified statutory data for this provision has not yet been loaded into the database. AI comparison and concordance analysis are unavailable until the official source data is ingested and verified."
        const val MISSING_STATUTORY_TEXT_NOTICE = "Note: The full statutory text of this provision has not yet been loaded into the database. Only verified structural mapping and metadata from official sources are available."

        const val SYSTEM_INSTRUCTION_TEXT = """You are TaxBridge AI, an assistant for understanding the transition from the Income-tax Act, 1961 to the Income-tax Act, 2025.

You must distinguish between:
1. Verified source data
2. Source-based explanation
3. AI-generated explanation

Never invent statutory text.
Never invent section mappings.
Never claim that a provision is identical, different or substantively changed unless the supplied source context supports that conclusion.
If statutory text has not been supplied, explicitly say that the statutory text has not yet been loaded.
Use the verified mapping supplied by TaxBridge as the source of truth.
Do not override the TaxBridge mapping with your own knowledge.
If the user asks something outside the supplied context, clearly say that additional source material is required.
You are an educational and research assistant, not a substitute for professional legal or tax advice.

For comparison questions, prefer structured response headers:
### Short Answer
### Old Act
### New Act
### What Changed?
### Why It Matters
### Example
### Source"""
    }

    override suspend fun generateSectionExplanation(
        section: TaxSection,
        mode: ExplanationMode
    ): Result<String> = withContext(Dispatchers.IO) {
        if (section.mappingStatus == MappingStatus.NOT_LOADED || !section.isDataLoaded) {
            return@withContext Result.success(
                """
                ### Short Answer
                Section ${section.oldSectionNumber} is currently marked as **${section.mappingStatus.label}** in the TaxBridge database.
                
                ### Status
                $UNVERIFIED_PROVISION_BLOCK_MSG
                """.trimIndent()
            )
        }

        val apiKey = BuildConfig.GEMINI_API_KEY
        if (apiKey.isBlank() || apiKey == "MY_GEMINI_API_KEY") {
            return@withContext Result.success(getPrecomputedExplanation(section, mode))
        }

        val prompt = buildString {
            appendLine("Provide a clear transitional analysis for this tax provision.")
            appendLine("Target Explanation Mode: ${mode.label} (${mode.subtitle})")
            appendLine()
            appendLine("=== VERIFIED STATUTORY CONTEXT FROM TAXBRIDGE ===")
            appendLine(buildGeminiContext(section))
            appendLine("=================================================")
            appendLine()
            appendLine("Instructions:")
            when (mode) {
                ExplanationMode.SIMPLE -> appendLine("Explain for a non-specialist in plain English. Avoid unnecessary legal terminology. Clearly explain the shift from Section 80C to Section 123 read with Schedule XV.")
                ExplanationMode.PROFESSIONAL -> appendLine("Explain for a CA/tax practitioner. Use appropriate technical terminology. Clearly distinguish source facts from interpretation. Emphasize the restructured architecture of Section 123 + Schedule XV.")
                ExplanationMode.EXAM_CA_STUDENT -> appendLine("Explain for someone studying Indian income tax. Include: concept, old Act position (80C), new Act structure (Section 123 + Schedule XV), key change, memory aid, and a practical example.")
            }
        }

        try {
            val request = GeminiRequest(
                systemInstruction = GeminiContent(
                    parts = listOf(GeminiPart(text = SYSTEM_INSTRUCTION_TEXT))
                ),
                contents = listOf(
                    GeminiContent(
                        role = "user",
                        parts = listOf(GeminiPart(text = prompt))
                    )
                ),
                generationConfig = GeminiGenConfig(temperature = 0.2f)
            )

            val response = GeminiClient.service.generateContent(apiKey, request)
            val text = response.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
            if (!text.isNullOrBlank()) {
                Result.success(text)
            } else {
                Result.success(getPrecomputedExplanation(section, mode))
            }
        } catch (e: Exception) {
            Result.success(getPrecomputedExplanation(section, mode))
        }
    }

    override suspend fun askQuestion(
        userQuestion: String,
        attachedSection: TaxSection?,
        mode: ExplanationMode,
        history: List<Pair<String, String>>
    ): Result<String> = withContext(Dispatchers.IO) {
        if (attachedSection != null && (!attachedSection.isDataLoaded || attachedSection.mappingStatus == MappingStatus.NOT_LOADED)) {
            return@withContext Result.success(
                """
                ### Short Answer
                Section ${attachedSection.oldSectionNumber} is unverified or not yet loaded in the TaxBridge database.
                
                ### Status
                $UNVERIFIED_PROVISION_BLOCK_MSG
                """.trimIndent()
            )
        }

        val apiKey = BuildConfig.GEMINI_API_KEY
        if (apiKey.isBlank() || apiKey == "MY_GEMINI_API_KEY") {
            return@withContext Result.success(getOfflineAssistantResponse(userQuestion, attachedSection, mode))
        }

        val prompt = buildString {
            if (attachedSection != null) {
                appendLine("=== VERIFIED STATUTORY CONTEXT FROM TAXBRIDGE ===")
                appendLine(buildGeminiContext(attachedSection))
                appendLine("=================================================")
                appendLine()
            }
            appendLine("User Question: $userQuestion")
            appendLine("Explanation Mode: ${mode.label} (${mode.subtitle})")
            appendLine("Instructions: Answer strictly adhering to the verified context, distinguishing source facts from AI explanation, and format using the specified structured response headers where appropriate.")
        }

        try {
            val contentList = mutableListOf<GeminiContent>()
            for ((role, text) in history.takeLast(4)) {
                contentList.add(GeminiContent(role = role, parts = listOf(GeminiPart(text = text))))
            }
            contentList.add(GeminiContent(role = "user", parts = listOf(GeminiPart(text = prompt))))

            val request = GeminiRequest(
                systemInstruction = GeminiContent(
                    parts = listOf(GeminiPart(text = SYSTEM_INSTRUCTION_TEXT))
                ),
                contents = contentList,
                generationConfig = GeminiGenConfig(temperature = 0.2f)
            )

            val response = GeminiClient.service.generateContent(apiKey, request)
            val text = response.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
            if (!text.isNullOrBlank()) {
                Result.success(text)
            } else {
                Result.success(getOfflineAssistantResponse(userQuestion, attachedSection, mode))
            }
        } catch (e: Exception) {
            Result.success(getOfflineAssistantResponse(userQuestion, attachedSection, mode))
        }
    }

    private fun getPrecomputedExplanation(section: TaxSection, mode: ExplanationMode): String {
        if (!section.isDataLoaded) {
            return """
            ### Short Answer
            Section ${section.oldSectionNumber} is unverified / not loaded.
            
            ### Status
            $UNVERIFIED_PROVISION_BLOCK_MSG
            """.trimIndent()
        }

        return when (mode) {
            ExplanationMode.SIMPLE -> """
            ### Short Answer
            Under the Income-tax Act, 2025, the popular investment deduction previously under Section 80C is now housed under **Section 123**, while the detailed list of eligible investment instruments is placed in **Schedule XV**.

            ### Old Act
            - **Section 80C** of the Income-tax Act, 1961: Deduction in respect of life insurance premia, provident fund contributions, PPF, ELSS, etc. (Statutory text not yet fully loaded).

            ### New Act
            - **Section 123**: Core deduction provision for investments and specified payments.
            - **Schedule XV**: Detailed catalog of eligible savings instruments and qualifying conditions.

            ### What Changed?
            This is a **structural restructuring**, not a simple one-to-one renumbering. The substantive deduction rule is placed in Section 123, while the itemized list of eligible investment instruments is extracted into Schedule XV.

            ### Why It Matters
            Taxpayers will now reference Section 123 in return filing, and look up qualifying instruments (like PPF, EPF, and Life Insurance) in Schedule XV.

            ### Example
            An individual investing in Public Provident Fund (PPF) claims deduction under Section 123, with PPF eligibility defined by Schedule XV.

            ### Source
            - Income Tax Department / CBDT Transition FAQs & Navigator
            - Old Act: Income-tax Act, 1961 (Section 80C) [PRIMARY]
            - New Act: Income-tax Act, 2025 (Section 123 read with Schedule XV) [PRIMARY]
            """.trimIndent()

            ExplanationMode.PROFESSIONAL -> """
            ### Short Answer
            Section 80C of the 1961 Act undergoes structural reorganization into **Section 123** (charging & deduction mechanism) and **Schedule XV** (itemized qualifying instruments) under the Income-tax Act, 2025.

            ### Old Act
            - **Section 80C (1961 Act)**: Comprehensive single-section architecture consolidating qualifying deductions, limits, and instrument definitions (read with Section 80CCE). Full statutory text not yet loaded.

            ### New Act
            - **Section 123 (2025 Act)**: Primary statutory deduction rule for investments and specified disbursements.
            - **Schedule XV (2025 Act)**: Statutory schedule setting out eligible instruments, qualifying terms, and fund classifications.

            ### What Changed?
            - **Mapping Type**: RESTRUCTURED (Verified)
            - Separation of substantive statutory authority (Sec 123) from instrument taxonomy (Schedule XV).
            - Note: Complete statutory text is awaiting official publication in the database.

            ### Why It Matters
            CAs and tax professionals must update computational templates, ERP mapping tables, and tax audit reporting to cite Section 123 read with Schedule XV.

            ### Example
            A salaried taxpayer claiming deduction for life insurance premia and 5-year tax saving term deposits will claim deduction under Section 123, verifying eligibility under Schedule XV.

            ### Source
            - Income Tax Department / CBDT Official Navigator & FAQ Guidance
            - Primary Sources: Income-tax Act 1961 (Sec 80C); Income-tax Act 2025 (Sec 123 + Schedule XV)
            """.trimIndent()

            ExplanationMode.EXAM_CA_STUDENT -> """
            ### Short Answer
            For tax exams, remember that Section 80C (1961 Act) is reorganized into a 2-tier structure: **Section 123** (Substantive deduction) + **Schedule XV** (Eligible instruments).

            ### Old Act Position
            - Section 80C of the Income-tax Act, 1961: Deductions for LIC, PF, PPF, Sukanya Samriddhi, ELSS, etc. (Statutory text not yet loaded).

            ### New Act Structure
            - **Section 123**: The charging deduction provision.
            - **Schedule XV**: The itemized statutory schedule listing all qualifying funds and instruments.

            ### Key Change & Concept
            - **Architecture**: It is **not** a simple renumbering. It is a restructured concordance separating the operational rule from the schedule of instruments.

            ### Memory Aid
            - 💡 **Memory Rule**: *"123 for the deduction fee, Schedule 15 (XV) lists what qualifies for thee!"*

            ### Example
            If a question asks: "Under which provision is PPF deduction claimed in 2025 Act?", answer: Section 123 read with Schedule XV.

            ### Source
            - Income Tax Department / CBDT Transition Navigator
            - Verified Status: PRIMARY Act references (Sec 123 / Schedule XV)
            """.trimIndent()
        }
    }

    private fun getOfflineAssistantResponse(
        question: String,
        section: TaxSection?,
        mode: ExplanationMode
    ): String {
        val q = question.lowercase().trim()

        if (section == null) {
            return """
            ### Short Answer
            Welcome to TaxBridge AI. Please select a statutory provision (e.g. Section 80C) from the provision selector above to analyze its transition from the 1961 Act to the 2025 Act.
            
            ### Available Verified Provisions
            - **Section 80C** → Section 123 + Schedule XV (Verified Restructured Mapping)
            
            ### Unloaded Provisions
            - Sections 43B, 14A, 37, 10, 2 are currently tagged as **DATA NOT YET LOADED** pending official verification.
            """.trimIndent()
        }

        if (!section.isDataLoaded || section.mappingStatus == MappingStatus.NOT_LOADED) {
            return """
            ### Short Answer
            Section ${section.oldSectionNumber} is unverified or not yet loaded in the TaxBridge database.
            
            ### Status
            $UNVERIFIED_PROVISION_BLOCK_MSG
            """.trimIndent()
        }

        // Section 80C questions handling
        if (q.contains("why is schedule xv involved") || q.contains("schedule xv") || q.contains("schedule")) {
            return """
            ### Short Answer
            **Schedule XV** is involved because the 2025 Act modularized the law: Section 123 grants the substantive deduction, while Schedule XV itemizes the specific qualifying investment instruments (e.g., PPF, EPF, life insurance, ELSS).

            ### Old Act
            In the 1961 Act, Section 80C contained both the deduction mechanism and lengthy sub-clauses defining eligible instruments. (Statutory text not yet fully loaded).

            ### New Act
            The 2025 Act segregates the deduction limit (Section 123) from the instrument catalog (Schedule XV).

            ### What Changed?
            Restructured drafting architecture separating substantive deduction rules from instrument categories.

            ### Why It Matters
            This keeps the main body of the Act streamlined while allowing schedule updates without altering core section numbering.

            ### Example
            A taxpayer investing in National Savings Certificates (NSC) looks up NSC under Schedule XV and claims deduction under Section 123.

            ### Source
            - Income Tax Department / CBDT Transition FAQs & Navigator (Item 18/24)
            - Income-tax Act, 2025: Section 123 & Schedule XV [PRIMARY]
            """.trimIndent()
        }

        if (q.contains("is this just renumbering") || q.contains("just renumbering") || q.contains("renumbering")) {
            return """
            ### Short Answer
            **No, this is not just a simple renumbering.** The official CBDT classification is **RESTRUCTURED**.

            ### Old Act
            Section 80C consolidated both the qualifying deduction rules and the expansive catalog of eligible instruments in one monolithic section.

            ### New Act
            The 2025 Act splits this into **Section 123** (deduction framework) and **Schedule XV** (detailed list of eligible instruments and conditions).

            ### What Changed?
            Structural bifurcation into a core section and a dedicated statutory schedule.

            ### Why It Matters
            Treating it as a simple renumbering would cause confusion because the qualifying criteria and eligible funds now reside in Schedule XV.

            ### Source
            - Income Tax Department / CBDT Official 1961 ↔ 2025 Navigator
            """.trimIndent()
        }

        if (q.contains("corresponding provision") || q.contains("what is the corresponding")) {
            return """
            ### Short Answer
            The corresponding 2025 provisions for Section 80C are **Section 123** and **Schedule XV**.

            ### Old Act
            - Section 80C: Deduction in respect of life insurance premia, contributions to provident fund, etc.

            ### New Act
            - **Section 123**: Deduction in respect of investments and specified payments.
            - **Schedule XV**: Eligible Instruments and Specified Funds for Investment Deductions.

            ### What Changed?
            Restructured into substantive section + schedule.

            ### Source
            - Income-tax Act, 2025 (as amended by Finance Act, 2026) [PRIMARY]
            """.trimIndent()
        }

        if (q.contains("ca student") || q.contains("exam")) {
            return getPrecomputedExplanation(section, ExplanationMode.EXAM_CA_STUDENT)
        }

        if (q.contains("simply") || q.contains("simple")) {
            return getPrecomputedExplanation(section, ExplanationMode.SIMPLE)
        }

        if (q.contains("professional") || q.contains("technical")) {
            return getPrecomputedExplanation(section, ExplanationMode.PROFESSIONAL)
        }

        return getPrecomputedExplanation(section, mode)
    }
}
