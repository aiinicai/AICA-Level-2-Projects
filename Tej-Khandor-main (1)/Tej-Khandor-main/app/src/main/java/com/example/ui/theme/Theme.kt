package com.example.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme =
  darkColorScheme(
    primary = EmeraldAccent,
    onPrimary = SlateNavy900,
    primaryContainer = SlateNavy800,
    onPrimaryContainer = EmeraldContainer,
    secondary = BlueAccent,
    onSecondary = Color.White,
    secondaryContainer = SlateNavy700,
    onSecondaryContainer = BlueContainer,
    background = NeutralDarkBackground,
    onBackground = NeutralDarkTextPrimary,
    surface = NeutralDarkSurface,
    onSurface = NeutralDarkTextPrimary,
    surfaceVariant = NeutralDarkSurfaceVariant,
    onSurfaceVariant = NeutralDarkTextSecondary,
    outline = NeutralDarkBorder,
    error = CrimsonAccent,
    onError = Color.White
  )

private val LightColorScheme =
  lightColorScheme(
    primary = SlateNavy900,
    onPrimary = Color.White,
    primaryContainer = SlateNavy800,
    onPrimaryContainer = Color.White,
    secondary = EmeraldPrimary,
    onSecondary = Color.White,
    secondaryContainer = EmeraldContainer,
    onSecondaryContainer = EmeraldOnContainer,
    tertiary = BlueAccent,
    onTertiary = Color.White,
    background = NeutralLightBackground,
    onBackground = NeutralTextPrimary,
    surface = NeutralLightSurface,
    onSurface = NeutralTextPrimary,
    surfaceVariant = NeutralLightSurfaceVariant,
    onSurfaceVariant = NeutralTextSecondary,
    outline = NeutralLightBorder,
    error = CrimsonPrimary,
    onError = Color.White
  )

@Composable
fun MyApplicationTheme(
  darkTheme: Boolean = isSystemInDarkTheme(),
  dynamicColor: Boolean = false, // Use intentional financial palette
  content: @Composable () -> Unit,
) {
  val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

  MaterialTheme(colorScheme = colorScheme, typography = Typography, content = content)
}
