package com.example.ui.screens.senior

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
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
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Brush
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FormatColorFill
import androidx.compose.material.icons.filled.Games
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.TextFields
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.SeniorLargeButton
import kotlinx.coroutines.delay

@Composable
fun SeniorGamesScreen(viewModel: GenerationsAppViewModel) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabTitles = listOf("Find Pairs", "Word Art", "Shared Canvas")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .testTag("senior_games_screen")
    ) {
        TabRow(
            selectedTabIndex = selectedTab,
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.primary
        ) {
            tabTitles.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    modifier = Modifier.defaultMinSize(minHeight = 56.dp),
                    text = {
                        Text(
                            text = title,
                            fontSize = 18.sp,
                            fontWeight = if (selectedTab == index) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        when (selectedTab) {
            0 -> FindThePairsGame(onWin = { viewModel.awardChildPoints(50) })
            1 -> WordArtCreator(onSendToBuddy = { viewModel.awardChildPoints(30) })
            2 -> SharedPaintingCanvas(onShare = { viewModel.awardChildPoints(40) })
        }
    }
}

// ---------------------------------------------
// 1. FIND THE PAIRS MEMORY GAME
// ---------------------------------------------
data class MemoryCard(
    val id: Int,
    val emoji: String,
    val name: String,
    var isFlipped: Boolean = false,
    var isMatched: Boolean = false
)

@Composable
fun FindThePairsGame(onWin: () -> Unit) {
    val emojis = listOf("🌻", "🦋", "🎨", "📖", "☕", "🐶")
    val cards = remember {
        mutableStateListOf<MemoryCard>().apply {
            val list = (emojis + emojis).shuffled().mapIndexed { i, em ->
                val name = when (em) {
                    "🌻" -> "Sunflower"
                    "🦋" -> "Butterfly"
                    "🎨" -> "Palette"
                    "📖" -> "Storybook"
                    "☕" -> "Tea Cup"
                    else -> "Puppy"
                }
                MemoryCard(id = i, emoji = em, name = name)
            }
            addAll(list)
        }
    }

    var selectedFirst by remember { mutableStateOf<Int?>(null) }
    var selectedSecond by remember { mutableStateOf<Int?>(null) }
    var moves by remember { mutableIntStateOf(0) }
    var matchesFound by remember { mutableIntStateOf(0) }
    var isChecking by remember { mutableStateOf(false) }

    val isGameOver = matchesFound == emojis.size

    LaunchedEffect(selectedSecond) {
        val first = selectedFirst
        val second = selectedSecond
        if (first != null && second != null) {
            isChecking = true
            moves += 1
            delay(900)
            if (cards[first].emoji == cards[second].emoji) {
                cards[first] = cards[first].copy(isMatched = true, isFlipped = true)
                cards[second] = cards[second].copy(isMatched = true, isFlipped = true)
                matchesFound += 1
                if (matchesFound == emojis.size) {
                    onWin()
                }
            } else {
                cards[first] = cards[first].copy(isFlipped = false)
                cards[second] = cards[second].copy(isFlipped = false)
            }
            selectedFirst = null
            selectedSecond = null
            isChecking = false
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Find the Pairs",
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Text(
                        text = "Match the 6 buddy pairs",
                        fontSize = 18.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Surface(
                    shape = RoundedCornerShape(14.dp),
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Text(
                        text = "Moves: $moves",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp)
                    )
                }
            }
        }

        if (isGameOver) {
            item {
                Card(
                    shape = RoundedCornerShape(22.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFDCFCE7)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(text = "🎉 Wonderful Match!", fontSize = 26.sp, fontWeight = FontWeight.Bold, color = Color(0xFF166534))
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "You found all pairs in $moves moves! Leo earned +50 team star points.",
                            fontSize = 18.sp,
                            textAlign = TextAlign.Center,
                            color = Color(0xFF14532D)
                        )
                    }
                }
            }
        }

        // Memory Grid: 4 columns x 3 rows = 12 big cards
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                for (row in 0 until 3) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        for (col in 0 until 4) {
                            val index = row * 4 + col
                            val card = cards[index]
                            val isShown = card.isFlipped || card.isMatched

                            Surface(
                                onClick = {
                                    if (!isChecking && !card.isMatched && !card.isFlipped) {
                                        if (selectedFirst == null) {
                                            selectedFirst = index
                                            cards[index] = cards[index].copy(isFlipped = true)
                                        } else if (selectedSecond == null && selectedFirst != index) {
                                            selectedSecond = index
                                            cards[index] = cards[index].copy(isFlipped = true)
                                        }
                                    }
                                },
                                shape = RoundedCornerShape(18.dp),
                                color = if (isShown) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
                                border = ButtonDefaults.outlinedButtonBorder.copy(width = 2.dp),
                                shadowElevation = 3.dp,
                                modifier = Modifier
                                    .weight(1f)
                                    .height(96.dp)
                            ) {
                                Box(
                                    contentAlignment = Alignment.Center,
                                    modifier = Modifier.fillMaxSize()
                                ) {
                                    if (isShown) {
                                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                            Text(text = card.emoji, fontSize = 34.sp)
                                            Text(text = card.name, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        }
                                    } else {
                                        Text(text = "❓", fontSize = 28.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        item {
            SeniorLargeButton(
                text = "Restart New Game",
                icon = Icons.Default.Refresh,
                isPrimary = false,
                onClick = {
                    cards.clear()
                    val list = (emojis + emojis).shuffled().mapIndexed { i, em ->
                        MemoryCard(id = i, emoji = em, name = "")
                    }
                    cards.addAll(list)
                    selectedFirst = null
                    selectedSecond = null
                    moves = 0
                    matchesFound = 0
                }
            )
        }
    }
}

// ---------------------------------------------
// 2. WORD ART CREATOR
// ---------------------------------------------
@Composable
fun WordArtCreator(onSendToBuddy: () -> Unit) {
    var customWord by remember { mutableStateOf("Kindness & Wisdom") }
    var secondaryWord by remember { mutableStateOf("Connecting Eleanor & Leo") }
    val colorOptions = listOf(
        Color(0xFF14535C),
        Color(0xFFE76F51),
        Color(0xFF7C3AED),
        Color(0xFF2563EB),
        Color(0xFF059669)
    )
    var selectedColorIndex by remember { mutableIntStateOf(0) }
    var sentNotice by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "Generational Word Art",
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Create colorful inspiring affirmation cards to send to your buddy",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Preview Banner
        item {
            Surface(
                shape = RoundedCornerShape(24.dp),
                color = colorOptions[selectedColorIndex],
                shadowElevation = 6.dp,
                modifier = Modifier
                    .fillMaxWidth()
                    .defaultMinSize(minHeight = 160.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(
                        text = "⭐ $customWord ⭐",
                        fontSize = 28.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = secondaryWord,
                        fontSize = 20.sp,
                        color = Color(0xFFFEF3C7),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        // Color Picker
        item {
            Text(
                text = "Card Theme Palette:",
                fontSize = 19.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                colorOptions.forEachIndexed { i, color ->
                    Box(
                        modifier = Modifier
                            .size(50.dp)
                            .clip(CircleShape)
                            .background(color)
                            .clickable { selectedColorIndex = i }
                            .border(
                                width = if (selectedColorIndex == i) 4.dp else 1.dp,
                                color = if (selectedColorIndex == i) MaterialTheme.colorScheme.onSurface else Color.Transparent,
                                shape = CircleShape
                            )
                    )
                }
            }
        }

        item {
            OutlinedTextField(
                value = customWord,
                onValueChange = { customWord = it },
                label = { Text("Main Affirmation / Phrase", fontSize = 18.sp) },
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth(),
                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 19.sp)
            )
        }

        item {
            OutlinedTextField(
                value = secondaryWord,
                onValueChange = { secondaryWord = it },
                label = { Text("Personal Dedication / Subtitle", fontSize = 18.sp) },
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth(),
                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 19.sp)
            )
        }

        item {
            SeniorLargeButton(
                text = "Send Word Art to Leo",
                icon = Icons.Default.Send,
                onClick = {
                    onSendToBuddy()
                    sentNotice = true
                }
            )
        }

        if (sentNotice) {
            item {
                Card(
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFDCFCE7)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Favorite, contentDescription = null, tint = Color(0xFF16A34A))
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "Card delivered to Leo's Daily Mission Center! +30 Points",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF166534)
                        )
                    }
                }
            }
        }
    }
}

