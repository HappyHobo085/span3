package com.example.studente_mobile_flutter_app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL = "moon/noodgeval_service"
        private const val NOTIFICATION_PERMISSION_REQUEST = 9101
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            CHANNEL
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "start" -> {
                    val host = call.argument<String>("host") ?: "127.0.0.1"
                    val port = call.argument<Int>("port") ?: 1883
                    val kampusId = call.argument<Int>("kampusId") ?: 1
                    val apiBaseUrl =
                        call.argument<String>("apiBaseUrl")?.trim().orEmpty()
                    val bearerToken =
                        call.argument<String>("bearerToken")?.trim().orEmpty()

                    requestNotificationPermissionIfNeeded()

                    val serviceIntent = Intent(
                        this,
                        NoodgevalForegroundService::class.java
                    ).apply {
                        putExtra(NoodgevalForegroundService.EXTRA_MQTT_HOST, host)
                        putExtra(NoodgevalForegroundService.EXTRA_MQTT_PORT, port)
                        putExtra(NoodgevalForegroundService.EXTRA_KAMPUS_ID, kampusId)
                        putExtra(
                            NoodgevalForegroundService.EXTRA_API_BASE_URL,
                            apiBaseUrl
                        )
                        putExtra(
                            NoodgevalForegroundService.EXTRA_BEARER_TOKEN,
                            bearerToken
                        )
                    }

                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(serviceIntent)
                    } else {
                        startService(serviceIntent)
                    }

                    result.success(true)
                }

                "stop" -> {
                    stopService(Intent(this, NoodgevalForegroundService::class.java))
                    result.success(true)
                }

                else -> result.notImplemented()
            }
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                NOTIFICATION_PERMISSION_REQUEST
            )
        }
    }
}
