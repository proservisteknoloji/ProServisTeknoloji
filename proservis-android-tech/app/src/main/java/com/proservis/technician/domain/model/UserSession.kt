package com.proservis.technician.domain.model

data class UserSession(
    val tenantId: String,
    val uid: String,
    val email: String,
    val globalTechnicianId: String = "",
    val technicianName: String,
    val technicianProfileId: String = "",
)
