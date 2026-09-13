package com.example.studente_mobile_flutter_app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build

class NoodgevalActionReceiver : BroadcastReceiver() {
    companion object {
        const val ACTION_ACK =
            "com.example.studente_mobile_flutter_app.ACTION_NOODGEVAL_ACK"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_ACK) {
            return
        }

        val serviceIntent = Intent(
            context,
            NoodgevalForegroundService::class.java
        ).apply {
            putExtra(
                NoodgevalForegroundService.EXTRA_COMMAND,
                NoodgevalForegroundService.COMMAND_ACK
            )
            putExtra(
                NoodgevalForegroundService.EXTRA_NOODGEVAL_ID,
                intent.getStringExtra(
                    NoodgevalForegroundService.EXTRA_NOODGEVAL_ID
                )
            )
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent)
        } else {
            context.startService(serviceIntent)
        }
    }
}
