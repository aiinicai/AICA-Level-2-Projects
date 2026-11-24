import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class BackupService {
  final SharedPreferencesAsync storage =
      SharedPreferencesAsync();

  static const String appName = 'LIFE360 AI';
  static const int backupVersion = 1;

  Future<String> createBackup() async {
    final preferences = await storage.getAll();

    final records = <String, Object>{};

    for (final entry in preferences.entries) {
      if (entry.key.startsWith('life360_')) {
        final value = entry.value;

if (value != null) {
  records[entry.key] = value;
}
      }
    }

    final backup = {
      'application': appName,
      'backupVersion': backupVersion,
      'createdAt': DateTime.now().toIso8601String(),
      'recordCount': records.length,
      'records': records,
    };

    return const JsonEncoder.withIndent('  ').convert(backup);
  }

  Map<String, dynamic> validateBackup(String backupText) {
    final decoded = jsonDecode(backupText);

    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Invalid backup format.');
    }

    if (decoded['application'] != appName) {
      throw const FormatException(
        'This backup does not belong to LIFE360 AI.',
      );
    }

    if (decoded['backupVersion'] != backupVersion) {
      throw const FormatException(
        'Unsupported backup version.',
      );
    }

    final records = decoded['records'];

    if (records is! Map<String, dynamic>) {
      throw const FormatException('Invalid backup records.');
    }

    if (decoded['recordCount'] != records.length) {
      throw const FormatException('Backup record count mismatch.');
    }

    for (final entry in records.entries) {
      if (!entry.key.startsWith('life360_')) {
        throw const FormatException(
          'Invalid application storage key.',
        );
      }

      final value = entry.value;

      if (value is! bool &&
          value is! int &&
          value is! double &&
          value is! String &&
          !(value is List &&
              value.every((item) => item is String))) {
        throw const FormatException(
          'Unsupported backup data type.',
        );
      }
    }

    return records;
  }
  bool isValidDate(String value) {
    final date = DateTime.tryParse(value);

    if (date == null) return false;

    final formatted =
        '${date.year.toString().padLeft(4, '0')}-'
        '${date.month.toString().padLeft(2, '0')}-'
        '${date.day.toString().padLeft(2, '0')}';

    return value == formatted;
  }

  void validateRecord(String key, Object? value) {
    const validActivities = {
      'Morning hydration',
      'Yoga / Physical exercise',
      'Meditation',
      'Medication check',
      'Plan work priorities',
      'Stand and stretch',
      'Evening walk',
      'Prepare for bedtime',
    };

    const validReminders = {
      'hydration',
      'stretch',
      'eyes',
      'breathing',
    };

    const validIntervals = {
      10, 900, 1200, 1800, 2700, 3600, 7200,
    };

    final activityMatch = RegExp(
      r'^life360_(\d{4}-\d{2}-\d{2})_(.+)$',
    ).firstMatch(key);

    if (activityMatch != null) {
      if (isValidDate(activityMatch.group(1)!) &&
          validActivities.contains(activityMatch.group(2)) &&
          value is bool) {
        return;
      }

      throw FormatException('Invalid activity record: $key');
    }

    final reminderMatch = RegExp(
      r'^life360_reminder_(.+)_seconds$',
    ).firstMatch(key);

    if (reminderMatch != null) {
      if (validReminders.contains(reminderMatch.group(1)) &&
          value is int &&
          validIntervals.contains(value)) {
        return;
      }

      throw FormatException('Invalid reminder record: $key');
    }

    final scheduleMatch = RegExp(
      r'^life360_schedule_([0-7])_(minutes|enabled|last_triggered)$',
    ).firstMatch(key);

    if (scheduleMatch != null) {
      final field = scheduleMatch.group(2);

      if (field == 'minutes' &&
          value is int &&
          value >= 0 &&
          value < 1440) {
        return;
      }

      if (field == 'enabled' && value is bool) {
        return;
      }

      if (field == 'last_triggered' && value is String) {
        if (isValidDate(value)) {
          return;
        }

        final parts = value.split('|');

        if (parts.length == 2 && isValidDate(parts[0])) {
          final minutes = int.tryParse(parts[1]);

          if (minutes != null &&
              minutes >= 0 &&
              minutes < 1440 &&
              parts[1] == minutes.toString()) {
            return;
          }
        }
      }

      throw FormatException('Invalid planner record: $key');
    }

    throw FormatException('Unknown storage record: $key');
  }

  Map<String, dynamic> validateForRestore(String backupText) {
    final records = validateBackup(backupText);

    for (final entry in records.entries) {
      validateRecord(entry.key, entry.value);
    }

    return records;
  }

  Future<int> restoreBackup(String backupText) async {
    final records = validateForRestore(backupText);

    final previousValues = await storage.getAll();
    final changedKeys = <String>[];

    try {
      for (final entry in records.entries) {
        changedKeys.add(entry.key);
        await writeRecord(entry.key, entry.value);
      }

      return records.length;
    } catch (_) {
      try {
        for (final key in changedKeys.reversed) {
          final previousValue = previousValues[key];

          if (previousValue == null) {
            await storage.remove(key);
          } else {
            await writeRecord(key, previousValue);
          }
        }
      } catch (_) {
        throw StateError(
          'Restore failed and rollback was incomplete.',
        );
      }

      throw StateError(
        'Restore failed. Previous records were recovered.',
      );
    }
  }

  Future<void> writeRecord(
    String key,
    Object? value,
  ) async {
    if (value is bool) {
      await storage.setBool(key, value);
    } else if (value is int) {
      await storage.setInt(key, value);
    } else if (value is double) {
      await storage.setDouble(key, value);
    } else if (value is String) {
      await storage.setString(key, value);
    } else if (value is List &&
        value.every((item) => item is String)) {
      await storage.setStringList(
        key,
        value.cast<String>(),
      );
    } else {
      throw FormatException(
        'Unsupported record type: $key',
      );
    }
  }


  Future<int> getRecordCount() async {
    final preferences = await storage.getAll();

    return preferences.keys
        .where((key) => key.startsWith('life360_'))
        .length;
  }
}
