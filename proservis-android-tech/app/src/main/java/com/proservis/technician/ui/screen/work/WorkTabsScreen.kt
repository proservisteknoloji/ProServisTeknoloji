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
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.android.gms.location.LocationServices
import com.google.firebase.firestore.FirebaseFirestore
import com.proservis.technician.domain.model.WorkItem
import com.proservis.technician.domain.model.WorkSource
import com.proservis.technician.domain.model.MeterReadingInput
import com.proservis.technician.navigation.AppNotificationTarget
import com.proservis.technician.ui.components.StitchCircleIconButton
import com.proservis.technician.ui.components.StitchStatusBadge
import com.proservis.technician.ui.screen.meter.CustomerMeterReadingSheet
import com.proservis.technician.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.text.Normalizer
import java.util.Locale

private fun normalizeWorkText(value: String?): String =
    Normalizer.normalize(value.orEmpty(), Normalizer.Form.NFD)
        .replace("\\p{InCombiningDiacriticalMarks}+".toRegex(), "")
        .lowercase(Locale.ROOT)
        .trim()

private fun distinctWorkCount(rows: List<WorkItem>): Int =
    rows.distinctBy { "${it.source.name}:${it.id}" }.size

private fun isMeterLikeRow(row: WorkItem): Boolean {
    if (row.source == WorkSource.METER_TASK) return true
    val jobType = normalizeWorkText(row.jobType)
    val title = normalizeWorkText(row.title)
    val description = normalizeWorkText(row.problemDescription)
    return jobType.contains("meter") ||
        jobType.contains("sayac") ||
        title.contains("meter") ||
        title.contains("sayac") ||
        description.contains("meter") ||
        description.contains("sayac")
}

private fun canonicalJobType(value: String?): String {
    val normalized = normalizeWorkText(value)
    val token = normalized.replace(Regex("[^a-z0-9]"), "")
    return when {
        token in setOf("metercollection", "sayacokuma", "sayactoplama", "sayacgorevi") ||
            normalized.contains("meter") || normalized.contains("sayac") -> "meter_collection"
        token in setOf("tonerdelivery", "tonerteslimi") -> "toner_delivery"
        token in setOf("devicereplacement", "cihazdegisimi") -> "device_replacement"
        token in setOf("devicedelivery", "cihazteslimati") -> "device_delivery"
        token in setOf("devicepickup", "cihazalimi") -> "device_pickup"
        token in setOf("cargoshipping", "kargogonderimi") -> "cargo_shipping"
        token in setOf("producttransfer", "urunteslimi", "urunteslimati") -> "product_transfer"
        token in setOf("misc", "muhtelif") -> "misc"
        normalized.isBlank() || token in setOf("service", "serviceassignment", "ariza", "fault") -> "service"
        else -> normalized
    }
}

