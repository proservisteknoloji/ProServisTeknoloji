package com.proservis.technician

import android.Manifest
import android.graphics.BitmapFactory
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Base64
import android.util.Patterns
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.ListenerRegistration
import com.google.firebase.firestore.Query
import com.google.firebase.firestore.SetOptions
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.proservis.technician.navigation.AppNavGraph
import com.proservis.technician.data.push.PushTokenSync
import com.proservis.technician.ui.theme.ProservisTechTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

private data class StatusOption(val value: String, val label: String)
private val SERVICE_STATUS_OPTIONS = listOf(
    StatusOption("In Progress", "Servise Alındı"),
    StatusOption("Fault Persists", "Arıza Devam Ediyor"),
    StatusOption("Repaired", "Onarım Tamamlandı"),
    StatusOption("Delivered", "Servisi Kapat"),
)
private fun statusLabel(status: String): String = when (normalize(status)) {
    "received" -> "Açıkta Bekliyor"
    "assigned" -> "Teknisyene Atandı"
    "in progress", "in_progress" -> "Servise Alındı"
    "fault persists", "fault_persists" -> "Arıza Devam Ediyor"
    "waiting approval", "waiting_approval" -> "Onay Bekliyor"
    "waiting part", "waiting_part" -> "Parça Bekliyor"
    "repaired" -> "Onarım Tamamlandı"
    "delivery" -> "Teslimatta"
    "delivered", "closed" -> "Servis Kapandı"
    "cancelled" -> "İptal Edildi"
    else -> status.trim()
}

private data class ServiceRow(
    val id: String,
    val customerName: String,
    val deviceModel: String,
    val problemDescription: String,
    val status: String,
    val technicianReport: String,
    val notes: String,
    val bwCounter: Int?,
    val colorCounter: Int?,
    val assignedId: String,
    val assignedName: String,
)

private data class CustomerRow(val id: String, val name: String)
private data class DeviceRow(
    val taskId: String,
    val customerId: String,
    val customerName: String,
    val id: String,
    val model: String,
    val serialNumber: String,
    val isColor: Boolean,
    val bwCurrent: Int,
    val colorCurrent: Int,
    val taskStatus: String,
)

private data class TechnicianIdentity(val uid: String, val email: String, val name: String)
private fun normalize(v: String?): String = v.orEmpty().trim().lowercase()
private fun normalizeLoose(v: String?): String = normalize(v).replace(Regex("[^a-z0-9]"), "")

private fun isPending(row: ServiceRow): Boolean {
    val status = normalize(row.status)
    if (row.assignedId.isBlank() && row.assignedName.isBlank()) return true
    return status == "received" || status == "unassigned" || status == "open"
}

private fun canSeeAssignedToMe(row: ServiceRow, me: TechnicianIdentity): Boolean {
    if (isPending(row)) return false
    val aliases = setOf(normalize(me.uid), normalize(me.email), normalize(me.email.substringBefore("@")), normalize(me.name))
        .filter { it.isNotBlank() }
    val strictId = normalize(row.assignedId)
    val strictName = normalize(row.assignedName)
    if (strictId in aliases || strictName in aliases) return true
    val looseAliases = aliases.map { normalizeLoose(it) }.toSet()
    val looseId = normalizeLoose(row.assignedId)
    val looseName = normalizeLoose(row.assignedName)
    return looseId in looseAliases || looseName in looseAliases
}

private suspend fun decodeLogoDataUrl(dataUrl: String): androidx.compose.ui.graphics.ImageBitmap? {
    val raw = dataUrl.trim()
    if (!raw.startsWith("data:image")) return null
    val base64Index = raw.indexOf("base64,")
    if (base64Index < 0) return null
    val encoded = raw.substring(base64Index + 7)
    return withContext(Dispatchers.Default) {
        runCatching {
            val bytes = Base64.decode(encoded, Base64.DEFAULT)
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
        }.getOrNull()
    }
}

