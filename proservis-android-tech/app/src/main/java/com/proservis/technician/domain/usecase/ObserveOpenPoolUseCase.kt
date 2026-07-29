package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import com.proservis.technician.domain.model.WorkItem
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class ObserveOpenPoolUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    operator fun invoke(tenantId: String): Flow<List<WorkItem>> {
        return workRepository.observeOpenPoolServices(tenantId)
    }
}

