package com.example.data.model

data class UserAccount(
    val uid: String = "",
    val email: String = "",
    val role: String = "Client", // "Admin", "Employee", "Client"
    val roleTitle: String = "",  // e.g. "Partner", "Manager", "Accountant", "Client"
    val linkedRecordId: String = "", // employeeId or clientId
    val createdAt: Long = System.currentTimeMillis(),
    val lastLogin: Long = System.currentTimeMillis()
)

data class Employee(
    val employeeId: String = "",
    val name: String = "",
    val email: String = "",
    val phone: String = "",
    val role: String = "Accountant", // Partner, Manager, Accountant, Paid Assistant, Article, Office Assistant, or custom
    val dateOfJoining: String = "",
    val status: String = "active", // active, inactive
    val addedBy: String = ""
)

data class Client(
    val clientId: String = "",
    val name: String = "",
    val email: String = "",
    val phone: String = "",
    val pan: String = "",
    val gstin: String = "",
    val clientType: String = "Individual", // Individual, Firm, Company, HUF, Trust
    val servicesSubscribed: List<String> = emptyList(), // "Income Tax", "GST", "PMS"
    val dateAdded: String = "",
    val addedBy: String = ""
)

data class TaskRemark(
    val id: String = "",
    val authorName: String = "",
    val text: String = "",
    val timestamp: Long = System.currentTimeMillis()
)

data class TaskItem(
    val taskId: String = "",
    val clientId: String = "",
    val clientName: String = "",
    val taskType: String = "",
    val category: String = "General", // "Income Tax", "GST", "PMS", "General/Compliance"
    val assignedTo: String = "",       // employeeId or uid
    val assignedToName: String = "",
    val assignedBy: String = "",
    val status: String = "Pending",   // "Pending", "In Progress", "Completed"
    val priority: String = "Medium",  // "Low", "Medium", "High"
    val dueDate: String = "",          // YYYY-MM-DD
    val notes: String = "",
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val remarks: List<TaskRemark> = emptyList()
)

data class TaskCatalogItem(
    val taskId: String = "",
    val taskName: String = "",
    val category: String = "Income Tax",
    val defaultDescription: String = "",
    val addedBy: String = ""
)

data class AuditLogEntry(
    val logId: String = "",
    val email: String = "",
    val action: String = "", // "Signup", "Login", "Create Task", "Update Status"
    val role: String = "",
    val timestamp: Long = System.currentTimeMillis(),
    val deviceInfo: String = ""
)

data class ClientQuery(
    val queryId: String = "",
    val clientId: String = "",
    val clientName: String = "",
    val clientEmail: String = "",
    val subject: String = "",
    val message: String = "",
    val timestamp: Long = System.currentTimeMillis(),
    val status: String = "Open"
)
