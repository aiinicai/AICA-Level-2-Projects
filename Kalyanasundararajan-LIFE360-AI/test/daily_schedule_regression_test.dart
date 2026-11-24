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

  test('Same-day rescheduled reminder triggers again', () {
    expect(
      service.shouldTrigger(
        id: 'evening_walk',
        hour: 19,
        minute: 11,
        now: DateTime(2026, 11, 24, 19, 11),
      ),
      isTrue,
    );

    expect(
      service.shouldTrigger(
        id: 'evening_walk',
        hour: 19,
        minute: 14,
        now: DateTime(2026, 11, 24, 19, 14),
      ),
      isTrue,
    );
  });

  test('Rescheduled reminder does not repeat in the same minute', () {
    expect(
      service.shouldTrigger(
        id: 'evening_walk',
        hour: 19,
        minute: 11,
        now: DateTime(2026, 11, 24, 19, 11),
      ),
      isTrue,
    );

    expect(
      service.shouldTrigger(
        id: 'evening_walk',
        hour: 19,
        minute: 14,
        now: DateTime(2026, 11, 24, 19, 14),
      ),
      isTrue,
    );

    expect(
      service.shouldTrigger(
        id: 'evening_walk',
        hour: 19,
        minute: 14,
        now: DateTime(2026, 11, 24, 19, 14, 30),
      ),
      isFalse,
    );
  });

  test('Reminder works across midnight', () {
    expect(
      service.shouldTrigger(
        id: 'wellness',
        hour: 23,
        minute: 59,
        now: DateTime(2026, 11, 24, 23, 59),
      ),
      isTrue,
    );

    expect(
      service.shouldTrigger(
        id: 'wellness',
        hour: 0,
        minute: 0,
        now: DateTime(2026, 11, 25, 0, 0),
      ),
      isTrue,
    );
  });

  test('Negative scheduling times are rejected', () {
    final now = DateTime(2026, 11, 24);

    expect(
      () => service.shouldTrigger(
        id: 'test',
        hour: -1,
        minute: 0,
        now: now,
      ),
      throwsArgumentError,
    );

    expect(
      () => service.shouldTrigger(
        id: 'test',
        hour: 8,
        minute: -1,
        now: now,
      ),
      throwsArgumentError,
    );
  });

  testWidgets('Disposing the engine stops automatic checks',
      (tester) async {
    int checks = 0;

    service.start(
      onCheck: (_) {
        checks++;
      },
    );

    await tester.pump(const Duration(seconds: 2));

    service.dispose();

    final previousChecks = checks;

    await tester.pump(const Duration(seconds: 5));

    expect(service.isRunning, isFalse);
    expect(checks, previousChecks);
  });
}
