package com.example.ui.components

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.Assignment
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.FolderSpecial
import androidx.compose.material.icons.outlined.AdminPanelSettings
import androidx.compose.material.icons.outlined.Assignment
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Dashboard
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.FolderSpecial
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.AmberTax
import com.example.ui.theme.SapphirePrimary

data class NavTabItem(
    val screenIndex: Int,
    val title: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector,
    val testTag: String,
    val badgeCount: Int = 0
)

@Composable
fun OfficeBottomNavigation(
    selectedScreen: Int,
    onTabSelected: (Int) -> Unit,
    pendingTasksCount: Int = 0,
    urgentTaxCount: Int = 0,
    // Admin & Partner see the full "Portals & Team" admin tab; a Manager sees a
    // read-only "Team Workload" view of the same tab; a Team Member sees neither.
    isPartnerOrAdmin: Boolean = true
) {
    val items = buildList {
        add(
            NavTabItem(
                screenIndex = 0,
                title = "Dashboard",
                selectedIcon = Icons.Filled.Dashboard,
                unselectedIcon = Icons.Outlined.Dashboard,
                testTag = "nav_dashboard"
            )
        )
        add(
            NavTabItem(
                screenIndex = 1,
                title = "Tasks",
                selectedIcon = Icons.Filled.Assignment,
                unselectedIcon = Icons.Outlined.Assignment,
                testTag = "nav_tasks",
                badgeCount = pendingTasksCount
            )
        )
        add(
            NavTabItem(
                screenIndex = 2,
                title = "Projects",
                selectedIcon = Icons.Filled.FolderSpecial,
                unselectedIcon = Icons.Outlined.FolderSpecial,
                testTag = "nav_projects"
            )
        )
        add(
            NavTabItem(
                screenIndex = 3,
                title = "Calendar",
                selectedIcon = Icons.Filled.CalendarMonth,
                unselectedIcon = Icons.Outlined.CalendarMonth,
                testTag = "nav_calendar"
            )
        )
        add(
            NavTabItem(
                screenIndex = 4,
                title = "Tax Alerts",
                selectedIcon = Icons.Filled.Description,
                unselectedIcon = Icons.Outlined.Description,
                testTag = "nav_tax_alerts",
                badgeCount = urgentTaxCount
            )
        )
        if (isPartnerOrAdmin) {
            add(
                NavTabItem(
                    screenIndex = 5,
                    title = "Team",
                    selectedIcon = Icons.Filled.AdminPanelSettings,
                    unselectedIcon = Icons.Outlined.AdminPanelSettings,
                    testTag = "nav_admin_portals"
                )
            )
        }
    }

    NavigationBar(
        modifier = Modifier
            .windowInsetsPadding(WindowInsets.navigationBars)
            .testTag("office_bottom_nav"),
        containerColor = MaterialTheme.colorScheme.surface,
        tonalElevation = 6.dp
    ) {
        items.forEach { item ->
            val isSelected = selectedScreen == item.screenIndex
            NavigationBarItem(
                selected = isSelected,
                onClick = { onTabSelected(item.screenIndex) },
                modifier = Modifier.testTag(item.testTag),
                icon = {
                    BadgedBox(
                        badge = {
                            if (item.badgeCount > 0) {
                                Badge(
                                    containerColor = if (item.screenIndex == 4) AmberTax else MaterialTheme.colorScheme.error,
                                    contentColor = Color.White
                                ) {
                                    Text(
                                        text = if (item.badgeCount > 9) "9+" else item.badgeCount.toString(),
                                        fontSize = 9.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }
                        }
                    ) {
                        Icon(
                            imageVector = if (isSelected) item.selectedIcon else item.unselectedIcon,
                            contentDescription = item.title,
                            modifier = Modifier.size(24.dp)
                        )
                    }
                },
                label = {
                    Text(
                        text = item.title,
                        fontSize = 11.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = SapphirePrimary,
                    selectedTextColor = SapphirePrimary,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            )
        }
    }
}
