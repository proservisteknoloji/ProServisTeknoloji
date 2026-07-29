package com.proservis.technician.domain.usecase

import com.proservis.technician.data.auth.AuthRepository
import com.proservis.technician.domain.model.UserSession
import javax.inject.Inject

class LoginUseCase @Inject constructor(
    private val authRepository: AuthRepository,
) {
    suspend operator fun invoke(email: String, password: String): Result<UserSession> {
        return authRepository.login(email = email, password = password)
    }
}
