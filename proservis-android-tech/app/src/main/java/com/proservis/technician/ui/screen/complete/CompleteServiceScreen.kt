package com.proservis.technician.ui.screen.complete

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
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

private val TopBarColor = Color(0xFF00897B)
private val PageBgColor = Color(0xFFE5E5E5)
private val ActionButtonColor = Color(0xFF6E6E6E)

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
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(TopBarColor)
                .padding(horizontal = 14.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = when {
                    state.isDeliveryJob -> "Teslim Ekrani"
                    state.isSimpleTask -> "Gorev Ekrani"
                    else -> "Ariza Servis Girisi"
                },
                color = Color.White,
                fontSize = 22.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f, fill = false)
                .verticalScroll(rememberScrollState())
                .padding(14.dp)
                .background(Color.White)
                .border(1.dp, Color(0xFFCDCDCD), RoundedCornerShape(2.dp))
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color(0xFFF5F5F5))
                    .padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text("Müşteri: ${state.customerName.ifBlank { "Müşteri Belirtilmemiş" }}", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                if (state.locationText.isNotBlank()) Text("Lokasyon: ${state.locationText}", fontSize = 12.sp, color = Color(0xFF616161))
                Text("Cihaz: ${state.title}${state.serialNumber?.let { " (Seri: $it)" } ?: ""}", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
            }

            // Prominent Arıza / Sorun Tanımı Box
            if (!state.problemDescription.isNullOrBlank()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFFFFF3E0), RoundedCornerShape(6.dp))
                        .border(1.dp, Color(0xFFFFB74D), RoundedCornerShape(6.dp))
                        .padding(12.dp)
                ) {
                    Column {
                        Text(
                            text = "BİLDİRİLEN ARIZA / SORUN TANIMI:",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFE65100)
                        )
                        Text(
                            text = state.problemDescription.orEmpty(),
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF212121),
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }

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
                minLines = if (state.isServiceJob) 4 else 3,
            )

            if (state.isDeliveryJob) {
                if (state.deliveryItems.isNotEmpty()) {
                    Text("Teslim Kalemleri", fontWeight = FontWeight.SemiBold)
                    state.deliveryItems.forEach { item ->
                        Text("- $item", style = MaterialTheme.typography.bodySmall)
                    }
                }
                OutlinedTextField(
                    value = state.deliveryRecipientName,
                    onValueChange = viewModel::onDeliveryRecipientChanged,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Teslim Alan Kişi") },
                )
            } else if (state.isServiceJob) {
                Text("Sayaç Bilgileri", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = state.lastBwCounter ?: "-",
                        onValueChange = {},
                        enabled = false,
                        modifier = Modifier.weight(1f),
                        label = { Text("Eski S/B") },
                    )
                    OutlinedTextField(
                        value = state.bwCounter,
                        onValueChange = viewModel::onBwCounterChanged,
                        modifier = Modifier.weight(1f),
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
                            label = { Text("Eski Renkli") },
                        )
                        OutlinedTextField(
                            value = state.colorCounter,
                            onValueChange = viewModel::onColorCounterChanged,
                            modifier = Modifier.weight(1f),
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
                Text("Servis Sonuç Durumunu Seçin ve Kaydedin:", fontWeight = FontWeight.Bold, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))

                Button(
                    onClick = { viewModel.submitWithStatus("Repaired") },
                    enabled = !state.loading,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32), contentColor = Color.White),
                ) {
                    if (state.loading) {
                        CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.padding(end = 8.dp))
                    }
                    Text("✓ ARIZA GİDERİLDİ (Servisi Kapat)", fontWeight = FontWeight.Bold)
                }

                Button(
                    onClick = { viewModel.submitWithStatus("Waiting Part") },
                    enabled = !state.loading,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE65100), contentColor = Color.White),
                ) {
                    Text("PARÇA DEĞİŞECEK (Parça Bekliyor)", fontWeight = FontWeight.Bold)
                }

                Button(
                    onClick = { viewModel.submitWithStatus("Fault Persists") },
                    enabled = !state.loading,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC62828), contentColor = Color.White),
                ) {
                    Text("✕ ARIZA GİDERİLEMEDİ (Arıza Devam Ediyor)", fontWeight = FontWeight.Bold)
                }
            } else {
                ActionButton(
                    label = when {
                        state.isDeliveryJob -> "TESLIM EDILDI OLARAK GONDER"
                        else -> "GÖREVİ TAMAMLA"
                    },
                    enabled = !state.loading,
                    onClick = viewModel::submit,
                    loading = state.loading,
                )
            }

            ActionButton(label = "GERİ", enabled = !state.loading, onClick = onBack)
        }
    }
}

@Composable
private fun StatusDropdown(currentValue: String, onSelect: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val currentLabel = serviceStatusOptions.firstOrNull { it.value == currentValue }?.label ?: currentValue

    Box {
        Button(
            onClick = { expanded = true },
            colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = Color.Black),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(currentLabel)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            serviceStatusOptions.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.label) },
                    onClick = {
                        expanded = false
                        onSelect(option.value)
                    },
                )
            }
        }
    }
}

@Composable
private fun ActionButton(label: String, enabled: Boolean, onClick: () -> Unit, loading: Boolean = false) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth(),
        colors = ButtonDefaults.buttonColors(containerColor = ActionButtonColor, contentColor = Color.White),
    ) {
        if (loading) {
            CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp, modifier = Modifier.padding(end = 8.dp))
        }
        Text(label)
    }
}