// ---------------------------------------------
// 3. SHARED PAINTING CANVAS
// ---------------------------------------------
data class DrawnLine(
    val points: List<Offset>,
    val color: Color,
    val strokeWidth: Float
)

@Composable
fun SharedPaintingCanvas(onShare: () -> Unit) {
    val templates = listOf("Sunflower", "Butterfly", "Cozy Cottage", "Playful Kitten")
    var selectedTemplateIndex by remember { mutableIntStateOf(0) }

    val palette = listOf(
        Color(0xFFFFB703), // Yellow
        Color(0xFFFF6584), // Coral
        Color(0xFF7C3AED), // Violet
        Color(0xFF10B981), // Green
        Color(0xFF2563EB), // Blue
        Color(0xFF1F2937)  // Charcoal
    )
    var selectedColor by remember { mutableStateOf(palette[0]) }
    var strokeSize by remember { mutableStateOf(16f) }
    val lines = remember { mutableStateListOf<DrawnLine>() }
    var currentLinePoints = remember { mutableStateListOf<Offset>() }
    var sharedConfirmation by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Text(
                text = "Shared Painting Canvas",
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                text = "Choose an outline and paint together with smooth brush colors",
                fontSize = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Outline selector
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                templates.forEachIndexed { i, template ->
                    Surface(
                        onClick = {
                            selectedTemplateIndex = i
                            lines.clear()
                            currentLinePoints.clear()
                        },
                        shape = RoundedCornerShape(14.dp),
                        color = if (selectedTemplateIndex == i) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text(
                            text = template,
                            fontSize = 14.sp,
                            fontWeight = if (selectedTemplateIndex == i) FontWeight.Bold else FontWeight.Normal,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(vertical = 10.dp),
                            color = if (selectedTemplateIndex == i) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }

        // Color and Brush Controls
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    palette.forEach { c ->
                        Box(
                            modifier = Modifier
                                .size(42.dp)
                                .clip(CircleShape)
                                .background(c)
                                .clickable { selectedColor = c }
                                .border(
                                    width = if (selectedColor == c) 3.dp else 1.dp,
                                    color = if (selectedColor == c) MaterialTheme.colorScheme.onSurface else Color.LightGray,
                                    shape = CircleShape
                                )
                        )
                    }
                }

                OutlinedButton(
                    onClick = {
                        lines.clear()
                        currentLinePoints.clear()
                    },
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Clear, contentDescription = "Clear")
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Clear", fontSize = 16.sp)
                }
            }
        }

        // Interactive Canvas with Pre-Drawn Outline & Freehand Brush
        item {
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                border = ButtonDefaults.outlinedButtonBorder.copy(width = 2.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(280.dp)
            ) {
                Canvas(
                    modifier = Modifier
                        .fillMaxSize()
                        .pointerInput(Unit) {
                            detectDragGestures(
                                onDragStart = { offset ->
                                    currentLinePoints.clear()
                                    currentLinePoints.add(offset)
                                },
                                onDrag = { change, _ ->
                                    change.consume()
                                    currentLinePoints.add(change.position)
                                },
                                onDragEnd = {
                                    if (currentLinePoints.isNotEmpty()) {
                                        lines.add(DrawnLine(currentLinePoints.toList(), selectedColor, strokeSize))
                                        currentLinePoints.clear()
                                    }
                                }
                            )
                        }
                ) {
                    // 1. Draw Pre-Drawn Template Outline
                    val w = size.width
                    val h = size.height
                    val templateOutlineColor = Color(0xFF6B7280)

                    when (selectedTemplateIndex) {
                        0 -> {
                            // Sunflower Outline
                            drawCircle(color = templateOutlineColor, radius = 45f, center = Offset(w / 2, h / 2 - 20f), style = Stroke(width = 4f))
                            // Petals
                            for (angle in 0 until 360 step 45) {
                                val rad = Math.toRadians(angle.toDouble())
                                val px = (w / 2 + Math.cos(rad) * 80).toFloat()
                                val py = (h / 2 - 20f + Math.sin(rad) * 80).toFloat()
                                drawCircle(color = templateOutlineColor, radius = 25f, center = Offset(px, py), style = Stroke(width = 3f))
                            }
                            // Stem
                            drawLine(color = templateOutlineColor, start = Offset(w / 2, h / 2 + 30f), end = Offset(w / 2, h - 20f), strokeWidth = 5f)
                        }
                        1 -> {
                            // Butterfly Outline
                            val cx = w / 2
                            val cy = h / 2
                            drawOval(color = templateOutlineColor, topLeft = Offset(cx - 15f, cy - 60f), size = androidx.compose.ui.geometry.Size(30f, 120f), style = Stroke(width = 4f))
                            // Left Wings
                            drawCircle(color = templateOutlineColor, radius = 55f, center = Offset(cx - 70f, cy - 35f), style = Stroke(width = 4f))
                            drawCircle(color = templateOutlineColor, radius = 40f, center = Offset(cx - 60f, cy + 35f), style = Stroke(width = 4f))
                            // Right Wings
                            drawCircle(color = templateOutlineColor, radius = 55f, center = Offset(cx + 70f, cy - 35f), style = Stroke(width = 4f))
                            drawCircle(color = templateOutlineColor, radius = 40f, center = Offset(cx + 60f, cy + 35f), style = Stroke(width = 4f))
                        }
                        else -> {
                            // Cozy House Outline
                            val cx = w / 2
                            val cy = h / 2
                            // House box
                            drawRect(color = templateOutlineColor, topLeft = Offset(cx - 90f, cy - 20f), size = androidx.compose.ui.geometry.Size(180f, 120f), style = Stroke(width = 4f))
                            // Roof triangle
                            val roofPath = Path().apply {
                                moveTo(cx - 110f, cy - 20f)
                                lineTo(cx, cy - 100f)
                                lineTo(cx + 110f, cy - 20f)
                                close()
                            }
                            drawPath(roofPath, color = templateOutlineColor, style = Stroke(width = 4f))
                            // Door & window
                            drawRect(color = templateOutlineColor, topLeft = Offset(cx - 25f, cy + 30f), size = androidx.compose.ui.geometry.Size(50f, 70f), style = Stroke(width = 3f))
                        }
                    }

                    // 2. Render Existing Drawn Lines
                    lines.forEach { line ->
                        if (line.points.size > 1) {
                            for (i in 0 until line.points.size - 1) {
                                drawLine(
                                    color = line.color,
                                    start = line.points[i],
                                    end = line.points[i + 1],
                                    strokeWidth = line.strokeWidth,
                                    cap = StrokeCap.Round
                                )
                            }
                        }
                    }

                    // 3. Render Current Active Drag Line
                    if (currentLinePoints.size > 1) {
                        for (i in 0 until currentLinePoints.size - 1) {
                            drawLine(
                                color = selectedColor,
                                start = currentLinePoints[i],
                                end = currentLinePoints[i + 1],
                                strokeWidth = strokeSize,
                                cap = StrokeCap.Round
                            )
                        }
                    }
                }
            }
        }

        item {
            SeniorLargeButton(
                text = "Share Painting with Leo",
                icon = Icons.Default.Send,
                onClick = {
                    onShare()
                    sharedConfirmation = true
                }
            )
        }

        if (sharedConfirmation) {
            item {
                Card(
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFDCFCE7)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Palette, contentDescription = null, tint = Color(0xFF16A34A))
                        Spacer(modifier = Modifier.width(10.dp))
                        Text(
                            text = "Painting shared with Leo! He can color his side too. +40 Points",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF166534)
                        )
                    }
                }
            }
        }
    }
}
