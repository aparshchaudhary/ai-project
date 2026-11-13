package com.assistant.ai.agent.network

import android.util.Log
import com.assistant.ai.agent.models.DeviceHeartbeat
import com.assistant.ai.agent.models.RemoteTaskDispatch
import com.assistant.ai.agent.models.RemoteTaskResult
import kotlinx.coroutines.*
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.*
import java.util.concurrent.TimeUnit

class AgentWebSocketClient(
    private val serverUrl: String,
    private val deviceId: String,
    private val onTaskReceived: suspend (RemoteTaskDispatch) -> Unit,
    private val onConnectionChanged: (Boolean) -> Unit
) {
    private val tag = "AgentWebSocketClient"
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val json = Json { ignoreUnknownKeys = true }
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var isRunning = true

    fun connect() {
        val wsUrl = "$serverUrl/ws/device/android/$deviceId"
            .replace("https://", "wss://")
            .replace("http://", "ws://")

        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(tag, "Connected to AI Agent Backend: $wsUrl")
                onConnectionChanged(true)
                startHeartbeat()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                scope.launch {
                    try {
                        if (text.contains("remote_task_dispatch")) {
                            val element = json.parseToJsonElement(text)
                            val dispatchJson = element.toString()
                            // Simple parser helper
                            val dispatch = json.decodeFromString<RemoteTaskDispatchWrapper>(text).dispatch
                            onTaskReceived(dispatch)
                        }
                    } catch (e: Exception) {
                        Log.e(tag, "Error parsing incoming task: ${e.message}", e)
                    }
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                onConnectionChanged(false)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w(tag, "WebSocket failure: ${t.message}. Reconnecting in 5s...")
                onConnectionChanged(false)
                scheduleReconnect()
            }
        })
    }

    fun sendTaskResult(result: RemoteTaskResult) {
        scope.launch {
            try {
                val jsonPayload = json.encodeToString(result)
                webSocket?.send(jsonPayload)
                Log.i(tag, "Sent task result for ${result.task_id}: ${result.status}")
            } catch (e: Exception) {
                Log.e(tag, "Error sending task result: ${e.message}")
            }
        }
    }

    private fun startHeartbeat() {
        scope.launch {
            while (isActive && isRunning) {
                try {
                    val hb = DeviceHeartbeat(
                        device_id = deviceId,
                        battery_pct = 85,
                        is_charging = true,
                        ram_usage_pct = 45.0,
                        storage_free_gb = 64.2,
                        status = "online"
                    )
                    webSocket?.send(json.encodeToString(hb))
                } catch (e: Exception) {
                    Log.w(tag, "Heartbeat failed: ${e.message}")
                }
                delay(30000)
            }
        }
    }

    private fun scheduleReconnect() {
        if (!isRunning) return
        scope.launch {
            delay(5000)
            connect()
        }
    }

    fun disconnect() {
        isRunning = false
        webSocket?.close(1000, "Normal closure")
        scope.cancel()
    }
}

@kotlinx.serialization.Serializable
data class RemoteTaskDispatchWrapper(
    val type: String,
    val dispatch: RemoteTaskDispatch
)
