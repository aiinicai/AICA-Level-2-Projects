package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.cube.ui.CameraCaptureScreen
import com.example.cube.ui.CubeViewModel
import com.example.cube.ui.HomeScreen
import com.example.cube.ui.ManualEditorScreen
import com.example.cube.ui.NotationGuideScreen
import com.example.cube.ui.ProfileHistoryScreen
import com.example.cube.ui.Screen
import com.example.cube.ui.SolutionScreen
import com.example.ui.theme.MyApplicationTheme

class MainActivity : ComponentActivity() {

    private val viewModel: CubeViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                MainAppContent(
                    viewModel = viewModel,
                    activity = this
                )
            }
        }
    }
}

@Composable
fun MainAppContent(
    viewModel: CubeViewModel,
    activity: ComponentActivity
) {
    val uiState by viewModel.uiState.collectAsState()
    val currentUser by viewModel.authManager.authStateFlow().collectAsState(initial = viewModel.authManager.currentUser)
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.errorMessage) {
        val err = uiState.errorMessage
        if (err != null) {
            snackbarHostState.showSnackbar(err)
        }
    }

    LaunchedEffect(uiState.saveSuccessMessage) {
        val msg = uiState.saveSuccessMessage
        if (msg != null) {
            snackbarHostState.showSnackbar(msg)
            viewModel.clearSuccess()
        }
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (uiState.screen) {
                Screen.HOME -> {
                    HomeScreen(
                        currentUser = currentUser,
                        onNavigateToCamera = { viewModel.navigateTo(Screen.CAMERA) },
                        onNavigateToManualEditor = { viewModel.openManualEditor() },
                        onNavigateToProfile = { viewModel.navigateTo(Screen.PROFILE_HISTORY) },
                        onNavigateToNotationGuide = { viewModel.navigateTo(Screen.NOTATION_GUIDE) },
                        onSolvePreset = { preset -> viewModel.solveCube(preset) }
                    )
                }

                Screen.CAMERA -> {
                    CameraCaptureScreen(
                        onPhotosCaptured = { photos -> viewModel.processCapturedPhotos(photos) },
                        onNavigateToManualEditor = { viewModel.openManualEditor() },
                        onBack = { viewModel.navigateTo(Screen.HOME) },
                        isProcessing = uiState.isProcessing
                    )
                }

                Screen.MANUAL_EDITOR -> {
                    ManualEditorScreen(
                        initialCubeState = uiState.currentCubeState,
                        onSolve = { state -> viewModel.solveCube(state) },
                        onBack = { viewModel.navigateTo(Screen.HOME) }
                    )
                }

                Screen.SOLUTION -> {
                    SolutionScreen(
                        initialCubeState = uiState.currentCubeState,
                        solutionMoves = uiState.solutionMoves,
                        solveTimeMs = uiState.solveTimeMs,
                        currentUser = currentUser,
                        onSaveSolve = { name, tags ->
                            viewModel.saveCurrentSolve(name, tags)
                        },
                        onSignInRequested = {
                            viewModel.signInWithGoogle(activity)
                        },
                        onOpenNotationGuide = {
                            viewModel.navigateTo(Screen.NOTATION_GUIDE)
                        },
                        onBack = { viewModel.navigateTo(Screen.HOME) }
                    )
                }

                Screen.PROFILE_HISTORY -> {
                    ProfileHistoryScreen(
                        authManager = viewModel.authManager,
                        historyRepository = viewModel.historyRepository,
                        onLoadSolve = { state, moves, time ->
                            viewModel.loadSavedSolve(state, moves, time)
                        },
                        onBack = { viewModel.navigateTo(Screen.HOME) }
                    )
                }

                Screen.NOTATION_GUIDE -> {
                    NotationGuideScreen(
                        onBack = { viewModel.navigateTo(Screen.HOME) }
                    )
                }
            }

            // Processing overlay dialog
            if (uiState.isProcessing) {
                AlertDialog(
                    onDismissRequest = {},
                    confirmButton = {},
                    title = { Text(uiState.statusMessage ?: "Processing") },
                    text = {
                        Box(
                            modifier = Modifier.fillMaxWidth().height(100.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator()
                        }
                    }
                )
            }

            // Error Dialog
            if (uiState.errorMessage != null && uiState.screen != Screen.MANUAL_EDITOR && uiState.screen != Screen.PROFILE_HISTORY) {
                AlertDialog(
                    onDismissRequest = { viewModel.clearError() },
                    confirmButton = {
                        TextButton(onClick = { viewModel.clearError() }) {
                            Text("OK")
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = {
                            viewModel.clearError()
                            viewModel.openManualEditor()
                        }) {
                            Text("Open Palette Editor")
                        }
                    },
                    title = { Text("Cube State Error") },
                    text = { Text(uiState.errorMessage.orEmpty()) }
                )
            }
        }
    }
}
