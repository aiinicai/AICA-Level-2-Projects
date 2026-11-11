// Settings that belong to this device rather than to the vault.
//
// Everything else the user configures lives inside the encrypted payload, so
// it travels with the vault. These two values must not: a folder path is
// meaningless on the other device, and a device name exists precisely to tell
// the two apart. Putting them in the vault would have each device overwrite
// the other's at every merge.
//
// They are stored in the clear, in the application's own support directory
// alongside the vault file. Nothing secret goes in here - no password, no key,
// no sync secret, and nothing about what the vault contains. Anyone able to
// read this file can already read the encrypted vault beside it.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

/// This device's own settings.
@immutable
final class DeviceSettings {
  const DeviceSettings({this.syncFolder, this.deviceName, this.lastSyncedAt});

  /// An empty set of settings, for a device that has never synced.
  static const DeviceSettings none = DeviceSettings();

  /// The shared folder two devices exchange files through, or null when
  /// shared-folder sync has not been set up here.
  final String? syncFolder;

  /// What this device calls itself in the shared folder, so the user can tell
  /// whose file is whose.
  final String? deviceName;

  /// When a sync last completed here.
  final DateTime? lastSyncedAt;

  /// True when there is a folder to sync through.
  bool get syncConfigured => syncFolder != null && deviceName != null;

  /// A copy with the given changes.
  DeviceSettings copyWith({
    String? syncFolder,
    String? deviceName,
    DateTime? lastSyncedAt,
    bool clearSync = false,
  }) {
    if (clearSync) {
      return const DeviceSettings();
    }
    return DeviceSettings(
      syncFolder: syncFolder ?? this.syncFolder,
      deviceName: deviceName ?? this.deviceName,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
    );
  }

  /// Stored form.
  Map<String, Object?> toJson() => <String, Object?>{
    'syncFolder': syncFolder,
    'deviceName': deviceName,
    'lastSyncedAt': lastSyncedAt?.toUtc().toIso8601String(),
  };

  /// Reads settings from stored form, tolerating anything unexpected.
  ///
  /// A damaged file must not stop the app from starting: the worst outcome of
  /// ignoring it is that sync has to be set up again.
  static DeviceSettings fromJson(Map<String, Object?> json) {
    final Object? folder = json['syncFolder'];
    final Object? name = json['deviceName'];
    final Object? synced = json['lastSyncedAt'];
    return DeviceSettings(
      syncFolder: folder is String && folder.isNotEmpty ? folder : null,
      deviceName: name is String && name.isNotEmpty ? name : null,
      lastSyncedAt: synced is String ? DateTime.tryParse(synced) : null,
    );
  }
}

/// Where this device's own settings are kept.
abstract interface class DeviceSettingsStore {
  /// Reads the settings, returning [DeviceSettings.none] when there are none.
  Future<DeviceSettings> read();

  /// Replaces the settings.
  Future<void> write(DeviceSettings settings);
}

/// A [DeviceSettingsStore] backed by a small JSON file on disk.
final class FileDeviceSettingsStore implements DeviceSettingsStore {
  FileDeviceSettingsStore({
    required this.directory,
    this.fileName = 'device.json',
  });

  /// Creates a store in the directory the platform gives this application.
  static Future<FileDeviceSettingsStore> forPlatform() async {
    final Directory directory = await getApplicationSupportDirectory();
    return FileDeviceSettingsStore(directory: directory);
  }

  /// Where the file lives.
  final Directory directory;

  /// What the file is called.
  final String fileName;

  File get _file => File('${directory.path}${Platform.pathSeparator}$fileName');

  @override
  Future<DeviceSettings> read() async {
    final File file = _file;
    if (!file.existsSync()) {
      return DeviceSettings.none;
    }
    try {
      final Object? parsed = jsonDecode(await file.readAsString());
      return parsed is Map<String, Object?>
          ? DeviceSettings.fromJson(parsed)
          : DeviceSettings.none;
    } on Object {
      // Unreadable or not JSON. Nothing here is irreplaceable, so starting
      // over beats refusing to start.
      return DeviceSettings.none;
    }
  }

  @override
  Future<void> write(DeviceSettings settings) async {
    if (!directory.existsSync()) {
      directory.createSync(recursive: true);
    }
    await _file.writeAsString(jsonEncode(settings.toJson()), flush: true);
  }
}
