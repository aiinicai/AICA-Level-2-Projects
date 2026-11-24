import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:life360_app/services/backup_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';
class FailingBackupService extends BackupService {
  int writeAttempts = 0;
  int failOnWrite = 3;
  bool failureTriggered = false;
  bool failDuringRollback = false;

  @override
  Future<void> writeRecord(
    String key,
    Object? value,
  ) async {
    writeAttempts++;

    if (writeAttempts == failOnWrite) {
      failureTriggered = true;

      throw StateError('Simulated storage failure.');
    }

    if (failureTriggered && failDuringRollback) {
      throw StateError('Simulated rollback failure.');
    }

    await super.writeRecord(key, value);
  }
}


void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late BackupService service;
  late SharedPreferencesAsync storage;

  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();

    service = BackupService();
    storage = SharedPreferencesAsync();
  });

  tearDown(() {
    SharedPreferencesAsyncPlatform.instance = null;
  });

  test('Creates a valid empty backup', () async {
    final backup = await service.createBackup();
    final records = service.validateBackup(backup);

    expect(records, isEmpty);
  });

  test('Backs up daily activity records', () async {
    await storage.setBool(
      'life360_2026-11-24_Morning hydration',
      true,
    );

    final backup = await service.createBackup();
    final records = service.validateBackup(backup);

    expect(
      records['life360_2026-11-24_Morning hydration'],
      isTrue,
    );
  });

  test('Backs up planner schedules', () async {
    await storage.setInt(
      'life360_schedule_0_minutes',
      420,
    );

    await storage.setBool(
      'life360_schedule_0_enabled',
      true,
    );

    final backup = await service.createBackup();
    final records = service.validateBackup(backup);

    expect(records['life360_schedule_0_minutes'], 420);
    expect(records['life360_schedule_0_enabled'], isTrue);
  });

  test('Excludes unrelated storage records', () async {
    await storage.setString('other_app_data', 'private');

    final backup = await service.createBackup();
    final records = service.validateBackup(backup);

    expect(records.containsKey('other_app_data'), isFalse);
  });

  test('Rejects invalid JSON', () {
    expect(
      () => service.validateBackup('invalid backup'),
      throwsFormatException,
    );
  });

  test('Rejects backups from other applications', () {
    final backup = jsonEncode({
      'application': 'Other App',
      'backupVersion': 1,
      'recordCount': 0,
      'records': {},
    });

    expect(
      () => service.validateBackup(backup),
      throwsFormatException,
    );
  });

  test('Rejects unsupported backup versions', () {
    final backup = jsonEncode({
      'application': 'LIFE360 AI',
      'backupVersion': 999,
      'recordCount': 0,
      'records': {},
    });

    expect(
      () => service.validateBackup(backup),
      throwsFormatException,
    );
  });

  test('Counts application records correctly', () async {
    await storage.setBool('life360_test_activity', true);
    await storage.setInt('life360_test_reminder', 1800);
    await storage.setString('unrelated_key', 'ignore');

    expect(await service.getRecordCount(), 2);
  });
    test('Restores activity records successfully', () async {
    const key = 'life360_2026-11-24_Morning hydration';

    await storage.setBool(key, true);

    final backup = await service.createBackup();

    await storage.remove(key);

    expect(await storage.getBool(key), isNull);

    final restored = await service.restoreBackup(backup);

    expect(restored, 1);
    expect(await storage.getBool(key), isTrue);
  });

  test('Restores planner settings correctly', () async {
    await storage.setInt('life360_schedule_0_minutes', 420);
    await storage.setBool('life360_schedule_0_enabled', true);

    final backup = await service.createBackup();

    await storage.remove('life360_schedule_0_minutes');
    await storage.remove('life360_schedule_0_enabled');

    expect(await service.restoreBackup(backup), 2);

    expect(
      await storage.getInt('life360_schedule_0_minutes'),
      420,
    );

    expect(
      await storage.getBool('life360_schedule_0_enabled'),
      isTrue,
    );
  });

  test('Restores reminder preferences correctly', () async {
    const key = 'life360_reminder_hydration_seconds';

    await storage.setInt(key, 1800);

    final backup = await service.createBackup();

    await storage.setInt(key, 3600);

    await service.restoreBackup(backup);

    expect(await storage.getInt(key), 1800);
  });

  test('Restore preserves records outside the backup', () async {
    await storage.setBool(
      'life360_2026-11-24_Morning hydration',
      true,
    );

    final backup = await service.createBackup();

    await storage.setString('unrelated_key', 'preserve');

    await storage.setBool(
      'life360_2026-11-25_Meditation',
      true,
    );

    await service.restoreBackup(backup);

    expect(
      await storage.getString('unrelated_key'),
      'preserve',
    );

    expect(
      await storage.getBool(
        'life360_2026-11-25_Meditation',
      ),
      isTrue,
    );
  });

  test('Rejects invalid reminder frequencies', () async {
    const key = 'life360_reminder_hydration_seconds';

    await storage.setInt(key, 999);

    final backup = await service.createBackup();

    await storage.setInt(key, 1800);

    await expectLater(
      service.restoreBackup(backup),
      throwsFormatException,
    );

    expect(await storage.getInt(key), 1800);
  });

  test('Rejects invalid planner times', () async {
    await storage.setInt(
      'life360_schedule_0_minutes',
      1500,
    );

    final backup = await service.createBackup();

    expect(
      () => service.validateForRestore(backup),
      throwsFormatException,
    );
  });

  test('Rejects invalid dates before restoring any records',
      () async {
    const validKey = 'life360_2026-11-24_Morning hydration';

    await storage.setBool(validKey, true);

    await storage.setBool(
      'life360_2026-02-30_Meditation',
      true,
    );

    final backup = await service.createBackup();

    await storage.setBool(validKey, false);

    await expectLater(
      service.restoreBackup(backup),
      throwsFormatException,
    );

    expect(await storage.getBool(validKey), isFalse);
  });
  test('Rollback recovers overwritten records', () async {
    const key1 = 'life360_2026-11-24_Morning hydration';
    const key2 = 'life360_2026-11-24_Meditation';
    const key3 = 'life360_schedule_0_minutes';

    await storage.setBool(key1, true);
    await storage.setBool(key2, true);
    await storage.setInt(key3, 420);

    final backup = await service.createBackup();

    await storage.setBool(key1, false);
    await storage.setBool(key2, false);
    await storage.setInt(key3, 480);

    final failingService = FailingBackupService();

    await expectLater(
      failingService.restoreBackup(backup),
      throwsA(
        isA<StateError>().having(
          (error) => error.message,
          'message',
          'Restore failed. Previous records were recovered.',
        ),
      ),
    );

    expect(failingService.failureTriggered, isTrue);
    expect(await storage.getBool(key1), isFalse);
    expect(await storage.getBool(key2), isFalse);
    expect(await storage.getInt(key3), 480);
  });

  test('Rollback removes newly inserted records', () async {
    const key1 = 'life360_2026-11-24_Morning hydration';
    const key2 = 'life360_2026-11-24_Meditation';
    const key3 = 'life360_schedule_0_minutes';

    await storage.setBool(key1, true);
    await storage.setBool(key2, true);
    await storage.setInt(key3, 420);

    final backup = await service.createBackup();

    await storage.remove(key1);
    await storage.remove(key2);
    await storage.remove(key3);

    await storage.setString(
      'unrelated_key',
      'preserve',
    );

    final failingService = FailingBackupService();

    await expectLater(
      failingService.restoreBackup(backup),
      throwsStateError,
    );

    expect(failingService.failureTriggered, isTrue);
    expect(await storage.getBool(key1), isNull);
    expect(await storage.getBool(key2), isNull);
    expect(await storage.getInt(key3), isNull);

    expect(
      await storage.getString('unrelated_key'),
      'preserve',
    );
  });

  test('Reports incomplete rollback accurately', () async {
    const key1 = 'life360_2026-11-24_Morning hydration';
    const key2 = 'life360_2026-11-24_Meditation';
    const key3 = 'life360_schedule_0_minutes';

    await storage.setBool(key1, true);
    await storage.setBool(key2, true);
    await storage.setInt(key3, 420);

    final backup = await service.createBackup();

    await storage.setBool(key1, false);
    await storage.setBool(key2, false);
    await storage.setInt(key3, 480);

    final failingService = FailingBackupService()
      ..failDuringRollback = true;

    await expectLater(
      failingService.restoreBackup(backup),
      throwsA(
        isA<StateError>().having(
          (error) => error.message,
          'message',
          'Restore failed and rollback was incomplete.',
        ),
      ),
    );

    expect(failingService.failureTriggered, isTrue);
  });

}
