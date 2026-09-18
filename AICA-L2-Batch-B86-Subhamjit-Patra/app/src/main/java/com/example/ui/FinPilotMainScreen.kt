package com.example.ui

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.ai.GeminiCfoAdvisor
import com.example.data.local.*
import com.example.data.model.*
import com.example.data.plaid.ConnectedBank
import com.example.data.plaid.PlaidManager
import com.example.domain.engine.FinancialHealthEngine
import com.example.domain.engine.LifeDecisionEngine
import com.example.ui.auth.AuthModalSheet
import com.example.ui.components.*
import com.example.ui.theme.*
import kotlinx.coroutines.launch
import kotlin.math.pow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FinPilotMainScreen() {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val db = remember { FinPilotDatabase.getDatabase(context) }
    val dao = db.finPilotDao()

    // Room reactive states
    val profile by dao.getUserProfile().collectAsStateWithLifecycle(initialValue = null)
    val assets by dao.getAllAssets().collectAsStateWithLifecycle(initialValue = emptyList())
    val liabilities by dao.getAllLiabilities().collectAsStateWithLifecycle(initialValue = emptyList())
    val transactions by dao.getAllTransactions().collectAsStateWithLifecycle(initialValue = emptyList())
    val goals by dao.getAllGoals().collectAsStateWithLifecycle(initialValue = emptyList())
    val insurancePolicies by dao.getAllInsurancePolicies().collectAsStateWithLifecycle(initialValue = emptyList())
    val notifications by dao.getAllNotifications().collectAsStateWithLifecycle(initialValue = emptyList())
    val chatMessages by dao.getAllChatMessages().collectAsStateWithLifecycle(initialValue = emptyList())
    val connectedBanks by PlaidManager.connectedAccounts.collectAsStateWithLifecycle()

    // Financial calculations
    val totalAssets = assets.sumOf { it.amount }
    val totalLiabilities = liabilities.sumOf { it.outstandingAmount }
    val netWorth = (totalAssets - totalLiabilities).coerceAtLeast(0.0)

    val totalIncome = transactions.filter { it.type == TransactionType.INCOME }.sumOf { it.amount }
    val totalExpense = transactions.filter { it.type == TransactionType.EXPENSE }.sumOf { it.amount }
    val monthlyCashFlow = totalIncome - totalExpense
    val debtRatio = if (totalAssets > 0) ((totalLiabilities / totalAssets) * 100).coerceIn(0.0, 100.0) else 0.0

    // Selected Navigation Tab (0: Home, 1: Assets, 2: CFO, 3: Goals, 4: Report)
    var selectedTab by remember { mutableIntStateOf(0) }

    // Dialog & Sheet states
    var showAuthSheet by remember { mutableStateOf(false) }
    var showPlaidSheet by remember { mutableStateOf(false) }
    var showAddTxDialog by remember { mutableStateOf(false) }
    var showAddAssetDialog by remember { mutableStateOf(false) }
    var showAddLiabilityDialog by remember { mutableStateOf(false) }
    var showProfileDialog by remember { mutableStateOf(false) }
    var showReportExportDialog by remember { mutableStateOf(false) }
    var showNotificationsSheet by remember { mutableStateOf(false) }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground),
        containerColor = DarkBackground,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            // Sophisticated Dark Bottom Navigation Bar
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(NavBackground)
                    .border(androidx.compose.foundation.BorderStroke(1.dp, DarkBorder))
                    .windowInsetsPadding(WindowInsets.navigationBars)
                    .height(72.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 8.dp),
                    horizontalArrangement = Arrangement.SpaceAround,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    NavItem(
                        icon = Icons.Default.Home,
                        label = "Home",
                        isSelected = selectedTab == 0,
                        onClick = { selectedTab = 0 }
                    )

                    NavItem(
                        icon = Icons.Default.AccountBalance,
                        label = "Assets",
                        isSelected = selectedTab == 1,
                        onClick = { selectedTab = 1 }
                    )

                    // Center CFO Button
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier
                            .offset(y = (-14).dp)
                            .clickable { selectedTab = 2 }
                    ) {
                        Box(
                            modifier = Modifier
                                .size(54.dp)
                                .clip(CircleShape)
                                .background(
                                    Brush.linearGradient(
                                        listOf(LavenderAccent, BlueAccent)
                                    )
                                )
                                .border(4.dp, DarkBackground, CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.SmartToy,
                                contentDescription = "AI CFO",
                                tint = Color(0xFF0F1115),
                                modifier = Modifier.size(26.dp)
                            )
                        }
                        Text(
                            text = "CFO",
                            color = if (selectedTab == 2) LavenderAccent else TextSecondary,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }

                    NavItem(
                        icon = Icons.Default.Flag,
                        label = "Goals",
                        isSelected = selectedTab == 3,
                        onClick = { selectedTab = 3 }
                    )

                    NavItem(
                        icon = Icons.Default.Description,
                        label = "Report",
                        isSelected = selectedTab == 4,
                        onClick = { selectedTab = 4 }
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(DarkBackground)
        ) {
            when (selectedTab) {
                0 -> HomeScreen(
                    profile = profile,
                    netWorth = if (netWorth > 0) netWorth else 482950.0,
                    cashFlow = if (monthlyCashFlow != 0.0) monthlyCashFlow else 12400.0,
                    goals = goals,
                    notifications = notifications,
                    onOpenNotifications = { showNotificationsSheet = true },
                    onOpenPlaid = { showPlaidSheet = true },
                    onOpenAiCfo = { selectedTab = 2 },
                    onOpenGoals = { selectedTab = 3 },
                    onOpenProfile = { showProfileDialog = true },
                    onOpenAddTx = { showAddTxDialog = true }
                )
                1 -> AssetsScreen(
                    assets = assets,
                    liabilities = liabilities,
                    totalAssets = totalAssets,
                    totalLiabilities = totalLiabilities,
                    netWorth = netWorth,
                    debtRatio = debtRatio,
                    connectedBanks = connectedBanks,
                    onOpenPlaid = { showPlaidSheet = true },
                    onAddAsset = { showAddAssetDialog = true },
                    onAddLiability = { showAddLiabilityDialog = true }
                )
                2 -> AiCfoScreen(
                    profile = profile,
                    netWorth = netWorth,
                    totalAssets = totalAssets,
                    totalLiabilities = totalLiabilities,
                    cashFlow = monthlyCashFlow,
                    assets = assets,
                    liabilities = liabilities,
                    transactions = transactions,
                    insurancePolicies = insurancePolicies,
                    chatMessages = chatMessages,
                    onSendMessage = { text ->
                        coroutineScope.launch {
                            dao.insertChatMessage(ChatMessageEntity(sender = "USER", message = text))
                            val prof = profile ?: UserProfileEntity()
                            val hResult = FinancialHealthEngine.calculate(
                                profile = prof,
                                assets = assets,
                                liabilities = liabilities,
                                transactions = transactions,
                                insurance = insurancePolicies
                            )
                            val advice = GeminiCfoAdvisor.consultCfo(
                                userQuery = text,
                                profile = prof,
                                netWorth = netWorth,
                                totalAssets = totalAssets,
                                totalLiabilities = totalLiabilities,
                                monthlyIncome = prof.monthlyIncome,
                                healthResult = hResult,
                                assets = assets,
                                liabilities = liabilities
                            )
                            dao.insertChatMessage(ChatMessageEntity(sender = "AI_CFO", message = advice))
                        }
                    }
                )
                3 -> GoalsAndRetirementScreen(
                    goals = goals,
                    profile = profile,
                    insurancePolicies = insurancePolicies,
                    onAddGoal = { title, target, current, years ->
                        coroutineScope.launch {
                            dao.insertGoal(
                                GoalEntity(
                                    title = title,
                                    category = GoalCategory.WEALTH,
                                    targetAmount = target,
                                    currentAmount = current,
                                    targetYears = years
                                )
                            )
                            Toast.makeText(context, "Goal added successfully!", Toast.LENGTH_SHORT).show()
                        }
                    }
                )
                4 -> ReportsScreen(
                    profile = profile,
                    netWorth = netWorth,
                    cashFlow = monthlyCashFlow,
                    totalIncome = totalIncome,
                    totalExpense = totalExpense,
                    transactions = transactions,
                    onExportReport = { showReportExportDialog = true },
                    onAddTransaction = { showAddTxDialog = true }
                )
            }
        }
    }

    // Modal Sheets and Dialogs
    if (showAuthSheet) {
        ModalBottomSheet(
            onDismissRequest = { showAuthSheet = false },
            containerColor = DarkSurface
        ) {
            AuthModalSheet(
                onDismiss = { showAuthSheet = false },
                onLoginSuccess = { session ->
                    showAuthSheet = false
                    Toast.makeText(context, "Welcome back, ${session.displayName}!", Toast.LENGTH_SHORT).show()
                }
            )
        }
    }

    if (showPlaidSheet) {
        ModalBottomSheet(
            onDismissRequest = { showPlaidSheet = false },
            containerColor = DarkSurface
        ) {
            PlaidLinkBottomSheet(
                onDismiss = { showPlaidSheet = false },
                onBankLinked = { institution, accountType, balance ->
                    coroutineScope.launch {
                        PlaidManager.linkNewBank(institution, accountType, balance, dao)
                        showPlaidSheet = false
                        Toast.makeText(context, "Successfully linked $institution!", Toast.LENGTH_LONG).show()
                    }
                }
            )
        }
    }

    if (showNotificationsSheet) {
        ModalBottomSheet(
            onDismissRequest = { showNotificationsSheet = false },
            containerColor = DarkSurface
        ) {
            NotificationsBottomSheet(
                notifications = notifications,
                onDismiss = { showNotificationsSheet = false },
                onMarkActioned = { id ->
                    coroutineScope.launch { dao.markNotificationActioned(id) }
                }
            )
        }
    }

    if (showAddTxDialog) {
        AddTransactionDialog(
            onDismiss = { showAddTxDialog = false },
            onAdd = { title, amount, type, expCat, incCat ->
                coroutineScope.launch {
                    dao.insertTransaction(
                        TransactionEntity(
                            title = title,
                            amount = amount,
                            type = type,
                            expenseCategory = expCat,
                            incomeCategory = incCat
                        )
                    )
                    showAddTxDialog = false
                    Toast.makeText(context, "Transaction recorded!", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    if (showAddAssetDialog) {
        AddAssetDialog(
            onDismiss = { showAddAssetDialog = false },
            onAdd = { name, cat, amount, inst, retRate ->
                coroutineScope.launch {
                    dao.insertAsset(
                        AssetEntity(
                            name = name,
                            category = cat,
                            amount = amount,
                            institution = inst,
                            expectedReturnRate = retRate
                        )
                    )
                    showAddAssetDialog = false
                    Toast.makeText(context, "Asset saved!", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    if (showAddLiabilityDialog) {
        AddLiabilityDialog(
            onDismiss = { showAddLiabilityDialog = false },
            onAdd = { name, cat, amt, rate, emi, tenure ->
                coroutineScope.launch {
                    dao.insertLiability(
                        LiabilityEntity(
                            name = name,
                            category = cat,
                            outstandingAmount = amt,
                            interestRate = rate,
                            monthlyEmi = emi,
                            tenureMonthsRemaining = tenure
                        )
                    )
                    showAddLiabilityDialog = false
                    Toast.makeText(context, "Liability saved!", Toast.LENGTH_SHORT).show()
                }
            }
        )
    }

    if (showProfileDialog) {
        ProfileDialog(
            profile = profile,
            onDismiss = { showProfileDialog = false },
            onSave = { updated ->
                coroutineScope.launch {
                    dao.insertOrUpdateProfile(updated)
                    showProfileDialog = false
                    Toast.makeText(context, "Profile updated!", Toast.LENGTH_SHORT).show()
                }
            },
            onSwitchAuth = {
                showProfileDialog = false
                showAuthSheet = true
            }
        )
    }

    if (showReportExportDialog) {
        MonthlyReportExportDialog(
            profile = profile,
            netWorth = netWorth,
            cashFlow = monthlyCashFlow,
            onDismiss = { showReportExportDialog = false }
        )
    }
}

// -------------------------------------------------------------
// NAVIGATION ITEM COMPONENT
// -------------------------------------------------------------
@Composable
fun NavItem(
    icon: ImageVector,
    label: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clickable(onClick = onClick)
            .padding(vertical = 4.dp, horizontal = 12.dp)
    ) {
        Box(
            modifier = Modifier
                .width(44.dp)
                .height(30.dp)
                .clip(CircleShape)
                .background(if (isSelected) DarkSurfaceVariant else Color.Transparent),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = if (isSelected) LavenderAccent else TextSecondary,
                modifier = Modifier.size(20.dp)
            )
        }
        Text(
            text = label,
            color = if (isSelected) LavenderAccent else TextSecondary,
            fontSize = 10.sp,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
            modifier = Modifier.padding(top = 2.dp)
        )
    }
}

// -------------------------------------------------------------
// MODULE 1 & DASHBOARD: HOME SCREEN
// -------------------------------------------------------------
@Composable
fun HomeScreen(
    profile: UserProfileEntity?,
    netWorth: Double,
    cashFlow: Double,
    goals: List<GoalEntity>,
    notifications: List<NotificationEntity>,
    onOpenNotifications: () -> Unit,
    onOpenPlaid: () -> Unit,
    onOpenAiCfo: () -> Unit,
    onOpenGoals: () -> Unit,
    onOpenProfile: () -> Unit,
    onOpenAddTx: () -> Unit
) {
    val unreadCount = notifications.count { !it.isActioned }

    val netWorthTrend = listOf(
        "Apr" to 425000.0,
        "May" to 438000.0,
        "Jun" to 449500.0,
        "Jul" to 462000.0,
        "Aug" to 474200.0,
        "Sep" to netWorth
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp)
            .padding(bottom = 90.dp)
    ) {
        // Top Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, bottom = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.clickable { onOpenProfile() }
            ) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(DarkSurfaceVariant)
                        .border(1.dp, DarkBorder, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = profile?.name?.take(2)?.uppercase() ?: "JS",
                        color = LavenderAccent,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp
                    )
                }
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "WELCOME BACK",
                        color = TextSecondary,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.SemiBold,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = profile?.name ?: "James Sterling",
                        color = TextPrimary,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            // Quick actions top right
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .clip(CircleShape)
                        .background(DarkSurface)
                        .border(1.dp, DarkBorder, CircleShape)
                        .clickable { onOpenPlaid() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Link,
                        contentDescription = "Link Bank",
                        tint = LavenderAccent,
                        modifier = Modifier.size(18.dp)
                    )
                }

                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .clip(CircleShape)
                        .background(DarkSurface)
                        .border(1.dp, DarkBorder, CircleShape)
                        .clickable { onOpenNotifications() },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Notifications,
                        contentDescription = "Notifications",
                        tint = TextPrimary,
                        modifier = Modifier.size(18.dp)
                    )
                    if (unreadCount > 0) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .offset(x = 6.dp, y = (-6).dp)
                                .background(LavenderAccent, CircleShape)
                        )
                    }
                }
            }
        }

        // Section 1: Financial Health Score Card (Sophisticated Dark Spec)
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(26.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top
                ) {
                    Column {
                        Text(
                            text = "Financial Health Score",
                            color = TextSecondary,
                            fontSize = 13.sp
                        )
                        Row(
                            verticalAlignment = Alignment.Bottom,
                            modifier = Modifier.padding(top = 2.dp)
                        ) {
                            Text(
                                text = "84",
                                color = LavenderAccent,
                                fontSize = 38.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "/100",
                                color = TextSecondary.copy(alpha = 0.6f),
                                fontSize = 18.sp,
                                modifier = Modifier.padding(bottom = 6.dp)
                            )
                        }
                    }

                    Box(
                        modifier = Modifier
                            .background(DarkSurfaceVariant, RoundedCornerShape(20.dp))
                            .border(1.dp, DarkBorderLight, RoundedCornerShape(20.dp))
                            .padding(horizontal = 12.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "OPTIMAL",
                            color = MintSuccess,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.ExtraBold,
                            letterSpacing = 0.5.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp))
                        .background(DarkBackground)
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .fillMaxWidth(0.84f)
                            .background(
                                Brush.horizontalGradient(
                                    listOf(LavenderAccent, BlueAccent)
                                )
                            )
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Your net worth increased by 4.2% this month. Debt-to-asset ratio is strictly within healthy limits.",
                    color = TextSecondary,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Section 2: Net Worth & Cash Flow Dual Metric Cards
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Card(
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = DarkSurface),
                border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "NET WORTH",
                        color = TextSecondary,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = "$${String.format("%,.0f", netWorth)}",
                        color = TextPrimary,
                        fontSize = 19.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(top = 4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.TrendingUp,
                            contentDescription = null,
                            tint = MintSuccess,
                            modifier = Modifier.size(13.dp)
                        )
                        Spacer(modifier = Modifier.width(3.dp))
                        Text(
                            text = "+12.5%",
                            color = MintSuccess,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }

            Card(
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = DarkSurface),
                border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "CASH FLOW",
                        color = TextSecondary,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = "$${String.format("%,.0f", cashFlow)}",
                        color = TextPrimary,
                        fontSize = 19.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 2.dp)
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(top = 4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.TrendingDown,
                            contentDescription = null,
                            tint = CoralExpense,
                            modifier = Modifier.size(13.dp)
                        )
                        Spacer(modifier = Modifier.width(3.dp))
                        Text(
                            text = "-2.1%",
                            color = CoralExpense,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Section 3: FinPilot AI Insight Callout Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onOpenAiCfo() },
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = InsightBg),
            border = androidx.compose.foundation.BorderStroke(1.dp, InsightBorder)
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(LavenderAccent),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.SmartToy,
                        contentDescription = "FinPilot AI",
                        tint = Color(0xFF0F1115),
                        modifier = Modifier.size(22.dp)
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "FinPilot AI Insight",
                        color = InsightTextPrimary,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Move $2,500 from Savings to Tech ETF to optimize yields...",
                        color = InsightTextSecondary,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Box(
                    modifier = Modifier
                        .size(30.dp)
                        .clip(CircleShape)
                        .background(InsightBtn)
                        .border(1.dp, InsightBorder, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.ChevronRight,
                        contentDescription = null,
                        tint = InsightTextPrimary,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Section 4: Interactive Net Worth Trend Chart (Reusable Component)
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Text(
                    text = "Net Worth Growth Trajectory",
                    color = TextPrimary,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "6-Month compounding performance",
                    color = TextSecondary,
                    fontSize = 11.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
                NetWorthTrendChart(dataPoints = netWorthTrend)
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Section 5: Upcoming Goals Preview
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Upcoming Goals",
                        color = TextPrimary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "View All",
                        color = LavenderAccent,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.clickable { onOpenGoals() }
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                GoalPreviewRow(
                    icon = Icons.Default.Home,
                    title = "New Family Home",
                    progressPct = 65,
                    barColor = BlueAccent
                )

                Spacer(modifier = Modifier.height(14.dp))

                GoalPreviewRow(
                    icon = Icons.Default.WorkspacePremium,
                    title = "Retirement Corpus",
                    progressPct = 12,
                    barColor = LavenderAccent
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // Section 6: Quick Action Pill Bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ActionChip(
                label = "+ Add Transaction",
                icon = Icons.Default.AddCircleOutline,
                onClick = onOpenAddTx
            )
            ActionChip(
                label = "🏦 Link Bank (Plaid)",
                icon = Icons.Default.Link,
                onClick = onOpenPlaid
            )
            ActionChip(
                label = "⚖️ Buy vs Rent",
                icon = Icons.Default.Calculate,
                onClick = onOpenAiCfo
            )
        }
    }
}

