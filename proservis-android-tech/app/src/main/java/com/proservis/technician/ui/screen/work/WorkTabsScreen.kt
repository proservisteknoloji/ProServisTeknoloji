package com.proservis.technician.ui.screen.work

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Call
import androidx.compose.material.icons.outlined.ExitToApp
import androidx.compose.material.icons.outlined.Navigation
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.ui.text.input.KeyboardType
import com.google.firebase.firestore.FieldValue
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.draw.scale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.proservis.technician.navigation.AppNotificationTarget
import com.google.android.gms.location.LocationServices
import com.google.firebase.firestore.DocumentSnapshot
import com.google.firebase.firestore.FirebaseFirestore
import com.proservis.technician.domain.model.WorkItem
import com.proservis.technician.domain.model.WorkSource
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.text.Normalizer
import java.util.Locale

private val TopBarColor = Color(0xFF00897B)
private val PageBgColor = Color(0xFFE5E5E5)
private val CardBorderColor = Color(0xFFCDCDCD)
private val ActionButtonColor = Color(0xFF6E6E6E)
private val TabActiveColor = Color(0xFFE91E63)

private fun normalizeWorkText(value: String?): String {
    val folded = Normalizer.normalize(value.orEmpty(), Normalizer.Form.NFD)
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

private fun distinctWorkCount(rows: List<WorkItem>): Int =
    rows.distinctBy { "${it.source.name}:${it.id}" }.size

private fun serviceStatusLabel(status: String): String = when (status) {
    "Received" -> "Açıkta Bekliyor"
    "Assigned" -> "Teknisyene Atandı"
    "Musteriye Geldim" -> "Müşteriye Geldim"
    "In Progress" -> "Servise Alındı"
    "Fault Persists" -> "Arıza Devam Ediyor"
    "Waiting Approval" -> "Onay Bekliyor"
    "Waiting Part" -> "Parça Bekliyor"
    "Repaired" -> "Onarım Tamamlandı"
    "Delivery" -> "Teslimatta"
    "Delivered" -> "Servis Kapandı"
    "Closed" -> "Servis Kapandı"
    "Cancelled" -> "İptal Edildi"
    "assigned" -> "Teknisyene Atandı"
    "in_progress" -> "Servise Alındı"
    "fault_persists" -> "Arıza Devam Ediyor"
    "unassigned" -> "Açıkta Bekliyor"
    else -> status
}

private fun isMeterLikeRow(row: WorkItem): Boolean {
    if (row.source == WorkSource.METER_TASK) return true
    val rawJobType = row.jobType.orEmpty().trim()
    if (rawJobType.equals("meter_collection", ignoreCase = true)) return true
    val cType = canonicalJobType(rawJobType)
    if (cType == "meter_collection") return true

    if (row.source == WorkSource.SERVICE) {
        if (cType in setOf(
                "device_replacement",
                "service",
                "maintenance",
                "part_replacement",
                "device_delivery",
                "device_pickup",
                "toner_delivery",
                "product_transfer",
                "cargo_shipping",
                "remote_support",
                "misc"
            )
        ) {
            return false
        }
    }

    val normTitle = normalizeWorkText(row.title)
    return normTitle.contains("sayac okuma") || normTitle.contains("meter collection")
}

private fun canonicalJobType(value: String?): String {
    val raw = value.orEmpty().trim()
    if (raw.isBlank()) return "service"
    val direct = raw.lowercase(Locale.ROOT)
    if (direct in setOf("meter_collection", "metercollection")) return "meter_collection"
    if (direct in setOf("toner_delivery", "tonerdelivery")) return "toner_delivery"
    if (direct in setOf("product_transfer", "producttransfer")) return "product_transfer"
    if (direct in setOf("device_pickup", "devicepickup", "cihaz_alimi")) return "device_pickup"
    if (direct in setOf("device_delivery", "devicedelivery", "cihaz_teslimati", "cihaz_teslimati_montaj")) return "device_delivery"
    if (direct in setOf("device_replacement", "devicereplacement", "cihaz_degisimi")) return "device_replacement"
    if (direct in setOf("remote_support", "remotesupport", "uzak_baglanti")) return "remote_support"
    if (direct in setOf("cargo_shipping", "cargoshipping", "kargo_gonderimi")) return "cargo_shipping"
    if (direct in setOf("misc")) return "misc"
    if (direct in setOf("service", "service_assignment")) return "service"

    val normalized = normalizeWorkText(value)
    val token = normalized.replace(Regex("[^a-z0-9]"), "")
    return when {
        token in setOf("cihazdegisimi", "devicereplacement") ||
            normalized.contains("degisim") ||
            normalized in setOf("cihaz degisimi", "device_replacement") -> "device_replacement"
        token in setOf("cihazalimi", "devicepickup") ||
            normalized.contains("alimi") ||
            normalized in setOf("cihaz alimi", "device_pickup") -> "device_pickup"
        token in setOf("cihazteslimati", "devicedelivery", "cihazteslimatimontaj", "montaj") ||
            normalized.contains("teslimat") ||
            normalized.contains("montaj") ||
            normalized in setOf("cihaz teslimati", "device_delivery", "cihaz teslimati & montaj") -> "device_delivery"
        token in setOf("uzakbaglanti", "remotesupport", "programkurulusu") ||
            normalized.contains("uzak") ||
            normalized.contains("kurulum") -> "remote_support"
        token in setOf("tonerteslimi", "tonerdelivery", "tonerteslimati") ||
            normalized.contains("toner") -> "toner_delivery"
        token in setOf("kargogonderimi", "cargoshipping") ||
            normalized.contains("kargo") -> "cargo_shipping"
        normalized.contains("bakim") -> "maintenance"
        normalized.contains("parca") -> "part_replacement"
        token in setOf("metercollection", "sayacokuma", "sayactoplama", "sayacgorevi") ||
            normalized.contains("sayac okuma") ||
            normalized.contains("sayac gorevi") ||
            token == "sayac" || token == "meter" -> "meter_collection"
        normalized in setOf("service", "service_assignment", "ariza", "fault") ||
            normalized.contains("ariza") -> "service"
        token in setOf("urunteslimi", "producttransfer", "urunalis") ||
            normalized in setOf("urun teslimi", "urun teslimati", "urun alimi", "product_transfer") -> "product_transfer"
        normalized in setOf("misc", "muhtelif") -> "misc"
        else -> if (normalized.isBlank()) "service" else normalized
    }
}

private fun jobTypeLabel(jobType: String?): String {
    if (jobType.isNullOrBlank()) return "Arıza Servis"
    return when (canonicalJobType(jobType)) {
        "meter_collection" -> "Sayaç Okuma"
        "service" -> "Arıza Servis"
        "maintenance" -> "Periyodik Bakım"
        "part_replacement" -> "Parça Değişimi"
        "device_pickup" -> "Cihaz Alımı"
        "device_delivery" -> "Cihaz Teslimatı & Montaj"
        "device_replacement" -> "Cihaz Değişimi"
        "remote_support" -> "Uzak Bağlantı & Kurulum"
        "cargo_shipping" -> "Kargo Gönderimi"
        "toner_delivery" -> "Toner Teslimi"
        "product_transfer" -> "Ürün Teslimatı"
        "misc" -> "Muhtelif İş"
        else -> {
            val raw = jobType.trim()
            if (raw.contains(" ") || raw.any { it.isLowerCase() }) return raw
            raw.lowercase(Locale.ROOT).split(" ").joinToString(" ") { word ->
                word.replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale("tr", "TR")) else it.toString() }
            }
        }
    }
}

