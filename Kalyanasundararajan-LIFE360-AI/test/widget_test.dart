import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life360_app/main.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_platform_interface/in_memory_shared_preferences_async.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_async_platform_interface.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferencesAsyncPlatform.instance =
        InMemorySharedPreferencesAsync.empty();
  });

  tearDown(() {
    SharedPreferencesAsyncPlatform.instance = null;
  });

  Future<void> prepareScreen(WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 2400));

    addTearDown(() => tester.binding.setSurfaceSize(null));
  }

  Future<void> completeActivity(WidgetTester tester, String activity) async {
    final tile = find.widgetWithText(CheckboxListTile, activity);

    expect(tile, findsOneWidget);

    final checkbox = find.descendant(of: tile, matching: find.byType(Checkbox));

    expect(checkbox, findsOneWidget);

    await tester.ensureVisible(checkbox);
    await tester.tap(checkbox);
    await tester.pumpAndSettle();
  }

  testWidgets('LIFE360 AI dashboard loads correctly', (
    WidgetTester tester,
  ) async {
    await prepareScreen(tester);

    await tester.pumpWidget(const Life360App());
    await tester.pumpAndSettle();

    expect(find.text('LIFE360 AI'), findsOneWidget);
    expect(find.text('0 of 8 activities completed'), findsOneWidget);
    expect(find.text('Morning hydration'), findsOneWidget);
  });

  testWidgets('Completing an activity updates progress', (
    WidgetTester tester,
  ) async {
    await prepareScreen(tester);

    await tester.pumpWidget(const Life360App());
    await tester.pumpAndSettle();

    expect(find.text('0 of 8 activities completed'), findsOneWidget);

    await completeActivity(tester, 'Morning hydration');

    expect(find.text('1 of 8 activities completed'), findsOneWidget);

    final progress = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );

    expect(progress.value, 0.125);
  });

  testWidgets('Saved progress is restored after reopening', (
    WidgetTester tester,
  ) async {
    await prepareScreen(tester);

    final date = DateTime(2026, 11, 24, 10);

    await tester.pumpWidget(Life360App(now: () => date));
    await tester.pumpAndSettle();

    await completeActivity(tester, 'Morning hydration');

    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();

    await tester.pumpWidget(Life360App(now: () => date));
    await tester.pumpAndSettle();

    expect(find.text('1 of 8 activities completed'), findsOneWidget);
  });

  testWidgets('Activities reset automatically after midnight', (
    WidgetTester tester,
  ) async {
    await prepareScreen(tester);

    var date = DateTime(2026, 11, 24, 23, 59, 45);

    await tester.pumpWidget(Life360App(now: () => date));
    await tester.pumpAndSettle();

    await completeActivity(tester, 'Morning hydration');
    await completeActivity(tester, 'Yoga / Physical exercise');
    await completeActivity(tester, 'Meditation');

    expect(find.text('3 of 8 activities completed'), findsOneWidget);

    date = DateTime(2026, 11, 25, 0, 0, 15);

    await tester.pump(const Duration(seconds: 30));
    await tester.pumpAndSettle();

    await tester.drag(
  find.byType(ListView).first,
  const Offset(0, 1500),
);

await tester.pumpAndSettle();

expect(find.text('Date: 2026-11-25'), findsOneWidget);

    expect(find.text('0 of 8 activities completed'), findsOneWidget);
  });

  testWidgets('Previous day records survive the daily reset', (
    WidgetTester tester,
  ) async {
    await prepareScreen(tester);

    var date = DateTime(2026, 11, 24, 23, 59, 45);

    await tester.pumpWidget(Life360App(now: () => date));
    await tester.pumpAndSettle();

    await completeActivity(tester, 'Morning hydration');

    date = DateTime(2026, 11, 25, 0, 0, 15);

    await tester.pump(const Duration(seconds: 30));
    await tester.pumpAndSettle();

    expect(find.text('0 of 8 activities completed'), findsOneWidget);

    final storage = SharedPreferencesAsync();

    expect(
      await storage.getBool('life360_2026-11-24_Morning hydration'),
      isTrue,
    );

    await tester.tap(find.byTooltip('7-Day Activity History'));
    await tester.pumpAndSettle();

    expect(find.text('7-Day Activity History'), findsOneWidget);

    expect(find.text('2026-11-24'), findsOneWidget);

    expect(find.text('1 of 8 completed (12.5%)'), findsOneWidget);

    await tester.tap(find.text('Close'));
    await tester.pumpAndSettle();
  });
}
