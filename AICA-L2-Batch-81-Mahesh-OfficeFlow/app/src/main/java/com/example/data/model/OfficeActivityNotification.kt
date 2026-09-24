package com.example.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey

enum class ActivityType {
    TASK_ASSIGNED,
    PROGRESS_PUSHED,
    DEADLINE_ALERT,
    TAX_CIRCULAR_ALERT,
    PROJECT_UPDATE,
    STATUS_CHANGED
}

@Entity(tableName = "activity_notifications")
data class OfficeActivityNotification(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val title: String,
    val message: String,
    val type: ActivityType,
    val timestampMillis: Long = System.currentTimeMillis(),
    val isRead: Boolean = false,
    val relatedEntityId: Long = 0,
    val actorName: String = "Office Manager"
)
