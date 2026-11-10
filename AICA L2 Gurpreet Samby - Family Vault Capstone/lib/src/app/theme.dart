import 'package:flutter/material.dart';

/// Light and dark themes for Family Vault.
///
/// Deliberately minimal: colour is derived from a single seed so that light and
/// dark stay consistent and accessible without hand-tuning every surface.
abstract final class AppTheme {
  /// Seed colour. A deep, calm blue - a password manager should look like a
  /// utility, not a toy.
  static const Color _seed = Color(0xFF1B5E9B);

  /// Theme used when the platform is in light mode.
  static ThemeData light() => _build(Brightness.light);

  /// Theme used when the platform is in dark mode.
  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    return ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: _seed,
        brightness: brightness,
      ),
      visualDensity: VisualDensity.adaptivePlatformDensity,
    );
  }
}
