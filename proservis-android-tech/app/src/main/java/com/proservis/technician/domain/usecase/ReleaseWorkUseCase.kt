package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import com.proservis.technician.domain.model.WorkSource
import javax.inject.Inject

class ReleaseWorkUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    suspend operator fun invoke(
        tenantId: String,
        id: String,
        source: WorkSource,
        uid: String,
    ) {
        if (source == WorkSource.SERVICE) {
            workRepository.releaseService(tenantId, id, uid)
        } else {
            workRepository.releaseMeterTask(tenantId, id, uid)
        }
    }
}

