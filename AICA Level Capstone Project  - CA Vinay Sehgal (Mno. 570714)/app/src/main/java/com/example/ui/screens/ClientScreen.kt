package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TaskItem
import com.example.ui.components.DonutPieChart
import com.example.ui.components.DonutSliceData
import com.example.ui.components.MetricSummaryCard
import com.example.ui.theme.*
import com.example.ui.viewmodel.CaViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClientScreen(
    viewModel: CaViewModel,
    onNavigateToProfile: () -> Unit
) {
    val currentUser by viewModel.currentUser.collectAsState()
    val clientRecord by viewModel.currentClientRecord.collectAsState()
    val myTasks by viewModel.myClientTasks.collectAsState()
    val allTasks by viewModel.tasks.collectAsState()
    val userMessage by viewModel.userMessage.collectAsState()

    // Determine tasks: if myTasks is empty (for demo fallback), show tasks with matching client ID or first client's tasks
    val effectiveTasks = if (myTasks.isNotEmpty()) {
        myTasks
    } else {
        val cliId = clientRecord?.clientId ?: "cli_1"
        allTasks.filter { it.clientId == cliId || it.clientName.contains("Apex", ignoreCase = true) }
    }

    var selectedTab by remember { mutableIntStateOf(0) } // 0: My Services, 1: My Portfolio, 2: Raise Query

    // Query form state
    var querySubject by remember { mutableStateOf("") }
    var queryMessage by remember { mutableStateOf("") }

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
                            "CLIENT SERVICES & PORTFOLIO PORTAL",
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
                            .testTag("client_profile_icon"),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "CL",
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
                        icon = { Icon(Icons.Default.Assignment, contentDescription = "My Services") },
                        label = { Text("SERVICES", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
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
                        icon = { Icon(Icons.Default.PieChart, contentDescription = "My Portfolio") },
                        label = { Text("PORTFOLIO", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
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
                        icon = { Icon(Icons.Default.ContactSupport, contentDescription = "Raise Query") },
                        label = { Text("CONTACT", fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp) },
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
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp, vertical = 10.dp)
        ) {
            // Client Header Info Card
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
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = clientRecord?.name ?: "Valued Client",
                                fontWeight = FontWeight.Bold,
                                fontSize = 15.sp,
                                color = TextPrimaryLight
                            )
                            Text(
                                text = currentUser?.email ?: "",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }

                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(GoldAccent.copy(alpha = 0.2f))
                                .padding(horizontal = 8.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = clientRecord?.clientType ?: "Client",
                                color = AmberWarning,
                                fontWeight = FontWeight.Bold,
                                fontSize = 11.sp
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            "PAN: ${clientRecord?.pan?.ifEmpty { "ABCDE1234F" } ?: "ABCDE1234F"}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium
                        )
                        if (clientRecord?.gstin?.isNotEmpty() == true) {
                            Text(
                                "GSTIN: ${clientRecord?.gstin}",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    // Services tags
                    val services = clientRecord?.servicesSubscribed ?: listOf("Income Tax", "GST", "PMS")
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        services.forEach { s ->
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(SlateBlue.copy(alpha = 0.1f))
                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                            ) {
                                Text(s, fontSize = 10.sp, fontWeight = FontWeight.SemiBold, color = SlateBlue)
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            when (selectedTab) {
                0 -> ClientServicesView(tasks = effectiveTasks)
                1 -> ClientPortfolioView()
                2 -> ClientQueryView(
                    subject = querySubject,
                    onSubjectChange = { querySubject = it },
                    message = queryMessage,
                    onMessageChange = { queryMessage = it },
                    onSubmit = {
                        if (querySubject.isNotBlank() && queryMessage.isNotBlank()) {
                            viewModel.submitClientQuery(querySubject, queryMessage)
                            querySubject = ""
                            queryMessage = ""
                        }
                    }
                )
            }
        }
    }
}

@Composable
fun ClientServicesView(tasks: List<TaskItem>) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Active Filings & Compliance",
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                "${tasks.size} Items",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        if (tasks.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    "No ongoing tasks assigned for this client.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(tasks) { task ->
                    val statusColor = when (task.status.lowercase()) {
                        "completed" -> StatusCompleted
                        "in progress" -> StatusInProgress
                        else -> StatusPending
                    }

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        border = androidx.compose.foundation.BorderStroke(1.dp, BorderSlate100),
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
                                            .background(statusColor)
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
                                    text = "Target: ${task.dueDate}",
                                    fontSize = 10.sp,
                                    color = TextSecondaryLight
                                )
                            }

                            Spacer(modifier = Modifier.height(6.dp))

                            Text(
                                text = task.taskType,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = TextPrimaryLight
                            )

                            if (task.notes.isNotEmpty()) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = task.notes,
                                    fontSize = 11.sp,
                                    color = TextSecondaryLight
                                )
                            }

                            Spacer(modifier = Modifier.height(8.dp))
                            HorizontalDivider(color = BorderSlate100, thickness = 1.dp)
                            Spacer(modifier = Modifier.height(6.dp))

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
                                    Text(
                                        text = task.status,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = statusColor
                                    )
                                }

                                Text(
                                    text = "Handled by CA Team",
                                    fontSize = 10.sp,
                                    color = TextMutedLight
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

@Composable
fun ClientPortfolioView() {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = NavyPrimary)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        "Total Portfolio Value",
                        color = GoldMuted,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "₹ 1,42,80,000",
                        color = Color.White,
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.TrendingUp,
                            contentDescription = null,
                            tint = StatusCompleted,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            "+16.4% Annualized Return (XIRR)",
                            color = StatusCompleted,
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                    }
                }
            }
        }

        // Asset Allocation Donut Chart
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "Asset Allocation Breakdown",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    val slices = listOf(
                        DonutSliceData("Large Cap Equities", 55f, SlateBlue),
                        DonutSliceData("Mid & Small Cap", 25f, GoldAccent),
                        DonutSliceData("Corporate Debt / G-Sec", 15f, StatusCompleted),
                        DonutSliceData("Liquid / Cash Reserve", 5f, SoftSlate)
                    )

                    DonutPieChart(
                        slices = slices,
                        centerTitle = "Invested",
                        centerSubtitle = "₹1.42 Cr"
                    )
                }
            }
        }

        // Capital Gains / Tax Efficiency Card
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
                            "FY 2024-25 Tax Estimation",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp
                        )
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(StatusCompleted.copy(alpha = 0.15f))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text("Optimized", fontSize = 10.sp, color = StatusCompleted, fontWeight = FontWeight.Bold)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text("Realized STCG (Equity)", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("₹ 2,45,000", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text("Realized LTCG (Equity)", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("₹ 6,80,000", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Note: Capital gains statement reconciled with AIS/TIS for upcoming ITR filing.",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        item { Spacer(modifier = Modifier.height(40.dp)) }
    }
}

@Composable
fun ClientQueryView(
    subject: String,
    onSubjectChange: (String) -> Unit,
    message: String,
    onMessageChange: (String) -> Unit,
    onSubmit: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.SupportAgent, contentDescription = null, tint = NavyPrimary)
                Spacer(modifier = Modifier.width(8.dp))
                Column {
                    Text(
                        "Contact Vinay Sehgal & Co",
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp
                    )
                    Text(
                        "Direct message our partners & tax managers",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            OutlinedTextField(
                value = subject,
                onValueChange = onSubjectChange,
                label = { Text("Subject") },
                placeholder = { Text("e.g. Query regarding GST Input Tax Credit") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(10.dp)
            )

            Spacer(modifier = Modifier.height(10.dp))

            OutlinedTextField(
                value = message,
                onValueChange = onMessageChange,
                label = { Text("Message / Query Details") },
                placeholder = { Text("Please describe your question, required filing, or documentation clarification...") },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(130.dp),
                maxLines = 5,
                shape = RoundedCornerShape(10.dp)
            )

            Spacer(modifier = Modifier.height(14.dp))

            Button(
                onClick = onSubmit,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = NavyPrimary)
            ) {
                Icon(Icons.Default.Send, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("Send Query to Firm")
            }
        }
    }
}