private fun jobTypeLabel(jobType: String?): String = when (canonicalJobType(jobType)) {
    "meter_collection" -> "Sayaç Okuma"
    "service" -> "Arıza Servis"
    "device_pickup" -> "Cihaz Alımı"
    "device_delivery" -> "Cihaz Teslimatı"
    "device_replacement" -> "Cihaz Değişimi"
    "cargo_shipping" -> "Kargo Gönderimi"
    "toner_delivery" -> "Toner Teslimi"
    "product_transfer" -> "Ürün Teslimatı"
    "misc" -> "Muhtelif İş"
    else -> jobType?.trim().orEmpty().ifBlank { "Arıza Servis" }
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
    onCompleteMeterTask: (WorkItem, List<MeterReadingInput>, String?) -> Unit,
    onUpdateTechnicianLocation: (latitude: Double, longitude: Double) -> Unit,
    onUpdateServiceStatus: (WorkItem, String) -> Unit,
    onLogout: () -> Unit,
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(1) } // 0: Havuz, 1: Atanmış İşler
    var meterSheetItem by remember { mutableStateOf<WorkItem?>(null) }
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

    LaunchedEffect(notificationTarget?.type, notificationTarget?.serviceId, notificationTarget?.taskId) {
        val target = notificationTarget ?: return@LaunchedEffect
        if (target.serviceId.isNotBlank() || target.taskId.isNotBlank()) {
            selectedTab = 1
        }
        onNotificationConsumed()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Surface)
            .statusBarsPadding()
            .navigationBarsPadding(),
    ) {
        // App Top Bar (Stitch Standartları)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Surface)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(
                    text = state.companyName.ifBlank { "Proservis Teknisyen" },
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = PrimaryContainer
                )
                Text(
                    text = "Teknisyen: ${state.session?.technicianName?.ifBlank { state.session.email } ?: "Aktif"}",
                    fontSize = 12.sp,
                    color = OnSurfaceVariant
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                IconButton(onClick = { sendCurrentLocation() }) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = PrimaryContainer)
                }
                IconButton(onClick = onLogout) {
                    Icon(Icons.Outlined.ExitToApp, contentDescription = "Çıkış", tint = Error)
                }
            }
        }

        // Segmented Tab Selector (Ergonomic High Contrast)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 6.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(SurfaceContainerHigh)
                .padding(4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            // Atanmış İşler Tab
            Button(
                onClick = { selectedTab = 1 },
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (selectedTab == 1) PrimaryContainer else Color.Transparent,
                    contentColor = if (selectedTab == 1) OnPrimary else OnSurfaceVariant
                ),
                elevation = if (selectedTab == 1) ButtonDefaults.buttonElevation(defaultElevation = 2.dp) else ButtonDefaults.buttonElevation(0.dp),
                modifier = Modifier.weight(1f).height(44.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Outlined.Engineering, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Atanmış İşler", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Spacer(Modifier.width(6.dp))
                    Box(
                        modifier = Modifier
                            .clip(CircleShape)
                            .background(if (selectedTab == 1) SurfaceContainerLowest else SurfaceContainer)
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = myBadgeCount.toString(),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (selectedTab == 1) PrimaryContainer else OnSurfaceVariant
                        )
                    }
                }
            }

            // Açıkta Bekleyen Tab
            Button(
                onClick = { selectedTab = 0 },
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (selectedTab == 0) PrimaryContainer else Color.Transparent,
                    contentColor = if (selectedTab == 0) OnPrimary else OnSurfaceVariant
                ),
                elevation = if (selectedTab == 0) ButtonDefaults.buttonElevation(defaultElevation = 2.dp) else ButtonDefaults.buttonElevation(0.dp),
                modifier = Modifier.weight(1f).height(44.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Outlined.Inbox, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Açık Havuz", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    Spacer(Modifier.width(6.dp))
                    Box(
                        modifier = Modifier
                            .clip(CircleShape)
                            .background(if (selectedTab == 0) SurfaceContainerLowest else ErrorContainer)
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = openBadgeCount.toString(),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (selectedTab == 0) PrimaryContainer else OnErrorContainer
                        )
                    }
                }
            }
        }

        if (state.loading) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = PrimaryContainer)
            }
            return@Column
        }

        val rows = if (selectedTab == 0) state.openPoolItems else state.myItems

        if (rows.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = if (selectedTab == 0) "Açıkta bekleyen iş emri bulunmuyor." else "Üzerinizde aktif bir iş emri bulunmuyor.",
                    color = OnSurfaceVariant,
                    fontSize = 14.sp
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(vertical = 10.dp)
            ) {
                items(rows, key = { it.source.name + ":" + it.id }) { item ->
                    val isLocallyArrived = state.arrivedItemIds.contains(item.id)
                    val statusLower = item.status.lowercase(Locale.ROOT)
                    val isArrived = item.isArrived || isLocallyArrived ||
                        statusLower in setOf("musteriye geldim", "in progress", "in_progress", "waiting part", "waiting approval", "islemde")
                    StitchWorkOrderCard(
                        item = item,
                        isOpenPool = selectedTab == 0,
                        actionBusy = state.actionBusyId == item.id,
                        isArrived = isArrived,
                        tenantId = state.session?.tenantId.orEmpty(),
                        onClaim = { onClaim(item) },
                        onMarkArrived = {
                            onMarkArrived(item)
                            sendCurrentLocation()
                        },
                        onStartService = {
                            if (isMeterLikeRow(item)) {
                                meterSheetItem = item
                            } else {
                                onNavigateCompleteService(item.id)
                            }
                            sendCurrentLocation()
                        }
                    )
                }
            }
        }
    }

    // Sayaç Okuma Tam Sayfa Sheet'i
    meterSheetItem?.let { item ->
        CustomerMeterReadingSheet(
            item = item,
            tenantId = state.session?.tenantId.orEmpty(),
            onDismiss = { meterSheetItem = null },
            onCompleteTask = { readings, note ->
                onCompleteMeterTask(item, readings, note)
                meterSheetItem = null
            }
        )
    }
}

