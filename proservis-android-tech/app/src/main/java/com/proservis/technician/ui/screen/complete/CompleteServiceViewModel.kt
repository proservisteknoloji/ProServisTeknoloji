package com.proservis.technician.ui.screen.complete

import android.util.Base64
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.Timestamp
import com.google.firebase.appcheck.FirebaseAppCheck
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.storage.FirebaseStorage
import com.google.firebase.storage.storageMetadata
import com.proservis.technician.data.session.SessionStore
import com.proservis.technician.domain.model.ServiceCompletionData
import com.proservis.technician.domain.usecase.CompleteServiceUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.util.Locale
import javax.inject.Inject

data class CompleteServiceUiState(
    val serviceId: String = "",
    val jobType: String = "service",
    val title: String = "",
    val customerName: String = "",
    val locationText: String = "",
    val serialNumber: String? = null,
    val status: String = "Repaired",
    val report: String = "",
    val bwCounter: String = "",
    val colorCounter: String = "",
    val isColorDevice: Boolean = false,
    val lastBwCounter: String? = null,
    val lastColorCounter: String? = null,
    val problemDescription: String? = null,
    val deliveryRecipientName: String = "",
    val deliveryItems: List<String> = emptyList(),
    val reportFileName: String? = null,
    val reportUploadInProgress: Boolean = false,
    val reportUploadError: String? = null,
    val loading: Boolean = false,
    val errorMessage: String? = null,
    val success: Boolean = false,
) {
    val isServiceJob: Boolean
        get() = jobType == "service" || jobType == "maintenance" || jobType == "part_replacement" || jobType == "bakim" || jobType == "parca_degisimi"
    val isDeliveryJob: Boolean
        get() = jobType == "toner_delivery" || jobType == "product_transfer" || jobType == "device_delivery" || jobType == "cihaz_teslimati"
    val isSimpleTask: Boolean
        get() = !isServiceJob && !isDeliveryJob
}

