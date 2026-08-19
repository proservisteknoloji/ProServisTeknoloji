package com.proservis.technician.ui.screen.complete

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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

private data class StatusOption(val value: String, val label: String)

private val serviceStatusOptions = listOf(
    StatusOption("In Progress", "Servise Alındı"),
    StatusOption("Fault Persists", "Arıza Devam Ediyor"),
    StatusOption("Repaired", "Onarım Tamamlandı"),
    StatusOption("Delivered", "Servisi Kapat"),
)

private val PageBgColor = Color(0xFFF8FAFC)
private val TopBarGradient = listOf(Color(0xFF1E3A8A), Color(0xFF2563EB))
private val ActionButtonColor = Color(0xFF2563EB)

@Composable
fun CompleteServiceRoute(
    onSuccess: () -> Unit,
    onBack: () -> Unit,
    viewModel: CompleteServiceViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.success) {
        if (state.success) onSuccess()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(PageBgColor),
    ) {
        // Modern TopBar with Proservis Gradient
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Brush.horizontalGradient(TopBarGradient))
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
            Text(
                text = when {
                    state.isDeliveryJob -> "Teslim Ekranı"
                    state.isSimpleTask -> "Görev Ekranı"
                    else -> "Servis Formu / İşlemler"
                },
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
            )
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f, fill = false)
                .verticalScroll(rememberScrollState())
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Customer & Device Info Card
            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                border = BorderStroke(1.dp, Color(0xFFE2E8F0)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
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
                        text = "🖨️ Cihaz: ${state.title}${state.serialNumber?.let { " (Seri: $it)" } ?: ""}",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF334155)
                    )
                }
            }

            // Prominent Problem Description Box
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
                            text = "BİLDİRİLEN ARIZA / SORUN TANIMI:",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFB45309)
                        )
                        Text(
                            text = state.problemDescription.orEmpty(),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF1E293B),
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }

            // Report / Form Card
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
                    OutlinedTextField(
                        value = state.report,
                        onValueChange = viewModel::onReportChanged,
                        modifier = Modifier.fillMaxWidth(),
                        label = {
                            Text(
                                when {
                                    state.isDeliveryJob -> "Teslim Notu"
                                    state.isSimpleTask -> "Yapılan İşlem / Açıklama"
                                    else -> "Yapılan İşlemler / Teknisyen Açıklaması *"
                                }
                            )
                        },
                        shape = RoundedCornerShape(12.dp),
                        minLines = if (state.isServiceJob) 4 else 3,
                    )

                    if (state.isDeliveryJob) {
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
                            label = { Text("Teslim Alan Kişi") },
                        )
                    } else if (state.isServiceJob) {
                        Text("Sayaç Bilgileri", fontWeight = FontWeight.Bold, fontSize = 13.sp, color = Color(0xFF1E293B))
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
                                label = { Text("Yeni S/B *") },
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
                                    label = { Text("Yeni Renkli *") },
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

                    // 3 Explicit Status Buttons for Arıza Completion
                    if (state.isServiceJob) {
                        Text("Servis Sonuç Durumunu Seçin ve Kaydedin:", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = Color(0xFF334155), modifier = Modifier.padding(top = 4.dp))

                        Button(
                            onClick = { viewModel.submitWithStatus("Repaired") },
                            enabled = !state.loading,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
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
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD97706), contentColor = Color.White),
                        ) {
                            Text("PARÇA DEĞİŞECEK (Parça Bekliyor)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }

                        Button(
                            onClick = { viewModel.submitWithStatus("Fault Persists") },
                            enabled = !state.loading,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626), contentColor = Color.White),
                        ) {
                            Text("✕ ARIZA GİDERİLEMEDİ (Arıza Devam Ediyor)", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                        }
                    } else {
                        Button(
                            onClick = viewModel::submit,
                            enabled = !state.loading,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB), contentColor = Color.White),
                        ) {
                            if (state.loading) {
                                CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                                Spacer(Modifier.width(8.dp))
                            }
                            Text(
                                if (state.isDeliveryJob) "TESLİM EDİLDİ OLARAK GÖNDER" else "GÖREVİ TAMAMLA",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                        }
                    }

                    OutlinedButton(
                        onClick = onBack,
                        enabled = !state.loading,
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                    ) {
                        Text("Geri Dön", color = Color(0xFF64748B), fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }
}