private fun jobTypeBadgeColors(jobType: String?): Pair<Color, Color> {
    return when (canonicalJobType(jobType)) {
        "service" -> Color(0xFFFEE2E2) to Color(0xFFDC2626) // Kırmızı (Arıza)
        "maintenance" -> Color(0xFFD1FAE5) to Color(0xFF059669) // Yeşil (Bakım)
        "device_replacement" -> Color(0xFFF3E8FF) to Color(0xFF7E22CE) // Mor (Cihaz Değişimi)
        "device_delivery" -> Color(0xFFECFDF5) to Color(0xFF047857) // Zümrüt (Teslimat & Montaj)
        "device_pickup" -> Color(0xFFE0E7FF) to Color(0xFF3730A3) // İndigo (Cihaz Alımı)
        "toner_delivery" -> Color(0xFFE0F2FE) to Color(0xFF0369A1) // Açık Mavi (Toner Teslimi)
        "part_replacement" -> Color(0xFFFEF3C7) to Color(0xFFD97706) // Amber (Parça Değişimi)
        "remote_support" -> Color(0xFFEDE9FE) to Color(0xFF6D28D9) // Menekşe (Uzak Bağlantı)
        "meter_collection" -> Color(0xFFCFFAFE) to Color(0xFF0891B2) // Camgöbeği (Sayaç)
        else -> Color(0xFFF1F5F9) to Color(0xFF475569) // Gri (Muhtelif)
    }
}

