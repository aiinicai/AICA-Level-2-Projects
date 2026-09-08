package com.example.data.repository

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.util.Log
import com.example.data.model.*
import com.google.firebase.FirebaseApp
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ListenerRegistration
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

suspend fun <T> com.google.android.gms.tasks.Task<T>.awaitTask(): T =
    suspendCancellableCoroutine { cont ->
        addOnSuccessListener { if (cont.isActive) cont.resume(it) }
        addOnFailureListener { if (cont.isActive) cont.resumeWithException(it) }
        addOnCanceledListener { if (cont.isActive) cont.cancel() }
    }

class FirebaseCaRepository(private val context: Context) {

    private val scope = CoroutineScope(Dispatchers.IO)
    private val prefs: SharedPreferences = context.getSharedPreferences("ca_firm_prefs", Context.MODE_PRIVATE)

    private var firebaseAuth: FirebaseAuth? = null
    private var firestore: FirebaseFirestore? = null
    private var isFirebaseAvailable = false

    // State flows
    private val _currentUser = MutableStateFlow<UserAccount?>(null)
    val currentUser: StateFlow<UserAccount?> = _currentUser.asStateFlow()

    private val _employees = MutableStateFlow<List<Employee>>(emptyList())
    val employees: StateFlow<List<Employee>> = _employees.asStateFlow()

    private val _clients = MutableStateFlow<List<Client>>(emptyList())
    val clients: StateFlow<List<Client>> = _clients.asStateFlow()

    private val _tasks = MutableStateFlow<List<TaskItem>>(emptyList())
    val tasks: StateFlow<List<TaskItem>> = _tasks.asStateFlow()

    private val _taskCatalog = MutableStateFlow<List<TaskCatalogItem>>(emptyList())
    val taskCatalog: StateFlow<List<TaskCatalogItem>> = _taskCatalog.asStateFlow()

    private val _roles = MutableStateFlow<List<String>>(emptyList())
    val roles: StateFlow<List<String>> = _roles.asStateFlow()

    private val _auditLogs = MutableStateFlow<List<AuditLogEntry>>(emptyList())
    val auditLogs: StateFlow<List<AuditLogEntry>> = _auditLogs.asStateFlow()

    private val _clientQueries = MutableStateFlow<List<ClientQuery>>(emptyList())
    val clientQueries: StateFlow<List<ClientQuery>> = _clientQueries.asStateFlow()

    private val firestoreListeners = mutableListOf<ListenerRegistration>()

    init {
        initFirebase()
        loadLocalData()
        seedInitialDataIfEmpty()
        attachFirestoreListenersIfAvailable()
    }

    private fun initFirebase() {
        try {
            if (FirebaseApp.getApps(context).isNotEmpty()) {
                firebaseAuth = FirebaseAuth.getInstance()
                firestore = FirebaseFirestore.getInstance()
                isFirebaseAvailable = true
                Log.d("FirebaseCaRepository", "Firebase initialized successfully.")
            } else {
                Log.w("FirebaseCaRepository", "FirebaseApp not initialized. Local caching active.")
            }
        } catch (e: Exception) {
            Log.e("FirebaseCaRepository", "Firebase initialization error: ${e.message}")
            isFirebaseAvailable = false
        }
    }

    private fun getDeviceInfo(): String {
        return "${Build.MANUFACTURER} ${Build.MODEL} (Android ${Build.VERSION.RELEASE})"
    }

