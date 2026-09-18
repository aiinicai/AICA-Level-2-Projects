package com.example.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.ui.components.AppLockOverlay
import com.example.ui.viewmodel.LedgerViewModel

enum class NavTab(val title: String, val icon: ImageVector) {
    DASHBOARD("Dashboard", Icons.Default.Dashboard),
    PARTIES("Parties", Icons.Default.People),
    ACCOUNTS("Cash & Bank", Icons.Default.AccountBalance),
    REPORTS("Reports", Icons.Default.ReceiptLong),
    SETTINGS("Settings", Icons.Default.Settings)
}

sealed class ScreenDestination {
    object Main : ScreenDestination()
    data class PartyDetail(val partyId: String) : ScreenDestination()
    data class AddTransaction(val partyId: String?, val isGave: Boolean) : ScreenDestination()
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: LedgerViewModel,
    modifier: Modifier = Modifier
) {
    val isAppLocked by viewModel.isAppLocked.collectAsStateWithLifecycle()
    val activeBusiness by viewModel.activeBusiness.collectAsStateWithLifecycle()

    var selectedTab by remember { mutableStateOf(NavTab.DASHBOARD) }
    var currentDestination by remember { mutableStateOf<ScreenDestination>(ScreenDestination.Main) }

    if (isAppLocked) {
        AppLockOverlay(
            onUnlock = { pin -> viewModel.unlockWithPin(pin) }
        )
        return
    }

    // Handle back button behavior
    BackHandler(enabled = currentDestination !is ScreenDestination.Main || selectedTab != NavTab.DASHBOARD) {
        if (currentDestination !is ScreenDestination.Main) {
            currentDestination = ScreenDestination.Main
        } else if (selectedTab != NavTab.DASHBOARD) {
            selectedTab = NavTab.DASHBOARD
        }
    }

    when (val dest = currentDestination) {
        is ScreenDestination.PartyDetail -> {
            PartyDetailScreen(
                partyId = dest.partyId,
                viewModel = viewModel,
                onNavigateBack = { currentDestination = ScreenDestination.Main },
                onAddTransaction = { pId, isGave ->
                    currentDestination = ScreenDestination.AddTransaction(pId, isGave)
                }
            )
        }
        is ScreenDestination.AddTransaction -> {
            AddTransactionScreen(
                viewModel = viewModel,
                preselectedPartyId = dest.partyId,
                initialIsGave = dest.isGave,
                onNavigateBack = { currentDestination = ScreenDestination.Main }
            )
        }
        is ScreenDestination.Main -> {
            Scaffold(
                topBar = {
                    CenterAlignedTopAppBar(
                        title = {
                            Text(
                                text = "LedgerPro",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.ExtraBold
                            )
                        },
                        actions = {
                            if (viewModel.securityManager.isLockEnabled()) {
                                IconButton(onClick = { viewModel.lockNow() }) {
                                    Icon(Icons.Default.Lock, contentDescription = "Lock App", modifier = Modifier.size(20.dp))
                                }
                            }
                        },
                        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                            containerColor = MaterialTheme.colorScheme.surface
                        )
                    )
                },
                bottomBar = {
                    NavigationBar(
                        tonalElevation = 8.dp
                    ) {
                        NavTab.values().forEach { tab ->
                            NavigationBarItem(
                                selected = selectedTab == tab,
                                onClick = { selectedTab = tab },
                                icon = { Icon(tab.icon, contentDescription = tab.title) },
                                label = { Text(tab.title, fontWeight = if (selectedTab == tab) FontWeight.Bold else FontWeight.Normal) }
                            )
                        }
                    }
                }
            ) { innerPadding ->
                Box(
                    modifier = modifier
                        .fillMaxSize()
                        .padding(innerPadding)
                ) {
                    when (selectedTab) {
                        NavTab.DASHBOARD -> DashboardScreen(
                            viewModel = viewModel,
                            onNavigateToPartyDetail = { pId -> currentDestination = ScreenDestination.PartyDetail(pId) },
                            onNavigateToAddTransaction = { pId, isGave -> currentDestination = ScreenDestination.AddTransaction(pId, isGave) },
                            onNavigateToParties = { selectedTab = NavTab.PARTIES },
                            onNavigateToCashAccounts = { selectedTab = NavTab.ACCOUNTS },
                            onNavigateToReports = { selectedTab = NavTab.REPORTS }
                        )
                        NavTab.PARTIES -> PartiesScreen(
                            viewModel = viewModel,
                            onNavigateToPartyDetail = { pId -> currentDestination = ScreenDestination.PartyDetail(pId) }
                        )
                        NavTab.ACCOUNTS -> CashAccountsScreen(
                            viewModel = viewModel
                        )
                        NavTab.REPORTS -> ReportsScreen(
                            viewModel = viewModel,
                            onNavigateToPartyDetail = { pId -> currentDestination = ScreenDestination.PartyDetail(pId) }
                        )
                        NavTab.SETTINGS -> SettingsScreen(
                            viewModel = viewModel
                        )
                    }
                }
            }
        }
    }
}
