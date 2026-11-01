package com.example.data.reminder

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.example.MainActivity
import com.example.R
import com.example.data.model.Medication
import java.util.Calendar
import java.util.Locale

object MedicationNotificationManager {
    const val CHANNEL_ID = "medication_reminders_channel"
    private const val CHANNEL_NAME = "Medication Dose Reminders"
    private const val CHANNEL_DESC = "Audio & visual alerts when senior doses are scheduled to be taken"

    const val ACTION_REMINDER = "com.example.ACTION_MEDICATION_REMINDER"
    const val EXTRA_MED_ID = "extra_med_id"
    const val EXTRA_MED_NAME = "extra_med_name"
    const val EXTRA_MED_DOSAGE = "extra_med_dosage"
    const val EXTRA_MED_TIME = "extra_med_time"
    const val EXTRA_MED_INSTRUCTIONS = "extra_med_instructions"

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val importance = NotificationManager.IMPORTANCE_HIGH
            val channel = NotificationChannel(CHANNEL_ID, CHANNEL_NAME, importance).apply {
                description = CHANNEL_DESC
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 450, 200, 450)
                setShowBadge(true)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    fun scheduleMedicationAlarm(
        context: Context,
        medication: Medication,
        delayMillis: Long? = null
    ) {
        createNotificationChannel(context)

        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

        val intent = Intent(context, MedicationAlarmReceiver::class.java).apply {
            action = ACTION_REMINDER
            putExtra(EXTRA_MED_ID, medication.id)
            putExtra(EXTRA_MED_NAME, medication.name)
            putExtra(EXTRA_MED_DOSAGE, medication.dosage)
            putExtra(EXTRA_MED_TIME, medication.scheduledTime)
            putExtra(EXTRA_MED_INSTRUCTIONS, medication.mealInstructions)
        }

        val requestCode = medication.id.hashCode()
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val triggerAtMillis = if (delayMillis != null) {
            System.currentTimeMillis() + delayMillis
        } else {
            calculateNextTriggerMillis(medication.scheduledTime)
        }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                if (alarmManager.canScheduleExactAlarms()) {
                    alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        triggerAtMillis,
                        pendingIntent
                    )
                } else {
                    alarmManager.setAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        triggerAtMillis,
                        pendingIntent
                    )
                }
            } else {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    triggerAtMillis,
                    pendingIntent
                )
            }
            Log.d("MedNotificationManager", "Scheduled reminder for ${medication.name} at timestamp $triggerAtMillis")
        } catch (e: SecurityException) {
            Log.w("MedNotificationManager", "SecurityException scheduling exact alarm, falling back to inexact", e)
            alarmManager.set(AlarmManager.RTC_WAKEUP, triggerAtMillis, pendingIntent)
        }
    }

    fun cancelMedicationAlarm(context: Context, medicationId: String) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val intent = Intent(context, MedicationAlarmReceiver::class.java).apply {
            action = ACTION_REMINDER
        }
        val requestCode = medicationId.hashCode()
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager.cancel(pendingIntent)
    }

    fun showNotification(
        context: Context,
        medId: String,
        medName: String,
        dosage: String,
        time: String,
        instructions: String
    ) {
        createNotificationChannel(context)

        // Intent to launch MainActivity when notification is tapped
        val openIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("NAVIGATE_TO", "MEDICINES")
        }
        val openPendingIntent = PendingIntent.getActivity(
            context,
            medId.hashCode(),
            openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val contentTitle = "Time for $medName ($dosage)"
        val contentText = "Scheduled for $time • $instructions"
        val bigText = "Dear Eleanor, it is time for your scheduled medicine dose.\n\n💊 $medName ($dosage)\n⏰ $time\n📋 $instructions\n\nTap to open your schedule and confirm 'I Took It'."

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(contentTitle)
            .setContentText(contentText)
            .setStyle(NotificationCompat.BigTextStyle().bigText(bigText))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setAutoCancel(true)
            .setContentIntent(openPendingIntent)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .build()

        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(medId.hashCode(), notification)
    }

    private fun calculateNextTriggerMillis(timeString: String): Long {
        val calendar = Calendar.getInstance()
        val now = Calendar.getInstance()

        try {
            // Parses e.g. "8:00 AM", "1:00 PM", "8:00 PM"
            val parts = timeString.trim().split(" ")
            if (parts.size == 2) {
                val timeParts = parts[0].split(":")
                var hour = timeParts[0].toInt()
                val minute = if (timeParts.size > 1) timeParts[1].toInt() else 0
                val amPm = parts[1].uppercase(Locale.getDefault())

                if (amPm == "PM" && hour < 12) hour += 12
                if (amPm == "AM" && hour == 12) hour = 0

                calendar.set(Calendar.HOUR_OF_DAY, hour)
                calendar.set(Calendar.MINUTE, minute)
                calendar.set(Calendar.SECOND, 0)
                calendar.set(Calendar.MILLISECOND, 0)

                if (calendar.before(now)) {
                    // Time has passed today, schedule for same time tomorrow
                    calendar.add(Calendar.DAY_OF_YEAR, 1)
                }
                return calendar.timeInMillis
            }
        } catch (e: Exception) {
            Log.e("MedNotificationManager", "Error parsing time: $timeString", e)
        }

        // Fallback: 1 hour from now
        return System.currentTimeMillis() + 3600000L
    }
}
