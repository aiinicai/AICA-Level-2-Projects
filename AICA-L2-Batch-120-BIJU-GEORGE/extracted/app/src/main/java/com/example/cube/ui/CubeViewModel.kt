package com.example.cube.ui

import android.app.Activity
import android.app.Application
import android.graphics.Bitmap
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.cube.auth.AuthManager
import com.example.cube.data.CubeHistoryRepository
import com.example.cube.gemini.GeminiVisionParser
import com.example.cube.model.CubeMove
import com.example.cube.model.CubeState
import com.example.cube.solver.KociembaSolver
import com.google.firebase.auth.FirebaseUser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class Screen {
    HOME,
    CAMERA,
    MANUAL_EDITOR,
    SOLUTION,
    PROFILE_HISTORY,
    NOTATION_GUIDE
}

data class CubeUiState(
    val screen: Screen = Screen.HOME,
    val isProcessing: Boolean = false,
    val statusMessage: String? = null,
    val errorMessage: String? = null,
    val currentCubeState: CubeState = CubeState.solved(),
    val solutionMoves: List<CubeMove> = emptyList(),
    val solveTimeMs: Long = 0L,
    val geminiErrorNotes: String? = null,
    val isSavingSolve: Boolean = false,
    val saveSuccessMessage: String? = null
)

class CubeViewModel(application: Application) : AndroidViewModel(application) {

    val historyRepository = CubeHistoryRepository(application)
    val authManager = AuthManager(application, historyRepository)

    private val _uiState = MutableStateFlow(CubeUiState())
    val uiState: StateFlow<CubeUiState> = _uiState.asStateFlow()

    fun navigateTo(screen: Screen) {
        _uiState.value = _uiState.value.copy(
            screen = screen,
            errorMessage = null,
            statusMessage = null,
            saveSuccessMessage = null
        )
    }

    fun openManualEditor(state: CubeState? = null) {
        _uiState.value = _uiState.value.copy(
            screen = Screen.MANUAL_EDITOR,
            currentCubeState = state ?: _uiState.value.currentCubeState,
            errorMessage = null
        )
    }

    fun solveCube(cubeState: CubeState) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isProcessing = true,
                statusMessage = "Computing optimal solve sequence...",
                errorMessage = null
            )

            val result = KociembaSolver.solve(cubeState)

            when (result) {
                is KociembaSolver.SolveResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isProcessing = false,
                        screen = Screen.SOLUTION,
                        currentCubeState = cubeState,
                        solutionMoves = result.moves,
                        solveTimeMs = result.timeMs,
                        statusMessage = null,
                        errorMessage = null
                    )
                }
                is KociembaSolver.SolveResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isProcessing = false,
                        errorMessage = result.message,
                        statusMessage = null
                    )
                }
            }
        }
    }

    fun loadSavedSolve(cubeState: CubeState, moves: List<CubeMove>, solveTimeMs: Long) {
        _uiState.value = _uiState.value.copy(
            screen = Screen.SOLUTION,
            currentCubeState = cubeState,
            solutionMoves = moves,
            solveTimeMs = solveTimeMs,
            errorMessage = null
        )
    }

    fun saveCurrentSolve(name: String, tags: List<String>) {
        val user = authManager.currentUser ?: return
        val currentSolveMoves = _uiState.value.solutionMoves
        val cube = _uiState.value.currentCubeState
        val solveTime = _uiState.value.solveTimeMs

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSavingSolve = true)
            val res = historyRepository.saveSolve(
                userId = user.uid,
                name = name,
                tags = tags,
                kociembaString = cube.toKociembaString(),
                solutionMoves = currentSolveMoves.joinToString(" ") { it.notation },
                moveCount = currentSolveMoves.size.toLong(),
                solveTimeMs = solveTime
            )
            _uiState.value = _uiState.value.copy(
                isSavingSolve = false,
                saveSuccessMessage = if (res.isSuccess) "Solve saved to your profile!" else null,
                errorMessage = res.exceptionOrNull()?.localizedMessage
            )
        }
    }

    fun signInWithGoogle(activity: Activity) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isProcessing = true)
            val res = authManager.signInWithGoogle(activity)
            _uiState.value = _uiState.value.copy(
                isProcessing = false,
                errorMessage = res.exceptionOrNull()?.localizedMessage
            )
        }
    }

    fun processCapturedPhotos(photos: Map<String, Bitmap>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isProcessing = true,
                statusMessage = "Gemini Vision is parsing 6 cube faces...",
                errorMessage = null
            )

            val parseResult = GeminiVisionParser.parseCubePhotos(photos)

            parseResult.fold(
                onSuccess = { res ->
                    try {
                        val parsedCube = CubeState.fromKociembaString(res.kociembaString)
                        val solveResult = KociembaSolver.solve(parsedCube)

                        when (solveResult) {
                            is KociembaSolver.SolveResult.Success -> {
                                _uiState.value = _uiState.value.copy(
                                    isProcessing = false,
                                    screen = Screen.SOLUTION,
                                    currentCubeState = parsedCube,
                                    solutionMoves = solveResult.moves,
                                    solveTimeMs = solveResult.timeMs,
                                    geminiErrorNotes = res.errorNotes,
                                    statusMessage = null
                                )
                            }
                            is KociembaSolver.SolveResult.Error -> {
                                _uiState.value = _uiState.value.copy(
                                    isProcessing = false,
                                    screen = Screen.MANUAL_EDITOR,
                                    currentCubeState = parsedCube,
                                    errorMessage = "Detected cube parity error: ${solveResult.message}. Please verify stickers in palette editor.",
                                    geminiErrorNotes = res.errorNotes
                                )
                            }
                        }
                    } catch (e: Exception) {
                        _uiState.value = _uiState.value.copy(
                            isProcessing = false,
                            screen = Screen.MANUAL_EDITOR,
                            errorMessage = "Parsing error: ${e.message}. You can adjust stickers in the manual editor."
                        )
                    }
                },
                onFailure = { err ->
                    _uiState.value = _uiState.value.copy(
                        isProcessing = false,
                        screen = Screen.MANUAL_EDITOR,
                        errorMessage = "Gemini Vision analysis failed: ${err.message}. Switched to manual editor."
                    )
                }
            )
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(errorMessage = null)
    }

    fun clearSuccess() {
        _uiState.value = _uiState.value.copy(saveSuccessMessage = null)
    }
}
