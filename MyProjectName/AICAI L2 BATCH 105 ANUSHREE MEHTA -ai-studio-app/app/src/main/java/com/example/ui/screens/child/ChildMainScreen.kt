package com.example.ui.screens.child

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Games
import androidx.compose.material.icons.filled.LocalFlorist
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
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
import com.example.data.model.BadgeItem
import com.example.data.model.DailyMission
import com.example.ui.GenerationsAppViewModel
import com.example.ui.screens.senior.FindThePairsGame
import com.example.ui.screens.senior.SeniorStoriesScreen
import com.example.ui.screens.senior.SharedPaintingCanvas
import com.example.ui.screens.child.MusicStudioScreen


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChildMainScreen(
    viewModel: GenerationsAppViewModel,
    onSwitchProfile: () -> Unit
) {
    val points by viewModel.childPoints.collectAsState()
    val badges by viewModel.childBadges.collectAsState()
    val missions by viewModel.dailyMissions.collectAsState()
    val palette by viewModel.palette.collectAsState()

    var activeSubView by remember { mutableIntStateOf(0) } // 0: Hub, 1: Co-writing Story, 2: Find Pairs, 3: Canvas

    Scaffold(
        topBar = {
            TopAppBar(
                navigationIcon = {
                    IconButton(
                        onClick = { activeSubView = 0 },
                        modifier = Modifier
                            .padding(start = 6.dp)
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(if (activeSubView == 0) Color.White.copy(alpha = 0.25f) else Color.Transparent)
                    ) {
                        Icon(
                            imageVector = androidx.compose.material.icons.filled.Home,
                            contentDescription = "Home",
                            tint = Color.White,
                            modifier = Modifier.size(28.dp)
                        )
                    }
                },
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(Color(0xFFFFB703)),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(text = "⭐", fontSize = 20.sp)
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Leo's Adventure Hub",
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            Text(
                                text = "Buddy with Grandma Eleanor",
                                fontSize = 14.sp,
                                color = Color.White.copy(alpha = 0.9f)
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF7C3AED),
                    titleContentColor = Color.White
                ),
                actions = {
                    Surface(
                        shape = RoundedCornerShape(20.dp),
                        color = Color(0xFFFFB703),
                        modifier = Modifier.padding(end = 6.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Star, contentDescription = null, tint = Color(0xFF78350F), modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(text = "$points pts", fontWeight = FontWeight.Bold, color = Color(0xFF78350F), fontSize = 15.sp)
                        }
                    }
                    com.example.ui.components.PalettePickerButton(
                        current = palette,
                        onSelect = { viewModel.setPalette(it) }
                    )
                    IconButton(onClick = onSwitchProfile) {
                        Icon(Icons.Default.SwapHoriz, contentDescription = "Switch profile", tint = Color.White, modifier = Modifier.size(28.dp))
                    }
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .testTag("child_main_screen")
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
            when (activeSubView) {
                1 -> {
                    // Back button to Child Hub
                    ChildSubHeader(title = "Co-Writing with Eleanor", onBack = { activeSubView = 0 })
                    SeniorStoriesScreen(viewModel = viewModel)
                }
                2 -> {
                    ChildSubHeader(title = "Memory Match Game", onBack = { activeSubView = 0 })
                    FindThePairsGame(onWin = { viewModel.awardChildPoints(50) })
                }
                3 -> {
                    ChildSubHeader(title = "Shared Art Canvas", onBack = { activeSubView = 0 })
                    SharedPaintingCanvas(onShare = { viewModel.awardChildPoints(40) })
                }
                4 -> {
                    MusicStudioScreen(viewModel = viewModel, onBack = { activeSubView = 0 })
                }
                else -> {
                    ChildHubContent(
                        points = points,
                        badges = badges,
                        missions = missions,
                        onOpenStory = { activeSubView = 1 },
                        onOpenGame = { activeSubView = 2 },
                        onOpenArt = { activeSubView = 3 },
                        onOpenMusic = { activeSubView = 4 },
                        onCompleteMission = { viewModel.completeMission(it) }
                    )
                }
            }
        }

    }
}

@Composable
fun ChildSubHeader(title: String, onBack: () -> Unit) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = title, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            Button(onClick = onBack, shape = RoundedCornerShape(12.dp)) {
                Text("Back to Hub")
            }
        }
    }
}

