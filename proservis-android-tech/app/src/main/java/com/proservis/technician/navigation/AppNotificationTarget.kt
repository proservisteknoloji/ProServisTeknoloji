package com.proservis.technician.navigation

import android.content.Intent
import com.proservis.technician.MainActivity

data class AppNotificationTarget(
    val type: String,
    val tenantId: String,
    val serviceId: String,
    val taskId: String,
) {
    companion object {
        fun fromIntent(intent: Intent?): AppNotificationTarget? {
            if (intent == null) return null

            val type = (intent.getStringExtra(MainActivity.EXTRA_NOTIFICATION_TYPE) ?: "").trim()
            val tenantId = (intent.getStringExtra(MainActivity.EXTRA_NOTIFICATION_TENANT_ID) ?: "").trim()
            val serviceId = (intent.getStringExtra(MainActivity.EXTRA_NOTIFICATION_SERVICE_ID) ?: "").trim()
            val taskId = (intent.getStringExtra(MainActivity.EXTRA_NOTIFICATION_TASK_ID) ?: "").trim()

            // System-delivered notification taps may keep payload in extras with variant keys.
            val extras = intent.extras
            fun pick(vararg keys: String): String {
                if (extras == null) return ""
                for (k in keys) {
                    val v = (extras.getString(k) ?: "").trim()
                    if (v.isNotBlank()) return v
                }
                return ""
            }
            val extraType = pick("type", "TYPE", "notification_type", "NOTIFICATION_TYPE")
            val extraTenantId = pick("tenantId", "tenant_id", "TENANT_ID")
            val extraServiceId = pick("serviceId", "service_id", "SERVICE_ID")
            val extraTaskId = pick("taskId", "task_id", "TASK_ID")

            val resolvedType = listOf(type, extraType).firstOrNull { it.isNotBlank() } ?: ""
            val resolvedTenantId = listOf(tenantId, extraTenantId).firstOrNull { it.isNotBlank() } ?: ""
            val resolvedServiceId = listOf(serviceId, extraServiceId).firstOrNull { it.isNotBlank() } ?: ""
            val resolvedTaskId = listOf(taskId, extraTaskId).firstOrNull { it.isNotBlank() } ?: ""

            if (
                resolvedType.isBlank() &&
                resolvedTenantId.isBlank() &&
                resolvedServiceId.isBlank() &&
                resolvedTaskId.isBlank()
            ) {
                return null
            }

            return AppNotificationTarget(
                type = resolvedType,
                tenantId = resolvedTenantId,
                serviceId = resolvedServiceId,
                taskId = resolvedTaskId,
            )
        }
    }
}
