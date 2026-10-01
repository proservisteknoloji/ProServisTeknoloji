package com.proservis.technician.domain.model

data class ServiceCompletionData(
    val status: String,
    val technicianReport: String,
    val bwCounter: Int?,
    val colorCounter: Int?,
    val deliveryRecipientName: String? = null,
    val meterReadings: List<MeterReadingInput> = emptyList(),
)

data class MeterReadingInput(
    val deviceId: String,
    val bwCounter: Int,
    val colorCounter: Int?,
)
