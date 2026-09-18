package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.ui.components.FinPilotBottomNav
import com.example.ui.screens.AiCfoScreen
import com.example.ui.screens.DashboardScreen
import com.example.ui.screens.GoalsScreen
import com.example.ui.screens.NetWorthScreen
import com.example.ui.screens.ReportScreen
import com.example.ui.theme.DarkBackground

@Composable
fun FinPilotApp(
    viewModel: FinPilotViewModel = viewModel()
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    var selectedTab by remember { mutableIntStateOf(0) }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground),
        containerColor = DarkBackground,
        bottomBar = {
            FinPilotBottomNav(
                selectedTab = selectedTab,
                onTabSelected = { selectedTab = it }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(DarkBackground)
        ) {
            when (selectedTab) {
                0 -> DashboardScreen(
                    state = state,
                    onNavigateToTab = { selectedTab = it },
                    onAddAsset = { name, cat, amt, inst -> viewModel.addAsset(name, cat, amt, inst) },
                    onAddGoal = { title, cat, target, current, years -> viewModel.addGoal(title, cat, target, current, years) },
                    onUpdateProfile = { viewModel.updateProfile(it) },
                    onFetchAllDetails = { viewModel.fetchAndSyncAllIndianDetails() }
                )
                1 -> NetWorthScreen(
                    state = state,
                    onAddAsset = { name, cat, amt, inst -> viewModel.addAsset(name, cat, amt, inst) },
                    onDeleteAsset = { viewModel.deleteAsset(it) },
                    onDeleteLiability = { viewModel.deleteLiability(it) }
                )
                2 -> AiCfoScreen(
                    state = state,
                    onSendMessage = { viewModel.sendCfoQuery(it) }
                )
                3 -> GoalsScreen(
                    state = state,
                    onAddGoal = { title, cat, target, current, years -> viewModel.addGoal(title, cat, target, current, years) },
                    onDeleteGoal = { viewModel.deleteGoal(it) }
                )
                4 -> ReportScreen(
                    state = state,
                    onMarkNotificationActioned = { viewModel.markNotificationActioned(it) }
                )
            }
        }
    }
}
