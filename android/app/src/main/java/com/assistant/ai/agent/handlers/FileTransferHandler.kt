package com.assistant.ai.agent.handlers

import android.content.Context
import android.os.Environment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream

class FileTransferHandler(private val context: Context, private val okHttpClient: OkHttpClient) {

    suspend fun downloadRelayFile(downloadUrl: String, filename: String): Result<File> = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder().url(downloadUrl).build()
            val response = okHttpClient.newCall(request).execute()

            if (!response.isSuccessful) {
                return@withContext Result.failure(Exception("Download failed with HTTP ${response.code}"))
            }

            val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
            val targetFile = File(downloadsDir, filename)

            response.body?.byteStream()?.use { input ->
                FileOutputStream(targetFile).use { output ->
                    input.copyTo(output)
                }
            } ?: return@withContext Result.failure(Exception("Empty response body"))

            Result.success(targetFile)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
