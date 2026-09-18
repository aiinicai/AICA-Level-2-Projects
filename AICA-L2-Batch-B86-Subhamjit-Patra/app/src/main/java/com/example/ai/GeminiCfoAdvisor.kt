package com.example.ai

import com.example.BuildConfig
import com.example.data.local.AssetEntity
import com.example.data.local.LiabilityEntity
import com.example.data.local.UserProfileEntity
import com.example.domain.engine.FinancialHealthResult
import com.example.util.CurrencyFormatter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object GeminiCfoAdvisor {

    private val client = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build()

    suspend fun consultCfo(
        userQuery: String,
        profile: UserProfileEntity,
        netWorth: Double,
        totalAssets: Double,
        totalLiabilities: Double,
        monthlyIncome: Double,
        healthResult: FinancialHealthResult,
        assets: List<AssetEntity>,
        liabilities: List<LiabilityEntity>
    ): String = withContext(Dispatchers.IO) {
        val apiKey = try {
            BuildConfig.GEMINI_API_KEY
        } catch (e: Exception) {
            ""
        }

        // Build Indian context prompt with Lakhs & Crores
        val contextPrompt = buildString {
            append("You are Pocket CFO, a Senior Chartered Financial Analyst (CFA/CFP) and fiduciary Personal CFO operating in the Indian financial regulatory landscape (RBI, SEBI, Income Tax Act).\n")
            append("Client Profile:\n")
            append("- Name: ${profile.name} (Age: ${profile.currentAge}, Target Retirement: ${profile.retirementAge})\n")
            append("- Profession: ${profile.profession}, City: ${profile.city}, Tax Regime: ${profile.taxRegime}\n")
            append("- Monthly Take-home Income: ${CurrencyFormatter.formatInr(monthlyIncome)}\n")
            append("- Consolidated Net Worth: ${CurrencyFormatter.formatInr(netWorth, compact = true)} (Gross Assets: ${CurrencyFormatter.formatInr(totalAssets, compact = true)}, Total Liabilities: ${CurrencyFormatter.formatInr(totalLiabilities, compact = true)})\n")
            append("- Financial Health Score: ${healthResult.totalScore}/100 (${healthResult.grade})\n")
            append("- Emergency Fund Runway: ${String.format("%.1f", healthResult.emergencyFundMonths)} months of family living expenses\n")
            append("- Debt-to-Income (EMI/Income): ${String.format("%.1f", healthResult.debtToIncomePercent)}%\n")
            append("- Monthly Savings Rate: ${String.format("%.1f", healthResult.savingsRatePercent)}%\n")
            append("\nClient Query: \"$userQuery\"\n")
            append("Respond with rigorous Indian fiduciary advice using INR (₹), Lakhs (L), and Crores (Cr). Factor in relevant Indian financial instruments (EPF 8.25%, PPF 7.1%, NPS Tier-1, Nifty 50 Index SIPs, Sovereign Gold Bonds, Home Loan interest Section 24b vs New Regime 115BAC, and 20/4/10 car affordability). Format with scannable bullet points and clear numbers.")
        }

        if (apiKey.isBlank() || apiKey == "MY_GEMINI_API_KEY" || apiKey.startsWith("PLACEHOLDER")) {
            return@withContext generateFiduciaryOfflineAdvice(userQuery, profile, netWorth, healthResult)
        }

        try {
            val jsonBody = JSONObject().apply {
                val contentsArray = JSONArray().apply {
                    val contentObj = JSONObject().apply {
                        val partsArray = JSONArray().apply {
                            put(JSONObject().put("text", contextPrompt))
                        }
                        put("parts", partsArray)
                    }
                    put(contentObj)
                }
                put("contents", contentsArray)
            }

            val mediaType = "application/json; charset=utf-8".toMediaType()
            val requestBody = jsonBody.toString().toRequestBody(mediaType)
            val url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$apiKey"

            val request = Request.Builder()
                .url(url)
                .post(requestBody)
                .build()

            val response = client.newCall(request).execute()
            val responseString = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val rootJson = JSONObject(responseString)
                val candidates = rootJson.optJSONArray("candidates")
                val firstCandidate = candidates?.optJSONObject(0)
                val content = firstCandidate?.optJSONObject("content")
                val parts = content?.optJSONArray("parts")
                val text = parts?.optJSONObject(0)?.optString("text")

                if (!text.isNullOrBlank()) {
                    return@withContext text.trim()
                }
            }
        } catch (e: Exception) {
            // fallback gracefully
        }

        generateFiduciaryOfflineAdvice(userQuery, profile, netWorth, healthResult)
    }

    private fun generateFiduciaryOfflineAdvice(
        query: String,
        profile: UserProfileEntity,
        netWorth: Double,
        health: FinancialHealthResult
    ): String {
        val q = query.lowercase()
        return when {
            q.contains("buy") && q.contains("rent") -> {
                "### Fiduciary Assessment: Buy vs Rent in ${profile.city}\n\n" +
                "• **Real Cost of Home Ownership**: A ₹1 Crore home in urban India typically demands ~₹20L down payment, ₹8L stamp duty & registration, plus interior capex. At 8.5% interest, a 20-year loan costs ~₹86,782/month in EMI, resulting in over ₹1.08 Crore in interest alone.\n" +
                "• **The Rent & Equity SIP Alternative**: Equivalent rental yield in cities like Bengaluru/Pune is 3.0%–3.5% (approx ₹30,000–₹35,000/month). Investing the ₹50,000+ monthly EMI difference plus down payment into a Nifty 50 / Flexi Cap SIP (12.5% CAGR) historically compounds to ~₹1.85 Cr liquid wealth in 10 years.\n" +
                "• **Personal CFO Recommendation**: If you plan to stay in the same locality for 10+ years, buying provides emotional stability. Otherwise, renting and running equity SIPs yields superior liquidity and geographical freedom."
            }
            q.contains("prepay") || q.contains("loan vs sip") || q.contains("mortgage") -> {
                "### Financial Audit: Prepay Loan vs Nifty 50 SIP\n\n" +
                "• **Debt Cost vs Return Arbitrage**: Your home loan interest rate is ~8.5% p.a. Under the New Tax Regime (Section 115BAC), home loan interest deduction under Section 24b is generally not applicable on self-occupied properties, making your effective debt cost a true 8.5%.\n" +
                "• **Equity Opportunity Return**: Broad Indian equities (Nifty 50 / Nifty 500) provide ~12.0%–13.5% long-term nominal CAGR. Even after 12.5% Long Term Capital Gains (LTCG) tax above ₹1.25 Lakh, net expected equity return is ~11.0%.\n" +
                "• **CFO Verdict**: Keep your equity SIP active, but allocate 20% of your annual bonus towards principal prepayment. Prepaying just 1 extra EMI per year reduces a 20-year loan to approximately 16 years, saving Lakhs in interest without sacrificing equity compounding."
            }
            q.contains("car") || q.contains("afford") || q.contains("vehicle") -> {
                val allowedMonthly = profile.monthlyIncome * 0.10
                "### 20/4/10 Car Affordability Analysis\n\n" +
                "• **The Rule**: 20% minimum down payment, maximum 4-year tenure (48 months), and total vehicle expense (EMI + Fuel + Insurance) under 10% of monthly take-home (${CurrencyFormatter.formatInr(allowedMonthly)}/mo for your salary of ${CurrencyFormatter.formatInr(profile.monthlyIncome)}).\n" +
                "• **Depreciation Reality**: A brand-new car depreciates 20%–25% in year one. In Indian metro traffic, electric vehicles (EVs) or 2–3 year pre-owned certified cars yield maximum utility-per-rupee.\n" +
                "• **CFO Recommendation**: Target on-road price where total monthly outflow stays below ${CurrencyFormatter.formatInr(allowedMonthly)}. Never compromise your emergency fund or mutual fund SIPs for vehicle upgrades."
            }
            q.contains("tax") || q.contains("regime") || q.contains("80c") -> {
                "### Tax Optimization Audit (Old vs New Regime)\n\n" +
                "• **New Regime (Section 115BAC)**: Offers reduced slab rates with standard deduction of ₹75,000. For taxable incomes up to ₹15 Lakhs without heavy home loan interest or HRA, New Regime is mathematically superior.\n" +
                "• **Old Regime Threshold**: Requires deductions exceeding ₹4.25 Lakhs (₹1.5L 80C + ₹50k 80CCD NPS + ₹25k 80D + ₹2L Section 24b home loan interest) to beat the New Regime.\n" +
                "• **NPS 80CCD(1B)**: Invest ₹50,000 in NPS Tier-1 for additional deduction under Old Regime, or use employer NPS contribution up to 14% under Section 80CCD(2) which is exempt even under the New Regime!"
            }
            else -> {
                "### Personal CFO Executive Statement\n\n" +
                "• **Net Worth Status**: Your consolidated net worth is ${CurrencyFormatter.formatInr(netWorth, compact = true)} with a Financial Health Score of ${health.totalScore}/100 (${health.grade}).\n" +
                "• **Emergency Buffer**: You maintain ${String.format("%.1f", health.emergencyFundMonths)} months of liquid runway across bank savings and FDs.\n" +
                "• **Key Action Item**: Automate ₹50,000+ monthly SIPs on your salary credit date, ensure your pure term insurance cover is at least 10x annual income (₹2.5 Cr+), and review tax regime elections before the financial year closing."
            }
        }
    }
}