@Composable
fun WorkTabsRoute(
    notificationTarget: AppNotificationTarget? = null,
    onNotificationConsumed: () -> Unit = {},
    onNavigateSerialVerify: (serviceId: String) -> Unit,
    onNavigateCompleteService: (serviceId: String) -> Unit,
    viewModel: WorkTabsViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    WorkTabsScreen(
        state = state,
        notificationTarget = notificationTarget,
        onNotificationConsumed = onNotificationConsumed,
        onClaim = viewModel::claim,
        onRelease = viewModel::release,
        onMarkArrived = viewModel::markArrived,
        onNavigateSerialVerify = onNavigateSerialVerify,
        onNavigateCompleteService = onNavigateCompleteService,
        onCompleteMeterTask = viewModel::completeMeterTask,
        onUpdateTechnicianLocation = viewModel::updateTechnicianLocation,
        onUpdateServiceStatus = viewModel::updateServiceStatus,
        onLogout = viewModel::logout,
    )
}

@Composable
private fun WorkTabsScreen(
    state: WorkTabsUiState,
    notificationTarget: AppNotificationTarget?,
    onNotificationConsumed: () -> Unit,
    onClaim: (WorkItem) -> Unit,
    onRelease: (WorkItem) -> Unit,
    onMarkArrived: (WorkItem) -> Unit,
    onNavigateSerialVerify: (serviceId: String) -> Unit,
    onNavigateCompleteService: (serviceId: String) -> Unit,
    onCompleteMeterTask: (WorkItem, Int?, Int?, String?) -> Unit,
    onUpdateTechnicianLocation: (latitude: Double, longitude: Double) -> Unit,
    onUpdateServiceStatus: (WorkItem, String) -> Unit,
    onLogout: () -> Unit,
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(1) }
    var previousOpenCount by remember { mutableIntStateOf(0) }
    var openTabPulse by remember { mutableStateOf(false) }
    val fusedLocationClient = remember { LocationServices.getFusedLocationProviderClient(context) }
    val openBadgeCount = remember(state.openPoolItems) { distinctWorkCount(state.openPoolItems) }
    val myBadgeCount = remember(state.myItems) { distinctWorkCount(state.myItems) }

    fun sendCurrentLocation() {
        fusedLocationClient.lastLocation
            .addOnSuccessListener { location ->
                if (location != null) {
                    onUpdateTechnicianLocation(location.latitude, location.longitude)
                }
            }
    }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        val granted = result.values.any { it }
        if (granted) sendCurrentLocation()
    }
    LaunchedEffect(state.locationRequestNonce) {
        if (state.locationRequestNonce <= 0) return@LaunchedEffect
        val fineGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val coarseGranted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (fineGranted || coarseGranted) {
            sendCurrentLocation()
        } else {
            locationPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                )
            )
        }
    }

    LaunchedEffect(notificationTarget?.type, notificationTarget?.serviceId, notificationTarget?.taskId) {
        val target = notificationTarget ?: return@LaunchedEffect
        if (target.serviceId.isNotBlank() || target.taskId.isNotBlank()) {
            selectedTab = 1
        }
        onNotificationConsumed()
    }

    LaunchedEffect(openBadgeCount) {
        val nextCount = openBadgeCount
        val shouldPulse = previousOpenCount > 0 && nextCount > previousOpenCount
        previousOpenCount = nextCount
        if (!shouldPulse) return@LaunchedEffect

        repeat(6) {
            openTabPulse = !openTabPulse
            delay(240)
        }
        openTabPulse = false
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(PageBgColor)
    ) {
        val logoBitmap = rememberDecodedLogo(state.companyLogoDataUrl)
        TopBar(
            companyName = state.companyName,
            logoBitmap = logoBitmap,
            onRefresh = { sendCurrentLocation() },
            onLogout = onLogout,
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color.White)
                .padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "Teknisyen ID: ${state.session?.globalTechnicianId ?: "-"}",
                style = MaterialTheme.typography.bodySmall,
            )
            Text(
                text = if (state.companyName.isBlank()) "PROSERVIS" else state.companyName.uppercase(),
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        TabHeader(
            selectedTab = selectedTab,
            openCount = openBadgeCount,
            myCount = myBadgeCount,
            openPulse = openTabPulse && selectedTab != 0,
            onSelectTab = { selectedTab = it }
        )

        if (state.loading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
            return@Column
        }

        if (!state.errorMessage.isNullOrBlank()) {
            Text(
                text = state.errorMessage,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
            )
        }

        val rows = if (selectedTab == 0) state.openPoolItems else state.myItems
        WorkList(
            tenantId = state.session?.tenantId.orEmpty(),
            rows = rows,
            isOpenPool = selectedTab == 0,
            actionBusyId = state.actionBusyId,
            onClaim = onClaim,
            onRelease = onRelease,
            onMarkArrived = { item ->
                onMarkArrived(item)
                sendCurrentLocation()
            },
            onNavigateSerialVerify = onNavigateSerialVerify,
            onNavigateCompleteService = { serviceId ->
                onNavigateCompleteService(serviceId)
                sendCurrentLocation()
            },
            onCompleteMeterTask = { item, bw, color, note ->
                onCompleteMeterTask(item, bw, color, note)
                sendCurrentLocation()
            },
            onUpdateServiceStatus = { item, status ->
                onUpdateServiceStatus(item, status)
                sendCurrentLocation()
            },
        )
    }
}

