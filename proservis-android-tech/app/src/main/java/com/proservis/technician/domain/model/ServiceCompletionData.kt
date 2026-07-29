package com.proservis.technician.domain.model

data class ServiceCompletionData(
    val status: String,
    val technicianReport: String,
    val bwCounter: Int?,
    val colorCounter: Int?,
    val deliveryRecipientName: String? = null,
)