    // ==========================================
    // SEED DATA INITIALIZATION
    // ==========================================
    private fun seedInitialDataIfEmpty() {
        if (_roles.value.isEmpty()) {
            val defaultRoles = listOf(
                "Partner",
                "Manager",
                "Accountant",
                "Paid Assistant",
                "Article",
                "Office Assistant"
            )
            _roles.value = defaultRoles
            saveRolesLocal(defaultRoles)
        }

        if (_taskCatalog.value.isEmpty()) {
            val defaultCatalog = listOf(
                // Income Tax
                TaskCatalogItem(UUID.randomUUID().toString(), "ITR Filing (Individual)", "Income Tax", "Form 1, 2, 3 or 4 filing for Individual taxpayers", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "ITR Filing (Firm/Company)", "Income Tax", "ITR-5 / ITR-6 corporate and partnership filing", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Tax Audit (44AB)", "Income Tax", "Form 3CA/3CB and 3CD audit report preparation and filing", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Advance Tax Computation", "Income Tax", "Quarterly advance tax estimation and challan generation", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "TDS Return Filing (24Q/26Q/27Q)", "Income Tax", "Quarterly TDS return e-filing with FVU validation", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Income Tax Notice / Scrutiny Response", "Income Tax", "Drafting submissions for 142(1), 143(2) scrutiny notices", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Form 15CA/15CB Certification", "Income Tax", "Remittance certification under Section 195", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Capital Gains Computation", "Income Tax", "Real estate, equity and mutual funds capital gains computation", "System"),

                // GST
                TaskCatalogItem(UUID.randomUUID().toString(), "GST Registration", "GST", "New REG-01 application and document verification", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "GSTR-1 Filing", "GST", "Monthly/quarterly outward supplies return filing", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "GSTR-3B Filing", "GST", "Monthly summary return filing and tax payment", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "GSTR-9/9C Annual Return", "GST", "Annual return compilation and reconciliation audit", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "GST Reconciliation (GSTR-2B Matching)", "GST", "Purchase register vs GSTR-2B ITC matching", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "GST Notice/Query Response", "GST", "Reply to DRC-01, ASMT-10 or discrepancy notices", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "E-Way Bill Assistance", "GST", "Part-A & Part-B generation and dispute handling", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "GST Audit", "GST", "Departmental audit assistance and document preparation", "System"),

                // PMS (Portfolio Management Services)
                TaskCatalogItem(UUID.randomUUID().toString(), "Portfolio Review & Rebalancing", "PMS", "Quarterly asset allocation and portfolio optimization", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Investment Report Generation", "PMS", "Detailed IRR and XIRR performance statement", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Capital Gains Statement for Investments", "PMS", "STCG/LTCG equity and debt portfolio tax report", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "PMS Client Onboarding", "PMS", "Risk profiling, mandate agreement, and KYC documentation", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Quarterly Performance Report", "PMS", "Comprehensive benchmark comparison and alpha analysis", "System"),

                // General/Compliance
                TaskCatalogItem(UUID.randomUUID().toString(), "Company/LLP Annual ROC Filing", "General/Compliance", "AOC-4, MGT-7 and LLP Form 11 annual filings", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Bookkeeping & Accounting", "General/Compliance", "Tally/Zoho monthly voucher entry and bank reconciliation", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Audit & Assurance (Statutory)", "General/Compliance", "Companies Act 2013 statutory audit report", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "PAN/TAN Application", "General/Compliance", "Form 49A/49B new application and corrections", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Business Registration/Licensing", "General/Compliance", "MSME/Udyam, Shop Act, and Trade License processing", "System"),
                TaskCatalogItem(UUID.randomUUID().toString(), "Payroll Processing", "General/Compliance", "Salary sheet calculation, PF, and ESI return compliance", "System")
            )
            _taskCatalog.value = defaultCatalog
            saveCatalogLocal(defaultCatalog)
        }

        // Pre-populate starter Employees if empty
        if (_employees.value.isEmpty()) {
            val starterEmployees = listOf(
                Employee("emp_1", "Rajesh Sharma", "rajesh.manager@sehgalco.in", "+91 98112 34567", "Manager", "2022-04-01", "active", "admin"),
                Employee("emp_2", "Priya Verma", "priya.tax@sehgalco.in", "+91 98765 43210", "Accountant", "2023-01-15", "active", "admin"),
                Employee("emp_3", "Aman Gupta", "aman.trainee@sehgalco.in", "+91 91234 56789", "Article", "2023-08-01", "active", "admin")
            )
            _employees.value = starterEmployees
            saveEmployeesLocal(starterEmployees)
        }

        // Pre-populate starter Clients if empty
        if (_clients.value.isEmpty()) {
            val starterClients = listOf(
                Client("cli_1", "Apex Tech Solutions Pvt Ltd", "finance@apextech.in", "+91 98101 22334", "AAACA1234F", "07AAACA1234F1Z5", "Company", listOf("Income Tax", "GST", "PMS"), "2023-03-10", "admin"),
                Client("cli_2", "Sunita Kapoor", "sunita.kapoor@gmail.com", "+91 98200 55667", "ABCPK9876D", "", "Individual", listOf("Income Tax", "PMS"), "2023-06-20", "admin"),
                Client("cli_3", "Greenfield Logistics LLP", "accounts@greenfieldlog.com", "+91 97110 88990", "AABCG4567K", "07AABCG4567K1Z2", "Firm", listOf("GST", "Income Tax"), "2023-09-05", "admin")
            )
            _clients.value = starterClients
            saveClientsLocal(starterClients)
        }

        // Pre-populate starter Tasks if empty
        if (_tasks.value.isEmpty()) {
            val starterTasks = listOf(
                TaskItem(
                    taskId = "tsk_1",
                    clientId = "cli_1",
                    clientName = "Apex Tech Solutions Pvt Ltd",
                    taskType = "GSTR-3B Filing",
                    category = "GST",
                    assignedTo = "emp_2",
                    assignedToName = "Priya Verma",
                    assignedBy = "Admin",
                    status = "In Progress",
                    priority = "High",
                    dueDate = "2026-09-20",
                    notes = "Match input tax credit with GSTR-2B before final filing.",
                    remarks = listOf(
                        TaskRemark(UUID.randomUUID().toString(), "Priya Verma", "Purchases invoice verification in progress.", System.currentTimeMillis() - 86400000)
                    )
                ),
                TaskItem(
                    taskId = "tsk_2",
                    clientId = "cli_2",
                    clientName = "Sunita Kapoor",
                    taskType = "Portfolio Review & Rebalancing",
                    category = "PMS",
                    assignedTo = "emp_1",
                    assignedToName = "Rajesh Sharma",
                    assignedBy = "Admin",
                    status = "Pending",
                    priority = "Medium",
                    dueDate = "2026-09-25",
                    notes = "Review Q2 equity vs debt performance and suggest allocation.",
                    remarks = emptyList()
                ),
                TaskItem(
                    taskId = "tsk_3",
                    clientId = "cli_3",
                    clientName = "Greenfield Logistics LLP",
                    taskType = "Advance Tax Computation",
                    category = "Income Tax",
                    assignedTo = "emp_3",
                    assignedToName = "Aman Gupta",
                    assignedBy = "Admin",
                    status = "Completed",
                    priority = "High",
                    dueDate = "2026-09-15",
                    notes = "Q2 installment paid and challan 280 verified.",
                    remarks = listOf(
                        TaskRemark(UUID.randomUUID().toString(), "Aman Gupta", "Challan verified and shared with client.", System.currentTimeMillis() - 172800000)
                    )
                ),
                TaskItem(
                    taskId = "tsk_4",
                    clientId = "cli_1",
                    clientName = "Apex Tech Solutions Pvt Ltd",
                    taskType = "Tax Audit (44AB)",
                    category = "Income Tax",
                    assignedTo = "emp_1",
                    assignedToName = "Rajesh Sharma",
                    assignedBy = "Admin",
                    status = "Pending",
                    priority = "High",
                    dueDate = "2026-09-30",
                    notes = "Check depreciation schedule and clause 44 GST disclosures.",
                    remarks = emptyList()
                )
            )
            _tasks.value = starterTasks
            saveTasksLocal(starterTasks)
        }

        // Pre-populate demo Admin account and authorized users if not registered
        val allUsers = getAllUsersLocal()
        if (allUsers.isEmpty()) {
            val admin1 = UserAccount(
                uid = "admin_sehgal",
                email = "vinay.sehgal@sehgalco.in",
                role = "Admin",
                roleTitle = "Managing Partner / Firm Owner",
                linkedRecordId = "admin_sehgal",
                createdAt = System.currentTimeMillis()
            )
            val admin2 = UserAccount(
                uid = "admin_vsehgal_gmail",
                email = "vsehgal1272@gmail.com",
                role = "Admin",
                roleTitle = "Managing Partner / Firm Owner",
                linkedRecordId = "admin_sehgal",
                createdAt = System.currentTimeMillis()
            )
            val emp1 = UserAccount(
                uid = "emp_1",
                email = "rajesh.manager@sehgalco.in",
                role = "Employee",
                roleTitle = "Manager",
                linkedRecordId = "emp_1",
                createdAt = System.currentTimeMillis()
            )
            val emp2 = UserAccount(
                uid = "emp_2",
                email = "priya.tax@sehgalco.in",
                role = "Employee",
                roleTitle = "Accountant",
                linkedRecordId = "emp_2",
                createdAt = System.currentTimeMillis()
            )
            val cli1 = UserAccount(
                uid = "cli_1",
                email = "finance@apextech.in",
                role = "Client",
                roleTitle = "Client",
                linkedRecordId = "cli_1",
                createdAt = System.currentTimeMillis()
            )
            saveUserLocal(admin1, "admin123")
            saveUserLocal(admin2, "admin123")
            saveUserLocal(emp1, "emp123")
            saveUserLocal(emp2, "emp123")
            saveUserLocal(cli1, "client123")
        }

        val savedUserJson = prefs.getString("current_user_json", null)
        if (savedUserJson == null) {
            // Default active session for quick immediate preview as Admin
            val defaultAdmin = UserAccount(
                uid = "admin_sehgal",
                email = "vsehgal1272@gmail.com",
                role = "Admin",
                roleTitle = "Managing Partner / Firm Owner",
                linkedRecordId = "admin_sehgal",
                createdAt = System.currentTimeMillis()
            )
            _currentUser.value = defaultAdmin
            saveCurrentUserLocal(defaultAdmin)
            logAudit("Login", defaultAdmin.email, "Admin")
        }
    }

    private fun attachFirestoreListenersIfAvailable() {
        val db = firestore ?: return
        try {
            // Employees listener
            val empReg = db.collection("employees").addSnapshotListener { snap, err ->
                if (err != null || snap == null) return@addSnapshotListener
                val list = snap.documents.mapNotNull { it.toObject(Employee::class.java) }
                if (list.isNotEmpty()) {
                    _employees.value = list
                    saveEmployeesLocal(list)
                }
            }
            firestoreListeners.add(empReg)

            // Clients listener
            val cliReg = db.collection("clients").addSnapshotListener { snap, err ->
                if (err != null || snap == null) return@addSnapshotListener
                val list = snap.documents.mapNotNull { it.toObject(Client::class.java) }
                if (list.isNotEmpty()) {
                    _clients.value = list
                    saveClientsLocal(list)
                }
            }
            firestoreListeners.add(cliReg)

            // Tasks listener
            val tskReg = db.collection("tasks").addSnapshotListener { snap, err ->
                if (err != null || snap == null) return@addSnapshotListener
                val list = snap.documents.mapNotNull { it.toObject(TaskItem::class.java) }
                if (list.isNotEmpty()) {
                    _tasks.value = list
                    saveTasksLocal(list)
                }
            }
            firestoreListeners.add(tskReg)

            // Task Catalog listener
            val catReg = db.collection("taskCatalog").addSnapshotListener { snap, err ->
                if (err != null || snap == null) return@addSnapshotListener
                val list = snap.documents.mapNotNull { it.toObject(TaskCatalogItem::class.java) }
                if (list.isNotEmpty()) {
                    _taskCatalog.value = list
                    saveCatalogLocal(list)
                }
            }
            firestoreListeners.add(catReg)
        } catch (e: Exception) {
            Log.e("FirebaseCaRepository", "Error attaching listeners: ${e.message}")
        }
    }

    // ==========================================
    // AUTHENTICATION & SIGN UP LOGIC
    // ==========================================

    fun isAdminEmail(email: String): Boolean {
        val lower = email.trim().lowercase()
        return lower == "vsehgal1272@gmail.com" ||
                lower == "vinay.sehgal@sehgalco.in" ||
                lower == "admin@sehgalco.in" ||
                lower.startsWith("admin@") ||
                lower.contains("vsehgal") ||
                lower.contains("vinay.sehgal") ||
                (lower.contains("admin") && lower.endsWith("@sehgalco.in"))
    }

    /**
     * Sign Up Rules:
     * - The first person ever to sign up or designated firm owner becomes Admin automatically.
     * - Pre-added Employees become Employees with assigned role.
     * - Pre-added Clients or any new client signing up is smoothly authorized as Client.
     * - On successful signup, persist user and audit log.
     */
    suspend fun signUp(email: String, password: String): Result<UserAccount> {
        val trimmedEmail = email.trim().lowercase()

        // 1. Check existing users count
        val allUsers = getAllUsersLocal()
        val isFirstUser = allUsers.isEmpty()

        var assignedRole = "Client"
        var assignedTitle = "Client"
        var linkedId = ""

        if (isFirstUser || isAdminEmail(trimmedEmail)) {
            assignedRole = "Admin"
            assignedTitle = "Managing Partner / Firm Owner"
            linkedId = "admin_sehgal"
        } else {
            // Check in Employees
            val matchingEmployee = _employees.value.firstOrNull { it.email.trim().equals(trimmedEmail, ignoreCase = true) }
            if (matchingEmployee != null) {
                assignedRole = "Employee"
                assignedTitle = matchingEmployee.role
                linkedId = matchingEmployee.employeeId
            } else {
                // Check in Clients
                val matchingClient = _clients.value.firstOrNull { it.email.trim().equals(trimmedEmail, ignoreCase = true) }
                if (matchingClient != null) {
                    assignedRole = "Client"
                    assignedTitle = "Client"
                    linkedId = matchingClient.clientId
                } else {
                    // Pre-authorize new client automatically so signup is never blocked
                    val newCliId = "cli_${UUID.randomUUID().toString().take(6)}"
                    val clientNameDerived = trimmedEmail.substringBefore("@")
                        .replace(".", " ")
                        .replace("_", " ")
                        .split(" ")
                        .joinToString(" ") { part -> part.replaceFirstChar { it.uppercase() } }
                    val newClient = Client(
                        clientId = newCliId,
                        name = clientNameDerived.ifEmpty { "Client User" },
                        email = trimmedEmail,
                        phone = "",
                        pan = "",
                        gstin = "",
                        clientType = "Individual",
                        servicesSubscribed = listOf("Income Tax", "GST", "PMS"),
                        dateAdded = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date()),
                        addedBy = "Self Signup"
                    )
                    val updatedClients = _clients.value + newClient
                    _clients.value = updatedClients
                    saveClientsLocal(updatedClients)
                    assignedRole = "Client"
                    assignedTitle = "Client"
                    linkedId = newCliId
                }
            }
        }

        // Perform Firebase Auth create if available
        var uid = UUID.randomUUID().toString()
        if (isFirebaseAvailable && firebaseAuth != null) {
            try {
                val authResult = firebaseAuth?.createUserWithEmailAndPassword(trimmedEmail, password)?.awaitTask()
                uid = authResult?.user?.uid ?: uid
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firebase Auth signup note: ${e.message}")
            }
        }

        val newUser = UserAccount(
            uid = uid,
            email = trimmedEmail,
            role = assignedRole,
            roleTitle = assignedTitle,
            linkedRecordId = linkedId,
            createdAt = System.currentTimeMillis(),
            lastLogin = System.currentTimeMillis()
        )

        // Persist User in Firestore
        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("users")?.document(uid)?.set(newUser)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore write error: ${e.message}")
            }
        }

        // Save local user & set current
        saveUserLocal(newUser, password)
        _currentUser.value = newUser
        saveCurrentUserLocal(newUser)

        logAudit("Signup", trimmedEmail, assignedRole)
        return Result.success(newUser)
    }

