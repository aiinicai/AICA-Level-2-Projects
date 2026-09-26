package com.example.alarm

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import com.example.data.model.IntakeLog
import com.example.data.model.Medicine
import com.example.receiver.MedicineAlarmReceiver
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

object AlarmScheduler {

    fun scheduleAlarm(
        context: Context,
        log: IntakeLog,
        medicine: Medicine?,
        vibrateInsteadOfSound: Boolean = false
    ) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return

        val baseDate = com.example.util.DateUtils.parseDate(log.scheduledDate) ?: return
        val cal = Calendar.getInstance().apply {
            time = baseDate
            val timeParts = log.scheduledTime.split(":")
            if (timeParts.size >= 2) {
                set(Calendar.HOUR_OF_DAY, timeParts[0].trim().toIntOrNull() ?: 8)
                set(Calendar.MINUTE, timeParts[1].trim().toIntOrNull() ?: 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
        }
        val triggerAtMillis = cal.timeInMillis

        // Alarm should alert strictly at the medicine time, not on overdue time
        if (triggerAtMillis <= System.currentTimeMillis()) {
            return
        }

        val targetTrigger = triggerAtMillis

        val intent = Intent(context, MedicineAlarmReceiver::class.java).apply {
            action = MedicineAlarmReceiver.ACTION_MEDICINE_ALARM
            putExtra(MedicineAlarmReceiver.EXTRA_LOG_ID, log.id)
            putExtra(MedicineAlarmReceiver.EXTRA_MEDICINE_NAME, medicine?.name ?: "Medicine")
            val effectiveDose = log.dosage.ifBlank { medicine?.dosage ?: "1 Dose" }
            putExtra(MedicineAlarmReceiver.EXTRA_DOSAGE, effectiveDose)
            putExtra(MedicineAlarmReceiver.EXTRA_INSTRUCTIONS, log.notes.ifBlank { medicine?.instructions ?: "As prescribed" })
            putExtra(MedicineAlarmReceiver.EXTRA_VIBRATE, vibrateInsteadOfSound)
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            log.id.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    targetTrigger,
                    pendingIntent
                )
            } else {
                alarmManager.setExact(
                    AlarmManager.RTC_WAKEUP,
                    targetTrigger,
                    pendingIntent
                )
            }
        } catch (_: SecurityException) {
            try {
                alarmManager.set(
                    AlarmManager.RTC_WAKEUP,
                    targetTrigger,
                    pendingIntent
                )
            } catch (_: Exception) {}
        } catch (_: Exception) {
            alarmManager.set(
                AlarmManager.RTC_WAKEUP,
                targetTrigger,
                pendingIntent
            )
        }
    }

    fun triggerTestAlarm(context: Context, secondsFromNow: Int = 3, medicineName: String = "Telmisartan 40mg") {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val triggerTime = System.currentTimeMillis() + (secondsFromNow * 1000L)

        val intent = Intent(context, MedicineAlarmReceiver::class.java).apply {
            action = MedicineAlarmReceiver.ACTION_MEDICINE_ALARM
            putExtra(MedicineAlarmReceiver.EXTRA_LOG_ID, 9999L)
            putExtra(MedicineAlarmReceiver.EXTRA_MEDICINE_NAME, medicineName)
            putExtra(MedicineAlarmReceiver.EXTRA_DOSAGE, "1 Tablet")
            putExtra(MedicineAlarmReceiver.EXTRA_INSTRUCTIONS, "Take with water after food")
            putExtra(MedicineAlarmReceiver.EXTRA_VIBRATE, false)
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            9999,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
            } else {
                alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
            }
        } catch (_: Exception) {
            alarmManager.set(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
        }
    }

    fun cancelAlarm(context: Context, logId: Long) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val intent = Intent(context, MedicineAlarmReceiver::class.java).apply {
            action = MedicineAlarmReceiver.ACTION_MEDICINE_ALARM
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            logId.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        alarmManager.cancel(pendingIntent)
    }
}
