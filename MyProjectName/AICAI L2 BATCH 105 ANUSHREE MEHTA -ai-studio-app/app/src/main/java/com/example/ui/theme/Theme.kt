package com.example.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import com.example.data.model.UserRole

private val SeniorLightScheme = lightColorScheme(
    primary = EnglishSagePrimary,
    onPrimary = Color.White,
    primaryContainer = EnglishSageContainer,
    onPrimaryContainer = EnglishSageOnContainer,
    secondary = SacredTerracotta,
    onSecondary = Color.White,
    tertiary = SacredGold,
    background = EnglishCreamBackground,
    surface = EnglishCreamSurface,
    onBackground = EnglishForestCharcoal,
    onSurface = EnglishForestCharcoal,
    surfaceVariant = EnglishCreamSurfaceVariant,
    onSurfaceVariant = EnglishTextSecondary,
    outline = EnglishSageBorder,
    outlineVariant = EnglishCreamBorder
)

private val SeniorDarkScheme = darkColorScheme(
    primary = Color(0xFF86A789),
    onPrimary = Color(0xFF132217),
    primaryContainer = Color(0xFF283D2F),
    onPrimaryContainer = Color(0xFFD4E6D9),
    secondary = Color(0xFFE07A5F),
    onSecondary = Color(0xFF3E1A11),
    tertiary = Color(0xFFF4D06F),
    background = DarkBg,
    surface = DarkSurface,
    onBackground = DarkTextPrimary,
    onSurface = DarkTextPrimary,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = DarkTextSecondary,
    outline = DarkBorder,
    outlineVariant = DarkBorder
)

private val ChildLightScheme = lightColorScheme(
    primary = ChildSaffronPrimary,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFEF3C7),
    onPrimaryContainer = Color(0xFF78350F),
    secondary = ChildPeacockBlue,
    onSecondary = Color.White,
    tertiary = SacredTerracotta,
    background = ChildCreamBg,
    surface = Color.White,
    onBackground = Color(0xFF1F2937),
    onSurface = Color(0xFF1F2937),
    outline = Color(0xFFF59E0B),
    outlineVariant = Color(0xFFFDE68A)
)

private val ParentLightScheme = lightColorScheme(
    primary = ParentRoyalBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDBEAFE),
    onPrimaryContainer = Color(0xFF1E3A8A),
    secondary = ParentSafetyEmerald,
    onSecondary = Color.White,
    background = ParentSlateBg,
    surface = Color.White,
    onBackground = Color(0xFF0F172A),
    onSurface = Color(0xFF0F172A),
    outline = Color(0xFF94A3B8),
    outlineVariant = Color(0xFFCBD5E1)
)

/** User-selectable colour palettes. `null` in [GenerationsTheme] means the original per-profile colours. */
enum class AppPalette(
    val label: String,
    val swatch: Color,
    val scheme: androidx.compose.material3.ColorScheme
) {
    MUSTARD(
        "Mustard Yellow", Color(0xFFE1AD01),
        lightColorScheme(
            primary = Color(0xFFE1AD01), onPrimary = Color(0xFF2B2100),
            primaryContainer = Color(0xFFFBF1CC), onPrimaryContainer = Color(0xFF2B2410),
            secondary = Color(0xFFB88A00), onSecondary = Color.White, tertiary = Color(0xFFB88A00),
            background = Color(0xFFFFFAEB), surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF2B2410), onSurface = Color(0xFF2B2410),
            surfaceVariant = Color(0xFFFBF1CC), onSurfaceVariant = Color(0xFF6B5E2E),
            outline = Color(0xFFD9B94A), outlineVariant = Color(0xFFEFD98A)
        )
    ),
    SALMON(
        "Salmon Pink", Color(0xFFE9857B),
        lightColorScheme(
            primary = Color(0xFFC95F57), onPrimary = Color.White,
            primaryContainer = Color(0xFFFDE6E2), onPrimaryContainer = Color(0xFF3B1E1B),
            secondary = Color(0xFFA8493F), onSecondary = Color.White, tertiary = Color(0xFFA8493F),
            background = Color(0xFFFFF5F3), surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF3B1E1B), onSurface = Color(0xFF3B1E1B),
            surfaceVariant = Color(0xFFFDE6E2), onSurfaceVariant = Color(0xFF7A4A45),
            outline = Color(0xFFE8A39C), outlineVariant = Color(0xFFF4C9C4)
        )
    ),
    SLATE(
        "Greyish Blue", Color(0xFF6F8BA8),
        lightColorScheme(
            primary = Color(0xFF58728F), onPrimary = Color.White,
            primaryContainer = Color(0xFFE3EAF2), onPrimaryContainer = Color(0xFF1B2633),
            secondary = Color(0xFF3F566F), onSecondary = Color.White, tertiary = Color(0xFF3F566F),
            background = Color(0xFFF3F6FA), surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF1B2633), onSurface = Color(0xFF1B2633),
            surfaceVariant = Color(0xFFE3EAF2), onSurfaceVariant = Color(0xFF4A5B6F),
            outline = Color(0xFF9DB0C6), outlineVariant = Color(0xFFC9D5E3)
        )
    ),
    PEARL(
        "Pearl White", Color(0xFFF3F0E8),
        lightColorScheme(
            primary = Color(0xFF55525C), onPrimary = Color.White,
            primaryContainer = Color(0xFFEFECE6), onPrimaryContainer = Color(0xFF24222A),
            secondary = Color(0xFF3F3D45), onSecondary = Color.White, tertiary = Color(0xFF3F3D45),
            background = Color(0xFFF8F6F1), surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF24222A), onSurface = Color(0xFF24222A),
            surfaceVariant = Color(0xFFEFECE6), onSurfaceVariant = Color(0xFF5E5B64),
            outline = Color(0xFFC9C4B8), outlineVariant = Color(0xFFE2DED3)
        )
    ),
    SAGE(
        "Light Sage Green", Color(0xFF9DB89A),
        lightColorScheme(
            primary = Color(0xFF5E8562), onPrimary = Color.White,
            primaryContainer = Color(0xFFE3EEE2), onPrimaryContainer = Color(0xFF1C2A1E),
            secondary = Color(0xFF47694B), onSecondary = Color.White, tertiary = Color(0xFF47694B),
            background = Color(0xFFF4F8F2), surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF1C2A1E), onSurface = Color(0xFF1C2A1E),
            surfaceVariant = Color(0xFFE3EEE2), onSurfaceVariant = Color(0xFF4B5F4D),
            outline = Color(0xFFA9C4A6), outlineVariant = Color(0xFFCFE0CD)
        )
    )
}

@Composable
fun GenerationsTheme(
    role: UserRole = UserRole.SENIOR,
    darkTheme: Boolean = isSystemInDarkTheme(),
    palette: AppPalette? = null,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        darkTheme -> SeniorDarkScheme
        palette != null -> palette.scheme
        role == UserRole.CHILD -> ChildLightScheme
        role == UserRole.PARENT -> ParentLightScheme
        else -> SeniorLightScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = SeniorTypography,
        content = content
    )
}

@Composable
fun GenerationsConnectTheme(
    currentRole: UserRole = UserRole.SENIOR,
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    GenerationsTheme(role = currentRole, darkTheme = darkTheme, content = content)
}

