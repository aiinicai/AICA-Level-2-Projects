package com.example.ui.screens

import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.NetworkCheck
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Public
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.IntegrationType
import com.example.data.model.PortalIntegration
import com.example.data.model.TaskItem
import com.example.data.model.TeamMember
import com.example.data.model.UserRole
import com.example.ui.theme.AmberTax
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun SettingsAndPortalsScreen(
    teamMembers: List<TeamMember>,
    portalIntegrations: List<PortalIntegration>,
    tasks: List<TaskItem>,
    currentUser: TeamMember?,
    // Admin & Partner get full management controls (add/edit/remove people, portals,
    // system reset). A Manager reaches this same screen read-only, scoped to seeing
    // their team's workload only.
    canManageTeam: Boolean = true,
    onAddTeamMemberClick: () -> Unit,
    onEditTeamMemberClick: (TeamMember) -> Unit,
    onUpdateTeamMemberRole: (memberId: String, newRole: UserRole) -> Unit,
    onDeleteTeamMemberClick: (TeamMember) -> Unit,
    onAddPortalClick: () -> Unit,
    onEditPortalClick: (PortalIntegration) -> Unit,
    onTestPortalSync: (PortalIntegration) -> Unit,
    onDeletePortalClick: (PortalIntegration) -> Unit,
    onResetDatabaseClick: () -> Unit
) {
    // 0: Websites & Portals, 1: People & Roles, 2: System Config.
    // A Manager only ever sees section 1, rendered as a read-only "Team Workload" view.
    var selectedSectionTab by remember { mutableIntStateOf(if (canManageTeam) 0 else 1) }
    val context = LocalContext.current
    var memberToDelete by remember { mutableStateOf<TeamMember?>(null) }
    var portalToDelete by remember { mutableStateOf<PortalIntegration?>(null) }
    var showResetConfirmationDialog by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .testTag("settings_portals_screen")
    ) {
        // Section Tabs (Admin & Partner only — a Manager only has the workload view)
        if (canManageTeam) {
        PrimaryTabRow(
            selectedTabIndex = selectedSectionTab,
            containerColor = MaterialTheme.colorScheme.surface,
            contentColor = MaterialTheme.colorScheme.primary
        ) {
            Tab(
                selected = selectedSectionTab == 0,
                onClick = { selectedSectionTab = 0 },
                text = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Language, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Websites & Portals (${portalIntegrations.size})", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                },
                modifier = Modifier.testTag("tab_portals")
            )
            Tab(
                selected = selectedSectionTab == 1,
                onClick = { selectedSectionTab = 1 },
                text = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Person, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("People & Roles (${teamMembers.size})", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                },
                modifier = Modifier.testTag("tab_people_roles")
            )
            Tab(
                selected = selectedSectionTab == 2,
                onClick = { selectedSectionTab = 2 },
                text = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Config & Reset", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                },
                modifier = Modifier.testTag("tab_system_config")
            )
        }
        }

        when (selectedSectionTab) {
            0 -> {
                // Websites & Portals Integration View
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    item {
                        Card(
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f)
                            ),
                            shape = RoundedCornerShape(14.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = "Official Portals & Webhooks",
                                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                    )
                                    Text(
                                        text = "Direct browser access, real-time gateway pings, and webhook synchronization.",
                                        style = MaterialTheme.typography.bodySmall.copy(
                                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                                            fontSize = 11.sp
                                        )
                                    )
                                }
                                Button(
                                    onClick = onAddPortalClick,
                                    modifier = Modifier.testTag("add_portal_button")
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Connect Portal", fontSize = 12.sp)
                                }
                            }
                        }
                    }

                    items(portalIntegrations, key = { it.id }) { portal ->
                        PortalIntegrationCard(
                            portal = portal,
                            onLaunchUrl = { url ->
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Could not open URL: $url", Toast.LENGTH_SHORT).show()
                                }
                            },
                            onTestSync = { onTestPortalSync(portal) },
                            onEdit = { onEditPortalClick(portal) },
                            onDelete = { portalToDelete = portal }
                        )
                    }

                    item {
                        Spacer(modifier = Modifier.height(40.dp))
                    }
                }
            }

            1 -> {
                // People & Role Administration View
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    item {
                        Card(
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.5f)
                            ),
                            shape = RoundedCornerShape(14.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = if (canManageTeam) "Team Directory & Role Privileges" else "Team Workload",
                                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                    )
                                    Text(
                                        text = if (canManageTeam)
                                            "Modify team profiles, elevate or downgrade roles (Admin, Manager, Member) stored in local Room DB."
                                        else
                                            "Read-only view of your team's current task load. Ask an Admin or Partner for profile or role changes.",
                                        style = MaterialTheme.typography.bodySmall.copy(
                                            color = MaterialTheme.colorScheme.onSecondaryContainer,
                                            fontSize = 11.sp
                                        )
                                    )
                                }
                                if (canManageTeam) {
                                    Button(
                                        onClick = onAddTeamMemberClick,
                                        modifier = Modifier.testTag("add_member_button")
                                    ) {
                                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("Add Person", fontSize = 12.sp)
                                    }
                                }
                            }
                        }
                    }

                    items(teamMembers, key = { it.id }) { member ->
                        val assignedTasks = tasks.filter { it.assignedMemberId == member.id }
                        val activeUser = currentUser?.id == member.id

                        TeamMemberAdminCard(
                            member = member,
                            assignedTasksCount = assignedTasks.size,
                            completedTasksCount = assignedTasks.count { it.status == com.example.data.model.TaskStatus.COMPLETED },
                            isCurrentUser = activeUser,
                            canManageTeam = canManageTeam,
                            onRoleChange = { newRole -> onUpdateTeamMemberRole(member.id, newRole) },
                            onEdit = { onEditTeamMemberClick(member) },
                            onDelete = { memberToDelete = member }
                        )
                    }

                    item {
                        Spacer(modifier = Modifier.height(40.dp))
                    }
                }
            }

            2 -> {
                // System Config & Database Management
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    item {
                        ElevatedCard(shape = RoundedCornerShape(14.dp)) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Shield, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Office System Parameters", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
                                }
                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "• Working Hours: 09:30 AM – 06:30 PM (IST)\n" +
                                            "• Tax Circular Reminder Buffer: 7 Days before filing deadline\n" +
                                            "• Automatic Milestone Broadcast: Enabled\n" +
                                            "• Live Gateway Synchronization: Enabled (HTTP 200 Handshake)\n" +
                                            "• Local Database: Room v3 with persistent encryption & identity sync",
                                    style = MaterialTheme.typography.bodyMedium,
                                    lineHeight = 22.sp
                                )
                            }
                        }
                    }

                    item {
                        OutlinedCard(
                            colors = CardDefaults.outlinedCardColors(
                                containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.25f)
                            ),
                            shape = RoundedCornerShape(14.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(
                                        text = "Reset Database to Demonstration State",
                                        style = MaterialTheme.typography.titleMedium.copy(
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.error
                                        )
                                    )
                                }
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Re-seeds the entire database with standard demonstration team members, active GST/IT projects, tasks, circular alerts, and connected portals.",
                                    style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                                )
                                Spacer(modifier = Modifier.height(14.dp))
                                Button(
                                    onClick = { showResetConfirmationDialog = true },
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = MaterialTheme.colorScheme.error
                                    ),
                                    modifier = Modifier.testTag("reset_db_button")
                                ) {
                                    Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Reset & Re-Seed Workspace Data")
                                }
                            }
                        }
                    }

                    item {
                        Spacer(modifier = Modifier.height(40.dp))
                    }
                }
            }
        }
    }

    // Delete Member Confirmation Dialog
    memberToDelete?.let { member ->
        AlertDialog(
            onDismissRequest = { memberToDelete = null },
            title = { Text("Remove Team Member?") },
            text = { Text("Are you sure you want to remove '${member.name}' (${member.role}) from the team roster?") },
            confirmButton = {
                Button(
                    onClick = {
                        onDeleteTeamMemberClick(member)
                        memberToDelete = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Delete")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { memberToDelete = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Delete Portal Confirmation Dialog
    portalToDelete?.let { portal ->
        AlertDialog(
            onDismissRequest = { portalToDelete = null },
            title = { Text("Remove Portal Integration?") },
            text = { Text("Are you sure you want to disconnect '${portal.name}' (${portal.portalUrl})?") },
            confirmButton = {
                Button(
                    onClick = {
                        onDeletePortalClick(portal)
                        portalToDelete = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Remove")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { portalToDelete = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Database Reset Confirmation Dialog
    if (showResetConfirmationDialog) {
        AlertDialog(
            onDismissRequest = { showResetConfirmationDialog = false },
            title = { Text("Reset Workspace Database?") },
            text = { Text("This will reset all tasks, projects, team rosters, and portals to the fresh initial state. Proceed?") },
            confirmButton = {
                Button(
                    onClick = {
                        onResetDatabaseClick()
                        showResetConfirmationDialog = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Yes, Reset Everything")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showResetConfirmationDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun PortalIntegrationCard(
    portal: PortalIntegration,
    onLaunchUrl: (String) -> Unit,
    onTestSync: () -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    val categoryBadgeColor = try {
        Color(android.graphics.Color.parseColor(portal.type.badgeColor))
    } catch (_: Exception) {
        MaterialTheme.colorScheme.primary
    }

    val syncFormatted = SimpleDateFormat("dd MMM, hh:mm a", Locale.getDefault()).format(Date(portal.lastSyncMillis))

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("portal_card_${portal.id}"),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(14.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.weight(1f)
                ) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(10.dp))
                            .background(categoryBadgeColor.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Public,
                            contentDescription = null,
                            tint = categoryBadgeColor,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = portal.name,
                            style = MaterialTheme.typography.titleMedium.copy(
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                        )
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = categoryBadgeColor.copy(alpha = 0.12f)
                        ) {
                            Text(
                                text = portal.type.displayName,
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = categoryBadgeColor,
                                    fontSize = 9.sp
                                ),
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                            )
                        }
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    IconButton(onClick = onEdit, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit Portal", modifier = Modifier.size(16.dp))
                    }
                    IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete Portal", modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.error)
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = portal.description.ifEmpty { "Connected statutory external portal." },
                style = MaterialTheme.typography.bodySmall.copy(
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 11.sp
                )
            )

            Spacer(modifier = Modifier.height(10.dp))
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Web URL: ", fontWeight = FontWeight.Bold, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(portal.portalUrl, fontSize = 10.sp, maxLines = 1, color = MaterialTheme.colorScheme.primary)
                    }
                    if (portal.webhookUrl.isNotBlank()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Webhook: ", fontWeight = FontWeight.Bold, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(portal.webhookUrl, fontSize = 10.sp, maxLines = 1, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = EmeraldSuccess, modifier = Modifier.size(12.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("${portal.statusText} • Last sync: $syncFormatted", fontSize = 10.sp, color = EmeraldSuccess, fontWeight = FontWeight.Medium)
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { onLaunchUrl(portal.portalUrl) },
                    modifier = Modifier
                        .weight(1f)
                        .testTag("launch_portal_${portal.id}")
                ) {
                    Icon(Icons.Default.OpenInBrowser, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Open Website", fontSize = 11.sp)
                }

                FilledTonalButton(
                    onClick = onTestSync,
                    modifier = Modifier.testTag("test_sync_${portal.id}")
                ) {
                    Icon(Icons.Default.NetworkCheck, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Test Gateway Ping", fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
fun TeamMemberAdminCard(
    member: TeamMember,
    assignedTasksCount: Int,
    completedTasksCount: Int,
    isCurrentUser: Boolean,
    canManageTeam: Boolean = true,
    onRoleChange: (UserRole) -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit
) {
    val roleColor = when (member.userRole) {
        UserRole.ADMIN -> RoseUrgent
        UserRole.PARTNER -> SapphirePrimary
        UserRole.MANAGER -> AmberTax
        UserRole.TEAM_MEMBER -> EmeraldSuccess
    }

    val avatarColor = try {
        Color(android.graphics.Color.parseColor(member.avatarColorHex))
    } catch (_: Exception) {
        MaterialTheme.colorScheme.primary
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag("member_card_${member.id}"),
        colors = CardDefaults.cardColors(
            containerColor = if (isCurrentUser) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.25f) else MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(14.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                    Box(
                        modifier = Modifier
                            .size(42.dp)
                            .clip(CircleShape)
                            .background(avatarColor),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = member.name.take(1),
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = member.name,
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold, fontSize = 14.sp)
                            )
                            if (isCurrentUser) {
                                Spacer(modifier = Modifier.width(6.dp))
                                Surface(
                                    shape = RoundedCornerShape(4.dp),
                                    color = MaterialTheme.colorScheme.primary
                                ) {
                                    Text(
                                        text = "Active You",
                                        color = Color.White,
                                        fontSize = 8.sp,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                    )
                                }
                            }
                        }
                        Text(
                            text = "${member.role} • ${member.department}",
                            style = MaterialTheme.typography.bodySmall.copy(
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 11.sp
                            )
                        )
                    }
                }

                if (canManageTeam) {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        IconButton(onClick = onEdit, modifier = Modifier.size(32.dp)) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit Member", modifier = Modifier.size(16.dp))
                        }
                        IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                            Icon(Icons.Default.Delete, contentDescription = "Delete Member", modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
            if (member.email.isNotBlank() || member.phone.isNotBlank()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    if (member.email.isNotBlank()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Email, contentDescription = null, modifier = Modifier.size(12.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(member.email, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    if (member.phone.isNotBlank()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(12.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(member.phone, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            if (canManageTeam) {
            Spacer(modifier = Modifier.height(10.dp))
            // Live Role Switcher Selector Chips
            Text(
                text = "System Security Role & Permissions",
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
            )
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                UserRole.entries.forEach { userRoleOption ->
                    val isSelected = member.userRole == userRoleOption
                    val optionColor = when (userRoleOption) {
                        UserRole.ADMIN -> RoseUrgent
                        UserRole.PARTNER -> SapphirePrimary
                        UserRole.MANAGER -> AmberTax
                        UserRole.TEAM_MEMBER -> EmeraldSuccess
                    }

                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = if (isSelected) optionColor.copy(alpha = 0.2f) else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                        border = if (isSelected) androidx.compose.foundation.BorderStroke(1.5.dp, optionColor) else null,
                        modifier = Modifier
                            .weight(1f)
                            .clickable { onRoleChange(userRoleOption) }
                            .testTag("set_role_${member.id}_${userRoleOption.name}")
                    ) {
                        Row(
                            modifier = Modifier.padding(vertical = 6.dp, horizontal = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            if (isSelected) {
                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = optionColor, modifier = Modifier.size(12.dp))
                                Spacer(modifier = Modifier.width(3.dp))
                            }
                            Text(
                                text = userRoleOption.displayName,
                                fontSize = 10.sp,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                color = if (isSelected) optionColor else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }
            }

            Spacer(modifier = Modifier.height(10.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "$assignedTasksCount tasks assigned • $completedTasksCount done",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
