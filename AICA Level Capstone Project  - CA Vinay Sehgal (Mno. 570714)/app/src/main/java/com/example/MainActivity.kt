package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ui.screens.*
import com.example.ui.theme.MyApplicationTheme
import com.example.ui.viewmodel.CaViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val caViewModel: CaViewModel = viewModel()
                    CaAppRoot(viewModel = caViewModel)
                }
            }
        }
    }
}

@Composable
fun CaAppRoot(viewModel: CaViewModel) {
    val currentUser by viewModel.currentUser.collectAsState()
    var currentScreen by remember { mutableStateOf("dashboard") }

    // When currentUser changes (login / logout / switch demo), reset to dashboard
    LaunchedEffect(currentUser) {
        currentScreen = "dashboard"
    }

    Crossfade(targetState = currentUser, label = "UserCrossfade") { user ->
        if (user == null) {
            AuthScreen(
                viewModel = viewModel,
                onAuthSuccess = {
                    currentScreen = "dashboard"
                }
            )
        } else {
            Crossfade(targetState = currentScreen, label = "ScreenCrossfade") { screen ->
                when (screen) {
                    "analytics" -> {
                        AnalyticsScreen(
                            viewModel = viewModel,
                            onBack = { currentScreen = "dashboard" }
                        )
                    }
                    "profile" -> {
                        ProfileScreen(
                            viewModel = viewModel,
                            onBack = { currentScreen = "dashboard" },
                            onLogout = {
                                currentScreen = "dashboard"
                            }
                        )
                    }
                    else -> {
                        when (user.role.lowercase()) {
                            "admin" -> {
                                AdminScreen(
                                    viewModel = viewModel,
                                    onNavigateToAnalytics = { currentScreen = "analytics" },
                                    onNavigateToProfile = { currentScreen = "profile" }
                                )
                            }
                            "employee" -> {
                                EmployeeScreen(
                                    viewModel = viewModel,
                                    onNavigateToProfile = { currentScreen = "profile" }
                                )
                            }
                            else -> {
                                ClientScreen(
                                    viewModel = viewModel,
                                    onNavigateToProfile = { currentScreen = "profile" }
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
