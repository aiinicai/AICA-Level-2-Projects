package com.example.ui.screens.child

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.FiberManualRecord
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.MandalaDecor
import com.example.util.ComposedMelody
import com.example.util.InstrumentSynthesizer
import com.example.util.InstrumentType
import com.example.util.NoteDefinition

@Composable
fun MusicStudioScreen(
    viewModel: GenerationsAppViewModel,
    onBack: () -> Unit
) {
    var selectedInstrument by remember { mutableStateOf(InstrumentType.PIANO) }
    val isRecording by InstrumentSynthesizer.isRecording.collectAsState()
    val recordingSeconds by InstrumentSynthesizer.recordingSeconds.collectAsState()
    val recordedNotes by InstrumentSynthesizer.recordedNotes.collectAsState()
    val isPlayingBack by InstrumentSynthesizer.isPlayingBack.collectAsState()

    var lastPlayedNoteName by remember { mutableStateOf("") }
    var songSharedNotice by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFFBF8F2))
            .testTag("music_studio_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Top Header with Back button and Artistic Mandala
        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                border = BorderStroke(2.5.dp, Color(0xFF75977E)),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(modifier = Modifier.fillMaxWidth()) {
                    // Decorative Mandala Corner Ornament
                    MandalaDecor(
                        size = 100.dp,
                        tint = Color(0xFFC29B38),
                        alpha = 0.25f,
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(end = 4.dp, top = 4.dp)
                    )

                    Column(modifier = Modifier.padding(18.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            IconButton(
                                onClick = onBack,
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFFE4EDE6))
                            ) {
                                Icon(
                                    imageVector = Icons.Default.ArrowBack,
                                    contentDescription = "Back",
                                    tint = Color(0xFF1B2E21)
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = "Kids Music Studio 🎶",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF18261D)
                                )
                                Text(
                                    text = "Play instruments & compose 1-min melodies",
                                    fontSize = 15.sp,
                                    color = Color(0xFF425447)
                                )
                            }
                        }
                    }
                }
            }
        }

        // Instrument Selection Tabs (Piano, Kalimba, Sitar, Tabla)
        item {
            Column {
                Text(
                    text = "Choose Your Instrument",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF18261D)
                )
                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    InstrumentType.values().forEach { inst ->
                        val isSelected = inst == selectedInstrument
                        Surface(
                            onClick = { selectedInstrument = inst },
                            shape = RoundedCornerShape(16.dp),
                            color = if (isSelected) Color(0xFF4A6B53) else Color(0xFFFFFDF9),
                            border = BorderStroke(
                                2.5.dp,
                                if (isSelected) Color(0xFF344D3B) else Color(0xFFD6CABA)
                            ),
                            shadowElevation = if (isSelected) 3.dp else 1.dp,
                            modifier = Modifier
                                .weight(1f)
                                .height(88.dp)
                                .testTag("instrument_tab_${inst.name.lowercase()}")
                        ) {
                            Column(
                                modifier = Modifier.padding(8.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                Text(text = inst.iconEmoji, fontSize = 28.sp)
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = when (inst) {
                                        InstrumentType.PIANO -> "Piano"
                                        InstrumentType.KALIMBA -> "Kalimba"
                                        InstrumentType.SITAR -> "Sitar"
                                        InstrumentType.TABLA -> "Tabla"
                                    },
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isSelected) Color.White else Color(0xFF18261D)
                                )
                            }
                        }
                    }
                }
            }
        }

        // 1-Minute Song Recorder & Composer Controls
        item {
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                border = BorderStroke(2.5.dp, if (isRecording) Color(0xFFDC2626) else Color(0xFFC29B38)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(CircleShape)
                                    .background(if (isRecording) Color(0xFFFEE2E2) else Color(0xFFFEF7E6)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = if (isRecording) Icons.Default.FiberManualRecord else Icons.Default.MusicNote,
                                    contentDescription = null,
                                    tint = if (isRecording) Color(0xFFDC2626) else Color(0xFFB45309),
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = if (isRecording) "Recording Composition..." else "1-Minute Song Composer",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF18261D)
                                )
                                Text(
                                    text = if (isRecording) "$recordingSeconds / 60 seconds • ${recordedNotes.size} notes" else "${recordedNotes.size} notes recorded",
                                    fontSize = 14.sp,
                                    color = Color(0xFF425447)
                                )
                            }
                        }

                        // Time pill
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = if (isRecording) Color(0xFFDC2626) else Color(0xFFE4EDE6)
                        ) {
                            Text(
                                text = String.format("%02d:%02d / 01:00", recordingSeconds / 60, recordingSeconds % 60),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isRecording) Color.White else Color(0xFF1B2E21),
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    LinearProgressIndicator(
                        progress = { recordingSeconds.toFloat() / 60f },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp)),
                        color = if (isRecording) Color(0xFFDC2626) else Color(0xFF4A6B53),
                        trackColor = Color(0xFFEFECE6)
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    // Recording Action Buttons
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        if (!isRecording) {
                            Button(
                                onClick = { InstrumentSynthesizer.startRecording() },
                                shape = RoundedCornerShape(14.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626)),
                                border = BorderStroke(2.dp, Color(0xFFB91C1C)),
                                modifier = Modifier
                                    .weight(1f)
                                    .defaultMinSize(minHeight = 52.dp)
                                    .testTag("start_record_btn")
                            ) {
                                Icon(Icons.Default.FiberManualRecord, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Record", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            }
                        } else {
                            Button(
                                onClick = { InstrumentSynthesizer.stopRecording() },
                                shape = RoundedCornerShape(14.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1F2937)),
                                border = BorderStroke(2.dp, Color(0xFF111827)),
                                modifier = Modifier
                                    .weight(1f)
                                    .defaultMinSize(minHeight = 52.dp)
                                    .testTag("stop_record_btn")
                            ) {
                                Icon(Icons.Default.Stop, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Stop", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                            }
                        }

                        // Playback Button
                        Button(
                            onClick = {
                                if (isPlayingBack) {
                                    InstrumentSynthesizer.stopPlayback()
                                } else {
                                    InstrumentSynthesizer.startPlayback()
                                }
                            },
                            enabled = recordedNotes.isNotEmpty() && !isRecording,
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4A6B53)),
                            border = BorderStroke(2.dp, Color(0xFF344D3B)),
                            modifier = Modifier
                                .weight(1f)
                                .defaultMinSize(minHeight = 52.dp)
                                .testTag("playback_btn")
                        ) {
                            Icon(
                                imageVector = if (isPlayingBack) Icons.Default.Stop else Icons.Default.PlayArrow,
                                contentDescription = null,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(if (isPlayingBack) "Playing..." else "Play Song", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        }

                        // Reset Button
                        IconButton(
                            onClick = { InstrumentSynthesizer.resetRecording() },
                            enabled = recordedNotes.isNotEmpty() && !isRecording,
                            modifier = Modifier
                                .size(52.dp)
                                .clip(RoundedCornerShape(14.dp))
                                .background(Color(0xFFF2ECE1))
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = "Clear", tint = Color(0xFF18261D))
                        }
                    }

                    // Share song with Grandma Eleanor
                    if (recordedNotes.isNotEmpty() && !isRecording) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(
                            onClick = {
                                viewModel.awardChildPoints(35)
                                songSharedNotice = true
                            },
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC86446)),
                            border = BorderStroke(2.dp, Color(0xFFA54E35)),
                            modifier = Modifier
                                .fillMaxWidth()
                                .defaultMinSize(minHeight = 52.dp)
                                .testTag("gift_song_btn")
                        ) {
                            Icon(Icons.Default.Send, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Gift Melody to Grandma Eleanor (+35★)", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        }
                    }

                    if (songSharedNotice) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "💝 Song shared with Grandma Eleanor! She can now listen to your composition in her profile.",
                            fontSize = 14.sp,
                            color = Color(0xFF15803D),
                            fontWeight = FontWeight.SemiBold,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }
        }

        // Active Instrument Surface & Keys
        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                border = BorderStroke(2.5.dp, Color(0xFF75977E)),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "${selectedInstrument.iconEmoji} ${selectedInstrument.title}",
                                fontSize = 22.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF18261D)
                            )
                            Text(
                                text = selectedInstrument.description,
                                fontSize = 14.sp,
                                color = Color(0xFF425447)
                            )
                        }

                        if (lastPlayedNoteName.isNotEmpty()) {
                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = Color(0xFFE4EDE6),
                                border = BorderStroke(1.5.dp, Color(0xFF75977E))
                            ) {
                                Text(
                                    text = "Played: $lastPlayedNoteName",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF1B2E21),
                                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(18.dp))

                    // Render Instrument-Specific Keys
                    when (selectedInstrument) {
                        InstrumentType.PIANO -> {
                            PianoKeyboard(
                                onNotePlayed = { note ->
                                    lastPlayedNoteName = "${note.name} (${note.subLabel})"
                                    InstrumentSynthesizer.playNote(InstrumentType.PIANO, note)
                                }
                            )
                        }
                        InstrumentType.KALIMBA -> {
                            KalimbaTines(
                                onNotePlayed = { note ->
                                    lastPlayedNoteName = "${note.name} • ${note.subLabel}"
                                    InstrumentSynthesizer.playNote(InstrumentType.KALIMBA, note)
                                }
                            )
                        }
                        InstrumentType.SITAR -> {
                            SitarFrets(
                                onNotePlayed = { note ->
                                    lastPlayedNoteName = "${note.name} (${note.subLabel})"
                                    InstrumentSynthesizer.playNote(InstrumentType.SITAR, note)
                                }
                            )
                        }
                        InstrumentType.TABLA -> {
                            TablaDrums(
                                onNotePlayed = { note ->
                                    lastPlayedNoteName = "${note.name} (${note.subLabel})"
                                    InstrumentSynthesizer.playNote(InstrumentType.TABLA, note)
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

// -------------------------------------------------------------
// INSTRUMENT 1: PIANO KEYBOARD
// -------------------------------------------------------------
@Composable
private fun PianoKeyboard(onNotePlayed: (NoteDefinition) -> Unit) {
    Column {
        Text(
            text = "Tap white keys to play natural octave notes:",
            fontSize = 14.sp,
            color = Color(0xFF425447),
            modifier = Modifier.padding(bottom = 8.dp)
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            InstrumentSynthesizer.pianoNotes.forEach { note ->
                val interactionSource = remember { MutableInteractionSource() }
                val isPressed by interactionSource.collectIsPressedAsState()

                Surface(
                    onClick = { onNotePlayed(note) },
                    interactionSource = interactionSource,
                    shape = RoundedCornerShape(bottomStart = 10.dp, bottomEnd = 10.dp, topStart = 6.dp, topEnd = 6.dp),
                    color = if (isPressed) Color(0xFFE4EDE6) else Color(0xFFFFFDF9),
                    border = BorderStroke(2.dp, Color(0xFF344D3B)),
                    shadowElevation = if (isPressed) 1.dp else 4.dp,
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxSize()
                        .testTag("piano_key_${note.name.lowercase()}")
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(bottom = 12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Bottom
                    ) {
                        Text(
                            text = note.name,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF18261D)
                        )
                        Text(
                            text = note.subLabel,
                            fontSize = 12.sp,
                            color = Color(0xFF425447)
                        )
                    }
                }
            }
        }
    }
}

// -------------------------------------------------------------
// INSTRUMENT 2: KALIMBA TINES
// -------------------------------------------------------------
@Composable
private fun KalimbaTines(onNotePlayed: (NoteDefinition) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Color(0xFF78350F).copy(alpha = 0.08f))
            .padding(14.dp)
    ) {
        Text(
            text = "Resonant thumb tines (numbered African tuning):",
            fontSize = 14.sp,
            color = Color(0xFF425447),
            modifier = Modifier.padding(bottom = 10.dp)
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(200.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.Top
        ) {
            InstrumentSynthesizer.kalimbaNotes.forEachIndexed { index, note ->
                val interactionSource = remember { MutableInteractionSource() }
                val isPressed by interactionSource.collectIsPressedAsState()

                // Kalimba tines have alternating lengths radiating from center
                val tineHeight = when (index) {
                    0, 7 -> 190.dp
                    1, 6 -> 175.dp
                    2, 5 -> 160.dp
                    else -> 145.dp
                }

                Surface(
                    onClick = { onNotePlayed(note) },
                    interactionSource = interactionSource,
                    shape = RoundedCornerShape(bottomStart = 12.dp, bottomEnd = 12.dp),
                    color = if (isPressed) Color(0xFFD4AF37) else Color(0xFFF3ECE0),
                    border = BorderStroke(2.5.dp, Color(0xFFB45309)),
                    shadowElevation = if (isPressed) 1.dp else 4.dp,
                    modifier = Modifier
                        .weight(1f)
                        .height(tineHeight)
                        .testTag("kalimba_tine_${note.name}")
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(bottom = 10.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Bottom
                    ) {
                        Text(
                            text = note.name,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF78350F)
                        )
                        Text(
                            text = note.subLabel,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF92400E)
                        )
                    }
                }
            }
        }
    }
}

