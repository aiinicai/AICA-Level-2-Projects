import 'dart:io';

import 'package:family_vault/src/platform/device_settings.dart';
import 'package:flutter_test/flutter_test.dart';

/// This device's own settings: the shared folder, the device name, and when a
/// sync last ran.
///
/// Worth its own tests for one reason: this is the only file the application
/// writes in the clear, so what it does and does not contain matters.
void main() {
  late Directory temporary;
  late FileDeviceSettingsStore store;

  setUp(() {
    temporary = Directory.systemTemp.createTempSync('fv-device-test');
    store = FileDeviceSettingsStore(directory: temporary);
  });

  tearDown(() {
    if (temporary.existsSync()) {
      temporary.deleteSync(recursive: true);
    }
  });

  File settingsFile() =>
      File('${temporary.path}${Platform.pathSeparator}device.json');

  group('an empty store', () {
    test('reports nothing configured rather than failing', () async {
      final DeviceSettings read = await store.read();
      expect(read.syncConfigured, isFalse);
      expect(read.syncFolder, isNull);
      expect(read.deviceName, isNull);
    });

    test('writes no file until there is something to write', () async {
      await store.read();
      expect(settingsFile().existsSync(), isFalse);
    });
  });

  group('round trip', () {
    test('keeps the folder, the name and the last sync time', () async {
      final DateTime when = DateTime.utc(2026, 11, 10, 9, 30);
      await store.write(
        DeviceSettings(
          syncFolder: '/home/someone/Drive/FamilyVault',
          deviceName: 'laptop',
          lastSyncedAt: when,
        ),
      );

      final DeviceSettings read = await store.read();
      expect(read.syncFolder, '/home/someone/Drive/FamilyVault');
      expect(read.deviceName, 'laptop');
      expect(read.lastSyncedAt, when);
      expect(read.syncConfigured, isTrue);
    });

    test('creates the directory if it is not there yet', () async {
      final Directory missing = Directory(
        '${temporary.path}${Platform.pathSeparator}nested',
      );
      final FileDeviceSettingsStore nested = FileDeviceSettingsStore(
        directory: missing,
      );

      await nested.write(
        const DeviceSettings(syncFolder: '/somewhere', deviceName: 'phone'),
      );

      expect((await nested.read()).deviceName, 'phone');
    });
  });

  group('what the file holds', () {
    test('holds nothing secret', () async {
      await store.write(
        const DeviceSettings(
          syncFolder: '/home/someone/Drive/FamilyVault',
          deviceName: 'laptop',
        ),
      );

      // Written in the clear, so the test states what may be in it. Three
      // keys, and no fourth: a password, a key or the vault's sync secret
      // must never find its way in here.
      final String text = await settingsFile().readAsString();
      expect(text, contains('syncFolder'));
      expect(text, contains('deviceName'));
      expect(text, contains('lastSyncedAt'));
      expect(text, isNot(contains('secret')));
      expect(text, isNot(contains('password')));
      expect(text, isNot(contains('key')));
    });
  });

  group('a damaged file', () {
    test('is treated as empty rather than stopping the app', () async {
      settingsFile().writeAsStringSync('this is not json at all {{{');

      final DeviceSettings read = await store.read();

      expect(read.syncConfigured, isFalse);
    });

    test('with the wrong shape is treated as empty', () async {
      settingsFile().writeAsStringSync('["not", "an", "object"]');
      expect((await store.read()).syncConfigured, isFalse);
    });

    test('with an empty folder is treated as not configured', () async {
      // An empty string would otherwise pass the null check and have sync try
      // to list the current working directory.
      settingsFile().writeAsStringSync(
        '{"syncFolder": "", "deviceName": "laptop"}',
      );
      expect((await store.read()).syncConfigured, isFalse);
    });

    test('with a bad timestamp keeps the rest', () async {
      settingsFile().writeAsStringSync(
        '{"syncFolder": "/x", "deviceName": "laptop", '
        '"lastSyncedAt": "not a date"}',
      );

      final DeviceSettings read = await store.read();
      expect(read.syncConfigured, isTrue);
      expect(read.lastSyncedAt, isNull);
    });
  });

  group('turning sync off', () {
    test('clears everything, so nothing is half-configured', () async {
      const DeviceSettings on = DeviceSettings(
        syncFolder: '/x',
        deviceName: 'laptop',
      );

      final DeviceSettings off = on.copyWith(clearSync: true);

      expect(off.syncFolder, isNull);
      expect(off.deviceName, isNull);
      expect(off.lastSyncedAt, isNull);
      expect(off.syncConfigured, isFalse);
    });
  });
}
