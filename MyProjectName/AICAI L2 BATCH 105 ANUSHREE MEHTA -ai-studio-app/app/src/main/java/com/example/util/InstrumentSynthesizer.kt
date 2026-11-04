package com.example.util

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin

enum class InstrumentType(val title: String, val iconEmoji: String, val description: String) {
    PIANO("Grand Piano", "🎹", "Rich acoustic keys with warm harmonics"),
    KALIMBA("Kalimba", "🎶", "African thumb piano with crystal bell chimes"),
    SITAR("Indian Sitar", "🪕", "Classical resonant strings with jawari buzz"),
    TABLA("Tabla Drums", "🥁", "Bayan & Dayan twin drums with authentic bols")
}

data class NoteDefinition(
    val id: String,
    val name: String,
    val subLabel: String,
    val frequency: Float,
    val isBlackKey: Boolean = false
)

data class RecordedNote(
    val instrument: InstrumentType,
    val noteId: String,
    val noteName: String,
    val timestampMs: Long
)

data class ComposedMelody(
    val id: String,
    val title: String,
    val instrument: InstrumentType,
    val durationSeconds: Int,
    val notes: List<RecordedNote>,
    val createdDate: String = "Today"
)

object InstrumentSynthesizer {

    private const val SAMPLE_RATE = 22050
    private val scope = CoroutineScope(Dispatchers.Default)

    // Recording State
    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()

    private val _recordingSeconds = MutableStateFlow(0)
    val recordingSeconds: StateFlow<Int> = _recordingSeconds.asStateFlow()

    private val _recordedNotes = MutableStateFlow<List<RecordedNote>>(emptyList())
    val recordedNotes: StateFlow<List<RecordedNote>> = _recordedNotes.asStateFlow()

    private val _isPlayingBack = MutableStateFlow(false)
    val isPlayingBack: StateFlow<Boolean> = _isPlayingBack.asStateFlow()

    private var recordingStartTime = 0L
    private var recordingTimerJob: Job? = null
    private var playbackJob: Job? = null

    // Instrument note scales
    val pianoNotes = listOf(
        NoteDefinition("p_c4", "C4", "Do", 261.63f),
        NoteDefinition("p_d4", "D4", "Re", 293.66f),
        NoteDefinition("p_e4", "E4", "Mi", 329.63f),
        NoteDefinition("p_f4", "F4", "Fa", 349.23f),
        NoteDefinition("p_g4", "G4", "Sol", 392.00f),
        NoteDefinition("p_a4", "A4", "La", 440.00f),
        NoteDefinition("p_b4", "B4", "Ti", 493.88f),
        NoteDefinition("p_c5", "C5", "Do'", 523.25f)
    )

    val kalimbaNotes = listOf(
        NoteDefinition("k_c4", "1", "C4", 261.63f),
        NoteDefinition("k_d4", "2", "D4", 293.66f),
        NoteDefinition("k_e4", "3", "E4", 329.63f),
        NoteDefinition("k_f4", "4", "F4", 349.23f),
        NoteDefinition("k_g4", "5", "G4", 392.00f),
        NoteDefinition("k_a4", "6", "A4", 440.00f),
        NoteDefinition("k_b4", "7", "B4", 493.88f),
        NoteDefinition("k_c5", "i", "C5", 523.25f)
    )

    val sitarNotes = listOf(
        NoteDefinition("s_sa", "Sa", "C4", 261.63f),
        NoteDefinition("s_re", "Re", "D4", 293.66f),
        NoteDefinition("s_ga", "Ga", "E4", 329.63f),
        NoteDefinition("s_ma", "Ma", "F4", 349.23f),
        NoteDefinition("s_pa", "Pa", "G4", 392.00f),
        NoteDefinition("s_dha", "Dha", "A4", 440.00f),
        NoteDefinition("s_ni", "Ni", "B4", 493.88f),
        NoteDefinition("s_sa2", "Ṡa", "C5", 523.25f)
    )

