package com.example.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

enum class TaxDepartment {
    GST,
    INCOME_TAX
}

enum class TaxSeverity {
    NORMAL, IMPORTANT, CRITICAL_ACTION_REQUIRED
}

@Entity(tableName = "tax_notifications")
data class TaxNotification(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val title: String,
    val department: TaxDepartment,
    val circularOrNotificationNo: String,
    val issueDateFormatted: String,
    val effectiveDateFormatted: String,
    val summary: String,
    val keyActionItems: String,
    val deadlineDateMillis: Long,
    val severity: TaxSeverity = TaxSeverity.IMPORTANT,
    val isRead: Boolean = false,
    val isPushedToTasks: Boolean = false,
    val sourceAuthority: String = "CBIC / CBDT",
    val createdTimestamp: Long = System.currentTimeMillis()
)
