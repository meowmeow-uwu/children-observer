package com.observer.childrenobserver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.widget.Toast

class NotificationActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        when (intent?.action) {
            "ACTION_ACTIVATE_ALARM" -> {
                // Logic thực tế để gửi lệnh bật loa đến camera qua backend hoặc MQTT
                Toast.makeText(context, "Đang kích hoạt loa báo động trên camera...", Toast.LENGTH_LONG).show()
            }
        }
    }
}
