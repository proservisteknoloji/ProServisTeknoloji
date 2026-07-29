package com.proservis.technician.domain.usecase

import com.proservis.technician.data.work.WorkRepository
import javax.inject.Inject

class VerifySerialUseCase @Inject constructor(
    private val workRepository: WorkRepository,
) {
    suspend operator fun invoke(tenantId: String, serviceId: String, uid: String, lastDigits: String) {
        workRepository.verifySerial(tenantId, serviceId, uid, lastDigits)
    }
}

