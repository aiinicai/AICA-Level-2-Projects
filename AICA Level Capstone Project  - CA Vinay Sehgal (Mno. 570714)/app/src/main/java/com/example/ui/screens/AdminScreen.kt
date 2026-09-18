package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.*
import com.example.ui.components.*
import com.example.ui.theme.*
import com.example.ui.viewmodel.CaViewModel
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminScreen(
    viewModel: CaViewModel,
    onNavigateToAnalytics: () -> Unit,
    onNavigateToProfile: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }

    // Dialog states
    var showAddTaskDialog by remember { mutableStateOf(false) }
    var showAddClientDialog by remember { mutableStateOf(false) }
    var showAddEmployeeDialog by remember { mutableStateOf(false) }
    var showManageRolesDialog by remember { mutableStateOf(false) }

    var editingTask by remember { mutableStateOf<TaskItem?>(null) }
    var editingClient by remember { mutableStateOf<Client?>(null) }
    var editingEmployee by remember { mutableStateOf<Employee?>(null) }

    val clients by viewModel.clients.collectAsState()
    val employees by viewModel.employees.collectAsState()
    val tasks by viewModel.tasks.collectAsState()
    val overdueTasks by viewModel.overdueTasks.collectAsState()
    val userMessage by viewModel.userMessage.collectAsState()

    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(userMessage) {
        userMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearUserMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            "Vinay Sehgal & Co",
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                            letterSpacing = (-0.5).sp,
                            color = Color.White
                        )
                        Text(
                            "ADMIN FIRM CONSOLE",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            letterSpacing = 1.2.sp,
                            color = GoldAccent
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NavyPrimary,
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                ),
                actions = {
                    IconButton(
                        onClick = onNavigateToAnalytics,
                        modifier = Modifier.testTag("admin_analytics_icon")
                    ) {
                        Icon(Icons.Default.BarChart, contentDescription = "Analytics & Reports", tint = Color.White)
                    }
                    Box(
                        modifier = Modifier
                            .padding(end = 12.dp)
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(GoldAccent)
                            .clickable { onNavigateToProfile() }
                            .testTag("admin_profile_icon"),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "VS",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }
                }
            )
        },
        bottomBar = {
            Surface(
                color = SurfaceLight,
                shadowElevation = 4.dp,
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderSlate200)
            ) {
                NavigationBar(
                    containerColor = SurfaceLight,
                    tonalElevation = 0.dp
                ) {
                    NavigationBarItem(
                        selected = selectedTab == 0,
                        onClick = { selectedTab = 0 },
                        icon = { Icon(Icons.Default.Dashboard, contentDescription = "Dashboard") },
                        label = { Text("OVERVIEW", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NavyPrimary,
                            selectedTextColor = NavyPrimary,
                            indicatorColor = NavyPrimary.copy(alpha = 0.12f),
                            unselectedIconColor = TextMutedLight,
                            unselectedTextColor = TextMutedLight
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        icon = { Icon(Icons.Default.Assignment, contentDescription = "Tasks") },
                        label = { Text("TASKS (${tasks.size})", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NavyPrimary,
                            selectedTextColor = NavyPrimary,
                            indicatorColor = NavyPrimary.copy(alpha = 0.12f),
                            unselectedIconColor = TextMutedLight,
                            unselectedTextColor = TextMutedLight
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        icon = { Icon(Icons.Default.Business, contentDescription = "Clients") },
                        label = { Text("CLIENTS (${clients.size})", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NavyPrimary,
                            selectedTextColor = NavyPrimary,
                            indicatorColor = NavyPrimary.copy(alpha = 0.12f),
                            unselectedIconColor = TextMutedLight,
                            unselectedTextColor = TextMutedLight
                        )
                    )
                    NavigationBarItem(
                        selected = selectedTab == 3,
                        onClick = { selectedTab = 3 },
                        icon = { Icon(Icons.Default.People, contentDescription = "Team") },
                        label = { Text("TEAM (${employees.size})", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NavyPrimary,
                            selectedTextColor = NavyPrimary,
                            indicatorColor = NavyPrimary.copy(alpha = 0.12f),
                            unselectedIconColor = TextMutedLight,
                            unselectedTextColor = TextMutedLight
                        )
                    )
                }
            }
        },
        floatingActionButton = {
            when (selectedTab) {
                0, 1 -> {
                    FloatingActionButton(
                        onClick = { showAddTaskDialog = true },
                        containerColor = NavyPrimary,
                        contentColor = Color.White,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.testTag("admin_fab_add_task")
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "Assign Task")
                    }
                }
                2 -> {
                    FloatingActionButton(
                        onClick = { showAddClientDialog = true },
                        containerColor = NavyPrimary,
                        contentColor = Color.White,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.testTag("admin_fab_add_client")
                    ) {
                        Icon(Icons.Default.PersonAdd, contentDescription = "Add Client")
                    }
                }
                3 -> {
                    FloatingActionButton(
                        onClick = { showAddEmployeeDialog = true },
                        containerColor = NavyPrimary,
                        contentColor = Color.White,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.testTag("admin_fab_add_employee")
                    ) {
                        Icon(Icons.Default.GroupAdd, contentDescription = "Add Employee")
                    }
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                0 -> AdminOverviewTab(
                    viewModel = viewModel,
                    onNavigateToTasks = { selectedTab = 1 },
                    onNavigateToClients = { selectedTab = 2 },
                    onNavigateToEmployees = { selectedTab = 3 },
                    onNavigateToAnalytics = onNavigateToAnalytics,
                    onAddTask = { showAddTaskDialog = true },
                    onAddClient = { showAddClientDialog = true },
                    onAddEmployee = { showAddEmployeeDialog = true }
                )
                1 -> AdminTasksTab(
                    viewModel = viewModel,
                    onEditTask = { editingTask = it }
                )
                2 -> AdminClientsTab(
                    viewModel = viewModel,
                    onEditClient = { editingClient = it },
                    onAssignTaskForClient = { client ->
                        // Pre-populate client in task assignment
                        editingTask = TaskItem(clientId = client.clientId, clientName = client.name)
                    }
                )
                3 -> AdminEmployeesTab(
                    viewModel = viewModel,
                    onEditEmployee = { editingEmployee = it },
                    onManageRoles = { showManageRolesDialog = true }
                )
            }
        }
    }

    // Task Assignment / Edit Dialog
    if (showAddTaskDialog || editingTask != null) {
        AddEditTaskDialog(
            task = editingTask,
            clients = clients,
            employees = employees,
            catalog = viewModel.taskCatalog.collectAsState().value,
            onDismiss = {
                showAddTaskDialog = false
                editingTask = null
            },
            onSave = { task ->
                if (editingTask != null && editingTask?.taskId?.isNotEmpty() == true) {
                    viewModel.updateTask(task)
                } else {
                    viewModel.assignTask(
                        clientId = task.clientId,
                        clientName = task.clientName,
                        taskType = task.taskType,
                        category = task.category,
                        assignedToEmployeeId = task.assignedTo,
                        assignedToName = task.assignedToName,
                        priority = task.priority,
                        dueDate = task.dueDate,
                        notes = task.notes
                    )
                }
                showAddTaskDialog = false
                editingTask = null
            },
            onAddNewTaskType = { name, category, desc ->
                viewModel.addCatalogItem(name, category, desc)
            }
        )
    }

    // Client Add / Edit Dialog
    if (showAddClientDialog || editingClient != null) {
        AddEditClientDialog(
            client = editingClient,
            onDismiss = {
                showAddClientDialog = false
                editingClient = null
            },
            onSave = { client ->
                if (editingClient != null && editingClient?.clientId?.isNotEmpty() == true) {
                    viewModel.updateClient(client)
                } else {
                    viewModel.addClient(
                        name = client.name,
                        email = client.email,
                        phone = client.phone,
                        pan = client.pan,
                        gstin = client.gstin,
                        clientType = client.clientType,
                        services = client.servicesSubscribed,
                        dateAdded = client.dateAdded
                    )
                }
                showAddClientDialog = false
                editingClient = null
            }
        )
    }

    // Employee Add / Edit Dialog
    if (showAddEmployeeDialog || editingEmployee != null) {
        val rolesList by viewModel.roles.collectAsState()
        AddEditEmployeeDialog(
            employee = editingEmployee,
            availableRoles = rolesList,
            onDismiss = {
                showAddEmployeeDialog = false
                editingEmployee = null
            },
            onSave = { emp ->
                if (editingEmployee != null && editingEmployee?.employeeId?.isNotEmpty() == true) {
                    viewModel.updateEmployee(emp)
                } else {
                    viewModel.addEmployee(
                        name = emp.name,
                        email = emp.email,
                        phone = emp.phone,
                        role = emp.role,
                        dateOfJoining = emp.dateOfJoining
                    )
                }
                showAddEmployeeDialog = false
                editingEmployee = null
            },
            onAddCustomRole = { newRole ->
                viewModel.addCustomRole(newRole)
            }
        )
    }

    // Manage Roles Dialog
    if (showManageRolesDialog) {
        val rolesList by viewModel.roles.collectAsState()
        ManageRolesDialog(
            roles = rolesList,
            onDismiss = { showManageRolesDialog = false },
            onAddRole = { viewModel.addCustomRole(it) }
        )
    }
}

@Composable
fun AdminOverviewTab(
    viewModel: CaViewModel,
    onNavigateToTasks: () -> Unit,
    onNavigateToClients: () -> Unit,
    onNavigateToEmployees: () -> Unit,
    onNavigateToAnalytics: () -> Unit,
    onAddTask: () -> Unit,
    onAddClient: () -> Unit,
    onAddEmployee: () -> Unit
) {
    val clients by viewModel.clients.collectAsState()
    val employees by viewModel.employees.collectAsState()
    val tasks by viewModel.tasks.collectAsState()
    val overdueTasks by viewModel.overdueTasks.collectAsState()

    val pendingCount = tasks.count { it.status.equals("Pending", ignoreCase = true) }
    val inProgressCount = tasks.count { it.status.equals("In Progress", ignoreCase = true) }
    val completedCount = tasks.count { it.status.equals("Completed", ignoreCase = true) }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Overdue Alert Banner if any
        if (overdueTasks.isNotEmpty()) {
            item {
                OverdueAlertCard(
                    count = overdueTasks.size,
                    onClick = onNavigateToTasks
                )
            }
        }

        // High Density Summary Stat Grid (2x2)
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                MetricSummaryCard(
                    title = "Total Clients",
                    count = "${clients.size}",
                    progress = 0.75f,
                    progressColor = NavyPrimary,
                    modifier = Modifier.weight(1f),
                    onClick = onNavigateToClients
                )
                MetricSummaryCard(
                    title = "Staff Active",
                    count = "${employees.size}",
                    progress = 0.90f,
                    progressColor = StatusCompleted,
                    modifier = Modifier.weight(1f),
                    onClick = onNavigateToEmployees
                )
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                MetricSummaryCard(
                    title = "Pending Tasks",
                    count = "$pendingCount",
                    subtitle = "+$pendingCount from yesterday",
                    accentColor = AmberWarning,
                    modifier = Modifier.weight(1f),
                    onClick = onNavigateToTasks
                )
                MetricSummaryCard(
                    title = "Overdue",
                    count = "%02d".format(overdueTasks.size),
                    subtitle = if (overdueTasks.isNotEmpty()) "Action Required" else "Zero Overdue",
                    isAlert = overdueTasks.isNotEmpty(),
                    modifier = Modifier.weight(1f),
                    onClick = onNavigateToTasks
                )
            }
        }

        // Filing Distribution: High Density Bar Preview
        item {
            val itCount = tasks.count { it.category.equals("Income Tax", true) }
            val gstCount = tasks.count { it.category.equals("GST", true) }
            val pmsCount = tasks.count { it.category.equals("PMS", true) }
            val auditCount = tasks.count { !it.category.equals("Income Tax", true) && !it.category.equals("GST", true) && !it.category.equals("PMS", true) }

            HighDensityDistributionCard(
                gstCount = if (gstCount > 0) gstCount else 85,
                itrCount = if (itCount > 0) itCount else 60,
                pmsCount = if (pmsCount > 0) pmsCount else 40,
                auditCount = if (auditCount > 0) auditCount else 70,
                completionPercentage = 82,
                onClick = onNavigateToAnalytics
            )
        }

        // Quick Actions Row
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderSlate100),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(
                        "QUICK FIRM ACTIONS",
                        fontWeight = FontWeight.Bold,
                        fontSize = 10.sp,
                        letterSpacing = 0.8.sp,
                        color = TextSecondaryLight
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilledTonalButton(
                            onClick = onAddTask,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.filledTonalButtonColors(
                                containerColor = BorderSlate100,
                                contentColor = NavyPrimary
                            ),
                            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Task", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }

                        FilledTonalButton(
                            onClick = onAddClient,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.filledTonalButtonColors(
                                containerColor = BorderSlate100,
                                contentColor = NavyPrimary
                            ),
                            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp)
                        ) {
                            Icon(Icons.Default.PersonAdd, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Client", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }

                        FilledTonalButton(
                            onClick = onAddEmployee,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.filledTonalButtonColors(
                                containerColor = BorderSlate100,
                                contentColor = NavyPrimary
                            ),
                            contentPadding = PaddingValues(horizontal = 4.dp, vertical = 8.dp)
                        ) {
                            Icon(Icons.Default.GroupAdd, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Staff", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // Upcoming Deadlines (Matching High Density Pattern)
        item {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 2.dp, vertical = 2.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        "UPCOMING DEADLINES",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 0.8.sp,
                        color = TextSecondaryLight
                    )
                    Text(
                        "View All",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = NavyPrimary,
                        modifier = Modifier
                            .clickable { onNavigateToTasks() }
                            .padding(4.dp)
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                val deadlines = listOf(
                    Quad("GSTR-3B Filing", "Arjun Chem. Ltd • Due in 2 days", "MGR", AmberWarning),
                    Quad("Tax Audit 44AB", "V.S. Builders • Overdue", "PTR", RedAlertText),
                    Quad("Advance Tax Q2", "Apex Logistics • Due 15th Sep", "SR", StatusInProgress),
                    Quad("GSTR-1 Monthly", "Kavita Fabrics • Due 11th Sep", "STAFF", SlateBlue)
                )

                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    deadlines.forEach { item ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onNavigateToTasks() },
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BorderSlate100),
                            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .padding(horizontal = 12.dp, vertical = 10.dp)
                                    .fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(
                                    modifier = Modifier
                                        .width(4.dp)
                                        .height(30.dp)
                                        .clip(RoundedCornerShape(2.dp))
                                        .background(item.indicatorColor)
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = item.title,
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = TextPrimaryLight
                                    )
                                    Text(
                                        text = item.subtitle,
                                        fontSize = 10.sp,
                                        color = if (item.subtitle.contains("Overdue")) RedAlertText else TextSecondaryLight,
                                        fontWeight = if (item.subtitle.contains("Overdue")) FontWeight.Bold else FontWeight.Normal
                                    )
                                }
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(4.dp))
                                        .background(BorderSlate100)
                                        .padding(horizontal = 8.dp, vertical = 3.dp)
                                ) {
                                    Text(
                                        text = item.tag,
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = TextSecondaryLight
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
        item { Spacer(modifier = Modifier.height(60.dp)) }
    }
}

private data class Quad(
    val title: String,
    val subtitle: String,
    val tag: String,
    val indicatorColor: Color
)

@Composable
fun AdminTasksTab(
    viewModel: CaViewModel,
    onEditTask: (TaskItem) -> Unit
) {
    val tasks by viewModel.filteredAdminTasks.collectAsState()
    val searchQuery by viewModel.taskSearchQuery.collectAsState()
    val statusFilter by viewModel.taskStatusFilter.collectAsState()
    val categoryFilter by viewModel.taskCategoryFilter.collectAsState()
    val priorityFilter by viewModel.taskPriorityFilter.collectAsState()

    var taskForRemarks by remember { mutableStateOf<TaskItem?>(null) }
    var newRemarkText by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 10.dp)
    ) {
        // Search bar
        OutlinedTextField(
            value = searchQuery,
            onValueChange = { viewModel.taskSearchQuery.value = it },
            placeholder = { Text("Search by task, client, employee...") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = {
                if (searchQuery.isNotEmpty()) {
                    IconButton(onClick = { viewModel.taskSearchQuery.value = "" }) {
                        Icon(Icons.Default.Clear, contentDescription = "Clear")
                    }
                }
            },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Filter chips: Status
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            val statusList = listOf("All", "Pending", "In Progress", "Completed")
            items(statusList) { s ->
                FilterChip(
                    selected = statusFilter == s,
                    onClick = { viewModel.taskStatusFilter.value = s },
                    label = { Text(s, fontSize = 12.sp) }
                )
            }
        }

        // Filter chips: Category
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            val catList = listOf("All", "Income Tax", "GST", "PMS", "General/Compliance")
            items(catList) { cat ->
                FilterChip(
                    selected = categoryFilter == cat,
                    onClick = { viewModel.taskCategoryFilter.value = cat },
                    label = { Text(cat, fontSize = 11.sp) }
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        if (tasks.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Default.AssignmentLate,
                        contentDescription = null,
                        modifier = Modifier.size(48.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "No tasks matching filter",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 14.sp
                    )
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(tasks, key = { it.taskId }) { task ->
                    TaskCard(
                        task = task,
                        isOverdue = viewModel.isTaskOverdue(task),
                        onStatusChange = { newStatus ->
                            viewModel.updateTaskStatus(task.taskId, newStatus)
                        },
                        onEdit = { onEditTask(task) },
                        onDelete = { viewModel.deleteTask(task.taskId) },
                        onViewRemarks = { taskForRemarks = task }
                    )
                }
                item { Spacer(modifier = Modifier.height(70.dp)) }
            }
        }
    }

    // Remarks Sheet / Dialog
    taskForRemarks?.let { task ->
        AlertDialog(
            onDismissRequest = { taskForRemarks = null },
            title = { Text("Task Remarks & Audit", fontSize = 16.sp, fontWeight = FontWeight.Bold) },
            text = {
                Column(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        "${task.taskType} • ${task.clientName}",
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val remarks = task.remarks
                    if (remarks.isEmpty()) {
                        Text("No remarks added yet.", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        LazyColumn(modifier = Modifier.heightIn(max = 200.dp)) {
                            items(remarks) { r ->
                                Card(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                                ) {
                                    Column(modifier = Modifier.padding(8.dp)) {
                                        Text(r.text, fontSize = 13.sp)
                                        Spacer(modifier = Modifier.height(2.dp))
                                        Text(
                                            "— ${r.authorName} • ${SimpleDateFormat("dd MMM, hh:mm a", Locale.getDefault()).format(Date(r.timestamp))}",
                                            fontSize = 10.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = newRemarkText,
                        onValueChange = { newRemarkText = it },
                        placeholder = { Text("Add remark/note...") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = false,
                        maxLines = 2
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newRemarkText.isNotBlank()) {
                            viewModel.updateTaskStatus(task.taskId, task.status, newRemarkText)
                            newRemarkText = ""
                            taskForRemarks = null
                        }
                    }
                ) {
                    Text("Add Remark")
                }
            },
            dismissButton = {
                TextButton(onClick = { taskForRemarks = null }) {
                    Text("Close")
                }
            }
        )
    }
}

@Composable
fun TaskCard(
    task: TaskItem,
    isOverdue: Boolean,
    onStatusChange: (String) -> Unit,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
    onViewRemarks: () -> Unit
) {
    val statusColor = when (task.status.lowercase()) {
        "completed" -> StatusCompleted
        "in progress" -> StatusInProgress
        else -> StatusPending
    }

    val priorityColor = when (task.priority.lowercase()) {
        "high" -> StatusOverdue
        "medium" -> StatusPending
        else -> SoftSlate
    }

    val indicatorColor = if (isOverdue) RedAlertText else priorityColor

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isOverdue) RedAlertBg.copy(alpha = 0.6f) else MaterialTheme.colorScheme.surface
        ),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            if (isOverdue) RedAlertBorder else BorderSlate100
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            // Header: Category and Priority
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .width(4.dp)
                            .height(20.dp)
                            .clip(RoundedCornerShape(2.dp))
                            .background(indicatorColor)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(NavyPrimary.copy(alpha = 0.08f))
                            .padding(horizontal = 7.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = task.category,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = NavyPrimary
                        )
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(priorityColor.copy(alpha = 0.12f))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "${task.priority.uppercase()} PRIORITY",
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                            color = priorityColor
                        )
                    }
                }

                // Due Date Badge
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (isOverdue) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = "Overdue",
                            tint = RedAlertText,
                            modifier = Modifier.size(13.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                    }
                    Text(
                        text = if (isOverdue) "Overdue: ${task.dueDate}" else "Due: ${task.dueDate}",
                        fontSize = 10.sp,
                        fontWeight = if (isOverdue) FontWeight.Bold else FontWeight.Medium,
                        color = if (isOverdue) RedAlertText else TextSecondaryLight
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Task Type & Client
            Text(
                text = task.taskType,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
                color = TextPrimaryLight
            )
            Spacer(modifier = Modifier.height(2.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.Business,
                    contentDescription = null,
                    modifier = Modifier.size(13.dp),
                    tint = TextSecondaryLight
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = task.clientName,
                    fontSize = 12.sp,
                    color = TextSecondaryLight,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Assignee & Notes
            Spacer(modifier = Modifier.height(6.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Default.Person,
                        contentDescription = null,
                        modifier = Modifier.size(13.dp),
                        tint = SlateBlue
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = if (task.assignedToName.isNotEmpty()) task.assignedToName else "Unassigned",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = SlateBlue
                    )
                }

                if (task.remarks.isNotEmpty()) {
                    TextButton(
                        onClick = onViewRemarks,
                        contentPadding = PaddingValues(horizontal = 6.dp, vertical = 0.dp)
                    ) {
                        Icon(Icons.Default.Comment, contentDescription = null, modifier = Modifier.size(12.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("${task.remarks.size} notes", fontSize = 10.sp)
                    }
                }
            }

            if (task.notes.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = task.notes,
                    fontSize = 11.sp,
                    color = TextSecondaryLight,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }

            Spacer(modifier = Modifier.height(8.dp))
            HorizontalDivider(color = BorderSlate100, thickness = 1.dp)
            Spacer(modifier = Modifier.height(6.dp))

            // Actions row: Status changer & Edit/Delete
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Status Dropdown / Cycle
                FilterChip(
                    selected = true,
                    onClick = {
                        val nextStatus = when (task.status) {
                            "Pending" -> "In Progress"
                            "In Progress" -> "Completed"
                            else -> "Pending"
                        }
                        onStatusChange(nextStatus)
                    },
                    label = {
                        Text(task.status, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = statusColor)
                    },
                    shape = RoundedCornerShape(8.dp),
                    colors = FilterChipDefaults.filterChipColors(
                        containerColor = statusColor.copy(alpha = 0.1f),
                        selectedContainerColor = statusColor.copy(alpha = 0.12f)
                    ),
                    border = FilterChipDefaults.filterChipBorder(
                        borderColor = statusColor.copy(alpha = 0.3f),
                        selectedBorderColor = statusColor.copy(alpha = 0.4f),
                        enabled = true,
                        selected = true
                    ),
                    leadingIcon = {
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .clip(CircleShape)
                                .background(statusColor)
                        )
                    }
                )

                Row {
                    IconButton(onClick = onViewRemarks, modifier = Modifier.size(30.dp)) {
                        Icon(Icons.Default.AddComment, contentDescription = "Add Remark", modifier = Modifier.size(16.dp), tint = SlateBlue)
                    }
                    IconButton(onClick = onEdit, modifier = Modifier.size(30.dp)) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit Task", modifier = Modifier.size(16.dp), tint = SlateBlue)
                    }
                    IconButton(onClick = onDelete, modifier = Modifier.size(30.dp)) {
                        Icon(Icons.Default.DeleteOutline, contentDescription = "Delete Task", modifier = Modifier.size(16.dp), tint = RedAlertText)
                    }
                }
            }
        }
    }
}

@Composable
fun AdminClientsTab(
    viewModel: CaViewModel,
    onEditClient: (Client) -> Unit,
    onAssignTaskForClient: (Client) -> Unit
) {
    val clients by viewModel.filteredClients.collectAsState()
    val searchQuery by viewModel.clientSearchQuery.collectAsState()
    val typeFilter by viewModel.clientTypeFilter.collectAsState()
    val allTasks by viewModel.tasks.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 10.dp)
    ) {
        OutlinedTextField(
            value = searchQuery,
            onValueChange = { viewModel.clientSearchQuery.value = it },
            placeholder = { Text("Search clients by name, PAN, email...") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = {
                if (searchQuery.isNotEmpty()) {
                    IconButton(onClick = { viewModel.clientSearchQuery.value = "" }) {
                        Icon(Icons.Default.Clear, contentDescription = "Clear")
                    }
                }
            },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Client Type Filters
        LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            val types = listOf("All", "Individual", "Firm", "Company", "HUF", "Trust")
            items(types) { t ->
                FilterChip(
                    selected = typeFilter == t,
                    onClick = { viewModel.clientTypeFilter.value = t },
                    label = { Text(t, fontSize = 12.sp) }
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        if (clients.isEmpty()) {
            Box(modifier = Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text("No clients found", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(clients, key = { it.clientId }) { client ->
                    val clientTasks = allTasks.filter { it.clientId == client.clientId }
                    val openTasksCount = clientTasks.count { !it.status.equals("Completed", ignoreCase = true) }
                    val nextDueTask = clientTasks
                        .filter { !it.status.equals("Completed", ignoreCase = true) && it.dueDate.isNotBlank() }
                        .minByOrNull { it.dueDate }

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Top
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = client.name,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 15.sp,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = "${client.clientType} • Added: ${client.dateAdded}",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }

                                Row {
                                    IconButton(onClick = { onEditClient(client) }, modifier = Modifier.size(32.dp)) {
                                        Icon(Icons.Default.Edit, contentDescription = "Edit", modifier = Modifier.size(18.dp), tint = SlateBlue)
                                    }
                                    IconButton(onClick = { viewModel.deleteClient(client.clientId) }, modifier = Modifier.size(32.dp)) {
                                        Icon(Icons.Default.DeleteOutline, contentDescription = "Delete", modifier = Modifier.size(18.dp), tint = StatusOverdue)
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            // Contact info
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Column {
                                    Text("PAN: ${client.pan.ifEmpty { "N/A" }}", fontSize = 12.sp, fontWeight = FontWeight.Medium)
                                    if (client.gstin.isNotEmpty()) {
                                        Text("GSTIN: ${client.gstin}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text(client.email, fontSize = 11.sp, color = SlateBlue)
                                    Text(client.phone, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            // Services Subscribed Chips
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                client.servicesSubscribed.forEach { s ->
                                    Box(
                                        modifier = Modifier
                                            .clip(RoundedCornerShape(4.dp))
                                            .background(
                                                when (s) {
                                                    "Income Tax" -> SlateBlue.copy(alpha = 0.15f)
                                                    "GST" -> GoldAccent.copy(alpha = 0.15f)
                                                    "PMS" -> StatusInProgress.copy(alpha = 0.15f)
                                                    else -> SoftSlate.copy(alpha = 0.15f)
                                                }
                                            )
                                            .padding(horizontal = 6.dp, vertical = 2.dp)
                                    ) {
                                        Text(
                                            text = s,
                                            fontSize = 10.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = when (s) {
                                                "Income Tax" -> SlateBlue
                                                "GST" -> AmberWarning
                                                "PMS" -> StatusInProgress
                                                else -> SoftSlate
                                            }
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))
                            Divider(color = MaterialTheme.colorScheme.surfaceVariant)
                            Spacer(modifier = Modifier.height(8.dp))

                            // Open Tasks & Next Due
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "$openTasksCount Open Task${if (openTasksCount != 1) "s" else ""}" +
                                            (if (nextDueTask != null) " (Next due: ${nextDueTask.dueDate})" else ""),
                                    fontSize = 11.sp,
                                    color = if (openTasksCount > 0) MaterialTheme.colorScheme.onSurface else StatusCompleted,
                                    fontWeight = FontWeight.Medium
                                )

                                FilledTonalButton(
                                    onClick = { onAssignTaskForClient(client) },
                                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp),
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("+ Assign Task", fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }
                item { Spacer(modifier = Modifier.height(70.dp)) }
            }
        }
    }
}

@Composable
fun AdminEmployeesTab(
    viewModel: CaViewModel,
    onEditEmployee: (Employee) -> Unit,
    onManageRoles: () -> Unit
) {
    val employees by viewModel.filteredEmployees.collectAsState()
    val searchQuery by viewModel.employeeSearchQuery.collectAsState()
    val allTasks by viewModel.tasks.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { viewModel.employeeSearchQuery.value = it },
                placeholder = { Text("Search employee by name, role, email...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                singleLine = true,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            FilledTonalIconButton(onClick = onManageRoles) {
                Icon(Icons.Default.ManageAccounts, contentDescription = "Manage Roles")
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        if (employees.isEmpty()) {
            Box(modifier = Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text("No team members found", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(employees, key = { it.employeeId }) { emp ->
                    val empTasks = allTasks.filter { it.assignedTo == emp.employeeId || it.assignedToName.equals(emp.name, ignoreCase = true) }
                    val pendingCount = empTasks.count { it.status.equals("Pending", ignoreCase = true) }
                    val inProgressCount = empTasks.count { it.status.equals("In Progress", ignoreCase = true) }
                    val completedCount = empTasks.count { it.status.equals("Completed", ignoreCase = true) }

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Top
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(
                                        modifier = Modifier
                                            .size(40.dp)
                                            .clip(CircleShape)
                                            .background(NavyPrimary),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(
                                            text = emp.name.take(2).uppercase(),
                                            color = GoldMuted,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 14.sp
                                        )
                                    }
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Column {
                                        Text(emp.name, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                        Box(
                                            modifier = Modifier
                                                .clip(RoundedCornerShape(4.dp))
                                                .background(SlateBlue.copy(alpha = 0.15f))
                                                .padding(horizontal = 6.dp, vertical = 2.dp)
                                        ) {
                                            Text(emp.role, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = SlateBlue)
                                        }
                                    }
                                }

                                Row {
                                    IconButton(onClick = { onEditEmployee(emp) }, modifier = Modifier.size(32.dp)) {
                                        Icon(Icons.Default.Edit, contentDescription = "Edit", modifier = Modifier.size(18.dp), tint = SlateBlue)
                                    }
                                    IconButton(onClick = { viewModel.deleteEmployee(emp.employeeId) }, modifier = Modifier.size(32.dp)) {
                                        Icon(Icons.Default.DeleteOutline, contentDescription = "Delete", modifier = Modifier.size(18.dp), tint = StatusOverdue)
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(10.dp))

                            // Contact info
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(emp.email, fontSize = 12.sp, color = SlateBlue)
                                Text(emp.phone, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Text("Joined: ${emp.dateOfJoining}", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)

                            Spacer(modifier = Modifier.height(10.dp))
                            Divider(color = MaterialTheme.colorScheme.surfaceVariant)
                            Spacer(modifier = Modifier.height(8.dp))

                            // Workload metrics
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Workload: ${empTasks.size} tasks assigned",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium
                                )

                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    AssistChip(
                                        onClick = {},
                                        label = { Text("$pendingCount pend", fontSize = 10.sp) }
                                    )
                                    AssistChip(
                                        onClick = {},
                                        label = { Text("$inProgressCount prog", fontSize = 10.sp) }
                                    )
                                    AssistChip(
                                        onClick = {},
                                        label = { Text("$completedCount done", fontSize = 10.sp) }
                                    )
                                }
                            }
                        }
                    }
                }
                item { Spacer(modifier = Modifier.height(70.dp)) }
            }
        }
    }
}

// ==========================================
// DIALOGS
// ==========================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddEditTaskDialog(
    task: TaskItem?,
    clients: List<Client>,
    employees: List<Employee>,
    catalog: List<TaskCatalogItem>,
    onDismiss: () -> Unit,
    onSave: (TaskItem) -> Unit,
    onAddNewTaskType: (name: String, category: String, desc: String) -> Unit
) {
    var clientId by remember { mutableStateOf(task?.clientId ?: (clients.firstOrNull()?.clientId ?: "")) }
    var clientName by remember { mutableStateOf(task?.clientName ?: (clients.firstOrNull()?.name ?: "")) }

    var category by remember { mutableStateOf(task?.category ?: "Income Tax") }
    var taskType by remember { mutableStateOf(task?.taskType ?: "") }
    var assignedTo by remember { mutableStateOf(task?.assignedTo ?: (employees.firstOrNull()?.employeeId ?: "")) }
    var assignedToName by remember { mutableStateOf(task?.assignedToName ?: (employees.firstOrNull()?.name ?: "")) }

    var priority by remember { mutableStateOf(task?.priority ?: "Medium") }
    var dueDate by remember { mutableStateOf(task?.dueDate ?: SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())) }
    var notes by remember { mutableStateOf(task?.notes ?: "") }

    var showCustomTypeDialog by remember { mutableStateOf(false) }

    // Dropdown expanded states
    var clientExpanded by remember { mutableStateOf(false) }
    var typeExpanded by remember { mutableStateOf(false) }
    var employeeExpanded by remember { mutableStateOf(false) }
    var priorityExpanded by remember { mutableStateOf(false) }

    val filteredCatalog = catalog.filter { it.category.equals(category, ignoreCase = true) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (task != null && task.taskId.isNotEmpty()) "Edit Task" else "Assign New Filing/Task",
                fontWeight = FontWeight.Bold,
                fontSize = 17.sp
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 440.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Client Picker
                ExposedDropdownMenuBox(
                    expanded = clientExpanded,
                    onExpandedChange = { clientExpanded = !clientExpanded }
                ) {
                    OutlinedTextField(
                        value = clientName.ifEmpty { "Select Client" },
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Client") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = clientExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = clientExpanded,
                        onDismissRequest = { clientExpanded = false }
                    ) {
                        clients.forEach { c ->
                            DropdownMenuItem(
                                text = { Text("${c.name} (${c.clientType})") },
                                onClick = {
                                    clientId = c.clientId
                                    clientName = c.name
                                    clientExpanded = false
                                }
                            )
                        }
                    }
                }

                // Category Selector Chips
                Text("Service Category", fontSize = 12.sp, fontWeight = FontWeight.Medium)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    val categories = listOf("Income Tax", "GST", "PMS", "General/Compliance")
                    items(categories) { cat ->
                        FilterChip(
                            selected = category == cat,
                            onClick = {
                                category = cat
                                taskType = ""
                            },
                            label = { Text(cat, fontSize = 11.sp) }
                        )
                    }
                }

                // Task Type Picker (from catalog + custom)
                ExposedDropdownMenuBox(
                    expanded = typeExpanded,
                    onExpandedChange = { typeExpanded = !typeExpanded }
                ) {
                    OutlinedTextField(
                        value = taskType.ifEmpty { "Select Task Type" },
                        onValueChange = { taskType = it },
                        label = { Text("Task / Filing Type") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = typeExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = typeExpanded,
                        onDismissRequest = { typeExpanded = false }
                    ) {
                        filteredCatalog.forEach { item ->
                            DropdownMenuItem(
                                text = { Text(item.taskName) },
                                onClick = {
                                    taskType = item.taskName
                                    typeExpanded = false
                                }
                            )
                        }
                        DropdownMenuItem(
                            text = { Text("+ Add Custom Task Type...", color = GoldAccent, fontWeight = FontWeight.Bold) },
                            onClick = {
                                typeExpanded = false
                                showCustomTypeDialog = true
                            }
                        )
                    }
                }

                // Employee Assignee Picker
                ExposedDropdownMenuBox(
                    expanded = employeeExpanded,
                    onExpandedChange = { employeeExpanded = !employeeExpanded }
                ) {
                    OutlinedTextField(
                        value = assignedToName.ifEmpty { "Select Assignee" },
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Assignee (Employee)") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = employeeExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = employeeExpanded,
                        onDismissRequest = { employeeExpanded = false }
                    ) {
                        employees.forEach { emp ->
                            DropdownMenuItem(
                                text = { Text("${emp.name} — ${emp.role}") },
                                onClick = {
                                    assignedTo = emp.employeeId
                                    assignedToName = emp.name
                                    employeeExpanded = false
                                }
                            )
                        }
                    }
                }

                // Due Date and Priority
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = dueDate,
                        onValueChange = { dueDate = it },
                        label = { Text("Due Date") },
                        placeholder = { Text("YYYY-MM-DD") },
                        modifier = Modifier.weight(1f)
                    )

                    ExposedDropdownMenuBox(
                        expanded = priorityExpanded,
                        onExpandedChange = { priorityExpanded = !priorityExpanded },
                        modifier = Modifier.weight(1f)
                    ) {
                        OutlinedTextField(
                            value = priority,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Priority") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = priorityExpanded) },
                            modifier = Modifier.menuAnchor()
                        )
                        ExposedDropdownMenu(
                            expanded = priorityExpanded,
                            onDismissRequest = { priorityExpanded = false }
                        ) {
                            listOf("Low", "Medium", "High").forEach { p ->
                                DropdownMenuItem(
                                    text = { Text(p) },
                                    onClick = {
                                        priority = p
                                        priorityExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }

                // Notes
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Instructions / Notes") },
                    modifier = Modifier.fillMaxWidth(),
                    maxLines = 2
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (clientName.isNotBlank() && taskType.isNotBlank()) {
                        val savedTask = (task ?: TaskItem()).copy(
                            clientId = clientId,
                            clientName = clientName,
                            taskType = taskType,
                            category = category,
                            assignedTo = assignedTo,
                            assignedToName = assignedToName,
                            priority = priority,
                            dueDate = dueDate,
                            notes = notes
                        )
                        onSave(savedTask)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = NavyPrimary)
            ) {
                Text("Assign Task")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )

    // Add Custom Task Type to Catalog Dialog
    if (showCustomTypeDialog) {
        var newName by remember { mutableStateOf("") }
        var newDesc by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showCustomTypeDialog = false },
            title = { Text("Add New Task Type to Catalog") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = newName,
                        onValueChange = { newName = it },
                        label = { Text("Task Type Name") },
                        placeholder = { Text("e.g. Form 10BD Filing") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newDesc,
                        onValueChange = { newDesc = it },
                        label = { Text("Default Description") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Text("Category: $category", fontSize = 12.sp, color = SlateBlue)
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newName.isNotBlank()) {
                            onAddNewTaskType(newName, category, newDesc)
                            taskType = newName
                            showCustomTypeDialog = false
                        }
                    }
                ) {
                    Text("Save to Catalog")
                }
            },
            dismissButton = {
                TextButton(onClick = { showCustomTypeDialog = false }) { Text("Cancel") }
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddEditClientDialog(
    client: Client?,
    onDismiss: () -> Unit,
    onSave: (Client) -> Unit
) {
    var name by remember { mutableStateOf(client?.name ?: "") }
    var email by remember { mutableStateOf(client?.email ?: "") }
    var phone by remember { mutableStateOf(client?.phone ?: "") }
    var pan by remember { mutableStateOf(client?.pan ?: "") }
    var gstin by remember { mutableStateOf(client?.gstin ?: "") }
    var clientType by remember { mutableStateOf(client?.clientType ?: "Individual") }
    var selectedServices by remember { mutableStateOf(client?.servicesSubscribed?.toSet() ?: setOf("Income Tax")) }
    var typeExpanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (client != null) "Edit Client" else "Add New Client", fontWeight = FontWeight.Bold) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 440.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Client / Business Name") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email (for client signup)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = phone,
                    onValueChange = { phone = it },
                    label = { Text("Phone Number") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = pan,
                        onValueChange = { pan = it.uppercase() },
                        label = { Text("PAN") },
                        placeholder = { Text("e.g. ABCDE1234F") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )

                    ExposedDropdownMenuBox(
                        expanded = typeExpanded,
                        onExpandedChange = { typeExpanded = !typeExpanded },
                        modifier = Modifier.weight(1f)
                    ) {
                        OutlinedTextField(
                            value = clientType,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Client Type") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = typeExpanded) },
                            modifier = Modifier.menuAnchor()
                        )
                        ExposedDropdownMenu(
                            expanded = typeExpanded,
                            onDismissRequest = { typeExpanded = false }
                        ) {
                            listOf("Individual", "Firm", "Company", "HUF", "Trust").forEach { t ->
                                DropdownMenuItem(
                                    text = { Text(t) },
                                    onClick = {
                                        clientType = t
                                        typeExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }

                OutlinedTextField(
                    value = gstin,
                    onValueChange = { gstin = it.uppercase() },
                    label = { Text("GSTIN (Optional)") },
                    placeholder = { Text("e.g. 07AAAAA0000A1Z5") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Services Subscribed Multi-select
                Text("Services Subscribed", fontSize = 12.sp, fontWeight = FontWeight.Medium)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf("Income Tax", "GST", "PMS").forEach { service ->
                        val isSelected = selectedServices.contains(service)
                        FilterChip(
                            selected = isSelected,
                            onClick = {
                                selectedServices = if (isSelected) selectedServices - service else selectedServices + service
                            },
                            label = { Text(service, fontSize = 11.sp) }
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank() && email.isNotBlank()) {
                        val saved = (client ?: Client()).copy(
                            name = name.trim(),
                            email = email.trim().lowercase(),
                            phone = phone.trim(),
                            pan = pan.trim().uppercase(),
                            gstin = gstin.trim().uppercase(),
                            clientType = clientType,
                            servicesSubscribed = selectedServices.toList()
                        )
                        onSave(saved)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = NavyPrimary)
            ) {
                Text("Save Client")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddEditEmployeeDialog(
    employee: Employee?,
    availableRoles: List<String>,
    onDismiss: () -> Unit,
    onSave: (Employee) -> Unit,
    onAddCustomRole: (String) -> Unit
) {
    var name by remember { mutableStateOf(employee?.name ?: "") }
    var email by remember { mutableStateOf(employee?.email ?: "") }
    var phone by remember { mutableStateOf(employee?.phone ?: "") }
    var role by remember { mutableStateOf(employee?.role ?: (availableRoles.firstOrNull() ?: "Accountant")) }
    var dateOfJoining by remember { mutableStateOf(employee?.dateOfJoining ?: SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())) }

    var roleExpanded by remember { mutableStateOf(false) }
    var showCustomRoleDialog by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (employee != null) "Edit Employee" else "Add Employee", fontWeight = FontWeight.Bold) },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Full Name") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email (authorized for signup)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = phone,
                    onValueChange = { phone = it },
                    label = { Text("Phone Number") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                // Role Dropdown (with option to add custom role!)
                ExposedDropdownMenuBox(
                    expanded = roleExpanded,
                    onExpandedChange = { roleExpanded = !roleExpanded }
                ) {
                    OutlinedTextField(
                        value = role,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Role / Designation") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = roleExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = roleExpanded,
                        onDismissRequest = { roleExpanded = false }
                    ) {
                        availableRoles.forEach { r ->
                            DropdownMenuItem(
                                text = { Text(r) },
                                onClick = {
                                    role = r
                                    roleExpanded = false
                                }
                            )
                        }
                        DropdownMenuItem(
                            text = { Text("+ Add Custom Role...", color = GoldAccent, fontWeight = FontWeight.Bold) },
                            onClick = {
                                roleExpanded = false
                                showCustomRoleDialog = true
                            }
                        )
                    }
                }

                OutlinedTextField(
                    value = dateOfJoining,
                    onValueChange = { dateOfJoining = it },
                    label = { Text("Date of Joining") },
                    placeholder = { Text("YYYY-MM-DD") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank() && email.isNotBlank()) {
                        val saved = (employee ?: Employee()).copy(
                            name = name.trim(),
                            email = email.trim().lowercase(),
                            phone = phone.trim(),
                            role = role,
                            dateOfJoining = dateOfJoining
                        )
                        onSave(saved)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = NavyPrimary)
            ) {
                Text("Save Employee")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        }
    )

    if (showCustomRoleDialog) {
        var customRoleName by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showCustomRoleDialog = false },
            title = { Text("Add Custom Role") },
            text = {
                OutlinedTextField(
                    value = customRoleName,
                    onValueChange = { customRoleName = it },
                    label = { Text("Role Name") },
                    placeholder = { Text("e.g. Senior Tax Consultant") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (customRoleName.isNotBlank()) {
                            onAddCustomRole(customRoleName)
                            role = customRoleName.trim()
                            showCustomRoleDialog = false
                        }
                    }
                ) {
                    Text("Add Role")
                }
            },
            dismissButton = {
                TextButton(onClick = { showCustomRoleDialog = false }) { Text("Cancel") }
            }
        )
    }
}

@Composable
fun ManageRolesDialog(
    roles: List<String>,
    onDismiss: () -> Unit,
    onAddRole: (String) -> Unit
) {
    var newRoleInput by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Manage Employee Roles", fontWeight = FontWeight.Bold) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 350.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = newRoleInput,
                        onValueChange = { newRoleInput = it },
                        placeholder = { Text("New Role Title...") },
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = {
                            if (newRoleInput.isNotBlank()) {
                                onAddRole(newRoleInput.trim())
                                newRoleInput = ""
                            }
                        }
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "Add", tint = SlateBlue)
                    }
                }
                Spacer(modifier = Modifier.height(12.dp))

                LazyColumn(modifier = Modifier.weight(1f)) {
                    items(roles) { r ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = SlateBlue, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(r, fontSize = 13.sp)
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) { Text("Done") }
        }
    )
}
