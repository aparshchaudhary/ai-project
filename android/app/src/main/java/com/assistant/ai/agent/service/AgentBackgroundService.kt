package com.assistant.ai.agent.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.assistant.ai.agent.handlers.*
import com.assistant.ai.agent.models.RemoteTaskDispatch
import com.assistant.ai.agent.models.RemoteTaskResult
import com.assistant.ai.agent.network.AgentWebSocketClient
import kotlinx.coroutines.*
import okhttp3.OkHttpClient

class AgentBackgroundService : Service() {

    private var wsClient: AgentWebSocketClient? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private lateinit var callingHandler: CallingHandler
    private lateinit var whatsAppHandler: WhatsAppHandler
    private lateinit var contactsHandler: ContactsHandler
    private lateinit var settingsHandler: SettingsHandler
    private lateinit var alarmHandler: AlarmHandler
    private lateinit var galleryHandler: GalleryHandler
    private lateinit var appLauncherHandler: AppLauncherHandler
    private lateinit var fileTransferHandler: FileTransferHandler

    companion object {
        const val CHANNEL_ID = "agent_foreground_channel"
        const val NOTIFICATION_ID = 1001

        var isConnected = false
            private set
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildForegroundNotification("Connecting to AI Orchestrator..."))

        callingHandler = CallingHandler(this)
        whatsAppHandler = WhatsAppHandler(this)
        contactsHandler = ContactsHandler(this)
        settingsHandler = SettingsHandler(this)
        alarmHandler = AlarmHandler(this)
        galleryHandler = GalleryHandler(this)
        appLauncherHandler = AppLauncherHandler(this)
        fileTransferHandler = FileTransferHandler(this, OkHttpClient())

        val prefs = getSharedPreferences("agent_prefs", Context.MODE_PRIVATE)
        val serverUrl = prefs.getString("server_url", "https://aura-voice-assistant.onrender.com") ?: "https://aura-voice-assistant.onrender.com"
        val deviceId = prefs.getString("device_id", "android_phone") ?: "android_phone"