@Composable
fun ChildHubContent(
    points: Int,
    badges: List<BadgeItem>,
    missions: List<DailyMission>,
    onOpenStory: () -> Unit,
    onOpenGame: () -> Unit,
    onOpenArt: () -> Unit,
    onOpenMusic: () -> Unit,
    onCompleteMission: (String) -> Unit
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Level & Points Card
        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF3E8FF)),
                border = BorderStroke(2.5.dp, Color(0xFF7C3AED).copy(alpha = 0.4f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text(
                                text = "Level 4: Story Explorer 🚀",
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF581C87)
                            )
                            Text(
                                text = "$points Star Points • 60 pts to Level 5",
                                fontSize = 16.sp,
                                color = Color(0xFF6B21A8)
                            )
                        }

                        Box(
                            modifier = Modifier
                                .size(56.dp)
                                .clip(CircleShape)
                                .background(Color(0xFFFFB703)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.EmojiEvents,
                                contentDescription = null,
                                tint = Color(0xFF78350F),
                                modifier = Modifier.size(34.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    LinearProgressIndicator(
                        progress = { 0.75f },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(12.dp)
                            .clip(RoundedCornerShape(6.dp)),
                        color = Color(0xFF7C3AED),
                        trackColor = Color(0xFFDDD6FE)
                    )
                }
            }
        }

        // Featured: Kids Music Studio Card
        item {
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFFDF9)),
                border = BorderStroke(2.5.dp, Color(0xFFD4AF37)),
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpenMusic() }
            ) {
                Row(
                    modifier = Modifier.padding(18.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(text = "🎵", fontSize = 24.sp)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Kids Music Studio",
                                fontSize = 21.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF4A6B53)
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Play Piano, Kalimba, Sitar & Tabla! Record 1-min melodies to gift Grandma Eleanor.",
                            fontSize = 15.sp,
                            color = Color(0xFF2C3E30)
                        )
                    }
                    Button(
                        onClick = onOpenMusic,
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4A6B53))
                    ) {
                        Text("Play 🎶", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // Quick Buddy Co-op Tiles - 4 in a grid/row
        item {
            Text(
                text = "Play with Grandma Eleanor",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.height(10.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                ChildActionTile(
                    title = "Music Studio",
                    subtitle = "Sitar & Tabla",
                    icon = Icons.Default.MusicNote,
                    bgBrush = Brush.linearGradient(listOf(Color(0xFF4A6B53), Color(0xFF2E4F37))),
                    modifier = Modifier.weight(1f),
                    onClick = onOpenMusic
                )
                ChildActionTile(
                    title = "Co-Write",
                    subtitle = "Chapter 3",
                    icon = Icons.Default.AutoStories,
                    bgBrush = Brush.linearGradient(listOf(Color(0xFF7C3AED), Color(0xFF9333EA))),
                    modifier = Modifier.weight(1f),
                    onClick = onOpenStory
                )
                ChildActionTile(
                    title = "Memory Pairs",
                    subtitle = "Find 6 matches",
                    icon = Icons.Default.Games,
                    bgBrush = Brush.linearGradient(listOf(Color(0xFFE76F51), Color(0xFFF97316))),
                    modifier = Modifier.weight(1f),
                    onClick = onOpenGame
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            // Second row of 3: scrolls with the page instead of sitting fixed at the bottom
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                ChildActionTile(
                    title = "Art Canvas",
                    subtitle = "Paint mandala",
                    icon = Icons.Default.Palette,
                    bgBrush = Brush.linearGradient(listOf(Color(0xFF059669), Color(0xFF10B981))),
                    modifier = Modifier.weight(1f),
                    onClick = onOpenArt
                )
                // "Switch Profile" tile removed: the top bar already has a switch-profile icon.
                Spacer(modifier = Modifier.weight(1f))
                Spacer(modifier = Modifier.weight(1f))
            }
        }

        // Daily Missions Checklist
        item {
            Card(
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "Daily Missions 🎯",
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "${missions.count { it.isCompleted }}/${missions.size} Done",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    missions.forEach { mission ->
                        MissionRowItem(
                            mission = mission,
                            onComplete = { onCompleteMission(mission.id) }
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                    }
                }
            }
        }

        // Badges Gallery
        item {
            Text(
                text = "Trophy Badges 🏆",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(modifier = Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                items(badges) { badge ->
                    BadgeCard(badge = badge)
                }
            }
        }
    }
}

@Composable
fun ChildActionTile(
    title: String,
    subtitle: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    bgBrush: Brush,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(20.dp),
        shadowElevation = 3.dp,
        modifier = modifier.height(130.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(bgBrush)
                .padding(14.dp),
            contentAlignment = Alignment.CenterStart
        ) {
            Column(verticalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxSize()) {
                Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(32.dp))
                Column {
                    Text(text = title, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = Color.White)
                    Text(text = subtitle, fontSize = 13.sp, color = Color.White.copy(alpha = 0.85f))
                }
            }
        }
    }
}

@Composable
fun MissionRowItem(
    mission: DailyMission,
    onComplete: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = if (mission.isCompleted) Color(0xFFDCFCE7) else MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (mission.isCompleted) Icons.Default.CheckCircle else Icons.Default.AutoAwesome,
                    contentDescription = null,
                    tint = if (mission.isCompleted) Color(0xFF16A34A) else Color(0xFF7C3AED),
                    modifier = Modifier.size(28.dp)
                )
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = mission.title,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (mission.isCompleted) Color(0xFF166534) else MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        text = mission.description,
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (!mission.isCompleted) {
                Button(
                    onClick = onComplete,
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF7C3AED))
                ) {
                    Text("+${mission.pointsReward}★", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
fun BadgeCard(badge: BadgeItem) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = if (badge.isUnlocked) Color(0xFFFEF3C7) else MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier
            .width(140.dp)
            .height(130.dp)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(text = if (badge.isUnlocked) "🏅" else "🔒", fontSize = 32.sp)
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = badge.title,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = if (badge.isUnlocked) Color(0xFF78350F) else MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = badge.description,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2
            )
        }
    }
}
