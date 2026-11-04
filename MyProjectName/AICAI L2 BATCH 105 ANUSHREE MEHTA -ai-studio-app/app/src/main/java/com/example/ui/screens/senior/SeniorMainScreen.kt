package com.example.ui.screens.senior

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Contrast
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.GenerationsAppViewModel
import com.example.ui.components.MandalaDecor
import com.example.ui.screens.child.MusicStudioScreen
import com.example.ui.screens.parent.ParentMainScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SeniorMainScreen(
    viewModel: GenerationsAppViewModel,
    onSwitchProfile: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val preferences by viewModel.seniorPreferences.collectAsState()
    val palette by viewModel.palette.collectAsState()
    val currentUser by viewModel.currentUser.collectAsState()

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val maxWidthConstraint = if (maxWidth > 800.dp) 740.dp else maxWidth

        Scaffold(
            topBar = {
                TopAppBar(
                    navigationIcon = {
                        // Home Button ALWAYS appears on top-left corner
                        IconButton(
                            onClick = { selectedTab = 0 },
                            modifier = Modifier
                                .padding(start = 6.dp)
                                .size(46.dp)
                                .clip(CircleShape)
                                .background(if (selectedTab == 0) Color.White.copy(alpha = 0.25f) else Color.Transparent)
                                .testTag("top_left_home_button")
                        ) {
                            Icon(
                                imageVector = Icons.Default.Home,
                                contentDescription = "Home",
                                tint = MaterialTheme.colorScheme.onPrimary,
                                modifier = Modifier.size(30.dp)
                            )
                        }
                    },
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            MandalaDecor(
                                size = 36.dp,
                                tint = Color(0xFFD4AF37),
                                alpha = 0.95f
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(
                                    text = "Generations Connect",
                                    fontSize = 20.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onPrimary
                                )
                                Text(
                                    text = currentUser?.let { "${it.displayName} • Senior" } ?: "Eleanor (73) • Senior",
                                    fontSize = 14.sp,
                                    color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.9f)
                                )
                            }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        titleContentColor = MaterialTheme.colorScheme.onPrimary
                    ),
                    actions = {
                        // Voice Mode Toggle Button (Default is ON, user can manually toggle OFF/ON)
                        IconButton(
                            onClick = { viewModel.toggleVoiceMode() },
                            modifier = Modifier.testTag("toggle_voice_mode_btn")
                        ) {
                            Icon(
                                imageVector = if (preferences.voiceModeEnabled) Icons.Default.VolumeUp else Icons.Default.VolumeOff,
                                contentDescription = if (preferences.voiceModeEnabled) "Voice Mode ON (Tap to mute)" else "Voice Mode OFF (Tap to enable)",
                                tint = if (preferences.voiceModeEnabled) Color(0xFFD4AF37) else MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.6f),
                                modifier = Modifier.size(28.dp)
                            )
                        }

                        // High Contrast Toggle
                        IconButton(
                            onClick = { viewModel.toggleHighContrast() },
                            modifier = Modifier.testTag("toggle_contrast")
                        ) {
                            Icon(
                                imageVector = Icons.Default.Contrast,
                                contentDescription = "Toggle High Contrast",
                                tint = MaterialTheme.colorScheme.onPrimary,
                                modifier = Modifier.size(26.dp)
                            )
                        }

                        // Colour palette picker. (The old top-bar Log Off icon duplicated the
                        // "Log Off" shortcut tile on the Home screen, so it was removed.)
                        com.example.ui.components.PalettePickerButton(
                            current = palette,
                            onSelect = { viewModel.setPalette(it) },
                            tint = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                )
            }
            // NO bottomBar! Fixed bottom buttons have been completely removed as requested.
        ) { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                // Main screen scrollable content
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .widthIn(max = maxWidthConstraint)
                        .align(Alignment.TopCenter)
                ) {
                    when (selectedTab) {
                        0 -> SeniorHomeScreen(
                            viewModel = viewModel,
                            onNavigateTab = { selectedTab = it },
                            onLogOff = {
                                viewModel.logOff()
                                onSwitchProfile()
                            }
                        )
                        1 -> SeniorMedicationsScreen(viewModel = viewModel)
                        2 -> SeniorDiaryScreen(viewModel = viewModel)
                        3 -> SeniorSleepScreen(viewModel = viewModel)
                        4 -> SeniorStoriesScreen(viewModel = viewModel)
                        5 -> SeniorGamesScreen(viewModel = viewModel)
                        6 -> SeniorPhotoStudioScreen(viewModel = viewModel)
                        7 -> SeniorBreathingScreen(viewModel = viewModel)
                        8 -> SeniorMilestonesScreen(viewModel = viewModel, onNavigateTab = { selectedTab = it })
                        9 -> MusicStudioScreen(viewModel = viewModel, onBack = { selectedTab = 0 })
                        10 -> SecuritySettingsSubScreen(viewModel = viewModel, onBack = { selectedTab = 0 })
                        11 -> ParentMainScreen(viewModel = viewModel, onSwitchProfile = { selectedTab = 0 })
                    }
                }

            }
        }
    }
}

@Composable
private fun SecuritySettingsSubScreen(
    viewModel: GenerationsAppViewModel,
    onBack: () -> Unit
) {
    val currentUser by viewModel.currentUser.collectAsState()
    var selectedMethod by remember { androidx.compose.runtime.mutableStateOf("Passcode") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(18.dp)
    ) {
        Text(
            text = "🔒 Mobile Security & Lock Settings",
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF1C271E)
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "Manage your mobile passcode, facial recognition, and screen pattern locks.",
            fontSize = 16.sp,
            color = Color(0xFF4F5E52)
        )

        Spacer(modifier = Modifier.height(18.dp))

        Surface(
            shape = RoundedCornerShape(18.dp),
            color = MaterialTheme.colorScheme.surface,
            border = BorderStroke(2.5.dp, MaterialTheme.colorScheme.outline),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Text(
                    text = "Registered Mobile Account",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF1C271E)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Phone Number: ${currentUser?.mobileNumber ?: "9876543210"}",
                    fontSize = 16.sp,
                    color = Color(0xFF4A6B53),
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = "User: ${currentUser?.displayName ?: "Eleanor Vance"} (${currentUser?.role?.name ?: "SENIOR"})",
                    fontSize = 15.sp,
                    color = Color(0xFF4F5E52)
                )

                Spacer(modifier = Modifier.height(14.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    androidx.compose.material3.OutlinedButton(
                        onClick = { viewModel.logOff() },
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(2.dp, Color(0xFFC86446)),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Log Off", color = Color(0xFFC86446), fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