        wsClient = AgentWebSocketClient(
            serverUrl = serverUrl,
            deviceId = deviceId,
            onTaskReceived = { dispatch -> handleTask(dispatch) },
            onConnectionChanged = { connected ->
                isConnected = connected
                val statusText = if (connected) "Connected to Central Orchestrator" else "Reconnecting..."
                updateNotification(statusText)
            }
        )
        wsClient?.connect()
    }

    private suspend fun handleTask(dispatch: RemoteTaskDispatch) {
        val startTime = System.currentTimeMillis()
        var status = "completed"
        var errorMessage: String? = null
        val resultData = mutableMapOf<String, String>()

        try {
            when (dispatch.intent) {
                "make_call" -> {
                    val phone = dispatch.action_params["phone"] ?: ""
                    val contact = dispatch.action_params["contact"] ?: "Contact"
                    val resolvedPhone = if (phone.isBlank()) {
                        val matches = contactsHandler.searchContacts(contact)
                        matches.firstOrNull()?.phone ?: phone
                    } else phone

                    val res = callingHandler.makeCall(resolvedPhone)
                    if (res.isSuccess) {
                        resultData["message"] = res.getOrNull() ?: "Call initiated"
                        resultData["phone"] = resolvedPhone
                    } else {
                        status = "failed"
                        errorMessage = res.exceptionOrNull()?.message ?: "Failed to initiate call"
                    }
                }

                "send_message" -> {
                    val phone = dispatch.action_params["phone"] ?: ""
                    val message = dispatch.action_params["message"] ?: "Hi"
                    val contact = dispatch.action_params["contact"] ?: "Contact"
                    val resolvedPhone = if (phone.isBlank()) {
                        val matches = contactsHandler.searchContacts(contact)
                        matches.firstOrNull()?.phone ?: phone
                    } else phone

                    val res = whatsAppHandler.sendMessage(resolvedPhone, message)
                    if (res.isSuccess) {
                        resultData["message"] = res.getOrNull() ?: "Message dispatched"
                    } else {
                        status = "failed"
                        errorMessage = res.exceptionOrNull()?.message ?: "Failed to send WhatsApp message"
                    }
                }

                "query_contacts" -> {
                    val query = dispatch.action_params["contact"] ?: ""
                    val matches = contactsHandler.searchContacts(query)
                    resultData["count"] = matches.size.toString()
                    resultData["message"] = if (matches.isNotEmpty()) {
                        "Found contact: ${matches[0].name} (${matches[0].phone})"
                    } else {
                        "No contacts found for '$query'"
                    }
                }

                "control_device_setting" -> {
                    val setting = dispatch.action_params["setting"] ?: "bluetooth"
                    val action = dispatch.action_params["action"] ?: "on"
                    if (setting.contains("bluetooth", ignoreCase = true)) {
                        val res = settingsHandler.setBluetooth(action.equals("on", ignoreCase = true))
                        resultData["message"] = res.getOrNull() ?: res.exceptionOrNull()?.message ?: "Bluetooth updated"
                    } else {
                        settingsHandler.openSettings()
                        resultData["message"] = "Opened phone settings"
                    }
                }

                "open_phone_app" -> {
                    settingsHandler.openSettings()
                    resultData["message"] = "Phone settings opened"
                }

                "set_alarm" -> {
                    val timeStr = dispatch.action_params["time"] ?: "07:00"
                    val parts = timeStr.replace(Regex("[^0-9:]"), "").split(":")
                    val hour = parts.getOrNull(0)?.toIntOrNull() ?: 7
                    val min = parts.getOrNull(1)?.toIntOrNull() ?: 0
                    val res = alarmHandler.setAlarm(hour, min, "AI Agent Alarm")
                    resultData["message"] = res.getOrNull() ?: "Alarm set"
                }

                "read_notifications" -> {
                    val notifs = NotificationMonitorService.getRecentNotifications()
                    resultData["count"] = notifs.size.toString()
                    resultData["message"] = if (notifs.isNotEmpty()) {
                        notifs.take(3).joinToString("; ")
                    } else {
                        "No unread notifications at this time."
                    }
                }

                "query_gallery" -> {
                    val photos = galleryHandler.getRecentPhotos(1)
                    resultData["count"] = photos.size.toString()
                    resultData["message"] = "Found ${photos.size} photos from yesterday in phone gallery"
                }

                "open_application" -> {
                    val app = dispatch.action_params["application"] ?: ""
                    if (app.contains("youtube", ignoreCase = true)) {
                        val q = dispatch.action_params["query"]
                        appLauncherHandler.launchYouTube(q)
                        resultData["message"] = "Opened YouTube on phone"
                    } else if (app.contains("spotify", ignoreCase = true)) {
                        appLauncherHandler.launchSpotify()
                        resultData["message"] = "Opened Spotify on phone"
                    } else {
                        settingsHandler.openSettings()
                        resultData["message"] = "Application opened"
                    }
                }

                else -> {
                    status = "failed"
                    errorMessage = "Unknown intent: ${dispatch.intent}"
                }
            }
        } catch (e: Exception) {
            status = "failed"
            errorMessage = e.message
        }

        val execTime = (System.currentTimeMillis() - startTime).toDouble()
        val taskResult = RemoteTaskResult(
            task_id = dispatch.task_id,
            device_id = dispatch.target_device_id,
            status = status,
            result_data = resultData,
            error = errorMessage,
            execution_time_ms = execTime
        )

        wsClient?.sendTaskResult(taskResult)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Cross-Platform AI Agent Background Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildForegroundNotification(statusText: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Cross-Platform AI Agent")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(statusText: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildForegroundNotification(statusText))
    }

    override fun onDestroy() {
        super.onDestroy()
        wsClient?.disconnect()
        scope.cancel()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
