package com.example.data.repository

import com.example.data.model.BadgeItem
import com.example.data.model.DailyMission
import com.example.data.model.DiaryEntry
import com.example.data.model.FriendRequest
import com.example.data.model.FriendRequestStatus
import com.example.data.model.InteractiveStory
import com.example.data.model.MedStatus
import com.example.data.model.Medication
import com.example.data.model.PhotoAnalysis
import com.example.data.model.SeniorMilestone
import com.example.data.model.SeniorMilestoneCategory
import com.example.data.model.SeniorPreferences
import com.example.data.model.SleepRecord
import com.example.data.model.StoryChoice
import com.example.data.model.StoryTurn
import com.example.data.model.UserRole
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class GenerationsRepository {


    private val _currentRole = MutableStateFlow(UserRole.SENIOR)
    val currentRole: StateFlow<UserRole> = _currentRole.asStateFlow()

    private val _seniorPreferences = MutableStateFlow(SeniorPreferences())
    val seniorPreferences: StateFlow<SeniorPreferences> = _seniorPreferences.asStateFlow()

    // Medications
    private val _medications = MutableStateFlow(initialMedications())
    val medications: StateFlow<List<Medication>> = _medications.asStateFlow()

    // Diary entries
    private val _diaryEntries = MutableStateFlow(initialDiaryEntries())
    val diaryEntries: StateFlow<List<DiaryEntry>> = _diaryEntries.asStateFlow()

    // Sleep records
    private val _sleepRecords = MutableStateFlow(initialSleepRecords())
    val sleepRecords: StateFlow<List<SleepRecord>> = _sleepRecords.asStateFlow()

    // Active interactive story
    private val _currentStory = MutableStateFlow(initialStory())
    val currentStory: StateFlow<InteractiveStory> = _currentStory.asStateFlow()

    // Friend requests & connections
    private val _friendRequests = MutableStateFlow(initialFriendRequests())
    val friendRequests: StateFlow<List<FriendRequest>> = _friendRequests.asStateFlow()

    // Child profile points & missions
    private val _childPoints = MutableStateFlow(340)
    val childPoints: StateFlow<Int> = _childPoints.asStateFlow()

    private val _childBadges = MutableStateFlow(initialBadges())
    val childBadges: StateFlow<List<BadgeItem>> = _childBadges.asStateFlow()

    // Senior milestones and gentle encouragement
    private val _seniorMilestones = MutableStateFlow(initialSeniorMilestones())
    val seniorMilestones: StateFlow<List<SeniorMilestone>> = _seniorMilestones.asStateFlow()

    private val _dailyMissions = MutableStateFlow(initialMissions())
    val dailyMissions: StateFlow<List<DailyMission>> = _dailyMissions.asStateFlow()

    // Selected / Analyzed Photos
    private val _analyzedPhotos = MutableStateFlow(initialPhotos())
    val analyzedPhotos: StateFlow<List<PhotoAnalysis>> = _analyzedPhotos.asStateFlow()

    // Last undone medication for undo toast
    private var lastToggledMedication: Medication? = null

    private val _currentUser = MutableStateFlow<com.example.data.model.AppUser?>(
        com.example.data.model.AppUser(
            mobileNumber = "9876543210",
            displayName = "Eleanor Vance",
            role = UserRole.SENIOR,
            passcode = "1234",
            patternCode = "0,1,2,5",
            hasFaceRegistered = true
        )
    )
    val currentUser: StateFlow<com.example.data.model.AppUser?> = _currentUser.asStateFlow()

    private val _registeredUsers = MutableStateFlow<List<com.example.data.model.AppUser>>(
        listOf(
            com.example.data.model.AppUser("9876543210", "Eleanor Vance", UserRole.SENIOR, "1234", "0,1,2,5", true),
            com.example.data.model.AppUser("9876543211", "Leo Martinez", UserRole.CHILD, "0000", "0,3,6,7", true),
            com.example.data.model.AppUser("9876543212", "Maria Martinez", UserRole.PARENT, "9999", "2,5,8,7", true)
        )
    )
    val registeredUsers: StateFlow<List<com.example.data.model.AppUser>> = _registeredUsers.asStateFlow()

    fun setRole(role: UserRole) {
        _currentRole.value = role
    }

    fun toggleHighContrast() {
        val cur = _seniorPreferences.value
        _seniorPreferences.value = cur.copy(highContrast = !cur.highContrast)
    }

    fun toggleVoiceMode() {
        val cur = _seniorPreferences.value
        val newVoice = !cur.voiceModeEnabled
        _seniorPreferences.value = cur.copy(
            voiceModeEnabled = newVoice,
            autoReadAloud = newVoice
        )
    }

    fun registerUser(user: com.example.data.model.AppUser) {
        _registeredUsers.value = _registeredUsers.value.filter { it.mobileNumber != user.mobileNumber } + user
        _currentUser.value = user
        _currentRole.value = user.role
    }

    fun loginUser(user: com.example.data.model.AppUser) {
        _currentUser.value = user
        _currentRole.value = user.role
    }

    fun logOff() {
        _currentUser.value = null
    }


    fun markMedicationTaken(medId: String) {
        val timeNow = SimpleDateFormat("h:mm a", Locale.getDefault()).format(Date())
        _medications.value = _medications.value.map { med ->
            if (med.id == medId) {
                lastToggledMedication = med
                med.copy(status = MedStatus.TAKEN, takenAt = timeNow)
            } else med
        }
        // Advance medication milestones
        advanceMilestoneProgress("sm_med_routine", 1)
        advanceMilestoneProgress("sm_med_7day", 1)
        checkDailyTrioHabit()
    }

    fun undoLastMedication(): Boolean {
        val last = lastToggledMedication ?: return false
        _medications.value = _medications.value.map { med ->
            if (med.id == last.id) {
                last.copy(status = MedStatus.PENDING, takenAt = null)
            } else med
        }
        lastToggledMedication = null
        return true
    }

    fun addMedication(name: String, dosage: String, time: String, instructions: String) {
        val newMed = Medication(
            id = "med_${System.currentTimeMillis()}",
            name = name,
            dosage = dosage,
            scheduledTime = time,
            mealInstructions = instructions,
            status = MedStatus.PENDING
        )
        _medications.value = _medications.value + newMed
    }

    fun addDiaryEntry(moodEmoji: String, moodLabel: String, noteText: String, voiceSec: Int) {
        val dateStr = SimpleDateFormat("EEE, MMM d", Locale.getDefault()).format(Date())
        val newEntry = DiaryEntry(
            id = "diary_${System.currentTimeMillis()}",
            date = dateStr,
            moodEmoji = moodEmoji,
            moodLabel = moodLabel,
            noteText = noteText,
            prompt = "What made you smile today?",
            voiceNoteDurationSec = voiceSec,
            isSharedWithBuddy = true
        )
        _diaryEntries.value = listOf(newEntry) + _diaryEntries.value

        // Advance diary milestones
        advanceMilestoneProgress("sm_diary_first", 1)
        advanceMilestoneProgress("sm_diary_reflections", 1)
        if (voiceSec > 0) {
            advanceMilestoneProgress("sm_diary_voice", 1)
        }
        checkDailyTrioHabit()
    }

    fun recordBreathingCompleted() {
        advanceMilestoneProgress("sm_breath_first", 1)
        advanceMilestoneProgress("sm_breath_vagus", 1)
        advanceMilestoneProgress("sm_breath_harbor", 1)
        checkDailyTrioHabit()
    }

    private fun advanceMilestoneProgress(milestoneId: String, delta: Int) {
        val todayStr = SimpleDateFormat("MMM d", Locale.getDefault()).format(Date())
        _seniorMilestones.value = _seniorMilestones.value.map { milestone ->
            if (milestone.id == milestoneId) {
                val newProgress = (milestone.currentProgress + delta).coerceAtMost(milestone.targetProgress)
                val isNowUnlocked = newProgress >= milestone.targetProgress
                milestone.copy(
                    currentProgress = newProgress,
                    isUnlocked = isNowUnlocked,
                    unlockedDate = if (isNowUnlocked && milestone.unlockedDate == null) todayStr else milestone.unlockedDate
                )
            } else milestone
        }
    }

    private fun checkDailyTrioHabit() {
        val medsTakenCount = _medications.value.count { it.status == MedStatus.TAKEN }
        val diaryDone = _diaryEntries.value.isNotEmpty()
        val breathingDone = _seniorMilestones.value.find { it.id == "sm_breath_first" }?.currentProgress ?: 0

        var habitsDone = 0
        if (medsTakenCount >= 2) habitsDone++
        if (diaryDone) habitsDone++
        if (breathingDone >= 1) habitsDone++

        _seniorMilestones.value = _seniorMilestones.value.map { milestone ->
            if (milestone.id == "sm_wellness_trio") {
                val isUnlocked = habitsDone >= milestone.targetProgress
                milestone.copy(
                    currentProgress = habitsDone,
                    isUnlocked = isUnlocked,
                    unlockedDate = if (isUnlocked && milestone.unlockedDate == null) "Today" else milestone.unlockedDate
                )
            } else milestone
        }
    }

    fun unlockSeniorMilestone(id: String) {
        val todayStr = SimpleDateFormat("MMM d", Locale.getDefault()).format(Date())
        _seniorMilestones.value = _seniorMilestones.value.map { milestone ->
            if (milestone.id == id) {
                milestone.copy(
                    isUnlocked = true,
                    currentProgress = milestone.targetProgress,
                    unlockedDate = milestone.unlockedDate ?: todayStr
                )
            } else milestone
        }
    }

    fun addSleepRecord(bedtime: String, wakeTime: String, hours: Float, quality: Int, notes: String) {
        val dayStr = SimpleDateFormat("EEE", Locale.getDefault()).format(Date())
        val dateStr = SimpleDateFormat("MMM d", Locale.getDefault()).format(Date())
        val newRecord = SleepRecord(
            id = "sleep_${System.currentTimeMillis()}",
            dayLabel = dayStr,
            date = dateStr,
            bedtime = bedtime,
            wakeTime = wakeTime,
            durationHours = hours,
            qualityStars = quality,
            notes = notes
        )
        // Keep 7 days
        val current = _sleepRecords.value.toMutableList()
        current.add(newRecord)
        if (current.size > 7) current.removeAt(0)
        _sleepRecords.value = current
    }

    fun advanceStoryWithChoice(choiceText: String, nextTurn: StoryTurn) {
        val cur = _currentStory.value
        val updatedTurns = cur.turns.toMutableList()
        if (cur.currentTurnIndex < updatedTurns.size) {
            val lastTurn = updatedTurns[cur.currentTurnIndex].copy(chosenChoice = choiceText)
            updatedTurns[cur.currentTurnIndex] = lastTurn
        }
        updatedTurns.add(nextTurn)
        _currentStory.value = cur.copy(
            turns = updatedTurns,
            currentTurnIndex = updatedTurns.size - 1
        )
        awardChildPoints(25)
    }

    fun switchStoryTheme(themeTitle: String) {
        val newStory = InteractiveStory(
            id = "story_${System.currentTimeMillis()}",
            title = themeTitle,
            theme = themeTitle,
            buddyName = "Leo (Age 8)",
            turns = listOf(
                StoryTurn(
                    turnNumber = 1,
                    narratorText = "Under a twilight sky dusted with shimmering stars, Eleanor and Leo unlocked the creaky garden gate of Willow Creek. A curious golden trail of stardust wound through the tall grass.",
                    choices = listOf(
                        StoryChoice("c1", "Follow the glowing stardust path"),
                        StoryChoice("c2", "Inspect the grandfather clock in the gazebo"),
                        StoryChoice("c3", "Whisper to the owl perched on the oak")
                    )
                )
            ),
            currentTurnIndex = 0
        )
        _currentStory.value = newStory
    }

    fun approveFriendRequest(requestId: String) {
        _friendRequests.value = _friendRequests.value.map { req ->
            if (req.id == requestId) req.copy(status = FriendRequestStatus.APPROVED, safetyApprovedByParent = true)
            else req
        }
    }

    fun declineFriendRequest(requestId: String) {
        _friendRequests.value = _friendRequests.value.map { req ->
            if (req.id == requestId) req.copy(status = FriendRequestStatus.DECLINED)
            else req
        }
    }

    fun blockUser(requestId: String) {
        _friendRequests.value = _friendRequests.value.map { req ->
            if (req.id == requestId) req.copy(status = FriendRequestStatus.BLOCKED)
            else req
        }
    }

    fun completeMission(missionId: String) {
        _dailyMissions.value = _dailyMissions.value.map { mission ->
            if (mission.id == missionId && !mission.isCompleted) {
                awardChildPoints(mission.pointsReward)
                mission.copy(isCompleted = true)
            } else mission
        }
    }

    fun awardChildPoints(amount: Int) {
        _childPoints.value += amount
    }

    fun addPhotoAnalysis(analysis: PhotoAnalysis) {
        _analyzedPhotos.value = listOf(analysis) + _analyzedPhotos.value
        awardChildPoints(30)
    }

    companion object {
        private fun initialMedications(): List<Medication> = listOf(
            Medication(
                id = "med_1",
                name = "Lisinopril",
                dosage = "10 mg",
                scheduledTime = "8:00 AM",
                mealInstructions = "Take with a glass of water after breakfast",
                status = MedStatus.TAKEN,
                takenAt = "8:15 AM",
                purpose = "Blood pressure & cardiovascular support"
            ),
            Medication(
                id = "med_2",
                name = "Metoprolol Tartrate",
                dosage = "25 mg",
                scheduledTime = "8:00 AM",
                mealInstructions = "Take with morning meal",
                status = MedStatus.TAKEN,
                takenAt = "8:15 AM",
                purpose = "Heart rate rhythm maintenance"
            ),
            Medication(
                id = "med_3",
                name = "Omega-3 Wild Fish Oil",
                dosage = "1,000 mg",
                scheduledTime = "1:00 PM",
                mealInstructions = "Take with lunch for optimal absorption",
                status = MedStatus.OVERDUE,
                purpose = "Joint mobility & cognitive health"
            ),
            Medication(
                id = "med_4",
                name = "Calcium Citrate & Vitamin D3",
                dosage = "500 mg / 400 IU",
                scheduledTime = "8:00 PM",
                mealInstructions = "Take with evening tea or light snack",
                status = MedStatus.PENDING,
                purpose = "Bone density & muscle strength"
            )
        )

        private fun initialDiaryEntries(): List<DiaryEntry> = listOf(
            DiaryEntry(
                id = "diary_1",
                date = "Today, Oct 31",
                moodEmoji = "😊",
                moodLabel = "Joyful & Connected",
                noteText = "Leo showed me his drawing of our secret garden story today! We giggled when he decided the owl should wear reading glasses. My joint stiffness felt much lighter after our talk.",
                prompt = "What made you smile today?",
                voiceNoteDurationSec = 42,
                isSharedWithBuddy = true
            ),
            DiaryEntry(
                id = "diary_2",
                date = "Yesterday, Oct 30",
                moodEmoji = "😌",
                moodLabel = "Peaceful",
                noteText = "Sat on the front porch with a warm cup of chamomile tea. The autumn leaves are a rich golden amber. Remembering autumn harvests with my father.",
                prompt = "A comforting sound or sight today",
                voiceNoteDurationSec = 28,
                isSharedWithBuddy = true
            )
        )

        private fun initialSleepRecords(): List<SleepRecord> = listOf(
            SleepRecord("s1", "Mon", "Oct 26", "10:15 PM", "6:45 AM", 7.5f, 4, "Woke up refreshed after gentle evening tea"),
            SleepRecord("s2", "Tue", "Oct 27", "10:45 PM", "6:15 AM", 6.8f, 3, "A bit restless around 3 AM"),
            SleepRecord("s3", "Wed", "Oct 28", "10:00 PM", "7:00 AM", 8.2f, 5, "Deep restorative sleep throughout the night"),
            SleepRecord("s4", "Thu", "Oct 29", "10:30 PM", "6:30 AM", 7.0f, 4, "Calm night"),
            SleepRecord("s5", "Fri", "Oct 30", "10:15 PM", "7:00 AM", 7.8f, 5, "Felt peaceful after reading story with Leo"),
            SleepRecord("s6", "Sat", "Oct 31", "11:00 PM", "6:30 AM", 6.5f, 3, "Listened to relaxing ocean sounds"),
            SleepRecord("s7", "Sun", "Nov 1", "9:50 PM", "6:50 AM", 8.0f, 5, "Woke up energized ready for morning walk")
        )

        private fun initialStory(): InteractiveStory = InteractiveStory(
            id = "story_1",
            title = "The Time-Traveling Bicycle of Willow Creek",
            theme = "Mystery & Invention",
            buddyName = "Leo (Age 8)",
            turns = listOf(
                StoryTurn(
                    turnNumber = 1,
                    narratorText = "In the attic above the old bicycle shop, Eleanor and Leo uncovered an antique two-seater tandem covered in a dusty velvet drape. When Leo gently tapped the brass handlebar bell, it rang with a melodic chime that caused the floorboards to shimmer in iridescent indigo light!",
                    choices = listOf(
                        StoryChoice("c1", "Pedal forward toward 1965"),
                        StoryChoice("c2", "Check the basket for a map"),
                        StoryChoice("c3", "Ring the chime one more time")
                    ),
                    chosenChoice = "Pedal forward toward 1965"
                ),
                StoryTurn(
                    turnNumber = 2,
                    narratorText = "Together they pressed their feet to the pedals. Whoosh! The attic walls dissolved into a warm summer breeze over a 1960s county fair! Vintage music played from a carousel, and children in retro hats were cheering for a pie-eating contest.",
                    choices = listOf(
                        StoryChoice("c4", "Join the carousel parade"),
                        StoryChoice("c5", "Taste the famous blueberry pie"),
                        StoryChoice("c6", "Look for young Eleanor's childhood house")
                    )
                )
            ),
            currentTurnIndex = 1
        )

        private fun initialFriendRequests(): List<FriendRequest> = listOf(
            FriendRequest(
                id = "req_1",
                seniorName = "Eleanor Vance (Age 73)",
                childName = "Leo Martinez (Age 8)",
                ageSummary = "Intergenerational Connection",
                sharedInterests = listOf("Botanical Gardening", "Fantasy Stories", "Watercolor Painting", "Animal Care"),
                bio = "Retired elementary science teacher who loves identifying wildflowers and making up playful bedtime tales.",
                status = FriendRequestStatus.APPROVED,
                safetyApprovedByParent = true
            ),
            FriendRequest(
                id = "req_2",
                seniorName = "Arthur Campbell (Age 76)",
                childName = "Maya Chen (Age 9)",
                ageSummary = "Shared Storytelling & Puzzles",
                sharedInterests = listOf("Antique Clocks", "Chess & Puzzles", "Space Mysteries"),
                bio = "Former watchmaker and avid reader. Enjoys riddles, history, and building wooden model gliders.",
                status = FriendRequestStatus.PENDING,
                safetyApprovedByParent = false
            )
        )

        private fun initialBadges(): List<BadgeItem> = listOf(
            BadgeItem("b1", "Story Pioneer", "Co-wrote first multi-chapter adventure", "auto_stories", true),
            BadgeItem("b2", "Memory Master", "Won Find the Pairs under 12 moves", "psychology", true),
            BadgeItem("b3", "Kindness Heart", "Sent a warm daily diary note to buddy", "favorite", true),
            BadgeItem("b4", "Master Painter", "Completed a shared canvas coloring", "palette", true),
            BadgeItem("b5", "Botanist Scout", "Analyzed 3 plants in the Photo Studio", "eco", false),
            BadgeItem("b6", "Grandpa's Hero", "Completed 7-day connection streak", "military_tech", false)
        )

        private fun initialMissions(): List<DailyMission> = listOf(
            DailyMission("m1", "Draw a Flower for Grandma Eleanor", "Pick a flower canvas and paint it with vibrant colors", 50, false),
            DailyMission("m2", "Play Find the Pairs Game", "Train your memory skills with buddy tiles", 35, true),
            DailyMission("m3", "Co-Write Chapter 3", "Choose the next twist for the Time-Traveling Bicycle", 40, false),
            DailyMission("m4", "Photo Studio Discovery", "Explore the medicinal secrets of Chamomile", 30, true)
        )

        private fun initialPhotos(): List<PhotoAnalysis> = listOf(
            com.example.data.ai.PhotoKnowledgeBase.getOrGenerateAnalysis("chamomile"),
            com.example.data.ai.PhotoKnowledgeBase.getOrGenerateAnalysis("lavender"),
            com.example.data.ai.PhotoKnowledgeBase.getOrGenerateAnalysis("antique compass")
        )

        private fun initialSeniorMilestones(): List<SeniorMilestone> = listOf(
            SeniorMilestone(
                id = "sm_med_routine",
                title = "Morning Sunshine",
                category = SeniorMilestoneCategory.MEDICATIONS,
                description = "Take morning doses consistently with breakfast",
                iconEmoji = "🌅",
                isUnlocked = true,
                currentProgress = 1,
                targetProgress = 1,
                progressUnit = "days",
                unlockedDate = "Yesterday",
                gentleAffirmation = "Your regular morning routine sets a calm, energizing foundation for the whole day."
            ),
            SeniorMilestone(
                id = "sm_med_7day",
                title = "7-Day Golden Rhythm",
                category = SeniorMilestoneCategory.MEDICATIONS,
                description = "Complete all scheduled doses for 7 days in a row",
                iconEmoji = "✨",
                isUnlocked = false,
                currentProgress = 6,
                targetProgress = 7,
                progressUnit = "days",
                gentleAffirmation = "Consistency is your greatest wellness ally. You are just one day away from this golden milestone!"
            ),
            SeniorMilestone(
                id = "sm_med_hydration",
                title = "Hydration Guardian",
                category = SeniorMilestoneCategory.MEDICATIONS,
                description = "Always take medications with a full glass of water",
                iconEmoji = "💧",
                isUnlocked = true,
                currentProgress = 5,
                targetProgress = 5,
                progressUnit = "times",
                unlockedDate = "3 days ago",
                gentleAffirmation = "Nourishing your body with plenty of water protects your kidneys and aids gentle absorption."
            ),
            SeniorMilestone(
                id = "sm_med_evening",
                title = "Evening Serenity",
                category = SeniorMilestoneCategory.MEDICATIONS,
                description = "Take your evening wellness doses before winding down",
                iconEmoji = "🌙",
                isUnlocked = true,
                currentProgress = 5,
                targetProgress = 5,
                progressUnit = "days",
                unlockedDate = "Oct 29",
                gentleAffirmation = "A thoughtful evening routine prepares your body for peaceful, restorative sleep."
            ),
            SeniorMilestone(
                id = "sm_diary_first",
                title = "Reflective Soul",
                category = SeniorMilestoneCategory.DIARY,
                description = "Record your daily feelings and moments of gratitude",
                iconEmoji = "🌸",
                isUnlocked = true,
                currentProgress = 3,
                targetProgress = 3,
                progressUnit = "entries",
                unlockedDate = "Oct 30",
                gentleAffirmation = "Reflecting on your day nurtures emotional peace and celebrates life's small joys."
            ),
            SeniorMilestone(
                id = "sm_diary_voice",
                title = "Voice of Wisdom",
                category = SeniorMilestoneCategory.DIARY,
                description = "Record 3 spoken voice memoirs shared with young buddy",
                iconEmoji = "🎙️",
                isUnlocked = true,
                currentProgress = 3,
                targetProgress = 3,
                progressUnit = "notes",
                unlockedDate = "Oct 28",
                gentleAffirmation = "The sound of your voice carries comfort, family history, and timeless love to young ears."
            ),
            SeniorMilestone(
                id = "sm_diary_reflections",
                title = "Memoir Keeper",
                category = SeniorMilestoneCategory.DIARY,
                description = "Write 7 thoughtful journal reflections",
                iconEmoji = "📖",
                isUnlocked = false,
                currentProgress = 5,
                targetProgress = 7,
                progressUnit = "entries",
                gentleAffirmation = "Every thought and memory you record is a cherished bridge between generations."
            ),
            SeniorMilestone(
                id = "sm_breath_first",
                title = "Gentle Breath",
                category = SeniorMilestoneCategory.BREATHING,
                description = "Complete a 1-minute guided deep breathing exercise",
                iconEmoji = "🌿",
                isUnlocked = true,
                currentProgress = 1,
                targetProgress = 1,
                progressUnit = "session",
                unlockedDate = "Today",
                gentleAffirmation = "Taking one quiet minute to breathe deeply slows the heart and calms the wandering mind."
            ),
            SeniorMilestone(
                id = "sm_breath_vagus",
                title = "Vagus Harmony",
                category = SeniorMilestoneCategory.BREATHING,
                description = "Complete 5 mindful breathing sessions",
                iconEmoji = "🧘",
                isUnlocked = true,
                currentProgress = 5,
                targetProgress = 5,
                progressUnit = "sessions",
                unlockedDate = "Yesterday",
                gentleAffirmation = "Deep belly breathing activates your vagal response, gently easing tension and soothing the body."
            ),
            SeniorMilestone(
                id = "sm_breath_harbor",
                title = "Sanctuary of Peace",
                category = SeniorMilestoneCategory.BREATHING,
                description = "Practice 10 mindful breathing exercises across the month",
                iconEmoji = "🕊️",
                isUnlocked = false,
                currentProgress = 7,
                targetProgress = 10,
                progressUnit = "sessions",
                gentleAffirmation = "You are cultivating a steady sanctuary of stillness within yourself each day."
            ),
            SeniorMilestone(
                id = "sm_wellness_trio",
                title = "Daily Harmony Trio",
                category = SeniorMilestoneCategory.WELLNESS,
                description = "Complete medicines, diary reflection, and calm breathing in one day",
                iconEmoji = "🌺",
                isUnlocked = true,
                currentProgress = 3,
                targetProgress = 3,
                progressUnit = "habits",
                unlockedDate = "Today",
                gentleAffirmation = "Caring for your body, heart, and breath creates a wonderful day of holistic balance."
            ),
            SeniorMilestone(
                id = "sm_wellness_beacon",
                title = "Inspiring Beacon",
                category = SeniorMilestoneCategory.WELLNESS,
                description = "Inspire your buddy Leo by celebrating 8 wellness milestones",
                iconEmoji = "⭐",
                isUnlocked = true,
                currentProgress = 8,
                targetProgress = 8,
                progressUnit = "milestones",
                unlockedDate = "Today",
                gentleAffirmation = "Leo says: 'Grandma Eleanor, your badges make me so proud of how well you take care of yourself!'"
            )
        )
    }
}

