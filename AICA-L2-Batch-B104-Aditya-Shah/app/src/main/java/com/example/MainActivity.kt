package com.example

import android.app.Application
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.CompareArrows
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ui.screens.AiAssistantScreen
import com.example.ui.screens.CompareScreen
import com.example.ui.screens.HomeScreen
import com.example.ui.screens.SectionsScreen
import com.example.ui.screens.SourceImportScreen
import com.example.ui.theme.PurpleAi
import com.example.ui.theme.TaxBridgeTheme
import com.example.viewmodel.AppTab
import com.example.viewmodel.TaxBridgeViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            TaxBridgeTheme {
                val context = LocalContext.current
                val application = context.applicationContext as Application
                val viewModel: TaxBridgeViewModel = viewModel(
                    factory = TaxBridgeViewModel.provideFactory(application)
                )
                TaxBridgeApp(viewModel = viewModel)
            }
        }
    }
}

@Composable
fun TaxBridgeApp(
    viewModel: TaxBridgeViewModel
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .testTag("taxbridge_app_root"),
        bottomBar = {
            if (uiState.currentTab != AppTab.SOURCE_IMPORT) {
                NavigationBar(
                    modifier = Modifier
                        .windowInsetsPadding(WindowInsets.navigationBars)
                        .testTag("main_bottom_nav"),
                    containerColor = MaterialTheme.colorScheme.surface,
                    tonalElevation = 8.dp
                ) {
                    // Home Tab
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.HOME,
                        onClick = { viewModel.selectTab(AppTab.HOME) },
                        icon = {
                            Icon(
                                imageVector = Icons.Default.Home,
                                contentDescription = "Home"
                            )
                        },
                        label = {
                            Text(
                                text = "Home",
                                fontSize = 11.sp,
                                fontWeight = if (uiState.currentTab == AppTab.HOME) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        modifier = Modifier.testTag("nav_home"),
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // Sections Tab
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.SECTIONS,
                        onClick = { viewModel.selectTab(AppTab.SECTIONS) },
                        icon = {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.MenuBook,
                                contentDescription = "Sections"
                            )
                        },
                        label = {
                            Text(
                                text = "Sections",
                                fontSize = 11.sp,
                                fontWeight = if (uiState.currentTab == AppTab.SECTIONS) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        modifier = Modifier.testTag("nav_sections"),
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // Compare Tab
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.COMPARE,
                        onClick = { viewModel.selectTab(AppTab.COMPARE) },
                        icon = {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.CompareArrows,
                                contentDescription = "Compare"
                            )
                        },
                        label = {
                            Text(
                                text = "Compare",
                                fontSize = 11.sp,
                                fontWeight = if (uiState.currentTab == AppTab.COMPARE) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        modifier = Modifier.testTag("nav_compare"),
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // AI Tab
                    NavigationBarItem(
                        selected = uiState.currentTab == AppTab.AI,
                        onClick = { viewModel.selectTab(AppTab.AI) },
                        icon = {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = "AI Assistant"
                            )
                        },
                        label = {
                            Text(
                                text = "AI",
                                fontSize = 11.sp,
                                fontWeight = if (uiState.currentTab == AppTab.AI) FontWeight.Bold else FontWeight.Normal
                            )
                        },
                        modifier = Modifier.testTag("nav_ai"),
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = PurpleAi,
                            selectedTextColor = PurpleAi,
                            indicatorColor = PurpleAi.copy(alpha = 0.15f)
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (uiState.currentTab) {
                AppTab.HOME -> {
                    HomeScreen(
                        uiState = uiState,
                        onSearchChange = { query -> viewModel.updateSearchQuery(query) },
                        onNavigateTab = { tab -> viewModel.selectTab(tab) },
                        onSelectSection = { section -> viewModel.openSectionDetail(section) }
                    )
                }
                AppTab.SECTIONS -> {
                    SectionsScreen(
                        uiState = uiState,
                        onSearchChange = { query -> viewModel.updateSearchQuery(query) },
                        onCategorySelect = { cat -> viewModel.selectCategoryFilter(cat) },
                        onStatusSelect = { status -> viewModel.selectStatusFilter(status) },
                        onFilterOptionSelect = { option -> viewModel.selectFilterOption(option) },
                        onSelectSection = { section -> viewModel.openSectionDetail(section) },
                        onDetailExplanationModeChange = { mode -> viewModel.setDetailExplanationMode(mode) },
                        onAskInAi = { section -> viewModel.askAboutSectionInAiTab(section) },
                        onCompareSection = { section -> viewModel.compareSectionInCompareTab(section) }
                    )
                }
                AppTab.COMPARE -> {
                    CompareScreen(
                        uiState = uiState,
                        onSelectSection = { section -> viewModel.selectCompareSection(section) },
                        onToggleSideBySide = { isSideBySide -> viewModel.toggleSideBySide(isSideBySide) },
                        onSelectCompareTab = { tab -> viewModel.setCompareTab(tab) },
                        onAskInAi = { section -> viewModel.askAboutSectionInAiTab(section) }
                    )
                }
                AppTab.AI -> {
                    AiAssistantScreen(
                        uiState = uiState,
                        onSendMessage = { preset -> viewModel.sendChatMessage(preset) },
                        onInputChange = { text -> viewModel.updateChatInput(text) },
                        onContextSectionChange = { sec -> viewModel.setAiContextSection(sec) },
                        onExplanationModeChange = { mode -> viewModel.setAiExplanationMode(mode) }
                    )
                }
                AppTab.SOURCE_IMPORT -> {
                    SourceImportScreen(
                        uiState = uiState,
                        onSelectDocument = { doc -> viewModel.selectImportDocument(doc) },
                        onImportClick = { doc -> viewModel.importFromDocument(doc) },
                        onValidateClick = { doc -> viewModel.validateCandidateSections(doc) },
                        onBackClick = { viewModel.selectTab(AppTab.HOME) }
                    )
                }
            }
        }
    }
}
