package com.example.data.reminder

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class MedicationAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.d("MedicationAlarmReceiver", "Received alarm action: ${intent.action}")

        val medId = intent.getStringExtra(MedicationNotificationManager.EXTRA_MED_ID) ?: "med_unknown"
        val medName = intent.getStringExtra(MedicationNotificationManager.EXTRA_MED_NAME) ?: "Daily Medication"
        val dosage = intent.getStringExtra(MedicationNotificationManager.EXTRA_MED_DOSAGE) ?: "Prescribed Dose"
        val time = intent.getStringExtra(MedicationNotificationManager.EXTRA_MED_TIME) ?: "Now"
        val instructions = intent.getStringExtra(MedicationNotificationManager.EXTRA_MED_INSTRUCTIONS) ?: "Take with water"

        MedicationNotificationManager.showNotification(
            context = context,
            medId = medId,
            medName = medName,
            dosage = dosage,
            time = time,
            instructions = instructions
        )
    }
}
