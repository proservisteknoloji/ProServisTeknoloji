package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import com.proservis.technician.domain.model.ServiceCompletionData
import javax.inject.Inject

class CompleteServiceUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    suspend operator fun invoke(
        tenantId: String,
        serviceId: String,
        uid: String,
        data: ServiceCompletionData,
    ) {
        workRepository.completeService(tenantId, serviceId, uid, data)
    }
}

