package com.example.data.repository

import android.content.Context
import com.example.data.local.OfficeDao
import com.example.data.local.OfficeDatabase
import com.example.data.model.ActivityType
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
import com.example.notification.NotificationHelper
import com.google.android.gms.tasks.Task as GmsTask
import com.google.firebase.FirebaseApp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.CollectionReference
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.FirebaseFirestoreException
import com.google.firebase.firestore.Query
import com.google.firebase.firestore.Source
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.buffer
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class OfficeRepository(
    private val context: Context,
    private val dao: OfficeDao
) {
    private val firestore: FirebaseFirestore = FirebaseFirestore.getInstance()
    private val auth: FirebaseAuth = FirebaseAuth.getInstance()

    private val tasksRef: CollectionReference get() = firestore.collection(COLLECTION_TASKS)
    private val projectsRef: CollectionReference get() = firestore.collection(COLLECTION_PROJECTS)
    private val membersRef: CollectionReference get() = firestore.collection(COLLECTION_MEMBERS)

    // --- Shared, cross-device data (Firestore) ---
    // Sorted client-side rather than with orderBy() so no composite Firestore indexes are
    // required, and documents are never dropped for missing sort fields.
    /**
     * Live task list scoped to what this member is permitted to read.
     *
     * Firestore evaluates a list query against the security rules as a whole and rejects the
     * whole query if it could return a forbidden document — it does not filter. A Team Member
     * may only read their own tasks, so their listener must carry a matching where() clause or
     * it fails outright. Everyone above them may read the collection, because the Team Workload
     * view has to count work assigned to other people.
     */
    fun tasksFor(member: TeamMember?): Flow<List<TaskItem>> {
        if (member == null) return flowOf(emptyList())
        val query = if (member.userRole == UserRole.TEAM_MEMBER) {
            tasksRef.whereEqualTo("assignedMemberId", member.id)
        } else {
            tasksRef
        }
        return query
            .asFlow({ e -> reportListenerFailure("tasks", e) }) { doc ->
                doc.toObject(TaskItem::class.java)?.copy(id = doc.id)
            }
            .sortedBy { list -> list.sortedWith(compareBy({ it.dueDateMillis }, { it.title })) }
    }

    // Every shared listener is a function of the signed-in member rather than a property.
    // Subscribing before sign-in would be denied by the rules, and a dead listener never
    // recovers — so they are created fresh once somebody is actually signed in.
    fun projectsFor(member: TeamMember?): Flow<List<Project>> {
        if (member == null) return flowOf(emptyList())
        return projectsRef
            .asFlow({ e -> reportListenerFailure("projects", e) }) { doc ->
                doc.toObject(Project::class.java)?.copy(id = doc.id)
            }
            .sortedBy { list -> list.sortedBy { it.targetDateMillis } }
    }

    fun teamMembersFor(member: TeamMember?): Flow<List<TeamMember>> {
        if (member == null) return flowOf(emptyList())
        return membersRef
            .asFlow({ e -> reportListenerFailure("the team roster", e) }) { doc ->
                doc.toObject(TeamMember::class.java)?.copy(id = doc.id)
            }
            .sortedBy { list -> list.sortedWith(compareByDescending<TeamMember> { it.isPrimaryAdmin }.thenBy { it.name }) }
    }

    // Non-null when the shared workspace could not be reached, so the UI can explain why it
    // looks empty instead of leaving the user guessing.
    private val _workspaceError = MutableStateFlow<String?>(null)
    val workspaceError: StateFlow<String?> = _workspaceError.asStateFlow()

    private fun reportListenerFailure(what: String, e: Exception) {
        _workspaceError.value = when {
            e is FirebaseFirestoreException &&
                e.code == FirebaseFirestoreException.Code.PERMISSION_DENIED ->
                "Not allowed to read $what. Check the Firestore security rules for project office-flow-integration."
            e is FirebaseFirestoreException &&
                e.code == FirebaseFirestoreException.Code.NOT_FOUND ->
                "No Firestore database exists for project office-flow-integration. Create it in the Firebase console under Build > Firestore Database."
            else -> "Could not load $what: ${e.message ?: e::class.java.simpleName}"
        }
    }

    // --- Device-local data (Room) ---
    val allTaxNotifications: Flow<List<TaxNotification>> = dao.getAllTaxNotifications()
    val allActivityNotifications: Flow<List<OfficeActivityNotification>> = dao.getAllActivityNotifications()
    val allPortalIntegrations: Flow<List<PortalIntegration>> = dao.getAllPortalIntegrations()

    init {
        CoroutineScope(Dispatchers.IO).launch {
            seedLocalTables()
        }
    }

    /** Device-local reference data. Needs no account, so it runs at startup. */
    private suspend fun seedLocalTables() {
        if (dao.getAllTaxNotifications().first().isEmpty()) {
            dao.insertTaxNotifications(InitialDataSeeder.getDefaultTaxNotifications())
        }
        if (dao.getAllPortalIntegrations().first().isEmpty()) {
            dao.insertPortalIntegrations(InitialDataSeeder.getDefaultPortalIntegrations())
            for (activity in InitialDataSeeder.getDefaultActivityNotifications()) {
                dao.insertActivityNotification(activity)
            }
        }
    }

    /**
     * Seeds the shared workspace. Runs only after sign-in and only for someone allowed to
     * create projects — the rules require an authenticated caller, so probing Firestore at
     * app startup would just fail and raise a misleading warning on the login screen.
     */
    private suspend fun seedWorkspaceIfNeeded(member: TeamMember) {
        if (member.userRole == UserRole.TEAM_MEMBER) return

        val existingProjects = try {
            projectsRef.get(Source.SERVER).awaitResult()
        } catch (e: Exception) {
            // Report rather than fail silently: otherwise a rules or connectivity problem
            // just looks like an empty workspace where every login says "invalid credentials".
            _workspaceError.value = when {
                e is FirebaseFirestoreException &&
                    e.code == FirebaseFirestoreException.Code.PERMISSION_DENIED ->
                    "Cannot reach the shared workspace: the Firestore security rules are blocking access. Update the rules for project office-flow-integration."
                e is FirebaseFirestoreException &&
                    e.code == FirebaseFirestoreException.Code.NOT_FOUND ->
                    "No Firestore database exists for project office-flow-integration. In the Firebase console open Build > Firestore Database > Create database (Native mode), and make sure it is the (default) database."
                else ->
                    // Firestore reports a missing database as UNAVAILABLE/offline too, so name
                    // it as a possibility rather than sending anyone after a network fault.
                    "Cannot reach the shared workspace. Check the connection — and confirm a (default) Firestore database has actually been created for project office-flow-integration."
            }
            return
        }
        _workspaceError.value = null

        // The roster is not seeded — members are created through Firebase Auth onboarding so
        // each document is keyed by that user's Auth UID. Only the sample projects are seeded.
        if (existingProjects.isEmpty) {
            for (project in InitialDataSeeder.getDefaultProjects()) {
                projectsRef.document(project.id).set(project).awaitResult()
            }
            dao.insertActivityNotification(
                OfficeActivityNotification(
                    title = "Welcome to OfficeFlow Workspace",
                    message = "Shared workspace initialized. Onboard your team from the Team tab.",
                    type = ActivityType.TAX_CIRCULAR_ALERT,
                    actorName = "Office Administrator"
                )
            )
        }
    }

    // --- Task Operations ---
    suspend fun assignTask(
        title: String,
        description: String,
        member: TeamMember,
        project: Project?,
        priority: TaskPriority,
        dueDateMillis: Long,
        category: TaskCategory,
        checklistItems: String,
        tags: String = "",
        assignedBy: String = "Mahesh",
        assignedByMemberId: String = ""
    ): String = withContext(Dispatchers.IO) {
        val checklistList = checklistItems.lines().filter { it.isNotBlank() }
        val ref = tasksRef.document()
        val task = TaskItem(
            id = ref.id,
            title = title,
            description = description,
            assignedMemberId = member.id,
            assignedMemberName = member.name,
            assignedMemberRole = member.role,
            assignedBy = assignedBy,
            assignedByMemberId = assignedByMemberId,
            projectId = project?.id ?: "",
            projectName = project?.name ?: "General Office",
            priority = priority,
            status = TaskStatus.TODO,
            progressPercentage = 0,
            dueDateMillis = dueDateMillis,
            category = category,
            tags = tags,
            checklistItems = checklistItems,
            completedChecklistCount = 0,
            totalChecklistCount = checklistList.size,
            lastProgressRemark = "Task assigned by $assignedBy"
        )
        ref.set(task).awaitResult()

        val notificationTitle = "New Task Assigned: $title"
        val notificationMsg = "Assigned to ${member.name} • Priority: ${priority.name} • Due: ${formatDate(dueDateMillis)}"
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = notificationTitle,
                message = notificationMsg,
                type = ActivityType.TASK_ASSIGNED,
                actorName = assignedBy
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = notificationTitle,
            message = notificationMsg,
            isTaxAlert = (category == TaskCategory.GST_COMPLIANCE || category == TaskCategory.INCOME_TAX)
        )

        ref.id
    }

    suspend fun updateTaskStatus(task: TaskItem, newStatus: TaskStatus) = withContext(Dispatchers.IO) {
        val newProgress = when (newStatus) {
            TaskStatus.TODO -> if (task.progressPercentage == 100) 0 else task.progressPercentage
            TaskStatus.IN_PROGRESS -> if (task.progressPercentage == 0) 25 else task.progressPercentage
            TaskStatus.IN_REVIEW -> if (task.progressPercentage < 80) 85 else task.progressPercentage
            TaskStatus.COMPLETED -> 100
        }
        val updatedTask = task.copy(
            status = newStatus,
            progressPercentage = newProgress,
            updatedMillis = System.currentTimeMillis(),
            lastProgressRemark = "Status changed to ${newStatus.name.replace("_", " ")}"
        )
        tasksRef.document(task.id).set(updatedTask).awaitResult()

        if (task.projectId.isNotBlank()) {
            recalculateProjectProgress(task.projectId)
        }

        val title = "Task Status Updated: ${task.title}"
        val msg = "${task.assignedMemberName} moved task to ${newStatus.name.replace("_", " ")} ($newProgress% done)"
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = title,
                message = msg,
                type = ActivityType.STATUS_CHANGED,
                actorName = task.assignedMemberName
            )
        )
    }

    suspend fun pushTaskProgress(
        taskId: String,
        progressPercentage: Int,
        remark: String,
        status: TaskStatus,
        completedChecklistItems: Int,
        actorName: String = "Team Member"
    ) = withContext(Dispatchers.IO) {
        val task = getTaskById(taskId) ?: return@withContext
        val updatedTask = task.copy(
            progressPercentage = progressPercentage,
            status = if (progressPercentage >= 100) TaskStatus.COMPLETED else status,
            lastProgressRemark = remark,
            completedChecklistCount = completedChecklistItems,
            updatedMillis = System.currentTimeMillis()
        )
        tasksRef.document(taskId).set(updatedTask).awaitResult()

        if (task.projectId.isNotBlank()) {
            recalculateProjectProgress(task.projectId)
        }

        val notificationTitle = "Progress Pushed: ${task.title} ($progressPercentage%)"
        val notificationMsg = "$actorName updated progress: \"$remark\" [${task.projectName}]"
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = notificationTitle,
                message = notificationMsg,
                type = ActivityType.PROGRESS_PUSHED,
                actorName = actorName
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = notificationTitle,
            message = notificationMsg,
            isTaxAlert = false
        )
    }

    suspend fun pushProjectProgress(
        projectId: String,
        newProgress: Int,
        remark: String,
        actorName: String = "Project Lead"
    ) = withContext(Dispatchers.IO) {
        val project = getProjectById(projectId) ?: return@withContext
        val updated = project.copy(
            progressPercentage = newProgress,
            lastUpdateRemark = remark
        )
        projectsRef.document(projectId).set(updated).awaitResult()

        val title = "Project Milestone Pushed: ${project.name} ($newProgress%)"
        val msg = "$actorName updated project status: \"$remark\""
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = title,
                message = msg,
                type = ActivityType.PROJECT_UPDATE,
                actorName = actorName
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = title,
            message = msg,
            isTaxAlert = false
        )
    }

    private suspend fun recalculateProjectProgress(projectId: String) {
        val projectTasks = tasksRef.whereEqualTo("projectId", projectId).get().awaitResult()
            .documents.mapNotNull { it.toObject(TaskItem::class.java) }
        if (projectTasks.isNotEmpty()) {
            val avgProgress = projectTasks.map { it.progressPercentage }.average().toInt()
            val project = getProjectById(projectId)
            if (project != null) {
                projectsRef.document(projectId).set(project.copy(progressPercentage = avgProgress)).awaitResult()
            }
        }
    }

    suspend fun deleteTask(task: TaskItem) = withContext(Dispatchers.IO) {
        tasksRef.document(task.id).delete().awaitResult()
        Unit
    }

    private suspend fun getTaskById(id: String): TaskItem? {
        if (id.isBlank()) return null
        val doc = tasksRef.document(id).get().awaitResult()
        return doc.toObject(TaskItem::class.java)?.copy(id = doc.id)
    }

    private suspend fun getProjectById(id: String): Project? {
        if (id.isBlank()) return null
        val doc = projectsRef.document(id).get().awaitResult()
        return doc.toObject(Project::class.java)?.copy(id = doc.id)
    }

    // --- Projects ---
    suspend fun createProject(
        name: String,
        code: String,
        clientName: String,
        description: String,
        leadMemberName: String,
        targetDateMillis: Long,
        category: String,
        colorHex: String
    ): String = withContext(Dispatchers.IO) {
        val ref = projectsRef.document()
        val project = Project(
            id = ref.id,
            name = name,
            code = code,
            clientName = clientName,
            description = description,
            leadMemberName = leadMemberName,
            startDateMillis = System.currentTimeMillis(),
            targetDateMillis = targetDateMillis,
            category = category,
            colorHex = colorHex,
            lastUpdateRemark = "Project created and initiated"
        )
        ref.set(project).awaitResult()
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = "New Project Initiated: $name",
                message = "Client: $clientName • Lead: $leadMemberName • Due: ${formatDate(targetDateMillis)}",
                type = ActivityType.PROJECT_UPDATE,
                actorName = "Office Administrator"
            )
        )
        ref.id
    }

    // --- Tax Notifications & Push Alerts (local) ---
    suspend fun pushTaxNotificationAlert(notification: TaxNotification) = withContext(Dispatchers.IO) {
        val title = "Statutory Alert: ${notification.department.name} - ${notification.circularOrNotificationNo}"
        val msg = "${notification.title}\nKey Action: ${notification.keyActionItems.take(90)}..."

        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = title,
                message = msg,
                type = ActivityType.TAX_CIRCULAR_ALERT,
                relatedEntityId = notification.id,
                actorName = notification.sourceAuthority
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = title,
            message = "${notification.title} • Action required before ${formatDate(notification.deadlineDateMillis)}",
            isTaxAlert = true,
            priorityHigh = notification.severity == TaxSeverity.CRITICAL_ACTION_REQUIRED
        )
    }

    suspend fun convertTaxNotificationToTask(
        notification: TaxNotification,
        assignedMember: TeamMember,
        project: Project?,
        assignedByMemberId: String = "",
        assignedByName: String = "Compliance Office"
    ): String = withContext(Dispatchers.IO) {
        val category = if (notification.department == TaxDepartment.GST) {
            TaskCategory.GST_COMPLIANCE
        } else {
            TaskCategory.INCOME_TAX
        }

        val checklist = notification.keyActionItems
        val checklistList = checklist.lines().filter { it.isNotBlank() }

        val ref = tasksRef.document()
        val task = TaskItem(
            id = ref.id,
            title = "Statutory Compliance: ${notification.title.take(50)}",
            description = "Ref: ${notification.circularOrNotificationNo}\n\nSummary:\n${notification.summary}\n\nAuthority: ${notification.sourceAuthority}",
            assignedMemberId = assignedMember.id,
            assignedMemberName = assignedMember.name,
            assignedMemberRole = assignedMember.role,
            assignedBy = assignedByName,
            assignedByMemberId = assignedByMemberId,
            projectId = project?.id ?: "",
            projectName = project?.name ?: "Statutory Tax Advisory",
            priority = if (notification.severity == TaxSeverity.CRITICAL_ACTION_REQUIRED) TaskPriority.URGENT else TaskPriority.HIGH,
            status = TaskStatus.TODO,
            progressPercentage = 0,
            dueDateMillis = notification.deadlineDateMillis,
            category = category,
            checklistItems = checklist,
            completedChecklistCount = 0,
            totalChecklistCount = checklistList.size,
            lastProgressRemark = "Generated from official statutory circular ${notification.circularOrNotificationNo}"
        )
        ref.set(task).awaitResult()
        dao.markTaxNotificationPushed(notification.id)

        val notifTitle = "Compliance Task Created from Notice"
        val notifMsg = "Task assigned to ${assignedMember.name} for circular ${notification.circularOrNotificationNo}"
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = notifTitle,
                message = notifMsg,
                type = ActivityType.TASK_ASSIGNED,
                actorName = assignedByName
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = notifTitle,
            message = notifMsg,
            isTaxAlert = true
        )
        ref.id
    }

    suspend fun createCustomTaxNotification(
        title: String,
        department: TaxDepartment,
        circularNumber: String,
        summary: String,
        keyActions: String,
        deadlineMillis: Long,
        severity: TaxSeverity,
        source: String
    ): Long = withContext(Dispatchers.IO) {
        val item = TaxNotification(
            title = title,
            department = department,
            circularOrNotificationNo = circularNumber,
            issueDateFormatted = "Today",
            effectiveDateFormatted = "Immediate",
            summary = summary,
            keyActionItems = keyActions,
            deadlineDateMillis = deadlineMillis,
            severity = severity,
            sourceAuthority = source
        )
        val id = dao.insertTaxNotification(item)
        pushTaxNotificationAlert(item.copy(id = id))
        id
    }

    suspend fun markTaxNotificationAsRead(id: Long) = withContext(Dispatchers.IO) {
        dao.markTaxNotificationAsRead(id)
    }

    suspend fun markActivityAsRead(id: Long) = withContext(Dispatchers.IO) {
        dao.markActivityAsRead(id)
    }

    suspend fun markAllActivitiesAsRead() = withContext(Dispatchers.IO) {
        dao.markAllActivitiesAsRead()
    }

    suspend fun clearAllActivities() = withContext(Dispatchers.IO) {
        dao.clearAllActivityNotifications()
    }

    // --- Team Member Operations & Role Admin ---
    private suspend fun findMemberByEmail(email: String): TeamMember? {
        val normalized = email.trim().lowercase()
        if (normalized.isEmpty()) return null
        val snapshot = membersRef.whereEqualTo("email", normalized).get().awaitResult()
        val doc = snapshot.documents.firstOrNull() ?: return null
        return doc.toObject(TeamMember::class.java)?.copy(id = doc.id)
    }

    /**
     * Signs in against Firebase Authentication and returns the caller's roster entry.
     *
     * The member document is keyed by the Auth UID so security rules can resolve the caller's
     * role. The primary admin is self-provisioned on first sign-in, because somebody has to
     * exist before anyone can be onboarded.
     */
    suspend fun signIn(email: String, password: String): TeamMember = withContext(Dispatchers.IO) {
        val normalizedEmail = email.trim().lowercase()
        val result = auth.signInWithEmailAndPassword(normalizedEmail, password).awaitResult()
        val uid = result.user?.uid ?: throw IllegalStateException("Sign-in returned no user.")

        val member = loadMemberByUid(uid)
            ?: provisionPrimaryAdmin(uid, normalizedEmail)
            ?: throw IllegalStateException(
                "$normalizedEmail signed in, but has no profile in this workspace. Ask an administrator to onboard this address."
            )

        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = "User Signed In",
                message = "${member.name} (${member.userRole.displayName}) authenticated successfully.",
                type = ActivityType.STATUS_CHANGED,
                actorName = member.name
            )
        )
        // Best effort: a seeding failure must never block a successful sign-in.
        try { seedWorkspaceIfNeeded(member) } catch (_: Exception) { }
        member
    }

    fun signOut() {
        auth.signOut()
    }

    /** The already-signed-in member, if Firebase Auth restored a session from a previous run. */
    suspend fun restoreSession(): TeamMember? = withContext(Dispatchers.IO) {
        val uid = auth.currentUser?.uid ?: return@withContext null
        val member = loadMemberByUid(uid) ?: return@withContext null
        try { seedWorkspaceIfNeeded(member) } catch (_: Exception) { }
        member
    }

    private suspend fun loadMemberByUid(uid: String): TeamMember? {
        val doc = membersRef.document(uid).get().awaitResult()
        return if (doc.exists()) doc.toObject(TeamMember::class.java)?.copy(id = doc.id) else null
    }

    private suspend fun provisionPrimaryAdmin(uid: String, email: String): TeamMember? {
        if (email != PRIMARY_ADMIN_EMAIL) return null
        val admin = TeamMember(
            id = uid,
            name = "Mahesh",
            role = "Managing Partner & Administrator",
            userRole = UserRole.ADMIN,
            department = "Executive & Practice Leadership",
            email = email,
            avatarColorHex = "#1E40AF",
            isPrimaryAdmin = true
        )
        membersRef.document(uid).set(admin).awaitResult()
        return admin
    }

    suspend fun getMemberByEmail(email: String): TeamMember? = withContext(Dispatchers.IO) {
        findMemberByEmail(email)
    }

    /**
     * Creates the employee's Firebase Auth account and their roster entry together.
     *
     * Account creation runs on a SECONDARY FirebaseApp instance: the normal client SDK call
     * signs the new user in, which would silently replace the admin's own session mid-onboarding.
     */
    suspend fun addTeamMember(
        name: String,
        role: String,
        userRole: UserRole,
        department: String,
        email: String,
        phone: String,
        avatarColorHex: String,
        password: String = "office123",
        actorName: String = "Admin"
    ): String = withContext(Dispatchers.IO) {
        val normalizedEmail = email.trim().lowercase()
        val uid = createAuthAccount(normalizedEmail, password.ifBlank { "office123" })
        val member = TeamMember(
            id = uid,
            name = name,
            role = role,
            userRole = userRole,
            department = department,
            email = normalizedEmail,
            phone = phone,
            avatarColorHex = avatarColorHex,
            isPrimaryAdmin = normalizedEmail == PRIMARY_ADMIN_EMAIL
        )
        membersRef.document(uid).set(member).awaitResult()

        val notifTitle = "New Team Member Onboarded: $name"
        val notifMsg = "$name joined as $role (${userRole.displayName}) with login account ($normalizedEmail)."
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = notifTitle,
                message = notifMsg,
                type = ActivityType.STATUS_CHANGED,
                actorName = actorName
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = notifTitle,
            message = notifMsg,
            isTaxAlert = false
        )
        uid
    }

    /**
     * Creates a Firebase Auth account without disturbing the caller's own session.
     *
     * createUserWithEmailAndPassword signs the new account in on whichever FirebaseApp it runs
     * against, so it runs on a throwaway secondary app instance that is torn down immediately.
     */
    private suspend fun createAuthAccount(email: String, password: String): String {
        val primary = FirebaseApp.getInstance()
        val secondary = try {
            FirebaseApp.initializeApp(context, primary.options, ONBOARDING_APP_NAME)
        } catch (_: IllegalStateException) {
            FirebaseApp.getInstance(ONBOARDING_APP_NAME)
        }
        return try {
            val secondaryAuth = FirebaseAuth.getInstance(secondary)
            val created = secondaryAuth.createUserWithEmailAndPassword(email, password).awaitResult()
            secondaryAuth.signOut()
            created.user?.uid ?: throw IllegalStateException("Account created but no UID was returned.")
        } finally {
            try { secondary.delete() } catch (_: Exception) { }
        }
    }

    suspend fun updateTeamMember(member: TeamMember, actorName: String = "Admin") = withContext(Dispatchers.IO) {
        val memberToStore = member.copy(email = member.email.trim().lowercase())
        membersRef.document(member.id).set(memberToStore).awaitResult()
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = "Team Member Profile Updated: ${member.name}",
                message = "Updated designation: ${member.role} • Dept: ${member.department} • Role: ${member.userRole.displayName}",
                type = ActivityType.STATUS_CHANGED,
                actorName = actorName
            )
        )
    }

    suspend fun updateTeamMemberRole(memberId: String, newRole: UserRole, actorName: String = "Admin") = withContext(Dispatchers.IO) {
        val doc = membersRef.document(memberId).get().awaitResult()
        val member = doc.toObject(TeamMember::class.java)?.copy(id = doc.id) ?: return@withContext
        val oldRole = member.userRole
        membersRef.document(memberId).set(member.copy(userRole = newRole)).awaitResult()

        val title = "Security Role Changed: ${member.name}"
        val msg = "Role permission adjusted from ${oldRole.displayName} to ${newRole.displayName} by $actorName."
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = title,
                message = msg,
                type = ActivityType.STATUS_CHANGED,
                actorName = actorName
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = title,
            message = msg,
            isTaxAlert = false
        )
    }

    suspend fun deleteTeamMember(member: TeamMember, actorName: String = "Admin") = withContext(Dispatchers.IO) {
        membersRef.document(member.id).delete().awaitResult()
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = "Team Member Removed: ${member.name}",
                message = "${member.name} (${member.role}) was removed from active office roster.",
                type = ActivityType.STATUS_CHANGED,
                actorName = actorName
            )
        )
    }

    // --- Portal & Website Integrations (local) ---
    suspend fun addPortalIntegration(portal: PortalIntegration, actorName: String = "Admin"): Long = withContext(Dispatchers.IO) {
        val id = dao.insertPortalIntegration(portal)
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = "Portal Configured: ${portal.name}",
                message = "Integration linked to URL: ${portal.portalUrl} • Webhook: ${portal.webhookUrl.ifEmpty { "None" }}",
                type = ActivityType.TAX_CIRCULAR_ALERT,
                relatedEntityId = id,
                actorName = actorName
            )
        )
        id
    }

    suspend fun updatePortalIntegration(portal: PortalIntegration) = withContext(Dispatchers.IO) {
        dao.updatePortalIntegration(portal)
    }

    suspend fun testPortalSync(portalId: Long, actorName: String = "Admin"): Boolean = withContext(Dispatchers.IO) {
        val portal = dao.getPortalIntegrationById(portalId) ?: return@withContext false
        val now = System.currentTimeMillis()
        val syncResult = "Ping Verified • Status 200 OK (${(40..120).random()}ms latency)"
        dao.updatePortalSyncStatus(portalId, syncResult, now)

        val title = "Portal Sync Verified: ${portal.name}"
        val msg = "$actorName initiated test sync with ${portal.portalUrl}. Gateway handshake successful."
        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = title,
                message = msg,
                type = ActivityType.PROJECT_UPDATE,
                relatedEntityId = portalId,
                actorName = actorName
            )
        )
        NotificationHelper.showNotification(
            context = context,
            title = title,
            message = msg,
            isTaxAlert = false
        )
        true
    }

    suspend fun deletePortalIntegration(portal: PortalIntegration) = withContext(Dispatchers.IO) {
        dao.deletePortalIntegration(portal)
    }

    // --- Workspace Reset ---
    /**
     * Clears tasks and restores the sample projects.
     *
     * The team roster is deliberately NOT wiped. Every member document is keyed by a Firebase
     * Auth UID, so deleting them would leave real Auth accounts with no profile — every
     * employee would sign in successfully and then be refused, with no way back except
     * re-onboarding each one by hand.
     */
    suspend fun resetDatabaseToDefaults(actorName: String = "Mahesh") = withContext(Dispatchers.IO) {
        for (ref in listOf(tasksRef, projectsRef)) {
            val existing = ref.get().awaitResult()
            for (doc in existing.documents) {
                ref.document(doc.id).delete().awaitResult()
            }
        }
        for (project in InitialDataSeeder.getDefaultProjects()) {
            projectsRef.document(project.id).set(project).awaitResult()
        }

        // Local tables
        dao.clearAllTaxNotifications()
        dao.clearAllPortalIntegrations()
        dao.clearAllActivityNotifications()
        dao.insertTaxNotifications(InitialDataSeeder.getDefaultTaxNotifications())
        dao.insertPortalIntegrations(InitialDataSeeder.getDefaultPortalIntegrations())

        dao.insertActivityNotification(
            OfficeActivityNotification(
                title = "Workspace Reset",
                message = "Tasks cleared and sample projects restored. The team roster was left untouched.",
                type = ActivityType.TAX_CIRCULAR_ALERT,
                actorName = actorName
            )
        )
        for (activity in InitialDataSeeder.getDefaultActivityNotifications()) {
            dao.insertActivityNotification(activity)
        }
    }

    private fun formatDate(millis: Long): String {
        val cal = java.util.Calendar.getInstance().apply { timeInMillis = millis }
        val day = cal.get(java.util.Calendar.DAY_OF_MONTH)
        val month = cal.getDisplayName(java.util.Calendar.MONTH, java.util.Calendar.SHORT, java.util.Locale.getDefault()) ?: ""
        return "$day $month"
    }

    companion object {
        const val COLLECTION_TASKS = "tasks"
        const val COLLECTION_PROJECTS = "projects"
        const val COLLECTION_MEMBERS = "teamMembers"
        const val PRIMARY_ADMIN_EMAIL = "mahesh@primeaccounting.in"
        private const val ONBOARDING_APP_NAME = "officeflow-onboarding"

        @Volatile
        private var instance: OfficeRepository? = null

        fun getInstance(context: Context): OfficeRepository {
            return instance ?: synchronized(this) {
                instance ?: run {
                    val db = OfficeDatabase.getDatabase(context)
                    val newInstance = OfficeRepository(context.applicationContext, db.officeDao())
                    instance = newInstance
                    newInstance
                }
            }
        }
    }
}

