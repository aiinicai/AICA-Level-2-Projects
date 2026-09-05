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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.AuditLogEntry
import com.example.data.model.Employee
import com.example.data.model.TaskCatalogItem
import com.example.ui.components.*
import com.example.ui.theme.*
import com.example.ui.viewmodel.CaViewModel
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalyticsScreen(
    viewModel: CaViewModel,
    onBack: () -> Unit
) {
    val employees by viewModel.employees.collectAsState()
    val tasks by viewModel.tasks.collectAsState()
    val clients by viewModel.clients.collectAsState()
    val catalog by viewModel.taskCatalog.collectAsState()
    val auditLogs by viewModel.auditLogs.collectAsState()

    var selectedTab by remember { mutableIntStateOf(0) }
    // 0: Visual Analytics & Trends, 1: Team Workload Drilldown, 2: Task Catalog Manager, 3: Security Audit Log

    var showAddCatalogDialog by remember { mutableStateOf(false) }

    Scaffold(
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
                            "FIRM ANALYTICS & GOVERNANCE",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            letterSpacing = 1.2.sp,
                            color = GoldAccent
                        )
                    }
                },
                navigationIcon = {
                    IconButton(
                        onClick = onBack,
                        modifier = Modifier.testTag("analytics_back_button")
                    ) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NavyPrimary)
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Scrollable Tab bar
            ScrollableTabRow(
                selectedTabIndex = selectedTab,
                containerColor = SurfaceLight,
                contentColor = NavyPrimary,
                edgePadding = 16.dp
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("CHARTS", fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("WORKLOAD", fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) }
                )
                Tab(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    text = { Text("CATALOG (${catalog.size})", fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) }
                )
                Tab(
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 },
                    text = { Text("AUDIT (${auditLogs.size})", fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) }
                )
            }

            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                when (selectedTab) {
                    0 -> ChartsView(employees, tasks, clients)
                    1 -> TeamDrillDownView(employees, tasks)
                    2 -> CatalogManagerView(catalog, onAddItem = { showAddCatalogDialog = true }, onDeleteItem = { viewModel.deleteCatalogItem(it) })
                    3 -> AuditLogsView(auditLogs)
                }
            }
        }
    }

    if (showAddCatalogDialog) {
        var name by remember { mutableStateOf("") }
        var category by remember { mutableStateOf("Income Tax") }
        var desc by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showAddCatalogDialog = false },
            title = { Text("Add New Catalog Item", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Task Name") },
                        placeholder = { Text("e.g. Form 10BD Annual Donation Filing") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Text("Category", fontSize = 12.sp, fontWeight = FontWeight.Medium)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        val cats = listOf("Income Tax", "GST", "PMS", "General/Compliance")
                        items(cats) { c ->
                            FilterChip(
                                selected = category == c,
                                onClick = { category = c },
                                label = { Text(c, fontSize = 11.sp) }
                            )
                        }
                    }

                    OutlinedTextField(
                        value = desc,
                        onValueChange = { desc = it },
                        label = { Text("Default Description / Steps") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 3
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (name.isNotBlank()) {
                            viewModel.addCatalogItem(name, category, desc)
                            showAddCatalogDialog = false
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = NavyPrimary)
                ) {
                    Text("Add to Catalog")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddCatalogDialog = false }) { Text("Cancel") }
            }
        )
    }
}

@Composable
fun ChartsView(
    employees: List<Employee>,
    tasks: List<com.example.data.model.TaskItem>,
    clients: List<com.example.data.model.Client>
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. Monthly Filing Trend Line Chart
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "Monthly Filing Completion Trend",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(GoldAccent.copy(alpha = 0.15f))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text("CY 2026", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = AmberWarning)
                        }
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        "Total filings completed per month across Income Tax, GST, and PMS",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    val trendPoints = listOf(
                        "Apr" to 14,
                        "May" to 22,
                        "Jun" to 38,
                        "Jul" to 65,
                        "Aug" to 42,
                        "Sep" to 58
                    )
                    TrendLineChart(points = trendPoints)
                }
            }
        }

        // 2. Status Breakdown Donut Chart
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Task Status Distribution",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val pending = tasks.count { it.status.equals("Pending", true) }
                    val inProg = tasks.count { it.status.equals("In Progress", true) }
                    val done = tasks.count { it.status.equals("Completed", true) }

                    val statusSlices = listOf(
                        DonutSliceData("Pending", pending.toFloat(), StatusPending),
                        DonutSliceData("In Progress", inProg.toFloat(), StatusInProgress),
                        DonutSliceData("Completed", done.toFloat(), StatusCompleted)
                    ).filter { it.value > 0 }

                    DonutPieChart(
                        slices = statusSlices,
                        centerTitle = "Total",
                        centerSubtitle = "${tasks.size}"
                    )
                }
            }
        }

        // 3. Category Breakdown Donut Chart
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Category Distribution",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val itCount = tasks.count { it.category.equals("Income Tax", true) }
                    val gstCount = tasks.count { it.category.equals("GST", true) }
                    val pmsCount = tasks.count { it.category.equals("PMS", true) }
                    val genCount = tasks.count { !it.category.equals("Income Tax", true) && !it.category.equals("GST", true) && !it.category.equals("PMS", true) }

                    val catSlices = listOf(
                        DonutSliceData("Income Tax", itCount.toFloat(), SlateBlue),
                        DonutSliceData("GST", gstCount.toFloat(), GoldAccent),
                        DonutSliceData("PMS", pmsCount.toFloat(), StatusInProgress),
                        DonutSliceData("General", genCount.toFloat(), SoftSlate)
                    ).filter { it.value > 0 }

                    DonutPieChart(
                        slices = catSlices,
                        centerTitle = "Total",
                        centerSubtitle = "${tasks.size}"
                    )
                }
            }
        }

        // 4. Client-Wise Summary Card
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Client-Wise Task Overview",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    clients.forEach { client ->
                        val clientTasks = tasks.filter { it.clientId == client.clientId }
                        val open = clientTasks.count { !it.status.equals("Completed", true) }
                        val next = clientTasks.filter { !it.status.equals("Completed", true) && it.dueDate.isNotBlank() }.minByOrNull { it.dueDate }

                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(client.name, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                                Text(
                                    if (next != null) "Next Due: ${next.dueDate} (${next.taskType})" else "All caught up",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(if (open > 0) StatusPending.copy(alpha = 0.15f) else StatusCompleted.copy(alpha = 0.15f))
                                    .padding(horizontal = 8.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    "$open open",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (open > 0) AmberWarning else StatusCompleted
                                )
                            }
                        }
                        Divider(color = MaterialTheme.colorScheme.surfaceVariant)
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(40.dp)) }
    }
}

