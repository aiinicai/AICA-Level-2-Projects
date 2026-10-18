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

private val SaathiDarkColorScheme = darkColorScheme(
    primary = CelestialGold,
    onPrimary = CosmicDark,
    primaryContainer = CosmicSurfaceLight,
    onPrimaryContainer = CelestialGoldLight,
    secondary = CelestialLavender,
    onSecondary = CosmicDark,
    secondaryContainer = CosmicCardElevated,
    onSecondaryContainer = Color.White,
    tertiary = CelestialRose,
    onTertiary = CosmicDark,
    background = CosmicDark,
    onBackground = TextWhite,
    surface = CosmicCard,
    onSurface = TextWhite,
    surfaceVariant = CosmicCardElevated,
    onSurfaceVariant = TextSoft,
    outline = CosmicBorder
)

private val SaathiLightColorScheme = lightColorScheme(
    primary = CelestialAmber,
    onPrimary = Color.White,
    primaryContainer = LightCardElevated,
    onPrimaryContainer = CosmicDark,
    secondary = CelestialLavender,
    onSecondary = Color.White,
    secondaryContainer = LightCardElevated,
    onSecondaryContainer = CosmicDark,
    tertiary = CelestialRose,
    onTertiary = Color.White,
    background = LightBackground,
    onBackground = LightTextDark,
    surface = LightCard,
    onSurface = LightTextDark,
    surfaceVariant = LightCardElevated,
    onSurfaceVariant = LightTextDark,
    outline = LightBorder
)

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = true, // Default to Saathi's signature celestial dark mode
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) SaathiDarkColorScheme else SaathiLightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