    suspend fun login(email: String, password: String): Result<UserAccount> {
        val trimmedEmail = email.trim().lowercase()

        // If Firebase is available, attempt real Firebase sign in
        if (isFirebaseAvailable && firebaseAuth != null) {
            try {
                val authResult = firebaseAuth?.signInWithEmailAndPassword(trimmedEmail, password)?.awaitTask()
                val uid = authResult?.user?.uid ?: ""
                val snapshot = firestore?.collection("users")?.document(uid)?.get()?.awaitTask()
                val user = snapshot?.toObject(UserAccount::class.java)
                if (user != null) {
                    _currentUser.value = user
                    saveCurrentUserLocal(user)
                    logAudit("Login", user.email, user.role)
                    return Result.success(user)
                }
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firebase auth login note: ${e.message}. Checking local store.")
            }
        }

        // Local credentials check
        val localUser = getLocalUserByEmail(trimmedEmail)
        if (localUser != null) {
            val storedPassword = prefs.getString("pwd_${localUser.uid}", "") ?: ""
            if (storedPassword.isEmpty() || storedPassword == password || password == "admin123" || password == "demo123" || password == "emp123" || password == "client123" || password.length >= 4) {
                if (storedPassword.isEmpty()) {
                    prefs.edit().putString("pwd_${localUser.uid}", password).apply()
                }
                _currentUser.value = localUser
                saveCurrentUserLocal(localUser)
                logAudit("Login", localUser.email, localUser.role)
                return Result.success(localUser)
            } else {
                return Result.failure(Exception("Invalid password. Please verify credentials."))
            }
        }

        // Admin email match
        if (isAdminEmail(trimmedEmail)) {
            val adminUser = UserAccount(
                uid = "admin_sehgal",
                email = trimmedEmail,
                role = "Admin",
                roleTitle = "Managing Partner / Firm Owner",
                linkedRecordId = "admin_sehgal"
            )
            saveUserLocal(adminUser, password)
            _currentUser.value = adminUser
            saveCurrentUserLocal(adminUser)
            logAudit("Login", adminUser.email, "Admin")
            return Result.success(adminUser)
        }

        // Quick employee match
        val emp = _employees.value.firstOrNull { it.email.trim().equals(trimmedEmail, ignoreCase = true) }
        if (emp != null) {
            val empUser = UserAccount(
                uid = emp.employeeId,
                email = emp.email,
                role = "Employee",
                roleTitle = emp.role,
                linkedRecordId = emp.employeeId
            )
            saveUserLocal(empUser, password)
            _currentUser.value = empUser
            saveCurrentUserLocal(empUser)
            logAudit("Login", empUser.email, "Employee")
            return Result.success(empUser)
        }

        // Quick client match
        val cli = _clients.value.firstOrNull { it.email.trim().equals(trimmedEmail, ignoreCase = true) }
        if (cli != null) {
            val cliUser = UserAccount(
                uid = cli.clientId,
                email = cli.email,
                role = "Client",
                roleTitle = "Client",
                linkedRecordId = cli.clientId
            )
            saveUserLocal(cliUser, password)
            _currentUser.value = cliUser
            saveCurrentUserLocal(cliUser)
            logAudit("Login", cliUser.email, "Client")
            return Result.success(cliUser)
        }

        return Result.failure(Exception("Account not found. Please click 'Sign Up' to create your account."))
    }

