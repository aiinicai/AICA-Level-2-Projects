import 'package:meta/meta.dart';

/// Per-vault preferences, stored inside the encrypted payload.
///
/// These live in the vault rather than in device settings so that they follow
/// the vault between a phone and a laptop, and so that nothing about how a
/// vault is protected is readable without opening it.
@immutable
final class VaultSettings {
  const VaultSettings({
    this.autoLockMinutes = defaultAutoLockMinutes,
    this.clipboardClearSeconds = defaultClipboardClearSeconds,
    this.lockWhenHidden = true,
  });

  /// Default inactivity timeout: five minutes.
  static const int defaultAutoLockMinutes = 5;

  /// Default clipboard lifetime: thirty seconds.
  static const int defaultClipboardClearSeconds = 30;

  /// Choices offered for auto-lock. Zero means "only when I say so".
  static const List<int> autoLockChoices = <int>[0, 1, 5, 15, 30, 60];

  /// Choices offered for clearing the clipboard. Zero means "never".
  static const List<int> clipboardChoices = <int>[0, 10, 30, 60, 120];

  /// Minutes of inactivity before the vault locks itself. Zero disables it.
  final int autoLockMinutes;

  /// Seconds before a copied password is cleared. Zero disables it.
  final int clipboardClearSeconds;

  /// Whether to lock as soon as the app is no longer on screen.
  ///
  /// On by default. Leaving a vault unlocked behind another app is how a
  /// borrowed or snatched phone gives up its contents.
  final bool lockWhenHidden;

  /// True when inactivity locking is switched on.
  bool get autoLockEnabled => autoLockMinutes > 0;

  /// True when the clipboard is cleared automatically.
  bool get clipboardClearEnabled => clipboardClearSeconds > 0;

  /// A copy with the given changes.
  VaultSettings copyWith({
    int? autoLockMinutes,
    int? clipboardClearSeconds,
    bool? lockWhenHidden,
  }) => VaultSettings(
    autoLockMinutes: autoLockMinutes ?? this.autoLockMinutes,
    clipboardClearSeconds: clipboardClearSeconds ?? this.clipboardClearSeconds,
    lockWhenHidden: lockWhenHidden ?? this.lockWhenHidden,
  );

  /// Stored form.
  Map<String, Object?> toJson() => <String, Object?>{
    'autoLockMinutes': autoLockMinutes,
    'clipboardClearSeconds': clipboardClearSeconds,
    'lockWhenHidden': lockWhenHidden,
  };

  /// Reads settings from their stored form, falling back to defaults for
  /// anything missing or out of range rather than refusing to open the vault.
  factory VaultSettings.fromJson(Map<String, Object?> json) {
    final Object? autoLock = json['autoLockMinutes'];
    final Object? clipboard = json['clipboardClearSeconds'];
    final Object? hidden = json['lockWhenHidden'];
    return VaultSettings(
      autoLockMinutes: autoLock is int && autoLock >= 0 && autoLock <= 1440
          ? autoLock
          : defaultAutoLockMinutes,
      clipboardClearSeconds:
          clipboard is int && clipboard >= 0 && clipboard <= 3600
          ? clipboard
          : defaultClipboardClearSeconds,
      lockWhenHidden: hidden is bool ? hidden : true,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is VaultSettings &&
      other.autoLockMinutes == autoLockMinutes &&
      other.clipboardClearSeconds == clipboardClearSeconds &&
      other.lockWhenHidden == lockWhenHidden;

  @override
  int get hashCode =>
      Object.hash(autoLockMinutes, clipboardClearSeconds, lockWhenHidden);
}