@Composable
fun TeamDrillDownView(
    employees: List<Employee>,
    tasks: List<com.example.data.model.TaskItem>
) {
    var selectedEmployeeForDrilldown by remember { mutableStateOf<Employee?>(null) }

    val barData = employees.map { emp ->
        val empTasks = tasks.filter { it.assignedTo == emp.employeeId || it.assignedToName.equals(emp.name, true) }
        val assigned = empTasks.size
        val completed = empTasks.count { it.status.equals("Completed", true) }
        BarGroupData(emp.name, assigned, completed)
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Employee Workload Comparison",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Text(
                        "Tap any employee to drill down into their task list",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(modifier = Modifier.height(14.dp))

                    InteractiveBarChart(
                        data = barData,
                        onBarClick = { group ->
                            selectedEmployeeForDrilldown = employees.firstOrNull { it.name == group.label }
                        }
                    )
                }
            }
        }

        item {
            Text(
                text = if (selectedEmployeeForDrilldown != null)
                    "Tasks Assigned to ${selectedEmployeeForDrilldown?.name} (${selectedEmployeeForDrilldown?.role})"
                else "Select an employee above to inspect their task list",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
        }

        if (selectedEmployeeForDrilldown != null) {
            val empTasks = tasks.filter {
                it.assignedTo == selectedEmployeeForDrilldown?.employeeId ||
                it.assignedToName.equals(selectedEmployeeForDrilldown?.name, true)
            }

            if (empTasks.isEmpty()) {
                item {
                    Text("No tasks currently assigned to this member.", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
                }
            } else {
                items(empTasks) { t ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(t.taskType, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                Text("Client: ${t.clientName} • Due: ${t.dueDate}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Text(
                                t.status,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = when (t.status.lowercase()) {
                                    "completed" -> StatusCompleted
                                    "in progress" -> StatusInProgress
                                    else -> StatusPending
                                }
                            )
                        }
                    }
                }
            }
        }

        item { Spacer(modifier = Modifier.height(40.dp)) }
    }
}

@Composable
fun CatalogManagerView(
    catalog: List<TaskCatalogItem>,
    onAddItem: () -> Unit,
    onDeleteItem: (String) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    "Default Task Catalog",
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
                Text(
                    "Standard services for Income Tax, GST, PMS, Compliance",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            FilledTonalButton(
                onClick = onAddItem,
                shape = RoundedCornerShape(8.dp)
            ) {
                Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("+ New Service", fontSize = 11.sp)
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        val grouped = catalog.groupBy { it.category }

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            grouped.forEach { (category, items) ->
                item {
                    Text(
                        text = category.uppercase(),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = SlateBlue,
                        letterSpacing = 1.sp
                    )
                }
                items(items, key = { it.taskId }) { item ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(item.taskName, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                if (item.defaultDescription.isNotEmpty()) {
                                    Text(item.defaultDescription, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                            IconButton(onClick = { onDeleteItem(item.taskId) }) {
                                Icon(Icons.Default.DeleteOutline, contentDescription = "Delete", tint = StatusOverdue, modifier = Modifier.size(18.dp))
                            }
                        }
                    }
                }
            }
            item { Spacer(modifier = Modifier.height(40.dp)) }
        }
    }
}

@Composable
fun AuditLogsView(logs: List<AuditLogEntry>) {
    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            "Firm Security Audit Trail",
            fontWeight = FontWeight.Bold,
            fontSize = 15.sp
        )
        Text(
            "Real-time records of authentication, registrations, and administrative actions",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(10.dp))

        if (logs.isEmpty()) {
            Box(modifier = Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.Center) {
                Text("No security audit logs yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(logs, key = { it.logId }) { entry ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(
                                        modifier = Modifier
                                            .size(8.dp)
                                            .clip(CircleShape)
                                            .background(NavyPrimary)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(entry.action, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                }
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(4.dp))
                                        .background(SlateBlue.copy(alpha = 0.1f))
                                        .padding(horizontal = 6.dp, vertical = 2.dp)
                                ) {
                                    Text(entry.role, fontSize = 10.sp, color = SlateBlue, fontWeight = FontWeight.SemiBold)
                                }
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("User: ${entry.email}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurface)
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date(entry.timestamp)),
                                    fontSize = 10.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Text(
                                    entry.deviceInfo,
                                    fontSize = 10.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
                item { Spacer(modifier = Modifier.height(40.dp)) }
            }
        }
    }
}
