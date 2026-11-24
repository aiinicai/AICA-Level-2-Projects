import 'dart:async';

class ReminderService {
  Timer? _timer;

  bool get isRunning => _timer?.isActive ?? false;

  void start({
    required Duration interval,
    required void Function() onReminder,
  }) {
    if (interval <= Duration.zero) {
      throw ArgumentError('Interval must be positive.');
    }

    stop();

    _timer = Timer.periodic(interval, (_) {
      onReminder();
    });
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  void dispose() {
    stop();
  }
}