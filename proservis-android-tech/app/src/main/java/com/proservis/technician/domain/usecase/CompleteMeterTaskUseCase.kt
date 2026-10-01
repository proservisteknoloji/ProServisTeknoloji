package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import com.proservis.technician.domain.model.MeterReadingInput
import javax.inject.Inject

class CompleteMeterTaskUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    suspend operator fun invoke(
        tenantId: String,
        taskId: String,
        uid: String,
        readings: List<MeterReadingInput>,
        note: String?,
    ) {
        workRepository.completeMeterTaskWithReading(
            tenantId = tenantId,
            taskId = taskId,
            uid = uid,
            readings = readings,
            note = note,
        )
    }
}

