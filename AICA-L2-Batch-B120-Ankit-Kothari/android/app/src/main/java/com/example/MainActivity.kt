package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.DirectionsWalk
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Nightlight
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.components.DownloadAppDialog
import com.example.ui.components.RoutinesDialog
import com.example.ui.components.ShareCardDialog
import com.example.ui.screens.BodyScreen
import com.example.ui.screens.GlowScreen
import com.example.ui.screens.MeScreen
import com.example.ui.screens.StarsScreen
import com.example.ui.screens.TodayScreen
import com.example.ui.theme.CelestialAmber
import com.example.ui.theme.CelestialGold
import com.example.ui.theme.CelestialGoldLight
import com.example.ui.theme.CelestialLavender
import com.example.ui.theme.CosmicCard
import com.example.ui.theme.CosmicCardElevated
import com.example.ui.theme.CosmicDark
import com.example.ui.theme.MyApplicationTheme
import com.example.ui.theme.TextMuted
import com.example.ui.theme.TextSoft
import com.example.ui.theme.TextWhite
import com.example.viewmodel.SaathiTab
import com.example.viewmodel.SaathiViewModel

class MainActivity : ComponentActivity() {

    private val viewModel: SaathiViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            MyApplicationTheme(darkTheme = true) {
                SaathiApp(viewModel = viewModel)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SaathiApp(viewModel: SaathiViewModel) {
    val state by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(CircleShape)
                                .background(CelestialGold.copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = "Saathi Logo",
                                tint = CelestialGold,
                                modifier = Modifier.size(18.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Saathi",
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp,
                            color = TextWhite
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "• Glow & Stars",
                            fontSize = 11.sp,
                            color = CelestialGoldLight
                        )
                    }
                },
                actions = {
                    // Website & App Download Action Pill
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(CosmicCardElevated)
                            .clickable { viewModel.showDownloadAppDialog() }
                            .padding(horizontal = 8.dp, vertical = 6.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Download,
                                contentDescription = "Download Options",
                                tint = CelestialGold,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "App / Web",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = CelestialGold
                            )
                        }
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    // Points Pill
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(16.dp))
                            .background(CelestialGold.copy(alpha = 0.15f))
                            .padding(horizontal = 10.dp, vertical = 5.dp)
                    ) {
                        Text(
                            text = "${state.gamification.totalPoints} pts",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = CelestialGoldLight
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = CosmicCard,
                    titleContentColor = TextWhite
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = CosmicCard,
                contentColor = TextSoft
            ) {
                // Tab 1: Today
                NavigationBarItem(
                    selected = state.currentTab == SaathiTab.TODAY,
                    onClick = { viewModel.selectTab(SaathiTab.TODAY) },
                    icon = { Icon(Icons.Default.AutoAwesome, contentDescription = "Today") },
                    label = { Text("Today", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = CosmicDark,
                        selectedTextColor = CelestialGold,
                        indicatorColor = CelestialGold,
                        unselectedIconColor = TextSoft,
                        unselectedTextColor = TextMuted
                    )
                )

                // Tab 2: Stars
                NavigationBarItem(
                    selected = state.currentTab == SaathiTab.STARS,
                    onClick = { viewModel.selectTab(SaathiTab.STARS) },
                    icon = { Icon(Icons.Default.Nightlight, contentDescription = "Stars") },
                    label = { Text("Stars", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = CosmicDark,
                        selectedTextColor = CelestialLavender,
                        indicatorColor = CelestialLavender,
                        unselectedIconColor = TextSoft,
                        unselectedTextColor = TextMuted
                    )
                )

                // Tab 3: Body
                NavigationBarItem(
                    selected = state.currentTab == SaathiTab.BODY,
                    onClick = { viewModel.selectTab(SaathiTab.BODY) },
                    icon = { Icon(Icons.Default.DirectionsWalk, contentDescription = "Body") },
                    label = { Text("Body", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = CosmicDark,
                        selectedTextColor = CelestialAmber,
                        indicatorColor = CelestialAmber,
                        unselectedIconColor = TextSoft,
                        unselectedTextColor = TextMuted
                    )
                )

                // Tab 4: Glow
                NavigationBarItem(
                    selected = state.currentTab == SaathiTab.GLOW,
                    onClick = { viewModel.selectTab(SaathiTab.GLOW) },
                    icon = { Icon(Icons.Default.Face, contentDescription = "Glow") },
                    label = { Text("Glow", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = CosmicDark,
                        selectedTextColor = Color(0xFFF472B6),
                        indicatorColor = Color(0xFFF472B6),
                        unselectedIconColor = TextSoft,
                        unselectedTextColor = TextMuted
                    )
                )

                // Tab 5: Me
                NavigationBarItem(
                    selected = state.currentTab == SaathiTab.ME,
                    onClick = { viewModel.selectTab(SaathiTab.ME) },
                    icon = { Icon(Icons.Default.Person, contentDescription = "Me") },
                    label = { Text("Me", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = CosmicDark,
                        selectedTextColor = CelestialGold,
                        indicatorColor = CelestialGold,
                        unselectedIconColor = TextSoft,
                        unselectedTextColor = TextMuted
                    )
                )
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (state.currentTab) {
                SaathiTab.TODAY -> TodayScreen(state = state, viewModel = viewModel)
                SaathiTab.STARS -> StarsScreen(state = state, viewModel = viewModel)
                SaathiTab.BODY -> BodyScreen(state = state, viewModel = viewModel)
                SaathiTab.GLOW -> GlowScreen(state = state, viewModel = viewModel)
                SaathiTab.ME -> MeScreen(state = state, viewModel = viewModel)
            }
        }

        // Active Routine Timer Dialog
        state.activeRoutineType?.let { routineType ->
            RoutinesDialog(
                routineType = routineType,
                onComplete = { viewModel.completeRoutine(it) },
                onDismiss = { viewModel.closeRoutine() }
            )
        }

        // Share Card Dialog
        if (state.showShareCardDialog) {
            val (title, content, subText) = when (state.shareCardType) {
                "FORTUNE" -> Triple(
                    if (state.dailyActivity.isGoldenCookie) "Golden Fortune Cookie" else "Daily Fortune",
                    state.dailyActivity.fortuneText.ifBlank { "A warm heart will unlock a doorway that intellect has been knocking on for weeks." },
                    "Daily wisdom cracked with Saathi • +${if (state.dailyActivity.isGoldenCookie) "25" else "5"} points"
                )
                "DAY" -> Triple(
                    "Cosmic Sky Card (${state.dayCard.moonSignVedic} Moon)",
                    state.dayCard.proTip,
                    "Nakshatra: ${state.dayCard.nakshatra}  |  Rahu Kaal: ${state.dayCard.rahuKaal}"
                )
                else -> Triple(
                    "Saathi Daily Streak Milestone",
                    "Maintained a ${state.gamification.streakDays}-day streak of healthy water, movement & self-care!",
                    "Level: ${state.gamification.levelName} (${state.gamification.totalPoints} pts)"
                )
            }

            ShareCardDialog(
                type = state.shareCardType,
                title = title,
                content = content,
                subText = subText,
                onDismiss = { viewModel.dismissShareCard() }
            )
        }

        // Website & Download App Dialog
        if (state.showDownloadAppDialog) {
            DownloadAppDialog(
                onDismiss = { viewModel.dismissDownloadAppDialog() }
            )
        }
    }
}