    val tablaNotes = listOf(
        NoteDefinition("t_dha", "Dha", "Bass + Rim", 110.0f),
        NoteDefinition("t_dhin", "Dhin", "Resonant Ring", 130.81f),
        NoteDefinition("t_ge", "Ge", "Open Bayan", 82.41f),
        NoteDefinition("t_na", "Na / Ta", "Sharp Dayan", 349.23f),
        NoteDefinition("t_tin", "Tin", "Open High", 293.66f),
        NoteDefinition("t_ke", "Ke / Kat", "Muted Slap", 200.0f)
    )

    /**
     * Plays instrument note immediately using real-time audio synthesis.
     */
    fun playNote(instrument: InstrumentType, note: NoteDefinition) {
        scope.launch {
            synthesizeAndPlay(instrument, note)
        }

        // Record if active
        if (_isRecording.value) {
            val offset = System.currentTimeMillis() - recordingStartTime
            val newNote = RecordedNote(
                instrument = instrument,
                noteId = note.id,
                noteName = note.name,
                timestampMs = offset
            )
            _recordedNotes.value = _recordedNotes.value + newNote
        }
    }

    private fun synthesizeAndPlay(instrument: InstrumentType, note: NoteDefinition) {
        val durationMs = when (instrument) {
            InstrumentType.PIANO -> 800
            InstrumentType.KALIMBA -> 1200
            InstrumentType.SITAR -> 1100
            InstrumentType.TABLA -> if (note.id == "t_ke") 200 else 600
        }

        val numSamples = (durationMs * SAMPLE_RATE) / 1000
        val buffer = ShortArray(numSamples)
        val freq = note.frequency

        for (i in 0 until numSamples) {
            val t = i.toDouble() / SAMPLE_RATE
            val sampleVal: Double = when (instrument) {
                InstrumentType.PIANO -> {
                    val envelope = exp(-3.2 * t)
                    val s1 = sin(2.0 * PI * freq * t)
                    val s2 = 0.5 * sin(2.0 * PI * (freq * 2) * t)
                    val s3 = 0.25 * sin(2.0 * PI * (freq * 3) * t)
                    (s1 + s2 + s3) * envelope * 0.7
                }
                InstrumentType.KALIMBA -> {
                    // Kalimba chime: fundamental + bright inharmonic bell tine
                    val envelope = exp(-2.5 * t)
                    val s1 = sin(2.0 * PI * freq * t)
                    val s2 = 0.4 * sin(2.0 * PI * (freq * 2.756) * t)
                    (s1 + s2) * envelope * 0.8
                }
                InstrumentType.SITAR -> {
                    // Sitar: slight frequency modulation / bend + jawari buzzing overtone
                    val bendFreq = freq * (1.0 + 0.015 * sin(2.0 * PI * 6.0 * t))
                    val envelope = exp(-2.8 * t)
                    val s1 = sin(2.0 * PI * bendFreq * t)
                    val s2 = 0.6 * sin(2.0 * PI * (bendFreq * 2) * t)
                    val s3 = 0.4 * sin(2.0 * PI * (bendFreq * 3) * t)
                    val s4 = 0.3 * sin(2.0 * PI * (bendFreq * 4.2) * t)
                    (s1 + s2 + s3 + s4) * envelope * 0.65
                }
                InstrumentType.TABLA -> {
                    when (note.id) {
                        "t_dha" -> {
                            // Bayan pitch drop (bass boom) + Dayan rim
                            val pitchDrop = 110.0 * exp(-7.0 * t) + 65.0
                            val bass = sin(2.0 * PI * pitchDrop * t) * exp(-4.0 * t)
                            val rim = sin(2.0 * PI * 340.0 * t) * exp(-12.0 * t) * 0.5
                            (bass + rim) * 0.85
                        }
                        "t_dhin" -> {
                            val pitchDrop = 130.0 * exp(-5.0 * t) + 75.0
                            val bass = sin(2.0 * PI * pitchDrop * t) * exp(-3.5 * t)
                            bass * 0.9
                        }
                        "t_ge" -> {
                            val pitchDrop = 90.0 * exp(-6.0 * t) + 55.0
                            sin(2.0 * PI * pitchDrop * t) * exp(-3.0 * t) * 0.85
                        }
                        "t_na" -> {
                            // Dayan sharp high metallic ring
                            sin(2.0 * PI * 350.0 * t) * exp(-10.0 * t) * 0.8
                        }
                        "t_tin" -> {
                            sin(2.0 * PI * 294.0 * t) * exp(-8.0 * t) * 0.75
                        }
                        else -> {
                            // "t_ke" muted slap
                            (sin(2.0 * PI * 180.0 * t) + (Math.random() - 0.5) * 0.4) * exp(-20.0 * t) * 0.7
                        }
                    }
                }
            }
            buffer[i] = (sampleVal.coerceIn(-1.0, 1.0) * Short.MAX_VALUE).toInt().toShort()
        }

        try {
            val audioTrack = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(SAMPLE_RATE)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setBufferSizeInBytes(buffer.size * 2)
                .setTransferMode(AudioTrack.MODE_STATIC)
                .build()

            audioTrack.write(buffer, 0, buffer.size)
            audioTrack.play()
            // Clean up after playing
            scope.launch {
                delay(durationMs.toLong() + 100)
                try {
                    audioTrack.stop()
                    audioTrack.release()
                } catch (_: Exception) {}
            }
        } catch (_: Exception) {
            // AudioTrack fallback
        }
    }

