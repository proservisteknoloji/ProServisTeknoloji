package com.proservis.technician.ui.screen.verify

import android.Manifest
import android.content.pm.PackageManager
import android.hardware.camera2.CaptureRequest
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.camera2.interop.Camera2Interop
import androidx.camera.core.AspectRatio
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

private val TopBarColor = Color(0xFF00897B)
private val PageBgColor = Color(0xFFE5E5E5)
private val ActionButtonColor = Color(0xFF6E6E6E)
private val OverlayShade = Color(0x99000000)
private val ScanBorderColor = Color(0xFFF4F4F4)
private val ScanLineColor = Color(0x99FF3B30)

@Composable
fun SerialVerifyRoute(
    onSuccess: (serviceId: String) -> Unit,
    onBack: () -> Unit,
    viewModel: SerialVerifyViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(state.success) {
        if (state.success) onSuccess(state.serviceId)
    }

    LaunchedEffect(state.scannedText) {
        if (state.scannedText.isBlank()) return@LaunchedEffect
        vibrateSuccess(context)
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        viewModel.onCameraPermissionResult(granted)
    }

    LaunchedEffect(Unit) {
        val granted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
        viewModel.onCameraPermissionResult(granted)
        if (!granted) permissionLauncher.launch(Manifest.permission.CAMERA)
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
                text = "Seri No Doğrulama",
                color = Color.White,
                fontSize = 22.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(14.dp)
                .background(Color.White)
                .border(1.dp, Color(0xFFCDCDCD), RoundedCornerShape(2.dp))
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Button(
                onClick = { viewModel.verifyAnyAndProceed() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(44.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF00897B),
                    contentColor = Color.White
                ),
                shape = RoundedCornerShape(6.dp)
            ) {
                Text(
                    text = "⚡ Sayaç Okuma / Seri No Doğrulamadan Geç",
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
            }

            Text("Servis ID: ${state.serviceId}", style = MaterialTheme.typography.bodySmall)
            Text("Kamera önizlemesi açık kalır. OCR sadece Oku butonuna bastığınızda tek kare için çalışır.")

            if (state.cameraPermissionGranted) {
                LiveSerialScanner(
                    onCanScan = viewModel::canScan,
                    onScanStarted = viewModel::beginProcessing,
                    onScanFinished = viewModel::finishProcessing,
                    onFrameResult = viewModel::onOcrResult,
                )
            } else {
                Text(
                    text = "Kamera izni olmadan tarama yapılamaz.",
                    color = MaterialTheme.colorScheme.error,
                )
                ActionButton(
                    label = "KAMERA IZNINI VER",
                    enabled = !state.loading,
                    onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) },
                )
            }

            Text(
                text = state.statusMessage,
                style = MaterialTheme.typography.bodySmall,
                color = if (state.isProcessing) Color(0xFF1565C0) else Color(0xFF5F6368),
            )

            if (state.scannedText.isNotBlank()) {
                Text(
                    text = "Okunan seri no: ${state.scannedText}",
                    color = Color(0xFF1565C0),
                    fontWeight = FontWeight.SemiBold,
                )
            }

            if (state.debugOcrText.isNotBlank()) {
                Text(
                    text = "OCR debug: ${state.debugOcrText}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF616161),
                )
            }

            OutlinedTextField(
                value = state.inputValue,
                onValueChange = viewModel::onInputChanged,
                label = { Text("Seri no / son haneler") },
                supportingText = { Text("Okunan sonuç otomatik buraya yazılır. İsterseniz manuel düzenleyebilirsiniz.") },
                modifier = Modifier.fillMaxWidth(),
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ActionButton(
                    label = if (state.isProcessing) "OKUNUYOR..." else "OKU",
                    enabled = state.cameraPermissionGranted && !state.loading && !state.isProcessing,
                    onClick = viewModel::requestScan,
                    loading = state.isProcessing,
                    modifier = Modifier.weight(1f),
                )
                ActionButton(
                    label = "TEMIZLE",
                    enabled = !state.loading && !state.isProcessing,
                    onClick = viewModel::clearScanResult,
                    modifier = Modifier.weight(1f),
                )
            }

            ActionButton(
                label = "DOGRULA",
                enabled = !state.loading && !state.isProcessing,
                onClick = viewModel::verify,
                loading = state.loading,
            )

            ActionButton(
                label = "GERI",
                enabled = !state.loading,
                onClick = onBack,
            )

            state.errorMessage?.takeIf { it.isNotBlank() }?.let {
                Text(it, color = MaterialTheme.colorScheme.error)
            }
        }
    }
}

