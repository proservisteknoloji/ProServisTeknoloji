package com.proservis.technician.ui.screen.complete

import android.graphics.Bitmap
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

private val PageBgColor = Color(0xFFF8FAFC)

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

    val topBarGradient = when {
        state.isDeviceReplacement -> listOf(Color(0xFF6B21A8), Color(0xFF9333EA)) // Mor
        state.isDeviceDelivery -> listOf(Color(0xFF065F46), Color(0xFF059669)) // Zümrüt Yeşili
        state.isDevicePickup -> listOf(Color(0xFF312E81), Color(0xFF4F46E5)) // İndigo
        state.isTonerDelivery -> listOf(Color(0xFF0369A1), Color(0xFF0284C7)) // Açık Mavi
        state.isMaintenance -> listOf(Color(0xFF047857), Color(0xFF10B981)) // Bakım Yeşili
        state.isPartReplacement -> listOf(Color(0xFFB45309), Color(0xFFD97706)) // Amber
        state.isRemoteSupport -> listOf(Color(0xFF4C1D95), Color(0xFF7C3AED)) // Menekşe
        else -> listOf(Color(0xFF1E3A8A), Color(0xFF2563EB)) // Koyu Mavi
    }

    val pageTitle = when {
        state.isDeviceReplacement -> "Cihaz Değişimi Formu"
        state.isDeviceDelivery -> "Cihaz Teslimat & Montaj"
        state.isDevicePickup -> "Cihaz Geri Alma Formu"
        state.isTonerDelivery -> "Toner Teslim Formu"
        state.isProductTransfer -> "Ürün Teslim Formu"
        state.isMaintenance -> "Periyodik Bakım Formu"
        state.isPartReplacement -> "Parça Değişimi Formu"
        state.isRemoteSupport -> "Uzak Bağlantı Formu"
        state.isSimpleTask -> "Görev Tamamlama"
        else -> "Arıza Servis Formu"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(PageBgColor),
    ) {
        // Modern Dinamik TopBar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Brush.horizontalGradient(topBarGradient))
                .padding(horizontal = 8.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Geri",
                    tint = Color.White
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = pageTitle,
                    color = Color.White,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                )
                if (state.serviceReason.isNotBlank()) {
                    Text(
                        text = state.serviceReason,
                        color = Color.White.copy(alpha = 0.85f),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                    )
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f, fill = false)
                .verticalScroll(rememberScrollState())
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Müşteri & Cihaz Bilgi Kartı
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                border = BorderStroke(1.dp, Color(0xFFE2E8F0)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = state.customerName.ifBlank { "Müşteri Belirtilmemiş" },
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = Color(0xFF1E293B)
                    )
                    if (state.locationText.isNotBlank()) {
                        Text(
                            text = "📍 Lokasyon: ${state.locationText}",
                            fontSize = 12.sp,
                            color = Color(0xFF64748B)
                        )
                    }
                    Text(
                        text = "🖨️ Cihaz: ${state.title}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF334155)
                    )
                    if (!state.serialNumber.isNullOrBlank()) {
                        Text(
                            text = "Seri No: ${state.serialNumber}",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF475569)
                        )
                    }
                }
            }

            // Bildirilen Arıza / Talep Tanımı
            if (!state.problemDescription.isNullOrBlank()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFFFFFBEB), RoundedCornerShape(12.dp))
                        .border(1.dp, Color(0xFFFDE68A), RoundedCornerShape(12.dp))
                        .padding(14.dp)
                ) {
                    Column {
                        Text(
                            text = "BİLDİRİLEN ARIZA / TALEP:",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFB45309)
                        )
                        Text(
                            text = state.problemDescription.orEmpty(),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF1E293B),
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }

            // 📸 Servis Formu / Fotoğraf Yükleme Bölümü
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                border = BorderStroke(1.dp, Color(0xFFE2E8F0)),
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
                        Text(
                            text = "📎 Servis Formu & Fotoğraf",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = Color(0xFF1E293B)
                        )
                        if (!state.reportFileName.isNullOrBlank()) {
                            Text(
                                text = "✓ Form Eklendi",
                                color = Color(0xFF16A34A),
                                fontWeight = FontWeight.Bold,
                                fontSize = 12.sp
                            )
                        }
                    }

                    Text(
                        text = "İmzalı servis formunu veya işlem fotoğrafını ekleyebilirsiniz.",
                        fontSize = 12.sp,
                        color = Color(0xFF64748B)
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        OutlinedButton(
                            onClick = { cameraLauncher.launch(null) },
                            enabled = !state.reportUploadInProgress && !state.loading,
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f).height(44.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF0284C7)),
                            border = BorderStroke(1.dp, Color(0xFFBAE6FD))
                        ) {
                            Text("📷 Fotoğraf Çek", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        }

                        OutlinedButton(
                            onClick = { fileLauncher.launch("image/*") },
                            enabled = !state.reportUploadInProgress && !state.loading,
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f).height(44.dp),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF4F46E5)),
                            border = BorderStroke(1.dp, Color(0xFFC7D2FE))
                        ) {
                            Text("📁 Dosya Seç", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        }
                    }

                    if (state.reportUploadInProgress) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                            Spacer(Modifier.width(8.dp))
                            Text("Form yükleniyor...", fontSize = 12.sp, color = Color(0xFF2563EB))
                        }
                    }

                    if (!state.reportFileName.isNullOrBlank()) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Color(0xFFF0FDF4), RoundedCornerShape(8.dp))
                                .border(1.dp, Color(0xFFBBF7D0), RoundedCornerShape(8.dp))
                                .padding(8.dp)
                        ) {
                            Text(
                                text = "📄 ${state.reportFileName}",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color(0xFF15803D)
                            )
                        }
                    }

                    if (!state.reportUploadError.isNullOrBlank()) {
                        Text(
                            text = state.reportUploadError.orEmpty(),
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            // Rapor & Sayaç & Teslim Kartı
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                border = BorderStroke(1.dp, Color(0xFFE2E8F0)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Yapılan İşlemler / Açıklama
                    OutlinedTextField(
                        value = state.report,
                        onValueChange = viewModel::onReportChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = {
                            Text(
                                when {
                                    state.isDeliveryJob -> "Teslim Notu / Açıklama"
                                    state.isSimpleTask -> "Yapılan İşlem / Açıklama"
                                    else -> "Yapılan İşlemler / Teknisyen Açıklaması *"
                                }
                            )
                        },
                        shape = RoundedCornerShape(12.dp),
                        minLines = if (state.isServiceJob) 4 else 3,
                    )

                    // Teslim Alan Kişi (Teslimat veya Değişim durumlarında)
                    if (state.isDeliveryJob || state.isDeviceDelivery || state.isDeviceReplacement || state.isDevicePickup) {
                        if (state.deliveryItems.isNotEmpty()) {
                            Text("Teslim Kalemleri", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                            state.deliveryItems.forEach { item ->
                                Text("• $item", style = MaterialTheme.typography.bodySmall, color = Color(0xFF475569))
                            }
                        }
                        OutlinedTextField(
                            value = state.deliveryRecipientName,
                            onValueChange = viewModel::onDeliveryRecipientChanged,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            label = { Text("Teslim Alan Kişi (Ad Soyad)") },
                        )
                    }

                    // Sayaç Girişi (Servis, Bakım, Değişim, Toner Teslimi vb.)
                    if (state.isServiceJob || state.isDevicePickup || state.isDeviceDelivery || state.isTonerDelivery) {
                        Text(
                            if (state.isTonerDelivery) "Sayaç Bilgileri (Opsiyonel)" else "Sayaç Bilgileri",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp,
                            color = Color(0xFF1E293B)
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedTextField(
                                value = state.lastBwCounter ?: "-",
                                onValueChange = {},
                                enabled = false,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                label = { Text("Eski S/B") },
                            )
                            OutlinedTextField(
                                value = state.bwCounter,
                                onValueChange = viewModel::onBwCounterChanged,
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                label = { Text(if (state.isServiceJob) "Yeni S/B *" else "Yeni S/B") },
                            )
                        }

                        if (state.isColorDevice) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                OutlinedTextField(
                                    value = state.lastColorCounter ?: "-",
                                    onValueChange = {},
                                    enabled = false,
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(12.dp),
                                    label = { Text("Eski Renkli") },
                                )
                                OutlinedTextField(
                                    value = state.colorCounter,
                                    onValueChange = viewModel::onColorCounterChanged,
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(12.dp),
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    label = { Text(if (state.isServiceJob) "Yeni Renkli *" else "Yeni Renkli") },
                                )
                            }
                        } else {
                            Text("(Siyah-Beyaz Cihaz - Renkli Sayaç Pasif)", fontSize = 11.sp, color = Color.Gray)
                        }
                    }

                    val errorMessage = state.errorMessage
                    if (!errorMessage.isNullOrBlank()) {
                        Text(errorMessage, color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
                    }

                    // Dinamik Sonuç & Kapatma Butonları
                    if (state.isDeviceReplacement) {
                        Button(
                            onClick = { viewModel.submitWithStatus("Repaired") },
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF9333EA), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text("✓ CİHAZ DEĞİŞİMİNİ TAMAMLA VE KAPAT", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    } else if (state.isDevicePickup) {
                        Button(
                            onClick = { viewModel.submitWithStatus("Repaired") },
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4F46E5), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text("✓ CİHAZI TESLİM ALDIM (Kapat)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    } else if (state.isMaintenance) {
                        Button(
                            onClick = { viewModel.submitWithStatus("Repaired") },
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text("✓ PERİYODİK BAKIM TAMAMLANDI", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    } else if (state.isDeliveryJob) {
                        Button(
                            onClick = viewModel::submit,
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0284C7), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text("✓ TESLİM EDİLDİ OLARAK KAYDET", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    } else if (state.isServiceJob) {
                        Text("Servis Sonuç Durumunu Seçin ve Kaydedin:", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xFF334155), modifier = Modifier.padding(top = 4.dp))

                        Button(
                            onClick = { viewModel.submitWithStatus("Repaired") },
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF16A34A), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text("✓ ARIZA GİDERİLDİ (Servisi Kapat)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }

                        Button(
                            onClick = { viewModel.submitWithStatus("Waiting Part") },
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD97706), contentColor = Color.White),
                        ) {
                            Text("PARÇA DEĞİŞECEK (Parça Bekliyor)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }

                        Button(
                            onClick = { viewModel.submitWithStatus("Fault Persists") },
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626), contentColor = Color.White),
                        ) {
                            Text("✕ ARIZA GİDERİLEMEDİ (Arıza Devam Ediyor)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    } else {
                        Button(
                            onClick = viewModel::submit,
                            enabled = !state.loading,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text("✓ GÖREVİ TAMAMLA", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    }

                    OutlinedButton(
                        onClick = onBack,
                        enabled = !state.loading,
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                    ) {
                        Text("Geri Dön", color = Color(0xFF64748B), fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }
}
