import 'package:flutter_test/flutter_test.dart';
import 'package:life360_app/services/daily_schedule_service.dart';

void main() {
  late DailyScheduleService service;

  setUp(() {
    service = DailyScheduleService();
  });

  tearDown(() {
    service.dispose();
  });

  test('Reminder triggers at the scheduled time', () {
    expect(
      service.shouldTrigger(
        id: 'hydration',
        hour: 8,
        minute: 30,
        now: DateTime(2026, 11, 24, 8, 30),
      ),
      isTrue,
    );
  });

  test('Reminder does not trigger at the wrong time', () {
    expect(
      service.shouldTrigger(
        id: 'hydration',
        hour: 8,
        minute: 30,
        now: DateTime(2026, 11, 24, 8, 29),
      ),
      isFalse,
    );
  });

  test('Duplicate reminders are prevented on the same day', () {
    final now = DateTime(2026, 11, 24, 8, 30);

    expect(
      service.shouldTrigger(
        id: 'hydration',
        hour: 8,
        minute: 30,
        now: now,
      ),
      isTrue,
    );

    expect(
      service.shouldTrigger(
        id: 'hydration',
        hour: 8,
        minute: 30,
        now: now,
      ),
      isFalse,
    );
  });

  test('Reminder triggers again on the following day', () {
    for (final day in [24, 25]) {
      expect(
        service.shouldTrigger(
          id: 'hydration',
          hour: 8,
          minute: 30,
          now: DateTime(2026, 11, day, 8, 30),
        ),
        isTrue,
      );
    }
  });

  test('Independent schedules can trigger together', () {
    final now = DateTime(2026, 11, 24, 8, 30);

    for (final id in ['hydration', 'meditation']) {
      expect(
        service.shouldTrigger(
          id: id,
          hour: 8,
          minute: 30,
          now: now,
        ),
        isTrue,
      );
    }
  });

  test('Invalid scheduling times are rejected', () {
    final now = DateTime(2026, 11, 24);

    expect(
      () => service.shouldTrigger(
        id: 'test',
        hour: 24,
        minute: 0,
        now: now,
      ),
      throwsArgumentError,
    );

    expect(
      () => service.shouldTrigger(
        id: 'test',
        hour: 8,
        minute: 60,
        now: now,
      ),
      throwsArgumentError,
    );
  });

  testWidgets('Scheduling engine checks time automatically',
      (tester) async {
    int checks = 0;

    service.start(
      onCheck: (_) {
        checks++;
      },
    );

    expect(service.isRunning, isTrue);
    expect(checks, 1);

    await tester.pump(const Duration(seconds: 3));

    expect(checks, 4);

    service.stop();
  });

  testWidgets('Stopping the engine prevents further checks',
      (tester) async {
    int checks = 0;

    service.start(
      onCheck: (_) {
        checks++;
      },
    );

    await tester.pump(const Duration(seconds: 2));

    service.stop();

    final previousChecks = checks;

    await tester.pump(const Duration(seconds: 5));

    expect(service.isRunning, isFalse);
    expect(checks, previousChecks);
  });
}