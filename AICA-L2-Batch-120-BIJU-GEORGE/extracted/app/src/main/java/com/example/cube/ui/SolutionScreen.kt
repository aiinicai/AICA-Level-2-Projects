package com.example.cube.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SkipNext
import androidx.compose.material.icons.filled.SkipPrevious
import androidx.compose.material.icons.filled.ViewInAr
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.cube.model.CubeMove
import com.example.cube.model.CubeState
import com.google.firebase.auth.FirebaseUser
import kotlinx.coroutines.delay

enum class GuideViewMode {
    VIEW_3D,
    TURN_DIAGRAM_2D,
    UNFOLDED_NET_2D
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SolutionScreen(
    initialCubeState: CubeState,
    solutionMoves: List<CubeMove>,
    solveTimeMs: Long,
    currentUser: FirebaseUser? = null,
    onSaveSolve: ((name: String, tags: List<String>) -> Unit)? = null,
    onSignInRequested: (() -> Unit)? = null,
    onOpenNotationGuide: (() -> Unit)? = null,
    onBack: () -> Unit
) {
    BackHandler { onBack() }

    // Precalculate cube state at every step
    val statesAtSteps = remember(initialCubeState, solutionMoves) {
        val list = mutableListOf<CubeState>()
        var current = initialCubeState
        list.add(current)
        for (move in solutionMoves) {
            current = current.applyMove(move)
            list.add(current)
        }
        list
    }

    var currentStepIndex by remember { mutableIntStateOf(0) }
    var isAutoPlaying by remember { mutableStateOf(false) }
    var playSpeedMs by remember { mutableStateOf(1000L) }
    var viewMode by remember { mutableStateOf(GuideViewMode.VIEW_3D) }
    var showSaveDialog by remember { mutableStateOf(false) }
    var isSolveSaved by remember { mutableStateOf(false) }

    val listState = rememberLazyListState()

    // Auto play loop
    LaunchedEffect(isAutoPlaying, currentStepIndex) {
        if (isAutoPlaying) {
            if (currentStepIndex < solutionMoves.size) {
                delay(playSpeedMs)
                currentStepIndex++
                listState.animateScrollToItem(currentStepIndex)
            } else {
                isAutoPlaying = false
            }
        }
    }

    // Keep active move chip in view
    LaunchedEffect(currentStepIndex) {
        if (currentStepIndex in solutionMoves.indices) {
            listState.animateScrollToItem(currentStepIndex)
        }
    }

    val isFinished = currentStepIndex >= solutionMoves.size
    val currentCubeState = if (isFinished) {
        if (statesAtSteps.last().isSolved()) statesAtSteps.last() else CubeState.solved()
    } else {
        statesAtSteps.getOrElse(currentStepIndex) { statesAtSteps.last() }
    }
    val currentMove = if (currentStepIndex in solutionMoves.indices) solutionMoves[currentStepIndex] else null

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "Step-by-Step Guide",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "${solutionMoves.size} moves optimal solve (${solveTimeMs}ms)",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack, modifier = Modifier.testTag("solution_back_button")) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                },
                actions = {
                    // Notation Guide button
                    if (onOpenNotationGuide != null) {
                        IconButton(onClick = onOpenNotationGuide) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.MenuBook,
                                contentDescription = "Notation Guide",
                                tint = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }

                    // Save to Profile button
                    IconButton(
                        onClick = { showSaveDialog = true },
                        modifier = Modifier.testTag("save_solve_icon_button")
                    ) {
                        Icon(
                            imageVector = if (isSolveSaved) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                            contentDescription = "Save to Profile",
                            tint = if (isSolveSaved) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
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
                .padding(horizontal = 16.dp, vertical = 6.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Top: Progress Bar & Mode Selector Row
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = if (isFinished) "Cube Solved!" else if (currentStepIndex == 0) "Step 1 of ${solutionMoves.size} (Initial State)" else "Step ${currentStepIndex + 1} of ${solutionMoves.size}",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                            color = if (isFinished) Color(0xFF10B981) else MaterialTheme.colorScheme.primary
                        )
                        Text(
                            text = if (isFinished) "All moves applied • Cube is fully solved" else "Follow moves or tap Play to solve",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 10.sp
                        )
                    }

                    // View Mode Selector Segmented Buttons
                    SingleChoiceSegmentedButtonRow {
                        SegmentedButton(
                            selected = viewMode == GuideViewMode.VIEW_3D,
                            onClick = { viewMode = GuideViewMode.VIEW_3D },
                            shape = SegmentedButtonDefaults.itemShape(index = 0, count = 3)
                        ) {
                            Text("3D", fontSize = 11.sp)
                        }
                        SegmentedButton(
                            selected = viewMode == GuideViewMode.TURN_DIAGRAM_2D,
                            onClick = { viewMode = GuideViewMode.TURN_DIAGRAM_2D },
                            shape = SegmentedButtonDefaults.itemShape(index = 1, count = 3)
                        ) {
                            Text("Turn Diagram", fontSize = 11.sp)
                        }
                        SegmentedButton(
                            selected = viewMode == GuideViewMode.UNFOLDED_NET_2D,
                            onClick = { viewMode = GuideViewMode.UNFOLDED_NET_2D },
                            shape = SegmentedButtonDefaults.itemShape(index = 2, count = 3)
                        ) {
                            Text("Net", fontSize = 11.sp)
                        }
                    }
                }

                LinearProgressIndicator(
                    progress = { currentStepIndex.toFloat() / maxOf(1, solutionMoves.size) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(5.dp)
                        .clip(RoundedCornerShape(3.dp))
                )

                // Quick Jump Assist Buttons: Start vs Solved
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AssistChip(
                        onClick = {
                            isAutoPlaying = false
                            currentStepIndex = 0
                        },
                        label = { Text("⏮ Initial Scramble", fontSize = 11.sp) }
                    )
                    AssistChip(
                        onClick = {
                            isAutoPlaying = false
                            currentStepIndex = solutionMoves.size
                        },
                        label = {
                            Text(
                                "🏁 Jump to Solved",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF047857)
                            )
                        },
                        leadingIcon = {
                            Icon(
                                imageVector = Icons.Default.CheckCircle,
                                contentDescription = null,
                                tint = Color(0xFF10B981),
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    )
                }
            }

            // Middle Visual Stage (3D / 2D Diagram / Unfolded Net)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .clip(RoundedCornerShape(16.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.25f)),
                contentAlignment = Alignment.Center
            ) {
                when (viewMode) {
                    GuideViewMode.VIEW_3D -> {
                        Cube3DView(
                            cubeState = currentCubeState,
                            activeMove = currentMove,
                            highlightActiveFace = true,
                            modifier = Modifier.fillMaxSize()
                        )
                        Box(
                            modifier = Modifier
                                .align(Alignment.TopStart)
                                .padding(8.dp)
                                .background(
                                    if (isFinished) Color(0xFF064E3B).copy(alpha = 0.9f) else MaterialTheme.colorScheme.surface.copy(alpha = 0.9f),
                                    RoundedCornerShape(8.dp)
                                )
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = if (isFinished) "✓ Fully Solved Cube • Drag to inspect"
                                       else if (currentStepIndex == 0) "Starting Position • Next: ${currentMove?.notation}"
                                       else "Step ${currentStepIndex + 1} of ${solutionMoves.size} • Turn ${currentMove?.notation}",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = if (isFinished) FontWeight.Bold else FontWeight.Medium,
                                color = if (isFinished) Color(0xFF10B981) else MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 10.sp
                            )
                        }
                    }

                    GuideViewMode.TURN_DIAGRAM_2D -> {
                        if (currentMove != null) {
                            MoveVisualDiagram(
                                move = currentMove,
                                showDetailedGrip = true,
                                size = 150.dp,
                                modifier = Modifier.padding(10.dp)
                            )
                        } else {
                            Text(
                                text = if (isFinished) "Cube Solved! All moves completed." else "Starting Position",
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    GuideViewMode.UNFOLDED_NET_2D -> {
                        CubeNetView(
                            cubeState = currentCubeState,
                            modifier = Modifier.padding(6.dp)
                        )
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            // Current Step Card with Notation Translation
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = if (isFinished) Color(0xFF064E3B) else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                )
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (isFinished) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.CheckCircle,
                                contentDescription = null,
                                tint = Color(0xFF10B981),
                                modifier = Modifier.size(26.dp)
                            )
                            Text(
                                text = "Cube Solved!",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                        Text(
                            text = "Optimal solve in ${solutionMoves.size} moves. Tap below to save.",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFFA7F3D0),
                            modifier = Modifier.padding(top = 2.dp)
                        )
                        Spacer(Modifier.height(8.dp))
                        Button(
                            onClick = { showSaveDialog = true },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981))
                        ) {
                            Icon(imageVector = Icons.Default.Bookmark, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Save to Profile & History")
                        }
                    } else if (currentMove != null) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            // Notation badge
                            Box(
                                modifier = Modifier
                                    .size(52.dp)
                                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(12.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = currentMove.notation,
                                    style = MaterialTheme.typography.headlineSmall,
                                    fontWeight = FontWeight.ExtraBold,
                                    color = MaterialTheme.colorScheme.onPrimary
                                )
                            }

                            // Translation description
                            Column(
                                modifier = Modifier
                                    .weight(1f)
                                    .padding(start = 12.dp)
                            ) {
                                Text(
                                    text = currentMove.description,
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Text(
                                    text = "${currentMove.layerLabel} • ${currentMove.directionName}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.primary,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            // Move Sequence Chips Strip (tap to jump)
            LazyRow(
                state = listState,
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // Initial Start Position Chip
                item {
                    val isStart = currentStepIndex == 0
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(
                                if (isStart) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                            )
                            .clickable {
                                isAutoPlaying = false
                                currentStepIndex = 0
                            }
                            .padding(horizontal = 10.dp, vertical = 6.dp)
                            .testTag("start_position_chip"),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "📍 Start",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = if (isStart) FontWeight.Bold else FontWeight.Medium,
                            color = if (isStart) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                itemsIndexed(solutionMoves) { idx, mv ->
                    val isCurrent = idx == currentStepIndex
                    val isPast = idx < currentStepIndex

                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(
                                when {
                                    isCurrent -> MaterialTheme.colorScheme.primary
                                    isPast -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                                    else -> MaterialTheme.colorScheme.surfaceVariant
                                }
                            )
                            .clickable {
                                isAutoPlaying = false
                                currentStepIndex = idx
                            }
                            .padding(horizontal = 10.dp, vertical = 6.dp)
                            .testTag("move_chip_$idx"),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = mv.notation,
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = if (isCurrent) FontWeight.ExtraBold else FontWeight.Medium,
                            color = if (isCurrent) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                // Final Solved State Chip
                item {
                    val isSolved = isFinished
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(
                                if (isSolved) Color(0xFF10B981) else MaterialTheme.colorScheme.surfaceVariant
                            )
                            .clickable {
                                isAutoPlaying = false
                                currentStepIndex = solutionMoves.size
                            }
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                            .testTag("solved_chip"),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "🏁 Solved",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = if (isSolved) FontWeight.ExtraBold else FontWeight.Medium,
                            color = if (isSolved) Color.White else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            // Controls: Prev, Play/Pause, Next, Reset, Speed
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = {
                        isAutoPlaying = false
                        currentStepIndex = 0
                    },
                    modifier = Modifier.size(42.dp)
                ) {
                    Icon(imageVector = Icons.Default.Refresh, contentDescription = "Restart")
                }

                FilledTonalIconButton(
                    onClick = {
                        isAutoPlaying = false
                        if (currentStepIndex > 0) currentStepIndex--
                    },
                    enabled = currentStepIndex > 0,
                    modifier = Modifier.size(48.dp).testTag("prev_step_button")
                ) {
                    Icon(
                        imageVector = Icons.Default.SkipPrevious,
                        contentDescription = "Previous move",
                        modifier = Modifier.size(24.dp)
                    )
                }

                Button(
                    onClick = {
                        if (isFinished) {
                            currentStepIndex = 0
                            isAutoPlaying = true
                        } else {
                            isAutoPlaying = !isAutoPlaying
                        }
                    },
                    shape = CircleShape,
                    modifier = Modifier.size(56.dp).testTag("play_pause_button"),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(
                        imageVector = if (isAutoPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                        contentDescription = if (isAutoPlaying) "Pause" else "Auto Play",
                        modifier = Modifier.size(28.dp)
                    )
                }

                FilledTonalIconButton(
                    onClick = {
                        isAutoPlaying = false
                        if (currentStepIndex < solutionMoves.size) currentStepIndex++
                    },
                    enabled = currentStepIndex < solutionMoves.size,
                    modifier = Modifier.size(48.dp).testTag("next_step_button")
                ) {
                    Icon(
                        imageVector = Icons.Default.SkipNext,
                        contentDescription = "Next move",
                        modifier = Modifier.size(24.dp)
                    )
                }

                FilledTonalButton(
                    onClick = {
                        playSpeedMs = when (playSpeedMs) {
                            1000L -> 500L
                            500L -> 2000L
                            else -> 1000L
                        }
                    },
                    contentPadding = ButtonDefaults.TextButtonContentPadding
                ) {
                    Text(
                        text = when (playSpeedMs) {
                            500L -> "2x"
                            2000L -> "0.5x"
                            else -> "1x"
                        },
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }

    // Save Solve Dialog
    if (showSaveDialog) {
        SaveSolveDialog(
            currentUser = currentUser,
            cubeState = initialCubeState,
            solutionMoves = solutionMoves,
            solveTimeMs = solveTimeMs,
            onSignInRequested = {
                showSaveDialog = false
                onSignInRequested?.invoke()
            },
            onSaveConfirmed = { name, tags ->
                onSaveSolve?.invoke(name, tags)
                isSolveSaved = true
                showSaveDialog = false
            },
            onDismiss = { showSaveDialog = false }
        )
    }
}
