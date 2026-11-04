package com.example

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.data.model.UserRole
import com.example.ui.GenerationsAppViewModel
import com.example.ui.screens.LandingScreen
import com.example.ui.screens.OnboardingModal
import com.example.ui.screens.child.ChildMainScreen
import com.example.ui.screens.parent.ParentMainScreen
import com.example.ui.screens.senior.SeniorMainScreen
import com.example.ui.theme.GenerationsTheme
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        com.example.data.reminder.MedicationNotificationManager.createNotificationChannel(applicationContext)

        val navigateToMed = intent?.getStringExtra("NAVIGATE_TO") == "MEDICINES"

        setContent {
            val appViewModel: GenerationsAppViewModel = viewModel()
            val currentRole by appViewModel.currentRole.collectAsState()
            val currentUser by appViewModel.currentUser.collectAsState()
            val preferences by appViewModel.seniorPreferences.collectAsState()
            val palette by appViewModel.palette.collectAsState()

            var showingLanding by remember { mutableStateOf(!navigateToMed) }
            var showingOnboarding by remember { mutableStateOf(false) }
            var showingWebView by remember { mutableStateOf(false) }
            var showingAuth by remember { mutableStateOf(false) }
            var confettiMessage by remember { mutableStateOf<String?>(null) }
            val context = LocalContext.current

            LaunchedEffect(navigateToMed) {
                if (navigateToMed) {
                    appViewModel.setRole(UserRole.SENIOR)
                }
            }

            // Toast listener
            LaunchedEffect(Unit) {
                appViewModel.toastEvent.collect { msg ->
                    Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
                }
            }

            // Confetti reward listener
            LaunchedEffect(Unit) {
                appViewModel.confettiEvent.collect { rewardMsg ->
                    confettiMessage = rewardMsg
                }
            }

            // Handle back navigation
            BackHandler(enabled = showingWebView || showingAuth || !showingLanding) {
                if (showingWebView) {
                    showingWebView = false
                } else if (showingAuth) {
                    showingAuth = false
                } else {
                    showingLanding = true
                }
            }

            GenerationsTheme(
                role = currentRole,
                darkTheme = preferences.highContrast,
                palette = palette
            ) {
                Box(modifier = Modifier.fillMaxSize()) {
                    if (showingWebView) {
                        com.example.ui.screens.WebViewScreen(
                            onBack = { showingWebView = false }
                        )
                    } else if (currentUser == null || showingAuth) {
                        com.example.ui.screens.auth.AuthScreen(
                            viewModel = appViewModel,
                            onAuthSuccess = {
                                showingAuth = false
                                showingLanding = false
                            },
                            onBack = {
                                showingAuth = false
                                showingLanding = true
                            }
                        )
                    } else if (showingLanding) {
                        LandingScreen(
                            viewModel = appViewModel,
                            onRoleSelected = { role ->
                                appViewModel.setRole(role)
                                showingLanding = false
                            },
                            onOpenOnboarding = { showingOnboarding = true },
                            onOpenWebVersion = { showingWebView = true },
                            onOpenAuth = { showingAuth = true }
                        )
                    } else {
                        when (currentRole) {
                            UserRole.SENIOR -> {
                                SeniorMainScreen(
                                    viewModel = appViewModel,
                                    onSwitchProfile = { showingLanding = true }
                                )
                            }
                            UserRole.CHILD -> {
                                ChildMainScreen(
                                    viewModel = appViewModel,
                                    onSwitchProfile = { showingLanding = true }
                                )
                            }
                            UserRole.PARENT -> {
                                ParentMainScreen(
                                    viewModel = appViewModel,
                                    onSwitchProfile = { showingLanding = true }
                                )
                            }
                        }
                    }

                    // Onboarding Modal Dialog
                    if (showingOnboarding) {
                        OnboardingModal(
                            onDismiss = { showingOnboarding = false },
                            onRoleSelected = { role ->
                                appViewModel.setRole(role)
                                showingLanding = false
                            }
                        )
                    }

                    // Joyful Reward Celebration Modal
                    if (confettiMessage != null) {
                        ConfettiRewardDialog(
                            message = confettiMessage!!,
                            onDismiss = { confettiMessage = null }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ConfettiRewardDialog(
    message: String,
    onDismiss: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        Surface(
            shape = RoundedCornerShape(28.dp),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 10.dp,
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
                .testTag("confetti_reward_dialog")
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .size(68.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFFEF08A)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.EmojiEvents,
                        contentDescription = null,
                        tint = Color(0xFF854D0E),
                        modifier = Modifier.size(44.dp)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    text = "🌟 Generational Spark! 🌟",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = message,
                    fontSize = 18.sp,
                    textAlign = TextAlign.Center,
                    lineHeight = 26.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(20.dp))

                Button(
                    onClick = onDismiss,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Text("Hooray!", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
