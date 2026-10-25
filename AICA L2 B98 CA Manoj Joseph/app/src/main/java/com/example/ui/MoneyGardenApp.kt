package com.example.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Category
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.Park
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Spa
import com.example.data.model.CategoryType
import com.example.ui.screens.AddCategoryDialog
import com.example.ui.screens.CategoryManagerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Surface
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import com.example.ui.screens.AddTransactionDialog
import com.example.ui.screens.DashboardScreen
import com.example.ui.screens.FriendsScreen
import com.example.ui.screens.MonthlyReviewDialog
import com.example.ui.screens.OpeningBalancesDialog
import com.example.ui.screens.ReconciliationDialog
import com.example.ui.screens.ReportsScreen
import com.example.ui.screens.SavingsGoalsScreen
import com.example.ui.screens.TransactionsScreen
import com.example.ui.screens.UserProfileDialog
import com.example.ui.screens.WelcomeNamePromptDialog
import com.google.firebase.auth.FirebaseUser

sealed class NavTab(val title: String, val icon: ImageVector, val tag: String) {
    object Dashboard : NavTab("Garden", Icons.Default.Spa, "tab_nav_garden")
    object Transactions : NavTab("Ledger", Icons.Default.ReceiptLong, "tab_nav_ledger")
    object Friends : NavTab("Friends", Icons.Default.Group, "tab_nav_friends")
    object Goals : NavTab("Goals", Icons.Default.Park, "tab_nav_goals")
    object Reports : NavTab("Reports", Icons.Default.Assessment, "tab_nav_reports")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MoneyGardenApp(
    viewModel: MoneyGardenViewModel,
    currentUser: FirebaseUser? = null,
    onSignOut: () -> Unit = {}
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val userMessage by viewModel.userMessage.collectAsStateWithLifecycle()
    val currentUserName = state.userProfile?.displayName?.takeIf { it.isNotBlank() } ?: "You"
    val snackbarHostState = remember { SnackbarHostState() }

    var selectedTabIndex by remember { mutableIntStateOf(0) }
    var showAddTxDialog by remember { mutableStateOf(false) }
    var initialAddTxTab by remember { mutableIntStateOf(0) }
    var showMonthlyReviewDialog by remember { mutableStateOf(false) }
    var showReconciliationDialog by remember { mutableStateOf(false) }
    var showOpeningBalancesDialog by remember { mutableStateOf(false) }
    var showUserProfileDialog by remember { mutableStateOf(false) }
    var showCategoryManagerDialog by remember { mutableStateOf(false) }
    var showAddCategoryDialog by remember { mutableStateOf(false) }
    var categoryTypeToAdd by remember { mutableStateOf<CategoryType?>(null) }

    val navTabs = listOf(
        NavTab.Dashboard,
        NavTab.Transactions,
        NavTab.Friends,
        NavTab.Goals,
        NavTab.Reports
    )

    LaunchedEffect(userMessage) {
        if (userMessage != null) {
            snackbarHostState.showSnackbar(userMessage!!)
            viewModel.clearUserMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Money Garden",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface
                ),
                actions = {
                    IconButton(
                        onClick = { showOpeningBalancesDialog = true },
                        modifier = Modifier.testTag("btn_top_opening_balances")
                    ) {
                        Icon(
                            androidx.compose.material.icons.Icons.Default.AccountBalance,
                            contentDescription = "Opening Balances",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }

                    IconButton(
                        onClick = { showCategoryManagerDialog = true },
                        modifier = Modifier.testTag("btn_top_categories")
                    ) {
                        Icon(
                            androidx.compose.material.icons.Icons.Default.Category,
                            contentDescription = "Manage Categories",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }

                    // Friendly health score badge in top bar
                    Text(
                        text = "${state.healthScore.gradeTitle.split(" ").firstOrNull() ?: "🌱"} ${state.healthScore.totalScore}/100",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(end = 4.dp)
                    )

                    // User Profile / Sign-Out avatar button
                    if (currentUser != null) {
                        IconButton(
                            onClick = { showUserProfileDialog = true },
                            modifier = Modifier.testTag("btn_top_user_profile")
                        ) {
                            val photoUrl = currentUser.photoUrl
                            if (photoUrl != null) {
                                AsyncImage(
                                    model = photoUrl,
                                    contentDescription = "User profile: ${currentUser.displayName ?: "User"}",
                                    modifier = Modifier
                                        .size(32.dp)
                                        .clip(CircleShape)
                                )
                            } else {
                                Surface(
                                    shape = CircleShape,
                                    color = MaterialTheme.colorScheme.primaryContainer,
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Box(contentAlignment = Alignment.Center) {
                                        Text(
                                            text = (currentUser.displayName?.take(1) ?: "U").uppercase(),
                                            style = MaterialTheme.typography.labelMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = MaterialTheme.colorScheme.onPrimaryContainer
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                modifier = Modifier.testTag("bottom_nav_bar")
            ) {
                navTabs.forEachIndexed { index, tab ->
                    NavigationBarItem(
                        selected = selectedTabIndex == index,
                        onClick = { selectedTabIndex = index },
                        icon = { Icon(tab.icon, contentDescription = tab.title) },
                        label = { Text(tab.title) },
                        modifier = Modifier.testTag(tab.tag)
                    )
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTabIndex) {
                0 -> DashboardScreen(
                    state = state,
                    onOpenAddTransaction = { tabIndex ->
                        initialAddTxTab = tabIndex
                        showAddTxDialog = true
                    },
                    onNavigateToFriends = { selectedTabIndex = 2 },
                    onNavigateToGoals = { selectedTabIndex = 3 },
                    onNavigateToTransactions = { selectedTabIndex = 1 },
                    onCheckInNoSpend = { viewModel.recordNoSpendCheckIn() },
                    onOpenOpeningBalances = { showOpeningBalancesDialog = true }
                )
                1 -> TransactionsScreen(
                    state = state,
                    onOpenAddTransaction = {
                        initialAddTxTab = 0
                        showAddTxDialog = true
                    },
                    onReverseTransaction = { txId, reason ->
                        viewModel.reverseTransaction(txId, reason)
                    },
                    onDeleteTransaction = { txId ->
                        viewModel.reverseTransaction(txId, "Deleted by user")
                    },
                    onClearAllTransactions = {
                        viewModel.nullifyAllExistingData()
                    }
                )
                2 -> FriendsScreen(
                    state = state,
                    onAddFriend = { name, nickname, contact, notes ->
                        viewModel.addFriend(name, nickname, contact, notes)
                    },
                    onDeleteFriend = { friendId ->
                        viewModel.deleteFriend(friendId)
                    },
                    onDeleteAllFriends = {
                        viewModel.deleteAllFriends()
                    },
                    onRecordRepaymentFromFriend = { date, amount, friendId, accountId, notes ->
                        viewModel.recordRepaymentFromFriend(amount, friendId, accountId, date, notes)
                    },
                    onRecordRepaymentToFriend = { date, amount, friendId, accountId, notes ->
                        viewModel.recordRepaymentToFriend(amount, friendId, accountId, date, notes)
                    },
                    onOpenOpeningBalances = { showOpeningBalancesDialog = true }
                )
                3 -> SavingsGoalsScreen(
                    state = state,
                    onCreateGoal = { name, target, date, type, notes ->
                        viewModel.createSavingsGoal(name, target, date, type, notes)
                    },
                    onContribute = { id, amount, notes ->
                        viewModel.contributeToGoal(id, amount, notes)
                    },
                    onWithdraw = { id, amount, notes ->
                        viewModel.withdrawFromGoal(id, amount, notes)
                    }
                )
                4 -> {
                    LaunchedEffect(Unit) {
                        viewModel.markReportReviewed()
                    }
                    ReportsScreen(
                        state = state,
                        onExportCsvClick = { viewModel.repository.exportTransactionsCsv() },
                        onOpenMonthlyReview = { showMonthlyReviewDialog = true },
                        onOpenReconciliation = { showReconciliationDialog = true }
                    )
                }
            }
        }
    }

    // Add Transaction Dialog
    if (showAddTxDialog) {
        AddTransactionDialog(
            initialTab = initialAddTxTab,
            accounts = state.accounts,
            categories = state.categories,
            friends = state.friends,
            userName = currentUserName,
            onDismiss = { showAddTxDialog = false },
            onSavePersonalExpense = { date, amount, desc, accId, catId, receiptUri, notes ->
                viewModel.postPersonalExpense(
                    date = date,
                    amountPaise = amount,
                    description = desc,
                    accountId = accId,
                    categoryId = catId,
                    receiptUri = receiptUri,
                    notes = notes
                )
            },
            onSaveSharedExpense = { date, total, arpitaShare, friendAllocations, desc, accId, catId, receiptUri, notes ->
                viewModel.postSharedExpense(
                    date = date,
                    totalAmountPaise = total,
                    personalSharePaise = arpitaShare,
                    friendAllocations = friendAllocations,
                    description = desc,
                    accountId = accId,
                    categoryId = catId,
                    receiptUri = receiptUri,
                    notes = notes
                )
            },
            onSaveFriendPaidExpense = { date, total, arpitaShare, desc, friendId, catId, notes ->
                viewModel.postFriendPaidExpense(
                    date = date,
                    totalPurchaseAmountPaise = total,
                    arpitaSharePaise = arpitaShare,
                    description = desc,
                    friendId = friendId,
                    categoryId = catId,
                    notes = notes
                )
            },
            onSaveIncome = { date, amount, desc, dstAccId, catId, notes ->
                viewModel.postIncome(
                    date = date,
                    amountPaise = amount,
                    description = desc,
                    destinationAccountId = dstAccId,
                    categoryId = catId,
                    notes = notes
                )
            },
            onSaveTransfer = { date, amount, fromId, toId, desc ->
                viewModel.postTransfer(
                    date = date,
                    amountPaise = amount,
                    fromAccountId = fromId,
                    toAccountId = toId,
                    description = desc
                )
            },
            onAddCategory = { name, type, icon, color, onCreated ->
                viewModel.addCategory(name, type, icon, color, onCreated)
            }
        )
    }

    // Monthly Review Wizard
    if (showMonthlyReviewDialog) {
        MonthlyReviewDialog(
            state = state,
            onDismiss = { showMonthlyReviewDialog = false },
            onCompleteReview = { viewModel.markMonthlyReviewCompleted() }
        )
    }

    // Reconciliation Wizard
    if (showReconciliationDialog) {
        ReconciliationDialog(
            accounts = state.accounts,
            onDismiss = { showReconciliationDialog = false },
            onConfirmReconcile = { accId, stmtPaise, notes ->
                viewModel.reconcileAccount(accId, stmtPaise, notes)
            }
        )
    }

    // Opening Balances & Data Setup Dialog
    if (showOpeningBalancesDialog) {
        OpeningBalancesDialog(
            accounts = state.accounts,
            friends = state.friends,
            userName = currentUserName,
            onDismiss = { showOpeningBalancesDialog = false },
            onSaveOpeningBalances = { asOfDate, accBalances, friendRec, friendPay ->
                viewModel.recordOpeningBalances(asOfDate, accBalances, friendRec, friendPay)
            },
            onNullifyAllData = {
                viewModel.nullifyAllExistingData()
            },
            onAddFriend = { name ->
                viewModel.addFriend(name, null, null, null)
            }
        )
    }

    // User Profile & Sign Out Dialog
    if (showUserProfileDialog && currentUser != null) {
        UserProfileDialog(
            user = currentUser,
            currentPreferredName = state.userProfile?.displayName ?: (currentUser.displayName ?: ""),
            onUpdatePreferredName = { newName ->
                viewModel.setPreferredDisplayName(newName, currentUser)
            },
            onManageCategories = { showCategoryManagerDialog = true },
            onDismiss = { showUserProfileDialog = false },
            onSignedOut = {
                showUserProfileDialog = false
                onSignOut()
            }
        )
    }

    // Category Manager Dialog
    if (showCategoryManagerDialog) {
        CategoryManagerDialog(
            categories = state.categories,
            onDismiss = { showCategoryManagerDialog = false },
            onAddCategoryClick = { type ->
                categoryTypeToAdd = type
                showAddCategoryDialog = true
            },
            onDeleteCategory = { catId ->
                viewModel.deleteCategory(catId)
            }
        )
    }

    // Add Category Dialog
    if (showAddCategoryDialog && categoryTypeToAdd != null) {
        AddCategoryDialog(
            initialType = categoryTypeToAdd!!,
            onDismiss = {
                showAddCategoryDialog = false
                categoryTypeToAdd = null
            },
            onCategoryAdded = { name, type, iconName, colorHex ->
                viewModel.addCategory(name, type, iconName, colorHex)
                showAddCategoryDialog = false
                categoryTypeToAdd = null
            }
        )
    }

    // First Sign-In Preferred Name Setup Prompt
    val userProfile = state.userProfile
    if (currentUser != null && userProfile != null && !userProfile.hasSetPreferredName) {
        WelcomeNamePromptDialog(
            initialName = currentUser.displayName?.takeIf { it.isNotBlank() } ?: "",
            onNameConfirmed = { chosenName ->
                viewModel.setPreferredDisplayName(chosenName, currentUser)
            }
        )
    }
}