@Composable
private fun TopBar(
    companyName: String,
    logoBitmap: ImageBitmap?,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(TopBarColor)
            .padding(horizontal = 12.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(
            modifier = Modifier.weight(1f),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (logoBitmap != null) {
                Box(
                    modifier = Modifier
                        .height(52.dp)
                        .width(92.dp),
                    contentAlignment = Alignment.CenterStart,
                ) {
                    Image(
                        bitmap = logoBitmap,
                        contentDescription = "Firma Logosu",
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Fit,
                    )
                }
            } else {
                Spacer(
                    modifier = Modifier
                        .height(52.dp)
                        .width(92.dp)
                )
            }
            Text(
                text = companyName.ifBlank { "PROSERVIS" },
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier
                    .weight(1f)
                    .padding(end = 6.dp),
                textAlign = TextAlign.End,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            IconButtonLike(icon = Icons.Outlined.Refresh, onClick = onRefresh)
            IconButtonLike(icon = Icons.Outlined.ExitToApp, onClick = onLogout)
        }
    }
}

@Composable
private fun IconButtonLike(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .size(48.dp)
            .background(Color.Transparent, RoundedCornerShape(6.dp))
            .border(1.dp, Color(0x88FFFFFF), RoundedCornerShape(6.dp)),
        contentAlignment = Alignment.Center
    ) {
        IconButton(onClick = onClick, modifier = Modifier.fillMaxSize()) {
            Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(28.dp))
        }
    }
}