// -------------------------------------------------------------
// INSTRUMENT 3: INDIAN SITAR FRETS
// -------------------------------------------------------------
@Composable
private fun SitarFrets(onNotePlayed: (NoteDefinition) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(Color(0xFFFEF7E6))
            .border(BorderStroke(2.dp, Color(0xFFD4AF37)), RoundedCornerShape(20.dp))
            .padding(14.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Indian Classical Swaras (Sa Re Ga Ma Pa Dha Ni Ṡa):",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF78350F)
            )
            Text(
                text = "✨ Jawari Buzz",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFB45309)
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // 2 rows of 4 frets
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                InstrumentSynthesizer.sitarNotes.take(4).forEach { note ->
                    SitarFretButton(note = note, onNotePlayed = onNotePlayed, modifier = Modifier.weight(1f))
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                InstrumentSynthesizer.sitarNotes.drop(4).forEach { note ->
                    SitarFretButton(note = note, onNotePlayed = onNotePlayed, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun SitarFretButton(
    note: NoteDefinition,
    onNotePlayed: (NoteDefinition) -> Unit,
    modifier: Modifier = Modifier
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Surface(
        onClick = { onNotePlayed(note) },
        interactionSource = interactionSource,
        shape = RoundedCornerShape(16.dp),
        color = if (isPressed) Color(0xFFD4AF37) else Color(0xFFFFFDF9),
        border = BorderStroke(2.5.dp, Color(0xFFC86446)),
        shadowElevation = if (isPressed) 1.dp else 3.dp,
        modifier = modifier
            .height(76.dp)
            .testTag("sitar_swara_${note.name.lowercase()}")
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = note.name,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = if (isPressed) Color.White else Color(0xFF78350F)
            )
            Text(
                text = note.subLabel,
                fontSize = 13.sp,
                color = if (isPressed) Color.White.copy(alpha = 0.9f) else Color(0xFF92400E)
            )
        }
    }
}

// -------------------------------------------------------------
// INSTRUMENT 4: TABLA DRUMS (BAYAN & DAYAN)
// -------------------------------------------------------------
@Composable
private fun TablaDrums(onNotePlayed: (NoteDefinition) -> Unit) {
    Column {
        Text(
            text = "Authentic Indian twin drums (Bayan bass & Dayan treble):",
            fontSize = 14.sp,
            color = Color(0xFF425447),
            modifier = Modifier.padding(bottom = 10.dp)
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Bayan (Bass metal drum on left)
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE4EDE6)),
                border = BorderStroke(2.5.dp, Color(0xFF4A6B53)),
                modifier = Modifier.weight(1f)
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Bayan (Bass Drum) 🥁",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF18261D)
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val bayanBols = InstrumentSynthesizer.tablaNotes.filter { it.id in listOf("t_dha", "t_dhin", "t_ge") }
                    bayanBols.forEach { bol ->
                        TablaBolPad(bol = bol, onNotePlayed = onNotePlayed)
                        Spacer(modifier = Modifier.height(6.dp))
                    }
                }
            }

            // Dayan (Treble wooden drum on right)
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF7E6)),
                border = BorderStroke(2.5.dp, Color(0xFFC86446)),
                modifier = Modifier.weight(1f)
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Dayan (Treble Drum) 🪘",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF78350F)
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val dayanBols = InstrumentSynthesizer.tablaNotes.filter { it.id in listOf("t_na", "t_tin", "t_ke") }
                    dayanBols.forEach { bol ->
                        TablaBolPad(bol = bol, onNotePlayed = onNotePlayed)
                        Spacer(modifier = Modifier.height(6.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun TablaBolPad(
    bol: NoteDefinition,
    onNotePlayed: (NoteDefinition) -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val isPressed by interactionSource.collectIsPressedAsState()

    Surface(
        onClick = { onNotePlayed(bol) },
        interactionSource = interactionSource,
        shape = RoundedCornerShape(14.dp),
        color = if (isPressed) Color(0xFF4A6B53) else Color(0xFFFFFDF9),
        border = BorderStroke(2.dp, Color(0xFF344D3B)),
        shadowElevation = if (isPressed) 1.dp else 3.dp,
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .testTag("tabla_bol_${bol.name.lowercase().replace(" ", "_").replace("/", "_")}")
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = bol.name,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = if (isPressed) Color.White else Color(0xFF18261D)
            )
            Text(
                text = bol.subLabel,
                fontSize = 13.sp,
                color = if (isPressed) Color.White.copy(alpha = 0.85f) else Color(0xFF425447)
            )
        }
    }
}
