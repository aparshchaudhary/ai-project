package com.assistant.ai.agent.handlers

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.ContextCompat

class CallingHandler(private val context: Context) {

    fun makeCall(phoneNumber: String, directCall: Boolean = true): Result<String> {
        return try {
            val cleanNumber = phoneNumber.replace(Regex("[^0-9+]"), "")
            val uri = Uri.parse("tel:$cleanNumber")

            val intent = if (directCall && ContextCompat.checkSelfPermission(
                    context,
                    android.Manifest.permission.CALL_PHONE
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                Intent(Intent.ACTION_CALL, uri)
            } else {
                Intent(Intent.ACTION_DIAL, uri)
            }

            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)

            val mode = if (intent.action == Intent.ACTION_CALL) "Direct call" else "Dialer preview"
            Result.success("$mode initiated for $cleanNumber")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
