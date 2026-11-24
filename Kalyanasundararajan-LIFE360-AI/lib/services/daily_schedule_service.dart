
import 'dart:async';

class DailyScheduleService {
  Timer? _timer;

  final Map<String, String> _lastTriggered = {};

  bool get isRunning => _timer?.isActive ?? false;

  void start({
    required void Function(DateTime now) onCheck,
    DateTime Function()? now,
  }) {
    stop();

    final clock = now ?? DateTime.now;

    _timer = Timer.periodic(
      const Duration(seconds: 1),
      (_) {
        onCheck(clock());
      },
    );

    onCheck(clock());
  }

  bool shouldTrigger({
    required String id,
    required int hour,
    required int minute,
    required DateTime now,
  }) {
    if (hour < 0 || hour > 23) {
      throw ArgumentError('Invalid hour.');
    }

    if (minute < 0 || minute > 59) {
      throw ArgumentError('Invalid minute.');
    }

    if (now.hour != hour || now.minute != minute) {
      return false;
    }

    final dateKey =
        '${now.year}-'
        '${now.month.toString().padLeft(2, '0')}-'
        '${now.day.toString().padLeft(2, '0')}';

    final occurrenceKey =
        '$id|$dateKey|$hour|$minute';

    if (_lastTriggered[id] == occurrenceKey) {
      return false;
    }

    _lastTriggered[id] = occurrenceKey;

    return true;
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  void dispose() {
    stop();
    _lastTriggered.clear();
  }
}
