package com.observer.childrenobserver

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.observer.childrenobserver.ui.theme.EmergencyRed
import androidx.compose.ui.graphics.toArgb

class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        remoteMessage.notification?.let {
            sendNotification(it.title, it.body, remoteMessage.data)
        }
    }

    private fun sendNotification(title: String?, messageBody: String?, data: Map<String, String>) {
        val channelId = "alert_channel"
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Cảnh báo an ninh",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Thông báo khi phát hiện nguy hiểm"
                enableLights(true)
                lightColor = android.graphics.Color.RED
            }
            notificationManager.createNotificationChannel(channel)
        }

        // Action: Xem trực tiếp
        val liveIntent = Intent(this, MainActivity::class.java).apply {
            putExtra("action", "view_live_stream")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val livePendingIntent = PendingIntent.getActivity(this, 0, liveIntent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

        // Action: Bật loa (Broadcast)
        val alarmIntent = Intent(this, NotificationActionReceiver::class.java).apply {
            action = "ACTION_ACTIVATE_ALARM"
        }
        val alarmPendingIntent = PendingIntent.getBroadcast(this, 1, alarmIntent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

        val notificationBuilder = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title ?: "ChildrenObserver Alert")
            .setContentText(messageBody)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .addAction(android.R.drawable.ic_menu_view, "Xem trực tiếp", livePendingIntent)
            .addAction(android.R.drawable.ic_lock_idle_alarm, "Bật báo động", alarmPendingIntent)

        // Snapshot giả lập (Sử dụng ảnh mẫu nếu có)
        // val bitmap = BitmapFactory.decodeResource(resources, R.drawable.placeholder_alert_1)
        // notificationBuilder.setLargeIcon(bitmap).setStyle(NotificationCompat.BigPictureStyle().bigPicture(bitmap))

        notificationManager.notify(System.currentTimeMillis().toInt(), notificationBuilder.build())
    }
}