@Composable
private fun StitchWorkOrderCard(
    item: WorkItem,
    isOpenPool: Boolean,
    actionBusy: Boolean,
    isArrived: Boolean,
    tenantId: String,
    onClaim: () -> Unit,
    onMarkArrived: () -> Unit,
    onStartService: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val isMeter = isMeterLikeRow(item)

    // Kritik Kural: "Müşteriye Geldim" yapılmadan "Servise Başla" aktif olamaz!
    val canStartService = isArrived || isMeter // Sayaç toplama işlerinde doğrudan başlanabilir

    val (badgeText, badgeDotColor, badgeBg) = when {
        isMeter -> Triple("Sayaç", Secondary, SecondaryFixed)
        item.jobType?.contains("toner", ignoreCase = true) == true -> Triple("Toner", Secondary, SecondaryFixed)
        item.jobType?.contains("bakim", ignoreCase = true) == true || item.jobType?.contains("maintenance", ignoreCase = true) == true -> Triple("Bakım", TertiaryContainer, TertiaryFixed)
        item.jobType?.contains("montaj", ignoreCase = true) == true || item.jobType?.contains("delivery", ignoreCase = true) == true -> Triple("Teslimat", PrimaryContainer, PrimaryFixed)
        else -> Triple("Arıza", Error, ErrorContainer)
    }

    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceContainerLowest),
        border = BorderStroke(1.dp, OutlineVariant.copy(alpha = 0.4f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // Header: İş No, Müşteri Adı, Durum Rozeti
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "İş Emri #${item.id.takeLast(6).uppercase()}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Secondary,
                        letterSpacing = 0.5.sp
                    )
                    Text(
                        text = item.customerName,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = OnSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    if (item.locationText.isNotBlank()) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            modifier = Modifier.padding(top = 2.dp)
                        ) {
                            Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = Outline, modifier = Modifier.size(14.dp))
                            Text(
                                text = item.locationText,
                                fontSize = 12.sp,
                                color = OnSurfaceVariant,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    }
                }

                StitchStatusBadge(
                    text = badgeText,
                    dotColor = badgeDotColor,
                    containerColor = badgeBg,
                    contentColor = OnSurface
                )
            }

            // Hızlı Ara & Navigasyon Kısayolları (Telefon ve Adres varsa)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                val phone = item.contactPhone
                if (!phone.isNullOrBlank()) {
                    OutlinedButton(
                        onClick = {
                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone"))
                            context.startActivity(intent)
                        },
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.height(36.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 0.dp),
                        border = BorderStroke(1.dp, PrimaryContainer.copy(alpha = 0.3f))
                    ) {
                        Icon(Icons.Outlined.Call, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Ara", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = PrimaryContainer)
                    }
                }

                if (item.locationText.isNotBlank()) {
                    OutlinedButton(
                        onClick = {
                            val uri = Uri.parse("geo:0,0?q=" + Uri.encode(item.locationText))
                            val intent = Intent(Intent.ACTION_VIEW, uri)
                            context.startActivity(intent)
                        },
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.height(36.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 0.dp),
                        border = BorderStroke(1.dp, Secondary.copy(alpha = 0.3f))
                    ) {
                        Icon(Icons.Outlined.Directions, contentDescription = null, tint = Secondary, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Yol Tarifi", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = Secondary)
                    }
                }
            }

            // Cihaz ve Problem Tanımı Kutusu
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(10.dp))
                    .background(SurfaceContainerLow)
                    .padding(10.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(Icons.Outlined.Print, contentDescription = null, tint = Secondary, modifier = Modifier.size(16.dp))
                        Text(
                            text = "Cihaz: ${item.title}",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = OnSurface,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    if (!item.problemDescription.isNullOrBlank()) {
                        Text(
                            text = item.problemDescription.orEmpty(),
                            fontSize = 12.sp,
                            color = OnSurfaceVariant,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                            lineHeight = 16.sp
                        )
                    }
                }
            }

            // Aksiyon Butonları (Stitch Şartlı Akışı)
            if (isOpenPool) {
                Button(
                    onClick = onClaim,
                    enabled = !actionBusy,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = PrimaryContainer,
                        contentColor = OnPrimary
                    )
                ) {
                    Text("İşi Üzerime Al", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Sol Buton: Müşteriye Geldim
                    if (!isArrived) {
                        Button(
                            onClick = onMarkArrived,
                            enabled = !actionBusy,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier
                                .weight(1f)
                                .height(50.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = SurfaceContainerHigh,
                                contentColor = Secondary
                            )
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.Center
                            ) {
                                Icon(Icons.Outlined.LocationOn, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("Müşteriye Geldim", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    } else {
                        // Varış tamamlanmışsa yeşil onay göstergesi
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .height(50.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(TertiaryContainer),
                            contentAlignment = Alignment.Center
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.Center
                            ) {
                                Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = OnTertiaryContainer, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("Müşteridesiniz ✓", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = OnTertiaryContainer)
                            }
                        }
                    }

                    // Sağ Buton: Servise Başla (Müşteriye Geldim olmadan pasif!)
                    Button(
                        onClick = onStartService,
                        enabled = canStartService && !actionBusy,
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .weight(1f)
                            .height(50.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = PrimaryContainer,
                            contentColor = OnPrimary,
                            disabledContainerColor = SurfaceContainerHigh.copy(alpha = 0.6f),
                            disabledContentColor = OutlineVariant
                        )
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Text(
                                text = if (isMeter) "Sayaçları Gir" else "Servise Başla",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Spacer(Modifier.width(4.dp))
                            Icon(Icons.Outlined.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
        }
    }
}
