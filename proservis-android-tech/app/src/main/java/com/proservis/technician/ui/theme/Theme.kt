package com.proservis.technician.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = BluePrimary,
    primaryContainer = BluePrimaryContainer,
)

private val DarkColors = darkColorScheme(
    primary = BluePrimary,
    primaryContainer = BluePrimaryContainer,
)

@Composable
fun ProservisTechTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        typography = AppTypography,
        content = content,
    )
}

