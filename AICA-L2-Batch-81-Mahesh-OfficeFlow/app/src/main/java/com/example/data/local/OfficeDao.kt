package com.example.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.data.model.OfficeActivityNotification
import com.example.data.model.PortalIntegration
import com.example.data.model.TaxNotification
import kotlinx.coroutines.flow.Flow

// Tasks, projects, and team members moved to Firestore — see OfficeRepository.
@Dao
interface OfficeDao {

    // --- Tax Notifications ---
    @Query("SELECT * FROM tax_notifications ORDER BY deadlineDateMillis ASC, id DESC")
    fun getAllTaxNotifications(): Flow<List<TaxNotification>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTaxNotification(notification: TaxNotification): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTaxNotifications(notifications: List<TaxNotification>)

    @Update
    suspend fun updateTaxNotification(notification: TaxNotification)

    @Query("UPDATE tax_notifications SET isRead = 1 WHERE id = :id")
    suspend fun markTaxNotificationAsRead(id: Long)

    @Query("UPDATE tax_notifications SET isPushedToTasks = 1 WHERE id = :id")
    suspend fun markTaxNotificationPushed(id: Long)

    @Query("DELETE FROM tax_notifications")
    suspend fun clearAllTaxNotifications()

    // --- Portal & Website Integrations ---
    @Query("SELECT * FROM portal_integrations ORDER BY id ASC")
    fun getAllPortalIntegrations(): Flow<List<PortalIntegration>>

    @Query("SELECT * FROM portal_integrations WHERE id = :id LIMIT 1")
    suspend fun getPortalIntegrationById(id: Long): PortalIntegration?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPortalIntegration(integration: PortalIntegration): Long

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPortalIntegrations(integrations: List<PortalIntegration>)

    @Update
    suspend fun updatePortalIntegration(integration: PortalIntegration)

    @Query("UPDATE portal_integrations SET statusText = :status, lastSyncMillis = :lastSync WHERE id = :id")
    suspend fun updatePortalSyncStatus(id: Long, status: String, lastSync: Long)

    @Delete
    suspend fun deletePortalIntegration(integration: PortalIntegration)

    @Query("DELETE FROM portal_integrations")
    suspend fun clearAllPortalIntegrations()

    // --- Activity / Real-time Notifications ---
    @Query("SELECT * FROM activity_notifications ORDER BY timestampMillis DESC")
    fun getAllActivityNotifications(): Flow<List<OfficeActivityNotification>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertActivityNotification(notification: OfficeActivityNotification): Long

    @Query("UPDATE activity_notifications SET isRead = 1 WHERE id = :id")
    suspend fun markActivityAsRead(id: Long)

    @Query("UPDATE activity_notifications SET isRead = 1")
    suspend fun markAllActivitiesAsRead()

    @Query("DELETE FROM activity_notifications")
    suspend fun clearAllActivityNotifications()
}
