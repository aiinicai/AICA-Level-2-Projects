package com.example.data.model

enum class ProjectStatus {
    PLANNING, ACTIVE, ON_HOLD, COMPLETED, CRITICAL
}

/** Synced live via Firestore (collection "projects") so every device shares the same project list. */
data class Project(
    val id: String = "",
    val name: String = "",
    val code: String = "",
    val clientName: String = "",
    val description: String = "",
    val leadMemberName: String = "Lead",
    val startDateMillis: Long = System.currentTimeMillis(),
    val targetDateMillis: Long = System.currentTimeMillis() + (30L * 24 * 60 * 60 * 1000),
    val status: ProjectStatus = ProjectStatus.ACTIVE,
    val progressPercentage: Int = 0,
    val category: String = "Tax & Audit",
    val colorHex: String = "#1D4ED8",
    val lastUpdateRemark: String = "Project initialized"
)
