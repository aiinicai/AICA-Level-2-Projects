package com.example.receiver

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.RingtoneManager
import android.os.Build
import androidx.core.app.NotificationCompat
import com.example.MainActivity
import com.example.R
import com.example.alarm.AlarmRingtonePlayer
import com.example.alarm.AlarmScheduler
import com.example.alarm.AlarmTriggerHub
import com.example.data.database.AppDatabase
import com.example.util.DateUtils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.launch

class MedicineAlarmReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action

        // Handle reboot or app update - reschedule all upcoming alarms for today
        if (action == Intent.ACTION_BOOT_COMPLETED || action == "android.intent.action.QUICKBOOT_POWERON" || action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            val pendingResult = goAsync()
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val db = AppDatabase.getInstance(context)
                    val dao = db.medicineDao()
                    val today = DateUtils.getToday()

                    val todayLogs = dao.getAllIntakeLogsForDate(today, DateUtils.getAlternateDateFormat(today)).firstOrNull() ?: emptyList()
                    val medicines = dao.getAllMedicines().firstOrNull() ?: emptyList()
                    val medMap = medicines.associateBy { it.id }

                    for (log in todayLogs.filter { it.status == "PENDING" || it.status == "SNOOZED" }) {
                        val med = medMap[log.medicineId]
                        AlarmScheduler.scheduleAlarm(context, log, med)
                    }
                } catch (_: Exception) {} finally {
                    pendingResult.finish()
                }
            }
            return
        }

        val medicineName = intent.getStringExtra(EXTRA_MEDICINE_NAME) ?: "Prescribed Medicine"
        val dosage = intent.getStringExtra(EXTRA_DOSAGE) ?: "1 Dose"
        val instructions = intent.getStringExtra(EXTRA_INSTRUCTIONS) ?: "As prescribed"
        val logId = intent.getLongExtra(EXTRA_LOG_ID, -1L)

        // Check audio mode
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
        val isSilentOrDnd = audioManager?.ringerMode != AudioManager.RINGER_MODE_NORMAL
        val vibrateOnly = isSilentOrDnd || intent.getBooleanExtra(EXTRA_VIBRATE, false)

        // 1. Ring alarm audio and vibrate immediately via AlarmRingtonePlayer
        try {
            AlarmRingtonePlayer.play(context, vibrateOnly)
        } catch (_: Exception) {}

        // 2. Dispatch to live UI hub (if app is in foreground, opens overlay immediately)
        AlarmTriggerHub.triggerLiveAlarm(logId, medicineName, dosage, instructions)

        // 3. Notification Channel setup with USAGE_ALARM
        val channelId = "medicine_reminder_alarm_v3"
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        val alarmSound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
            ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val audioAttributes = AudioAttributes.Builder()
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(AudioAttributes.USAGE_ALARM)
                .build()

            val channel = NotificationChannel(
                channelId,
                "Medicine Intake Reminders",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "High visibility reminders and alarms for scheduled medicines"
                enableLights(true)
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 800, 400, 800)
                setSound(alarmSound, audioAttributes)
                lockscreenVisibility = NotificationCompat.VISIBILITY_PUBLIC
                setBypassDnd(true)
            }
            notificationManager.createNotificationChannel(channel)
        }

        // Full screen / Open app intent
        val openIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("EXTRA_ALARM_TRIGGERED", true)
            putExtra("EXTRA_LOG_ID", logId)
            putExtra("EXTRA_MED_NAME", medicineName)
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            (logId.toInt().takeIf { it != -1 } ?: 1001),
            openIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        try {
            context.startActivity(openIntent)
        } catch (_: Exception) {}

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("⏰ Time to take: $medicineName")
            .setContentText("Dose: $dosage • $instructions")
            .setStyle(
                NotificationCompat.BigTextStyle()
                    .bigText("💊 Medicine: $medicineName\n📋 Dosage: $dosage\n📝 Note: $instructions\n\nTap to record dose or snooze schedule.")
            )
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setAutoCancel(true)
            .setSound(alarmSound)
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true)
            .build()

        val notificationId = if (logId != -1L) logId.toInt() else 1002
        notificationManager.notify(notificationId, notification)
    }

    companion object {
        const val ACTION_MEDICINE_ALARM = "com.example.ACTION_MEDICINE_ALARM"
        const val EXTRA_LOG_ID = "EXTRA_LOG_ID"
        const val EXTRA_MEDICINE_NAME = "EXTRA_MEDICINE_NAME"
        const val EXTRA_DOSAGE = "EXTRA_DOSAGE"
        const val EXTRA_INSTRUCTIONS = "EXTRA_INSTRUCTIONS"
        const val EXTRA_VIBRATE = "EXTRA_VIBRATE"
    }
}
