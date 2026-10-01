package com.proservis.technician.ui.screen.complete

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.proservis.technician.ui.components.StitchCounterDeltaBadge
import com.proservis.technician.ui.components.StitchStatusBadge
import com.proservis.technician.ui.theme.*

@Composable
fun CompleteServiceRoute(
    onSuccess: () -> Unit,
    onBack: () -> Unit,
    viewModel: CompleteServiceViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    // Fotoğraf çekme (Kamera) launcher
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicturePreview()
    ) { bitmap: Bitmap? ->
        if (bitmap != null) {
            viewModel.uploadReportBitmap(bitmap)
        }
    }

    // Dosya / Galeri seçme launcher
    val fileLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            viewModel.uploadReportFromUri(context, uri)
        }
    }

    LaunchedEffect(state.success) {
        if (state.success) onSuccess()
    }

    val pageTitle = when {
        state.isDeviceReplacement -> "Cihaz Değişimi Detayı"
        state.isDeviceDelivery -> "Cihaz Teslimat & Montaj"
        state.isDevicePickup -> "Cihaz Geri Alma Formu"
        state.isTonerDelivery -> "Sarf / Toner Teslimat Detayı"
        state.isProductTransfer -> "Ürün Teslimat Detayı"
        state.isMaintenance -> "Bakım Servis Detayı"
        state.isPartReplacement -> "Parça Değişimi Servisi"
        state.isRemoteSupport -> "Uzak Destek / Kurulum"
        state.isSimpleTask -> "Görev Detayı ve Tamamlama"
        else -> "Arıza Servis Detayı"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Surface)
            .statusBarsPadding()
            .navigationBarsPadding(),
    ) {
        // TopBar (Stitch Standardı)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Surface)
                .padding(horizontal = 12.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Geri",
                    tint = OnSurface
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = pageTitle,
                    color = OnSurface,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                if (state.serviceReason.isNotBlank()) {
                    Text(
                        text = state.serviceReason,
                        color = OnSurfaceVariant,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }
            StitchStatusBadge(
                text = if (state.isDeliveryJob) "Teslimat" else "İşlemde",
                dotColor = if (state.isDeliveryJob) Secondary else PrimaryContainer,
                containerColor = SurfaceContainerHigh,
                contentColor = OnSurface
            )
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 6.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            // Müşteri & Cihaz Bilgi Kartı
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceContainerLowest),
                border = BorderStroke(1.dp, OutlineVariant.copy(alpha = 0.4f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = state.customerName.ifBlank { "Müşteri Belirtilmemiş" },
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        color = OnSurface
                    )
                    if (state.locationText.isNotBlank()) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            Icon(Icons.Outlined.LocationOn, contentDescription = null, tint = Secondary, modifier = Modifier.size(16.dp))
                            Text(
                                text = state.locationText,
                                fontSize = 12.sp,
                                color = OnSurfaceVariant
                            )
                        }
                    }
                    HorizontalDivider(color = SurfaceContainerLow, thickness = 1.dp, modifier = Modifier.padding(vertical = 4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Outlined.Print, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(18.dp))
                            Text(
                                text = state.title,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = OnSurface
                            )
                        }
                        if (!state.serialNumber.isNullOrBlank()) {
                            Text(
                                text = "SN: ${state.serialNumber}",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = OnSurfaceVariant
                            )
                        }
                    }
                }
            }

            // Bildirilen Sorun / Talep Kutusu
            if (!state.problemDescription.isNullOrBlank()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(SurfaceContainerLow)
                        .padding(14.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(
                            text = "BİLDİRİLEN ARIZA / TALEP ÖZETİ",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = OrangeWarning,
                            letterSpacing = 0.5.sp
                        )
                        Text(
                            text = state.problemDescription.orEmpty(),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium,
                            color = OnSurface,
                            lineHeight = 18.sp
                        )
                    }
                }
            }

            // Teslim Kalemleri Listesi (Eğer Teslimat / Sarf işi ise)
            if (state.deliveryItems.isNotEmpty()) {
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
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Icon(Icons.Outlined.Inventory2, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(18.dp))
                                Text("Teslim Edilecek Malzemeler", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = OnSurface)
                            }
                            Text("${state.deliveryItems.size} Kalem", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = PrimaryContainer)
                        }

                        state.deliveryItems.forEach { item ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(SurfaceContainerLow)
                                    .padding(10.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = item,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = OnSurface,
                                    modifier = Modifier.weight(1f)
                                )
                                Icon(Icons.Outlined.CheckCircle, contentDescription = "Hazır", tint = GreenSuccess, modifier = Modifier.size(18.dp))
                            }
                        }
                    }
                }
            }

            // Sayaç Bilgileri Bölümü (Stitch Delta Hesaplamalı)
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceContainerLowest),
                border = BorderStroke(1.dp, OutlineVariant.copy(alpha = 0.4f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Icon(Icons.Outlined.Speed, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(18.dp))
                            Text(
                                text = if (state.isDeliveryJob) "Sayaç Bilgileri (Opsiyonel)" else "Sayaç Bilgileri",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = OnSurface
                            )
                        }
                    }

                    // S/B Sayaç
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(if (state.isServiceJob) "Siyah / Beyaz Sayaç *" else "S/B Sayaç", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = OnSurface)
                            Text("Önceki: ${state.lastBwCounter ?: "-"}", fontSize = 11.sp, color = OnSurfaceVariant)
                        }
                        OutlinedTextField(
                            value = state.bwCounter,
                            onValueChange = viewModel::onBwCounterChanged,
                            placeholder = { Text("Yeni S/B Sayaç Değeri") },
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
                            oldCounter = state.lastBwCounter?.toIntOrNull(),
                            newCounter = state.bwCounter.toIntOrNull()
                        )
                    }

                    // Renkli Sayaç
                    if (state.isColorDevice) {
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(if (state.isServiceJob) "Renkli Sayaç (Color) *" else "Renkli Sayaç", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = OnSurface)
                                Text("Önceki: ${state.lastColorCounter ?: "-"}", fontSize = 11.sp, color = OnSurfaceVariant)
                            }
                            OutlinedTextField(
                                value = state.colorCounter,
                                onValueChange = viewModel::onColorCounterChanged,
                                placeholder = { Text("Yeni Renkli Sayaç Değeri") },
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
                                oldCounter = state.lastColorCounter?.toIntOrNull(),
                                newCounter = state.colorCounter.toIntOrNull()
                            )
                        }
                    }
                }
            }

            // Teslim Alan Kişi Bilgisi (Sadece Ad Soyad - Telefon ve imza yok)
            if (state.isDeliveryJob || state.isDeviceDelivery || state.isDeviceReplacement || state.isDevicePickup) {
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
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Icon(Icons.Outlined.Badge, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(18.dp))
                            Text("Teslim Alan Yetkili Bilgisi", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = OnSurface)
                        }

                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("Teslim Alan Adı Soyadı *", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = OnSurface)
                            OutlinedTextField(
                                value = state.deliveryRecipientName,
                                onValueChange = viewModel::onDeliveryRecipientChanged,
                                placeholder = { Text("Örn: Ahmet Yılmaz") },
                                singleLine = true,
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier.fillMaxWidth(),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = SurfaceContainerLowest,
                                    unfocusedContainerColor = SurfaceContainerLow
                                )
                            )
                        }
                    }
                }
            }

            // Fotoğraf & Servis Formu Yükleme
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
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Icon(Icons.Outlined.CameraAlt, contentDescription = null, tint = PrimaryContainer, modifier = Modifier.size(18.dp))
                            Text("Servis Fotoğrafı / Formu", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = OnSurface)
                        }
                        if (!state.reportFileName.isNullOrBlank()) {
                            Text("✓ Eklendi", color = GreenSuccess, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        OutlinedButton(
                            onClick = { cameraLauncher.launch(null) },
                            enabled = !state.reportUploadInProgress && !state.loading,
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f).height(46.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = PrimaryContainer),
                            border = BorderStroke(1.dp, PrimaryContainer.copy(alpha = 0.4f))
                        ) {
                            Text("📷 Fotoğraf Çek", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }

                        OutlinedButton(
                            onClick = { fileLauncher.launch("image/*") },
                            enabled = !state.reportUploadInProgress && !state.loading,
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f).height(46.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Secondary),
                            border = BorderStroke(1.dp, Secondary.copy(alpha = 0.4f))
                        ) {
                            Text("📁 Dosya Seç", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }

                    if (state.reportUploadInProgress) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = PrimaryContainer)
                            Spacer(Modifier.width(8.dp))
                            Text("Yükleniyor...", fontSize = 12.sp, color = PrimaryContainer)
                        }
                    }

                    if (!state.reportFileName.isNullOrBlank()) {
                        Text("Yüklenen Dosya: ${state.reportFileName}", fontSize = 12.sp, color = Tertiary, fontWeight = FontWeight.Medium)
                    }

                    if (!state.reportUploadError.isNullOrBlank()) {
                        Text(state.reportUploadError.orEmpty(), color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                    }
                }
            }

            // Yapılan İşlemler / Teknisyen Açıklaması
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceContainerLowest),
                border = BorderStroke(1.dp, OutlineVariant.copy(alpha = 0.4f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = if (state.isDeliveryJob) "Teslimat Notu / Açıklama" else "Yapılan İşlemler / Rapor *",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = OnSurface
                    )
                    OutlinedTextField(
                        value = state.report,
                        onValueChange = viewModel::onReportChanged,
                        placeholder = { Text(if (state.isDeliveryJob) "Teslim edildi, irsaliye no vb." else "Yapılan onarım, değişen parçalar vb.") },
                        minLines = 3,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = SurfaceContainerLowest,
                            unfocusedContainerColor = SurfaceContainerLow
                        )
                    )
                }
            }

            if (!state.errorMessage.isNullOrBlank()) {
                Text(
                    text = state.errorMessage.orEmpty(),
                    color = MaterialTheme.colorScheme.error,
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(horizontal = 4.dp)
                )
            }

            // Alt Kapatma Butonu (56dp height)
            Button(
                onClick = { viewModel.submit() },
                enabled = !state.loading,
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(54.dp)
                    .padding(bottom = 8.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (state.isDeliveryJob) TertiaryContainer else PrimaryContainer,
                    contentColor = OnPrimary
                )
            ) {
                if (state.loading) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = OnPrimary, strokeWidth = 2.dp)
                } else {
                    Text(
                        text = if (state.isDeliveryJob) "✓ Teslimatı Onayla ve Kapat" else "✓ Servisi Tamamla ve Kapat",
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp
                    )
                }
            }
        }
    }
}
