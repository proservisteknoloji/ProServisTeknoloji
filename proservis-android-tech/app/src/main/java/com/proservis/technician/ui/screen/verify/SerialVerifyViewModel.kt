package com.proservis.technician.ui.screen.verify

import android.os.SystemClock
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.proservis.technician.data.session.SessionStore
import com.proservis.technician.domain.usecase.VerifySerialUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

private const val MIN_VERIFY_LENGTH = 4
private const val SCAN_DEBOUNCE_MS = 800L

data class SerialVerifyUiState(
    val serviceId: String = "",
    val inputValue: String = "",
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val success: Boolean = false,
    val cameraPermissionGranted: Boolean = false,
    val scanRequested: Boolean = false,
    val isProcessing: Boolean = false,
    val scannedText: String = "",
    val debugOcrText: String = "",
    val statusMessage: String = "Kamera hazir. Seri numarayi hizalayip Oku butonuna basin.",
    val lastScanTimeMs: Long = 0L,
)

@HiltViewModel
class SerialVerifyViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val sessionStore: SessionStore,
    private val verifySerialUseCase: VerifySerialUseCase,
) : ViewModel() {

    private val serviceId: String = savedStateHandle["serviceId"] ?: ""

    private val _uiState = MutableStateFlow(SerialVerifyUiState(serviceId = serviceId))
    val uiState: StateFlow<SerialVerifyUiState> = _uiState.asStateFlow()

    fun onCameraPermissionResult(granted: Boolean) {
        _uiState.update { it.copy(cameraPermissionGranted = granted) }
    }

    fun onInputChanged(value: String) {
        _uiState.update {
            it.copy(
                inputValue = sanitizeSerialInput(value),
                errorMessage = null,
            )
        }
    }

    fun requestScan() {
        val state = _uiState.value
        val now = SystemClock.elapsedRealtime()
        if (state.isProcessing) return
        if (now - state.lastScanTimeMs < SCAN_DEBOUNCE_MS) return

        _uiState.update {
            it.copy(
                scanRequested = true,
                errorMessage = null,
                statusMessage = "Okuma bekleniyor...",
                debugOcrText = "",
                lastScanTimeMs = now,
            )
        }
    }

    fun beginProcessing(): Boolean {
        val state = _uiState.value
        if (!state.scanRequested || state.isProcessing) return false
        _uiState.update {
            it.copy(
                scanRequested = false,
                isProcessing = true,
                statusMessage = "Seri numara okunuyor...",
            )
        }
        return true
    }

    fun finishProcessing() {
        _uiState.update {
            it.copy(
                isProcessing = false,
                statusMessage = if (it.scannedText.isBlank()) {
                    "Okuma tamamlandi. Yeni okuma icin Oku butonuna basin."
                } else {
                    "Okuma hazir. Dogrulayabilir veya yeniden okuyabilirsiniz."
                },
            )
        }
    }

    fun canScan(): Boolean {
        val state = _uiState.value
        return state.scanRequested && !state.isProcessing
    }

    fun onOcrResult(result: SerialOcrFrameResult) {
        val best = result.bestCandidate
        _uiState.update {
            it.copy(
                debugOcrText = result.debugText,
                scannedText = best.orEmpty(),
                inputValue = if (!best.isNullOrBlank()) best else it.inputValue,
                statusMessage = if (!best.isNullOrBlank()) {
                    "Seri numara okundu."
                } else {
                    "Seri numara okunamadi. Konumu duzeltip yeniden deneyin."
                },
                errorMessage = if (!best.isNullOrBlank()) null else "Okuma sonucu uygun bir seri numara bulunamadi.",
            )
        }
    }

    fun clearScanResult() {
        _uiState.update {
            it.copy(
                scannedText = "",
                debugOcrText = "",
                errorMessage = null,
                statusMessage = "Tarama alani sifirlandi. Seri numarayi hizalayip Oku butonuna basin.",
            )
        }
    }

    fun verify() {
        val serial = sanitizeSerialInput(_uiState.value.inputValue)
        if (serial.length < MIN_VERIFY_LENGTH) {
            _uiState.update { it.copy(errorMessage = "En az 4 karakter girmelisiniz.") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, errorMessage = null) }
            val session = sessionStore.sessionFlow.firstOrNull()
            if (session == null) {
                _uiState.update { it.copy(loading = false, errorMessage = "Oturum bulunamadi.") }
                return@launch
            }
            runCatching {
                verifySerialUseCase(
                    tenantId = session.tenantId,
                    serviceId = serviceId,
                    uid = session.uid,
                    lastDigits = serial,
                )
            }.onSuccess {
                _uiState.update { it.copy(loading = false, success = true) }
            }.onFailure { err ->
                val msg = when (err.message) {
                    "SERI_ESLESMEDI" -> "Seri no eşleşmedi."
                    "CIHAZ_SERI_BILGISI_YOK" -> "Cihaz seri bilgisi bulunamadi."
                    "SERI_DOGRULAMA_MIN_4" -> "En az 4 karakter girmelisiniz."
                    else -> "Doğrulama hatasi: ${err.message ?: "Bilinmeyen"}"
                }
                _uiState.update { it.copy(loading = false, errorMessage = msg) }
            }
        }
    }

    fun verifyAnyAndProceed() {
        _uiState.update { it.copy(success = true) }
    }

    private fun sanitizeSerialInput(value: String): String {
        return value
            .replace(Regex("\\s+"), "")
            .replace(Regex("[^A-Za-z0-9\\-/]"), "")
            .uppercase()
    }
}
