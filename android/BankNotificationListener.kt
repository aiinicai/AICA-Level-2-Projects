package ae.dirhamtrack.ai.service

import android.app.Notification
import android.content.Intent
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.regex.Pattern

/**
 * BankNotificationListener
 * Native Android NotificationListenerService that captures push notifications
 * from Emirates NBD, Citi, FAB, Mashreq (including salary deposits), CBD, and SMS messaging apps.
 */
class BankNotificationListener : NotificationListenerService() {

    private val TAG = "DirhamTrackListener"
    private val scope = CoroutineScope(Dispatchers.IO)

    // Known UAE Banking app package identifiers & SMS apps
    private val BANK_PACKAGES = setOf(
        "com.emiratesnbd.enbd",
        "com.citibank.citimobile.ae",
        "com.bankfab.mobile",
        "com.mashreq.mobile",
        "com.cbd.mobile",
        "com.rakbank.digital",
        "com.google.android.apps.messaging", // SMS bank alerts
        "com.samsung.android.messaging"
    )

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        if (sbn == null) return

        val packageName = sbn.packageName
        val extras: Bundle = sbn.notification.extras
        val title = extras.getString(Notification.EXTRA_TITLE, "") ?: ""
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: ""
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString() ?: text

        val fullContent = "$title $bigText"

        // Filter: Check if originating from bank app or contains financial keywords
        val isFinancial = fullContent.contains("AED", ignoreCase = true) ||
                fullContent.contains("Purchase", ignoreCase = true) ||
                fullContent.contains("debited", ignoreCase = true) ||
                fullContent.contains("spent", ignoreCase = true) ||
                fullContent.contains("credited", ignoreCase = true) ||
                fullContent.contains("Salary", ignoreCase = true) ||
                BANK_PACKAGES.contains(packageName)

        if (!isFinancial) return

        Log.d(TAG, "Captured Financial Notification from $packageName: $fullContent")

        scope.launch {
            processAndStoreTransaction(title, bigText, packageName)
        }
    }

    private fun processAndStoreTransaction(title: String, body: String, pkg: String) {
        val full = "$title $body"

        // 1. Detect Bank
        val bankName = when {
            full.contains("Emirates NBD", true) || full.contains("ENBD", true) -> "Emirates NBD"
            full.contains("Citi", true) || full.contains("Citibank", true) -> "Citi"
            full.contains("Mashreq", true) -> "Mashreq"
            full.contains("FAB", true) || full.contains("First Abu Dhabi", true) -> "FAB"
            full.contains("CBD", true) -> "CBD"
            else -> "UAE Bank"
        }

        // 2. Identify Salary Deposit vs Expense
        val isSalary = full.contains("Salary", true) || full.contains("WPS", true)
        val isIncome = isSalary || (full.contains("credited", true) && !full.contains("spent", true) && !full.contains("debited", true))
        val type = if (isIncome) "income" else "expense"

        // 3. Extract Amount & Currency
        var currency = "AED"
        var amount = 0.0
        var isRedFlag = false
        var redFlagReason = ""

        // Check foreign currency first
        val foreignPattern = Pattern.compile("\\b(USD|EUR|GBP|INR|SAR)\\s*([0-9,]+\\.[0-9]{2})", Pattern.CASE_INSENSITIVE)
        val foreignMatcher = foreignPattern.matcher(full)

        val creditPattern = Pattern.compile("(?:credited(?:\\s+with)?|salary(?:\\s+of)?)\\s*(?:AED|DHS)?\\s*([0-9,]+(?:\\.[0-9]{1,2})?)", Pattern.CASE_INSENSITIVE)
        val creditMatcher = creditPattern.matcher(full)

        val aedPattern = Pattern.compile("\\b(?:AED|DHS)\\s*([0-9,]+(?:\\.[0-9]{1,2})?)", Pattern.CASE_INSENSITIVE)
        val aedMatcher = aedPattern.matcher(full)

        if (foreignMatcher.find()) {
            val foreignCurr = foreignMatcher.group(1)?.uppercase() ?: "USD"
            val foreignAmt = foreignMatcher.group(2)?.replace(",", "")?.toDoubleOrNull() ?: 0.0
            isRedFlag = true
            redFlagReason = "Foreign currency ($foreignCurr $foreignAmt) detected outside UAE."

            // Approximate conversion to AED
            val fxRate = when (foreignCurr) {
                "USD" -> 3.6725
                "EUR" -> 3.98
                "GBP" -> 4.65
                "INR" -> 0.044
                else -> 3.67
            }
            amount = foreignAmt * fxRate
        } else if (isIncome && creditMatcher.find()) {
            amount = creditMatcher.group(1)?.replace(",", "")?.toDoubleOrNull() ?: 0.0
        } else if (aedMatcher.find()) {
            amount = aedMatcher.group(1)?.replace(",", "")?.toDoubleOrNull() ?: 0.0
        }

        if (type == "expense" && amount > 1500.0 && !isRedFlag) {
            isRedFlag = true
            redFlagReason = "High value purchase (> AED 1,500.00)"
        }

        // 4. Extract Merchant or Income Source
        var merchant = "Unknown Merchant"
        var category = "Other"

        if (isSalary) {
            category = "Salary"
            merchant = if (bankName == "Mashreq") "Mashreq Salary Deposit" else "Salary Deposit"
        } else if (isIncome) {
            category = "Other"
            merchant = if (bankName == "Mashreq") "Mashreq Credit Deposit" else "Bank Credit Transfer"
        } else {
            val merchantPattern = Pattern.compile("\\b(?:at|to|in)\\s+([A-Z0-9\\s&.\\-/]+?)(?:\\s+(?:on|dated|ref|avail|limit)|\\.|,|$)", Pattern.CASE_INSENSITIVE)
            val mMatcher = merchantPattern.matcher(full)
            if (mMatcher.find()) {
                merchant = mMatcher.group(1)?.trim() ?: "Unknown Merchant"
            }

            category = when {
                merchant.contains("ENOC", true) || merchant.contains("ADNOC", true) || merchant.contains("EPPCO", true) -> "Petrol"
                merchant.contains("KFC", true) || merchant.contains("McDonald", true) || merchant.contains("Starbucks", true) -> "Food"
                merchant.contains("Carrefour", true) || merchant.contains("Lulu", true) || merchant.contains("Nesto", true) -> "Groceries"
                merchant.contains("DEWA", true) || merchant.contains("SEWA", true) -> "Utilities"
                merchant.contains("Etisalat", true) || merchant.contains("du", true) -> "Telecom"
                merchant.contains("Amazon", true) || merchant.contains("Noon", true) -> "Shopping"
                merchant.contains("RTA", true) || merchant.contains("Salik", true) || merchant.contains("Careem", true) -> "Transport"
                else -> "Other"
            }
        }

        Log.i(TAG, "Recorded: $bankName | $type | AED $amount | $merchant | $category | RedFlag: $isRedFlag ($redFlagReason)")

        // Broadcast to local Android WebView Activity
        val intent = Intent("ae.dirhamtrack.TRANSACTION_RECORDED").apply {
            putExtra("amount", amount)
            putExtra("currency", currency)
            putExtra("merchant", merchant)
            putExtra("category", category)
            putExtra("bank", bankName)
            putExtra("type", type)
            putExtra("isRedFlag", isRedFlag)
            putExtra("redFlagReason", redFlagReason)
            putExtra("raw", full)
        }
        sendBroadcast(intent)
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {}
}
