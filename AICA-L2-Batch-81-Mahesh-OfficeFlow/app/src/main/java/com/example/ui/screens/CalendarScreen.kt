package com.example.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Today
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.Project
import com.example.data.model.TaskCategory
import com.example.data.model.TaskItem
import com.example.data.model.TaskPriority
import com.example.data.model.TaskStatus
import com.example.data.model.TaxNotification
import com.example.data.model.TeamMember
import com.example.ui.components.TaskCard
import com.example.ui.components.TaxNotificationCard
import com.example.ui.theme.AmberTax
import com.example.ui.theme.AmberTaxLight
import com.example.ui.theme.EmeraldSuccess
import com.example.ui.theme.RoseUrgent
import com.example.ui.theme.SapphirePrimary
import com.example.ui.theme.TealSecondary
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

@Composable
fun CalendarScreen(
    tasks: List<TaskItem>,
    projects: List<Project>,
    taxNotifications: List<TaxNotification>,
    teamMembers: List<TeamMember>,
    selectedDateMillis: Long,
    onDateSelected: (Long) -> Unit,
    onAssignTaskOnDate: (Long) -> Unit,
    onTaskClick: (TaskItem) -> Unit,
    onPushTaskProgressClick: (TaskItem) -> Unit,
    onTaxAlertClick: (TaxNotification) -> Unit,
    canAssignTasks: Boolean = true
) {
    var selectedMemberId by remember { mutableStateOf<String?>(null) }
    var calendarMonthOffset by remember { mutableIntStateOf(0) }

    val cal = Calendar.getInstance().apply {
        set(Calendar.DAY_OF_MONTH, 1)
        set(Calendar.HOUR_OF_DAY, 12)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
        add(Calendar.MONTH, calendarMonthOffset)
    }

    val currentMonthName = cal.getDisplayName(Calendar.MONTH, Calendar.LONG, Locale.getDefault()) ?: ""
    val currentYear = cal.get(Calendar.YEAR)

    val daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH)
    val firstDayOfWeek = cal.get(Calendar.DAY_OF_WEEK) // 1 = Sunday, 2 = Monday...

    val dayFormat = SimpleDateFormat("EEEE, dd MMMM yyyy", Locale.getDefault())
    val selectedDayStart = getDayStart(selectedDateMillis)
    val selectedDayEnd = selectedDayStart + (24L * 60 * 60 * 1000)

    // Filter items by member if selected
    val filteredTasks = tasks.filter { selectedMemberId == null || it.assignedMemberId == selectedMemberId }

    // Deadlines scheduled on selected date
    val tasksOnSelectedDate = filteredTasks.filter {
        it.dueDateMillis in selectedDayStart until selectedDayEnd
    }

    val taxDeadlinesOnSelectedDate = taxNotifications.filter {
        it.deadlineDateMillis in selectedDayStart until selectedDayEnd
    }

    val projectsTargetOnSelectedDate = projects.filter {
        it.targetDateMillis in selectedDayStart until selectedDayEnd
    }

    val dayNames = listOf("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .testTag("calendar_screen"),
            contentPadding = PaddingValues(bottom = 80.dp)
        ) {
            // Calendar Header: Month Switcher & Member Filter
            item {
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    tonalElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "$currentMonthName $currentYear",
                                    style = MaterialTheme.typography.titleLarge.copy(
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurface
                                    )
                                )
                                Text(
                                    text = "Team Deadlines & Tax Compliance Calendar",
                                    style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                                )
                            }

                            Row(verticalAlignment = Alignment.CenterVertically) {
                                IconButton(
                                    onClick = { calendarMonthOffset-- },
                                    modifier = Modifier.testTag("prev_month_btn")
                                ) {
                                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowLeft, contentDescription = "Previous Month")
                                }

                                TextButton(
                                    onClick = {
                                        calendarMonthOffset = 0
                                        onDateSelected(System.currentTimeMillis())
                                    },
                                    modifier = Modifier.testTag("today_btn")
                                ) {
                                    Text("Today", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                }

                                IconButton(
                                    onClick = { calendarMonthOffset++ },
                                    modifier = Modifier.testTag("next_month_btn")
                                ) {
                                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = "Next Month")
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Member Filter Chips
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            item {
                                FilterChip(
                                    selected = selectedMemberId == null,
                                    onClick = { selectedMemberId = null },
                                    label = { Text("All Team Deadlines", fontSize = 11.sp) },
                                    modifier = Modifier.testTag("calendar_filter_all_members")
                                )
                            }
                            items(teamMembers) { member ->
                                val isSelected = selectedMemberId == member.id
                                FilterChip(
                                    selected = isSelected,
                                    onClick = { selectedMemberId = if (isSelected) null else member.id },
                                    label = { Text(member.name, fontSize = 11.sp) },
                                    modifier = Modifier.testTag("calendar_filter_member_${member.id}")
                                )
                            }
                        }
                    }
                }
            }

            // Month Grid Card
            item {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        // Day of week headers
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            dayNames.forEach { dayName ->
                                Text(
                                    text = dayName,
                                    modifier = Modifier.weight(1f),
                                    textAlign = TextAlign.Center,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        // Days Grid
                        val totalCells = (firstDayOfWeek - 1) + daysInMonth
                        val rows = (totalCells + 6) / 7

                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            for (row in 0 until rows) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    for (col in 0 until 7) {
                                        val cellIndex = row * 7 + col
                                        val dayNumber = cellIndex - (firstDayOfWeek - 1) + 1

                                        if (dayNumber in 1..daysInMonth) {
                                            val cellCal = (cal.clone() as Calendar).apply {
                                                set(Calendar.DAY_OF_MONTH, dayNumber)
                                            }
                                            val cellMillis = cellCal.timeInMillis
                                            val cellDayStart = getDayStart(cellMillis)
                                            val cellDayEnd = cellDayStart + (24L * 60 * 60 * 1000)

                                            val isSelected = getDayStart(selectedDateMillis) == cellDayStart
                                            val isToday = getDayStart(System.currentTimeMillis()) == cellDayStart

                                            // Count deadlines on this day
                                            val dayTasks = filteredTasks.filter { it.dueDateMillis in cellDayStart until cellDayEnd }
                                            val dayTax = taxNotifications.filter { it.deadlineDateMillis in cellDayStart until cellDayEnd }
                                            val hasDeadlines = dayTasks.isNotEmpty() || dayTax.isNotEmpty()

                                            Box(
                                                modifier = Modifier
                                                    .weight(1f)
                                                    .aspectRatio(1f)
                                                    .clip(RoundedCornerShape(8.dp))
                                                    .background(
                                                        if (isSelected) SapphirePrimary
                                                        else if (isToday) SapphirePrimary.copy(alpha = 0.12f)
                                                        else Color.Transparent
                                                    )
                                                    .border(
                                                        width = if (isToday && !isSelected) 1.5.dp else 0.dp,
                                                        color = if (isToday && !isSelected) SapphirePrimary else Color.Transparent,
                                                        shape = RoundedCornerShape(8.dp)
                                                    )
                                                    .clickable { onDateSelected(cellMillis) }
                                                    .padding(2.dp)
                                                    .testTag("cal_day_$dayNumber"),
                                                contentAlignment = Alignment.Center
                                            ) {
                                                Column(
                                                    horizontalAlignment = Alignment.CenterHorizontally,
                                                    verticalArrangement = Arrangement.Center
                                                ) {
                                                    Text(
                                                        text = "$dayNumber",
                                                        fontSize = 12.sp,
                                                        fontWeight = if (isSelected || isToday) FontWeight.Bold else FontWeight.Medium,
                                                        color = if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface
                                                    )
                                                    if (hasDeadlines) {
                                                        Row(
                                                            horizontalArrangement = Arrangement.spacedBy(2.dp),
                                                            verticalAlignment = Alignment.CenterVertically,
                                                            modifier = Modifier.padding(top = 2.dp)
                                                        ) {
                                                            if (dayTasks.isNotEmpty()) {
                                                                Box(
                                                                    modifier = Modifier
                                                                        .size(4.dp)
                                                                        .clip(CircleShape)
                                                                        .background(if (isSelected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.primary)
                                                                )
                                                            }
                                                            if (dayTax.isNotEmpty()) {
                                                                Box(
                                                                    modifier = Modifier
                                                                        .size(4.dp)
                                                                        .clip(CircleShape)
                                                                        .background(if (isSelected) AmberTaxLight else AmberTax)
                                                                )
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        } else {
                                            Spacer(modifier = Modifier.weight(1f))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Selected Day Header
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = dayFormat.format(Date(selectedDateMillis)),
                            style = MaterialTheme.typography.titleMedium.copy(
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        )
                        Text(
                            text = "${tasksOnSelectedDate.size} Tasks • ${taxDeadlinesOnSelectedDate.size} Tax Due Dates",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    if (canAssignTasks) {
                        TextButton(
                            onClick = { onAssignTaskOnDate(selectedDateMillis) },
                            modifier = Modifier.testTag("add_task_on_date_btn")
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("+ Task", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }
                }
            }

            // Statutory Tax Deadlines on this Date
            if (taxDeadlinesOnSelectedDate.isNotEmpty()) {
                item {
                    Text(
                        text = "🏛 Statutory Tax Compliance Due Today",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = AmberTax,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                    )
                }
                items(taxDeadlinesOnSelectedDate) { taxNotice ->
                    Box(modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)) {
                        TaxNotificationCard(
                            notification = taxNotice,
                            onBroadcastAlert = {},
                            onConvertToTask = {},
                            onClick = { onTaxAlertClick(taxNotice) }
                        )
                    }
                }
            }

            // Tasks on this Date
            if (tasksOnSelectedDate.isNotEmpty()) {
                item {
                    Text(
                        text = "📋 Assigned Team Tasks Due",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                    )
                }
                items(tasksOnSelectedDate) { task ->
                    Box(modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)) {
                        TaskCard(
                            task = task,
                            onClick = { onTaskClick(task) },
                            onPushProgressClick = { onPushTaskProgressClick(task) },
                            onStatusChangeClick = {}
                        )
                    }
                }
            }

            // Empty state for selected date
            if (tasksOnSelectedDate.isEmpty() && taxDeadlinesOnSelectedDate.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Column(
                            modifier = Modifier.padding(20.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Event,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(32.dp)
                            )
                            Text(
                                text = "No team deadlines scheduled for this day",
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 14.sp
                            )
                            Text(
                                text = "Tap '+ Task' to schedule a deliverable or compliance milestone.",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
            }
        }

        // FAB to quickly schedule on date (Role Aware)
        if (canAssignTasks) {
            FloatingActionButton(
                onClick = { onAssignTaskOnDate(selectedDateMillis) },
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(20.dp)
                    .testTag("fab_calendar_add_task"),
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add Task on Date")
            }
        }
    }
}

private fun getDayStart(millis: Long): Long {
    val cal = Calendar.getInstance().apply {
        timeInMillis = millis
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }
    return cal.timeInMillis
}
