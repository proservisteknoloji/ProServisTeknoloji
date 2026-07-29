package com.proservis.technician.ui.screen.work

import com.proservis.technician.domain.model.WorkItem
import com.proservis.technician.domain.model.WorkSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WorkTabsScreenLabelTest {
    @Test
    fun jobTypeLabel_mapsMeterCollectionToMeterTaskLabel() {
        val kotlinClass = Class.forName("com.proservis.technician.ui.screen.work.WorkTabsScreenKt")
        val method = kotlinClass.getDeclaredMethod("jobTypeLabel", String::class.java)
        method.isAccessible = true

        val label = method.invoke(null, "meter_collection") as String

        assertEquals("Sayaç Okuma", label)
    }

    @Test
    fun isMeterLikeRow_detectsMeterJobTypeLabels() {
        val kotlinClass = Class.forName("com.proservis.technician.ui.screen.work.WorkTabsScreenKt")
        val method = kotlinClass.getDeclaredMethod("isMeterLikeRow", WorkItem::class.java)
        method.isAccessible = true

        assertTrue(method.invoke(null, sampleWorkItem("Saya\u00e7 Okuma")) as Boolean)
        assertTrue(method.invoke(null, sampleWorkItem("sayac toplama")) as Boolean)
    }

    private fun sampleWorkItem(jobType: String): WorkItem =
        WorkItem(
            id = "service-1",
            source = WorkSource.SERVICE,
            title = "Servis Kaydi",
            serialNumber = null,
            jobType = jobType,
            customerId = "customer-1",
            deviceId = null,
            customerName = "Musteri",
            problemDescription = null,
            locationText = "",
            contactPhone = null,
            status = "Assigned",
            technicianId = "tech-1",
            technicianName = "Teknisyen",
            priority = null,
            createdAtEpochMs = null,
        )
}