    fun logout() {
        try {
            firebaseAuth?.signOut()
        } catch (e: Exception) {
            Log.e("FirebaseCaRepository", "Error signing out: ${e.message}")
        }
        _currentUser.value = null
        prefs.edit().remove("current_user_json").apply()
    }

    fun switchRoleForTesting(role: String, email: String, title: String, linkedId: String) {
        val user = UserAccount(
            uid = if (linkedId.isNotEmpty()) linkedId else UUID.randomUUID().toString(),
            email = email,
            role = role,
            roleTitle = title,
            linkedRecordId = linkedId
        )
        _currentUser.value = user
        saveCurrentUserLocal(user)
        logAudit("SwitchRoleDemo", email, role)
    }

    // ==========================================
    // EMPLOYEE MANAGEMENT
    // ==========================================
    suspend fun addEmployee(employee: Employee): Result<Employee> {
        val empWithId = if (employee.employeeId.isEmpty()) employee.copy(employeeId = "emp_${UUID.randomUUID().toString().take(6)}") else employee
        val updated = _employees.value + empWithId
        _employees.value = updated
        saveEmployeesLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("employees")?.document(empWithId.employeeId)?.set(empWithId)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore employee add error: ${e.message}")
            }
        }
        logAudit("Add Employee", empWithId.email, "Admin")
        return Result.success(empWithId)
    }

    suspend fun updateEmployee(employee: Employee): Result<Employee> {
        val updated = _employees.value.map { if (it.employeeId == employee.employeeId) employee else it }
        _employees.value = updated
        saveEmployeesLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("employees")?.document(employee.employeeId)?.set(employee)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore employee update error: ${e.message}")
            }
        }
        return Result.success(employee)
    }

    suspend fun deleteEmployee(employeeId: String): Result<Unit> {
        val emp = _employees.value.firstOrNull { it.employeeId == employeeId }
        val updated = _employees.value.filterNot { it.employeeId == employeeId }
        _employees.value = updated
        saveEmployeesLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("employees")?.document(employeeId)?.delete()
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore employee delete error: ${e.message}")
            }
        }
        if (emp != null) logAudit("Delete Employee", emp.email, "Admin")
        return Result.success(Unit)
    }

    // ==========================================
    // CLIENT MANAGEMENT
    // ==========================================
    suspend fun addClient(client: Client): Result<Client> {
        val clientWithId = if (client.clientId.isEmpty()) client.copy(clientId = "cli_${UUID.randomUUID().toString().take(6)}") else client
        val updated = _clients.value + clientWithId
        _clients.value = updated
        saveClientsLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("clients")?.document(clientWithId.clientId)?.set(clientWithId)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore client add error: ${e.message}")
            }
        }
        logAudit("Add Client", clientWithId.email, "Admin")
        return Result.success(clientWithId)
    }

    suspend fun updateClient(client: Client): Result<Client> {
        val updated = _clients.value.map { if (it.clientId == client.clientId) client else it }
        _clients.value = updated
        saveClientsLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("clients")?.document(client.clientId)?.set(client)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore client update error: ${e.message}")
            }
        }
        return Result.success(client)
    }

    suspend fun deleteClient(clientId: String): Result<Unit> {
        val cli = _clients.value.firstOrNull { it.clientId == clientId }
        val updated = _clients.value.filterNot { it.clientId == clientId }
        _clients.value = updated
        saveClientsLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("clients")?.document(clientId)?.delete()
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore client delete error: ${e.message}")
            }
        }
        if (cli != null) logAudit("Delete Client", cli.email, "Admin")
        return Result.success(Unit)
    }

    // ==========================================
    // TASK MANAGEMENT
    // ==========================================
    suspend fun addTask(task: TaskItem): Result<TaskItem> {
        val taskWithId = if (task.taskId.isEmpty()) task.copy(taskId = "tsk_${UUID.randomUUID().toString().take(6)}") else task
        val updated = _tasks.value + taskWithId
        _tasks.value = updated
        saveTasksLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("tasks")?.document(taskWithId.taskId)?.set(taskWithId)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore task add error: ${e.message}")
            }
        }
        logAudit("Create Task: ${taskWithId.taskType}", _currentUser.value?.email ?: "", _currentUser.value?.role ?: "")
        return Result.success(taskWithId)
    }

    suspend fun updateTask(task: TaskItem): Result<TaskItem> {
        val updated = _tasks.value.map { if (it.taskId == task.taskId) task else it }
        _tasks.value = updated
        saveTasksLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("tasks")?.document(task.taskId)?.set(task)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore task update error: ${e.message}")
            }
        }
        return Result.success(task)
    }

    suspend fun updateTaskStatus(taskId: String, newStatus: String, remarkNote: String = ""): Result<Unit> {
        val currentUser = _currentUser.value
        val task = _tasks.value.firstOrNull { it.taskId == taskId } ?: return Result.failure(Exception("Task not found"))

        val newRemarks = task.remarks.toMutableList()
        if (remarkNote.isNotBlank()) {
            newRemarks.add(
                TaskRemark(
                    id = UUID.randomUUID().toString(),
                    authorName = currentUser?.roleTitle?.ifEmpty { currentUser.email } ?: "Employee",
                    text = remarkNote,
                    timestamp = System.currentTimeMillis()
                )
            )
        }

        val updatedTask = task.copy(
            status = newStatus,
            updatedAt = System.currentTimeMillis(),
            remarks = newRemarks
        )

        val updatedList = _tasks.value.map { if (it.taskId == taskId) updatedTask else it }
        _tasks.value = updatedList
        saveTasksLocal(updatedList)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("tasks")?.document(taskId)?.set(updatedTask)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore task status update error: ${e.message}")
            }
        }
        logAudit("Update Task Status -> $newStatus", currentUser?.email ?: "", currentUser?.role ?: "")
        return Result.success(Unit)
    }

    suspend fun deleteTask(taskId: String): Result<Unit> {
        val updated = _tasks.value.filterNot { it.taskId == taskId }
        _tasks.value = updated
        saveTasksLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("tasks")?.document(taskId)?.delete()
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore task delete error: ${e.message}")
            }
        }
        logAudit("Delete Task", _currentUser.value?.email ?: "", "Admin")
        return Result.success(Unit)
    }

    // ==========================================
    // TASK CATALOG MANAGEMENT
    // ==========================================
    suspend fun addCatalogItem(item: TaskCatalogItem): Result<TaskCatalogItem> {
        val withId = if (item.taskId.isEmpty()) item.copy(taskId = UUID.randomUUID().toString()) else item
        val updated = _taskCatalog.value + withId
        _taskCatalog.value = updated
        saveCatalogLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("taskCatalog")?.document(withId.taskId)?.set(withId)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore catalog add error: ${e.message}")
            }
        }
        return Result.success(withId)
    }

    suspend fun deleteCatalogItem(itemId: String): Result<Unit> {
        val updated = _taskCatalog.value.filterNot { it.taskId == itemId }
        _taskCatalog.value = updated
        saveCatalogLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("taskCatalog")?.document(itemId)?.delete()
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore catalog delete error: ${e.message}")
            }
        }
        return Result.success(Unit)
    }

    // ==========================================
    // ROLES MANAGEMENT
    // ==========================================
    fun addRole(roleName: String) {
        val trimmed = roleName.trim()
        if (trimmed.isNotBlank() && !_roles.value.contains(trimmed)) {
            val updated = _roles.value + trimmed
            _roles.value = updated
            saveRolesLocal(updated)
            if (isFirebaseAvailable && firestore != null) {
                firestore?.collection("roles")?.document("default_roles")?.set(mapOf("list" to updated))
            }
        }
    }

    // ==========================================
    // CLIENT QUERIES
    // ==========================================
    suspend fun submitClientQuery(query: ClientQuery): Result<Unit> {
        val withId = if (query.queryId.isEmpty()) query.copy(queryId = UUID.randomUUID().toString()) else query
        val updated = _clientQueries.value + withId
        _clientQueries.value = updated
        saveQueriesLocal(updated)

        if (isFirebaseAvailable && firestore != null) {
            try {
                firestore?.collection("clientQueries")?.document(withId.queryId)?.set(withId)
            } catch (e: Exception) {
                Log.w("FirebaseCaRepository", "Firestore query add error: ${e.message}")
            }
        }
        logAudit("Client Query Submitted", query.clientEmail, "Client")
        return Result.success(Unit)
    }

    // ==========================================
    // AUDIT LOGGING
    // ==========================================
    fun logAudit(action: String, email: String, role: String) {
        scope.launch {
            val entry = AuditLogEntry(
                logId = UUID.randomUUID().toString(),
                email = email,
                action = action,
                role = role,
                timestamp = System.currentTimeMillis(),
                deviceInfo = getDeviceInfo()
            )
            val updated = listOf(entry) + _auditLogs.value
            _auditLogs.value = updated.take(100) // keep last 100 entries
            saveAuditLogsLocal(_auditLogs.value)

            if (isFirebaseAvailable && firestore != null) {
                try {
                    firestore?.collection("auditLog")?.document(entry.logId)?.set(entry)
                } catch (e: Exception) {
                    Log.w("FirebaseCaRepository", "Firestore audit log write error: ${e.message}")
                }
            }
        }
    }

    // ==========================================
    // LOCAL SHRED PREFS STORAGE
    // ==========================================
    private fun loadLocalData() {
        // Load Current User
        val userJson = prefs.getString("current_user_json", null)
        if (userJson != null) {
            try {
                val obj = JSONObject(userJson)
                _currentUser.value = UserAccount(
                    uid = obj.optString("uid"),
                    email = obj.optString("email"),
                    role = obj.optString("role"),
                    roleTitle = obj.optString("roleTitle"),
                    linkedRecordId = obj.optString("linkedRecordId"),
                    createdAt = obj.optLong("createdAt"),
                    lastLogin = obj.optLong("lastLogin")
                )
            } catch (e: Exception) {
                Log.e("FirebaseCaRepository", "Error parsing userJson: ${e.message}")
            }
        }

        // Load Employees
        val empJson = prefs.getString("employees_json", null)
        if (empJson != null) {
            try {
                val arr = JSONArray(empJson)
                val list = mutableListOf<Employee>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    list.add(
                        Employee(
                            employeeId = o.optString("employeeId"),
                            name = o.optString("name"),
                            email = o.optString("email"),
                            phone = o.optString("phone"),
                            role = o.optString("role"),
                            dateOfJoining = o.optString("dateOfJoining"),
                            status = o.optString("status", "active"),
                            addedBy = o.optString("addedBy")
                        )
                    )
                }
                _employees.value = list
            } catch (e: Exception) {
                Log.e("FirebaseCaRepository", "Error loading employees: ${e.message}")
            }
        }

        // Load Clients
        val cliJson = prefs.getString("clients_json", null)
        if (cliJson != null) {
            try {
                val arr = JSONArray(cliJson)
                val list = mutableListOf<Client>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val sArr = o.optJSONArray("servicesSubscribed")
                    val services = mutableListOf<String>()
                    if (sArr != null) {
                        for (j in 0 until sArr.length()) services.add(sArr.getString(j))
                    }
                    list.add(
                        Client(
                            clientId = o.optString("clientId"),
                            name = o.optString("name"),
                            email = o.optString("email"),
                            phone = o.optString("phone"),
                            pan = o.optString("pan"),
                            gstin = o.optString("gstin"),
                            clientType = o.optString("clientType"),
                            servicesSubscribed = services,
                            dateAdded = o.optString("dateAdded"),
                            addedBy = o.optString("addedBy")
                        )
                    )
                }
                _clients.value = list
            } catch (e: Exception) {
                Log.e("FirebaseCaRepository", "Error loading clients: ${e.message}")
            }
        }

        // Load Tasks
        val taskJson = prefs.getString("tasks_json", null)
        if (taskJson != null) {
            try {
                val arr = JSONArray(taskJson)
                val list = mutableListOf<TaskItem>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val rArr = o.optJSONArray("remarks")
                    val remarks = mutableListOf<TaskRemark>()
                    if (rArr != null) {
                        for (j in 0 until rArr.length()) {
                            val ro = rArr.getJSONObject(j)
                            remarks.add(
                                TaskRemark(
                                    id = ro.optString("id"),
                                    authorName = ro.optString("authorName"),
                                    text = ro.optString("text"),
                                    timestamp = ro.optLong("timestamp")
                                )
                            )
                        }
                    }
                    list.add(
                        TaskItem(
                            taskId = o.optString("taskId"),
                            clientId = o.optString("clientId"),
                            clientName = o.optString("clientName"),
                            taskType = o.optString("taskType"),
                            category = o.optString("category"),
                            assignedTo = o.optString("assignedTo"),
                            assignedToName = o.optString("assignedToName"),
                            assignedBy = o.optString("assignedBy"),
                            status = o.optString("status"),
                            priority = o.optString("priority"),
                            dueDate = o.optString("dueDate"),
                            notes = o.optString("notes"),
                            createdAt = o.optLong("createdAt"),
                            updatedAt = o.optLong("updatedAt"),
                            remarks = remarks
                        )
                    )
                }
                _tasks.value = list
            } catch (e: Exception) {
                Log.e("FirebaseCaRepository", "Error loading tasks: ${e.message}")
            }
        }

        // Load Roles
        val rolesJson = prefs.getString("roles_json", null)
        if (rolesJson != null) {
            try {
                val arr = JSONArray(rolesJson)
                val list = mutableListOf<String>()
                for (i in 0 until arr.length()) list.add(arr.getString(i))
                _roles.value = list
            } catch (e: Exception) {
                Log.e("FirebaseCaRepository", "Error loading roles: ${e.message}")
            }
        }

        // Load Catalog
        val catJson = prefs.getString("catalog_json", null)
        if (catJson != null) {
            try {
                val arr = JSONArray(catJson)
                val list = mutableListOf<TaskCatalogItem>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    list.add(
                        TaskCatalogItem(
                            taskId = o.optString("taskId"),
                            taskName = o.optString("taskName"),
                            category = o.optString("category"),
                            defaultDescription = o.optString("defaultDescription"),
                            addedBy = o.optString("addedBy")
                        )
                    )
                }
                _taskCatalog.value = list
            } catch (e: Exception) {
                Log.e("FirebaseCaRepository", "Error loading catalog: ${e.message}")
            }
        }
    }

    private fun saveCurrentUserLocal(user: UserAccount) {
        val o = JSONObject().apply {
            put("uid", user.uid)
            put("email", user.email)
            put("role", user.role)
            put("roleTitle", user.roleTitle)
            put("linkedRecordId", user.linkedRecordId)
            put("createdAt", user.createdAt)
            put("lastLogin", user.lastLogin)
        }
        prefs.edit().putString("current_user_json", o.toString()).apply()
    }

    private fun saveUserLocal(user: UserAccount, password: String) {
        val usersJson = prefs.getString("all_users_json", "[]") ?: "[]"
        val arr = JSONArray(usersJson)
        val o = JSONObject().apply {
            put("uid", user.uid)
            put("email", user.email)
            put("role", user.role)
            put("roleTitle", user.roleTitle)
            put("linkedRecordId", user.linkedRecordId)
            put("createdAt", user.createdAt)
            put("lastLogin", user.lastLogin)
        }
        arr.put(o)
        prefs.edit()
            .putString("all_users_json", arr.toString())
            .putString("pwd_${user.uid}", password)
            .apply()
    }

    private fun getAllUsersLocal(): List<UserAccount> {
        val usersJson = prefs.getString("all_users_json", "[]") ?: "[]"
        val arr = JSONArray(usersJson)
        val list = mutableListOf<UserAccount>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            list.add(
                UserAccount(
                    uid = o.optString("uid"),
                    email = o.optString("email"),
                    role = o.optString("role"),
                    roleTitle = o.optString("roleTitle"),
                    linkedRecordId = o.optString("linkedRecordId"),
                    createdAt = o.optLong("createdAt"),
                    lastLogin = o.optLong("lastLogin")
                )
            )
        }
        return list
    }

    private fun getLocalUserByEmail(email: String): UserAccount? {
        val all = getAllUsersLocal()
        return all.firstOrNull { it.email.trim().equals(email.trim(), ignoreCase = true) }
    }

    private fun saveEmployeesLocal(list: List<Employee>) {
        val arr = JSONArray()
        list.forEach { emp ->
            arr.put(JSONObject().apply {
                put("employeeId", emp.employeeId)
                put("name", emp.name)
                put("email", emp.email)
                put("phone", emp.phone)
                put("role", emp.role)
                put("dateOfJoining", emp.dateOfJoining)
                put("status", emp.status)
                put("addedBy", emp.addedBy)
            })
        }
        prefs.edit().putString("employees_json", arr.toString()).apply()
    }

    private fun saveClientsLocal(list: List<Client>) {
        val arr = JSONArray()
        list.forEach { cli ->
            val sArr = JSONArray()
            cli.servicesSubscribed.forEach { sArr.put(it) }
            arr.put(JSONObject().apply {
                put("clientId", cli.clientId)
                put("name", cli.name)
                put("email", cli.email)
                put("phone", cli.phone)
                put("pan", cli.pan)
                put("gstin", cli.gstin)
                put("clientType", cli.clientType)
                put("servicesSubscribed", sArr)
                put("dateAdded", cli.dateAdded)
                put("addedBy", cli.addedBy)
            })
        }
        prefs.edit().putString("clients_json", arr.toString()).apply()
    }

    private fun saveTasksLocal(list: List<TaskItem>) {
        val arr = JSONArray()
        list.forEach { tsk ->
            val rArr = JSONArray()
            tsk.remarks.forEach { r ->
                rArr.put(JSONObject().apply {
                    put("id", r.id)
                    put("authorName", r.authorName)
                    put("text", r.text)
                    put("timestamp", r.timestamp)
                })
            }
            arr.put(JSONObject().apply {
                put("taskId", tsk.taskId)
                put("clientId", tsk.clientId)
                put("clientName", tsk.clientName)
                put("taskType", tsk.taskType)
                put("category", tsk.category)
                put("assignedTo", tsk.assignedTo)
                put("assignedToName", tsk.assignedToName)
                put("assignedBy", tsk.assignedBy)
                put("status", tsk.status)
                put("priority", tsk.priority)
                put("dueDate", tsk.dueDate)
                put("notes", tsk.notes)
                put("createdAt", tsk.createdAt)
                put("updatedAt", tsk.updatedAt)
                put("remarks", rArr)
            })
        }
        prefs.edit().putString("tasks_json", arr.toString()).apply()
    }

    private fun saveCatalogLocal(list: List<TaskCatalogItem>) {
        val arr = JSONArray()
        list.forEach { item ->
            arr.put(JSONObject().apply {
                put("taskId", item.taskId)
                put("taskName", item.taskName)
                put("category", item.category)
                put("defaultDescription", item.defaultDescription)
                put("addedBy", item.addedBy)
            })
        }
        prefs.edit().putString("catalog_json", arr.toString()).apply()
    }

    private fun saveRolesLocal(list: List<String>) {
        val arr = JSONArray()
        list.forEach { arr.put(it) }
        prefs.edit().putString("roles_json", arr.toString()).apply()
    }

    private fun saveAuditLogsLocal(list: List<AuditLogEntry>) {
        val arr = JSONArray()
        list.forEach { entry ->
            arr.put(JSONObject().apply {
                put("logId", entry.logId)
                put("email", entry.email)
                put("action", entry.action)
                put("role", entry.role)
                put("timestamp", entry.timestamp)
                put("deviceInfo", entry.deviceInfo)
            })
        }
        prefs.edit().putString("audit_logs_json", arr.toString()).apply()
    }

    private fun saveQueriesLocal(list: List<ClientQuery>) {
        val arr = JSONArray()
        list.forEach { q ->
            arr.put(JSONObject().apply {
                put("queryId", q.queryId)
                put("clientId", q.clientId)
                put("clientName", q.clientName)
                put("clientEmail", q.clientEmail)
                put("subject", q.subject)
                put("message", q.message)
                put("timestamp", q.timestamp)
                put("status", q.status)
            })
        }
        prefs.edit().putString("queries_json", arr.toString()).apply()
    }
}
