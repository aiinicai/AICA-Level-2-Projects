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
import com.example.data.model.TaskItem
import com.example.ui.components.OverdueAlertCard
import com.example.ui.theme.*
import com.example.ui.viewmodel.CaViewModel
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EmployeeScreen(
    viewModel: CaViewModel,
    onNavigateToProfile: () -> Unit
) {
    val currentUser by viewModel.currentUser.collectAsState()
    val myTasks by viewModel.myEmployeeTasks.collectAsState()
    val allTasks by viewModel.tasks.collectAsState()
    val userMessage by viewModel.userMessage.collectAsState()

    // Determine relevant tasks: if myTasks is empty (for demo fallback), show tasks where assignedTo matches or sample
    val effectiveTasks = if (myTasks.isNotEmpty()) {
        myTasks
    } else {
        allTasks.filter {
            it.assignedTo.contains("emp", ignoreCase = true) ||
            it.assignedToName.isNotEmpty()
        }
    }

    val pendingCount = effectiveTasks.count { it.status.equals("Pending", true) }
    val inProgressCount = effectiveTasks.count { it.status.equals("In Progress", true) }
    val completedCount = effectiveTasks.count { it.status.equals("Completed", true) }
    val overdueCount = effectiveTasks.count { viewModel.isTaskOverdue(it) }

    var selectedStatusFilter by remember { mutableStateOf("All") }
    var selectedCategoryFilter by remember { mutableStateOf("All") }
    var searchQuery by remember { mutableStateOf("") }

    var selectedTaskForDetail by remember { mutableStateOf<TaskItem?>(null) }
    var newRemarkText by remember { mutableStateOf("") }

    val filteredList = effectiveTasks.filter { task ->
        val matchesQuery = searchQuery.isBlank() ||
                task.taskType.contains(searchQuery, ignoreCase = true) ||
                task.clientName.contains(searchQuery, ignoreCase = true) ||
                task.notes.contains(searchQuery, ignoreCase = true)
        val matchesStatus = selectedStatusFilter == "All" || task.status.equals(selectedStatusFilter, ignoreCase = true)
        val matchesCategory = selectedCategoryFilter == "All" || task.category.equals(selectedCategoryFilter, ignoreCase = true)
        matchesQuery && matchesStatus && matchesCategory
    }

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
                            "EMPLOYEE WORKSPACE • ${(currentUser?.roleTitle?.ifEmpty { "Staff" } ?: "Staff").uppercase()}",
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
                    Box(
                        modifier = Modifier
                            .padding(end = 12.dp)
                            .size(36.dp)
                            .clip(CircleShape)
                            .background(GoldAccent)
                            .clickable { onNavigateToProfile() }
                            .testTag("employee_profile_icon"),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "EM",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp, vertical = 10.dp)
        ) {
            // Welcome Header Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surface
                ),
                border = androidx.compose.foundation.BorderStroke(1.dp, BorderSlate100),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                "My Assigned Filings",
                                fontWeight = FontWeight.Bold,
                                fontSize = 15.sp,
                                color = TextPrimaryLight
                            )
                            Text(
                                currentUser?.email ?: "Employee Portal",
                                fontSize = 11.sp,
                                color = TextSecondaryLight
                            )
                        }
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(BorderSlate100)
                                .padding(horizontal = 8.dp, vertical = 3.dp)
                        ) {
                            Text(
                                (currentUser?.roleTitle?.ifEmpty { "Staff" } ?: "Staff").uppercase(),
                                color = NavyPrimary,
                                fontWeight = FontWeight.Bold,
                                fontSize = 10.sp,
                                letterSpacing = 0.5.sp
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // 3 Metric Pills
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Card(
                            modifier = Modifier
                                .weight(1f)
                                .clickable { selectedStatusFilter = "Pending" },
                            colors = CardDefaults.cardColors(containerColor = AmberWarning.copy(alpha = 0.08f)),
                            border = androidx.compose.foundation.BorderStroke(1.dp, AmberWarning.copy(alpha = 0.25f)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("$pendingCount", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = AmberWarning)
                                Text("PENDING", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp, color = AmberWarning)
                            }
                        }

                        Card(
                            modifier = Modifier
                                .weight(1f)
                                .clickable { selectedStatusFilter = "In Progress" },
                            colors = CardDefaults.cardColors(containerColor = StatusInProgress.copy(alpha = 0.08f)),
                            border = androidx.compose.foundation.BorderStroke(1.dp, StatusInProgress.copy(alpha = 0.25f)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("$inProgressCount", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = StatusInProgress)
                                Text("IN PROGRESS", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp, color = StatusInProgress)
                            }
                        }

                        Card(
                            modifier = Modifier
                                .weight(1f)
                                .clickable { selectedStatusFilter = "Completed" },
                            colors = CardDefaults.cardColors(containerColor = StatusCompleted.copy(alpha = 0.08f)),
                            border = androidx.compose.foundation.BorderStroke(1.dp, StatusCompleted.copy(alpha = 0.25f)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("$completedCount", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = StatusCompleted)
                                Text("COMPLETED", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp, color = StatusCompleted)
                            }
                        }
                    }
                }
            }

            if (overdueCount > 0) {
                Spacer(modifier = Modifier.height(10.dp))
                OverdueAlertCard(
                    count = overdueCount,
                    onClick = { selectedStatusFilter = "Pending" }
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Search and Filters
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                placeholder = { Text("Search my tasks, clients, instructions...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { searchQuery = "" }) {
                            Icon(Icons.Default.Clear, contentDescription = "Clear")
                        }
                    }
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Filter chips
            LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                val statuses = listOf("All", "Pending", "In Progress", "Completed")
                items(statuses) { s ->
                    FilterChip(
                        selected = selectedStatusFilter == s,
                        onClick = { selectedStatusFilter = s },
                        label = { Text(s, fontSize = 11.sp) }
                    )
                }
            }

            LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                val cats = listOf("All", "Income Tax", "GST", "PMS", "General/Compliance")
                items(cats) { c ->
                    FilterChip(
                        selected = selectedCategoryFilter == c,
                        onClick = { selectedCategoryFilter = c },
                        label = { Text(c, fontSize = 11.sp) }
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Task List
            if (filteredList.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            Icons.Default.TaskAlt,
                            contentDescription = null,
                            tint = StatusCompleted,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "No tasks in this view",
                            fontWeight = FontWeight.Medium,
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(filteredList, key = { it.taskId }) { task ->
                        val isOverdue = viewModel.isTaskOverdue(task)
                        val statusColor = when (task.status.lowercase()) {
                            "completed" -> StatusCompleted
                            "in progress" -> StatusInProgress
                            else -> StatusPending
                        }

                        val indicatorColor = if (isOverdue) RedAlertText else statusColor

                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { selectedTaskForDetail = task },
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
                                            Text(task.category, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = NavyPrimary)
                                        }
                                    }

                                    Text(
                                        text = if (isOverdue) "Overdue: ${task.dueDate}" else "Due: ${task.dueDate}",
                                        fontSize = 10.sp,
                                        fontWeight = if (isOverdue) FontWeight.Bold else FontWeight.Medium,
                                        color = if (isOverdue) RedAlertText else TextSecondaryLight
                                    )
                                }

                                Spacer(modifier = Modifier.height(6.dp))

                                Text(
                                    text = task.taskType,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 14.sp,
                                    color = TextPrimaryLight
                                )
                                Text(
                                    text = "Client: ${task.clientName}",
                                    fontSize = 12.sp,
                                    color = TextSecondaryLight
                                )

                                if (task.notes.isNotEmpty()) {
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

                                // Status action button
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Box(
                                            modifier = Modifier
                                                .size(7.dp)
                                                .clip(CircleShape)
                                                .background(statusColor)
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(task.status, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = statusColor)
                                    }

                                    FilledTonalButton(
                                        onClick = { selectedTaskForDetail = task },
                                        shape = RoundedCornerShape(8.dp),
                                        colors = ButtonDefaults.filledTonalButtonColors(
                                            containerColor = BorderSlate100,
                                            contentColor = NavyPrimary
                                        ),
                                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 2.dp)
                                    ) {
                                        Text("Update & Notes", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }
                    }
                    item { Spacer(modifier = Modifier.height(30.dp)) }
                }
            }
        }
    }

    // Detail & Status Update Dialog for Employee
    selectedTaskForDetail?.let { task ->
        var chosenStatus by remember(task.taskId) { mutableStateOf(task.status) }

        AlertDialog(
            onDismissRequest = {
                selectedTaskForDetail = null
                newRemarkText = ""
            },
            title = {
                Text(task.taskType, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 440.dp)
                ) {
                    Text("Client: ${task.clientName}", fontSize = 13.sp, fontWeight = FontWeight.Medium)
                    Text("Due Date: ${task.dueDate} • Priority: ${task.priority}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (task.notes.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Text("Instructions: ${task.notes}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurface)
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    Text("Update Status:", fontSize = 12.sp, fontWeight = FontWeight.Bold)

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("Pending", "In Progress", "Completed").forEach { st ->
                            FilterChip(
                                selected = chosenStatus == st,
                                onClick = { chosenStatus = st },
                                label = { Text(st, fontSize = 11.sp) }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    Text("Remarks & Progress Log:", fontSize = 12.sp, fontWeight = FontWeight.Bold)

                    val remarks = task.remarks
                    if (remarks.isEmpty()) {
                        Text("No remarks recorded yet.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        LazyColumn(modifier = Modifier.heightIn(max = 120.dp)) {
                            items(remarks) { r ->
                                Card(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 3.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                                ) {
                                    Column(modifier = Modifier.padding(6.dp)) {
                                        Text(r.text, fontSize = 12.sp)
                                        Text(
                                            "— ${r.authorName} (${SimpleDateFormat("dd MMM, hh:mm a", Locale.getDefault()).format(Date(r.timestamp))})",
                                            fontSize = 9.sp,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = newRemarkText,
                        onValueChange = { newRemarkText = it },
                        placeholder = { Text("Add work remark or filing reference...") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 2
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.updateTaskStatus(task.taskId, chosenStatus, newRemarkText)
                        selectedTaskForDetail = null
                        newRemarkText = ""
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = NavyPrimary)
                ) {
                    Text("Save Progress")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    selectedTaskForDetail = null
                    newRemarkText = ""
                }) {
                    Text("Cancel")
                }
            }
        )
    }
}
