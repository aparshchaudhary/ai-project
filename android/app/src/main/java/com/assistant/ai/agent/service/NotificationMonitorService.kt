package com.assistant.ai.agent.service

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class NotificationMonitorService : NotificationListenerService() {

    companion object {
        private val recentNotifications = mutableListOf<String>()

        fun getRecentNotifications(): List<String> {
            synchronized(recentNotifications) {
                return recentNotifications.toList()
            }
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        val packageName = sbn?.packageName ?: return
        val extras = sbn.notification?.extras ?: return
        val title = extras.getString("android.title") ?: ""
        val text = extras.getCharSequence("android.text")?.toString() ?: ""

        if (title.isNotBlank() || text.isNotBlank()) {
            val item = "$title: $text (from $packageName)"
            synchronized(recentNotifications) {
                recentNotifications.add(0, item)
                if (recentNotifications.size > 20) {
                    recentNotifications.removeAt(recentNotifications.size - 1)
                }
            }
            Log.d("NotificationMonitor", "Notification received: $item")
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // Notification dismissed
    }
}
