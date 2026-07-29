package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import com.proservis.technician.domain.model.WorkItem
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class ObserveMyWorkUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    operator fun invoke(
        tenantId: String,
        uid: String,
        email: String,
        technicianName: String,
        globalTechnicianId: String,
        technicianProfileId: String,
        additionalTechnicianDocIds: Set<String> = emptySet(),
    ): Flow<List<WorkItem>> {
        return workRepository.observeMyServices(
            tenantId = tenantId,
            uid = uid,
            email = email,
            technicianName = technicianName,
            globalTechnicianId = globalTechnicianId,
            technicianProfileId = technicianProfileId,
            additionalTechnicianDocIds = additionalTechnicianDocIds,
        )
    }
}
