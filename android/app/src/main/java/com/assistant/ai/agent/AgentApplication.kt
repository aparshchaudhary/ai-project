package com.assistant.ai.agent

import android.app.Application
import android.content.Intent
import android.os.Build
import com.assistant.ai.agent.service.AgentBackgroundService

class AgentApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        startAgentService()
    }

    private fun startAgentService() {
        val serviceIntent = Intent(this, AgentBackgroundService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }
}
