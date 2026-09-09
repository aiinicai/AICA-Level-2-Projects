package com.example.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val FinPilotDarkColorScheme = darkColorScheme(
    primary = LavenderAccent,
    onPrimary = Color(0xFF0F1115),
    primaryContainer = DarkSurfaceVariant,
    onPrimaryContainer = LavenderAccent,
    secondary = BlueAccent,
    onSecondary = Color(0xFF0F1115),
    secondaryContainer = DarkSurfaceVariant,
    onSecondaryContainer = BlueAccent,
    tertiary = MintSuccess,
    onTertiary = Color(0xFF0F1115),
    background = DarkBackground,
    onBackground = TextPrimary,
    surface = DarkSurface,
    onSurface = TextPrimary,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = TextSecondary,
    outline = DarkBorder,
    outlineVariant = DarkBorderLight,
    error = CoralExpense,
    onError = Color(0xFF0F1115)
)

@Composable
fun FinPilotTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = FinPilotDarkColorScheme,
        typography = Typography,
        content = content
    )
}

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = true,
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    FinPilotTheme(content = content)
}
