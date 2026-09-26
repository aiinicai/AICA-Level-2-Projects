package com.example.alarm

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

data class LiveAlarmEvent(
    val logId: Long,
    val medicineName: String,
    val dosage: String,
    val instructions: String
)

object AlarmTriggerHub {
    private val _liveAlarmEvents = MutableSharedFlow<LiveAlarmEvent>(extraBufferCapacity = 10)
    val liveAlarmEvents: SharedFlow<LiveAlarmEvent> = _liveAlarmEvents.asSharedFlow()

    fun triggerLiveAlarm(
        logId: Long,
        medicineName: String,
        dosage: String,
        instructions: String
    ) {
        _liveAlarmEvents.tryEmit(
            LiveAlarmEvent(
                logId = logId,
                medicineName = medicineName,
                dosage = dosage,
                instructions = instructions
            )
        )
    }
}