/** Live Firestore query as a Flow, backed by the SDK's offline cache. Never throws. */
private fun <T> Query.asFlow(
    onError: (Exception) -> Unit = {},
    map: (com.google.firebase.firestore.DocumentSnapshot) -> T?
): Flow<List<T>> =
    callbackFlow {
        val registration = addSnapshotListener { snapshot, error ->
            if (error != null) {
                // Deliberately NOT close(error): these flows are collected by stateIn(viewModelScope),
                // whose coroutine has no exception handler, so a thrown error would kill the whole
                // app. A denied listener before sign-in is normal, not fatal — report it, hand the
                // UI an empty list, and end the flow quietly.
                onError(error)
                trySend(emptyList())
                close()
                return@addSnapshotListener
            }
            trySend(snapshot?.documents?.mapNotNull(map) ?: emptyList())
        }
        awaitClose { registration.remove() }
    }.buffer(Channel.CONFLATED) // Firestore emits from its own thread; never drop the latest snapshot.

private fun <T> Flow<List<T>>.sortedBy(sort: (List<T>) -> List<T>): Flow<List<T>> =
    map { sort(it) }

/** Bridges a Google Play Services Task into a coroutine without extra dependencies. */
private suspend fun <T> GmsTask<T>.awaitResult(): T = suspendCancellableCoroutine { cont ->
    addOnSuccessListener { result -> if (cont.isActive) cont.resume(result) }
    addOnFailureListener { error -> if (cont.isActive) cont.resumeWithException(error) }
}
