import 'package:flutter_test/flutter_test.dart';
import 'package:life360_app/services/reminder_service.dart';

void main() {
  late ReminderService service;

  setUp(() {
    service = ReminderService();
  });

  tearDown(() {
    service.dispose();
  });

  testWidgets('Reminder engine starts correctly', (tester) async {
    expect(service.isRunning, isFalse);

    service.start(
      interval: const Duration(seconds: 5),
      onReminder: () {},
    );

    expect(service.isRunning, isTrue);

    service.stop();
  });

  testWidgets('Reminder triggers at the correct interval', (tester) async {
    int count = 0;

    service.start(
      interval: const Duration(seconds: 5),
      onReminder: () {
        count++;
      },
    );

    await tester.pump(const Duration(seconds: 4));
    expect(count, 0);

    await tester.pump(const Duration(seconds: 1));
    expect(count, 1);

    await tester.pump(const Duration(seconds: 5));
    expect(count, 2);

    service.stop();
  });

  testWidgets('Reminder stops correctly', (tester) async {
    int count = 0;

    service.start(
      interval: const Duration(seconds: 5),
      onReminder: () {
        count++;
      },
    );

    await tester.pump(const Duration(seconds: 5));
    expect(count, 1);

    service.stop();

    await tester.pump(const Duration(seconds: 10));

    expect(count, 1);
    expect(service.isRunning, isFalse);
  });

  testWidgets('Restarting does not create duplicate timers', (tester) async {
    int count = 0;

    service.start(
      interval: const Duration(seconds: 5),
      onReminder: () {
        count++;
      },
    );

    service.start(
      interval: const Duration(seconds: 5),
      onReminder: () {
        count++;
      },
    );

    await tester.pump(const Duration(seconds: 5));

    expect(count, 1);

    service.stop();
  });

  test('Invalid reminder intervals are rejected', () {
    expect(
      () => service.start(
        interval: Duration.zero,
        onReminder: () {},
      ),
      throwsArgumentError,
    );

    expect(
      () => service.start(
        interval: const Duration(seconds: -1),
        onReminder: () {},
      ),
      throwsArgumentError,
    );
  });

  testWidgets('Disposing releases reminder resources', (tester) async {
    int count = 0;

    service.start(
      interval: const Duration(seconds: 5),
      onReminder: () {
        count++;
      },
    );

    service.dispose();

    await tester.pump(const Duration(seconds: 10));

    expect(service.isRunning, isFalse);
    expect(count, 0);
  });
}