package com.proservis.technician.ui.screen.work

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ListenerRegistration
import com.google.firebase.firestore.SetOptions
import com.proservis.technician.data.session.SessionStore
import com.proservis.technician.domain.model.UserSession
import com.proservis.technician.domain.model.WorkItem
import com.proservis.technician.domain.model.WorkSource
import com.proservis.technician.domain.usecase.ClaimWorkUseCase
import com.proservis.technician.domain.usecase.CompleteMeterTaskUseCase
import com.proservis.technician.data.location.LocationReporter
import com.proservis.technician.domain.usecase.MarkArrivedUseCase
import com.proservis.technician.domain.usecase.ObserveMyWorkUseCase
import com.proservis.technician.domain.usecase.ObserveOpenPoolUseCase
import com.proservis.technician.domain.usecase.ReleaseWorkUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import javax.inject.Inject

@HiltViewModel
class WorkTabsViewModel @Inject constructor(
    private val sessionStore: SessionStore,
    private val db: FirebaseFirestore,
    private val observeOpenPoolUseCase: ObserveOpenPoolUseCase,
    private val observeMyWorkUseCase: ObserveMyWorkUseCase,
    private val claimWorkUseCase: ClaimWorkUseCase,
    private val releaseWorkUseCase: ReleaseWorkUseCase,
    private val markArrivedUseCase: MarkArrivedUseCase,
    private val completeMeterTaskUseCase: CompleteMeterTaskUseCase,
    private val locationReporter: LocationReporter,
) : ViewModel() {
    private val _uiState = MutableStateFlow(WorkTabsUiState())
    val uiState: StateFlow<WorkTabsUiState> = _uiState.asStateFlow()
    private var locationRequestListener: ListenerRegistration? = null
    private var lastHandledLocationRequestAtMs: Long = 0L

    init {
        observeData()
    }

    private fun normalize(value: String?): String = value.orEmpty().trim().lowercase()

    /** Web bazen atamada teknisyen doküman id'si yazabiliyor; e-posta/isimle eşleşen tüm teknisyen doc id'lerini "bana atanan" sayarız. */
    private suspend fun loadTechnicianDocIdsForSession(
        tenantId: String,
        email: String,
        technicianName: String,
    ): Set<String> {
        val col = db.collection("tenants").document(tenantId).collection("technicians")
        val aliases = mutableSetOf<String>()
        fun addAliases(doc: com.google.firebase.firestore.DocumentSnapshot) {
            aliases.add(doc.id)
            val data = doc.data ?: emptyMap<String, Any>()
            listOf(
                data["globalTechnicianId"] as? String,
                data["assignedGlobalTechnicianId"] as? String,
                data["technicianId"] as? String,
                data["technicianUid"] as? String,
                data["uid"] as? String,
                data["userId"] as? String,
                data["email"] as? String,
                data["loginId"] as? String,
            ).forEach { raw ->
                val value = raw.orEmpty().trim()
                if (value.isNotBlank()) aliases.add(value)
            }
        }
        val emailNorm = normalize(email)
        val nameTrim = technicianName.trim()
        if (emailNorm.isNotBlank()) {
            runCatching {
                col.whereEqualTo("email", emailNorm).limit(50).get().await().documents.forEach(::addAliases)
                col.whereEqualTo("loginId", emailNorm).limit(50).get().await().documents.forEach(::addAliases)
            }
        }
        if (nameTrim.isNotBlank()) {
            runCatching {
                col.whereEqualTo("name", nameTrim).limit(50).get().await().documents.forEach(::addAliases)
            }
        }
        return aliases
    }

    private fun observeData() {
        viewModelScope.launch {
            sessionStore.sessionFlow.collectLatest { session ->
                locationRequestListener?.remove()
                locationRequestListener = null
                lastHandledLocationRequestAtMs = 0L
                if (session == null) {
                    _uiState.update { WorkTabsUiState(loading = false, session = null) }
                    return@collectLatest
                }
                val effectiveSession = resolveSessionWithProfileId(session)
                ensureTenantMembership(effectiveSession)
                _uiState.update { it.copy(loading = true, session = effectiveSession, errorMessage = null) }
                loadCompanyInfo(effectiveSession.tenantId)
                observeLocationRequest(effectiveSession.tenantId, effectiveSession.uid)
                val additionalTechnicianDocIds = loadTechnicianDocIdsForSession(
                    effectiveSession.tenantId,
                    effectiveSession.email,
                    effectiveSession.technicianName,
                )
                combine(
                    observeOpenPoolUseCase(effectiveSession.tenantId),
                    observeMyWorkUseCase(
                        tenantId = effectiveSession.tenantId,
                        uid = effectiveSession.uid,
                        email = effectiveSession.email,
                        technicianName = effectiveSession.technicianName,
                        globalTechnicianId = effectiveSession.globalTechnicianId,
                        technicianProfileId = effectiveSession.technicianProfileId,
                        additionalTechnicianDocIds = additionalTechnicianDocIds,
                    ),
                ) { open, mine -> open to mine }
                    .collect { (open, mine) ->
                        _uiState.update {
                            it.copy(
                                loading = false,
                                openPoolItems = open,
                                myItems = mine,
                                session = effectiveSession,
                            )
                        }
                    }
            }
        }
    }

    private suspend fun ensureTenantMembership(session: UserSession) {
        val ref = db.document("tenants/${session.tenantId}/users/${session.uid}")
        val snap = ref.get().await()
        if (snap.exists()) return
        runCatching {
            ref.set(
                mapOf(
                    "uid" to session.uid,
                    "email" to session.email.trim(),
                    "name" to session.technicianName,
                    "role" to "technician",
                    "active" to true,
                    "createdAt" to FieldValue.serverTimestamp(),
                    "updatedAt" to FieldValue.serverTimestamp(),
                ),
                SetOptions.merge()
            ).await()
        }
    }

    private suspend fun resolveSessionWithProfileId(session: UserSession): UserSession {
        if (session.technicianProfileId.isNotBlank()) return session
        val tenantId = session.tenantId
        val uid = session.uid
        val emailNorm = normalize(session.email)
        val name = session.technicianName.trim()
        val technicians = db.collection("tenants").document(tenantId).collection("technicians")

        val direct = technicians.document(uid).get().await()
        if (direct.exists()) {
            val next = session.copy(technicianProfileId = uid)
            sessionStore.save(next)
            return next
        }

        if (emailNorm.isNotBlank()) {
            val byEmail = technicians.whereEqualTo("email", emailNorm).limit(1).get().await().documents.firstOrNull()
            if (byEmail != null) {
                val next = session.copy(technicianProfileId = byEmail.id)
                sessionStore.save(next)
                return next
            }
            val byLoginId = technicians.whereEqualTo("loginId", emailNorm).limit(1).get().await().documents.firstOrNull()
            if (byLoginId != null) {
                val next = session.copy(technicianProfileId = byLoginId.id)
                sessionStore.save(next)
                return next
            }
        }

        if (name.isNotBlank()) {
            val byName = technicians.whereEqualTo("name", name).limit(1).get().await().documents.firstOrNull()
            if (byName != null) {
                val next = session.copy(technicianProfileId = byName.id)
                sessionStore.save(next)
                return next
            }
        }

        val allTechs = technicians.get().await().documents
        val normalizedName = normalize(name)
        for (row in allTechs) {
            val data = row.data ?: emptyMap<String, Any>()
            val rowEmail = normalize(data["email"] as? String)
            val rowLoginId = normalize(data["loginId"] as? String)
            val rowName = normalize(data["name"] as? String)
            if (emailNorm.isNotBlank() && (rowEmail == emailNorm || rowLoginId == emailNorm)) {
                val next = session.copy(technicianProfileId = row.id)
                sessionStore.save(next)
                return next
            }
            if (normalizedName.isNotBlank() && rowName == normalizedName) {
                val next = session.copy(technicianProfileId = row.id)
                sessionStore.save(next)
                return next
            }
        }

        return session.copy(technicianProfileId = uid)
    }

    private fun observeLocationRequest(tenantId: String, uid: String) {
        locationRequestListener?.remove()
        locationRequestListener = db.document("tenants/$tenantId/technician_location_requests/$uid")
            .addSnapshotListener { snapshot, error ->
                if (error != null) return@addSnapshotListener
                val requestedAt = snapshot?.getTimestamp("requestedAt")
                val requestedMs = requestedAt?.toDate()?.time ?: 0L
                if (requestedMs <= 0L) return@addSnapshotListener
                if (requestedMs <= lastHandledLocationRequestAtMs) return@addSnapshotListener
                lastHandledLocationRequestAtMs = requestedMs
                _uiState.update { it.copy(locationRequestNonce = it.locationRequestNonce + 1) }
            }
    }

    private fun loadCompanyInfo(tenantId: String) {
        viewModelScope.launch {
            runCatching {
                db.document("tenants/$tenantId/settings/company_info").get().await()
            }.onSuccess { snap ->
                val data = if (snap.exists()) {
                    snap.data.orEmpty()
                } else {
                    runCatching { db.document("tenants/$tenantId/settings/company").get().await().data.orEmpty() }
                        .getOrDefault(emptyMap())
                }
                val tenantData = runCatching { db.document("tenants/$tenantId").get().await().data.orEmpty() }
                    .getOrDefault(emptyMap())
                val resolvedName =
                    (data["companyName"] as? String).orEmpty().trim().ifBlank {
                        (data["name"] as? String).orEmpty().trim().ifBlank {
                            (data["title"] as? String).orEmpty().trim().ifBlank {
                                (tenantData["companyName"] as? String).orEmpty().trim().ifBlank {
                                    (tenantData["name"] as? String).orEmpty().trim().ifBlank { tenantId }
                                }
                            }
                        }
                    }
                val resolvedLogo =
                    (data["logoDataUrl"] as? String).orEmpty().trim().ifBlank {
                        (data["logoBase64"] as? String).orEmpty().trim().ifBlank {
                            (data["logo"] as? String).orEmpty().trim()
                        }
                    }
                _uiState.update {
                    it.copy(
                        companyName = resolvedName,
                        companyLogoDataUrl = resolvedLogo,
                    )
                }
            }
        }
    }

    fun claim(item: WorkItem) {
        val session = _uiState.value.session ?: return
        runAction(item.id) {
            claimWorkUseCase(
                tenantId = session.tenantId,
                id = item.id,
                source = item.source,
                uid = session.uid,
                technicianName = session.technicianName,
            )
        }
    }

    fun release(item: WorkItem) {
        val session = _uiState.value.session ?: return
        runAction(item.id) {
            releaseWorkUseCase(
                tenantId = session.tenantId,
                id = item.id,
                source = item.source,
                uid = session.uid,
            )
        }
    }

    fun markArrived(item: WorkItem) {
        val session = _uiState.value.session ?: return
        if (item.source != WorkSource.SERVICE) return
        runAction(item.id) {
            markArrivedUseCase(
                tenantId = session.tenantId,
                serviceId = item.id,
                uid = session.uid,
            )
        }
    }

    fun completeMeterTask(item: WorkItem, bwCounter: Int?, colorCounter: Int?, note: String?) {
        val session = _uiState.value.session ?: return
        if (item.source == WorkSource.METER_TASK) {
            runAction(item.id) {
                completeMeterTaskUseCase(
                    tenantId = session.tenantId,
                    taskId = item.id,
                    uid = session.uid,
                    bwCounter = bwCounter,
                    colorCounter = colorCounter,
                    note = note,
                )
                // Tamamlanan görevin bağlı service_records kaydını da güncelle:
                // technician_tasks belgesinde serviceRecordId varsa bwCounter/colorCounter yaz
                runCatching {
                    val taskSnap = db.document("tenants/${session.tenantId}/technician_tasks/${item.id}").get().await()
                    val serviceRecordId = taskSnap.getString("serviceRecordId")
                        ?: taskSnap.getString("parentServiceId")
                        ?: taskSnap.getString("serviceId")
                    if (!serviceRecordId.isNullOrBlank()) {
                        val serviceUpdates = mutableMapOf<String, Any?>(
                            "technicianReport" to (note ?: "Sayaç okuma tamamlandı"),
                            "status" to "Repaired",
                            "closedAt" to FieldValue.serverTimestamp(),
                            "updatedAt" to FieldValue.serverTimestamp(),
                        )
                        bwCounter?.let { serviceUpdates["bwCounter"] = it }
                        colorCounter?.let { serviceUpdates["colorCounter"] = it }
                        db.document("tenants/${session.tenantId}/service_records/$serviceRecordId")
                            .update(serviceUpdates)
                            .await()
                    }
                }
            }
        } else if (item.source == WorkSource.SERVICE) {
            runAction(item.id) {
                val updates = mutableMapOf<String, Any?>(
                    "status" to "Repaired",
                    "technicianReport" to (note ?: "Sayaç okuma tamamlandı"),
                    "closedAt" to FieldValue.serverTimestamp(),
                    "updatedAt" to FieldValue.serverTimestamp(),
                )
                bwCounter?.let { updates["bwCounter"] = it }
                colorCounter?.let { updates["colorCounter"] = it }
                db.document("tenants/${session.tenantId}/service_records/${item.id}").update(updates).await()
            }
        }
    }


    fun updateServiceStatus(item: WorkItem, newStatus: String) {
        val session = _uiState.value.session ?: return
        if (item.source != WorkSource.SERVICE) return
        runAction(item.id) {
            val updates = mutableMapOf<String, Any>(
                "status" to newStatus,
                "updatedAt" to FieldValue.serverTimestamp(),
            )
            if (newStatus == "Repaired" || newStatus == "Delivered" || newStatus == "Closed") {
                updates["closedAt"] = FieldValue.serverTimestamp()
            }
            db.document("tenants/${session.tenantId}/service_records/${item.id}").update(updates).await()
        }
    }

    fun updateTechnicianLocation(latitude: Double, longitude: Double) {
        val session = _uiState.value.session ?: return
        viewModelScope.launch {
            val location = android.location.Location("").apply {
                this.latitude = latitude
                this.longitude = longitude
            }
            locationReporter.reportLocation(session.tenantId, location, "workflow_trigger")
        }
    }

    private fun runAction(id: String, block: suspend () -> Unit) {
        viewModelScope.launch {
            _uiState.update { it.copy(actionBusyId = id, errorMessage = null) }
            runCatching { block() }
                .onFailure { err ->
                    _uiState.update { it.copy(errorMessage = err.message ?: "İşlem hatası") }
                }
            _uiState.update { it.copy(actionBusyId = null) }
        }
    }

    fun logout() {
        viewModelScope.launch {
            runCatching {
                com.google.firebase.auth.FirebaseAuth.getInstance().signOut()
                sessionStore.clear()
            }
        }
    }

    override fun onCleared() {
        locationRequestListener?.remove()
        locationRequestListener = null
        super.onCleared()
    }
}
