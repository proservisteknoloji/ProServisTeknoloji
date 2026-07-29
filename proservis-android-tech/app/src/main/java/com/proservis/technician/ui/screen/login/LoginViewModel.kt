package com.proservis.technician.ui.screen.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.proservis.technician.domain.usecase.LoginUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val loginUseCase: LoginUseCase,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun onEmailChanged(value: String) {
        _uiState.update { it.copy(email = value, errorMessage = null) }
    }

    fun onPasswordChanged(value: String) {
        _uiState.update { it.copy(password = value, errorMessage = null) }
    }

    fun onLogin() {
        val state = _uiState.value
        if (state.email.isBlank() || state.password.isBlank()) {
            _uiState.update { it.copy(errorMessage = "E-posta ve sifre zorunludur.") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, errorMessage = null) }
            val result = loginUseCase(
                email = state.email.trim().lowercase(),
                password = state.password,
            )
            result.fold(
                onSuccess = {
                    _uiState.update { prev ->
                        prev.copy(
                            loading = false,
                            loginSuccessful = true,
                            errorMessage = null,
                        )
                    }
                },
                onFailure = { throwable ->
                    val message = when (throwable.message) {
                        "TEKNISYEN_ID_BULUNAMADI" -> "Teknisyen kaydi bulunamadi."
                        "TEKNISYEN_EMAIL_ESLESMIYOR" -> "Bu hesapla teknisyen kaydi eslesmiyor."
                        "YETKINIZ_YOK" -> "Bu teknisyen için yetkiniz yok."
                        "HESAP_PASIF" -> "Kullanıcı hesabı pasif."
                        "KULLANICI_BULUNAMADI" -> "Teknisyen kullanıcısı bulunamadı."
                        "GECERSIZ_GIRIS_BILGISI" -> "E-posta veya şifre hatalı."
                        else -> "Giriş başarısız: ${throwable.message ?: "Bilinmeyen hata"}"
                    }
                    _uiState.update { it.copy(loading = false, errorMessage = message) }
                }
            )
        }
    }

    fun consumeNavigation() {
        _uiState.update { it.copy(loginSuccessful = false) }
    }
}