@Composable
private fun LiveSerialScanner(
    onCanScan: () -> Boolean,
    onScanStarted: () -> Boolean,
    onScanFinished: () -> Unit,
    onFrameResult: (SerialOcrFrameResult) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }
    val previewView = remember {
        PreviewView(context).apply {
            implementationMode = PreviewView.ImplementationMode.COMPATIBLE
            scaleType = PreviewView.ScaleType.FILL_CENTER
        }
    }

    DisposableEffect(Unit) {
        onDispose { cameraExecutor.shutdown() }
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(250.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(Color.Black, RoundedCornerShape(12.dp)),
    ) {
        AndroidView(
            factory = { previewView },
            modifier = Modifier.fillMaxSize(),
            update = { view ->
                bindCameraUseCases(
                    context = context,
                    lifecycleOwner = lifecycleOwner,
                    previewView = view,
                    cameraExecutor = cameraExecutor,
                    onCanScan = onCanScan,
                    onScanStarted = onScanStarted,
                    onScanFinished = onScanFinished,
                    onFrameResult = onFrameResult,
                )
            },
        )
        SerialScannerOverlay(modifier = Modifier.fillMaxSize())
    }
}

private fun bindCameraUseCases(
    context: android.content.Context,
    lifecycleOwner: androidx.lifecycle.LifecycleOwner,
    previewView: PreviewView,
    cameraExecutor: ExecutorService,
    onCanScan: () -> Boolean,
    onScanStarted: () -> Boolean,
    onScanFinished: () -> Unit,
    onFrameResult: (SerialOcrFrameResult) -> Unit,
) {
    val providerFuture = ProcessCameraProvider.getInstance(context)
    providerFuture.addListener(
        {
            val cameraProvider = providerFuture.get()
            cameraProvider.unbindAll()

            val previewBuilder = Preview.Builder().setTargetAspectRatio(AspectRatio.RATIO_16_9)
            Camera2Interop.Extender(previewBuilder)
                .setCaptureRequestOption(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
                .setCaptureRequestOption(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)

            val analysisBuilder = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setTargetAspectRatio(AspectRatio.RATIO_16_9)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
            Camera2Interop.Extender(analysisBuilder)
                .setCaptureRequestOption(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
                .setCaptureRequestOption(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)

            val preview = previewBuilder.build().also {
                it.surfaceProvider = previewView.surfaceProvider
            }

            val analysis = analysisBuilder.build().also {
                it.setAnalyzer(
                    cameraExecutor,
                    SerialScannerAnalyzer(
                        canScan = onCanScan,
                        onScanStarted = onScanStarted,
                        onScanFinished = onScanFinished,
                        onFrameResult = onFrameResult,
                    )
                )
            }

            cameraProvider.bindToLifecycle(
                lifecycleOwner,
                CameraSelector.DEFAULT_BACK_CAMERA,
                preview,
                analysis,
            )
        },
        ContextCompat.getMainExecutor(context),
    )
}

@Composable
private fun SerialScannerOverlay(modifier: Modifier = Modifier) {
    Box(modifier = modifier) {
        val horizontalPadding = 30.dp
        val topHeight = 80.dp
        val roiHeight = 54.dp

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(topHeight)
                .background(OverlayShade)
                .align(Alignment.TopCenter)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(roiHeight)
                .align(Alignment.Center),
        ) {
            Box(
                modifier = Modifier
                    .width(horizontalPadding)
                    .fillMaxSize()
                    .background(OverlayShade)
            )
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxSize()
                    .border(1.5.dp, ScanBorderColor, RoundedCornerShape(12.dp))
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val centerY = size.height / 2f
                    drawLine(
                        color = ScanLineColor,
                        start = Offset(12.dp.toPx(), centerY),
                        end = Offset(size.width - 12.dp.toPx(), centerY),
                        strokeWidth = 2.dp.toPx(),
                    )
                }
            }
            Box(
                modifier = Modifier
                    .width(horizontalPadding)
                    .fillMaxSize()
                    .background(OverlayShade)
            )
        }
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(topHeight)
                .background(OverlayShade)
                .align(Alignment.BottomCenter)
        )

        Text(
            text = "Seri numarayi kirmizi cizgiye hizalayin",
            color = Color.White,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 12.dp),
        )
    }
}

private fun vibrateSuccess(context: android.content.Context) {
    runCatching {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            context.getSystemService(VibratorManager::class.java)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Vibrator::class.java)
        } ?: return

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createOneShot(80L, VibrationEffect.DEFAULT_AMPLITUDE))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(80L)
        }
    }
}

@Composable
private fun ActionButton(
    label: String,
    enabled: Boolean,
    onClick: () -> Unit,
    loading: Boolean = false,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
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
        if (loading) {
            CircularProgressIndicator(color = Color.White, strokeWidth = 2.dp)
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text(label)
    }
}
