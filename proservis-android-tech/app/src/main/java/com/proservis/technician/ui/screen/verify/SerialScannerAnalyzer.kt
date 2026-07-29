package com.proservis.technician.ui.screen.verify

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.SystemClock
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.util.concurrent.atomic.AtomicBoolean

private const val MIN_SERIAL_LENGTH = 8

data class SerialOcrFrameResult(
    val bestCandidate: String?,
    val allCandidates: List<String>,
    val debugText: String,
)

class SerialScannerAnalyzer(
    private val canScan: () -> Boolean,
    private val onScanStarted: () -> Boolean,
    private val onScanFinished: () -> Unit,
    private val onFrameResult: (SerialOcrFrameResult) -> Unit,
) : ImageAnalysis.Analyzer {
    private val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    private val processing = AtomicBoolean(false)
    private var lastAcceptedFrameAtMs: Long = 0L

    override fun analyze(image: ImageProxy) {
        val now = SystemClock.elapsedRealtime()
        if (!canScan() || processing.get() || now - lastAcceptedFrameAtMs < 600L) {
            image.close()
            return
        }

        if (!onScanStarted()) {
            image.close()
            return
        }

        processing.set(true)
        lastAcceptedFrameAtMs = now

        val bitmap = runCatching { imageProxyToBitmap(image) }.getOrNull()
        image.close()
        if (bitmap == null) {
            processing.set(false)
            onScanFinished()
            return
        }

        val roiBitmap = cropCenterSerialRoi(bitmap)
        if (roiBitmap !== bitmap) bitmap.recycle()

        recognizer.process(InputImage.fromBitmap(roiBitmap, 0))
            .addOnSuccessListener { result ->
                val candidates = extractSerialCandidates(result.text)
                onFrameResult(
                    SerialOcrFrameResult(
                        bestCandidate = candidates.firstOrNull(),
                        allCandidates = candidates,
                        debugText = result.text.trim(),
                    )
                )
            }
            .addOnFailureListener {
                onFrameResult(
                    SerialOcrFrameResult(
                        bestCandidate = null,
                        allCandidates = emptyList(),
                        debugText = "",
                    )
                )
            }
            .addOnCompleteListener {
                roiBitmap.recycle()
                processing.set(false)
                onScanFinished()
            }
    }
}

private fun cropCenterSerialRoi(source: Bitmap): Bitmap {
    val width = source.width
    val height = source.height
    if (width <= 0 || height <= 0) return source

    val roiWidth = (width * 0.8f).toInt().coerceAtLeast(1)
    val roiHeight = (height * 0.16f).toInt().coerceAtLeast(1)
    val left = ((width - roiWidth) / 2).coerceAtLeast(0)
    val top = ((height - roiHeight) / 2).coerceAtLeast(0)
    val safeWidth = roiWidth.coerceAtMost(width - left)
    val safeHeight = roiHeight.coerceAtMost(height - top)

    return Bitmap.createBitmap(source, left, top, safeWidth, safeHeight)
}

private fun extractSerialCandidates(rawText: String): List<String> {
    if (rawText.isBlank()) return emptyList()

    val lines = rawText
        .lines()
        .map { sanitizeSerialText(it) }
        .filter { it.length >= MIN_SERIAL_LENGTH }

    val fullText = sanitizeSerialText(rawText)
    val merged = if (lines.size > 1) sanitizeSerialText(lines.joinToString("")) else ""

    return buildList {
        addAll(lines)
        if (fullText.length >= MIN_SERIAL_LENGTH) add(fullText)
        if (merged.length >= MIN_SERIAL_LENGTH) add(merged)
    }
        .map { it.uppercase() }
        .distinct()
        .sortedWith(
            compareByDescending<String> { token -> token.any(Char::isLetter) && token.any(Char::isDigit) }
                .thenByDescending { it.length }
        )
}

private fun sanitizeSerialText(value: String): String {
    return value
        .replace(Regex("\\s+"), "")
        .replace(Regex("[^A-Za-z0-9\\-/]"), "")
        .trim()
}

private fun imageProxyToBitmap(image: ImageProxy): Bitmap? {
    val nv21 = yuv420888ToNv21(image)
    val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
    val out = ByteArrayOutputStream()
    yuvImage.compressToJpeg(Rect(0, 0, image.width, image.height), 92, out)
    val bytes = out.toByteArray()
    var bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return null

    val rotation = image.imageInfo.rotationDegrees
    if (rotation == 0) return bitmap

    val matrix = android.graphics.Matrix().apply { postRotate(rotation.toFloat()) }
    val rotated = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    bitmap.recycle()
    bitmap = rotated
    return bitmap
}

private fun yuv420888ToNv21(image: ImageProxy): ByteArray {
    val width = image.width
    val height = image.height
    val ySize = width * height
    val uvSize = width * height / 4
    val nv21 = ByteArray(ySize + uvSize * 2)

    image.planes[0].buffer.toByteArray(nv21, 0, ySize)

    val uBuffer = image.planes[1].buffer
    val vBuffer = image.planes[2].buffer
    val chromaRowStride = image.planes[1].rowStride
    val chromaPixelStride = image.planes[1].pixelStride

    var outputOffset = ySize
    val uBytes = ByteArray(uBuffer.remaining())
    val vBytes = ByteArray(vBuffer.remaining())
    uBuffer.get(uBytes)
    vBuffer.get(vBytes)

    for (row in 0 until height / 2) {
        val rowStart = row * chromaRowStride
        for (col in 0 until width / 2) {
            val index = rowStart + col * chromaPixelStride
            nv21[outputOffset++] = vBytes[index]
            nv21[outputOffset++] = uBytes[index]
        }
    }

    return nv21
}

private fun ByteBuffer.toByteArray(destination: ByteArray, offset: Int, length: Int) {
    rewind()
    get(destination, offset, length)
}