@Composable
private fun TabHeader(
    selectedTab: Int,
    openCount: Int,
    myCount: Int,
    openPulse: Boolean,
    onSelectTab: (Int) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White)
            .padding(horizontal = 12.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        TabButton(
            label = "Beklemede",
            count = openCount,
            pulse = openPulse,
            active = selectedTab == 0,
            onClick = { onSelectTab(0) },
            modifier = Modifier.weight(1f)
        )
        TabButton(
            label = "Üzerimdeki İşler",
            count = myCount,
            pulse = false,
            active = selectedTab == 1,
            onClick = { onSelectTab(1) },
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun TabButton(
    label: String,
    count: Int,
    pulse: Boolean,
    active: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onClick,
        modifier = modifier
            .height(42.dp)
            .scale(if (pulse) 1.03f else 1f),
        shape = RoundedCornerShape(0.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = when {
                active -> TabActiveColor
                pulse -> Color(0xFFFF7043)
                else -> Color(0xFFBDBDBD)
            },
            contentColor = Color.White
        ),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
        ) {
            Text(
                text = label,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (count > 0) {
                Spacer(modifier = Modifier.width(8.dp))
                Box(
                    modifier = Modifier
                        .widthIn(min = 26.dp)
                        .background(Color.White, RoundedCornerShape(999.dp))
                        .border(1.dp, Color(0x33FFFFFF), RoundedCornerShape(999.dp))
                        .padding(horizontal = 8.dp, vertical = 2.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = count.toString(),
                        color = when {
                            active -> TabActiveColor
                            pulse -> Color(0xFFFF7043)
                            else -> Color(0xFF616161)
                        },
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}



@Composable
private fun WorkList(
    tenantId: String,
    rows: List<WorkItem>,
    isOpenPool: Boolean,
    actionBusyId: String?,
    onClaim: (WorkItem) -> Unit,
    onRelease: (WorkItem) -> Unit,
    onMarkArrived: (WorkItem) -> Unit,
    onNavigateSerialVerify: (serviceId: String) -> Unit,
    onNavigateCompleteService: (serviceId: String) -> Unit,
    onCompleteMeterTask: (WorkItem, Int?, Int?, String?) -> Unit,
    onUpdateServiceStatus: (WorkItem, String) -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val db = remember { FirebaseFirestore.getInstance() }
    var meterDialogItem by remember { mutableStateOf<WorkItem?>(null) }
    var pendingPhoneNumber by remember { mutableStateOf<String?>(null) }
    val callPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        val phone = pendingPhoneNumber
        pendingPhoneNumber = null
        if (phone.isNullOrBlank()) return@rememberLauncherForActivityResult
        val callUri = Uri.parse("tel:$phone")
        if (granted) {
            context.startActivity(Intent(Intent.ACTION_CALL, callUri))
        } else {
            context.startActivity(Intent(Intent.ACTION_DIAL, callUri))
        }
    }

    fun pickPhoneFromSnap(snap: DocumentSnapshot): String? {
        val keys = listOf(
            "phone",
            "mobile",
            "telephone",
            "customerPhone",
            "customerPhoneNumber",
            "contactPhone",
            "contactNumber",
            "locationPhone",
            "customer.phone",
            "location.phone",
            "contact.phone",
        )
        return keys.firstNotNullOfOrNull { key ->
            when (val raw = snap.get(key)) {
                is String -> raw.trim().takeIf { it.isNotBlank() }
                is Number -> raw.toLong().toString()
                else -> null
            }
        }
    }

    fun normalizeForDial(raw: String): String {
        val digits = raw.replace(Regex("[^0-9]"), "")
        if (digits.isBlank()) return ""
        return when {
            digits.startsWith("90") && digits.length == 12 -> "0" + digits.substring(2)
            digits.length == 10 -> "0$digits"
            else -> digits
        }
    }

    fun chooseBestPhone(candidates: List<String>): String? {
        val normalized = candidates
            .map { normalizeForDial(it) }
            .filter { it.isNotBlank() }
            .distinct()
        if (normalized.isEmpty()) return null
        return normalized.maxWithOrNull(compareBy<String> { it.length }.thenBy { it })?.takeIf { it.isNotBlank() }
    }

    suspend fun resolvePhoneForRow(row: WorkItem): String? {
        val candidates = mutableListOf<String>()
        row.contactPhone?.trim()?.takeIf { it.isNotBlank() }?.let { candidates.add(it) }
        if (tenantId.isBlank()) return chooseBestPhone(candidates)

        // 1) Servis kaydından tüm olası telefonları topla
        runCatching {
            db.document("tenants/$tenantId/service_records/${row.id}").get().await()
        }.getOrNull()?.let { serviceSnap ->
            pickPhoneFromSnap(serviceSnap)?.let { candidates.add(it) }
        }

        // 2) Müşteri kartından dene
        val customerId = row.customerId?.trim().orEmpty()
        if (customerId.isNotBlank()) {
            runCatching {
                db.document("tenants/$tenantId/customers/$customerId").get().await()
            }.getOrNull()?.let { customerSnap ->
                pickPhoneFromSnap(customerSnap)?.let { candidates.add(it) }
            }
        }
        return chooseBestPhone(candidates)
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(rows, key = { it.source.name + it.id }) { row ->
            val isMeterGroup = isMeterLikeRow(row)
            val jobTypeCanonical = canonicalJobType(row.jobType)
            val isServiceGroup = row.source == WorkSource.SERVICE && !isMeterGroup && (jobTypeCanonical in setOf("service", "maintenance", "part_replacement", "device_replacement", "remote_support"))
            val isDeliveryTask = !isMeterGroup && !isServiceGroup
            val primaryActionLabel = when {
                isOpenPool -> "İşi Sahiplen"
                isServiceGroup -> "Servise Başla"
                isMeterGroup -> "Sayaç Gir ve Kaydet"
                else -> "Görev / Teslim Ekranı"
            }

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color.White)
                    .border(1.dp, CardBorderColor, RoundedCornerShape(12.dp))
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = row.customerName,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleMedium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    val (badgeBg, badgeText) = jobTypeBadgeColors(if (isMeterGroup) "meter_collection" else row.jobType)
                    val displayJobType = if (isMeterGroup) "Sayaç Okuma" else jobTypeLabel(row.jobType)
                    Box(
                        modifier = Modifier
                            .background(badgeBg, RoundedCornerShape(6.dp))
                            .padding(horizontal = 8.dp, vertical = 3.dp)
                    ) {
                        Text(
                            text = displayJobType,
                            color = badgeText,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }

                if (row.locationText.isNotBlank()) {
                    DetailLine(text = "📍 Konum: ${row.locationText}")
                }

                DetailLine(text = "🖨️ Cihaz: ${row.title}")
                if (!row.serialNumber.isNullOrBlank()) {
                    DetailLine(text = "🔢 Seri No: ${row.serialNumber}")
                }

                if (!row.problemDescription.isNullOrBlank()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFFFFF3E0), RoundedCornerShape(6.dp))
                            .border(1.dp, Color(0xFFFFB74D), RoundedCornerShape(6.dp))
                            .padding(10.dp)
                    ) {
                        Column {
                            Text(
                                text = "BİLDİRİLEN ARIZA / SORUN TANIMI:",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFFE65100)
                            )
                            Text(
                                text = row.problemDescription.orEmpty(),
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color(0xFF212121),
                                modifier = Modifier.padding(top = 3.dp)
                            )
                        }
                    }
                }

                Text(
                    text = "Durum: ${serviceStatusLabel(row.status)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = when (row.status) {
                        "Musteriye Geldim" -> Color(0xFF0284C7)
                        "In Progress", "in_progress" -> Color(0xFFD97706)
                        "Fault Persists", "fault_persists" -> Color(0xFFDC2626)
                        "Repaired", "Delivered", "Closed" -> Color(0xFF059669)
                        else -> Color(0xFF00897B)
                    },
                    fontWeight = FontWeight.Bold,
                )

                val isBusy = actionBusyId == row.id
                val isArrived = row.status == "Musteriye Geldim" || row.status == "In Progress" || row.status == "in_progress"

                if (!isOpenPool && row.source == WorkSource.SERVICE && !isArrived) {
                    Button(
                        onClick = { onMarkArrived(row) },
                        enabled = !isBusy,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(40.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF0284C7),
                            contentColor = Color.White
                        ),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            text = "📍 Müşteriye Geldim (Konum Damgala)",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    MiniActionButton(
                        label = "Ara",
                        modifier = Modifier.weight(1f),
                        onClick = {
                            scope.launch {
                                val phone = resolvePhoneForRow(row)
                                if (phone.isNullOrBlank()) {
                                    Toast.makeText(context, "Telefon numarasi bulunamadi.", Toast.LENGTH_SHORT).show()
                                    return@launch
                                }
                                val callUri = Uri.parse("tel:$phone")
                                val granted = ContextCompat.checkSelfPermission(
                                    context,
                                    Manifest.permission.CALL_PHONE
                                ) == PackageManager.PERMISSION_GRANTED
                                if (granted) {
                                    context.startActivity(Intent(Intent.ACTION_CALL, callUri))
                                } else {
                                    pendingPhoneNumber = phone
                                    callPermissionLauncher.launch(Manifest.permission.CALL_PHONE)
                                }
                            }
                        },
                    )
                    MiniActionButton(
                        label = "Yol",
                        modifier = Modifier.weight(1f),
                        enabled = row.locationText.isNotBlank() || row.customerName.isNotBlank(),
                        onClick = {
                            val targetAddress = row.locationText.ifBlank { row.customerName }
                            if (targetAddress.isNotBlank()) {
                                val query = Uri.encode(targetAddress)
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=$query"))
                                context.startActivity(intent)
                            }
                        },
                    )
                    MiniActionButton(
                        label = primaryActionLabel,
                        modifier = Modifier.weight(1.45f),
                        enabled = !isBusy,
                        primary = true,
                        onClick = {
                            when {
                                isOpenPool -> onClaim(row)
                                isServiceGroup -> onNavigateSerialVerify(row.id)
                                isMeterGroup -> meterDialogItem = row
                                else -> onNavigateCompleteService(row.id)
                            }
                        },
                    )
                }

                if (!isOpenPool) {
                    TextButton(
                        onClick = { onRelease(row) },
                        enabled = !isBusy,
                        modifier = Modifier.align(Alignment.End),
                    ) {
                        Text("Atamayı İptal Et")
                    }
                }
            }
        }
    }

    meterDialogItem?.let { item ->
        CustomerMeterCollectionDialog(
            item = item,
            tenantId = tenantId,
            onDismiss = { meterDialogItem = null },
            onFinishCollection = {
                onCompleteMeterTask(item, null, null, "Sayaç okuma tamamlandı")
                meterDialogItem = null
            },
        )
    }
}

