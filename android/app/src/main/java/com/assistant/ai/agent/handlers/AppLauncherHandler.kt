package com.assistant.ai.agent.handlers

import android.content.Context
import android.content.Intent
import android.net.Uri
import java.net.URLEncoder

class AppLauncherHandler(private val context: Context) {

    fun launchYouTube(query: String? = null): Result<String> {
        return try {
            val url = if (!query.isNullOrBlank()) {
                "https://www.youtube.com/results?search_query=" + URLEncoder.encode(query, "UTF-8")
            } else {
                "https://www.youtube.com"
            }
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            Result.success("YouTube opened for '${query ?: "home"}'")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun launchSpotify(): Result<String> {
        return try {
            val launchIntent = context.packageManager.getLaunchIntentForPackage("com.spotify.music")
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(launchIntent)
                Result.success("Spotify application launched")
            } else {
                val webIntent = Intent(Intent.ACTION_VIEW, Uri.parse("https://open.spotify.com")).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(webIntent)
                Result.success("Spotify web player opened")
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
