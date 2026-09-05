package com.example.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.model.*
import com.example.data.repository.FirebaseCaRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class CaViewModel(application: Application) : AndroidViewModel(application) {

    val repository = FirebaseCaRepository(application)

    val currentUser = repository.currentUser
    val employees = repository.employees
    val clients = repository.clients
    val tasks = repository.tasks
    val taskCatalog = repository.taskCatalog
    val roles = repository.roles
    val auditLogs = repository.auditLogs
    val clientQueries = repository.clientQueries

    // UI state
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _authError = MutableStateFlow<String?>(null)
    val authError: StateFlow<String?> = _authError.asStateFlow()

    private val _userMessage = MutableStateFlow<String?>(null)
    val userMessage: StateFlow<String?> = _userMessage.asStateFlow()

    // Filters
    val taskSearchQuery = MutableStateFlow("")
    val taskStatusFilter = MutableStateFlow("All")
    val taskCategoryFilter = MutableStateFlow("All")
    val taskPriorityFilter = MutableStateFlow("All")

    val clientSearchQuery = MutableStateFlow("")
    val clientTypeFilter = MutableStateFlow("All")

    val employeeSearchQuery = MutableStateFlow("")

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())

    fun clearAuthError() {
        _authError.value = null
    }

    fun clearUserMessage() {
        _userMessage.value = null
    }

    fun login(email: String, pass: String, onSuccess: () -> Unit = {}) {
        if (email.isBlank() || pass.isBlank()) {
            _authError.value = "Please enter both email and password."
            return
        }
        viewModelScope.launch {
            _isLoading.value = true
            _authError.value = null
            val result = repository.login(email, pass)
            _isLoading.value = false
            result.onSuccess {
                _userMessage.value = "Welcome, ${it.roleTitle.ifEmpty { it.role }}!"
                onSuccess()
            }.onFailure {
                _authError.value = it.message ?: "Login failed. Check credentials."
            }
        }
    }

    fun signUp(email: String, pass: String, confirmPass: String, onSuccess: () -> Unit = {}) {
        if (email.isBlank() || pass.isBlank()) {
            _authError.value = "All fields are required."
            return
        }
        if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email.trim()).matches()) {
            _authError.value = "Please enter a valid email address."
            return
        }
        if (pass.length < 6) {
            _authError.value = "Password must be at least 6 characters long."
            return
        }
        if (pass != confirmPass) {
            _authError.value = "Passwords do not match."
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            _authError.value = null
            val result = repository.signUp(email, pass)
            _isLoading.value = false
            result.onSuccess {
                _userMessage.value = "Account created as ${it.role} (${it.roleTitle})!"
                onSuccess()
            }.onFailure {
                _authError.value = it.message ?: "Sign up failed."
            }
        }
    }

    fun logout() {
        repository.logout()
    }

    fun switchRoleDemo(role: String, email: String, title: String, linkedId: String) {
        repository.switchRoleForTesting(role, email, title, linkedId)
        _userMessage.value = "Switched to $role ($title)"
    }

    // Filtered Tasks for Admin
    val filteredAdminTasks: StateFlow<List<TaskItem>> = combine(
        tasks,
        taskSearchQuery,
        taskStatusFilter,
        taskCategoryFilter,
        taskPriorityFilter
    ) { allTasks, query, status, category, priority ->
        allTasks.filter { task ->
            val matchesQuery = query.isBlank() ||
                    task.taskType.contains(query, ignoreCase = true) ||
                    task.clientName.contains(query, ignoreCase = true) ||
                    task.assignedToName.contains(query, ignoreCase = true)
            val matchesStatus = status == "All" || task.status.equals(status, ignoreCase = true)
            val matchesCategory = category == "All" || task.category.equals(category, ignoreCase = true)
            val matchesPriority = priority == "All" || task.priority.equals(priority, ignoreCase = true)
            matchesQuery && matchesStatus && matchesCategory && matchesPriority
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Filtered Tasks for Employee (Restricted: ONLY assigned to this employee)
    val myEmployeeTasks: StateFlow<List<TaskItem>> = combine(
        tasks,
        currentUser,
        taskSearchQuery,
        taskStatusFilter
    ) { allTasks, user, query, status ->
        if (user == null || user.role != "Employee") return@combine emptyList<TaskItem>()
        val empId = user.linkedRecordId.ifEmpty { user.uid }
        val empEmail = user.email.lowercase()

        allTasks.filter { task ->
            val isAssigned = task.assignedTo == empId ||
                    task.assignedTo == user.uid ||
                    task.assignedToName.equals(user.roleTitle, ignoreCase = true) ||
                    employees.value.any { it.email.lowercase() == empEmail && it.employeeId == task.assignedTo }

            val matchesQuery = query.isBlank() ||
                    task.taskType.contains(query, ignoreCase = true) ||
                    task.clientName.contains(query, ignoreCase = true)

            val matchesStatus = status == "All" || task.status.equals(status, ignoreCase = true)

            isAssigned && matchesQuery && matchesStatus
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Tasks for Client (Restricted: ONLY tasks belonging to this client)
    val myClientTasks: StateFlow<List<TaskItem>> = combine(
        tasks,
        currentUser
    ) { allTasks, user ->
        if (user == null || user.role != "Client") return@combine emptyList<TaskItem>()
        val cliId = user.linkedRecordId.ifEmpty { user.uid }
        val cliEmail = user.email.lowercase()

        allTasks.filter { task ->
            task.clientId == cliId ||
                    clients.value.any { it.email.lowercase() == cliEmail && it.clientId == task.clientId }
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Current Client Record
    val currentClientRecord: StateFlow<Client?> = combine(
        clients,
        currentUser
    ) { allClients, user ->
        if (user == null || user.role != "Client") return@combine null
        val cliId = user.linkedRecordId.ifEmpty { user.uid }
        allClients.firstOrNull { it.clientId == cliId || it.email.equals(user.email, ignoreCase = true) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    // Filtered Clients for Admin
    val filteredClients: StateFlow<List<Client>> = combine(
        clients,
        clientSearchQuery,
        clientTypeFilter
    ) { list, query, type ->
        list.filter { client ->
            val matchesQuery = query.isBlank() ||
                    client.name.contains(query, ignoreCase = true) ||
                    client.pan.contains(query, ignoreCase = true) ||
                    client.email.contains(query, ignoreCase = true)
            val matchesType = type == "All" || client.clientType.equals(type, ignoreCase = true)
            matchesQuery && matchesType
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Filtered Employees for Admin
    val filteredEmployees: StateFlow<List<Employee>> = combine(
        employees,
        employeeSearchQuery
    ) { list, query ->
        list.filter { emp ->
            query.isBlank() ||
                    emp.name.contains(query, ignoreCase = true) ||
                    emp.role.contains(query, ignoreCase = true) ||
                    emp.email.contains(query, ignoreCase = true)
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // ==========================================
    // OVERDUE TASKS COMPUTATION
    // ==========================================
    fun isTaskOverdue(task: TaskItem): Boolean {
        if (task.status.equals("Completed", ignoreCase = true)) return false
        if (task.dueDate.isBlank()) return false
        return try {
            val due = dateFormat.parse(task.dueDate)
            val today = dateFormat.parse(dateFormat.format(Date()))
            due != null && today != null && due.before(today)
        } catch (e: Exception) {
            false
        }
    }

    val overdueTasks: StateFlow<List<TaskItem>> = tasks.map { list ->
        list.filter { isTaskOverdue(it) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // ==========================================
    // EMPLOYEE / CLIENT / TASK ACTIONS
    // ==========================================
    fun addEmployee(name: String, email: String, phone: String, role: String, dateOfJoining: String) {
        viewModelScope.launch {
            _isLoading.value = true
            val emp = Employee(
                name = name.trim(),
                email = email.trim().lowercase(),
                phone = phone.trim(),
                role = role,
                dateOfJoining = dateOfJoining.ifEmpty { dateFormat.format(Date()) },
                status = "active",
                addedBy = currentUser.value?.uid ?: "Admin"
            )
            repository.addEmployee(emp)
            _isLoading.value = false
            _userMessage.value = "Employee $name added. Email is now authorized to sign up!"
        }
    }

    fun updateEmployee(employee: Employee) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.updateEmployee(employee)
            _isLoading.value = false
            _userMessage.value = "Employee updated."
        }
    }

    fun deleteEmployee(employeeId: String) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.deleteEmployee(employeeId)
            _isLoading.value = false
            _userMessage.value = "Employee deleted."
        }
    }

    fun addClient(
        name: String,
        email: String,
        phone: String,
        pan: String,
        gstin: String,
        clientType: String,
        services: List<String>,
        dateAdded: String
    ) {
        viewModelScope.launch {
            _isLoading.value = true
            val cli = Client(
                name = name.trim(),
                email = email.trim().lowercase(),
                phone = phone.trim(),
                pan = pan.trim().uppercase(),
                gstin = gstin.trim().uppercase(),
                clientType = clientType,
                servicesSubscribed = services,
                dateAdded = dateAdded.ifEmpty { dateFormat.format(Date()) },
                addedBy = currentUser.value?.uid ?: "Admin"
            )
            repository.addClient(cli)
            _isLoading.value = false
            _userMessage.value = "Client $name added. Email is now authorized to sign up!"
        }
    }

    fun updateClient(client: Client) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.updateClient(client)
            _isLoading.value = false
            _userMessage.value = "Client updated."
        }
    }

    fun deleteClient(clientId: String) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.deleteClient(clientId)
            _isLoading.value = false
            _userMessage.value = "Client deleted."
        }
    }

    fun assignTask(
        clientId: String,
        clientName: String,
        taskType: String,
        category: String,
        assignedToEmployeeId: String,
        assignedToName: String,
        priority: String,
        dueDate: String,
        notes: String
    ) {
        viewModelScope.launch {
            _isLoading.value = true
            val task = TaskItem(
                clientId = clientId,
                clientName = clientName,
                taskType = taskType,
                category = category,
                assignedTo = assignedToEmployeeId,
                assignedToName = assignedToName,
                assignedBy = currentUser.value?.roleTitle ?: "Admin",
                status = "Pending",
                priority = priority,
                dueDate = dueDate,
                notes = notes,
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            )
            repository.addTask(task)
            _isLoading.value = false
            _userMessage.value = "Task assigned to $assignedToName"
        }
    }

    fun updateTask(task: TaskItem) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.updateTask(task.copy(updatedAt = System.currentTimeMillis()))
            _isLoading.value = false
            _userMessage.value = "Task details saved."
        }
    }

    fun updateTaskStatus(taskId: String, status: String, remark: String = "") {
        viewModelScope.launch {
            _isLoading.value = true
            repository.updateTaskStatus(taskId, status, remark)
            _isLoading.value = false
            _userMessage.value = "Status updated to $status"
        }
    }

    fun deleteTask(taskId: String) {
        viewModelScope.launch {
            _isLoading.value = true
            repository.deleteTask(taskId)
            _isLoading.value = false
            _userMessage.value = "Task removed."
        }
    }

    fun addCatalogItem(name: String, category: String, desc: String) {
        viewModelScope.launch {
            val item = TaskCatalogItem(
                taskName = name.trim(),
                category = category,
                defaultDescription = desc.trim(),
                addedBy = currentUser.value?.email ?: "Admin"
            )
            repository.addCatalogItem(item)
            _userMessage.value = "New task type '$name' added to catalog."
        }
    }

    fun deleteCatalogItem(itemId: String) {
        viewModelScope.launch {
            repository.deleteCatalogItem(itemId)
            _userMessage.value = "Catalog item removed."
        }
    }

    fun addCustomRole(roleName: String) {
        repository.addRole(roleName)
        _userMessage.value = "Role '$roleName' added to dropdown."
    }

    fun submitClientQuery(subject: String, message: String) {
        val user = currentUser.value ?: return
        val client = currentClientRecord.value
        viewModelScope.launch {
            _isLoading.value = true
            val query = ClientQuery(
                clientId = client?.clientId ?: user.linkedRecordId,
                clientName = client?.name ?: user.email,
                clientEmail = user.email,
                subject = subject.trim(),
                message = message.trim(),
                timestamp = System.currentTimeMillis()
            )
            repository.submitClientQuery(query)
            _isLoading.value = false
            _userMessage.value = "Your query has been submitted to Vinay Sehgal & Co."
        }
    }
}