private fun isAssignedToMe(
    assignedId: String?,
    assignedName: String?,
    me: TechnicianIdentity,
): Boolean {
    val aliases = setOf(
        normalize(me.uid),
        normalize(me.email),
        normalize(me.email.substringBefore("@")),
        normalize(me.name),
    ).filter { it.isNotBlank() }.toSet()
    if (aliases.isEmpty()) return false
    val strictId = normalize(assignedId)
    val strictName = normalize(assignedName)
    if (strictId in aliases || strictName in aliases) return true
    val looseAliases = aliases.map { normalizeLoose(it) }.toSet()
    return normalizeLoose(assignedId) in looseAliases || normalizeLoose(assignedName) in looseAliases
}

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val requestAllPermissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestAllPermissionsOnLaunch()
        setContent { ProservisTechTheme { AppNavGraph() } }
    }

    private fun requestAllPermissionsOnLaunch() {
        val permissionsToRequest = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.CAMERA,
            Manifest.permission.CALL_PHONE,
        )
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            permissionsToRequest.add(Manifest.permission.POST_NOTIFICATIONS)
            permissionsToRequest.add(Manifest.permission.READ_MEDIA_IMAGES)
        } else {
            permissionsToRequest.add(Manifest.permission.READ_EXTERNAL_STORAGE)
        }

        val missing = permissionsToRequest.filter { perm ->
            androidx.core.content.ContextCompat.checkSelfPermission(this, perm) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isNotEmpty()) {
            requestAllPermissionsLauncher.launch(missing.toTypedArray())
        }
    }

    companion object {
        const val ACTION_OPEN_FROM_NOTIFICATION = "com.proservis.technician.OPEN_FROM_NOTIFICATION"
        const val EXTRA_NOTIFICATION_TYPE = "notification_type"
        const val EXTRA_NOTIFICATION_TENANT_ID = "notification_tenant_id"
        const val EXTRA_NOTIFICATION_SERVICE_ID = "notification_service_id"
        const val EXTRA_NOTIFICATION_TASK_ID = "notification_task_id"
    }
}

@Composable
private fun RootScreen() {
    val auth = remember { FirebaseAuth.getInstance() }
    val db = remember { FirebaseFirestore.getInstance() }
    var user by remember { mutableStateOf(auth.currentUser) }
    var tenantId by remember { mutableStateOf("") }
    var techName by remember { mutableStateOf("") }
    var logoDataUrl by remember { mutableStateOf("") }
    var logoBitmap by remember { mutableStateOf<androidx.compose.ui.graphics.ImageBitmap?>(null) }
    var loading by remember { mutableStateOf(true) }
    var err by remember { mutableStateOf("") }

    DisposableEffect(auth) {
        val listener = FirebaseAuth.AuthStateListener { user = it.currentUser }
        auth.addAuthStateListener(listener)
        onDispose { auth.removeAuthStateListener(listener) }
    }

    LaunchedEffect(user?.uid) {
        val u = user ?: return@LaunchedEffect
        loading = true
        err = ""
        tenantId = ""
        try {
            val g = db.document("users/${u.uid}").get().await()
            tenantId = (g.getString("tenantId") ?: "").trim()
            if (tenantId.isBlank()) {
                err = "Firma bilgisi bulunamadi."
            } else {
                val tu = db.document("tenants/$tenantId/users/${u.uid}").get().await()
                techName = (tu.getString("name") ?: "").trim()
                val company = db.document("tenants/$tenantId/settings/company_info").get().await()
                logoDataUrl = (company.getString("logoDataUrl") ?: "").trim()
                runCatching {
                    PushTokenSync.sync(tenantId, u.uid, u.email.orEmpty(), techName.ifBlank { u.email.orEmpty().substringBefore("@") }, db)
                }
            }
        } catch (e: Exception) {
            err = "Kullanici bilgisi okunamadi: ${e.localizedMessage ?: "Hata"}"
        } finally {
            loading = false
        }
    }

    if (user == null) {
        LoginScreen(auth)
        return
    }
    if (loading) {
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) { CircularProgressIndicator() }
        return
    }
    if (err.isNotBlank()) {
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
            Text(err, color = MaterialTheme.colorScheme.error)
        }
        return
    }

    if (tenantId.isBlank()) {
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
            CircularProgressIndicator()
        }
        return
    }

    LaunchedEffect(logoDataUrl) {
        logoBitmap = if (logoDataUrl.isBlank()) null else decodeLogoDataUrl(logoDataUrl)
    }

    MainScreen(auth, db, tenantId, user!!.uid, user!!.email.orEmpty(), techName, logoBitmap)
}

