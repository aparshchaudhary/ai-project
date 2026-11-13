package com.assistant.ai.agent.models

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class RemoteTaskDispatch(
    val task_id: String,
    val intent: String,
    val target_device_id: String,
    val target_device_type: String,
    val action_params: Map<String, String> = emptyMap(),
    val timeout_seconds: Double = 30.0
)

@Serializable
data class RemoteTaskResult(
    val type: String = "task_result",
    val task_id: String,
    val device_id: String,
    val status: String, // "completed" | "failed"
    val result_data: Map<String, String> = emptyMap(),
    val error: String? = null,
    val execution_time_ms: Double? = null
)

@Serializable
data class DeviceRegistration(
    val device_id: String,
    val device_name: String,
    val device_type: String = "android",
    val pairing_code: String? = null,
    val capabilities: List<String> = emptyList(),
    val system_info: Map<String, String> = emptyMap()
)

@Serializable
data class DeviceHeartbeat(
    val type: String = "heartbeat",
    val device_id: String,
    val battery_pct: Int? = null,
    val is_charging: Boolean? = null,
    val ram_usage_pct: Double? = null,
    val storage_free_gb: Double? = null,
    val status: String = "online"
)

data class ContactInfo(
    val id: String,
    val name: String,
    val phone: String,
    val relationship: String? = null
)

data class PhotoItem(
    val id: Long,
    val displayName: String,
    val uriString: String,
    val dateTaken: Long
)
