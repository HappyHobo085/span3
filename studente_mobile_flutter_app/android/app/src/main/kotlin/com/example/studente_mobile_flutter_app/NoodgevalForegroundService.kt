package com.example.studente_mobile_flutter_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.util.Log
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import java.util.concurrent.Executors
import kotlin.math.abs

class NoodgevalForegroundService : Service() {
    companion object {
        const val EXTRA_MQTT_HOST = "mqtt_host"
        const val EXTRA_MQTT_PORT = "mqtt_port"
        const val EXTRA_KAMPUS_ID = "kampus_id"

        private const val PREFS = "moon_noodgeval_service"
        private const val PREF_HOST = "host"
        private const val PREF_PORT = "port"
        private const val PREF_KAMPUS_ID = "kampus_id"

        private const val SERVICE_CHANNEL_ID = "moon_noodgeval_service_native"
        private const val ALERT_CHANNEL_ID = "moon_noodgeval_alerts_native"
        private const val SERVICE_NOTIFICATION_ID = 7001
        private const val TAG = "MOON-NoodgevalService"
    }

    private val mqttExecutor = Executors.newSingleThreadExecutor()

    @Volatile
    private var mqttClient: MqttClient? = null

    @Volatile
    private var mqttHost: String = "127.0.0.1"

    @Volatile
    private var mqttPort: Int = 1883