    fun startRecording() {
        stopPlayback()
        _isRecording.value = true
        _recordingSeconds.value = 0
        _recordedNotes.value = emptyList()
        recordingStartTime = System.currentTimeMillis()

        recordingTimerJob?.cancel()
        recordingTimerJob = scope.launch {
            while (_isRecording.value && _recordingSeconds.value < 60) {
                delay(1000)
                _recordingSeconds.value += 1
                if (_recordingSeconds.value >= 60) {
                    stopRecording()
                }
            }
        }
    }

    fun stopRecording(): List<RecordedNote> {
        _isRecording.value = false
        recordingTimerJob?.cancel()
        return _recordedNotes.value
    }

    fun resetRecording() {
        stopPlayback()
        _isRecording.value = false
        _recordingSeconds.value = 0
        _recordedNotes.value = emptyList()
        recordingTimerJob?.cancel()
    }

    fun startPlayback(notesToPlay: List<RecordedNote> = _recordedNotes.value) {
        if (notesToPlay.isEmpty()) return
        stopPlayback()
        _isPlayingBack.value = true

        playbackJob = scope.launch {
            val startPlayTime = System.currentTimeMillis()
            var noteIndex = 0

            while (_isPlayingBack.value && noteIndex < notesToPlay.size) {
                val currentOffset = System.currentTimeMillis() - startPlayTime
                val targetNote = notesToPlay[noteIndex]

                if (currentOffset >= targetNote.timestampMs) {
                    // Find note definition
                    val noteDef = findNoteDef(targetNote.instrument, targetNote.noteId)
                    if (noteDef != null) {
                        synthesizeAndPlay(targetNote.instrument, noteDef)
                    }
                    noteIndex++
                }
                delay(15)
            }
            _isPlayingBack.value = false
        }
    }

    fun stopPlayback() {
        _isPlayingBack.value = false
        playbackJob?.cancel()
    }

    private fun findNoteDef(instrument: InstrumentType, noteId: String): NoteDefinition? {
        val list = when (instrument) {
            InstrumentType.PIANO -> pianoNotes
            InstrumentType.KALIMBA -> kalimbaNotes
            InstrumentType.SITAR -> sitarNotes
            InstrumentType.TABLA -> tablaNotes
        }
        return list.find { it.id == noteId }
    }
}
