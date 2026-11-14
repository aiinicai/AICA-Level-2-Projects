package com.giaarthwise.loanfacilitator;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final String PREFS_NAME = "GiaArthwiseLoanPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_URL = "http://192.0.0.2:8000";
    private static final int FILECHOOSER_RESULTCODE = 1001;

    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout errorLayout;
    private TextView errorTextView;
    private ValueCallback<Uri[]> uploadMessage;
    private SharedPreferences preferences;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Configure Status Bar Color
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            Window window = getWindow();
            window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            window.setStatusBarColor(Color.parseColor("#111820"));
        }

        preferences = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);

        // Build UI Layout Programmatically
        LinearLayout rootLayout = new LinearLayout(this);
        rootLayout.setOrientation(LinearLayout.VERTICAL);
        rootLayout.setBackgroundColor(Color.parseColor("#f8fafc"));
        rootLayout.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        // Header Action Bar
        LinearLayout headerLayout = new LinearLayout(this);
        headerLayout.setOrientation(LinearLayout.HORIZONTAL);
        headerLayout.setBackgroundColor(Color.parseColor("#1b2632"));
        headerLayout.setPadding(32, 24, 32, 24);
        headerLayout.setGravity(Gravity.CENTER_VERTICAL);
        headerLayout.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView titleView = new TextView(this);
        titleView.setText("GIA_ARTHWISE | Loan Facilitator");
        titleView.setTextColor(Color.WHITE);
        titleView.setTextSize(16);
        titleView.setTypeface(null, android.graphics.Typeface.BOLD);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f);
        titleView.setLayoutParams(titleParams);
        headerLayout.addView(titleView);

        // Change Server Button
        Button serverBtn = new Button(this);
        serverBtn.setText("⚙ Server IP");
        serverBtn.setTextSize(12);
        serverBtn.setTextColor(Color.parseColor("#1b2632"));
        serverBtn.setBackgroundColor(Color.WHITE);
        serverBtn.setPadding(24, 8, 24, 8);
        serverBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showServerUrlDialog();
            }
        });
        headerLayout.addView(serverBtn);

        rootLayout.addView(headerLayout);

        // Progress Bar
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 8));
        progressBar.setMax(100);
        progressBar.setVisibility(View.GONE);
        rootLayout.addView(progressBar);

        // Content Container (WebView + Error View)
        FrameLayout contentContainer = new FrameLayout(this);
        contentContainer.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1.0f));

        // WebView
        webView = new WebView(this);
        webView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        setupWebView();
        contentContainer.addView(webView);

        // Error Fallback View
        errorLayout = new LinearLayout(this);
        errorLayout.setOrientation(LinearLayout.VERTICAL);
        errorLayout.setGravity(Gravity.CENTER);
        errorLayout.setPadding(48, 48, 48, 48);
        errorLayout.setBackgroundColor(Color.WHITE);
        errorLayout.setVisibility(View.GONE);
        errorLayout.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        TextView errorTitle = new TextView(this);
        errorTitle.setText("Connection Notice");
        errorTitle.setTextSize(18);
        errorTitle.setTypeface(null, android.graphics.Typeface.BOLD);
        errorTitle.setTextColor(Color.parseColor("#0f172a"));
        errorLayout.addView(errorTitle);

        errorTextView = new TextView(this);
        errorTextView.setTextSize(13);
        errorTextView.setTextColor(Color.parseColor("#64748b"));
        errorTextView.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams errTextParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        errTextParams.setMargins(0, 16, 0, 32);
        errorTextView.setLayoutParams(errTextParams);
        errorLayout.addView(errorTextView);

        Button retryButton = new Button(this);
        retryButton.setText("Retry Connection");
        retryButton.setTextColor(Color.WHITE);
        retryButton.setBackgroundColor(Color.parseColor("#1b2632"));
        retryButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                loadCurrentServerUrl();
            }
        });
        errorLayout.addView(retryButton);

        Button changeIpButton = new Button(this);
        changeIpButton.setText("Change Server IP / Domain");
        changeIpButton.setTextColor(Color.parseColor("#1b2632"));
        changeIpButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showServerUrlDialog();
            }
        });
        errorLayout.addView(changeIpButton);

        contentContainer.addView(errorLayout);
        rootLayout.addView(contentContainer);

        setContentView(rootLayout);

        // Load configured URL
        loadCurrentServerUrl();
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(false);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                progressBar.setVisibility(View.VISIBLE);
                errorLayout.setVisibility(View.GONE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    progressBar.setVisibility(View.GONE);
                    errorLayout.setVisibility(View.VISIBLE);
                    String currentUrl = preferences.getString(KEY_SERVER_URL, DEFAULT_URL);
                    errorTextView.setText("Could not connect to the backend server at:\n" + currentUrl +
                            "\n\nMake sure the FastAPI server is running (e.g. ./start.sh) and your phone is connected to the same Wi-Fi network.");
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                if (newProgress == 100) {
                    progressBar.setVisibility(View.GONE);
                }
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                return super.onConsoleMessage(consoleMessage);
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (uploadMessage != null) {
                    uploadMessage.onReceiveValue(null);
                }
                uploadMessage = filePathCallback;

                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");

                try {
                    startActivityForResult(Intent.createChooser(intent, "Select Client Document"), FILECHOOSER_RESULTCODE);
                } catch (ActivityNotFoundException e) {
                    uploadMessage = null;
                    Toast.makeText(MainActivity.this, "Cannot open file chooser", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });
    }

    private void loadCurrentServerUrl() {
        String serverUrl = preferences.getString(KEY_SERVER_URL, DEFAULT_URL);
        errorLayout.setVisibility(View.GONE);
        webView.loadUrl(serverUrl);
    }

    private void showServerUrlDialog() {
        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        String currentUrl = preferences.getString(KEY_SERVER_URL, DEFAULT_URL);
        input.setText(currentUrl);
        input.setSelection(currentUrl.length());

        new AlertDialog.Builder(this)
                .setTitle("Configure Server Endpoint")
                .setMessage("Enter the URL of your GIA_Arthwise server (e.g. http://192.168.1.15:8000 or production domain):")
                .setView(input)
                .setPositiveButton("Save & Connect", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        String newUrl = input.getText().toString().trim();
                        if (!newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
                            newUrl = "http://" + newUrl;
                        }
                        preferences.edit().putString(KEY_SERVER_URL, newUrl).apply();
                        Toast.makeText(MainActivity.this, "Connecting to " + newUrl, Toast.LENGTH_SHORT).show();
                        loadCurrentServerUrl();
                    }
                })
                .setNeutralButton("Load Bundled Web Assets", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        webView.loadUrl("file:///android_asset/www/index.html");
                    }
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent intent) {
        if (requestCode == FILECHOOSER_RESULTCODE) {
            if (uploadMessage == null) return;
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && intent != null) {
                String dataString = intent.getDataString();
                if (dataString != null) {
                    results = new Uri[]{Uri.parse(dataString)};
                } else if (intent.getClipData() != null) {
                    int count = intent.getClipData().getItemCount();
                    results = new Uri[count];
                    for (int i = 0; i < count; i++) {
                        results[i] = intent.getClipData().getItemAt(i).getUri();
                    }
                }
            }
            uploadMessage.onReceiveValue(results);
            uploadMessage = null;
        } else {
            super.onActivityResult(requestCode, resultCode, intent);
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
