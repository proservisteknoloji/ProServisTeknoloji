package com.proservis.technician

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Application
import android.content.pm.ApplicationInfo
import android.os.Build
import com.google.firebase.FirebaseApp
import com.google.firebase.appcheck.FirebaseAppCheck
import com.google.firebase.appcheck.AppCheckProviderFactory
import com.google.firebase.appcheck.playintegrity.PlayIntegrityAppCheckProviderFactory
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.FirebaseFirestoreSettings
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class ProservisTechApp : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseApp.initializeApp(this)
        val appCheck = FirebaseAppCheck.getInstance()
        val isDebuggable = (applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        if (isDebuggable) {
            // Gelistirme/test: debug token ile calisir.
            val debugFactory = runCatching {
                val clazz = Class.forName("com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory")
                val getInstance = clazz.getMethod("getInstance")
                getInstance.invoke(null) as AppCheckProviderFactory
            }.getOrNull()
            if (debugFactory != null) {
                appCheck.installAppCheckProviderFactory(debugFactory)
            } else {
                // Debug factory bulunamazsa yine de calismasi icin release provider'a duser.
                appCheck.installAppCheckProviderFactory(PlayIntegrityAppCheckProviderFactory.getInstance())
            }
        } else {
            // Canli: tum teknisyenler icin token yerine Play Integrity kullanilir.
            appCheck.installAppCheckProviderFactory(PlayIntegrityAppCheckProviderFactory.getInstance())
        }
        appCheck.setTokenAutoRefreshEnabled(true)

        ensureNotificationChannel()
        val db = FirebaseFirestore.getInstance()
        db.firestoreSettings = FirebaseFirestoreSettings.Builder()
            .setPersistenceEnabled(true)
            .build()
    }

    private fun ensureNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Proservis Is Bildirimleri",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Yeni atanan servis ve gorev bildirimleri"
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager?.createNotificationChannel(channel)
    }

    companion object {
        const val CHANNEL_ID = "proservis_jobs"
    }
}
