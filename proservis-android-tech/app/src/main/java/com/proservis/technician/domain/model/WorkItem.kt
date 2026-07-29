package com.proservis.technician.domain.model

enum class WorkSource {
    SERVICE,
    METER_TASK,
}

data class WorkItem(
    val id: String,
    val source: WorkSource,
    val title: String,
    val serialNumber: String?,
    val jobType: String? = null,
    val customerId: String? = null,
    val deviceId: String? = null,
    val customerName: String,
    val problemDescription: String?,
    val locationText: String,
    val contactPhone: String?,
    val status: String,
    val isColorDevice: Boolean = false,
    val lastBwCounter: Int? = null,
    val lastColorCounter: Int? = null,
    val technicianId: String?,
    val technicianName: String?,
    val priority: String?,
    val createdAtEpochMs: Long?,
    val selectedMeterDeviceIds: List<String>? = null,
)
