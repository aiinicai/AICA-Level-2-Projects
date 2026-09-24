package com.example.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val LightColorScheme = lightColorScheme(
    primary = ElegantPrimary,
    onPrimary = ElegantOnPrimary,
    primaryContainer = ElegantPrimaryContainer,
    onPrimaryContainer = ElegantOnPrimaryContainer,
    secondary = ElegantSecondary,
    onSecondary = ElegantOnSecondary,
    secondaryContainer = ElegantSecondaryContainer,
    onSecondaryContainer = ElegantOnSecondaryContainer,
    tertiary = ElegantTertiary,
    onTertiary = ElegantOnTertiary,
    tertiaryContainer = ElegantTertiaryContainer,
    onTertiaryContainer = ElegantOnTertiaryContainer,
    background = ElegantWhiteBackground,
    onBackground = ElegantTextPrimary,
    surface = ElegantWhiteSurface,
    onSurface = ElegantTextPrimary,
    surfaceVariant = ElegantWhiteSurfaceVariant,
    onSurfaceVariant = ElegantTextSecondary,
    surfaceContainer = ElegantWhiteSurfaceContainer,
    outline = ElegantOutline,
    outlineVariant = ElegantOutlineVariant,
    error = RoseUrgent,
    onError = ElegantOnPrimary,
    errorContainer = RoseContainer,
    onErrorContainer = OnRoseContainer
)

private val DarkColorScheme = LightColorScheme // Preserving clean White aesthetic across configurations

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = false, // Clean White Theme
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colorScheme = LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
