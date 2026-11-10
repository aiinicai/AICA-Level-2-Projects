import 'package:family_vault/src/platform/device_settings.dart';

/// A device-settings store that keeps its contents in memory.
///
/// The real one writes a small JSON file; which directory it writes to is
/// tested against the real file system in device_settings_test.dart. This
/// keeps the session tests free of disk.
final class InMemoryDeviceSettingsStore implements DeviceSettingsStore {
  DeviceSettings _settings = DeviceSettings.none;

  /// How many times the settings were written.
  int writes = 0;

  /// What is currently stored, for assertions.
  DeviceSettings get stored => _settings;

  @override
  Future<DeviceSettings> read() async => _settings;

  @override
  Future<void> write(DeviceSettings settings) async {
    writes++;
    _settings = settings;
  }
}
