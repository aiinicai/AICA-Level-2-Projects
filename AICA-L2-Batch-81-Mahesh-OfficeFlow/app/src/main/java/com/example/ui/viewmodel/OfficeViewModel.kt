package com.example.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.model.OfficeActivityNotification
import com.example.data.model.PortalIntegration
import com.example.data.model.Project
import com.example.data.model.TaskCategory
import com.example.data.model.TaskItem
import com.example.data.model.TaskPriority
import com.example.data.model.TaskStatus
import com.example.data.model.TaxDepartment
import com.example.data.model.TaxNotification
import com.example.data.model.TaxSeverity
import com.example.data.model.TeamMember
import com.example.data.model.UserRole
import com.example.data.repository.OfficeRepository
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.FirebaseAuthInvalidUserException
import com.google.firebase.firestore.FirebaseFirestoreException
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.Calendar

class OfficeViewModel(application: Application) : AndroidViewModel(application) {
    private val repository = OfficeRepository.getInstance(application)

    private val _currentUser = MutableStateFlow<TeamMember?>(null)
    val currentUser: StateFlow<TeamMember?> = _currentUser.asStateFlow()

    // Each shared flow re-subscribes whenever the signed-in user changes: the Firestore query
    // must match what that role is allowed to read, or the rules reject the whole listener.
    //
    // catch{} is not belt-and-braces here — it is load-bearing. stateIn runs the flow in
    // viewModelScope, whose coroutine has NO exception handler, so any error escaping one of
    // these would crash the app rather than surface as a message.
    @OptIn(ExperimentalCoroutinesApi::class)
    val tasks: StateFlow<List<TaskItem>> = currentUser
        .flatMapLatest { member -> repository.tasksFor(member) }
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    @OptIn(ExperimentalCoroutinesApi::class)
    val projects: StateFlow<List<Project>> = currentUser
        .flatMapLatest { member -> repository.projectsFor(member) }
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    @OptIn(ExperimentalCoroutinesApi::class)
    val teamMembers: StateFlow<List<TeamMember>> = currentUser
        .flatMapLatest { member -> repository.teamMembersFor(member) }
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val taxNotifications: StateFlow<List<TaxNotification>> = repository.allTaxNotifications
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val activityNotifications: StateFlow<List<OfficeActivityNotification>> = repository.allActivityNotifications
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val portalIntegrations: StateFlow<List<PortalIntegration>> = repository.allPortalIntegrations
        .catch { emit(emptyList()) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // UI Navigation & Filters
    private val _currentScreen = MutableStateFlow(0) // 0: Dashboard, 1: Tasks, 2: Projects, 3: Calendar, 4: Tax Alerts
    val currentScreen: StateFlow<Int> = _currentScreen.asStateFlow()

    // Active User Persona & Role Management
    private val _isAuthenticated = MutableStateFlow(false)
    val isAuthenticated: StateFlow<Boolean> = _isAuthenticated.asStateFlow()

    // Role-scoped task list: Admins & Partners see everything; a Manager only sees tasks
    // they assigned or that were assigned to them; a Team Member only sees tasks assigned
    // to them. This is what every screen should render instead of the raw `tasks` flow.
    val visibleTasks: StateFlow<List<TaskItem>> = combine(tasks, currentUser) { allTasks, user ->
        when {
            user == null -> allTasks
            user.userRole == UserRole.ADMIN || user.userRole == UserRole.PARTNER -> allTasks
            user.userRole == UserRole.MANAGER -> allTasks.filter {
                it.assignedMemberId == user.id || it.assignedByMemberId == user.id
            }
            else -> allTasks.filter { it.assignedMemberId == user.id }
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _selectedCalendarDateMillis = MutableStateFlow(getStartOfDay(System.currentTimeMillis()))
    val selectedCalendarDateMillis: StateFlow<Long> = _selectedCalendarDateMillis.asStateFlow()

    private val _taskStatusFilter = MutableStateFlow<TaskStatus?>(null)
    val taskStatusFilter: StateFlow<TaskStatus?> = _taskStatusFilter.asStateFlow()

    private val _taskPriorityFilter = MutableStateFlow<TaskPriority?>(null)
    val taskPriorityFilter: StateFlow<TaskPriority?> = _taskPriorityFilter.asStateFlow()

    private val _taskCategoryFilter = MutableStateFlow<TaskCategory?>(null)
    val taskCategoryFilter: StateFlow<TaskCategory?> = _taskCategoryFilter.asStateFlow()

    private val _taskTagFilter = MutableStateFlow<String?>(null)
    val taskTagFilter: StateFlow<String?> = _taskTagFilter.asStateFlow()

    private val _memberFilterId = MutableStateFlow<String?>(null)
    val memberFilterId: StateFlow<String?> = _memberFilterId.asStateFlow()

    private val _onlyMyTasksFilter = MutableStateFlow(false)
    val onlyMyTasksFilter: StateFlow<Boolean> = _onlyMyTasksFilter.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _taxDepartmentFilter = MutableStateFlow<TaxDepartment?>(null)
    val taxDepartmentFilter: StateFlow<TaxDepartment?> = _taxDepartmentFilter.asStateFlow()

    private val _snackbarMessage = MutableStateFlow<String?>(null)
    val snackbarMessage: StateFlow<String?> = _snackbarMessage.asStateFlow()

    // Repository calls now hit Firestore, so any of them can fail (offline, or rejected by
    // security rules). Without this, an uncaught failure in a launched coroutine crashes the
    // app instead of telling the user what went wrong.
    private val errorHandler = CoroutineExceptionHandler { _, throwable ->
        showSnackbar(describeFailure(throwable))
    }

    init {
        restoreSession()
        // Surface workspace connection/permission problems instead of showing an empty app.
        viewModelScope.launch(errorHandler) {
            repository.workspaceError.collect { error ->
                if (error != null) showSnackbar(error)
            }
        }
    }

    private fun describeFailure(throwable: Throwable): String = when {
        throwable is FirebaseFirestoreException &&
            throwable.code == FirebaseFirestoreException.Code.PERMISSION_DENIED ->
            "Database access denied. Check the Firestore security rules for this project."
        throwable is FirebaseFirestoreException &&
            throwable.code == FirebaseFirestoreException.Code.UNAVAILABLE ->
            "No connection to the workspace. Your change is saved locally and will sync when you are back online."
        else -> "Something went wrong: ${throwable.message ?: throwable::class.java.simpleName}"
    }

    // --- Authentication & Session ---
    fun login(email: String, password: String, onResult: (Boolean, String) -> Unit) {
        viewModelScope.launch(errorHandler) {
            // Caught here rather than left to errorHandler: onResult must always fire, or the
            // Sign In button stays disabled and the user is stuck on the login screen.
            val user = try {
                repository.signIn(email, password)
            } catch (e: Exception) {
                onResult(false, describeAuthFailure(e))
                return@launch
            }
            _currentUser.value = user
            _isAuthenticated.value = true
            showSnackbar("Welcome back, ${user.name}! Logged in as ${user.userRole.displayName}.")
            onResult(true, "Authentication successful")
        }
    }

    fun logout() {
        repository.signOut()
        _currentUser.value = null
        _isAuthenticated.value = false
        showSnackbar("You have been signed out.")
    }

    /** Restores a Firebase Auth session so a returning user is not asked to sign in again. */
    private fun restoreSession() {
        viewModelScope.launch(errorHandler) {
            val member = try {
                repository.restoreSession()
            } catch (_: Exception) {
                null
            }
            if (member != null) {
                _currentUser.value = member
                _isAuthenticated.value = true
            }
        }
    }

    private fun describeAuthFailure(throwable: Throwable): String = when (throwable) {
        is FirebaseAuthInvalidUserException ->
            "No account exists for that email address. Ask an administrator to onboard you."
        is FirebaseAuthInvalidCredentialsException ->
            "Incorrect email or password."
        else -> throwable.message ?: describeFailure(throwable)
    }

    // Role & Permission Checks
    fun getCurrentUserRole(): com.example.data.model.UserRole {
        return _currentUser.value?.userRole ?: com.example.data.model.UserRole.ADMIN
    }

    fun canAssignTasks(): Boolean {
        val role = getCurrentUserRole()
        return role == com.example.data.model.UserRole.ADMIN || role == com.example.data.model.UserRole.PARTNER || role == com.example.data.model.UserRole.MANAGER
    }

    fun canCreateProjects(): Boolean {
        val role = getCurrentUserRole()
        return role == com.example.data.model.UserRole.ADMIN || role == com.example.data.model.UserRole.PARTNER || role == com.example.data.model.UserRole.MANAGER
    }

    fun canDeleteTasks(): Boolean {
        val role = getCurrentUserRole()
        return role == com.example.data.model.UserRole.ADMIN || role == com.example.data.model.UserRole.PARTNER
    }

    fun canBroadcastTax(): Boolean {
        val role = getCurrentUserRole()
        return role == com.example.data.model.UserRole.ADMIN || role == com.example.data.model.UserRole.PARTNER || role == com.example.data.model.UserRole.MANAGER
    }

    /** Only Admin & Partner can add, edit, remove, or re-role team members. */
    fun canManageTeam(): Boolean {
        val role = getCurrentUserRole()
        return role == com.example.data.model.UserRole.ADMIN || role == com.example.data.model.UserRole.PARTNER
    }

    /** Team Workload view: everyone except a plain Team Member. */
    fun canViewTeamWorkload(): Boolean {
        return getCurrentUserRole() != com.example.data.model.UserRole.TEAM_MEMBER
    }

    fun canPushProgressFor(task: TaskItem): Boolean {
        val user = _currentUser.value ?: return true
        if (user.userRole == com.example.data.model.UserRole.ADMIN || user.userRole == com.example.data.model.UserRole.PARTNER || user.userRole == com.example.data.model.UserRole.MANAGER) {
            return true
        }
        // Team member can push progress if assigned or general
        return task.assignedMemberId == user.id || task.assignedMemberId.isBlank()
    }

    // Persona switching was removed with the move to Firebase Auth: the signed-in identity is
    // what Firestore rules enforce, so pretending to be someone else would show a role the
    // server will not honour and attribute that person's writes to the wrong account.

    fun setScreen(index: Int) {
        _currentScreen.value = index
    }

    fun setSelectedCalendarDate(dateMillis: Long) {
        _selectedCalendarDateMillis.value = getStartOfDay(dateMillis)
    }

    fun setTaskStatusFilter(status: TaskStatus?) {
        _taskStatusFilter.value = status
    }

    fun setTaskPriorityFilter(priority: TaskPriority?) {
        _taskPriorityFilter.value = priority
    }

    fun setTaskCategoryFilter(category: TaskCategory?) {
        _taskCategoryFilter.value = category
    }

    fun setTaskTagFilter(tag: String?) {
        _taskTagFilter.value = tag
    }

    fun setMemberFilter(memberId: String?) {
        _memberFilterId.value = memberId
    }

    fun setOnlyMyTasksFilter(enabled: Boolean) {
        _onlyMyTasksFilter.value = enabled
    }

    fun setSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun setTaxDepartmentFilter(dept: TaxDepartment?) {
        _taxDepartmentFilter.value = dept
    }

    fun clearSnackbar() {
        _snackbarMessage.value = null
    }

    fun showSnackbar(msg: String) {
        _snackbarMessage.value = msg
    }

    // --- Action Handlers ---
    fun assignTask(
        title: String,
        description: String,
        member: TeamMember,
        project: Project?,
        priority: TaskPriority,
        dueDateMillis: Long,
        category: TaskCategory,
        checklist: String,
        tags: String = "",
        assignedBy: String? = null
    ) {
        if (!canAssignTasks()) {
            showSnackbar("Permission Denied: Only Admins and Managers can assign tasks.")
            return
        }
        val actor = assignedBy ?: _currentUser.value?.name ?: "Mahesh"
        val actorId = _currentUser.value?.id ?: ""
        viewModelScope.launch(errorHandler) {
            repository.assignTask(
                title = title,
                description = description,
                member = member,
                project = project,
                priority = priority,
                dueDateMillis = dueDateMillis,
                category = category,
                checklistItems = checklist,
                tags = tags,
                assignedBy = actor,
                assignedByMemberId = actorId
            )
            showSnackbar("Task successfully assigned to ${member.name} (${priority.name} Priority)!")
        }
    }

    fun updateTaskStatus(task: TaskItem, newStatus: TaskStatus) {
        viewModelScope.launch(errorHandler) {
            repository.updateTaskStatus(task, newStatus)
            showSnackbar("Status updated: ${task.title} is now ${newStatus.name.replace("_", " ")}")
        }
    }

    fun pushTaskProgress(
        taskId: String,
        progressPercentage: Int,
        remark: String,
        status: TaskStatus,
        completedCount: Int,
        actorName: String = "Team Member"
    ) {
        viewModelScope.launch(errorHandler) {
            repository.pushTaskProgress(
                taskId = taskId,
                progressPercentage = progressPercentage,
                remark = remark,
                status = status,
                completedChecklistItems = completedCount,
                actorName = actorName
            )
            showSnackbar("Progress pushed! $progressPercentage% broadcasted to dashboard & notifications.")
        }
    }

    fun pushProjectProgress(
        projectId: String,
        progressPercentage: Int,
        remark: String,
        actorName: String = "Project Lead"
    ) {
        viewModelScope.launch(errorHandler) {
            repository.pushProjectProgress(
                projectId = projectId,
                newProgress = progressPercentage,
                remark = remark,
                actorName = actorName
            )
            showSnackbar("Project milestone pushed ($progressPercentage%) & broadcasted.")
        }
    }

    fun broadcastTaxAlert(notification: TaxNotification) {
        if (!canBroadcastTax()) {
            showSnackbar("Permission Denied: Only Admins and Managers can broadcast tax notices.")
            return
        }
        viewModelScope.launch(errorHandler) {
            repository.pushTaxNotificationAlert(notification)
            showSnackbar("Tax notification pushed to team: ${notification.circularOrNotificationNo}")
        }
    }

    fun convertTaxNoticeToTask(
        notification: TaxNotification,
        assignedMember: TeamMember,
        project: Project?
    ) {
        if (!canAssignTasks()) {
            showSnackbar("Permission Denied: Only Admins and Managers can assign tasks from notices.")
            return
        }
        val actor = _currentUser.value?.name ?: "Compliance Office"
        val actorId = _currentUser.value?.id ?: ""
        viewModelScope.launch(errorHandler) {
            repository.convertTaxNotificationToTask(notification, assignedMember, project, actorId, actor)
            showSnackbar("Converted notice to task assigned to ${assignedMember.name}!")
        }
    }

    fun createCustomTaxNotification(
        title: String,
        department: TaxDepartment,
        circularNumber: String,
        summary: String,
        keyActions: String,
        deadlineMillis: Long,
        severity: TaxSeverity,
        source: String
    ) {
        if (!canBroadcastTax()) {
            showSnackbar("Permission Denied: Only Admins and Managers can create tax notices.")
            return
        }
        viewModelScope.launch(errorHandler) {
            repository.createCustomTaxNotification(
                title = title,
                department = department,
                circularNumber = circularNumber,
                summary = summary,
                keyActions = keyActions,
                deadlineMillis = deadlineMillis,
                severity = severity,
                source = source
            )
            showSnackbar("Tax statutory notice created & broadcasted to team!")
        }
    }

    fun createProject(
        name: String,
        code: String,
        clientName: String,
        description: String,
        leadName: String,
        targetDateMillis: Long,
        category: String,
        colorHex: String
    ) {
        if (!canCreateProjects()) {
            showSnackbar("Permission Denied: Only Admins and Managers can create projects.")
            return
        }
        viewModelScope.launch(errorHandler) {
            repository.createProject(
                name = name,
                code = code,
                clientName = clientName,
                description = description,
                leadMemberName = leadName,
                targetDateMillis = targetDateMillis,
                category = category,
                colorHex = colorHex
            )
            showSnackbar("Project '$name' created successfully!")
        }
    }

    fun addTeamMember(
        name: String,
        role: String,
        userRole: UserRole = UserRole.TEAM_MEMBER,
        department: String,
        email: String,
        phone: String,
        colorHex: String,
        password: String = "office123"
    ) {
        if (!canManageTeam()) {
            showSnackbar("Permission Denied: Only Admins and Partners can onboard team members.")
            return
        }
        val actor = _currentUser.value?.name ?: "Admin"
        viewModelScope.launch(errorHandler) {
            repository.addTeamMember(
                name = name,
                role = role,
                userRole = userRole,
                department = department,
                email = email,
                phone = phone,
                avatarColorHex = colorHex,
                password = password,
                actorName = actor
            )
            showSnackbar("Team member '$name' onboarded with active login account ($email)!")
        }
    }

    fun updateTeamMember(member: TeamMember) {
        val actor = _currentUser.value?.name ?: "Admin"
        viewModelScope.launch(errorHandler) {
            repository.updateTeamMember(member, actor)
            // If the updated member is current user, update session as well
            if (_currentUser.value?.id == member.id) {
                _currentUser.value = member
            }
            showSnackbar("Updated profile for ${member.name} (${member.userRole.displayName})")
        }
    }

    fun updateTeamMemberRole(memberId: String, newRole: UserRole) {
        if (!canManageTeam()) {
            showSnackbar("Permission Denied: Only Admins and Partners can change security roles.")
            return
        }
        val actor = _currentUser.value?.name ?: "Admin"
        viewModelScope.launch(errorHandler) {
            repository.updateTeamMemberRole(memberId, newRole, actor)
            if (_currentUser.value?.id == memberId) {
                _currentUser.value = _currentUser.value?.copy(userRole = newRole)
            }
            val memberName = teamMembers.value.firstOrNull { it.id == memberId }?.name ?: "team member"
            showSnackbar("Role changed to ${newRole.displayName} for $memberName")
        }
    }

    fun deleteTeamMember(member: TeamMember) {
        if (!canManageTeam()) {
            showSnackbar("Permission Denied: Only Admins and Partners can remove team members.")
            return
        }
        val actor = _currentUser.value?.name ?: "Admin"
        viewModelScope.launch(errorHandler) {
            repository.deleteTeamMember(member, actor)
            if (_currentUser.value?.id == member.id) {
                // switch to first remaining
                val remaining = teamMembers.value.filter { it.id != member.id }
                if (remaining.isNotEmpty()) {
                    _currentUser.value = remaining.first()
                }
            }
            showSnackbar("Removed ${member.name} from team database.")
        }
    }

    // --- Website & Portal Integrations ---
    fun addPortalIntegration(portal: PortalIntegration) {
        val actor = _currentUser.value?.name ?: "Admin"
        viewModelScope.launch(errorHandler) {
            repository.addPortalIntegration(portal, actor)
            showSnackbar("Integration portal '${portal.name}' configured and saved!")
        }
    }

    fun updatePortalIntegration(portal: PortalIntegration) {
        viewModelScope.launch(errorHandler) {
            repository.updatePortalIntegration(portal)
            showSnackbar("Updated settings for ${portal.name}")
        }
    }

    fun testPortalSync(portal: PortalIntegration) {
        val actor = _currentUser.value?.name ?: "Admin"
        viewModelScope.launch(errorHandler) {
            val success = repository.testPortalSync(portal.id, actor)
            if (success) {
                showSnackbar("Live ping handshake successful for ${portal.name} (HTTP 200 OK)")
            } else {
                showSnackbar("Could not connect to ${portal.name}")
            }
        }
    }

    fun deletePortalIntegration(portal: PortalIntegration) {
        viewModelScope.launch(errorHandler) {
            repository.deletePortalIntegration(portal)
            showSnackbar("Removed ${portal.name} portal integration.")
        }
    }

    // --- System Reset / Factory Seed ---
    fun resetDatabaseToDefaults() {
        val actor = _currentUser.value?.name ?: "Mahesh"
        viewModelScope.launch(errorHandler) {
            repository.resetDatabaseToDefaults(actor)
            showSnackbar("Workspace database reset to fresh demonstration records.")
        }
    }

    fun markTaxNotificationAsRead(id: Long) {
        viewModelScope.launch(errorHandler) { repository.markTaxNotificationAsRead(id) }
    }

    fun markActivityAsRead(id: Long) {
        viewModelScope.launch(errorHandler) { repository.markActivityAsRead(id) }
    }

    fun markAllActivitiesAsRead() {
        viewModelScope.launch(errorHandler) { repository.markAllActivitiesAsRead() }
    }

    fun clearAllActivities() {
        viewModelScope.launch(errorHandler) { repository.clearAllActivities() }
    }

    fun deleteTask(task: TaskItem) {
        if (!canDeleteTasks()) {
            showSnackbar("Permission Denied: Only Admins have full control to delete tasks.")
            return
        }
        viewModelScope.launch(errorHandler) {
            repository.deleteTask(task)
            showSnackbar("Task '${task.title}' deleted by Admin.")
        }
    }

    companion object {
        fun getStartOfDay(millis: Long): Long {
            val cal = Calendar.getInstance().apply {
                timeInMillis = millis
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            return cal.timeInMillis
        }
    }
}
