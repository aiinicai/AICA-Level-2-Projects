package com.example.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = MintGreenPrimaryDark,
    onPrimary = Color(0xFF003830),
    primaryContainer = MintGreenContainerDark,
    onPrimaryContainer = Color(0xFFCCFBF1),
    secondary = LavenderSecondaryDark,
    onSecondary = Color(0xFF2E1065),
    secondaryContainer = Color(0xFF4C1D95),
    onSecondaryContainer = Color(0xFFEDE9FE),
    tertiary = GoldAccentDark,
    onTertiary = Color(0xFF451A03),
    tertiaryContainer = Color(0xFF78350F),
    onTertiaryContainer = Color(0xFFFEF3C7),
    background = DarkBackground,
    onBackground = Color(0xFFE6F4EA),
    surface = DarkSurface,
    onSurface = Color(0xFFE6F4EA),
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = Color(0xFFA7D5C5)
)

private val LightColorScheme = lightColorScheme(
    primary = MintGreenPrimary,
    onPrimary = Color.White,
    primaryContainer = MintGreenContainer,
    onPrimaryContainer = MintGreenOnContainer,
    secondary = LavenderSecondary,
    onSecondary = Color.White,
    secondaryContainer = LavenderContainer,
    onSecondaryContainer = LavenderOnContainer,
    tertiary = GoldAccent,
    onTertiary = Color.White,
    tertiaryContainer = GoldContainer,
    onTertiaryContainer = GoldOnContainer,
    background = CreamBackground,
    onBackground = Color(0xFF132B22),
    surface = CreamSurface,
    onSurface = Color(0xFF132B22),
    surfaceVariant = SurfaceVariant,
    onSurfaceVariant = Color(0xFF2D5A4C)
)

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
