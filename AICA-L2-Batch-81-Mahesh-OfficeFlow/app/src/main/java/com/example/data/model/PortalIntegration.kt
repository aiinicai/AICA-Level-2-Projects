package com.example.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

enum class IntegrationType(val displayName: String, val badgeColor: String) {
    GST("GST Portal", "#1E40AF"),
    INCOME_TAX("Income Tax e-Filing", "#047857"),
    MCA("MCA21 / Corporate", "#7C3AED"),
    EWAY_BILL("e-Way Bill System", "#0284C7"),
    EPFO("EPFO / ESIC", "#D97706"),
    CUSTOM_WEBHOOK("Custom Webhook / API", "#475569")
}

@Entity(tableName = "portal_integrations")
data class PortalIntegration(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val name: String,
    val type: IntegrationType,
    val portalUrl: String,
    val webhookUrl: String = "",
    val apiKeyOrClientId: String = "",
    val isEnabled: Boolean = true,
    val statusText: String = "Connected",
    val lastSyncMillis: Long = System.currentTimeMillis(),
    val description: String = ""
)
