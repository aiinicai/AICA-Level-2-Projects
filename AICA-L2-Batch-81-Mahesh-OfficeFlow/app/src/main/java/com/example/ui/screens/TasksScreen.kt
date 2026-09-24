package com.example.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Assignment
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.LocalOffer
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TaskCategory
import com.example.data.model.TaskItem
import com.example.data.model.TaskPriority
import com.example.data.model.TaskStatus
import com.example.data.model.TeamMember
import com.example.data.model.UserRole
import com.example.data.model.tagList
import com.example.ui.components.TaskCard
import com.example.ui.theme.AmberTax
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun TasksScreen(
    tasks: List<TaskItem>,
    teamMembers: List<TeamMember>,
    currentUser: TeamMember?,
    selectedStatusFilter: TaskStatus?,
    selectedPriorityFilter: TaskPriority? = null,
    selectedCategoryFilter: TaskCategory?,
    selectedTagFilter: String? = null,
    selectedMemberFilterId: String?,
    onlyMyTasks: Boolean = false,
    searchQuery: String,
    onStatusFilterChange: (TaskStatus?) -> Unit,
    onPriorityFilterChange: (TaskPriority?) -> Unit = {},
    onCategoryFilterChange: (TaskCategory?) -> Unit,
    onTagFilterChange: (String?) -> Unit = {},
    onMemberFilterChange: (String?) -> Unit,
    onOnlyMyTasksToggle: (Boolean) -> Unit = {},
    onSearchQueryChange: (String) -> Unit,
    onAssignTaskClick: () -> Unit,
    onTaskClick: (TaskItem) -> Unit,
    onPushProgressClick: (TaskItem) -> Unit,
    onStatusChangeClick: (TaskItem, TaskStatus) -> Unit
) {
    val statusTabs = listOf(
        "All" to null,
        "To Do" to TaskStatus.TODO,
        "In Progress" to TaskStatus.IN_PROGRESS,
        "In Review" to TaskStatus.IN_REVIEW,
        "Completed" to TaskStatus.COMPLETED
    )

    val currentTabIndex = statusTabs.indexOfFirst { it.second == selectedStatusFilter }.coerceAtLeast(0)

    // Collect all unique tags across tasks for tag filter row
    val allUniqueTags = remember(tasks) {
        tasks.flatMap { it.tagList }.distinct().filter { it.isNotBlank() }
    }

    val filteredTasks = tasks.filter { task ->
        val matchesStatus = selectedStatusFilter == null || task.status == selectedStatusFilter
        val matchesPriority = selectedPriorityFilter == null || task.priority == selectedPriorityFilter
        val matchesCategory = selectedCategoryFilter == null || task.category == selectedCategoryFilter
        val matchesTag = selectedTagFilter == null || task.tagList.any { it.equals(selectedTagFilter, ignoreCase = true) }
        val matchesMember = if (onlyMyTasks && currentUser != null) {
            task.assignedMemberId == currentUser.id
        } else {
            selectedMemberFilterId == null || task.assignedMemberId == selectedMemberFilterId
        }
        val matchesSearch = searchQuery.isBlank() ||
            task.title.contains(searchQuery, ignoreCase = true) ||
            task.projectName.contains(searchQuery, ignoreCase = true) ||
            task.assignedMemberName.contains(searchQuery, ignoreCase = true) ||
            task.description.contains(searchQuery, ignoreCase = true) ||
            task.tags.contains(searchQuery, ignoreCase = true)
        matchesStatus && matchesPriority && matchesCategory && matchesTag && matchesMember && matchesSearch
    }

    val canAssign = currentUser == null || currentUser.userRole != UserRole.TEAM_MEMBER

    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .testTag("tasks_screen")
        ) {
            // Search Input Box & Tab Header
            Surface(
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 1.dp
            ) {
                Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = onSearchQueryChange,
                        placeholder = { Text("Search tasks, #tags, GST, project, or member...", fontSize = 13.sp) },
                        leadingIcon = {
                            Icon(Icons.Default.Search, contentDescription = null, modifier = Modifier.size(18.dp))
                        },
                        trailingIcon = {
                            if (searchQuery.isNotBlank()) {
                                IconButton(onClick = { onSearchQueryChange("") }) {
                                    Icon(Icons.Default.Clear, contentDescription = "Clear search", modifier = Modifier.size(18.dp))
                                }
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                            .testTag("tasks_search_input"),
                        shape = RoundedCornerShape(12.dp),
                        singleLine = true
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Status Tabs
                    ScrollableTabRow(
                        selectedTabIndex = currentTabIndex,
                        edgePadding = 0.dp,
                        containerColor = Color.Transparent,
                        indicator = { tabPositions ->
                            TabRowDefaults.SecondaryIndicator(
                                Modifier.tabIndicatorOffset(tabPositions[currentTabIndex]),
                                color = SapphirePrimary,
                                height = 3.dp
                            )
                        },
                        divider = {}
                    ) {
                        statusTabs.forEachIndexed { index, (label, status) ->
                            val isSelected = currentTabIndex == index
                            val count = if (status == null) tasks.size else tasks.count { it.status == status }
                            Tab(
                                selected = isSelected,
                                onClick = { onStatusFilterChange(status) },
                                modifier = Modifier.testTag("status_tab_${label.replace(" ", "_")}"),
                                text = {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                                    ) {
                                        Text(
                                            text = label,
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                            color = if (isSelected) SapphirePrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                                            fontSize = 12.sp
                                        )
                                        Surface(
                                            shape = RoundedCornerShape(10.dp),
                                            color = if (isSelected) SapphirePrimary.copy(alpha = 0.15f) else MaterialTheme.colorScheme.surfaceVariant
                                        ) {
                                            Text(
                                                text = "$count",
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = if (isSelected) SapphirePrimary else MaterialTheme.colorScheme.onSurfaceVariant,
                                                modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp)
                                            )
                                        }
                                    }
                                }
                            )
                        }
                    }
                }
            }

            // Priority & Quick Role Filters Row
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp, bottom = 4.dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // "My Tasks Only" filter (especially great for Team Members)
                if (currentUser != null) {
                    item {
                        FilterChip(
                            selected = onlyMyTasks,
                            onClick = { onOnlyMyTasksToggle(!onlyMyTasks) },
                            label = {
                                Text(
                                    text = if (onlyMyTasks) "✓ My Tasks (${currentUser.name})" else "My Tasks Only",
                                    fontSize = 11.sp,
                                    fontWeight = if (onlyMyTasks) FontWeight.Bold else FontWeight.Normal
                                )
                            },
                            modifier = Modifier.testTag("filter_my_tasks")
                        )
                    }
                }

                // Priority Filter Chips
                item {
                    FilterChip(
                        selected = selectedPriorityFilter == null,
                        onClick = { onPriorityFilterChange(null) },
                        label = { Text("All Priorities", fontSize = 11.sp) },
                        modifier = Modifier.testTag("priority_filter_all")
                    )
                }

                items(TaskPriority.values()) { priority ->
                    val isSelected = selectedPriorityFilter == priority
                    val prioColor = when (priority) {
                        TaskPriority.LOW -> EmeraldSuccess
                        TaskPriority.MEDIUM -> SapphirePrimary
                        TaskPriority.HIGH -> AmberTax
                        TaskPriority.URGENT -> RoseUrgent
                    }
                    FilterChip(
                        selected = isSelected,
                        onClick = { onPriorityFilterChange(if (isSelected) null else priority) },
                        label = {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.Flag,
                                    contentDescription = null,
                                    tint = prioColor,
                                    modifier = Modifier.size(12.dp)
                                )
                                Spacer(modifier = Modifier.width(3.dp))
                                Text(priority.name, fontSize = 11.sp, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal)
                            }
                        },
                        modifier = Modifier.testTag("priority_filter_${priority.name}")
                    )
                }
            }

            // Tag & Category Filter Row
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 6.dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // Category Filter Pills
                item {
                    FilterChip(
                        selected = selectedCategoryFilter == null && selectedTagFilter == null,
                        onClick = {
                            onCategoryFilterChange(null)
                            onTagFilterChange(null)
                        },
                        label = { Text("All Categories", fontSize = 11.sp) },
                        modifier = Modifier.testTag("category_filter_all")
                    )
                }

                items(TaskCategory.values()) { category ->
                    val isSelected = selectedCategoryFilter == category
                    FilterChip(
                        selected = isSelected,
                        onClick = { onCategoryFilterChange(if (isSelected) null else category) },
                        label = { Text(category.name.replace("_", " "), fontSize = 11.sp) },
                        modifier = Modifier.testTag("category_filter_${category.name}")
                    )
                }

                // Custom Tag Filter Chips
                items(allUniqueTags) { tag ->
                    val isSelected = selectedTagFilter == tag
                    FilterChip(
                        selected = isSelected,
                        onClick = { onTagFilterChange(if (isSelected) null else tag) },
                        label = {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.LocalOffer,
                                    contentDescription = null,
                                    modifier = Modifier.size(11.dp),
                                    tint = if (isSelected) SapphirePrimary else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Spacer(modifier = Modifier.width(3.dp))
                                Text("#$tag", fontSize = 11.sp, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal)
                            }
                        },
                        modifier = Modifier.testTag("tag_filter_$tag")
                    )
                }

                // Member Filter pills
                items(teamMembers) { member ->
                    val isSelected = selectedMemberFilterId == member.id
                    FilterChip(
                        selected = isSelected,
                        onClick = { onMemberFilterChange(if (isSelected) null else member.id) },
                        label = { Text("👤 ${member.name}", fontSize = 11.sp) },
                        modifier = Modifier.testTag("member_filter_${member.id}")
                    )
                }
            }

            // Task List
            if (filteredTasks.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(64.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.surfaceVariant),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Assignment,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(32.dp)
                            )
                        }
                        Text(
                            text = "No tasks found matching criteria",
                            fontWeight = FontWeight.Bold,
                            fontSize = 16.sp
                        )
                        Text(
                            text = "Try clearing filters or assign a new task to your team.",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 80.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredTasks, key = { it.id }) { task ->
                        TaskCard(
                            task = task,
                            onClick = { onTaskClick(task) },
                            onPushProgressClick = { onPushProgressClick(task) },
                            onStatusChangeClick = { newStatus -> onStatusChangeClick(task, newStatus) }
                        )
                    }
                }
            }
        }

        // Floating Action Button to Assign Task (Role Aware)
        if (canAssign) {
            FloatingActionButton(
                onClick = onAssignTaskClick,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(20.dp)
                    .testTag("fab_assign_task"),
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Assign Task")
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Assign Task", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
            }
        }
    }
}