@HiltViewModel
class CompleteServiceViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val sessionStore: SessionStore,
    private val completeServiceUseCase: CompleteServiceUseCase,
    private val db: FirebaseFirestore,
    private val storage: FirebaseStorage,
) : ViewModel() {
    companion object {
        private const val INLINE_ATTACHMENT_MAX_BYTES = 450_000
    }

    private val serviceId: String = savedStateHandle["serviceId"] ?: ""
    private val _uiState = MutableStateFlow(CompleteServiceUiState(serviceId = serviceId))
    val uiState: StateFlow<CompleteServiceUiState> = _uiState.asStateFlow()

    init {
        loadCurrentServiceData()
    }

    fun onStatusChanged(value: String) {
        _uiState.update { it.copy(status = value, errorMessage = null) }
    }

    fun onReportChanged(value: String) {
        _uiState.update { it.copy(report = value, errorMessage = null) }
    }

    fun onBwCounterChanged(value: String) {
        _uiState.update { it.copy(bwCounter = value, errorMessage = null) }
    }

    fun onColorCounterChanged(value: String) {
        _uiState.update { it.copy(colorCounter = value, errorMessage = null) }
    }

    fun onDeliveryRecipientChanged(value: String) {
        _uiState.update { it.copy(deliveryRecipientName = value, errorMessage = null) }
    }

    fun uploadReport(fileName: String, contentType: String?, bytes: ByteArray) {
        if (bytes.isEmpty()) {
            _uiState.update { it.copy(reportUploadError = "Yuklenen dosya bos.") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(reportUploadInProgress = true, reportUploadError = null) }
            val session = sessionStore.sessionFlow.firstOrNull()
            if (session == null) {
                _uiState.update { it.copy(reportUploadInProgress = false, reportUploadError = "Oturum bulunamadi.") }
                return@launch
            }

            val sanitizedName = fileName.replace(Regex("[^a-zA-Z0-9._-]"), "_").ifBlank { "rapor.bin" }
            val path = "tenants/${session.tenantId}/service_reports/$serviceId/technician_form/${System.currentTimeMillis()}_$sanitizedName"
            val metadata = storageMetadata { this.contentType = contentType ?: "application/octet-stream" }
            val refs = buildStorageRefs(path)
            runCatching {
                FirebaseAppCheck.getInstance().getAppCheckToken(false).await()
                var uploaded = false
                var lastUploadError: Throwable? = null
                for (candidate in refs) {
                    try {
                        uploadWithRetry(candidate, bytes, metadata)
                        uploaded = true
                        break
                    } catch (inner: Throwable) {
                        lastUploadError = inner
                    }
                }
                if (!uploaded) throw (lastUploadError ?: IllegalStateException("Tum bucket denemeleri basarisiz."))
                val attachment = mapOf(
                    "id" to "technician_form_${System.currentTimeMillis()}_${session.uid.take(8)}",
                    "type" to "technician_form",
                    "fileName" to fileName,
                    "contentType" to (contentType ?: "application/octet-stream"),
                    "fileSize" to bytes.size,
                    "url" to "",
                    "storagePath" to path,
                    "uploadedByUid" to session.uid,
                    "uploadedByName" to session.technicianName.ifBlank { session.email },
                    "uploadedAt" to Timestamp.now(),
                )
                db.document("tenants/${session.tenantId}/service_records/$serviceId").update(
                    mapOf(
                        "attachments" to FieldValue.arrayUnion(attachment),
                        "updatedAt" to FieldValue.serverTimestamp(),
                    )
                ).await()
            }.onSuccess {
                _uiState.update { it.copy(reportUploadInProgress = false, reportUploadError = null, reportFileName = fileName) }
            }.onFailure { err ->
                runCatching {
                    persistInlineAttachment(
                        tenantId = session.tenantId,
                        sessionUid = session.uid,
                        sessionName = session.technicianName.ifBlank { session.email },
                        fileName = fileName,
                        contentType = contentType ?: "application/octet-stream",
                        bytes = bytes,
                    )
                }.onSuccess {
                    _uiState.update { it.copy(reportUploadInProgress = false, reportUploadError = null, reportFileName = fileName) }
                }.onFailure { inlineErr ->
                    _uiState.update {
                        it.copy(
                            reportUploadInProgress = false,
                            reportUploadError = "Rapor yuklenemedi: ${(err.message ?: "Bilinmeyen")} | Firestore fallback: ${(inlineErr.message ?: "Bilinmeyen")}".trim(),
                        )
                    }
                }
            }
        }
    }

    fun submitWithStatus(targetStatus: String) {
        _uiState.update { it.copy(status = targetStatus) }
        submit()
    }

    fun submit() {
        val current = _uiState.value
        val report = current.report.trim()
        val isDeliveryJob = current.isDeliveryJob
        val isServiceJob = current.isServiceJob
        if (isDeliveryJob && current.deliveryRecipientName.trim().length < 3) {
            _uiState.update { it.copy(errorMessage = "Teslim alan kisi en az 3 karakter olmali.") }
            return
        }
        if (!isDeliveryJob && report.length < 3) {
            _uiState.update { it.copy(errorMessage = "Rapor en az 3 karakter olmali.") }
            return
        }

        val bw = parseCounter(current.bwCounter)
        val color = parseCounter(current.colorCounter)
        val lastBw = current.lastBwCounter?.toIntOrNull()
        val lastColor = current.lastColorCounter?.toIntOrNull()
        if (isServiceJob) {
            if (bw == null) {
                _uiState.update { it.copy(errorMessage = "Yeni S/B sayac zorunlu.") }
                return
            }
            if (lastBw != null && bw < lastBw) {
                _uiState.update { it.copy(errorMessage = "Yeni S/B sayac son okunan degerden kucuk olamaz.") }
                return
            }
            if (current.isColorDevice && color == null) {
                _uiState.update { it.copy(errorMessage = "Renkli cihazda yeni renkli sayac zorunlu.") }
                return
            }
            if (current.isColorDevice && lastColor != null && color != null && color < lastColor) {
                _uiState.update { it.copy(errorMessage = "Yeni renkli sayac son okunan degerden kucuk olamaz.") }
                return
            }
        }

        viewModelScope.launch {
            _uiState.update { it.copy(loading = true, errorMessage = null) }
            val session = sessionStore.sessionFlow.firstOrNull()
            if (session == null) {
                _uiState.update { it.copy(loading = false, errorMessage = "Oturum bulunamadi.") }
                return@launch
            }

            val finalStatus = when {
                isDeliveryJob -> "Delivery"
                current.isSimpleTask -> "Repaired"
                else -> current.status.ifBlank { "Repaired" }
            }

            val data = ServiceCompletionData(
                status = finalStatus,
                technicianReport = if (report.isBlank() && isDeliveryJob) "Teslim bilgisi girildi" else report,
                bwCounter = if (isServiceJob) bw else null,
                colorCounter = if (isServiceJob && current.isColorDevice) color else null,
                deliveryRecipientName = current.deliveryRecipientName.trim().ifBlank { null },
            )

            runCatching {
                completeServiceUseCase(session.tenantId, serviceId, session.uid, data)
            }.onSuccess {
                _uiState.update { it.copy(loading = false, success = true) }
            }.onFailure { err ->
                _uiState.update { it.copy(loading = false, errorMessage = "Tamamlama hatasi: ${err.message ?: "Bilinmeyen"}") }
            }
        }
    }

    private fun loadCurrentServiceData() {
        viewModelScope.launch {
            val session = sessionStore.sessionFlow.firstOrNull() ?: return@launch
            val snap = db.document("tenants/${session.tenantId}/service_records/$serviceId").get().await()
            if (!snap.exists()) return@launch
            val jobType = inferJobType(snap)
            val currentBw = (snap.get("bwCounter") as? Number)?.toLong()?.toString()
            val currentColor = (snap.get("colorCounter") as? Number)?.toLong()?.toString()
            val report = snap.getString("technicianReport").orEmpty()
            val summary = snap.getString("problemDescription")
                ?: snap.getString("taskSummary")
                ?: snap.getString("problem")
                ?: snap.getString("faultDescription")
                ?: snap.getString("description")
                ?: snap.getString("notes")
                ?: snap.getString("serviceReason")
                ?: snap.getString("actionsTaken")
            val deviceModel = snap.getString("deviceModel").orEmpty()
            val deviceSerial = snap.getString("deviceSerialNumber")
            val customerName = snap.getString("customerName").orEmpty()
            val locationText = snap.getString("locationName")
                ?: snap.getString("locationText")
                ?: snap.getString("locationAddress")
                ?: snap.getString("customerAddress")
                ?: ""
            val fulfillmentItems = (snap.get("fulfillmentItems") as? List<Map<String, Any?>>).orEmpty().mapNotNull { row ->
                val name = row["stockItemName"]?.toString().orEmpty().trim()
                val quantity = (row["quantity"] as? Number)?.toInt() ?: row["quantity"]?.toString()?.toIntOrNull() ?: 0
                if (name.isBlank()) null else "$name x$quantity"
            }
            val customerId = snap.getString("customerId").orEmpty()
            val deviceId = snap.getString("deviceId").orEmpty()
            var deviceIsColor: Boolean? = null
            var fallbackBw: String? = null
            var fallbackColor: String? = null
            if (customerId.isNotBlank() && deviceId.isNotBlank()) {
                runCatching { db.document("tenants/${session.tenantId}/customers/$customerId/devices/$deviceId").get().await() }
                    .onSuccess { deviceSnap ->
                        if (deviceSnap.exists()) {
                            deviceIsColor = deviceSnap.getBoolean("isColor")
                            fallbackBw = (deviceSnap.get("currentCounters.bw") as? Number)?.toLong()?.toString()
                            fallbackColor = (deviceSnap.get("currentCounters.color") as? Number)?.toLong()?.toString()
                        }
                    }
            }
            val isColorDevice = snap.getBoolean("isColorDevice") ?: snap.getBoolean("isColor") ?: deviceIsColor ?: false
            _uiState.update {
                it.copy(
                    jobType = jobType,
                    title = deviceModel.ifBlank {
                        when (jobType) {
                            "toner_delivery" -> "Toner Teslimi"
                            "product_transfer" -> "Urun Teslimi"
                            "misc" -> "Muhtelif Is"
                            else -> "Servis Kaydi"
                        }
                    },
                    customerName = customerName,
                    locationText = locationText,
                    serialNumber = deviceSerial,
                    report = report,
                    bwCounter = "",
                    colorCounter = "",
                    lastBwCounter = currentBw ?: fallbackBw,
                    lastColorCounter = if (isColorDevice) (currentColor ?: fallbackColor) else null,
                    problemDescription = summary,
                    isColorDevice = isColorDevice,
                    deliveryRecipientName = snap.getString("deliveryRecipientName").orEmpty(),
                    deliveryItems = fulfillmentItems,
                    status = run {
                        val raw = (snap.getString("status") ?: "").trim().lowercase()
                        when (raw) {
                            "fault_persists", "fault persists", "ariza devam ediyor" -> "Fault Persists"
                            "repaired", "onarildi", "onarım tamamlandı" -> "Repaired"
                            "delivered", "closed", "servisi kapat" -> "Delivered"
                            else -> "In Progress"
                        }
                    },
                )
            }
        }
    }

    private fun parseCounter(value: String): Int? = value.trim().replace(Regex("[^0-9]"), "").toIntOrNull()

    private fun canonicalJobType(value: String?): String {
        val raw = value.orEmpty().trim()
        if (raw.isBlank()) return "service"
        val direct = raw.lowercase(Locale.ROOT)
        if (direct in setOf("meter_collection", "metercollection")) return "meter_collection"
        if (direct in setOf("toner_delivery", "tonerdelivery")) return "toner_delivery"
        if (direct in setOf("product_transfer", "producttransfer")) return "product_transfer"
        if (direct in setOf("device_pickup", "devicepickup", "cihaz_alimi")) return "device_pickup"
        if (direct in setOf("device_delivery", "devicedelivery", "cihaz_teslimati")) return "device_delivery"
        if (direct in setOf("device_replacement", "devicereplacement", "cihaz_degisimi")) return "device_replacement"
        if (direct in setOf("cargo_shipping", "cargoshipping", "kargo_gonderimi")) return "cargo_shipping"
        if (direct in setOf("misc")) return "misc"
        if (direct in setOf("service", "service_assignment")) return "service"

        val normalized = normalizeJobType(value)
        val token = normalized.replace(Regex("[^a-z0-9]"), "")
        return when {
            token in setOf("metercollection", "sayacokuma", "sayactoplama", "sayacgorevi") ||
                normalized.contains("sayac") ||
                normalized.contains("meter") -> "meter_collection"
            normalized in setOf("service", "service_assignment", "ariza", "fault") -> "service"
            normalized.contains("bakim") || normalized.contains("parca") -> "service"
            token in setOf("cihazalimi", "devicepickup") ||
                normalized in setOf("cihaz alimi", "device_pickup") -> "device_pickup"
            token in setOf("cihazteslimati", "devicedelivery") ||
                normalized in setOf("cihaz teslimati", "device_delivery") -> "device_delivery"
            token in setOf("cihazdegisimi", "devicereplacement") ||
                normalized in setOf("cihaz degisimi", "device_replacement") -> "device_replacement"
            token in setOf("kargogonderimi", "cargoshipping") ||
                normalized in setOf("kargo gonderimi", "cargo_shipping") -> "cargo_shipping"
            token in setOf("tonerteslimi", "tonerdelivery") ||
                normalized in setOf("toner_delivery", "toner teslimi") -> "toner_delivery"
            token in setOf("urunteslimi", "producttransfer", "urunalis") ||
                normalized in setOf("urun teslimi", "urun teslimati", "urun alimi", "product_transfer") -> "product_transfer"
            normalized in setOf("misc", "muhtelif") -> "misc"
            else -> if (normalized.isBlank()) "service" else normalized
        }
    }

    private fun normalizeJobType(value: String?): String {
        val folded = java.text.Normalizer.normalize(value.orEmpty(), java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .lowercase(Locale.ROOT)
        return folded.trim()
            .replace("ı", "i")
            .replace("ğ", "g")
            .replace("ü", "u")
            .replace("ş", "s")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace("â", "a")
            .replace("î", "i")
            .replace("û", "u")
    }

    private fun inferJobType(snap: com.google.firebase.firestore.DocumentSnapshot): String {
        val explicit = snap.getString("jobType").orEmpty().trim()
        if (explicit.isNotBlank()) {
            val result = canonicalJobType(explicit)
            if (result != "service" || explicit.lowercase(Locale.ROOT) in setOf("service", "service_assignment")) {
                return result
            }
        }

        val explicitReason = snap.getString("serviceReason") ?: snap.getString("service_reason")
        if (!explicitReason.isNullOrBlank()) return canonicalJobType(explicitReason.trim())

        val desc = snap.getString("problemDescription") ?: snap.getString("taskSummary")
        if (!desc.isNullOrBlank() && desc.startsWith("[") && desc.contains("]")) {
            val bracketReason = desc.substringAfter("[").substringBefore("]").trim()
            if (bracketReason.isNotBlank() && bracketReason.length < 50) return canonicalJobType(bracketReason)
        }

        if (explicit.isNotBlank()) return canonicalJobType(explicit)

        val combined = listOfNotNull(
            snap.getString("taskSummary"),
            snap.getString("problemDescription"),
            snap.getString("problem"),
            snap.getString("faultDescription"),
            snap.getString("description"),
        ).joinToString(" ").lowercase()
        return when {
            "toner" in combined -> "toner_delivery"
            "muhtelif" in combined -> "misc"
            "urun teslim" in combined || "ürün teslim" in combined || "urun" in combined -> "product_transfer"
            else -> "service"
        }
    }

    private suspend fun uploadWithRetry(ref: com.google.firebase.storage.StorageReference, bytes: ByteArray, metadata: com.google.firebase.storage.StorageMetadata) {
        var lastError: Throwable? = null
        repeat(3) { index ->
            try {
                ref.putBytes(bytes, metadata).await(); return
            } catch (err: Throwable) {
                lastError = err
                if (index < 2) delay(800L * (index + 1))
            }
        }
        throw (lastError ?: IllegalStateException("Upload basarisiz"))
    }

    private fun buildStorageRefs(path: String): List<com.google.firebase.storage.StorageReference> =
        listOf(storage.reference.child(path))

    private suspend fun persistInlineAttachment(tenantId: String, sessionUid: String, sessionName: String, fileName: String, contentType: String, bytes: ByteArray) {
        require(bytes.size <= INLINE_ATTACHMENT_MAX_BYTES) { "Dosya fallback limiti asiyor." }
        val attachment = mapOf(
            "id" to "technician_inline_${System.currentTimeMillis()}_${sessionUid.take(8)}",
            "type" to "technician_form_inline",
            "fileName" to fileName,
            "contentType" to contentType,
            "fileSize" to bytes.size,
            "inlineBase64" to Base64.encodeToString(bytes, Base64.NO_WRAP),
            "uploadedByUid" to sessionUid,
            "uploadedByName" to sessionName,
            "uploadedAt" to Timestamp.now(),
        )
        db.document("tenants/$tenantId/service_records/$serviceId").update(
            mapOf(
                "attachments" to FieldValue.arrayUnion(attachment),
                "updatedAt" to FieldValue.serverTimestamp(),
            )
        ).await()
    }
}
