package com.example.cube.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.FormatColorFill
import androidx.compose.material.icons.filled.GridOn
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material.icons.filled.ViewInAr
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.cube.model.CubeColor
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeState

enum class EditorViewMode {
    SINGLE_FACE,
    UNFOLDED_NET
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ManualEditorScreen(
    initialCubeState: CubeState,
    onSolve: (CubeState) -> Unit,
    onBack: () -> Unit
) {
    BackHandler { onBack() }

    var cubeState by remember { mutableStateOf(initialCubeState) }
    var selectedColor by remember { mutableStateOf(CubeColor.WHITE) }
    var activeFace by remember { mutableStateOf(CubeFace.F) }
    var viewMode by remember { mutableStateOf(EditorViewMode.SINGLE_FACE) }
    var rawKociembaInput by remember { mutableStateOf(cubeState.toKociembaString()) }
    var showRawInput by remember { mutableStateOf(false) }

    val counts = cubeState.validateColorCounts()
    val isDistributionValid = cubeState.isColorDistributionValid()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "Manual Cube Palette",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = if (isDistributionValid) "Ready to solve (54 stickers)" else "Customize sticker colors",
                            style = MaterialTheme.typography.bodySmall,
                            color = if (isDistributionValid) Color(0xFF10B981) else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack, modifier = Modifier.testTag("editor_back_button")) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                },
                actions = {
                    IconButton(
                        onClick = {
                            cubeState = CubeState.solved()
                            rawKociembaInput = cubeState.toKociembaString()
                        },
                        modifier = Modifier.testTag("reset_solved_button")
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Reset to Solved"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // View Mode Switcher
            SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
                SegmentedButton(
                    selected = viewMode == EditorViewMode.SINGLE_FACE,
                    onClick = { viewMode = EditorViewMode.SINGLE_FACE },
                    shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
                ) {
                    Icon(imageVector = Icons.Default.GridOn, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Focused 3x3 Face", fontSize = 12.sp)
                }
                SegmentedButton(
                    selected = viewMode == EditorViewMode.UNFOLDED_NET,
                    onClick = { viewMode = EditorViewMode.UNFOLDED_NET },
                    shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
                ) {
                    Icon(imageVector = Icons.Default.ViewInAr, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("All Faces Net", fontSize = 12.sp)
                }
            }

            // PRIMARY INTERACTIVE AREA
            if (viewMode == EditorViewMode.SINGLE_FACE) {
                // Focused Single Face Editor (Large touch targets, zero clipping!)
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f))
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        // Face Selector Tabs
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            val faces = listOf(CubeFace.U, CubeFace.L, CubeFace.F, CubeFace.R, CubeFace.B, CubeFace.D)
                            faces.forEach { face ->
                                val isSelected = activeFace == face
                                val centerColor = cubeState.getFaceStickers(face)[4]

                                Surface(
                                    onClick = { activeFace = face },
                                    shape = RoundedCornerShape(10.dp),
                                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
                                    border = androidx.compose.foundation.BorderStroke(
                                        width = if (isSelected) 2.dp else 1.dp,
                                        color = if (isSelected) MaterialTheme.colorScheme.primary else Color(0x33000000)
                                    ),
                                    modifier = Modifier.testTag("face_tab_${face.name}")
                                ) {
                                    Row(
                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(12.dp)
                                                .clip(CircleShape)
                                                .background(centerColor.composeColor)
                                                .border(0.5.dp, Color(0x55000000), CircleShape)
                                        )
                                        Text(
                                            text = "${face.name}: ${face.displayName.substringBefore(" ")}",
                                            style = MaterialTheme.typography.labelSmall,
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                            color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurface
                                        )
                                    }
                                }
                            }
                        }

                        // Active Face Info & Quick Actions
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "${activeFace.displayName} Face",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "Tap any tile to apply ${selectedColor.displayName}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            // Fill Face button
                            OutlinedButton(
                                onClick = {
                                    var state = cubeState
                                    for (i in 0..8) {
                                        state = state.withSticker(activeFace, i, selectedColor)
                                    }
                                    cubeState = state
                                    rawKociembaInput = cubeState.toKociembaString()
                                },
                                contentPadding = ButtonDefaults.TextButtonContentPadding
                            ) {
                                Icon(Icons.Default.FormatColorFill, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("Fill Face", fontSize = 11.sp)
                            }
                        }

                        // Large 3x3 Grid (Stickers are large and easy to tap)
                        val currentFaceStickers = cubeState.getFaceStickers(activeFace)
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(6.dp),
                            modifier = Modifier.padding(vertical = 4.dp)
                        ) {
                            for (row in 0..2) {
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    for (col in 0..2) {
                                        val idx = row * 3 + col
                                        val stickerColor = currentFaceStickers[idx]
                                        val isCenter = idx == 4

                                        Box(
                                            modifier = Modifier
                                                .size(68.dp)
                                                .clip(RoundedCornerShape(10.dp))
                                                .background(stickerColor.composeColor)
                                                .border(
                                                    width = 2.dp,
                                                    color = if (isCenter) Color(0xFFFBBF24) else Color(0x33000000),
                                                    shape = RoundedCornerShape(10.dp)
                                                )
                                                .clickable {
                                                    cubeState = cubeState.withSticker(activeFace, idx, selectedColor)
                                                    rawKociembaInput = cubeState.toKociembaString()
                                                }
                                                .testTag("sticker_focus_${activeFace.name}_$idx"),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            if (isCenter) {
                                                Column(
                                                    horizontalAlignment = Alignment.CenterHorizontally
                                                ) {
                                                    Icon(
                                                        imageVector = Icons.Default.Lock,
                                                        contentDescription = null,
                                                        tint = stickerColor.contrastTextColor.copy(alpha = 0.8f),
                                                        modifier = Modifier.size(14.dp)
                                                    )
                                                    Text(
                                                        text = "Center ${activeFace.name}",
                                                        style = MaterialTheme.typography.labelSmall,
                                                        fontWeight = FontWeight.Bold,
                                                        fontSize = 9.sp,
                                                        color = stickerColor.contrastTextColor.copy(alpha = 0.8f)
                                                    )
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Prev / Next Face navigation buttons
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            val facesList = listOf(CubeFace.U, CubeFace.L, CubeFace.F, CubeFace.R, CubeFace.B, CubeFace.D)
                            val currentIdx = facesList.indexOf(activeFace)

                            FilledTonalButton(
                                onClick = {
                                    val nextIdx = (currentIdx - 1 + facesList.size) % facesList.size
                                    activeFace = facesList[nextIdx]
                                }
                            ) {
                                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("Prev Face", fontSize = 12.sp)
                            }

                            Text(
                                text = "${currentIdx + 1}/6: ${activeFace.name}",
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )

                            FilledTonalButton(
                                onClick = {
                                    val nextIdx = (currentIdx + 1) % facesList.size
                                    activeFace = facesList[nextIdx]
                                }
                            ) {
                                Text("Next Face", fontSize = 12.sp)
                                Spacer(Modifier.width(4.dp))
                                Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(14.dp))
                            }
                        }
                    }
                }
            } else {
                // Unfolded 2D Net View (Responsive, adapted to screen width)
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f))
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "Tap any sticker in the unfolded net to paint with active color",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.Center
                        )
                        Spacer(Modifier.height(8.dp))
                        CubeNetView(
                            cubeState = cubeState,
                            selectedFace = activeFace,
                            onStickerClick = { face, idx ->
                                activeFace = face
                                cubeState = cubeState.withSticker(face, idx, selectedColor)
                                rawKociembaInput = cubeState.toKociembaString()
                            }
                        )
                    }
                }
            }

            // COLOR PALETTE (Paint Brush Selector)
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Paint Brush Color",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Active: ${selectedColor.displayName}",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    Spacer(Modifier.height(10.dp))

                    // 6 Color Chips with Live Parity Count directly on each
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        CubeColor.entries.forEach { color ->
                            val isSelected = selectedColor == color
                            val count = counts[color] ?: 0
                            val isColorBalanced = count == 9

                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(48.dp)
                                        .clip(CircleShape)
                                        .background(color.composeColor)
                                        .border(
                                            width = if (isSelected) 3.5.dp else 1.dp,
                                            color = if (isSelected) MaterialTheme.colorScheme.primary else Color(0x33000000),
                                            shape = CircleShape
                                        )
                                        .clickable { selectedColor = color }
                                        .testTag("palette_${color.name}"),
                                    contentAlignment = Alignment.Center
                                ) {
                                    if (isSelected) {
                                        Icon(
                                            imageVector = Icons.Default.Check,
                                            contentDescription = "Selected color",
                                            tint = color.contrastTextColor,
                                            modifier = Modifier.size(24.dp)
                                        )
                                    }
                                }

                                Text(
                                    text = color.displayName,
                                    style = MaterialTheme.typography.labelSmall,
                                    fontSize = 11.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                )

                                // Live Count Badge (9/9)
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(4.dp))
                                        .background(if (isColorBalanced) Color(0x2210B981) else Color(0x22EF4444))
                                        .padding(horizontal = 4.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = "$count/9",
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 10.sp,
                                        color = if (isColorBalanced) Color(0xFF10B981) else Color(0xFFEF4444)
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // PARITY & AUTO-BALANCE CARD
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = if (isDistributionValid) Color(0x1F10B981) else Color(0x1FEF4444)
                ),
                shape = RoundedCornerShape(14.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(
                            imageVector = if (isDistributionValid) Icons.Default.CheckCircle else Icons.Default.Warning,
                            contentDescription = null,
                            tint = if (isDistributionValid) Color(0xFF10B981) else Color(0xFFEF4444),
                            modifier = Modifier.size(22.dp)
                        )
                        Column {
                            Text(
                                text = if (isDistributionValid) "Valid Cube Parity" else "Color Count Mismatch",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = if (isDistributionValid) Color(0xFF10B981) else Color(0xFFEF4444)
                            )
                            Text(
                                text = if (isDistributionValid) "All 54 stickers balanced (9 of each color)" else "Each color must appear exactly 9 times across the cube.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    if (!isDistributionValid) {
                        FilledTonalButton(
                            onClick = {
                                // Auto-balance sticker distribution to exactly 9 of each color
                                val balanced = autoBalanceStickers(cubeState)
                                cubeState = balanced
                                rawKociembaInput = balanced.toKociembaString()
                            },
                            contentPadding = ButtonDefaults.TextButtonContentPadding,
                            modifier = Modifier.testTag("auto_balance_button")
                        ) {
                            Icon(Icons.Default.Build, contentDescription = null, modifier = Modifier.size(14.dp))
                            Spacer(Modifier.width(4.dp))
                            Text("Auto-Fix", fontSize = 11.sp)
                        }
                    }
                }
            }

            // PRESET SCRAMBLES & TEST CASES
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "Preset Scrambles & Test Cases",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    SuggestionChip(
                        onClick = {
                            val (state, _) = CubeState.randomScramble()
                            cubeState = state
                            rawKociembaInput = cubeState.toKociembaString()
                        },
                        label = { Text("Random Scramble") },
                        icon = { Icon(Icons.Default.Shuffle, contentDescription = null, Modifier.size(16.dp)) },
                        modifier = Modifier.testTag("preset_random")
                    )
                    SuggestionChip(
                        onClick = {
                            cubeState = CubeState.easyScramble()
                            rawKociembaInput = cubeState.toKociembaString()
                        },
                        label = { Text("Easy 7-Move") },
                        modifier = Modifier.testTag("preset_easy")
                    )
                    SuggestionChip(
                        onClick = {
                            cubeState = CubeState.checkerboard()
                            rawKociembaInput = cubeState.toKociembaString()
                        },
                        label = { Text("Checkerboard") }
                    )
                }
            }

            // ADVANCED RAW KOCIEMBA STRING
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "54-Char Facelet String",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                FilledTonalButton(
                    onClick = { showRawInput = !showRawInput },
                    contentPadding = ButtonDefaults.TextButtonContentPadding
                ) {
                    Text(if (showRawInput) "Hide" else "Edit Raw String", fontSize = 11.sp)
                }
            }

            AnimatedVisibility(visible = showRawInput) {
                OutlinedTextField(
                    value = rawKociembaInput,
                    onValueChange = {
                        rawKociembaInput = it
                        if (it.length == 54) {
                            try {
                                cubeState = CubeState.fromKociembaString(it)
                            } catch (_: Exception) {}
                        }
                    },
                    label = { Text("54 characters (U R F D L B)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    textStyle = MaterialTheme.typography.bodySmall
                )
            }

            Spacer(Modifier.height(4.dp))

            // PRIMARY SOLVE BUTTON
            Button(
                onClick = { onSolve(cubeState) },
                enabled = isDistributionValid,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(54.dp)
                    .testTag("solve_cube_button"),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Icon(imageVector = Icons.Default.AutoFixHigh, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (isDistributionValid) "Solve Cube (Kociemba Engine)" else "Fix Color Counts (9 each) to Solve",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

/**
 * Auto-balances sticker colors to guarantee exactly 9 of each color.
 * Keeps center stickers intact.
 */
private fun autoBalanceStickers(cubeState: CubeState): CubeState {
    val facelets = cubeState.facelets.toMutableList()
    val counts = mutableMapOf<CubeColor, Int>()
    CubeColor.entries.forEach { counts[it] = 0 }
    facelets.forEach { counts[it] = (counts[it] ?: 0) + 1 }

    val needed = mutableListOf<CubeColor>()
    CubeColor.entries.forEach { c ->
        val deficit = 9 - (counts[c] ?: 0)
        repeat(maxOf(0, deficit)) { needed.add(c) }
    }

    if (needed.isEmpty()) return cubeState

    // Replace non-center surplus stickers with needed colors
    val centerIndices = setOf(4, 13, 22, 31, 40, 49)
    for (i in facelets.indices) {
        if (i in centerIndices) continue
        val current = facelets[i]
        if ((counts[current] ?: 0) > 9 && needed.isNotEmpty()) {
            val replacement = needed.removeAt(0)
            facelets[i] = replacement
            counts[current] = (counts[current] ?: 0) - 1
            counts[replacement] = (counts[replacement] ?: 0) + 1
        }
    }

    return CubeState(facelets)
}
