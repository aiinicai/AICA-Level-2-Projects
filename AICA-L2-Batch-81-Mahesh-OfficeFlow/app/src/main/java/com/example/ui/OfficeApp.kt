package com.example.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.data.model.PortalIntegration
import com.example.data.model.Project
import com.example.data.model.TaskCategory
import com.example.data.model.TaskItem
import com.example.data.model.TaskStatus
import com.example.data.model.TaxNotification
import com.example.data.model.TaxSeverity
import com.example.data.model.TeamMember
import com.example.ui.components.AddTaxNotificationDialog
import com.example.ui.components.AssignTaskDialog
import com.example.ui.components.ConfigurePortalDialog
import com.example.ui.components.ConvertNoticeToTaskDialog
import com.example.ui.components.CreateProjectDialog
import com.example.ui.components.MemberFormDialog
import com.example.ui.components.OfficeBottomNavigation
import com.example.ui.components.OfficeTopBar
import com.example.ui.components.ProjectDetailBottomSheet
import com.example.ui.components.PushProgressDialog
import com.example.ui.components.PushProjectProgressDialog
import com.example.ui.components.TaskDetailBottomSheet
import com.example.ui.components.TaxDetailBottomSheet
import com.example.ui.screens.CalendarScreen
import com.example.ui.screens.DashboardScreen
import com.example.ui.screens.LoginScreen
import com.example.ui.screens.NotificationsScreen
import com.example.ui.screens.ProjectsScreen
import com.example.ui.screens.SettingsAndPortalsScreen
import com.example.ui.screens.TasksScreen
import com.example.ui.screens.TaxAlertsScreen
import com.example.ui.viewmodel.OfficeViewModel

