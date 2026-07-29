package com.proservis.technician.navigation

object AppRoute {
    const val Login = "login"
    const val WorkTabs = "work_tabs"
    const val SerialVerify = "serial_verify/{serviceId}"
    const val CompleteService = "complete_service/{serviceId}"

    fun serialVerify(serviceId: String) = "serial_verify/$serviceId"
    fun completeService(serviceId: String) = "complete_service/$serviceId"
}
