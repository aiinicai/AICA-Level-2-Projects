package com.example.data.model

import com.google.firebase.firestore.Exclude

enum class UserRole(val displayName: String, val description: String) {
    ADMIN("Admin", "Full Control: Assign, edit, delete tasks, projects, tax notices & manage permissions"),
    PARTNER("Partner", "Partner Access: Strategic firm oversight, statutory portals, team management & approvals"),
    MANAGER("Manager", "Management: Assign tasks, create projects, broadcast alerts & view all progress"),
    TEAM_MEMBER("Team Member", "Execution: View assigned tasks, track milestones & update progress");

    val isPartnerOrAdmin: Boolean
        get() = this == ADMIN || this == PARTNER
}

/**
 * Synced live via Firestore (collection "teamMembers") so the roster is shared across every device.
 *
 * The document ID is the member's Firebase Authentication UID. Security rules resolve a
 * caller's role by reading teamMembers/{request.auth.uid}, so that must hold for every member.
 * Credentials live in Firebase Auth and are deliberately absent here.
 */
data class TeamMember(
    val id: String = "",
    val name: String = "",
    val role: String = "", // e.g. Senior Managing Partner & Office Admin
    val userRole: UserRole = UserRole.TEAM_MEMBER,
    val department: String = "Direct & Indirect Tax",
    val email: String = "",
    val phone: String = "",
    val avatarColorHex: String = "#1E40AF",
    val isPrimaryAdmin: Boolean = false,
    val createdDateMillis: Long = System.currentTimeMillis()
) {
    // Derived from userRole — @Exclude keeps Firestore from persisting it as a real field
    // that could later disagree with userRole, or be trusted by security rules.
    @get:Exclude
    val isPartnerOrAdmin: Boolean
        get() = isPrimaryAdmin || userRole.isPartnerOrAdmin || role.contains("Partner", ignoreCase = true) || role.contains("Admin", ignoreCase = true)
}
