package com.example.data.model

enum class TaskPriority {
    LOW, MEDIUM, HIGH, URGENT
}

enum class TaskStatus {
    TODO, IN_PROGRESS, IN_REVIEW, COMPLETED
}

enum class TaskCategory {
    GST_COMPLIANCE,
    INCOME_TAX,
    INTERNAL_AUDIT,
    PAYROLL,
    CLIENT_PROJECT,
    OPERATIONS,
    LEGAL_SECRETARIAL
}

/** Synced live via Firestore (collection "tasks") so every device shares the same task list. */
data class TaskItem(
    val id: String = "",
    val title: String = "",
    val description: String = "",
    val assignedMemberId: String = "",
    val assignedMemberName: String = "Unassigned",
    val assignedMemberRole: String = "",
    val assignedBy: String = "Mahesh",
    val assignedByMemberId: String = "",
    val projectId: String = "",
    val projectName: String = "General Office",
    val priority: TaskPriority = TaskPriority.MEDIUM,
    val status: TaskStatus = TaskStatus.TODO,
    val progressPercentage: Int = 0, // 0 - 100
    val dueDateMillis: Long = System.currentTimeMillis(),
    val category: TaskCategory = TaskCategory.CLIENT_PROJECT,
    val monthlyRepetitiveCategory: String = "NONE", // ACCOUNTS, PAYROLL, TDS, GST, NONE
    val tags: String = "", // Comma-separated tags e.g. "Audit2024,MSME,Statutory"
    val checklistItems: String = "", // Comma-separated or newline-separated checklist
    val completedChecklistCount: Int = 0,
    val totalChecklistCount: Int = 0,
    val lastProgressRemark: String = "",
    val createdMillis: Long = System.currentTimeMillis(),
    val updatedMillis: Long = System.currentTimeMillis()
)

val TaskItem.tagList: List<String>
    get() = if (tags.isBlank()) emptyList() else tags.split(",").map { it.trim() }.filter { it.isNotEmpty() }
