package com.example.ui.screens

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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Assignment
import androidx.compose.material.icons.filled.AssignmentTurnedIn
import androidx.compose.material.icons.filled.Campaign
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ElectricBolt
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material.icons.filled.PendingActions
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.OfficeActivityNotification
import com.example.data.model.Project
import com.example.data.model.TaskItem
import com.example.data.model.TaskStatus
import com.example.data.model.TaxDepartment
import com.example.data.model.TaxNotification
import com.example.data.model.TaxSeverity
import com.example.ui.components.ProjectProgressCard
import com.example.ui.components.TaskCard
import com.example.ui.theme.AmberTax
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary
import com.example.ui.theme.TealSecondary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun DashboardScreen(
    tasks: List<TaskItem>,
    projects: List<Project>,
    taxNotifications: List<TaxNotification>,
    recentActivities: List<OfficeActivityNotification>,
    onAssignTaskClick: () -> Unit,
    onPushProjectProgressClick: (Project) -> Unit,
    onPushTaskProgressClick: (TaskItem) -> Unit,
    onTaskClick: (TaskItem) -> Unit,
    onProjectClick: (Project) -> Unit,
    onTaxAlertClick: (TaxNotification) -> Unit,
    onBroadcastTaxAlert: (TaxNotification) -> Unit,
    onNavigateToTasks: () -> Unit,
    onNavigateToProjects: () -> Unit,
    onNavigateToTaxAlerts: () -> Unit,
    onNavigateToCalendar: () -> Unit,
    onNavigateToPortalsAndTeam: () -> Unit = {},
    isPartnerOrAdmin: Boolean = true,
    canAssignTasks: Boolean = true
) {
    val totalTasks = tasks.size
    val completedTasks = tasks.count { it.status == TaskStatus.COMPLETED }
    val inProgressTasks = tasks.count { it.status == TaskStatus.IN_PROGRESS }
    val inReviewTasks = tasks.count { it.status == TaskStatus.IN_REVIEW }
    val todoTasks = tasks.count { it.status == TaskStatus.TODO }

    val urgentTasks = tasks.filter {
        it.status != TaskStatus.COMPLETED &&
        it.dueDateMillis <= System.currentTimeMillis() + (48L * 60 * 60 * 1000)
    }.take(3)

    val avgProjectProgress = if (projects.isNotEmpty()) {
        projects.map { it.progressPercentage }.average().toInt()
    } else 0

    val urgentTaxAlert = taxNotifications.firstOrNull { it.severity == TaxSeverity.CRITICAL_ACTION_REQUIRED }
        ?: taxNotifications.firstOrNull()

    val dateFormat = SimpleDateFormat("dd MMM", Locale.getDefault())

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("dashboard_screen"),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        // --- 1. Top Executive Banner ---
        item {
            Card(
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color.Transparent),
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("dashboard_header_card")
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(
                            Brush.horizontalGradient(
                                colors = listOf(Color(0xFF3730A3), Color(0xFF4F46E5), Color(0xFF6366F1))
                            )
                        )
                        .padding(18.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "Office Operations & Tax Desk",
                                    color = Color.White.copy(alpha = 0.8f),
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium
                                )
                                Text(
                                    text = "Team Pulse & Progress",
                                    color = Color.White,
                                    fontSize = 20.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }

                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = Color.White.copy(alpha = 0.15f)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.TrendingUp,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.primary,
                                        modifier = Modifier.size(16.dp)
                                    )
                                    Text(
                                        text = "$avgProjectProgress% Avg",
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 12.sp
                                    )
                                }
                            }
                        }

                        // Mini KPI stats in Banner
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            // Active Projects
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = Color.White.copy(alpha = 0.12f),
                                modifier = Modifier.weight(1f)
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text("Active Projects", color = Color.White.copy(alpha = 0.7f), fontSize = 10.sp)
                                    Text("${projects.size}", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                                }
                            }

                            // Pending Tasks
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = Color.White.copy(alpha = 0.12f),
                                modifier = Modifier.weight(1f)
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text("Open Tasks", color = Color.White.copy(alpha = 0.7f), fontSize = 10.sp)
                                    Text("${totalTasks - completedTasks}", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                                }
                            }

                            // Tax Deadlines
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = Color.White.copy(alpha = 0.12f),
                                modifier = Modifier.weight(1f)
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text("Tax Alerts", color = Color.White.copy(alpha = 0.7f), fontSize = 10.sp)
                                    Text("${taxNotifications.size}", color = AmberTax, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }

                        // Quick Action Buttons
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            if (canAssignTasks) {
                                Button(
                                    onClick = onAssignTaskClick,
                                    modifier = Modifier
                                        .weight(1f)
                                        .testTag("dashboard_quick_assign_btn"),
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = MaterialTheme.colorScheme.primary,
                                        contentColor = MaterialTheme.colorScheme.onPrimary
                                    ),
                                    shape = RoundedCornerShape(10.dp)
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Assign Task", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                }
                            }

                            Button(
                                onClick = onNavigateToCalendar,
                                modifier = Modifier
                                    .weight(1f)
                                    .testTag("dashboard_quick_calendar_btn"),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = Color.White.copy(alpha = 0.2f),
                                    contentColor = Color.White
                                ),
                                shape = RoundedCornerShape(10.dp)
                            ) {
                                Icon(Icons.Default.Schedule, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Deadlines", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                            }
                        }
                    }
                }
            }
        }

        // --- 2. Real-Time GST & Income Tax Urgent Alert Strip ---
        if (urgentTaxAlert != null) {
            item {
                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.4f)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onTaxAlertClick(urgentTaxAlert) }
                        .testTag("dashboard_urgent_tax_alert")
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Surface(
                                    shape = RoundedCornerShape(6.dp),
                                    color = AmberTax
                                ) {
                                    Text(
                                        text = if (urgentTaxAlert.department == TaxDepartment.GST) "GST ALERT" else "INCOME TAX ALERT",
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 10.sp,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                                Text(
                                    text = urgentTaxAlert.circularOrNotificationNo,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onTertiaryContainer
                                )
                            }

                            FilledTonalButton(
                                onClick = { onBroadcastTaxAlert(urgentTaxAlert) },
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.filledTonalButtonColors(
                                    containerColor = AmberTax,
                                    contentColor = Color.White
                                ),
                                modifier = Modifier
                                    .height(28.dp)
                                    .testTag("dashboard_broadcast_tax_alert_btn")
                            ) {
                                Icon(Icons.Default.NotificationsActive, contentDescription = null, modifier = Modifier.size(12.dp))
                                Spacer(modifier = Modifier.width(3.dp))
                                Text("Push Alert", fontSize = 10.sp, fontWeight = FontWeight.Bold)
                            }
                        }

                        Text(
                            text = urgentTaxAlert.title,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis
                        )

                        Text(
                            text = "Due: ${dateFormat.format(Date(urgentTaxAlert.deadlineDateMillis))} • ${urgentTaxAlert.sourceAuthority}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onTertiaryContainer
                        )
                    }
                }
            }
        }

        // --- 3. Task Workflow Status Breakdown ---
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Task Progress Overview",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    TextButton(onClick = onNavigateToTasks) {
                        Text("View All ($totalTasks)", fontSize = 12.sp)
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Todo
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surface,
                        tonalElevation = 1.dp,
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("To Do", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("$todoTasks", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
                        }
                    }

                    // In Progress
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surface,
                        tonalElevation = 1.dp,
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("In Progress", fontSize = 11.sp, color = SapphirePrimary)
                            Text("$inProgressTasks", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = SapphirePrimary)
                        }
                    }

                    // In Review
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surface,
                        tonalElevation = 1.dp,
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("Review", fontSize = 11.sp, color = AmberTax)
                            Text("$inReviewTasks", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = AmberTax)
                        }
                    }

                    // Completed
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surface,
                        tonalElevation = 1.dp,
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("Completed", fontSize = 11.sp, color = EmeraldSuccess)
                            Text("$completedTasks", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = EmeraldSuccess)
                        }
                    }
                }
            }
        }

        // --- 4. Active Projects Progress Tracker ---
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Active Projects & Milestones",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    TextButton(onClick = onNavigateToProjects) {
                        Text("All Projects", fontSize = 12.sp)
                    }
                }

                projects.take(2).forEach { project ->
                    val projTasks = tasks.filter { it.projectId == project.id }
                    ProjectProgressCard(
                        project = project,
                        totalTasks = projTasks.size,
                        completedTasks = projTasks.count { it.status == TaskStatus.COMPLETED },
                        onPushProgressClick = { onPushProjectProgressClick(project) },
                        onClick = { onProjectClick(project) }
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                }
            }
        }

        // --- 5. Urgent Team Deadlines (< 48 hrs) ---
        if (urgentTasks.isNotEmpty()) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Icon(Icons.Default.Warning, contentDescription = null, tint = RoseUrgent, modifier = Modifier.size(18.dp))
                            Text(
                                text = "Urgent Deadlines (< 48 Hours)",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold, color = RoseUrgent)
                            )
                        }
                        TextButton(onClick = onNavigateToCalendar) {
                            Text("Calendar", fontSize = 12.sp)
                        }
                    }

                    urgentTasks.forEach { task ->
                        TaskCard(
                            task = task,
                            onClick = { onTaskClick(task) },
                            onPushProgressClick = { onPushTaskProgressClick(task) },
                            onStatusChangeClick = {}
                        )
                    }
                }
            }
        }

        // --- 6. Quick Portal & Team Administration Shortcut Card (Only for Partners and Admins) ---
        if (isPartnerOrAdmin) {
            item {
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onNavigateToPortalsAndTeam() }
                        .testTag("dashboard_portals_admin_shortcut")
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                            Box(
                                modifier = Modifier
                                    .size(40.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Campaign,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(22.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = "Portals & Team Administration",
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                )
                                Text(
                                    text = "Configure GST/IT portals, change member roles & manage roster",
                                    style = MaterialTheme.typography.bodySmall.copy(
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        fontSize = 11.sp
                                    )
                                )
                            }
                        }
                        OutlinedButton(
                            onClick = onNavigateToPortalsAndTeam,
                            shape = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text("Manage", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
                Spacer(modifier = Modifier.height(30.dp))
            }
        } else {
            item {
                Spacer(modifier = Modifier.height(24.dp))
            }
        }
    }
}