@Composable
private fun ActionButton(
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp),
        shape = RoundedCornerShape(0.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = ActionButtonColor,
            contentColor = Color.White,
            disabledContainerColor = Color(0xFFA9A9A9),
            disabledContentColor = Color.White,
        ),
    ) {
        Text(text = label, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun DetailLine(text: String) {
    Text(
        text = text,
        color = Color(0xFF666666),
        style = MaterialTheme.typography.bodyMedium,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
    )
}

@Composable
private fun MiniActionButton(
    label: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    primary: Boolean = false,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.height(44.dp),
        shape = RoundedCornerShape(10.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (primary) TopBarColor else Color(0xFFF1F1F1),
            contentColor = if (primary) Color.White else Color(0xFF3F3F3F),
            disabledContainerColor = Color(0xFFD9D9D9),
            disabledContentColor = Color(0xFF7E7E7E),
        ),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 8.dp),
    ) {
        Text(
            text = label,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            fontWeight = if (primary) FontWeight.SemiBold else FontWeight.Medium,
        )
    }
}

@Composable
private fun SmallActionIconButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    enabled: Boolean = true,
    onClick: () -> Unit,
) {
    Box(
        modifier = Modifier
            .size(42.dp)
            .border(1.dp, Color(0xFFBDBDBD), RoundedCornerShape(6.dp)),
        contentAlignment = Alignment.Center
    ) {
        IconButton(onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxSize()) {
            Icon(
                imageVector = icon,
                contentDescription = contentDescription,
                tint = if (enabled) Color(0xFF444444) else Color(0xFFBDBDBD),
                modifier = Modifier.size(24.dp),
            )
        }
    }
}

