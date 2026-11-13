package com.assistant.ai.agent.handlers

import android.bluetooth.BluetoothAdapter
import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.os.Build
import android.provider.Settings

class SettingsHandler(private val context: Context) {

    fun setBluetooth(enable: Boolean): Result<String> {
        return try {
            val adapter = BluetoothAdapter.getDefaultAdapter()
                ?: return Result.failure(Exception("Bluetooth adapter not available on this device"))

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                // On Android 13+, open Bluetooth settings intent for user confirmation
                val intent = Intent(Settings.ACTION_BLUETOOTH_SETTINGS).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                Result.success("Opened Bluetooth settings to turn ${if (enable) "ON" else "OFF"}")
            } else {
                @Suppress("DEPRECATION")
                val ok = if (enable) adapter.enable() else adapter.disable()
                if (ok) Result.success("Bluetooth turned ${if (enable) "ON" else "OFF"}")
                else Result.failure(Exception("Failed to change Bluetooth state"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun openSettings(): Result<String> {
        return try {
            val intent = Intent(Settings.ACTION_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            Result.success("Opened phone settings")
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
