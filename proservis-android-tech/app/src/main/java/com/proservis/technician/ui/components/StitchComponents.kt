package com.proservis.technician.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Call
import androidx.compose.material.icons.outlined.Directions
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.proservis.technician.ui.theme.*

/**
 * Stitch Tasarım Sistemi: Noktalı Durum Rozeti (Status Badge)
 */
@Composable
fun StitchStatusBadge(
    text: String,
    dotColor: Color,
    containerColor: Color,
    contentColor: Color,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .clip(CircleShape)
            .background(containerColor)
            .padding(horizontal = 10.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(dotColor)
        )
        Text(
            text = text,
            color = contentColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.3.sp
        )
    }
}

/**
 * Hızlı İletişim & Navigasyon Yuvarlak Butonu (44dp hit target)
 */
@Composable
fun StitchCircleIconButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    containerColor: Color = SurfaceContainerHigh,
    contentColor: Color = Primary,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .size(44.dp)
            .clip(CircleShape)
            .background(containerColor)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = contentColor,
            modifier = Modifier.size(20.dp)
        )
    }
}

/**
 * Otomatik Fark Hesaplayıcı Hap Rozet (+X.XXX Fark)
 */
@Composable
fun StitchCounterDeltaBadge(
    oldCounter: Int?,
    newCounter: Int?,
    modifier: Modifier = Modifier
) {
    if (oldCounter == null || newCounter == null) return
    val delta = newCounter - oldCounter
    val isValid = delta >= 0
    val containerColor = if (isValid) TertiaryFixed else ErrorContainer
    val contentColor = if (isValid) OnTertiaryFixed else OnErrorContainer
    val prefix = if (delta >= 0) "+" else ""

    Row(
        modifier = modifier
            .clip(CircleShape)
            .background(containerColor)
            .padding(horizontal = 8.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            text = "$prefix$delta Baskı Farkı",
            color = contentColor,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold
        )
    }
}