@Composable
private fun LoginScreen(auth: FirebaseAuth) {
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var msg by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Teknisyen Girisi", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(20.dp))
        OutlinedTextField(email, { email = it }, label = { Text("E-posta") }, singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email), modifier = Modifier.fillMaxWidth())
        OutlinedTextField(password, { password = it }, label = { Text("Sifre") }, singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password), modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(16.dp))
        Button(onClick = {
            val normalized = email.trim().lowercase()
            if (!Patterns.EMAIL_ADDRESS.matcher(normalized).matches()) { msg = "Gecerli e-posta girin."; return@Button }
            if (password.isBlank()) { msg = "Sifre bos olamaz."; return@Button }
            loading = true
            msg = ""
            auth.signInWithEmailAndPassword(normalized, password).addOnCompleteListener {
                loading = false
                if (!it.isSuccessful) msg = "Giris basarisiz: ${it.exception?.localizedMessage ?: "Hata"}"
            }
        }, enabled = !loading, modifier = Modifier.fillMaxWidth()) {
            if (loading) CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.height(18.dp)) else Text("Giris Yap")
        }
        if (msg.isNotBlank()) { Spacer(Modifier.height(12.dp)); Text(msg) }
    }
}

@Composable
private fun MainScreen(
    auth: FirebaseAuth,
    db: FirebaseFirestore,
    tenantId: String,
    uid: String,
    email: String,
    techName: String,
    logoBitmap: androidx.compose.ui.graphics.ImageBitmap?,
) {
    var mainTab by remember { mutableStateOf(0) } // 0 servis, 1 sayac
    Column(Modifier.fillMaxSize()) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = Color.Transparent)
        ) {
            Column(
                modifier = Modifier
                    .background(
                brush = Brush.linearGradient(
                    colors = listOf(Color(0xFF5D7F6C), Color(0xFF6F9781))
                )
            )
            .padding(14.dp)
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    if (logoBitmap != null) {
                        androidx.compose.foundation.Image(
                            bitmap = logoBitmap,
                            contentDescription = "Firma Logosu",
                            modifier = Modifier.size(52.dp).clip(MaterialTheme.shapes.medium)
                        )
                    } else {
                        Surface(
                            modifier = Modifier.size(52.dp),
                            shape = MaterialTheme.shapes.medium,
                            color = Color(0x33FFFFFF)
                        ) {
                            Column(
                                modifier = Modifier.fillMaxSize(),
                                verticalArrangement = Arrangement.Center,
                                horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally
                            ) { Text("PS", color = Color.White, fontWeight = FontWeight.Bold) }
                        }
                    }
                    Column {
                        Text("Teknisyen Paneli", color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text("Firma: $tenantId", color = Color(0xFFE0E7FF), style = MaterialTheme.typography.bodySmall)
                        Text(
                            if (email.isBlank()) "Kullanici: $uid" else "Kullanici: $email",
                            color = Color(0xFFE0E7FF),
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }

        TabRow(
            selectedTabIndex = mainTab,
            modifier = Modifier.fillMaxWidth().padding(top = 10.dp)
        ) {
            Tab(selected = mainTab == 0, onClick = { mainTab = 0 }, text = { Text("Servis") })
            Tab(selected = mainTab == 1, onClick = { mainTab = 1 }, text = { Text("Sayac") })
        }
        Spacer(Modifier.height(8.dp))
        if (mainTab == 0) ServiceSection(db, tenantId, uid, email, techName) else MeterSection(db, tenantId, uid)
    }
}

@Composable
private fun ServiceSection(
    db: FirebaseFirestore,
    tenantId: String,
    uid: String,
    email: String,
    technicianName: String,
) {
    if (tenantId.isBlank()) {
        Text("Firma bilgisi yukleniyor...")
        return
    }

    val scope = rememberCoroutineScope()
    var rows by remember { mutableStateOf<List<ServiceRow>>(emptyList()) }
    var loadErr by remember { mutableStateOf("") }
    var selected by remember { mutableStateOf<ServiceRow?>(null) }
    var tab by remember { mutableStateOf(0) } // 0 atanmamis 1 atanmis

    DisposableEffect(tenantId, uid, email, technicianName) {
        val reg: ListenerRegistration = db.collection("tenants").document(tenantId).collection("service_records")
            .orderBy("createdAt", Query.Direction.DESCENDING)
            .addSnapshotListener { snap, err ->
                if (err != null) { loadErr = "Servisler alinamadi: ${err.localizedMessage ?: "Hata"}"; return@addSnapshotListener }
                loadErr = ""
                val me = TechnicianIdentity(uid, email, technicianName)
                rows = snap?.documents.orEmpty().map { d ->
                    val assignedId = (d.getString("technicianId") ?: d.getString("technicianUid") ?: d.getString("assignedTechnicianId")
                        ?: d.getString("assignedTechnicianUid") ?: d.getString("assignedToUid") ?: "").trim()
                    val assignedName = (d.getString("technicianName") ?: d.getString("assignedTechnicianName") ?: d.getString("assignedToName") ?: "").trim()
                    ServiceRow(
                        id = d.id,
                        customerName = (d.getString("customerName") ?: d.getString("customer_name") ?: "-").trim().ifBlank { "-" },
                        deviceModel = (d.getString("deviceModel") ?: d.getString("device_model") ?: "-").trim().ifBlank { "-" },
                        problemDescription = (d.getString("problemDescription") ?: d.getString("problem") ?: "").trim(),
                        status = (d.getString("status") ?: "Received").trim().ifBlank { "Received" },
                        technicianReport = (d.getString("technicianReport") ?: d.getString("actionsTaken") ?: "").trim(),
                        notes = (d.getString("notes") ?: "").trim(),
                        bwCounter = (d.getLong("bwCounter") ?: 0L).toInt().takeIf { d.get("bwCounter") != null },
                        colorCounter = (d.getLong("colorCounter") ?: 0L).toInt().takeIf { d.get("colorCounter") != null },
                        assignedId = assignedId,
                        assignedName = assignedName,
                    )
                }.filter { isPending(it) || canSeeAssignedToMe(it, me) }
            }
        onDispose { reg.remove() }
    }

    if (loadErr.isNotBlank()) Text(loadErr, color = MaterialTheme.colorScheme.error)
    val unassigned = rows.filter { isPending(it) }
    val assigned = rows.filter {
        !isPending(it) &&
            normalize(it.status) != "repaired" &&
            normalize(it.status) != "delivered" &&
            normalize(it.status) != "closed" &&
            normalize(it.status) != "cancelled"
    }

    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        FilledTonalButton(
            onClick = { tab = 0 },
            colors = ButtonDefaults.filledTonalButtonColors(
                containerColor = if (tab == 0) Color(0xFFD1FAE5) else MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier.weight(1f)
        ) { Text("Atanmamis (${unassigned.size})") }
        FilledTonalButton(
            onClick = { tab = 1 },
            colors = ButtonDefaults.filledTonalButtonColors(
                containerColor = if (tab == 1) Color(0xFFFEE2E2) else MaterialTheme.colorScheme.surfaceVariant
            ),
            modifier = Modifier.weight(1f)
        ) { Text("Atanmis (${assigned.size})") }
    }

    Spacer(Modifier.height(8.dp))
    val visible = if (tab == 0) unassigned else assigned
    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(visible, key = { it.id }) { row ->
            Card(
                modifier = Modifier.fillMaxWidth().clickable { selected = row },
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF8FAFC))
            ) {
                Column(Modifier.padding(12.dp)) {
                    Text(row.customerName, fontWeight = FontWeight.Bold)
                    Text(row.deviceModel)
                    Text("Durum: ${statusLabel(row.status)}", style = MaterialTheme.typography.bodySmall)
                    if (row.problemDescription.isNotBlank()) {
                        Text("Ariza: ${row.problemDescription}", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }

    selected?.let { service ->
        var statusText by remember(service.id) { mutableStateOf(service.status.ifBlank { "Received" }) }
        var reportText by remember(service.id) { mutableStateOf(service.technicianReport) }
        var notesText by remember(service.id) { mutableStateOf(service.notes) }
        var bwText by remember(service.id) { mutableStateOf(service.bwCounter?.toString().orEmpty()) }
        var colorText by remember(service.id) { mutableStateOf(service.colorCounter?.toString().orEmpty()) }

        AlertDialog(
            onDismissRequest = { selected = null },
            title = { Text("Servis Guncelle") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("ID: ${service.id}", style = MaterialTheme.typography.bodySmall)
                    StatusDropdown(value = statusText, onValueSelected = { statusText = it })
                    OutlinedTextField(reportText, { reportText = it }, label = { Text("Teknisyen Raporu") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(notesText, { notesText = it }, label = { Text("Servis Notu") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(
                        bwText,
                        { bwText = it.filter { ch -> ch.isDigit() } },
                        label = { Text("S/B Sayac") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        colorText,
                        { colorText = it.filter { ch -> ch.isDigit() } },
                        label = { Text("Renkli Sayac") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val cleanStatus = statusText.trim().ifBlank { service.status }
                    val cleanReport = reportText.trim()
                    val cleanNotes = notesText.trim()
                    val bw = bwText.trim().toIntOrNull()
                    val color = colorText.trim().toIntOrNull()
                    val shouldClaim = isPending(service)
                    scope.launch {
                        runCatching {
                            val updates = mutableMapOf<String, Any>(
                                "status" to cleanStatus,
                                "technicianReport" to cleanReport,
                                "actionsTaken" to cleanReport,
                                "notes" to cleanNotes,
                                "updatedAt" to FieldValue.serverTimestamp(),
                            )
                            if (bw != null) updates["bwCounter"] = bw
                            if (color != null) updates["colorCounter"] = color
                            if (shouldClaim) {
                                val displayName = technicianName.ifBlank { email.substringBefore("@") }
                                updates["technicianId"] = uid
                                updates["technicianUid"] = uid
                                updates["assignedTechnicianId"] = uid
                                updates["assignedTechnicianUid"] = uid
                                updates["assignedToUid"] = uid
                                updates["technicianName"] = displayName
                                updates["assignedTechnicianName"] = displayName
                                updates["assignedToName"] = displayName
                            }
                            db.document("tenants/$tenantId/service_records/${service.id}").update(updates).await()
                        }
                        selected = null
                    }
                }) { Text("Guncelle") }
            },
            dismissButton = { TextButton(onClick = { selected = null }) { Text("Iptal") } }
        )
    }
}

@Composable
private fun MeterSection(
    db: FirebaseFirestore,
    tenantId: String,
    uid: String,
) {
    if (tenantId.isBlank()) {
        Text("Firma bilgisi yukleniyor...")
        return
    }

    val auth = remember { FirebaseAuth.getInstance() }
    var companies by remember { mutableStateOf<List<CustomerRow>>(emptyList()) }
    var selectedCompanyId by remember { mutableStateOf("") }
    var allAssignedDevices by remember { mutableStateOf<List<DeviceRow>>(emptyList()) }
    var selectedDevice by remember { mutableStateOf<DeviceRow?>(null) }
    var loadError by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var searchText by remember { mutableStateOf("") }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val fusedLocationClient = remember { LocationServices.getFusedLocationProviderClient(context) }
    var pendingLocationSend by remember { mutableStateOf(false) }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        val granted = result.values.any { it }
        if (granted) {
            pendingLocationSend = true
        }
    }

    fun logLocationRequestStatus(
        status: String,
        message: String,
        extra: Map<String, Any> = emptyMap(),
    ) {
        scope.launch {
            runCatching {
                db.document("tenants/$tenantId/technician_location_requests/$uid")
                    .set(
                        buildMap<String, Any> {
                            put("uid", uid)
                            put("lastHandledAt", FieldValue.serverTimestamp())
                            put("lastStatus", status)
                            put("lastError", message)
                            putAll(extra)
                        },
                        SetOptions.merge()
                    )
                    .await()
            }
        }
    }

    fun sendCurrentLocation() {
        val fineGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val coarseGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val backgroundGranted =
            android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.Q ||
                ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_BACKGROUND_LOCATION
                ) == PackageManager.PERMISSION_GRANTED
        if (!fineGranted && !coarseGranted) {
            logLocationRequestStatus(
                status = "permission_missing",
                message = "Konum izni yok",
                extra = mapOf(
                    "fineGranted" to fineGranted,
                    "coarseGranted" to coarseGranted,
                    "backgroundGranted" to backgroundGranted,
                )
            )
            locationPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                )
            )
            return
        }
        logLocationRequestStatus(
            status = "requested_foreground",
            message = "Uygulama icinden konum alimi basladi",
            extra = mapOf(
                "fineGranted" to fineGranted,
                "coarseGranted" to coarseGranted,
                "backgroundGranted" to backgroundGranted,
            )
        )
        fusedLocationClient.lastLocation.addOnSuccessListener { location ->
            if (location != null) {
                scope.launch {
                    runCatching {
                        db.document("tenants/$tenantId/technician_locations/$uid")
                            .set(
                                mapOf(
                                    "uid" to uid,
                                    "latitude" to location.latitude,
                                    "longitude" to location.longitude,
                                    "source" to "app_foreground",
                                    "updatedAt" to FieldValue.serverTimestamp(),
                                ),
                                SetOptions.merge()
                            )
                            .await()
                        db.document("tenants/$tenantId/technician_location_requests/$uid")
                            .set(
                                mapOf(
                                    "lastFulfilledAt" to FieldValue.serverTimestamp(),
                                    "fulfilledBy" to "app_foreground",
                                    "lastStatus" to "success",
                                    "lastError" to "",
                                ),
                                SetOptions.merge()
                            )
                            .await()
                    }.onFailure {
                        logLocationRequestStatus(
                            status = "write_failed",
                            message = it.message ?: "Konum Firestore'a yazilamadi",
                            extra = mapOf(
                                "fineGranted" to fineGranted,
                                "coarseGranted" to coarseGranted,
                                "backgroundGranted" to backgroundGranted,
                            )
                        )
                    }
                }
            } else {
                fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null)
                    .addOnSuccessListener { current ->
                        if (current != null) {
                            scope.launch {
                                runCatching {
                                    db.document("tenants/$tenantId/technician_locations/$uid")
                                        .set(
                                            mapOf(
                                                "uid" to uid,
                                                "latitude" to current.latitude,
                                                "longitude" to current.longitude,
                                                "source" to "app_foreground",
                                                "updatedAt" to FieldValue.serverTimestamp(),
                                            ),
                                            SetOptions.merge()
                                        )
                                        .await()
                                    db.document("tenants/$tenantId/technician_location_requests/$uid")
                                        .set(
                                            mapOf(
                                                "lastFulfilledAt" to FieldValue.serverTimestamp(),
                                                "fulfilledBy" to "app_foreground",
                                                "lastStatus" to "success",
                                                "lastError" to "",
                                            ),
                                            SetOptions.merge()
                                        )
                                        .await()
                                }.onFailure {
                                    logLocationRequestStatus(
                                        status = "write_failed",
                                        message = it.message ?: "Konum Firestore'a yazilamadi",
                                        extra = mapOf(
                                            "fineGranted" to fineGranted,
                                            "coarseGranted" to coarseGranted,
                                            "backgroundGranted" to backgroundGranted,
                                        )
                                    )
                                }
                            }
                        } else {
                            logLocationRequestStatus(
                                status = "location_unavailable",
                                message = "Konum bilgisi null dondu",
                                extra = mapOf(
                                    "fineGranted" to fineGranted,
                                    "coarseGranted" to coarseGranted,
                                    "backgroundGranted" to backgroundGranted,
                                )
                            )
                        }
                    }
                    .addOnFailureListener {
                        logLocationRequestStatus(
                            status = "location_failed",
                            message = it.message ?: "Anlik konum alinamadi",
                            extra = mapOf(
                                "fineGranted" to fineGranted,
                                "coarseGranted" to coarseGranted,
                                "backgroundGranted" to backgroundGranted,
                            )
                        )
                    }
            }
        }
            .addOnFailureListener {
                logLocationRequestStatus(
                    status = "location_failed",
                    message = it.message ?: "Son konum alinamadi",
                    extra = mapOf(
                        "fineGranted" to fineGranted,
                        "coarseGranted" to coarseGranted,
                        "backgroundGranted" to backgroundGranted,
                    )
                )
            }
    }

    LaunchedEffect(pendingLocationSend) {
        if (!pendingLocationSend) return@LaunchedEffect
        pendingLocationSend = false
        sendCurrentLocation()
    }

    val me = remember(uid, auth.currentUser?.email) {
        TechnicianIdentity(
            uid = uid,
            email = auth.currentUser?.email.orEmpty(),
            name = "",
        )
    }

    DisposableEffect(tenantId, uid) {
        var lastHandledRequestMs = 0L
        val reg = db.document("tenants/$tenantId/technician_location_requests/$uid")
            .addSnapshotListener { snapshot, error ->
                if (error != null) return@addSnapshotListener
                val requestedAt = snapshot?.getTimestamp("requestedAt")
                val requestedMs = requestedAt?.toDate()?.time ?: 0L
                if (requestedMs <= 0L) return@addSnapshotListener
                if (requestedMs <= lastHandledRequestMs) return@addSnapshotListener
                lastHandledRequestMs = requestedMs
                sendCurrentLocation()
            }
        onDispose { reg.remove() }
    }

    DisposableEffect(tenantId, uid) {
        loading = true
        loadError = ""
        val reg = db.collection("tenants").document(tenantId).collection("technician_tasks")
            .addSnapshotListener { snap, err ->
                if (err != null) {
                    loadError = "Sayaï¿½ gorevleri alinamadi: ${err.localizedMessage ?: "Hata"}"
                    loading = false
                    return@addSnapshotListener
                }
                val docs = snap?.documents.orEmpty()
                val filtered = docs.filter { row ->
                    val type = (row.getString("type") ?: "").trim()
                    val status = (row.getString("status") ?: "").trim().lowercase()
                    val assignedId = (
                        row.getString("technicianId")
                            ?: row.getString("assignedTechnicianId")
                            ?: row.getString("assignedToUid")
                            ?: row.getString("technicianUid")
                            ?: row.getString("assignedTechnicianUid")
                            ?: ""
                        ).trim()
                    val assignedName = (
                        row.getString("technicianName")
                            ?: row.getString("assignedTechnicianName")
                            ?: row.getString("assignedToName")
                            ?: ""
                        ).trim()
                    val typeOk = type == "meter_collection" || type.isBlank()
                    val statusOk = status == "assigned" || status == "in_progress"
                    typeOk && statusOk && isAssignedToMe(assignedId, assignedName, me)
                }

                val nextDevices = filtered.mapNotNull { row ->
                    val customerId = (row.getString("customerId") ?: "").trim()
                    val deviceId = (row.getString("deviceId") ?: "").trim()
                    if (customerId.isBlank() || deviceId.isBlank()) return@mapNotNull null
                    DeviceRow(
                        taskId = row.id,
                        customerId = customerId,
                        customerName = (row.getString("customerName") ?: "-").trim().ifBlank { "-" },
                        id = deviceId,
                        model = (row.getString("deviceModel") ?: "-").trim().ifBlank { "-" },
                        serialNumber = (row.getString("deviceSerialNumber") ?: "-").trim().ifBlank { "-" },
                        isColor = false,
                        bwCurrent = 0,
                        colorCurrent = 0,
                        taskStatus = (row.getString("status") ?: "").trim()
                    )
                }
                allAssignedDevices = nextDevices
                companies = nextDevices
                    .map { CustomerRow(it.customerId, it.customerName) }
                    .distinctBy { it.id }
                    .sortedBy { it.name }
                if (selectedCompanyId.isBlank() && companies.isNotEmpty()) {
                    selectedCompanyId = companies.first().id
                } else if (companies.none { it.id == selectedCompanyId }) {
                    selectedCompanyId = companies.firstOrNull()?.id.orEmpty()
                }
                loading = false
            }
        onDispose { reg.remove() }
    }

    var devices by remember { mutableStateOf<List<DeviceRow>>(emptyList()) }
    LaunchedEffect(tenantId, selectedCompanyId, allAssignedDevices) {
        if (selectedCompanyId.isBlank()) {
            devices = emptyList()
            return@LaunchedEffect
        }
        val base = allAssignedDevices.filter { it.customerId == selectedCompanyId }
        if (base.isEmpty()) {
            devices = emptyList()
            return@LaunchedEffect
        }
        try {
            devices = base.map { taskDevice ->
                val deviceSnap = db.collection("tenants").document(tenantId)
                    .collection("customers").document(selectedCompanyId)
                    .collection("devices").document(taskDevice.id)
                    .get()
                    .await()
                val counters = deviceSnap.get("currentCounters") as? Map<*, *>
                taskDevice.copy(
                    model = (deviceSnap.getString("model") ?: taskDevice.model).trim().ifBlank { taskDevice.model },
                    serialNumber = (deviceSnap.getString("serialNumber") ?: taskDevice.serialNumber).trim().ifBlank { taskDevice.serialNumber },
                    isColor = deviceSnap.getBoolean("isColor") == true,
                    bwCurrent = (counters?.get("bw") as? Number)?.toInt() ?: 0,
                    colorCurrent = (counters?.get("color") as? Number)?.toInt() ?: 0,
                )
            }.sortedBy { "${it.model} ${it.serialNumber}" }
        } catch (e: Exception) {
            loadError = "Cihazlar alinamadi: ${e.localizedMessage ?: "Hata"}"
        }
    }

    if (loading) { CircularProgressIndicator(); return }
    if (loadError.isNotBlank()) Text(loadError, color = MaterialTheme.colorScheme.error)

    Text("Sayac Gorevleri", style = MaterialTheme.typography.titleMedium)
    Spacer(Modifier.height(6.dp))
    CompanyDropdown(companies, selectedCompanyId, onSelected = { selectedCompanyId = it })
    Spacer(Modifier.height(8.dp))
    OutlinedTextField(
        value = searchText,
        onValueChange = { searchText = it },
        label = { Text("Cihaz ara (model/seri)") },
        singleLine = true,
        modifier = Modifier.fillMaxWidth()
    )
    Spacer(Modifier.height(8.dp))

    val visibleDevices = devices.filter {
        val q = searchText.trim().lowercase()
        q.isBlank() || it.model.lowercase().contains(q) || it.serialNumber.lowercase().contains(q)
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(visibleDevices, key = { "${it.taskId}_${it.id}" }) { device ->
            Card(
                modifier = Modifier.fillMaxWidth().clickable { selectedDevice = device },
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF8FAFC))
            ) {
                Column(Modifier.padding(12.dp)) {
                    Text("${device.model} - ${device.serialNumber}", fontWeight = FontWeight.SemiBold)
                    Text("Durum: ${device.taskStatus}", style = MaterialTheme.typography.bodySmall)
                    Text(if (device.isColor) "Renkli cihaz" else "S/B cihaz", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }

    selectedDevice?.let { device ->
        var bwText by remember(device.id) { mutableStateOf(device.bwCurrent.toString()) }
        var colorText by remember(device.id) { mutableStateOf(device.colorCurrent.toString()) }
        var saveError by remember(device.id) { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { selectedDevice = null },
            title = { Text("Sayac Gir") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("${device.model} - ${device.serialNumber}")
                    OutlinedTextField(
                        bwText,
                        { bwText = it.filter { ch -> ch.isDigit() } },
                        label = { Text("S/B Sayac") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth()
                    )
                    if (device.isColor) {
                        OutlinedTextField(
                            colorText,
                            { colorText = it.filter { ch -> ch.isDigit() } },
                            label = { Text("Renkli Sayac") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    if (saveError.isNotBlank()) Text(saveError, color = MaterialTheme.colorScheme.error)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val bw = bwText.toIntOrNull()
                    val color = if (device.isColor) colorText.toIntOrNull() else device.colorCurrent
                    if (bw == null) { saveError = "S/B sayac zorunlu."; return@TextButton }
                    if (device.isColor && color == null) { saveError = "Renkli sayac zorunlu."; return@TextButton }
                    if (bw < device.bwCurrent) { saveError = "S/B sayac onceki degerden kucuk olamaz."; return@TextButton }
                    if (device.isColor && color!! < device.colorCurrent) { saveError = "Renkli sayac onceki degerden kucuk olamaz."; return@TextButton }
                    saveError = ""
                    scope.launch {
                        runCatching {
                            val customerName = companies.firstOrNull { it.id == selectedCompanyId }?.name.orEmpty()
                            db.collection("tenants").document(tenantId).collection("meter_readings")
                                .add(
                                    mapOf(
                                        "tenantId" to tenantId,
                                        "customerId" to selectedCompanyId,
                                        "customerName" to customerName,
                                        "deviceId" to device.id,
                                        "deviceModel" to device.model,
                                        "deviceSerialNumber" to device.serialNumber,
                                        "date" to FieldValue.serverTimestamp(),
                                        "bwCounter" to bw,
                                        "colorCounter" to (color ?: 0),
                                        "userId" to uid,
                                        "isBilled" to false,
                                        "isColorDevice" to device.isColor,
                                        "createdAt" to FieldValue.serverTimestamp(),
                                    )
                                )
                                .await()

                            db.document("tenants/$tenantId/customers/$selectedCompanyId/devices/${device.id}")
                                .update(
                                    mapOf(
                                        "currentCounters.bw" to bw,
                                        "currentCounters.color" to (color ?: 0),
                                        "currentCounters.updatedAt" to FieldValue.serverTimestamp(),
                                    )
                                )
                                .await()

                            db.document("tenants/$tenantId/technician_tasks/${device.taskId}")
                                .update(
                                    mapOf(
                                        "status" to "completed",
                                        "meterReadingBwCounter" to bw,
                                        "meterReadingColorCounter" to (color ?: 0),
                                        "completedAt" to FieldValue.serverTimestamp(),
                                        "updatedAt" to FieldValue.serverTimestamp(),
                                    )
                                )
                                .await()
                        }.onFailure {
                            saveError = it.localizedMessage ?: "Kayit hatasi"
                            return@launch
                        }
                        selectedDevice = null
                    }
                }) { Text("Kaydet") }
            },
            dismissButton = { TextButton(onClick = { selectedDevice = null }) { Text("Iptal") } }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StatusDropdown(value: String, onValueSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
        OutlinedTextField(
            value = statusLabel(value),
            onValueChange = {},
            readOnly = true,
            label = { Text("Durum") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.menuAnchor().fillMaxWidth()
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            SERVICE_STATUS_OPTIONS.forEach { o ->
                DropdownMenuItem(text = { Text(o.label) }, onClick = { onValueSelected(o.value); expanded = false })
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CompanyDropdown(companies: List<CustomerRow>, selectedCompanyId: String, onSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val selectedLabel = companies.firstOrNull { it.id == selectedCompanyId }?.name ?: "Firma secin"
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
        OutlinedTextField(
            value = selectedLabel,
            onValueChange = {},
            readOnly = true,
            label = { Text("Firma") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.menuAnchor().fillMaxWidth()
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            companies.forEach { c ->
                DropdownMenuItem(text = { Text(c.name) }, onClick = { onSelected(c.id); expanded = false })
            }
        }
    }
}
