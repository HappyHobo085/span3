package com.example.studente_mobile_flutter_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import android.os.IBinder
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings
import android.util.Log
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import kotlin.math.abs

class NoodgevalForegroundService : Service() {
    companion object {
        const val EXTRA_MQTT_HOST = "mqtt_host"
        const val EXTRA_MQTT_PORT = "mqtt_port"
        const val EXTRA_KAMPUS_ID = "kampus_id"
        const val EXTRA_API_BASE_URL = "api_base_url"
        const val EXTRA_BEARER_TOKEN = "bearer_token"
        const val EXTRA_COMMAND = "command"
        const val EXTRA_NOODGEVAL_ID = "noodgeval_id"

        const val COMMAND_ACK = "ACK"

        private const val PREFS = "moon_noodgeval_service"
        private const val PREF_HOST = "host"
        private const val PREF_PORT = "port"
        private const val PREF_KAMPUS_ID = "kampus_id"
        private const val PREF_API_BASE_URL = "api_base_url"
        private const val PREF_BEARER_TOKEN = "bearer_token"
        private const val PREF_PENDING_ACK_ID = "pending_ack_id"

        private const val SERVICE_CHANNEL_ID = "moon_noodgeval_service_native"
        private const val ALERT_CHANNEL_ID = "moon_noodgeval_alarm_native_v2"
        private const val SERVICE_NOTIFICATION_ID = 7001
        private const val ALERT_NOTIFICATION_ID = 8001
        private const val TAG = "MOON-NoodgevalService"
    }

    private val mqttExecutor = Executors.newSingleThreadExecutor()
    private val apiExecutor = Executors.newSingleThreadExecutor()

    @Volatile
    private var mqttClient: MqttClient? = null

    @Volatile
    private var mqttHost: String = "127.0.0.1"

    @Volatile
    private var mqttPort: Int = 1883

    @Volatile
    private var kampusId: Int = 1

    @Volatile
    private var apiBaseUrl: String = ""

    @Volatile
    private var bearerToken: String = ""

