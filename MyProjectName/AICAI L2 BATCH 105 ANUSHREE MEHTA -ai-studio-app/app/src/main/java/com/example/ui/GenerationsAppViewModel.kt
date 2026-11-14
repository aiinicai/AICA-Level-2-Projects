package com.example.ui

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.BuildConfig
import com.example.data.ai.GeminiService
import com.example.data.model.DailyMission
import com.example.data.model.DiaryEntry
import com.example.data.model.FriendRequest
import com.example.data.model.InteractiveStory
import com.example.data.model.Medication
import com.example.data.model.PhotoAnalysis
import com.example.data.model.SeniorMilestone
import com.example.data.model.SeniorPreferences
import com.example.data.model.SleepRecord
import com.example.data.model.UserRole
import com.example.data.repository.GenerationsRepository
import com.example.util.SpeechManager
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class GenerationsAppViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = GenerationsRepository()
    val speechManager = SpeechManager(application)

    val currentRole: StateFlow<UserRole> = repository.currentRole
    val seniorPreferences: StateFlow<SeniorPreferences> = repository.seniorPreferences
    val medications: StateFlow<List<Medication>> = repository.medications
    val diaryEntries: StateFlow<List<DiaryEntry>> = repository.diaryEntries
    val sleepRecords: StateFlow<List<SleepRecord>> = repository.sleepRecords
    val currentStory: StateFlow<InteractiveStory> = repository.currentStory
    val friendRequests: StateFlow<List<FriendRequest>> = repository.friendRequests
    val childPoints: StateFlow<Int> = repository.childPoints
    val childBadges = repository.childBadges
    val seniorMilestones: StateFlow<List<SeniorMilestone>> = repository.seniorMilestones
    val dailyMissions: StateFlow<List<DailyMission>> = repository.dailyMissions
    val analyzedPhotos: StateFlow<List<PhotoAnalysis>> = repository.analyzedPhotos
    val currentUser = repository.currentUser
    val registeredUsers = repository.registeredUsers

    val isSpeaking: StateFlow<Boolean> = speechManager.isSpeaking

    // Colour palette chosen from the top-bar palette button (null = original per-profile colours)
    private val _palette = MutableStateFlow<com.example.ui.theme.AppPalette?>(com.example.ui.theme.AppPalette.SAGE)
    val palette: StateFlow<com.example.ui.theme.AppPalette?> = _palette.asStateFlow()
    fun setPalette(p: com.example.ui.theme.AppPalette?) { _palette.value = p }

    private val _isGeneratingStory = MutableStateFlow(false)
    val isGeneratingStory: StateFlow<Boolean> = _isGeneratingStory.asStateFlow()

    private val _isAnalyzingPhoto = MutableStateFlow(false)
    val isAnalyzingPhoto: StateFlow<Boolean> = _isAnalyzingPhoto.asStateFlow()

    private val _remindersEnabled = MutableStateFlow(true)
    val remindersEnabled: StateFlow<Boolean> = _remindersEnabled.asStateFlow()

    private val _toastEvent = MutableSharedFlow<String>()
    val toastEvent: SharedFlow<String> = _toastEvent.asSharedFlow()

    private val _confettiEvent = MutableSharedFlow<String>()
    val confettiEvent: SharedFlow<String> = _confettiEvent.asSharedFlow()

    fun toggleReminders(context: Context) {
        val newState = !_remindersEnabled.value
        _remindersEnabled.value = newState
        if (newState) {
            scheduleAllActiveReminders(context)
            viewModelScope.launch {
                _toastEvent.emit("Dose reminders active. Daily alerts scheduled!")
            }
        } else {
            medications.value.forEach { med ->
                com.example.data.reminder.MedicationNotificationManager.cancelMedicationAlarm(context, med.id)
            }
            viewModelScope.launch {
                _toastEvent.emit("Dose reminders paused.")
            }
        }
    }

    fun scheduleAllActiveReminders(context: Context) {
        if (!_remindersEnabled.value) return
        medications.value.forEach { med ->
            com.example.data.reminder.MedicationNotificationManager.scheduleMedicationAlarm(context, med)
        }
    }

    fun scheduleTestReminder(context: Context, medication: Medication) {
        com.example.data.reminder.MedicationNotificationManager.scheduleMedicationAlarm(
            context = context,
            medication = medication,
            delayMillis = 5000L // 5 seconds test alert
        )
        viewModelScope.launch {
            _toastEvent.emit("Test notification scheduled! Will ring in 5 seconds 🔔")
        }
    }

    fun setRole(role: UserRole) {
        repository.setRole(role)
        speechManager.stop()
        viewModelScope.launch {
            _toastEvent.emit("Switched to ${role.name.lowercase().replaceFirstChar { it.uppercase() }} Profile")
        }
    }

    fun toggleHighContrast() {
        repository.toggleHighContrast()
    }

    fun toggleVoiceMode() {
        repository.toggleVoiceMode()
        val enabled = seniorPreferences.value.voiceModeEnabled
        viewModelScope.launch {
            _toastEvent.emit(if (enabled) "Voice mode is ON (Speech enabled)" else "Voice mode is OFF (Muted)")
        }
        if (!enabled) {
            speechManager.stop()
        }
    }

    fun registerUser(user: com.example.data.model.AppUser) {
        repository.registerUser(user)
        viewModelScope.launch {
            _toastEvent.emit("Welcome, ${user.displayName}! Registered with ${user.mobileNumber}")
            _confettiEvent.emit("Account Created! Registered with mobile passcode & security.")
        }
    }

    fun loginUser(user: com.example.data.model.AppUser) {
        repository.loginUser(user)
        viewModelScope.launch {
            _toastEvent.emit("Signed in as ${user.displayName}")
        }
    }

    fun logOff() {
        speechManager.stop()
        repository.logOff()
        viewModelScope.launch {
            _toastEvent.emit("Logged off successfully. Please sign in.")
        }
    }

    fun markMedicationTaken(medId: String) {
        repository.markMedicationTaken(medId)
        viewModelScope.launch {
            _toastEvent.emit("Marked as taken. Undo available.")
        }
    }

    fun undoLastMedication() {
        val success = repository.undoLastMedication()
        if (success) {
            viewModelScope.launch {
                _toastEvent.emit("Medication marked back to pending")
            }
        }
    }

    fun addMedication(name: String, dosage: String, time: String, instructions: String, context: Context? = null) {
        repository.addMedication(name, dosage, time, instructions)
        if (context != null && _remindersEnabled.value) {
            val lastMed = repository.medications.value.lastOrNull()
            if (lastMed != null) {
                com.example.data.reminder.MedicationNotificationManager.scheduleMedicationAlarm(context, lastMed)
            }
        }
        viewModelScope.launch {
            _toastEvent.emit("Medication added & reminder scheduled!")
        }
    }

    fun addDiaryEntry(moodEmoji: String, moodLabel: String, noteText: String, voiceSec: Int) {
        repository.addDiaryEntry(moodEmoji, moodLabel, noteText, voiceSec)
        viewModelScope.launch {
            _toastEvent.emit("Diary entry saved and shared with buddy!")
            _confettiEvent.emit("Great job reflecting on your day! +20 connection points")
        }
    }

    fun addSleepRecord(bedtime: String, wakeTime: String, hours: Float, quality: Int, notes: String) {
        repository.addSleepRecord(bedtime, wakeTime, hours, quality, notes)
        viewModelScope.launch {
            _toastEvent.emit("Sleep logged for today")
        }
    }

    fun speakAloud(text: String) {
        speechManager.speak(text)
    }

    fun stopSpeaking() {
        speechManager.stop()
    }

    fun advanceStoryWithChoice(choiceText: String) {
        val story = currentStory.value
        val turnIdx = story.currentTurnIndex
        val lastTurn = story.turns.getOrNull(turnIdx)
        val prevContext = lastTurn?.narratorText ?: ""

        viewModelScope.launch {
            _isGeneratingStory.value = true
            val nextTurn = GeminiService.generateNextStoryTurn(
                storyTheme = story.theme,
                storyTitle = story.title,
                currentTurn = turnIdx + 1,
                previousContext = prevContext,
                userSelection = choiceText,
                apiKey = BuildConfig.GEMINI_API_KEY
            )
            repository.advanceStoryWithChoice(choiceText, nextTurn)
            _isGeneratingStory.value = false
            _confettiEvent.emit("Story chapter continued! +25 Points")
        }
    }

    fun advanceStoryWithCustomIdea(customIdea: String) {
        advanceStoryWithChoice(customIdea)
    }

    fun changeStoryTheme(theme: String) {
        repository.switchStoryTheme(theme)
        viewModelScope.launch {
            _toastEvent.emit("Started new story: $theme")
        }
    }

    fun analyzeNewPhoto(title: String, customNotes: String) {
        viewModelScope.launch {
            _isAnalyzingPhoto.value = true
            val analysis = GeminiService.analyzePhoto(title, customNotes, BuildConfig.GEMINI_API_KEY)
            repository.addPhotoAnalysis(analysis)
            _isAnalyzingPhoto.value = false
            _confettiEvent.emit("Photo analysis ready! +30 Points")
        }
    }

    fun approveFriendRequest(reqId: String) {
        repository.approveFriendRequest(reqId)
        viewModelScope.launch {
            _toastEvent.emit("Safety Approved: Connection is now active!")
        }
    }

    fun declineFriendRequest(reqId: String) {
        repository.declineFriendRequest(reqId)
        viewModelScope.launch {
            _toastEvent.emit("Request declined.")
        }
    }

    fun blockUser(reqId: String) {
        repository.blockUser(reqId)
        viewModelScope.launch {
            _toastEvent.emit("User blocked and reported to safety moderation.")
        }
    }

    fun completeMission(missionId: String) {
        repository.completeMission(missionId)
        viewModelScope.launch {
            _confettiEvent.emit("Mission Accomplished! Sparkles earned!")
        }
    }

    fun awardChildPoints(amount: Int) {
        repository.awardChildPoints(amount)
        viewModelScope.launch {
            _confettiEvent.emit("Earned +$amount Points! Great teamwork! ⭐")
        }
    }

    fun recordBreathingCompleted() {
        repository.recordBreathingCompleted()
        viewModelScope.launch {
            _toastEvent.emit("Calm breathing completed. Milestone progress updated! 🌿")
            _confettiEvent.emit("Wonderful deep breathing! +15 Points & Milestone progress")
        }
    }

    fun celebrateMilestone(milestone: SeniorMilestone) {
        speakAloud("${milestone.title}. ${milestone.gentleAffirmation}")
        viewModelScope.launch {
            _toastEvent.emit("🌟 Milestone: ${milestone.title}")
            _confettiEvent.emit("Celebrating ${milestone.title}! Wonderful consistency, Eleanor.")
        }
    }

    fun unlockSeniorMilestone(id: String) {
        repository.unlockSeniorMilestone(id)
    }

    override fun onCleared() {
        super.onCleared()
        speechManager.shutdown()
    }
}