@Composable
fun OfficeApp(viewModel: OfficeViewModel = viewModel()) {
    val tasks by viewModel.tasks.collectAsState()
    // Role-scoped: Admin/Partner see everything; Manager sees tasks assigned to/by them;
    // Team Member sees only tasks assigned to them. Feed this (not the raw `tasks`) to any
    // screen that renders a task list or task-derived KPIs.
    val visibleTasks by viewModel.visibleTasks.collectAsState()
    val projects by viewModel.projects.collectAsState()
    val teamMembers by viewModel.teamMembers.collectAsState()
    val taxNotifications by viewModel.taxNotifications.collectAsState()
    val activityNotifications by viewModel.activityNotifications.collectAsState()
    val portalIntegrations by viewModel.portalIntegrations.collectAsState()
    val currentUser by viewModel.currentUser.collectAsState()
    val isAuthenticated by viewModel.isAuthenticated.collectAsState()

    val currentScreen by viewModel.currentScreen.collectAsState()
    val selectedCalendarDate by viewModel.selectedCalendarDateMillis.collectAsState()
    val taskStatusFilter by viewModel.taskStatusFilter.collectAsState()
    val taskPriorityFilter by viewModel.taskPriorityFilter.collectAsState()
    val taskCategoryFilter by viewModel.taskCategoryFilter.collectAsState()
    val taskTagFilter by viewModel.taskTagFilter.collectAsState()
    val memberFilterId by viewModel.memberFilterId.collectAsState()
    val onlyMyTasksFilter by viewModel.onlyMyTasksFilter.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val taxDepartmentFilter by viewModel.taxDepartmentFilter.collectAsState()
    val snackbarMessage by viewModel.snackbarMessage.collectAsState()

    val snackbarHostState = remember { SnackbarHostState() }

    // Dialog & Bottom Sheet States
    var showAssignTaskDialog by remember { mutableStateOf(false) }
    var assignTaskInitialDate by remember { mutableStateOf<Long?>(null) }
    var assignTaskInitialCategory by remember { mutableStateOf<TaskCategory?>(null) }

    var taskToPushProgress by remember { mutableStateOf<TaskItem?>(null) }
    var projectToPushProgress by remember { mutableStateOf<Project?>(null) }
    var showCreateProjectDialog by remember { mutableStateOf(false) }
    var showAddTaxNoticeDialog by remember { mutableStateOf(false) }
    var noticeToConvert by remember { mutableStateOf<TaxNotification?>(null) }

    var selectedTaskDetail by remember { mutableStateOf<TaskItem?>(null) }
    var selectedProjectDetail by remember { mutableStateOf<Project?>(null) }
    var selectedTaxDetail by remember { mutableStateOf<TaxNotification?>(null) }

    // Team & Portal Management Dialog States
    var showAddMemberDialog by remember { mutableStateOf(false) }
    var memberToEdit by remember { mutableStateOf<TeamMember?>(null) }
    var showAddPortalDialog by remember { mutableStateOf(false) }
    var portalToEdit by remember { mutableStateOf<PortalIntegration?>(null) }

    var showNotificationsOverlay by remember { mutableStateOf(false) }

    val unreadNotifCount = activityNotifications.count { !it.isRead }
    val pendingTasksCount = visibleTasks.count { it.status != TaskStatus.COMPLETED }
    val urgentTaxCount = taxNotifications.count { it.severity == TaxSeverity.CRITICAL_ACTION_REQUIRED }
    val isPartnerOrAdmin = currentUser?.isPartnerOrAdmin ?: true
    val canAssignTasks = viewModel.canAssignTasks()
    val canManageTeam = viewModel.canManageTeam()
    val canViewTeamWorkload = viewModel.canViewTeamWorkload()

    // If not authenticated, show modern Non-SSO Login and User Onboarding screen
    if (!isAuthenticated) {
        LoginScreen(
            teamMembers = teamMembers,
            onLogin = { email, password, callback ->
                viewModel.login(email, password, callback)
            }
        )
        return
    }

    // Auto-redirect away from the Team tab for a plain Team Member (no workload access at all)
    LaunchedEffect(canViewTeamWorkload, currentScreen) {
        if (currentScreen == 5 && !canViewTeamWorkload) {
            viewModel.setScreen(0)
        }
    }

    // Handle Snackbars
    LaunchedEffect(snackbarMessage) {
        snackbarMessage?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearSnackbar()
        }
    }

    val topBarTitle = when (currentScreen) {
        0 -> "OfficeFlow"
        1 -> "Task Assignments"
        2 -> "Projects & Milestones"
        3 -> "Team Calendar"
        4 -> "Statutory Tax Desk"
        5 -> if (canManageTeam) "Portals & Team Admin" else "Team Workload"
        else -> "OfficeFlow"
    }

    val topBarSubtitle = when (currentScreen) {
        0 -> "Dashboard & Team Pulse"
        1 -> "${visibleTasks.size} Total • $pendingTasksCount Open"
        2 -> "${projects.size} Active Projects"
        3 -> "Tracking Team Deadlines"
        4 -> "GST & Income Tax Notices"
        5 -> if (canManageTeam) "${portalIntegrations.size} Portals • ${teamMembers.size} Team Members" else "${teamMembers.size} Team Members • Workload View"
        else -> "Office Management"
    }

    Scaffold(
        topBar = {
            if (!showNotificationsOverlay) {
                OfficeTopBar(
                    title = topBarTitle,
                    subtitle = topBarSubtitle,
                    unreadCount = unreadNotifCount,
                    currentUser = currentUser,
                    teamMembers = teamMembers,
                    onNotificationClick = { showNotificationsOverlay = true },
                    onQuickTaxBroadcast = { showAddTaxNoticeDialog = true },
                    onSignOut = { viewModel.logout() }
                )
            }
        },
        bottomBar = {
            if (!showNotificationsOverlay) {
                OfficeBottomNavigation(
                    selectedScreen = currentScreen,
                    onTabSelected = { viewModel.setScreen(it) },
                    pendingTasksCount = pendingTasksCount,
                    urgentTaxCount = urgentTaxCount,
                    isPartnerOrAdmin = canViewTeamWorkload
                )
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            if (showNotificationsOverlay) {
                NotificationsScreen(
                    notifications = activityNotifications,
                    onMarkAsRead = { viewModel.markActivityAsRead(it) },
                    onMarkAllRead = { viewModel.markAllActivitiesAsRead() },
                    onClearAll = { viewModel.clearAllActivities() },
                    onClose = { showNotificationsOverlay = false }
                )
            } else {
                when (currentScreen) {
                    0 -> DashboardScreen(
                        tasks = visibleTasks,
                        projects = projects,
                        taxNotifications = taxNotifications,
                        recentActivities = activityNotifications,
                        onAssignTaskClick = {
                            assignTaskInitialDate = null
                            assignTaskInitialCategory = null
                            showAssignTaskDialog = true
                        },
                        onPushProjectProgressClick = { projectToPushProgress = it },
                        onPushTaskProgressClick = { taskToPushProgress = it },
                        onTaskClick = { selectedTaskDetail = it },
                        onProjectClick = { selectedProjectDetail = it },
                        onTaxAlertClick = { selectedTaxDetail = it },
                        onBroadcastTaxAlert = { viewModel.broadcastTaxAlert(it) },
                        onNavigateToTasks = { viewModel.setScreen(1) },
                        onNavigateToProjects = { viewModel.setScreen(2) },
                        onNavigateToTaxAlerts = { viewModel.setScreen(4) },
                        onNavigateToCalendar = { viewModel.setScreen(3) },
                        onNavigateToPortalsAndTeam = { viewModel.setScreen(5) },
                        isPartnerOrAdmin = isPartnerOrAdmin,
                        canAssignTasks = canAssignTasks
                    )
                    1 -> TasksScreen(
                        tasks = visibleTasks,
                        teamMembers = teamMembers,
                        currentUser = currentUser,
                        selectedStatusFilter = taskStatusFilter,
                        selectedPriorityFilter = taskPriorityFilter,
                        selectedCategoryFilter = taskCategoryFilter,
                        selectedTagFilter = taskTagFilter,
                        selectedMemberFilterId = memberFilterId,
                        onlyMyTasks = onlyMyTasksFilter,
                        searchQuery = searchQuery,
                        onStatusFilterChange = { viewModel.setTaskStatusFilter(it) },
                        onPriorityFilterChange = { viewModel.setTaskPriorityFilter(it) },
                        onCategoryFilterChange = { viewModel.setTaskCategoryFilter(it) },
                        onTagFilterChange = { viewModel.setTaskTagFilter(it) },
                        onMemberFilterChange = { viewModel.setMemberFilter(it) },
                        onOnlyMyTasksToggle = { viewModel.setOnlyMyTasksFilter(it) },
                        onSearchQueryChange = { viewModel.setSearchQuery(it) },
                        onAssignTaskClick = {
                            assignTaskInitialDate = null
                            assignTaskInitialCategory = null
                            showAssignTaskDialog = true
                        },
                        onTaskClick = { selectedTaskDetail = it },
                        onPushProgressClick = { taskToPushProgress = it },
                        onStatusChangeClick = { task, status -> viewModel.updateTaskStatus(task, status) }
                    )
                    2 -> ProjectsScreen(
                        projects = projects,
                        tasks = tasks,
                        onCreateProjectClick = { showCreateProjectDialog = true },
                        onPushProgressClick = { projectToPushProgress = it },
                        onProjectClick = { selectedProjectDetail = it }
                    )
                    3 -> CalendarScreen(
                        tasks = visibleTasks,
                        projects = projects,
                        taxNotifications = taxNotifications,
                        teamMembers = teamMembers,
                        selectedDateMillis = selectedCalendarDate,
                        onDateSelected = { viewModel.setSelectedCalendarDate(it) },
                        onAssignTaskOnDate = { dateMillis ->
                            assignTaskInitialDate = dateMillis
                            showAssignTaskDialog = true
                        },
                        onTaskClick = { selectedTaskDetail = it },
                        onPushTaskProgressClick = { taskToPushProgress = it },
                        onTaxAlertClick = { selectedTaxDetail = it },
                        canAssignTasks = canAssignTasks
                    )
                    4 -> TaxAlertsScreen(
                        taxNotifications = taxNotifications,
                        selectedDepartmentFilter = taxDepartmentFilter,
                        onDepartmentFilterChange = { viewModel.setTaxDepartmentFilter(it) },
                        onBroadcastAlert = { viewModel.broadcastTaxAlert(it) },
                        onConvertToTask = { noticeToConvert = it },
                        onAddCustomTaxNotice = { showAddTaxNoticeDialog = true },
                        onTaxNoticeClick = { selectedTaxDetail = it }
                    )
                    5 -> {
                        if (canViewTeamWorkload) {
                            // Admin/Partner get full management controls; a Manager gets the
                            // same screen read-only, scoped to workload viewing only.
                            SettingsAndPortalsScreen(
                                teamMembers = teamMembers,
                                portalIntegrations = portalIntegrations,
                                tasks = tasks,
                                currentUser = currentUser,
                                canManageTeam = canManageTeam,
                                onAddTeamMemberClick = { showAddMemberDialog = true },
                                onEditTeamMemberClick = { memberToEdit = it },
                                onUpdateTeamMemberRole = { id, role -> viewModel.updateTeamMemberRole(id, role) },
                                onDeleteTeamMemberClick = { viewModel.deleteTeamMember(it) },
                                onAddPortalClick = { showAddPortalDialog = true },
                                onEditPortalClick = { portalToEdit = it },
                                onTestPortalSync = { viewModel.testPortalSync(it) },
                                onDeletePortalClick = { viewModel.deletePortalIntegration(it) },
                                onResetDatabaseClick = { viewModel.resetDatabaseToDefaults() }
                            )
                        } else {
                            // Team Members never reach screen index 5 (see the LaunchedEffect
                            // redirect above); this is just a safe fallback.
                            DashboardScreen(
                                tasks = visibleTasks,
                                projects = projects,
                                taxNotifications = taxNotifications,
                                recentActivities = activityNotifications,
                                onAssignTaskClick = {
                                    assignTaskInitialDate = null
                                    assignTaskInitialCategory = null
                                    showAssignTaskDialog = true
                                },
                                onPushProjectProgressClick = { projectToPushProgress = it },
                                onPushTaskProgressClick = { taskToPushProgress = it },
                                onTaskClick = { selectedTaskDetail = it },
                                onProjectClick = { selectedProjectDetail = it },
                                onTaxAlertClick = { selectedTaxDetail = it },
                                onBroadcastTaxAlert = { viewModel.broadcastTaxAlert(it) },
                                onNavigateToTasks = { viewModel.setScreen(1) },
                                onNavigateToProjects = { viewModel.setScreen(2) },
                                onNavigateToTaxAlerts = { viewModel.setScreen(4) },
                                onNavigateToCalendar = { viewModel.setScreen(3) },
                                onNavigateToPortalsAndTeam = { viewModel.setScreen(5) },
                                isPartnerOrAdmin = isPartnerOrAdmin,
                                canAssignTasks = canAssignTasks
                            )
                        }
                    }
                }
            }
        }
    }

    // --- Dialogs & Bottom Sheets ---

    // 1. Assign Task Dialog
    if (showAssignTaskDialog) {
        AssignTaskDialog(
            teamMembers = teamMembers,
            projects = projects,
            initialDueDateMillis = assignTaskInitialDate ?: (System.currentTimeMillis() + (3L * 24 * 60 * 60 * 1000)),
            prefilledCategory = assignTaskInitialCategory,
            assignedBy = currentUser?.name ?: "Mahesh",
            onDismiss = { showAssignTaskDialog = false },
            onAssignTask = { title, desc, member, proj, prio, due, cat, checklist, tags, assignedBy ->
                viewModel.assignTask(title, desc, member, proj, prio, due, cat, checklist, tags, assignedBy)
            }
        )
    }

    // 2. Push Task Progress Dialog
    taskToPushProgress?.let { task ->
        PushProgressDialog(
            task = task,
            defaultActorName = currentUser?.name,
            onDismiss = { taskToPushProgress = null },
            onPushProgress = { progress, remark, status, completedCount, actorName ->
                viewModel.pushTaskProgress(
                    taskId = task.id,
                    progressPercentage = progress,
                    remark = remark,
                    status = status,
                    completedCount = completedCount,
                    actorName = actorName
                )
            }
        )
    }

    // 3. Push Project Progress Dialog
    projectToPushProgress?.let { proj ->
        PushProjectProgressDialog(
            project = proj,
            defaultActorName = currentUser?.name,
            onDismiss = { projectToPushProgress = null },
            onPushProgress = { newProgress, remark, actorName ->
                viewModel.pushProjectProgress(
                    projectId = proj.id,
                    progressPercentage = newProgress,
                    remark = remark,
                    actorName = actorName
                )
            }
        )
    }

    // 4. Create Project Dialog
    if (showCreateProjectDialog) {
        CreateProjectDialog(
            teamMembers = teamMembers,
            onDismiss = { showCreateProjectDialog = false },
            onCreateProject = { name, code, client, desc, lead, targetDate, cat, colorHex ->
                viewModel.createProject(name, code, client, desc, lead, targetDate, cat, colorHex)
            }
        )
    }

    // 5. Add Custom Tax Notice Dialog
    if (showAddTaxNoticeDialog) {
        AddTaxNotificationDialog(
            onDismiss = { showAddTaxNoticeDialog = false },
            onBroadcastNotification = { title, dept, circularNo, summary, actions, deadline, severity, source ->
                viewModel.createCustomTaxNotification(title, dept, circularNo, summary, actions, deadline, severity, source)
            }
        )
    }

    // 6. Convert Notice to Task Dialog
    noticeToConvert?.let { notice ->
        ConvertNoticeToTaskDialog(
            notification = notice,
            teamMembers = teamMembers,
            projects = projects,
            onDismiss = { noticeToConvert = null },
            onConvert = { notif, member, proj ->
                viewModel.convertTaxNoticeToTask(notif, member, proj)
            }
        )
    }

    // 7. Add or Edit Team Member Dialog
    if (showAddMemberDialog || memberToEdit != null) {
        MemberFormDialog(
            memberToEdit = memberToEdit,
            onDismiss = {
                showAddMemberDialog = false
                memberToEdit = null
            },
            onSave = { name, role, userRole, dept, email, phone, colorHex, password ->
                if (memberToEdit != null) {
                    val updated = memberToEdit!!.copy(
                        name = name,
                        role = role,
                        userRole = userRole,
                        department = dept,
                        email = email,
                        phone = phone,
                        avatarColorHex = colorHex
                    )
                    viewModel.updateTeamMember(updated)
                } else {
                    viewModel.addTeamMember(name, role, userRole, dept, email, phone, colorHex, password)
                }
                showAddMemberDialog = false
                memberToEdit = null
            }
        )
    }

    // 8. Add or Edit Portal Integration Dialog
    if (showAddPortalDialog || portalToEdit != null) {
        ConfigurePortalDialog(
            portalToEdit = portalToEdit,
            onDismiss = {
                showAddPortalDialog = false
                portalToEdit = null
            },
            onSave = { portal ->
                if (portalToEdit != null) {
                    viewModel.updatePortalIntegration(portal)
                } else {
                    viewModel.addPortalIntegration(portal)
                }
                showAddPortalDialog = false
                portalToEdit = null
            }
        )
    }

    // 9. Task Detail Bottom Sheet
    selectedTaskDetail?.let { task ->
        val latestTask = tasks.find { it.id == task.id } ?: task
        TaskDetailBottomSheet(
            task = latestTask,
            onDismiss = { selectedTaskDetail = null },
            onPushProgressClick = {
                taskToPushProgress = latestTask
            },
            onStatusChange = { newStatus ->
                viewModel.updateTaskStatus(latestTask, newStatus)
            },
            onDeleteTask = {
                viewModel.deleteTask(latestTask)
                selectedTaskDetail = null
            }
        )
    }

    // 10. Project Detail Bottom Sheet
    selectedProjectDetail?.let { proj ->
        val latestProj = projects.find { it.id == proj.id } ?: proj
        val projTasks = tasks.filter { it.projectId == latestProj.id }
        ProjectDetailBottomSheet(
            project = latestProj,
            projectTasks = projTasks,
            onDismiss = { selectedProjectDetail = null },
            onPushProgressClick = {
                projectToPushProgress = latestProj
            },
            onTaskClick = { task ->
                selectedProjectDetail = null
                selectedTaskDetail = task
            }
        )
    }

    // 11. Tax Detail Bottom Sheet
    selectedTaxDetail?.let { notice ->
        val latestNotice = taxNotifications.find { it.id == notice.id } ?: notice
        TaxDetailBottomSheet(
            notification = latestNotice,
            onDismiss = { selectedTaxDetail = null },
            onBroadcastAlert = {
                viewModel.broadcastTaxAlert(latestNotice)
            },
            onConvertToTask = {
                noticeToConvert = latestNotice
            }
        )
    }
}