    private var activeNoodgevalId: String? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startAsForeground("MOON luister vir kampus-noodgevalle.")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)

        mqttHost = intent?.getStringExtra(EXTRA_MQTT_HOST)
            ?.takeIf { it.isNotBlank() }
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

        apiBaseUrl = intent?.getStringExtra(EXTRA_API_BASE_URL)
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: prefs.getString(PREF_API_BASE_URL, "")
            ?: ""

        bearerToken = intent?.getStringExtra(EXTRA_BEARER_TOKEN)
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: prefs.getString(PREF_BEARER_TOKEN, "")
            ?: ""

        prefs.edit()
            .putString(PREF_HOST, mqttHost)
            .putInt(PREF_PORT, mqttPort)
            .putInt(PREF_KAMPUS_ID, kampusId)
            .putString(PREF_API_BASE_URL, apiBaseUrl)
            .putString(PREF_BEARER_TOKEN, bearerToken)
            .apply()

        if (intent?.getStringExtra(EXTRA_COMMAND) == COMMAND_ACK) {
            val id = intent.getStringExtra(EXTRA_NOODGEVAL_ID)
            acknowledgeLocally(id)
            return START_STICKY
        }

        connectMqttAsync()
        retryPendingAcknowledgementIfNeeded()
        return START_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        Log.i(TAG, "Flutter task verwyder; native noodgevaldiens bly aktief.")
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        stopAlarmAndVibration()

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
        apiExecutor.shutdownNow()
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
                        val rawPayload = message?.payload
                            ?.toString(Charsets.UTF_8)
                            ?.trim()
                            .orEmpty()

                        Log.i(TAG, "MQTT ONTVANG [$topic]: $rawPayload")
                        handleIncomingPayload(rawPayload)
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

    private fun handleIncomingPayload(rawPayload: String) {
        if (rawPayload.isBlank()) {
            return
        }

        // STAP 3B:
        // Net JSON met status=AKTIEF begin die alarm.
        // Plain-text MQTT bly 'n gewone stille toetsnotification.
        val json = try {
            JSONObject(rawPayload)
        } catch (_: Exception) {
            showTestNotification(rawPayload)
            return
        }

        val status = json.optString("status", "").trim().uppercase()
        val noodgevalId = json.opt("noodgeval_id")?.toString()
            ?.takeIf { it.isNotBlank() && it != "null" }
            ?: "local-${System.currentTimeMillis()}"

        when (status) {
            "AKTIEF", "ACTIVE" -> {
                val titel = json.optString("titel", "MOON NOODGEVAL")
                    .ifBlank { "MOON NOODGEVAL" }
                val boodskap = json.optString(
                    "boodskap",
                    "Noodgevalboodskap ontvang."
                ).ifBlank { "Noodgevalboodskap ontvang." }

                startEmergencyAlarm(
                    noodgevalId = noodgevalId,
                    titel = titel,
                    boodskap = boodskap,
                )
            }

            "GESTOP", "GESLUIT", "GEKANSELLEER", "STOP", "CANCELLED", "CLOSED" -> {
                stopAlarmAndVibration()
                activeNoodgevalId = null
                getSystemService(NotificationManager::class.java)
                    .cancel(ALERT_NOTIFICATION_ID)

                updateForegroundNotification(
                    "Geen aktiewe noodgeval • MQTT gekoppel"
                )
            }

            else -> {
                showTestNotification(rawPayload)
            }
        }
    }

    private fun startEmergencyAlarm(
        noodgevalId: String,
        titel: String,
        boodskap: String,
    ) {
        activeNoodgevalId = noodgevalId

        // Rapporteer outomaties dat hierdie toestel die noodgeval ontvang het.
        reportReceivedAsync(noodgevalId)

        // Klank word deur Android se alarm-notification channel beheer.
        // Vibrasie word ook direk geloop sodat dit aanhou totdat die gebruiker erken.
        startVibration()
        showEmergencyNotification(
            noodgevalId = noodgevalId,
            titel = titel,
            boodskap = boodskap,
        )

        updateForegroundNotification(
            "AKTIEWE NOODGEVAL • kennisname word vereis"
        )
    }

    @Suppress("DEPRECATION")
    private fun startVibration() {
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val manager = getSystemService(VibratorManager::class.java)
                manager.defaultVibrator
            } else {
                getSystemService(VIBRATOR_SERVICE) as Vibrator
            }

            if (!vibrator.hasVibrator()) {
                return
            }

            val pattern = longArrayOf(
                0,
                900, 450,
                900, 450,
                1400, 700
            )

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val amplitudes = intArrayOf(
                    0,
                    255, 0,
                    255, 0,
                    255, 0
                )
                vibrator.vibrate(
                    VibrationEffect.createWaveform(
                        pattern,
                        amplitudes,
                        0
                    )
                )
            } else {
                vibrator.vibrate(pattern, 0)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Kon nie vibrasie begin nie", e)
        }
    }

    @Suppress("DEPRECATION")
    private fun stopAlarmAndVibration() {
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val manager = getSystemService(VibratorManager::class.java)
                manager.defaultVibrator
            } else {
                getSystemService(VIBRATOR_SERVICE) as Vibrator
            }
            vibrator.cancel()
        } catch (e: Exception) {
            Log.e(TAG, "Kon nie vibrasie stop nie", e)
        }

        // FLAG_INSISTENT se alarmklank stop wanneer die notification gekanselleer word.
        getSystemService(NotificationManager::class.java)
            .cancel(ALERT_NOTIFICATION_ID)
    }

    private fun acknowledgeLocally(noodgevalId: String?) {
        if (
            noodgevalId != null &&
            activeNoodgevalId != null &&
            noodgevalId != activeNoodgevalId
        ) {
            Log.w(
                TAG,
                "ACK vir ou noodgeval geïgnoreer: $noodgevalId "
                    + "(aktief=$activeNoodgevalId)"
            )
            return
        }

        val idToAcknowledge = activeNoodgevalId ?: noodgevalId

        // Die gebruiker se plaaslike alarm stop onmiddellik wanneer hy/sy
        // "EK HET KENNIS GENEEM" druk. Die API-sinkronisering gebeur daarna.
        stopAlarmAndVibration()

        getSystemService(NotificationManager::class.java)
            .cancel(ALERT_NOTIFICATION_ID)

        Log.i(
            TAG,
            "EK HET KENNIS GENEEM: ${idToAcknowledge ?: "onbekend"}"
        )

        activeNoodgevalId = null

        if (idToAcknowledge.isNullOrBlank()) {
            updateForegroundNotification(
                "Kennis geneem plaaslik • geen noodgeval-ID beskikbaar nie"
            )
            return
        }

        getSharedPreferences(PREFS, MODE_PRIVATE)
            .edit()
            .putString(PREF_PENDING_ACK_ID, idToAcknowledge)
            .apply()

        updateForegroundNotification(
            "Kennis geneem • stoor bevestiging..."
        )

        reportAcknowledgementAsync(idToAcknowledge)
    }

    private fun reportReceivedAsync(noodgevalId: String) {
        apiExecutor.execute {
            postNoodgevalState(
                noodgevalId = noodgevalId,
                action = "ontvang",
                retryDelaysMs = longArrayOf(0L, 1500L, 4000L),
            )
        }
    }

    private fun reportAcknowledgementAsync(noodgevalId: String) {
        apiExecutor.execute {
            val success = postNoodgevalState(
                noodgevalId = noodgevalId,
                action = "kennisname",
                retryDelaysMs = longArrayOf(0L, 2000L, 5000L, 15000L),
            )

            if (success) {
                getSharedPreferences(PREFS, MODE_PRIVATE)
                    .edit()
                    .remove(PREF_PENDING_ACK_ID)
                    .apply()

                updateForegroundNotification(
                    "Kennis geneem en gestoor • MQTT gekoppel • kampus $kampusId"
                )
            } else {
                updateForegroundNotification(
                    "Kennis geneem plaaslik • sinkronisering wag"
                )
            }
        }
    }

    private fun retryPendingAcknowledgementIfNeeded() {
        val pendingId = getSharedPreferences(PREFS, MODE_PRIVATE)
            .getString(PREF_PENDING_ACK_ID, null)
            ?.takeIf { it.isNotBlank() }
            ?: return

        reportAcknowledgementAsync(pendingId)
    }

    private fun postNoodgevalState(
        noodgevalId: String,
        action: String,
        retryDelaysMs: LongArray,
    ): Boolean {
        val numericId = noodgevalId.toLongOrNull()
        if (numericId == null) {
            Log.w(
                TAG,
                "Kan /$action nie rapporteer nie: ongeldige noodgeval-ID $noodgevalId"
            )
            return false
        }

        val base = apiBaseUrl.trim().trimEnd('/')
        val token = bearerToken.trim()

        if (base.isBlank() || token.isBlank()) {
            Log.w(
                TAG,
                "Kan /$action nie rapporteer nie: API URL of JWT ontbreek."
            )
            return false
        }

        for (delayMs in retryDelaysMs) {
            if (delayMs > 0) {
                try {
                    Thread.sleep(delayMs)
                } catch (_: InterruptedException) {
                    Thread.currentThread().interrupt()
                    return false
                }
            }

            var connection: HttpURLConnection? = null
            try {
                val url = URL("$base/noodgeval/$numericId/$action")
                connection = (url.openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 10000
                    readTimeout = 10000
                    useCaches = false
                    doInput = true
                    setRequestProperty("Accept", "application/json")
                    setRequestProperty("Authorization", "Bearer $token")
                    setFixedLengthStreamingMode(0)
                    doOutput = true
                }

                connection.outputStream.use {
                    // Leë POST body; FastAPI endpoint verwag geen request model nie.
                }

                val code = connection.responseCode
                val body = try {
                    val stream = if (code in 200..299) {
                        connection.inputStream
                    } else {
                        connection.errorStream
                    }
                    stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                } catch (_: Exception) {
                    ""
                }

                if (code in 200..299) {
                    Log.i(
                        TAG,
                        "Noodgeval $noodgevalId /$action suksesvol gestoor."
                    )
                    return true
                }

                Log.w(
                    TAG,
                    "Noodgeval $noodgevalId /$action HTTP $code: ${body.take(300)}"
                )

                // 4xx is gewoonlik nie 'n tydelike netwerkfout nie.
                if (code in 400..499) {
                    return false
                }
            } catch (e: Exception) {
                Log.w(
                    TAG,
                    "Noodgeval $noodgevalId /$action kon nie sinkroniseer nie.",
                    e
                )
            } finally {
                connection?.disconnect()
            }
        }

        return false
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

    private fun showEmergencyNotification(
        noodgevalId: String,
        titel: String,
        boodskap: String,
    ) {
        val manager = getSystemService(NotificationManager::class.java)

        val launchIntent = packageManager.getLaunchIntentForPackage(packageName)
        val contentPendingIntent = if (launchIntent != null) {
            PendingIntent.getActivity(
                this,
                10,
                launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        } else {
            null
        }

        val ackIntent = Intent(
            this,
            NoodgevalActionReceiver::class.java
        ).apply {
            action = NoodgevalActionReceiver.ACTION_ACK
            putExtra(EXTRA_NOODGEVAL_ID, noodgevalId)
        }

        val ackPendingIntent = PendingIntent.getBroadcast(
            this,
            11,
            ackIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, ALERT_CHANNEL_ID)
        } else {
            Notification.Builder(this)
                .setPriority(Notification.PRIORITY_MAX)
        }

        builder
            .setSmallIcon(R.drawable.ic_stat_moon)
            .setContentTitle("🚨 $titel")
            .setContentText(boodskap)
            .setStyle(Notification.BigTextStyle().bigText(boodskap))
            .setOngoing(true)
            .setAutoCancel(false)
            .setCategory(Notification.CATEGORY_ALARM)
            .addAction(
                R.drawable.ic_stat_moon,
                "EK HET KENNIS GENEEM",
                ackPendingIntent
            )

        if (contentPendingIntent != null) {
            builder.setContentIntent(contentPendingIntent)
        }

        val emergencyNotification = builder.build().apply {
            // Android herhaal die channel se alarmklank totdat hierdie
            // notification gekanselleer word.
            flags = flags or Notification.FLAG_INSISTENT
            flags = flags or Notification.FLAG_NO_CLEAR
        }

        manager.notify(
            ALERT_NOTIFICATION_ID,
            emergencyNotification
        )
    }

    private fun showTestNotification(payload: String) {
        val manager = getSystemService(NotificationManager::class.java)

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, SERVICE_CHANNEL_ID)
        } else {
            Notification.Builder(this)
                .setPriority(Notification.PRIORITY_DEFAULT)
        }

        builder
            .setSmallIcon(R.drawable.ic_stat_moon)
            .setContentTitle("MOON MQTT TOETS ONTVANG")
            .setContentText(payload)
            .setStyle(Notification.BigTextStyle().bigText(payload))
            .setAutoCancel(true)

        val id = 8200 + abs(
            (System.currentTimeMillis() % 100000).toInt()
        )

        manager.notify(id, builder.build())
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

        // NUWE channel ID (_v2) is doelbewus belangrik:
        // Android cache notification-channel klank/vibrasie instellings.
        // Die vorige channel was stil geskep, en daardie instellings kan nie
        // betroubaar programmaties verander word nadat die channel bestaan nie.
        val alarmUri =
            RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
                ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
                ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

        val alarmAudioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ALARM)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()

        val alertChannel = NotificationChannel(
            ALERT_CHANNEL_ID,
            "MOON Noodgeval Alarm",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Harde MOON kampus-noodgevalle."
            setSound(alarmUri, alarmAudioAttributes)
            enableVibration(true)
            vibrationPattern = longArrayOf(
                0,
                900, 450,
                900, 450,
                1400, 700
            )
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        }

        manager.createNotificationChannel(serviceChannel)
        manager.createNotificationChannel(alertChannel)
    }
}
