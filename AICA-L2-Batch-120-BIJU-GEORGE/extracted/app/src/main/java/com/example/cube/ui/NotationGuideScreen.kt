package com.example.cube.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.cube.model.CubeFace
import com.example.cube.model.CubeMove
import com.example.cube.model.CubeState
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotationGuideScreen(
    onBack: () -> Unit
) {
    BackHandler { onBack() }

    var selectedFaceFilter by remember { mutableStateOf<CubeFace?>(null) }
    var activeMove by remember { mutableStateOf(CubeMove.ALL_STANDARD_MOVES.first()) }
    var isCheatSheetExpanded by remember { mutableStateOf(false) }

    // Interactive animated simulation: toggle between solved state and applied move state
    var isSimulatingTurn by remember { mutableStateOf(false) }
    var showMovedState by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    val filteredMoves = remember(selectedFaceFilter) {
        if (selectedFaceFilter == null) {
            CubeMove.ALL_STANDARD_MOVES
        } else {
            CubeMove.ALL_STANDARD_MOVES.filter { it.face == selectedFaceFilter }
        }
    }

    // Cube state displayed in the live 3D preview
    val demoCubeState = remember(activeMove, showMovedState) {
        if (showMovedState) {
            CubeState.solved().applyMove(activeMove)
        } else {
            CubeState.solved()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "Cube Moves & Notation Guide",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "Official WCA Singmaster Notation",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack, modifier = Modifier.testTag("notation_back_button")) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Notation 101 Rules Banner
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f)
                    )
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Info,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = "How Rubik's Cube Notation Works",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                        Spacer(Modifier.height(10.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            NotationRuleChip(
                                symbol = "R",
                                title = "Clockwise",
                                desc = "90° Turn",
                                modifier = Modifier.weight(1f)
                            )
                            NotationRuleChip(
                                symbol = "R'",
                                title = "Prime",
                                desc = "90° Counter-CW",
                                modifier = Modifier.weight(1f)
                            )
                            NotationRuleChip(
                                symbol = "R2",
                                title = "Double",
                                desc = "180° Half Turn",
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }

            // Interactive 3D Demo Preview of Active Selected Move
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                    )
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
                            Column {
                                Text(
                                    text = "Live 3D Move Simulation",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = if (showMovedState) "Showing state after ${activeMove.notation}" else "Showing starting solved state",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontSize = 11.sp
                                )
                            }

                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(8.dp))
                                        .padding(horizontal = 10.dp, vertical = 4.dp)
                                ) {
                                    Text(
                                        text = activeMove.notation,
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.ExtraBold,
                                        color = MaterialTheme.colorScheme.onPrimary
                                    )
                                }
                            }
                        }

                        Spacer(Modifier.height(10.dp))

                        // 3D Canvas
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(180.dp)
                                .clip(RoundedCornerShape(14.dp))
                                .background(
                                    brush = Brush.verticalGradient(
                                        colors = listOf(Color(0xFF0F172A), Color(0xFF1E293B))
                                    )
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Cube3DView(
                                cubeState = demoCubeState,
                                activeMove = if (showMovedState) activeMove else null,
                                highlightActiveFace = true,
                                modifier = Modifier.fillMaxSize()
                            )
                        }

                        Spacer(Modifier.height(10.dp))

                        // Interactive Move Player Controls
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(
                                onClick = {
                                    scope.launch {
                                        isSimulatingTurn = true
                                        showMovedState = false
                                        delay(400)
                                        showMovedState = true
                                        isSimulatingTurn = false
                                    }
                                },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(10.dp),
                                enabled = !isSimulatingTurn,
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                            ) {
                                Icon(imageVector = Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Play Turn", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }

                            OutlinedButton(
                                onClick = { showMovedState = !showMovedState },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(10.dp)
                            ) {
                                Icon(imageVector = Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(Modifier.width(6.dp))
                                Text(if (showMovedState) "Show Solved" else "Show Turned", fontSize = 12.sp)
                            }
                        }
                    }
                }
            }

            // Professional Visual Turn Diagram Card for the Active Move
            item {
                MoveVisualDiagram(
                    move = activeMove,
                    showDetailedGrip = true,
                    size = 150.dp
                )
            }

            // Quick Notation Cheat Sheet (Collapsible)
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { isCheatSheetExpanded = !isCheatSheetExpanded },
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                    )
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.AutoAwesome,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.secondary,
                                    modifier = Modifier.size(18.dp)
                                )
                                Spacer(Modifier.width(8.dp))
                                Text(
                                    text = "Notation Cheat Sheet & Inverse Pairs",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Icon(
                                imageVector = if (isCheatSheetExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }

                        AnimatedVisibility(visible = isCheatSheetExpanded) {
                            Column(modifier = Modifier.padding(top = 10.dp)) {
                                CheatSheetRow(moveName = "Right (R)", cw = "R (away)", ccw = "R' (toward)", doubleTurn = "R2 (180°)")
                                CheatSheetRow(moveName = "Left (L)", cw = "L (toward)", ccw = "L' (away)", doubleTurn = "L2 (180°)")
                                CheatSheetRow(moveName = "Top (U)", cw = "U (left flick)", ccw = "U' (right flick)", doubleTurn = "U2 (180°)")
                                CheatSheetRow(moveName = "Bottom (D)", cw = "D (right)", ccw = "D' (left)", doubleTurn = "D2 (180°)")
                                CheatSheetRow(moveName = "Front (F)", cw = "F (clockwise)", ccw = "F' (counter-cw)", doubleTurn = "F2 (180°)")
                                CheatSheetRow(moveName = "Back (B)", cw = "B (clockwise)", ccw = "B' (counter-cw)", doubleTurn = "B2 (180°)")
                            }
                        }
                    }
                }
            }

            // Face Filters
            item {
                Text(
                    text = "Select Move to Inspect",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(6.dp))
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    item {
                        FilterChip(
                            selected = selectedFaceFilter == null,
                            onClick = { selectedFaceFilter = null },
                            label = { Text("All Moves (${CubeMove.ALL_STANDARD_MOVES.size})") }
                        )
                    }
                    items(CubeFace.entries.toTypedArray()) { face ->
                        FilterChip(
                            selected = selectedFaceFilter == face,
                            onClick = { selectedFaceFilter = face },
                            label = { Text("${face.char} (${face.displayName.take(5)})") }
                        )
                    }
                }
            }

            // Moves Grid / List
            items(filteredMoves) { move ->
                val isSelected = move == activeMove
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            activeMove = move
                            showMovedState = true
                        },
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)
                    )
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(44.dp)
                                .background(
                                    if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant,
                                    RoundedCornerShape(10.dp)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = move.notation,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.ExtraBold,
                                color = if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface
                            )
                        }
                        Spacer(Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = move.description,
                                style = MaterialTheme.typography.labelLarge,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "${move.layerLabel} • ${move.directionName}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 11.sp
                            )
                        }
                        if (isSelected) {
                            Icon(
                                imageVector = Icons.Default.CheckCircle,
                                contentDescription = "Selected",
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun NotationRuleChip(
    symbol: String,
    title: String,
    desc: String,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.7f))
            .padding(8.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = symbol,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                text = title,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = desc,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 10.sp
            )
        }
    }
}

@Composable
private fun CheatSheetRow(
    moveName: String,
    cw: String,
    ccw: String,
    doubleTurn: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = moveName,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.width(90.dp)
        )
        Text(text = cw, style = MaterialTheme.typography.bodySmall, fontSize = 11.sp, modifier = Modifier.weight(1f))
        Text(text = ccw, style = MaterialTheme.typography.bodySmall, fontSize = 11.sp, modifier = Modifier.weight(1f))
        Text(text = doubleTurn, style = MaterialTheme.typography.bodySmall, fontSize = 11.sp, modifier = Modifier.weight(1f))
    }
}
