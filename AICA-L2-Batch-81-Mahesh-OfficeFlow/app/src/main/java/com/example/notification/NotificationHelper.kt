package com.example.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.example.MainActivity
import java.util.concurrent.atomic.AtomicInteger

object NotificationHelper {
    const val CHANNEL_ID_OFFICE = "office_progress_channel"
    const val CHANNEL_ID_TAX = "tax_compliance_channel"
    private val notificationIdCounter = AtomicInteger(100)

    fun createNotificationChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val progressChannel = NotificationChannel(
                CHANNEL_ID_OFFICE,
                "Office Tasks & Project Progress",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Real-time updates on team progress, assigned tasks, and milestones"
                enableVibration(true)
            }

            val taxChannel = NotificationChannel(
                CHANNEL_ID_TAX,
                "GST & Income Tax Statutory Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Urgent statutory tax circulars, return due dates and compliance advisories"
                enableVibration(true)
            }

            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
            manager?.createNotificationChannel(progressChannel)
            manager?.createNotificationChannel(taxChannel)
        }
    }

    fun showNotification(
        context: Context,
        title: String,
        message: String,
        isTaxAlert: Boolean = false,
        priorityHigh: Boolean = true
    ) {
        try {
            val channelId = if (isTaxAlert) CHANNEL_ID_TAX else CHANNEL_ID_OFFICE

            val intent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            val pendingIntent = PendingIntent.getActivity(
                context,
                0,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val builder = NotificationCompat.Builder(context, channelId)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(message)
                .setStyle(NotificationCompat.BigTextStyle().bigText(message))
                .setPriority(if (priorityHigh) NotificationCompat.PRIORITY_HIGH else NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent)

            val notificationManager = NotificationManagerCompat.from(context)
            notificationManager.notify(notificationIdCounter.incrementAndGet(), builder.build())
        } catch (e: SecurityException) {
            // Permission not granted yet on Android 13+; in-app feed handles notification
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