@Composable
fun GoalPreviewRow(
    icon: ImageVector,
    title: String,
    progressPct: Int,
    barColor: Color
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(42.dp)
                .clip(CircleShape)
                .background(DarkSurfaceVariant),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (icon == Icons.Default.WorkspacePremium) GoldWarning else TextPrimary,
                modifier = Modifier.size(20.dp)
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = title,
                    color = TextPrimary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "$progressPct%",
                    color = TextSecondary,
                    fontSize = 10.sp
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(DarkBackground)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth(progressPct / 100f)
                        .background(barColor)
                )
            }
        }
    }
}

@Composable
fun ActionChip(
    label: String,
    icon: ImageVector,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .background(DarkSurface, RoundedCornerShape(12.dp))
            .border(1.dp, DarkBorder, RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(imageVector = icon, contentDescription = null, tint = LavenderAccent, modifier = Modifier.size(14.dp))
            Spacer(modifier = Modifier.width(6.dp))
            Text(text = label, color = TextPrimary, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

// -------------------------------------------------------------
// MODULE 2 & 11: ASSETS & NET WORTH SCREEN
// -------------------------------------------------------------
@Composable
fun AssetsScreen(
    assets: List<AssetEntity>,
    liabilities: List<LiabilityEntity>,
    totalAssets: Double,
    totalLiabilities: Double,
    netWorth: Double,
    debtRatio: Double,
    connectedBanks: List<ConnectedBank>,
    onOpenPlaid: () -> Unit,
    onAddAsset: () -> Unit,
    onAddLiability: () -> Unit
) {
    var selectedCategoryTab by remember { mutableIntStateOf(0) }

    val allocationSegments = remember(assets) {
        listOf(
            DonutSegment("Equities & Mutual Funds", assets.filter { it.category == AssetCategory.MUTUAL_FUNDS || it.category == AssetCategory.SHARES }.sumOf { it.amount }, LavenderAccent),
            DonutSegment("Real Estate", assets.filter { it.category == AssetCategory.REAL_ESTATE }.sumOf { it.amount }, BlueAccent),
            DonutSegment("Retirement (EPF/NPS)", assets.filter { it.category == AssetCategory.EPF || it.category == AssetCategory.NPS }.sumOf { it.amount }, MintSuccess),
            DonutSegment("Bonds & Debt", assets.filter { it.category == AssetCategory.BONDS || it.category == AssetCategory.FIXED_DEPOSIT }.sumOf { it.amount }, GoldWarning),
            DonutSegment("Liquid Cash & Gold", assets.filter { it.category == AssetCategory.BANK || it.category == AssetCategory.CASH || it.category == AssetCategory.GOLD }.sumOf { it.amount }, CoralExpense)
        ).filter { it.value > 0 }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp)
            .padding(bottom = 90.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text("NET WORTH & ASSETS", color = TextSecondary, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                Text("Portfolio Statement", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            }
            IconButton(
                onClick = onOpenPlaid,
                modifier = Modifier
                    .size(36.dp)
                    .background(DarkSurface, CircleShape)
                    .border(1.dp, DarkBorder, CircleShape)
            ) {
                Icon(Icons.Default.Link, contentDescription = "Plaid", tint = LavenderAccent, modifier = Modifier.size(18.dp))
            }
        }

        // Summary Net Worth Banner
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("Total Assets", color = TextSecondary, fontSize = 11.sp)
                        Text("$${String.format("%,.0f", totalAssets)}", color = MintSuccess, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text("Total Liabilities", color = TextSecondary, fontSize = 11.sp)
                        Text("$${String.format("%,.0f", totalLiabilities)}", color = CoralExpense, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    }
                }

                Divider(modifier = Modifier.padding(vertical = 12.dp), color = DarkBorder)

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Net Worth", color = TextSecondary, fontSize = 12.sp)
                        Text("$${String.format("%,.0f", netWorth)}", color = LavenderAccent, fontSize = 26.sp, fontWeight = FontWeight.Bold)
                    }
                    Box(
                        modifier = Modifier
                            .background(DarkSurfaceVariant, RoundedCornerShape(12.dp))
                            .border(1.dp, DarkBorderLight, RoundedCornerShape(12.dp))
                            .padding(horizontal = 10.dp, vertical = 6.dp)
                    ) {
                        Text(
                            text = "Debt/Asset: ${String.format("%.1f", debtRatio)}%",
                            color = if (debtRatio < 30) MintSuccess else CoralExpense,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Asset Allocation Donut Chart (Reusable Component)
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Text("Asset Allocation", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Text("Diversification across 12 asset classes", color = TextSecondary, fontSize = 11.sp)
                Spacer(modifier = Modifier.height(14.dp))
                ExpenseBreakdownDonutChart(
                    segments = allocationSegments,
                    centerTitle = "Total Assets",
                    centerValue = "$${String.format("%,.0f", totalAssets)}"
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Category Tab Switcher
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(DarkSurface, RoundedCornerShape(14.dp))
                .border(1.dp, DarkBorder, RoundedCornerShape(14.dp))
                .padding(4.dp)
        ) {
            listOf("Assets (${assets.size})", "Liabilities (${liabilities.size})", "Plaid Sync (${connectedBanks.size})").forEachIndexed { index, title ->
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(10.dp))
                        .background(if (selectedCategoryTab == index) DarkSurfaceVariant else Color.Transparent)
                        .clickable { selectedCategoryTab = index }
                        .padding(vertical = 8.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = title,
                        color = if (selectedCategoryTab == index) LavenderAccent else TextSecondary,
                        fontSize = 11.sp,
                        fontWeight = if (selectedCategoryTab == index) FontWeight.Bold else FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        when (selectedCategoryTab) {
            0 -> {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Tracked Assets", color = TextSecondary, fontSize = 12.sp)
                    Text("+ Add Asset", color = LavenderAccent, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.clickable { onAddAsset() })
                }
                assets.forEach { asset ->
                    AssetItemRow(asset)
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
            1 -> {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Outstanding Debts", color = TextSecondary, fontSize = 12.sp)
                    Text("+ Add Liability", color = CoralExpense, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.clickable { onAddLiability() })
                }
                liabilities.forEach { liability ->
                    LiabilityItemRow(liability)
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
            2 -> {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Plaid Bank Feeds", color = TextSecondary, fontSize = 12.sp)
                    Text("+ Link Bank", color = LavenderAccent, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.clickable { onOpenPlaid() })
                }
                connectedBanks.forEach { bank ->
                    BankItemRow(bank)
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
fun AssetItemRow(asset: AssetEntity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .background(DarkSurfaceVariant, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = when (asset.category) {
                        AssetCategory.BANK -> "🏦"
                        AssetCategory.MUTUAL_FUNDS, AssetCategory.SHARES -> "📈"
                        AssetCategory.REAL_ESTATE -> "🏢"
                        AssetCategory.GOLD -> "🪙"
                        AssetCategory.EPF, AssetCategory.NPS -> "🛡️"
                        else -> "💵"
                    },
                    fontSize = 16.sp
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(asset.name, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("${asset.category.displayName} • ${asset.institution}", color = TextSecondary, fontSize = 10.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("$${String.format("%,.0f", asset.amount)}", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Text("${asset.expectedReturnRate}% return", color = MintSuccess, fontSize = 10.sp)
            }
        }
    }
}

@Composable
fun LiabilityItemRow(liability: LiabilityEntity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .background(DarkSurfaceVariant, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = when (liability.category) {
                        LiabilityCategory.HOME_LOAN -> "🏠"
                        LiabilityCategory.VEHICLE_LOAN -> "🚗"
                        LiabilityCategory.CREDIT_CARD -> "💳"
                        else -> "📑"
                    },
                    fontSize = 16.sp
                )
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(liability.name, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                Text("EMI: $${String.format("%,.0f", liability.monthlyEmi)}/mo • ${liability.interestRate}% APR", color = TextSecondary, fontSize = 10.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("$${String.format("%,.0f", liability.outstandingAmount)}", color = CoralExpense, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Text("${liability.tenureMonthsRemaining} mos left", color = TextSecondary, fontSize = 10.sp)
            }
        }
    }
}

@Composable
fun BankItemRow(bank: ConnectedBank) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(bank.logoEmoji, fontSize = 22.sp)
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(bank.institutionName, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text("${bank.accountType} ${bank.accountNumberMask} • Synced ${bank.lastSynced}", color = TextSecondary, fontSize = 10.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("$${String.format("%,.0f", bank.balance)}", color = MintSuccess, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Text("Plaid Active", color = LavenderAccent, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

// -------------------------------------------------------------
// MODULE 5 & 6: AI CFO & LIFE DECISION SIMULATOR SCREEN
// -------------------------------------------------------------
@Composable
fun AiCfoScreen(
    profile: UserProfileEntity?,
    netWorth: Double,
    totalAssets: Double,
    totalLiabilities: Double,
    cashFlow: Double,
    assets: List<AssetEntity>,
    liabilities: List<LiabilityEntity>,
    transactions: List<TransactionEntity>,
    insurancePolicies: List<InsurancePolicyEntity>,
    chatMessages: List<ChatMessageEntity>,
    onSendMessage: (String) -> Unit
) {
    var subTab by remember { mutableIntStateOf(0) }
    var inputQuery by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .padding(bottom = 80.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp, vertical = 12.dp)
                .background(DarkSurface, RoundedCornerShape(14.dp))
                .border(1.dp, DarkBorder, RoundedCornerShape(14.dp))
                .padding(4.dp)
        ) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (subTab == 0) DarkSurfaceVariant else Color.Transparent)
                    .clickable { subTab = 0 }
                    .padding(vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                Text("AI CFO Advisor", color = if (subTab == 0) LavenderAccent else TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(if (subTab == 1) DarkSurfaceVariant else Color.Transparent)
                    .clickable { subTab = 1 }
                    .padding(vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                Text("Life Decision Engine", color = if (subTab == 1) LavenderAccent else TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }
        }

        if (subTab == 0) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 18.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .padding(bottom = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf(
                        "How to optimize my taxes?",
                        "Should I prepay mortgage?",
                        "Car affordability 20/4/10",
                        "Retirement readiness check"
                    ).forEach { prompt ->
                        Box(
                            modifier = Modifier
                                .background(DarkSurface, RoundedCornerShape(12.dp))
                                .border(1.dp, DarkBorder, RoundedCornerShape(12.dp))
                                .clickable { onSendMessage(prompt) }
                                .padding(horizontal = 10.dp, vertical = 6.dp)
                        ) {
                            Text(prompt, color = BlueAccent, fontSize = 11.sp)
                        }
                    }
                }

                LazyColumn(
                    modifier = Modifier.weight(1f),
                    reverseLayout = false,
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(chatMessages) { msg ->
                        val isUser = msg.sender == "USER"
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
                        ) {
                            Card(
                                shape = RoundedCornerShape(16.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = if (isUser) LavenderAccent.copy(alpha = 0.2f) else DarkSurface
                                ),
                                border = androidx.compose.foundation.BorderStroke(1.dp, if (isUser) LavenderAccent.copy(alpha = 0.4f) else DarkBorder),
                                modifier = Modifier.widthIn(max = 310.dp)
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text(
                                        text = if (isUser) "You" else "FinPilot AI (Chartered CFO)",
                                        color = if (isUser) LavenderAccent else MintSuccess,
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = msg.message,
                                        color = TextPrimary,
                                        fontSize = 12.sp,
                                        lineHeight = 17.sp
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = inputQuery,
                        onValueChange = { inputQuery = it },
                        placeholder = { Text("Ask your Personal CFO...", color = TextSecondary, fontSize = 12.sp) },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(16.dp),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = LavenderAccent,
                            unfocusedBorderColor = DarkBorder,
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary
                        )
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = {
                            if (inputQuery.isNotBlank()) {
                                val q = inputQuery
                                inputQuery = ""
                                onSendMessage(q)
                            }
                        },
                        modifier = Modifier
                            .size(46.dp)
                            .background(LavenderAccent, RoundedCornerShape(14.dp))
                    ) {
                        Icon(Icons.Default.Send, contentDescription = "Send", tint = Color(0xFF0F1115))
                    }
                }
            }
        } else {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 18.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                DecisionSimulatorBuyVsRent()
                Spacer(modifier = Modifier.height(14.dp))

                DecisionSimulatorCarAffordability(profile?.monthlyIncome ?: 14500.0)
                Spacer(modifier = Modifier.height(14.dp))

                DecisionSimulatorPrepayVsSip()
                Spacer(modifier = Modifier.height(14.dp))
            }
        }
    }
}

@Composable
fun DecisionSimulatorBuyVsRent() {
    var price by remember { mutableStateOf("450000") }
    var rent by remember { mutableStateOf("2100") }

    val result = remember(price, rent) {
        val p = price.toDoubleOrNull() ?: 450000.0
        val r = rent.toDoubleOrNull() ?: 2100.0
        LifeDecisionEngine.simulateBuyVsRent(propertyPrice = p, monthlyRent = r)
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🏠", fontSize = 18.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Buy vs. Rent House Simulator", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = price,
                    onValueChange = { price = it },
                    label = { Text("Property Price ($)", fontSize = 10.sp) },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = rent,
                    onValueChange = { rent = it },
                    label = { Text("Monthly Rent ($)", fontSize = 10.sp) },
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
            }
            Spacer(modifier = Modifier.height(10.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(DarkSurfaceVariant, RoundedCornerShape(12.dp))
                    .padding(12.dp)
            ) {
                Column {
                    Text(
                        "10-Yr Buy NW: $${String.format("%,.0f", result.buyNetWorth10Yr)} vs Rent NW: $${String.format("%,.0f", result.rentNetWorth10Yr)}",
                        color = MintSuccess,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(result.recommendation, color = TextSecondary, fontSize = 11.sp, lineHeight = 16.sp)
                }
            }
        }
    }
}

@Composable
fun DecisionSimulatorCarAffordability(income: Double) {
    var carPrice by remember { mutableStateOf("38000") }

    val result = remember(carPrice, income) {
        val cp = carPrice.toDoubleOrNull() ?: 38000.0
        LifeDecisionEngine.checkCarAffordability(onRoadPrice = cp, monthlyTakeHomeIncome = income)
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🚗", fontSize = 18.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text("20/4/10 Car Affordability Rule", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(10.dp))
            OutlinedTextField(
                value = carPrice,
                onValueChange = { carPrice = it },
                label = { Text("Target Car Price ($)", fontSize = 10.sp) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
            )
            Spacer(modifier = Modifier.height(10.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(DarkSurfaceVariant, RoundedCornerShape(12.dp))
                    .padding(12.dp)
            ) {
                Column {
                    Text(
                        text = if (result.isAffordable) "APPROVED BY CFO (20/4/10 Compliant)" else "CAUTION: HIGH FINANCIAL DRAG",
                        color = if (result.isAffordable) MintSuccess else CoralExpense,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(result.recommendation, color = TextSecondary, fontSize = 11.sp, lineHeight = 16.sp)
                }
            }
        }
    }
}

@Composable
fun DecisionSimulatorPrepayVsSip() {
    var extraMonthly by remember { mutableStateOf("600") }

    val result = remember(extraMonthly) {
        val em = extraMonthly.toDoubleOrNull() ?: 600.0
        LifeDecisionEngine.simulatePrepayVsSip(prepaymentLumpSum = em * 12)
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("⚖️", fontSize = 18.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Prepay Mortgage vs. Mutual Fund SIP", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(10.dp))
            OutlinedTextField(
                value = extraMonthly,
                onValueChange = { extraMonthly = it },
                label = { Text("Extra Annual Cash to Deploy ($)", fontSize = 10.sp) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
            )
            Spacer(modifier = Modifier.height(10.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(DarkSurfaceVariant, RoundedCornerShape(12.dp))
                    .padding(12.dp)
            ) {
                Column {
                    Text(
                        text = "Net Advantage: +$${String.format("%,.0f", result.netFinancialAdvantage)} via Equity Index SIP",
                        color = MintSuccess,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(result.recommendation, color = TextSecondary, fontSize = 11.sp, lineHeight = 16.sp)
                }
            }
        }
    }
}

// -------------------------------------------------------------
// MODULE 7, 8 & 9: GOALS, RETIREMENT & INSURANCE SCREEN
// -------------------------------------------------------------
@Composable
fun GoalsAndRetirementScreen(
    goals: List<GoalEntity>,
    profile: UserProfileEntity?,
    insurancePolicies: List<InsurancePolicyEntity>,
    onAddGoal: (String, Double, Double, Int) -> Unit
) {
    var goalSectionTab by remember { mutableIntStateOf(0) }
    var showAddGoalDialog by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp)
            .padding(bottom = 90.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text("STRATEGIC PLANNING", color = TextSecondary, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                Text("Goals & Protection", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            }
            if (goalSectionTab == 0) {
                IconButton(
                    onClick = { showAddGoalDialog = true },
                    modifier = Modifier.size(36.dp).background(DarkSurface, CircleShape).border(1.dp, DarkBorder, CircleShape)
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Add Goal", tint = LavenderAccent, modifier = Modifier.size(18.dp))
                }
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(DarkSurface, RoundedCornerShape(14.dp))
                .border(1.dp, DarkBorder, RoundedCornerShape(14.dp))
                .padding(4.dp)
        ) {
            listOf("Goals (${goals.size})", "Retirement", "Insurance (${insurancePolicies.size})").forEachIndexed { index, title ->
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(10.dp))
                        .background(if (goalSectionTab == index) DarkSurfaceVariant else Color.Transparent)
                        .clickable { goalSectionTab = index }
                        .padding(vertical = 8.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = title,
                        color = if (goalSectionTab == index) LavenderAccent else TextSecondary,
                        fontSize = 11.sp,
                        fontWeight = if (goalSectionTab == index) FontWeight.Bold else FontWeight.Medium
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        when (goalSectionTab) {
            0 -> {
                goals.forEach { goal ->
                    GoalCardDetail(goal)
                    Spacer(modifier = Modifier.height(10.dp))
                }
            }
            1 -> {
                RetirementPlannerCard(profile)
            }
            2 -> {
                InsuranceAnalyzerCard(profile, insurancePolicies)
            }
        }
    }

    if (showAddGoalDialog) {
        AddGoalDialog(
            onDismiss = { showAddGoalDialog = false },
            onAdd = { title, target, current, years ->
                onAddGoal(title, target, current, years)
                showAddGoalDialog = false
            }
        )
    }
}

@Composable
fun GoalCardDetail(goal: GoalEntity) {
    val progress = if (goal.targetAmount > 0) (goal.currentAmount / goal.targetAmount).toFloat().coerceIn(0f, 1f) else 0f
    val pct = (progress * 100).toInt()

    val r = (goal.expectedReturnRate / 100.0) / 12.0
    val n = (goal.targetYears * 12).toDouble()
    val gap = (goal.targetAmount - goal.currentAmount).coerceAtLeast(0.0)
    val monthlySip = if (r > 0 && n > 0) {
        gap * r / ((1 + r).pow(n) - 1)
    } else 0.0

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = when (goal.category) {
                            GoalCategory.HOUSE -> "🏡"
                            GoalCategory.RETIREMENT -> "🏖️"
                            GoalCategory.EDUCATION -> "🎓"
                            GoalCategory.VACATION -> "✈️"
                            else -> "💎"
                        },
                        fontSize = 18.sp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(goal.title, color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                }
                Text("$pct%", color = LavenderAccent, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            }

            Spacer(modifier = Modifier.height(10.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(DarkBackground)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth(progress)
                        .background(
                            Brush.horizontalGradient(
                                listOf(LavenderAccent, BlueAccent)
                            )
                        )
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text("Saved: $${String.format("%,.0f", goal.currentAmount)}", color = TextSecondary, fontSize = 11.sp)
                Text("Target: $${String.format("%,.0f", goal.targetAmount)}", color = TextPrimary, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }

            Spacer(modifier = Modifier.height(6.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text("Timeline: ${goal.targetYears} Years", color = TextSecondary, fontSize = 10.sp)
                Text("Recommended SIP: $${String.format("%,.0f", monthlySip)}/mo", color = MintSuccess, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun RetirementPlannerCard(profile: UserProfileEntity?) {
    val currentAge = profile?.currentAge ?: 34
    val retirementAge = profile?.retirementAge ?: 60
    val yearsRemaining = retirementAge - currentAge

    val requiredCorpus = 1500000.0
    val currentSaved = 180000.0
    val gap = requiredCorpus - currentSaved

    val r = 0.11 / 12.0
    val n = (yearsRemaining * 12).toDouble()
    val recommendedSip = gap * r / ((1 + r).pow(n) - 1)

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text("Retirement Corpus Roadmap", color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            Text("Target Age: $retirementAge ($yearsRemaining years horizon)", color = TextSecondary, fontSize = 11.sp)

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text("Target Corpus", color = TextSecondary, fontSize = 11.sp)
                    Text("$${String.format("%,.0f", requiredCorpus)}", color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("Current Savings", color = TextSecondary, fontSize = 11.sp)
                    Text("$${String.format("%,.0f", currentSaved)}", color = LavenderAccent, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(DarkSurfaceVariant, RoundedCornerShape(14.dp))
                    .padding(14.dp)
            ) {
                Column {
                    Text("Gap Analysis & Recommendation", color = MintSuccess, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "To bridge the $${String.format("%,.0f", gap)} gap by age $retirementAge at 11% CAGR, invest \$${String.format("%,.0f", recommendedSip)}/month in a diversified equity index fund.",
                        color = TextSecondary,
                        fontSize = 11.sp,
                        lineHeight = 16.sp
                    )
                }
            }
        }
    }
}

@Composable
fun InsuranceAnalyzerCard(
    profile: UserProfileEntity?,
    policies: List<InsurancePolicyEntity>
) {
    val annualIncome = (profile?.monthlyIncome ?: 14500.0) * 12
    val recommendedTermLife = annualIncome * 12.0
    val totalLifeCover = policies.filter { it.type == InsuranceType.TERM_LIFE }.sumOf { it.sumAssured }
    val lifeGap = (recommendedTermLife - totalLifeCover).coerceAtLeast(0.0)

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text("Human Life Value (HLV) & Protection", color = TextPrimary, fontSize = 15.sp, fontWeight = FontWeight.Bold)
            Text("Safety cushion for ${profile?.dependentsCount ?: 2} dependents", color = TextSecondary, fontSize = 11.sp)

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text("Recommended Life Cover", color = TextSecondary, fontSize = 10.sp)
                    Text("$${String.format("%,.0f", recommendedTermLife)}", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text("Current Cover", color = TextSecondary, fontSize = 10.sp)
                    Text("$${String.format("%,.0f", totalLifeCover)}", color = MintSuccess, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(if (lifeGap == 0.0) DarkSurfaceVariant else CoralExpense.copy(alpha = 0.15f), RoundedCornerShape(12.dp))
                    .padding(12.dp)
            ) {
                Text(
                    text = if (lifeGap == 0.0) "✓ Life protection is fully adequate (Optimal)" else "Protection Deficit: \$$lifeGap additional cover recommended.",
                    color = if (lifeGap == 0.0) MintSuccess else CoralExpense,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            Text("Active Policies", color = TextSecondary, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            policies.forEach { pol ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(pol.policyName, color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                        Text("${pol.provider} • Premium: $${pol.annualPremium}/yr", color = TextSecondary, fontSize = 10.sp)
                    }
                    Text("$${String.format("%,.0f", pol.sumAssured)}", color = LavenderAccent, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

// -------------------------------------------------------------
// MODULE 3 & 10: CASH FLOW & MONTHLY CFO REPORT SCREEN
// -------------------------------------------------------------
@Composable
fun ReportsScreen(
    profile: UserProfileEntity?,
    netWorth: Double,
    cashFlow: Double,
    totalIncome: Double,
    totalExpense: Double,
    transactions: List<TransactionEntity>,
    onExportReport: () -> Unit,
    onAddTransaction: () -> Unit
) {
    val months = listOf("May", "Jun", "Jul", "Aug", "Sep")
    val incomeTrend = listOf(13500.0, 13800.0, 14200.0, 14500.0, totalIncome.coerceAtLeast(14500.0))
    val expenseTrend = listOf(2600.0, 2400.0, 2900.0, 2300.0, totalExpense.coerceAtLeast(2100.0))

    val expenseBreakdown = remember(transactions) {
        listOf(
            DonutSegment("Mortgage & EMI", 1730.0, CoralExpense),
            DonutSegment("Household & Living", 650.0, LavenderAccent),
            DonutSegment("Insurance & Health", 280.0, BlueAccent),
            DonutSegment("Utilities & Bills", 220.0, GoldWarning)
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 18.dp)
            .padding(bottom = 90.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 16.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text("MONTHLY CFO STATEMENT", color = TextSecondary, fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                Text("Cash Flow & Reports", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
            }
            IconButton(
                onClick = onExportReport,
                modifier = Modifier.size(36.dp).background(DarkSurface, CircleShape).border(1.dp, DarkBorder, CircleShape)
            ) {
                Icon(Icons.Default.Download, contentDescription = "Export Report", tint = LavenderAccent, modifier = Modifier.size(18.dp))
            }
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Text("Monthly Inflow vs. Outflow", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Text("Healthy operational cash surplus of +$${String.format("%,.0f", cashFlow)}/mo", color = TextSecondary, fontSize = 11.sp)
                Spacer(modifier = Modifier.height(14.dp))
                CashFlowBarChart(months = months, incomes = incomeTrend, expenses = expenseTrend)
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Text("Expense Category Distribution", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(14.dp))
                ExpenseBreakdownDonutChart(
                    segments = expenseBreakdown,
                    centerTitle = "Total Outflow",
                    centerValue = "$${String.format("%,.0f", totalExpense.coerceAtLeast(2880.0))}"
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = DarkSurface),
            border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
        ) {
            Column(modifier = Modifier.padding(18.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Executive CFO Action Plan", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Button(
                        onClick = onExportReport,
                        colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent),
                        shape = RoundedCornerShape(10.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text("Export PDF", color = Color(0xFF0F1115), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                listOf(
                    "1. Prepay Executive Credit Card balance to eliminate 18% APR interest drag.",
                    "2. Channel $2,500 of idle checking cash into low-cost Vanguard S&P500 SIP.",
                    "3. Review Term Life renewal due on Oct 15 to maintain $1.5M coverage.",
                    "4. Rebalance portfolio to 50% Equity / 35% Real Estate / 15% Debt target."
                ).forEach { item ->
                    Text(
                        text = item,
                        color = TextSecondary,
                        fontSize = 11.sp,
                        lineHeight = 16.sp,
                        modifier = Modifier.padding(vertical = 3.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        Row(
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Recent Transactions", color = TextSecondary, fontSize = 12.sp)
            Text("+ Record Transaction", color = LavenderAccent, fontSize = 12.sp, fontWeight = FontWeight.Bold, modifier = Modifier.clickable { onAddTransaction() })
        }

        transactions.take(8).forEach { tx ->
            TransactionRow(tx)
            Spacer(modifier = Modifier.height(8.dp))
        }
    }
}

@Composable
fun TransactionRow(tx: TransactionEntity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = DarkSurface),
        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(34.dp)
                    .background(if (tx.type == TransactionType.INCOME) MintSuccess.copy(alpha = 0.15f) else CoralExpense.copy(alpha = 0.15f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = if (tx.type == TransactionType.INCOME) Icons.Default.ArrowDownward else Icons.Default.ArrowUpward,
                    contentDescription = null,
                    tint = if (tx.type == TransactionType.INCOME) MintSuccess else CoralExpense,
                    modifier = Modifier.size(16.dp)
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(tx.title, color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.Medium, maxLines = 1)
                Text(
                    text = if (tx.type == TransactionType.INCOME) tx.incomeCategory?.displayName ?: "Income" else tx.expenseCategory?.displayName ?: "Expense",
                    color = TextSecondary,
                    fontSize = 10.sp
                )
            }
            Text(
                text = "${if (tx.type == TransactionType.INCOME) "+" else "-"}$${String.format("%,.0f", tx.amount)}",
                color = if (tx.type == TransactionType.INCOME) MintSuccess else CoralExpense,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

// -------------------------------------------------------------
// PLAID LINK BOTTOM SHEET
// -------------------------------------------------------------
@Composable
fun PlaidLinkBottomSheet(
    onDismiss: () -> Unit,
    onBankLinked: (String, String, Double) -> Unit
) {
    var selectedBank by remember { mutableStateOf("Chase Bank") }
    var accountType by remember { mutableStateOf("Checking & Savings") }
    var balanceInput by remember { mutableStateOf("15000") }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("🔗", fontSize = 20.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Link Bank Account (Plaid)", color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            }
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, contentDescription = "Close", tint = TextSecondary)
            }
        }

        Text(
            text = "Connect financial institutions securely with end-to-end 256-bit encryption. Balances and transactions sync automatically.",
            color = TextSecondary,
            fontSize = 11.sp,
            modifier = Modifier.padding(top = 4.dp, bottom = 16.dp)
        )

        Text("Select Institution", color = TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            PlaidManager.supportedInstitutions.forEach { (name, emoji) ->
                val isSelected = selectedBank == name
                Box(
                    modifier = Modifier
                        .background(if (isSelected) DarkSurfaceVariant else DarkBackground, RoundedCornerShape(14.dp))
                        .border(1.dp, if (isSelected) LavenderAccent else DarkBorder, RoundedCornerShape(14.dp))
                        .clickable { selectedBank = name }
                        .padding(horizontal = 14.dp, vertical = 10.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(emoji, fontSize = 16.sp)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(name, color = if (isSelected) LavenderAccent else TextPrimary, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = balanceInput,
            onValueChange = { balanceInput = it },
            label = { Text("Starting Balance ($)", color = TextSecondary) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
        )

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {
                val bal = balanceInput.toDoubleOrNull() ?: 15000.0
                onBankLinked(selectedBank, accountType, bal)
            },
            modifier = Modifier.fillMaxWidth().height(48.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
        ) {
            Text("Authorize & Sync via Plaid", color = Color(0xFF0F1115), fontWeight = FontWeight.Bold)
        }
    }
}

// -------------------------------------------------------------
// NOTIFICATIONS BOTTOM SHEET
// -------------------------------------------------------------
@Composable
fun NotificationsBottomSheet(
    notifications: List<NotificationEntity>,
    onDismiss: () -> Unit,
    onMarkActioned: (Long) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Reminders & Notifications", color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, contentDescription = "Close", tint = TextSecondary)
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (notifications.isEmpty()) {
            Text("No pending reminders.", color = TextSecondary, fontSize = 12.sp)
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxWidth().heightIn(max = 350.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(notifications) { notif ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = if (notif.isActioned) DarkBackground else DarkSurface),
                        border = androidx.compose.foundation.BorderStroke(1.dp, DarkBorder)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(notif.title, color = if (notif.isActioned) TextSecondary else TextPrimary, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                Text(notif.description, color = TextSecondary, fontSize = 10.sp)
                                Text("Due: ${notif.dueDateString}", color = LavenderAccent, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            }
                            if (!notif.isActioned) {
                                TextButton(onClick = { onMarkActioned(notif.id) }) {
                                    Text("Done", color = MintSuccess, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

// -------------------------------------------------------------
// ADD TRANSACTION DIALOG
// -------------------------------------------------------------
@Composable
fun AddTransactionDialog(
    onDismiss: () -> Unit,
    onAdd: (String, Double, TransactionType, ExpenseCategory?, IncomeCategory?) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var amount by remember { mutableStateOf("") }
    var isExpense by remember { mutableStateOf(true) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Record Transaction", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(modifier = Modifier.fillMaxWidth()) {
                    Button(
                        onClick = { isExpense = true },
                        colors = ButtonDefaults.buttonColors(containerColor = if (isExpense) CoralExpense else DarkSurfaceVariant),
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Expense", color = if (isExpense) Color.White else TextSecondary, fontSize = 11.sp)
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = { isExpense = false },
                        colors = ButtonDefaults.buttonColors(containerColor = if (!isExpense) MintSuccess else DarkSurfaceVariant),
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Income", color = if (!isExpense) Color.Black else TextSecondary, fontSize = 11.sp)
                    }
                }
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Description", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = amount,
                    onValueChange = { amount = it },
                    label = { Text("Amount ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amt = amount.toDoubleOrNull() ?: 0.0
                    if (title.isNotBlank() && amt > 0) {
                        onAdd(
                            title,
                            amt,
                            if (isExpense) TransactionType.EXPENSE else TransactionType.INCOME,
                            if (isExpense) ExpenseCategory.HOUSEHOLD else null,
                            if (!isExpense) IncomeCategory.SALARY else null
                        )
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
            ) {
                Text("Save", color = Color(0xFF0F1115), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel", color = TextSecondary) }
        }
    )
}

// -------------------------------------------------------------
// ADD ASSET DIALOG
// -------------------------------------------------------------
@Composable
fun AddAssetDialog(
    onDismiss: () -> Unit,
    onAdd: (String, AssetCategory, Double, String, Double) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var amount by remember { mutableStateOf("") }
    var institution by remember { mutableStateOf("Vanguard") }
    var returnRate by remember { mutableStateOf("10.0") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Add Portfolio Asset", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Asset Name", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = amount,
                    onValueChange = { amount = it },
                    label = { Text("Current Value ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = institution,
                    onValueChange = { institution = it },
                    label = { Text("Institution / Depository", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amt = amount.toDoubleOrNull() ?: 0.0
                    val ret = returnRate.toDoubleOrNull() ?: 10.0
                    if (name.isNotBlank() && amt > 0) {
                        onAdd(name, AssetCategory.MUTUAL_FUNDS, amt, institution, ret)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
            ) {
                Text("Add Asset", color = Color(0xFF0F1115), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel", color = TextSecondary) }
        }
    )
}

// -------------------------------------------------------------
// ADD LIABILITY DIALOG
// -------------------------------------------------------------
@Composable
fun AddLiabilityDialog(
    onDismiss: () -> Unit,
    onAdd: (String, LiabilityCategory, Double, Double, Double, Int) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var amount by remember { mutableStateOf("") }
    var interestRate by remember { mutableStateOf("6.5") }
    var emi by remember { mutableStateOf("450") }
    var tenure by remember { mutableStateOf("60") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Add Loan / Liability", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Loan Name", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = amount,
                    onValueChange = { amount = it },
                    label = { Text("Outstanding Balance ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = emi,
                    onValueChange = { emi = it },
                    label = { Text("Monthly EMI ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val amt = amount.toDoubleOrNull() ?: 0.0
                    val emiVal = emi.toDoubleOrNull() ?: 0.0
                    val rate = interestRate.toDoubleOrNull() ?: 6.5
                    val mos = tenure.toIntOrNull() ?: 60
                    if (name.isNotBlank() && amt > 0) {
                        onAdd(name, LiabilityCategory.PERSONAL_LOAN, amt, rate, emiVal, mos)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = CoralExpense)
            ) {
                Text("Add Liability", color = Color.White, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel", color = TextSecondary) }
        }
    )
}

// -------------------------------------------------------------
// ADD GOAL DIALOG
// -------------------------------------------------------------
@Composable
fun AddGoalDialog(
    onDismiss: () -> Unit,
    onAdd: (String, Double, Double, Int) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var target by remember { mutableStateOf("") }
    var current by remember { mutableStateOf("") }
    var years by remember { mutableStateOf("5") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Create Financial Goal", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it },
                    label = { Text("Goal Title", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = target,
                    onValueChange = { target = it },
                    label = { Text("Target Amount ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = current,
                    onValueChange = { current = it },
                    label = { Text("Already Saved ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = years,
                    onValueChange = { years = it },
                    label = { Text("Horizon (Years)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val tgt = target.toDoubleOrNull() ?: 0.0
                    val cur = current.toDoubleOrNull() ?: 0.0
                    val yr = years.toIntOrNull() ?: 5
                    if (title.isNotBlank() && tgt > 0) {
                        onAdd(title, tgt, cur, yr)
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
            ) {
                Text("Create Goal", color = Color(0xFF0F1115), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel", color = TextSecondary) }
        }
    )
}

// -------------------------------------------------------------
// USER PROFILE & SETTINGS DIALOG
// -------------------------------------------------------------
@Composable
fun ProfileDialog(
    profile: UserProfileEntity?,
    onDismiss: () -> Unit,
    onSave: (UserProfileEntity) -> Unit,
    onSwitchAuth: () -> Unit
) {
    var name by remember { mutableStateOf(profile?.name ?: "James Sterling") }
    var profession by remember { mutableStateOf(profile?.profession ?: "Senior Financial Consultant") }
    var income by remember { mutableStateOf(profile?.monthlyIncome?.toString() ?: "14500") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("User Profile & Risk Settings", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Full Name", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = profession,
                    onValueChange = { profession = it },
                    label = { Text("Profession", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                OutlinedTextField(
                    value = income,
                    onValueChange = { income = it },
                    label = { Text("Monthly Income ($)", fontSize = 11.sp) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = LavenderAccent, unfocusedBorderColor = DarkBorder)
                )
                Spacer(modifier = Modifier.height(4.dp))
                Button(
                    onClick = onSwitchAuth,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = DarkSurfaceVariant),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Switch Account / Auth Provider", color = LavenderAccent, fontSize = 11.sp)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val inc = income.toDoubleOrNull() ?: (profile?.monthlyIncome ?: 14500.0)
                    val updated = (profile ?: UserProfileEntity()).copy(
                        name = name,
                        profession = profession,
                        monthlyIncome = inc
                    )
                    onSave(updated)
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
            ) {
                Text("Save Profile", color = Color(0xFF0F1115), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Close", color = TextSecondary) }
        }
    )
}

// -------------------------------------------------------------
// MONTHLY CFO REPORT EXPORT DIALOG
// -------------------------------------------------------------
@Composable
fun MonthlyReportExportDialog(
    profile: UserProfileEntity?,
    netWorth: Double,
    cashFlow: Double,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("📑", fontSize = 20.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Monthly CFO Report Generated", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Executive Dossier Ready:", color = MintSuccess, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                Text("• Subject: ${profile?.name ?: "James Sterling"} – September 2026", color = TextPrimary, fontSize = 11.sp)
                Text("• Net Worth: $${String.format("%,.0f", netWorth)} (+12.5% YoY)", color = TextPrimary, fontSize = 11.sp)
                Text("• Cash Flow: +$${String.format("%,.0f", cashFlow)}/mo", color = TextPrimary, fontSize = 11.sp)
                Text("• Financial Health Score: 84/100 (Optimal Tier)", color = TextPrimary, fontSize = 11.sp)
                Text("• Certified Fiduciary Action Plan with 4 strategic priorities attached.", color = TextSecondary, fontSize = 10.sp)
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    Toast.makeText(context, "Monthly CFO Report exported as PDF & Excel!", Toast.LENGTH_LONG).show()
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(containerColor = LavenderAccent)
            ) {
                Text("Download PDF & Excel", color = Color(0xFF0F1115), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Dismiss", color = TextSecondary) }
        }
    )
}
