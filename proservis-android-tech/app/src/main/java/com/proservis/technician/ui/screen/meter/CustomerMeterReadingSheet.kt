package com.proservis.technician.ui.screen.meter

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Print
import androidx.compose.material.icons.outlined.Speed
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.proservis.technician.domain.model.WorkItem
import com.proservis.technician.domain.model.MeterReadingInput
import com.proservis.technician.ui.components.StitchCounterDeltaBadge
import com.proservis.technician.ui.components.StitchStatusBadge
import com.proservis.technician.ui.theme.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

data class MeterDeviceEntry(
    val id: String,
    val model: String,
    val serialNumber: String,
    val isColor: Boolean,
    val lastBw: Int?,
    val lastColor: Int?,
    var newBw: String = "",
    var newColor: String = "",
    var isSaved: Boolean = false,
)

@Composable
fun CustomerMeterReadingSheet(
    item: WorkItem,
    tenantId: String,
    onDismiss: () -> Unit,
    onCompleteTask: (readings: List<MeterReadingInput>, note: String?) -> Unit,
) {
    val db = remember { FirebaseFirestore.getInstance() }
    val scope = rememberCoroutineScope()
    var loading by remember { mutableStateOf(true) }
    var devices by remember { mutableStateOf<List<MeterDeviceEntry>>(emptyList()) }
    var resolvedCustomerId by remember(item.id) { mutableStateOf(item.customerId.orEmpty().trim()) }
    var selectedTab by remember { mutableIntStateOf(0) } // 0: Okunacaklar, 1: Tamamlananlar

    LaunchedEffect(item.customerId, item.customerName) {
        loading = true
        val customerId = item.customerId.orEmpty().trim()
        val customerName = item.customerName.orEmpty().trim()
        resolvedCustomerId = customerId
        var list = emptyList<MeterDeviceEntry>()

        if (customerId.isNotBlank()) {
            runCatching {
                db.collection("tenants/$tenantId/customers/$customerId/devices").get().await()
            }.onSuccess { snap ->
                list = snap.documents.map { doc ->
                    MeterDeviceEntry(
                        id = doc.id,
                        model = doc.getString("model") ?: doc.getString("deviceModel") ?: "Yazıcı",
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
                            MeterDeviceEntry(
                                id = doc.id,
                                model = doc.getString("model") ?: doc.getString("deviceModel") ?: "Yazıcı",
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

        val targetIds = (item.selectedMeterDeviceIds?.filter { it.isNotBlank() } ?: emptyList()).ifEmpty {
            listOfNotNull(item.deviceId?.takeIf { it.isNotBlank() })
        }
        if (targetIds.isNotEmpty()) {
            list = list.filter { targetIds.contains(it.id) }
        }
        devices = list
        loading = false
    }

    val pendingDevices = devices.filter { !it.isSaved }
    val completedDevices = devices.filter { it.isSaved }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
        ) {
            // Top Bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Surface)
                    .padding(horizontal = 12.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                IconButton(onClick = onDismiss) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = "Geri",
                        tint = OnSurface
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Filo Sayaç Okuma",
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = OnSurface
                    )
                    Text(
                        text = item.customerName,
                        fontSize = 12.sp,
                        color = OnSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                StitchStatusBadge(
                    text = "Aylık Okuma",
                    dotColor = PrimaryContainer,
                    containerColor = SurfaceContainerHigh,
                    contentColor = PrimaryContainer
                )
            }

            // Customer Summary Card & Progress
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceContainerLowest),
                border = BorderStroke(1.dp, OutlineVariant.copy(alpha = 0.4f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 4.dp)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = item.customerName,
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = OnSurface
                            )
                            if (item.locationText.isNotBlank()) {
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

                    // Progress Bar
                    val total = devices.size
                    val done = completedDevices.size
                    val progressFraction = if (total > 0) done.toFloat() / total.toFloat() else 0f

                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "$done / $total Cihaz Tamamlandı",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = PrimaryContainer
                            )
                            Text(
                                text = "Kalan: ${pendingDevices.size}",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Secondary
                            )
                        }
                        LinearProgressIndicator(
                            progress = { progressFraction },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            color = Secondary,
                            trackColor = SurfaceContainer
                        )
                    }
                }
            }

            // Segmented Tabs: Okunacaklar & Tamamlananlar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(SurfaceContainerHigh)
                    .padding(4.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Button(
                    onClick = { selectedTab = 0 },
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (selectedTab == 0) SurfaceContainerLowest else Color.Transparent,
                        contentColor = if (selectedTab == 0) PrimaryContainer else OnSurfaceVariant
                    ),
                    elevation = if (selectedTab == 0) ButtonDefaults.buttonElevation(defaultElevation = 1.dp) else ButtonDefaults.buttonElevation(defaultElevation = 0.dp),
                    modifier = Modifier.weight(1f).height(40.dp)
                ) {
                    Text("Okunacaklar (${pendingDevices.size})", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }

                Button(
                    onClick = { selectedTab = 1 },
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (selectedTab == 1) SurfaceContainerLowest else Color.Transparent,
                        contentColor = if (selectedTab == 1) PrimaryContainer else OnSurfaceVariant
                    ),
                    elevation = if (selectedTab == 1) ButtonDefaults.buttonElevation(defaultElevation = 1.dp) else ButtonDefaults.buttonElevation(defaultElevation = 0.dp),
                    modifier = Modifier.weight(1f).height(40.dp)
                ) {
                    Text("Tamamlanan (${completedDevices.size})", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                }
            }

            if (loading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = PrimaryContainer)
                }
            } else {
                val currentList = if (selectedTab == 0) pendingDevices else completedDevices
                if (currentList.isEmpty()) {
                    Box(modifier = Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.Center) {
                        Text(
                            text = if (selectedTab == 0) "Tüm cihazların sayacı alındı!" else "Henüz tamamlanan cihaz yok.",
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
                        contentPadding = PaddingValues(vertical = 8.dp)
                    ) {
                        items(currentList, key = { it.id }) { dev ->
                            MeterDeviceCard(
                                device = dev,
                                onSaveDeviceReading = { bw, color ->
                                    scope.launch {
                                        val custId = resolvedCustomerId
                                        if (custId.isBlank()) return@launch
                                        try {
                                            db.document("tenants/$tenantId/customers/$custId/devices/${dev.id}").update(
                                                mapOf(
                                                    "currentCounters.bw" to bw,
                                                    "currentCounters.color" to (color ?: 0),
                                                    "currentCounters.updatedAt" to FieldValue.serverTimestamp()
                                                )
                                            ).await()
                                            devices = devices.map { current ->
                                                if (current.id == dev.id) current.copy(
                                                    newBw = bw.toString(),
                                                    newColor = color?.toString().orEmpty(),
                                                    isSaved = true,
                                                ) else current
                                            }
                                        } catch (error: Throwable) {
                                            android.util.Log.e("CustomerMeterReading", "Sayaç kaydedilemedi", error)
                                        }
                                    }
                                }
                            )
                        }
                    }
                }

                // Sticky Bottom Action Dock
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(SurfaceContainerLowest)
                        .padding(16.dp)
                ) {
                    Button(
                        onClick = {
                            val readings = completedDevices.mapNotNull { device ->
                                device.newBw.toIntOrNull()?.let { bw ->
                                    MeterReadingInput(
                                        deviceId = device.id,
                                        bwCounter = bw,
                                        colorCounter = device.newColor.toIntOrNull(),
                                    )
                                }
                            }
                            onCompleteTask(readings, "${readings.size} cihaz sayaç okuma tamamlandı")
                        },
                        enabled = completedDevices.isNotEmpty(),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(54.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (pendingDevices.isEmpty()) TertiaryContainer else PrimaryContainer,
                            contentColor = OnPrimary
                        )
                    ) {
                        Text(
                            text = if (pendingDevices.isEmpty()) "✓ Sayaç Görevini Başarıyla Kapat" else "Okunanları Kaydet ve Kapat (${completedDevices.size})",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MeterDeviceCard(
    device: MeterDeviceEntry,
    onSaveDeviceReading: (bw: Int, color: Int?) -> Unit,
) {
    var bwInput by remember(device.id) { mutableStateOf(device.newBw) }
    var colorInput by remember(device.id) { mutableStateOf(device.newColor) }
    var errorText by remember(device.id) { mutableStateOf<String?>(null) }

    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceContainerLowest),
        border = BorderStroke(1.dp, OutlineVariant.copy(alpha = 0.4f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    modifier = Modifier.weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(38.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(SurfaceContainer),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Outlined.Print, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(20.dp))
                    }
                    Column {
                        Text(
                            text = device.model,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = OnSurface,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = "SN: ${device.serialNumber}",
                            fontSize = 12.sp,
                            color = OnSurfaceVariant
                        )
                    }
                }

                if (device.isSaved) {
                    StitchStatusBadge(
                        text = "Kaydedildi",
                        dotColor = GreenSuccess,
                        containerColor = TertiaryFixed.copy(alpha = 0.5f),
                        contentColor = OnTertiaryFixed
                    )
                } else {
                    StitchStatusBadge(
                        text = if (device.isColor) "Renkli MFP" else "S/B Mono",
                        dotColor = if (device.isColor) Secondary else Outline,
                        containerColor = SurfaceContainerHigh,
                        contentColor = OnSurface
                    )
                }
            }

            if (!device.isSaved) {
                // S/B Sayaç
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Siyah / Beyaz Sayaç *", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = OnSurface)
                        Text("Önceki: ${device.lastBw ?: "-"}", fontSize = 11.sp, color = OnSurfaceVariant)
                    }
                    OutlinedTextField(
                        value = bwInput,
                        onValueChange = {
                            bwInput = it
                            errorText = null
                        },
                        placeholder = { Text("Sayaç değerini girin") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = SurfaceContainerLowest,
                            unfocusedContainerColor = SurfaceContainerLow
                        )
                    )
                    StitchCounterDeltaBadge(
                        oldCounter = device.lastBw,
                        newCounter = bwInput.toIntOrNull()
                    )
                }

                // Renkli Sayaç
                if (device.isColor) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("Renkli Sayaç (Color) *", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = OnSurface)
                            Text("Önceki: ${device.lastColor ?: "-"}", fontSize = 11.sp, color = OnSurfaceVariant)
                        }
                        OutlinedTextField(
                            value = colorInput,
                            onValueChange = {
                                colorInput = it
                                errorText = null
                            },
                            placeholder = { Text("Renkli sayaç değerini girin") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = SurfaceContainerLowest,
                                unfocusedContainerColor = SurfaceContainerLow
                            )
                        )
                        StitchCounterDeltaBadge(
                            oldCounter = device.lastColor,
                            newCounter = colorInput.toIntOrNull()
                        )
                    }
                }

                if (!errorText.isNullOrBlank()) {
                    Text(text = errorText!!, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                }

                Button(
                    onClick = {
                        val bwVal = bwInput.trim().toIntOrNull()
                        if (bwVal == null) {
                            errorText = "Geçerli bir S/B sayaç giriniz."
                            return@Button
                        }
                        val colorVal = if (device.isColor) colorInput.trim().toIntOrNull() else null
                        if (device.isColor && colorVal == null) {
                            errorText = "Geçerli bir renkli sayaç giriniz."
                            return@Button
                        }
                        onSaveDeviceReading(bwVal, colorVal)
                    },
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth().height(44.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = PrimaryContainer,
                        contentColor = OnPrimary
                    )
                ) {
                    Text("Bu Cihazın Sayacını Onayla", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Kaydedilen Sayaç: ${device.newBw.ifBlank { device.lastBw?.toString() ?: "-" }}", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Tertiary)
                    if (device.isColor) {
                        Text("Renkli: ${device.newColor.ifBlank { device.lastColor?.toString() ?: "-" }}", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Tertiary)
                    }
                }
            }
        }
    }
}