    @Volatile
    private var kampusId: Int = 1

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startAsForeground("MOON luister vir kampus-noodgevalle.")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)

        mqttHost = intent?.getStringExtra(EXTRA_MQTT_HOST)
            ?: prefs.getString(PREF_HOST, "127.0.0.1")
            ?: "127.0.0.1"

        mqttPort = if (intent?.hasExtra(EXTRA_MQTT_PORT) == true) {
            intent.getIntExtra(EXTRA_MQTT_PORT, 1883)
        } else {
            prefs.getInt(PREF_PORT, 1883)
        }

        kampusId = if (intent?.hasExtra(EXTRA_KAMPUS_ID) == true) {
            intent.getIntExtra(EXTRA_KAMPUS_ID, 1)
        } else {
            prefs.getInt(PREF_KAMPUS_ID, 1)
        }

        prefs.edit()
            .putString(PREF_HOST, mqttHost)
            .putInt(PREF_PORT, mqttPort)
            .putInt(PREF_KAMPUS_ID, kampusId)
            .apply()

        connectMqttAsync()

        // Android mag die proses later herstel indien dit om geheue-redes gestop word.
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Belangrik: moenie die service stop wanneer die gebruiker die Flutter task
        // uit Recent Apps weg-swipe nie.
        Log.i(TAG, "Flutter task verwyder; native noodgevaldiens bly aktief.")
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        try {
            mqttClient?.let { client ->
                if (client.isConnected) {
                    client.disconnectForcibly(1000, 1000)
                }
                client.close()
            }
        } catch (_: Exception) {
        }

        mqttClient = null
        mqttExecutor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun connectMqttAsync() {
        mqttExecutor.execute {
            try {
                val existing = mqttClient
                if (existing?.isConnected == true) {
                    val expectedUri = brokerUri()
                    if (existing.serverURI == expectedUri) {
                        subscribe(existing)
                        return@execute
                    }
                }

                try {
                    existing?.disconnectForcibly(500, 500)
                    existing?.close()
                } catch (_: Exception) {
                }

                val androidId = Settings.Secure.getString(
                    contentResolver,
                    Settings.Secure.ANDROID_ID
                ) ?: "unknown"

                val safeId = androidId.replace(Regex("[^A-Za-z0-9_-]"), "")
                val clientId = "moon_${safeId}_$kampusId"

                val client = MqttClient(
                    brokerUri(),
                    clientId,
                    MemoryPersistence()
                )

                client.setCallback(object : MqttCallbackExtended {
                    override fun connectComplete(reconnect: Boolean, serverURI: String?) {
                        Log.i(
                            TAG,
                            "MQTT connected reconnect=$reconnect server=$serverURI"
                        )
                        subscribe(client)
                        updateForegroundNotification(
                            "MQTT gekoppel • kampus $kampusId"
                        )
                    }

                    override fun connectionLost(cause: Throwable?) {
                        Log.w(TAG, "MQTT verbinding verloor", cause)
                        updateForegroundNotification(
                            "MQTT verbinding verloor • probeer weer koppel"
                        )
                    }

                    override fun messageArrived(topic: String?, message: MqttMessage?) {
                        val payload = message?.payload
                            ?.toString(Charsets.UTF_8)
                            ?.takeIf { it.isNotBlank() }
                            ?: "Noodgevalboodskap ontvang"

                        Log.i(TAG, "MQTT ONTVANG [$topic]: $payload")
                        showAlertNotification(payload)
                    }

                    override fun deliveryComplete(token: IMqttDeliveryToken?) {
                        // Hierdie service publish nie tans boodskappe nie.
                    }
                })

                val options = MqttConnectOptions().apply {
                    isAutomaticReconnect = true
                    isCleanSession = false
                    connectionTimeout = 10
                    keepAliveInterval = 20
                }

                mqttClient = client
                client.connect(options)
                subscribe(client)
            } catch (e: Exception) {
                Log.e(TAG, "Kon nie aan MQTT koppel nie", e)
                updateForegroundNotification(
                    "MQTT nie gekoppel nie • wag vir herverbinding"
                )
            }
        }
    }

    private fun subscribe(client: MqttClient) {
        try {
            val topic = "moon/noodgeval/kampus/$kampusId"
            if (client.isConnected) {
                client.subscribe(topic, 1)
                Log.i(TAG, "Subscribed: $topic")
            }
        } catch (e: Exception) {
            Log.e(TAG, "MQTT subscribe fout", e)
        }
    }

    private fun brokerUri(): String {
        val cleanHost = mqttHost
            .removePrefix("tcp://")
            .removeSuffix("/")
        return "tcp://$cleanHost:$mqttPort"
    }

    private fun startAsForeground(text: String) {
        val notification = buildServiceNotification(text)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                SERVICE_NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MANIFEST
            )
        } else {
            startForeground(SERVICE_NOTIFICATION_ID, notification)
        }
    }

    private fun updateForegroundNotification(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(
            SERVICE_NOTIFICATION_ID,
            buildServiceNotification(text)
        )
    }

    private fun buildServiceNotification(text: String): Notification {
        val launchIntent = packageManager.getLaunchIntentForPackage(packageName)

        val pendingIntent = if (launchIntent != null) {
            PendingIntent.getActivity(
                this,
                0,
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        } else {
            null
        }

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, SERVICE_CHANNEL_ID)
        } else {
            Notification.Builder(this)
        }

        builder
            .setSmallIcon(R.drawable.ic_stat_moon)
            .setContentTitle("MOON Noodgevaldiens aktief")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_SERVICE)

        if (pendingIntent != null) {
            builder.setContentIntent(pendingIntent)
        }

        return builder.build()
    }

    private fun showAlertNotification(payload: String) {
        val manager = getSystemService(NotificationManager::class.java)
        val launchIntent = packageManager.getLaunchIntentForPackage(packageName)

        val pendingIntent = if (launchIntent != null) {
            PendingIntent.getActivity(
                this,
                1,
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        } else {
            null
        }

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, ALERT_CHANNEL_ID)
        } else {
            Notification.Builder(this)
                .setPriority(Notification.PRIORITY_HIGH)
        }

        builder
            .setSmallIcon(R.drawable.ic_stat_moon)
            .setContentTitle("🚨 MOON MQTT TOETS ONTVANG")
            .setContentText(payload)
            .setStyle(Notification.BigTextStyle().bigText(payload))
            .setAutoCancel(true)
            .setCategory(Notification.CATEGORY_ALARM)

        if (pendingIntent != null) {
            builder.setContentIntent(pendingIntent)
        }

        val notificationId = 8000 + abs(
            (System.currentTimeMillis() % 100000).toInt()
        )

        manager.notify(notificationId, builder.build())
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }

        val manager = getSystemService(NotificationManager::class.java)

        val serviceChannel = NotificationChannel(
            SERVICE_CHANNEL_ID,
            "MOON Noodgevaldiens",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Hou MOON se noodgeval-MQTT diens aktief."
            setSound(null, null)
            enableVibration(false)
        }

        val alertChannel = NotificationChannel(
            ALERT_CHANNEL_ID,
            "MOON Noodgeval Waarskuwings",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Noodgeval-toetsboodskappe vanaf MOON."
            setSound(null, null)
            enableVibration(false)
        }

        manager.createNotificationChannel(serviceChannel)
        manager.createNotificationChannel(alertChannel)
    }
}
