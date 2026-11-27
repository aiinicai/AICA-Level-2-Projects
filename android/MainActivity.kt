package ae.dirhamtrack.ai.ui

import android.annotation.SuppressLint
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject

/**
 * MainActivity
 * Wraps the DirhamTrack AI web dashboard inside an Android WebView
 * and connects it seamlessly with the native BankNotificationListener.
 *
 * When a bank notification is caught by Android's NotificationListenerService,
 * it is automatically injected into the web dashboard with ZERO manual pasting.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    // Receives transactions intercepted by BankNotificationListener
    private val notificationReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == "ae.dirhamtrack.TRANSACTION_RECORDED") {
                val amount = intent.getDoubleExtra("amount", 0.0)
                val currency = intent.getStringExtra("currency") ?: "AED"
                val merchant = intent.getStringExtra("merchant") ?: "Unknown"
                val category = intent.getStringExtra("category") ?: "Other"
                val bank = intent.getStringExtra("bank") ?: "UAE Bank"
                val type = intent.getStringExtra("type") ?: "expense"
                val isRedFlag = intent.getBooleanExtra("isRedFlag", false)
                val redFlagReason = intent.getStringExtra("redFlagReason") ?: ""
                val raw = intent.getStringExtra("raw") ?: ""

                val payload = JSONObject().apply {
                    put("amount", amount)
                    put("currency", currency)
                    put("merchant", merchant)
                    put("category", category)
                    put("bankName", bank)
                    put("type", type)
                    put("isRedFlag", isRedFlag)
                    put("redFlagReason", redFlagReason)
                    put("rawNotificationText", raw)
                    put("source", "auto_notification")
                }

                // Inject directly into the running UI with zero user interaction
                runOnUiThread {
                    webView.evaluateJavascript(
                        "if (typeof window.onNativeBankNotificationReceived === 'function') { window.onNativeBankNotificationReceived(${payload.toString()}); }",
                        null
                    )
                    Toast.makeText(
                        applicationContext,
                        "DirhamTrack Auto-Caught: $currency $amount at $merchant",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(this)
        setContentView(webView)

        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()

        // Provide Native Bridge to Frontend
        webView.addJavascriptInterface(AndroidBridge(this), "AndroidBridge")

        // Check if Notification Listener permission is granted; prompt user if not
        if (!isNotificationListenerEnabled()) {
            Toast.makeText(
                this,
                "Please enable DirhamTrack in 'Device & app notifications' to automatically catch bank alerts",
                Toast.LENGTH_LONG
            ).show()
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        // Register broadcast receiver for automatic transaction events
        val filter = IntentFilter("ae.dirhamtrack.TRANSACTION_RECORDED")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(notificationReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(notificationReceiver, filter)
        }

        // Load the live app URL or local asset
        val appUrl = "https://ais-dev-vjcjzsbq6gh5mvl3nxprfp-969974775552.europe-west2.run.app"
        webView.loadUrl(appUrl)
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val pkgName = packageName
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        return flat != null && flat.contains(pkgName)
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            unregisterReceiver(notificationReceiver)
        } catch (_: Exception) {}
    }

    inner class AndroidBridge(private val context: Context) {
        @JavascriptInterface
        fun isNativeListenerActive(): Boolean {
            return isNotificationListenerEnabled()
        }

        @JavascriptInterface
        fun openNotificationAccessSettings() {
            context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
    }
}