internal data class CustomerDeviceItem(
    val id: String,
    val model: String,
    val serialNumber: String,
    val isColor: Boolean,
    val lastBw: Int?,
    val lastColor: Int?,
    val isDone: Boolean = false,
)

@Composable
private fun CustomerMeterCollectionDialog(
    item: WorkItem,
    tenantId: String,
    onDismiss: () -> Unit,
    onFinishCollection: () -> Unit,
) {
    val db = remember { FirebaseFirestore.getInstance() }
    var devices by remember { mutableStateOf<List<CustomerDeviceItem>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var resolvedCustomerId by remember(item.id) { mutableStateOf(item.customerId.orEmpty().trim()) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(item.customerId, item.customerName) {
        loading = true
        val customerId = item.customerId.orEmpty().trim()
        val customerName = item.customerName.orEmpty().trim()
        resolvedCustomerId = customerId
        var list = emptyList<CustomerDeviceItem>()
        if (customerId.isNotBlank()) {
            runCatching {
                db.collection("tenants/$tenantId/customers/$customerId/devices").get().await()
            }.onSuccess { snap ->
                list = snap.documents.map { doc ->
                    CustomerDeviceItem(
                        id = doc.id,
                        model = doc.getString("model") ?: doc.getString("deviceModel") ?: "Cihaz",
                        serialNumber = doc.getString("serialNumber") ?: doc.getString("serial") ?: doc.id,
                        isColor = doc.getBoolean("isColor") ?: false,
                        lastBw = (doc.get("currentCounters.bw") as? Number)?.toInt() ?: (doc.get("bwCounter") as? Number)?.toInt(),
                        lastColor = (doc.get("currentCounters.color") as? Number)?.toInt() ?: (doc.get("colorCounter") as? Number)?.toInt(),
                    )
                }
            }
        }
        if (list.isEmpty() && customerName.isNotBlank() && customerName != "-") {
            runCatching {
                db.collection("tenants/$tenantId/customers")
                    .whereEqualTo("name", customerName)
                    .get().await()
            }.onSuccess { custSnap ->
                val realCustId = custSnap.documents.firstOrNull()?.id
                if (!realCustId.isNullOrBlank()) {
                    resolvedCustomerId = realCustId
                    runCatching {
                        db.collection("tenants/$tenantId/customers/$realCustId/devices").get().await()
                    }.onSuccess { snap ->
                        list = snap.documents.map { doc ->
                            CustomerDeviceItem(
                                id = doc.id,
                                model = doc.getString("model") ?: doc.getString("deviceModel") ?: "Cihaz",
                                serialNumber = doc.getString("serialNumber") ?: doc.getString("serial") ?: doc.id,
                                isColor = doc.getBoolean("isColor") ?: false,
                                lastBw = (doc.get("currentCounters.bw") as? Number)?.toInt() ?: (doc.get("bwCounter") as? Number)?.toInt(),
                                lastColor = (doc.get("currentCounters.color") as? Number)?.toInt() ?: (doc.get("colorCounter") as? Number)?.toInt(),
                            )
                        }
                    }
                }
            }
        }
        val targetMeterDeviceIds = (item.selectedMeterDeviceIds?.filter { it.isNotBlank() } ?: emptyList()).ifEmpty {
            listOfNotNull(item.deviceId?.takeIf { it.isNotBlank() })
        }
        if (targetMeterDeviceIds.isNotEmpty()) {
            list = list.filter { dev -> targetMeterDeviceIds.contains(dev.id) }
        }
        devices = list
        loading = false
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Column {
                Text("Müşteri Sayaç Okuma", fontWeight = FontWeight.Bold)
                Text("Müşteri: ${item.customerName}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF666666))
            }
        },
        text = {
            if (loading) {
                Box(modifier = Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else if (devices.isEmpty()) {
                Text("Müşteriye ait sistemde kayıtlı cihaz bulunamadı.")
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(devices.filter { !it.isDone }, key = { it.id }) { dev ->
                        var bwInput by remember(dev.id) { mutableStateOf("") }
                        var colorInput by remember(dev.id) { mutableStateOf("") }
                        var devError by remember(dev.id) { mutableStateOf<String?>(null) }
                        var devSaving by remember(dev.id) { mutableStateOf(false) }

                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp),
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFF9F9F9))
                        ) {
                            Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text("${dev.model} (${dev.serialNumber})", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                Text("Son S/B: ${dev.lastBw ?: "-"}" + if (dev.isColor) " | Son Renkli: ${dev.lastColor ?: "-"}" else "", style = MaterialTheme.typography.bodySmall)

                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedTextField(
                                        value = bwInput,
                                        onValueChange = { bwInput = it; devError = null },
                                        label = { Text("Yeni S/B") },
                                        modifier = Modifier.weight(1f),
                                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                                    )
                                    if (dev.isColor) {
                                        OutlinedTextField(
                                            value = colorInput,
                                            onValueChange = { colorInput = it; devError = null },
                                            label = { Text("Yeni Renkli") },
                                            modifier = Modifier.weight(1f),
                                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                                        )
                                    }
                                }
                                if (devError != null) {
                                    Text(devError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                                }
                                Button(
                                    onClick = {
                                        val bw = bwInput.trim().toIntOrNull()
                                        val color = if (dev.isColor) colorInput.trim().toIntOrNull() else null
                                        if (bw == null) { devError = "S/B sayaç giriniz"; return@Button }
                                        if (dev.lastBw != null && bw < dev.lastBw) { devError = "S/B sayaç düşük olamaz"; return@Button }
                                        if (dev.isColor && color == null) { devError = "Renkli sayaç giriniz"; return@Button }
                                        if (dev.isColor && dev.lastColor != null && color != null && color < dev.lastColor) { devError = "Renkli sayaç düşük olamaz"; return@Button }

                                        scope.launch {
                                            devSaving = true
                                            runCatching {
                                                val customerId = resolvedCustomerId.ifBlank { item.customerId.orEmpty().trim() }
                                                val custName = item.customerName.ifBlank { "Müşteri" }
                                                val devModel = dev.model
                                                val devSerial = dev.serialNumber
                                                val isColorDev = dev.isColor
                                                if (customerId.isBlank()) throw IllegalStateException("Musteri kaydi bulunamadi.")
                                                db.document("tenants/$tenantId/customers/$customerId/devices/${dev.id}").update(
                                                    mapOf(
                                                        "currentCounters.bw" to bw,
                                                        "currentCounters.color" to (color ?: 0),
                                                        "currentCounters.updatedAt" to FieldValue.serverTimestamp(),
                                                    )
                                                ).await()
                                                db.collection("tenants/$tenantId/meter_readings").add(
                                                    mapOf(
                                                        "tenantId" to tenantId,
                                                        "customerId" to customerId,
                                                        "customerName" to custName,
                                                        "deviceId" to dev.id,
                                                        "deviceModel" to devModel,
                                                        "deviceSerialNumber" to devSerial,
                                                        "isColorDevice" to isColorDev,
                                                        "bwCounter" to bw,
                                                        "colorCounter" to (color ?: 0),
                                                        "date" to FieldValue.serverTimestamp(),
                                                        "readAt" to FieldValue.serverTimestamp(),
                                                        "createdAt" to FieldValue.serverTimestamp(),
                                                        "isBilled" to false,
                                                        "entrySource" to "technician_app",
                                                        "source" to "technician_app",
                                                    )
                                                ).await()
                                            }.onSuccess {
                                                devices = devices.map { d -> if (d.id == dev.id) d.copy(isDone = true) else d }
                                            }.onFailure { err ->
                                                devError = err.message ?: "Kayıt hatası"
                                            }
                                            devSaving = false
                                        }
                                    },
                                    enabled = !devSaving,
                                    modifier = Modifier.align(Alignment.End),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF00897B))
                                ) {
                                    Text("SAYAÇ KAYDET")
                                }
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = onFinishCollection,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF059669))
            ) {
                Text("SAYAÇ OKUMAYI TAMAMLA", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Kapat") }
        }
    )
}

@Composable
private fun rememberDecodedLogo(dataUrl: String): ImageBitmap? {
    val normalized = dataUrl.trim()
    return remember(normalized) {
        if (normalized.isBlank()) return@remember null
        val encoded = if (normalized.startsWith("data:image")) {
            val base64Index = normalized.indexOf("base64,")
            if (base64Index < 0) return@remember null
            normalized.substring(base64Index + 7)
        } else {
            normalized
        }
        runCatching {
            val bytes = Base64.decode(encoded, Base64.DEFAULT)
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
        }.getOrNull()
    }
}


