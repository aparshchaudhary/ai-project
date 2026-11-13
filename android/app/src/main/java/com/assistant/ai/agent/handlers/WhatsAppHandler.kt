package com.assistant.ai.agent.handlers

import android.content.Context
import android.content.Intent
import android.net.Uri
import java.net.URLEncoder

class WhatsAppHandler(private val context: Context) {

    fun sendMessage(phoneNumber: String, message: String): Result<String> {
        return try {
            val cleanNumber = phoneNumber.replace(Regex("[^0-9]"), "")
            val encodedMessage = URLEncoder.encode(message, "UTF-8")
            val url = "https://api.whatsapp.com/send?phone=$cleanNumber&text=$encodedMessage"

            val intent = Intent(Intent.ACTION_VIEW).apply {
                data = Uri.parse(url)
                setPackage("com.whatsapp")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            // Fallback to any browser if WhatsApp app package is not explicitly matched
            val packageManager = context.packageManager
            if (intent.resolveActivity(packageManager) != null) {
                context.startActivity(intent)
            } else {
                val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(browserIntent)
            }

            Result.success("WhatsApp message dispatched to $cleanNumber: '$message'")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun sendDocument(phoneNumber: String, fileUri: Uri, mimeType: String = "application/pdf"): Result<String> {
        return try {
            val cleanNumber = phoneNumber.replace(Regex("[^0-9]"), "")
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = mimeType
                putExtra(Intent.EXTRA_STREAM, fileUri)
                putExtra("jid", "$cleanNumber@s.whatsapp.net")
                setPackage("com.whatsapp")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            context.startActivity(intent)
            Result.success("Document shared with $cleanNumber via WhatsApp")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
