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

private val DarkColorScheme =
  darkColorScheme(
    primary = GoldDark,
    onPrimary = NavyPrimary,
    primaryContainer = NavySecondary,
    onPrimaryContainer = GoldMuted,
    secondary = SoftSlate,
    onSecondary = NavyPrimary,
    tertiary = GoldAccent,
    background = NavyDarkBg,
    surface = NavyDarkSurface,
    surfaceVariant = NavyDarkSurfaceVariant,
    onBackground = OffWhite,
    onSurface = OffWhite,
    onSurfaceVariant = SoftSlate,
  )

private val LightColorScheme =
  lightColorScheme(
    primary = NavyPrimary,
    onPrimary = Color.White,
    primaryContainer = NavySecondary,
    onPrimaryContainer = Color.White,
    secondary = SlateBlue,
    onSecondary = Color.White,
    tertiary = GoldAccent,
    onTertiary = Color.White,
    background = BgLight,
    surface = SurfaceLight,
    surfaceVariant = SurfaceVariantLight,
    outline = BorderSlate200,
    outlineVariant = BorderSlate100,
    onBackground = TextPrimaryLight,
    onSurface = TextPrimaryLight,
    onSurfaceVariant = TextSecondaryLight,
  )

@Composable
fun MyApplicationTheme(
  darkTheme: Boolean = isSystemInDarkTheme(),
  // Dynamic color is available on Android 12+ (default false to enforce High Density theme design)
  dynamicColor: Boolean = false,
  content: @Composable () -> Unit,
) {
  val colorScheme =
    when {
      dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
        val context = LocalContext.current
        if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
      }

      darkTheme -> DarkColorScheme
      else -> LightColorScheme
    }

  MaterialTheme(colorScheme = colorScheme, typography = Typography, content = content)
}
