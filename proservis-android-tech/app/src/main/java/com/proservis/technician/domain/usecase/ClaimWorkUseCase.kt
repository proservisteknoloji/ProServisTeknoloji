package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import com.proservis.technician.domain.model.WorkSource
import javax.inject.Inject

class ClaimWorkUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    suspend operator fun invoke(
        tenantId: String,
        id: String,
        source: WorkSource,
        uid: String,
        technicianName: String,
    ) {
        if (source == WorkSource.SERVICE) {
            workRepository.claimService(tenantId, id, uid, technicianName)
        } else {
            workRepository.claimMeterTask(tenantId, id, uid, technicianName)
        }
    }
}

