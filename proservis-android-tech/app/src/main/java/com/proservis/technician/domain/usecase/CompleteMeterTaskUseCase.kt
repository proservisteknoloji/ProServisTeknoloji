package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import javax.inject.Inject

class CompleteMeterTaskUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    suspend operator fun invoke(
        tenantId: String,
        taskId: String,
        uid: String,
        bwCounter: Int?,
        colorCounter: Int?,
        note: String?,
    ) {
        workRepository.completeMeterTaskWithReading(
            tenantId = tenantId,
            taskId = taskId,
            uid = uid,
            bwCounter = bwCounter,
            colorCounter = colorCounter,
            note = note,
        )
    }
}

