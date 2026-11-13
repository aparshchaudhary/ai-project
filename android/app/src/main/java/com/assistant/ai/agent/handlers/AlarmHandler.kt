package com.assistant.ai.agent.handlers

import android.content.Context
import android.content.Intent
import android.provider.AlarmClock

class AlarmHandler(private val context: Context) {

    fun setAlarm(hour: Int, minutes: Int, message: String = "Agent Alarm"): Result<String> {
        return try {
            val intent = Intent(AlarmClock.ACTION_SET_ALARM).apply {
                putExtra(AlarmClock.EXTRA_HOUR, hour)
                putExtra(AlarmClock.EXTRA_MINUTES, minutes)
                putExtra(AlarmClock.EXTRA_MESSAGE, message)
                putExtra(AlarmClock.EXTRA_SKIP_UI, true)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            val timeFormatted = String.format("%02d:%02d", hour, minutes)
            Result.success("Alarm set for $timeFormatted ($message)")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
