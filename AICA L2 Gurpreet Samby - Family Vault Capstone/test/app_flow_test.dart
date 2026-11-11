import 'package:family_vault/src/app/family_vault_app.dart';
import 'package:family_vault/src/app/vault_session.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';
import 'support/in_memory_device_settings.dart';
import 'support/in_memory_vault_repository.dart';

/// End-to-end tests of the interface, driven the way a person would drive it.
///
/// These run against the real widgets and the real session, with only the
/// cryptography and the file system replaced, so what they prove is that the
/// screens are actually wired to the vault — not merely that they render.
void main() {
  late InMemoryVaultRepository repository;
  late InMemoryDeviceSettingsStore deviceStore;
  late VaultSession session;

  setUp(() {
    repository = InMemoryVaultRepository();
    deviceStore = InMemoryDeviceSettingsStore();
    session = VaultSession(
      crypto: FakeCryptoService(),
      repository: repository,
      deviceSettings: deviceStore,
    );
  });

  /// Runs a test and then shuts everything down inside the test body.
  ///
  /// An unlocked vault holds a live auto-lock timer, and flutter_test fails a
  /// test that finishes with a timer still pending. A `tearDown` is too late:
  /// the check runs when the test body's fake-async zone completes, before
  /// tearDowns do. So the tree is unmounted here, which disposes the widgets
  /// and their timers, and then the session is disposed, which cancels the
  /// lock timer.
  void appTest(
    String description,
    Future<void> Function(WidgetTester tester) body,
  ) {
    testWidgets(description, (WidgetTester tester) async {
      try {
        await body(tester);
      } finally {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        session.dispose();
      }
    });
  }

  /// Starts the app in a window tall enough to show a whole screen.
  ///
  /// The default test window is 800x600, which is shorter than the setup
  /// screen. Widgets below the fold are not hit-testable, so taps on them
  /// silently do nothing - which is exactly how this suite first failed.
  Future<void> start(WidgetTester tester) async {
    // Set the physical size AND the pixel ratio. The default test view is
    // 800x600 at a device pixel ratio of 3, so setting the surface size alone
    // left the logical width around 367 - narrow enough that the shell chose
    // its phone layout, where the section list lives in a closed drawer and
    // is therefore not in the tree at all.
    tester.view.physicalSize = const Size(1400, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(FamilyVaultApp(sessionOverride: session));
    await tester.pumpAndSettle();
  }

  /// Scrolls [finder] into view, then taps it.
  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  /// Creates a vault through the interface, as a first-time user would.
  Future<void> createVault(WidgetTester tester, String password) async {
    await tester.enterText(find.byType(TextField).first, password);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(1), password);
    await tester.pumpAndSettle();
    await tapVisible(tester, find.text('I understand'));
    await tapVisible(tester, find.text('Create my vault'));
  }

  group('first run', () {
    appTest('offers to create a vault', (WidgetTester tester) async {
      await start(tester);
      expect(find.text('Set up Family Vault'), findsOneWidget);
      expect(find.text('Create my vault'), findsOneWidget);
    });

    appTest('warns that a lost password cannot be recovered', (
      WidgetTester tester,
    ) async {
      await start(tester);
      expect(
        find.textContaining('cannot be opened'),
        findsOneWidget,
        reason: 'the consequence of losing the password must be stated',
      );
    });

    appTest('will not create a vault until the warning is acknowledged', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await tester.enterText(find.byType(TextField).first, 'a long password');
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(1), 'a long password');
      await tester.pumpAndSettle();

      final Finder button = find.widgetWithText(
        FilledButton,
        'Create my vault',
      );
      expect(tester.widget<FilledButton>(button).onPressed, isNull);

      await tapVisible(tester, find.text('I understand'));
      expect(tester.widget<FilledButton>(button).onPressed, isNotNull);
    });

    appTest('will not create a vault with a short password', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await tester.enterText(find.byType(TextField).first, 'short');
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(1), 'short');
      await tester.pumpAndSettle();
      await tapVisible(tester, find.text('I understand'));

      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Create my vault'),
            )
            .onPressed,
        isNull,
      );
    });

    appTest('creating a vault opens it', (WidgetTester tester) async {
      await start(tester);
      await createVault(tester, 'a proper master password');

      expect(session.status, VaultStatus.unlocked);
      // Dashboard content, which both layouts show, rather than a sidebar
      // label that only the wide layout builds.
      expect(find.text('Your vault'), findsOneWidget);
    });
  });

  group('once a vault exists', () {
    appTest('asks for the password and opens on the right one', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await createVault(tester, 'the master password');
      session.lock();
      await tester.pumpAndSettle();

      expect(find.text('Unlock'), findsOneWidget);

      await tester.enterText(find.byType(TextField).first, 'wrong password');
      await tester.pumpAndSettle();
      await tester.tap(find.text('Unlock'));
      await tester.pumpAndSettle();
      expect(session.status, VaultStatus.locked);

      await tester.enterText(
        find.byType(TextField).first,
        'the master password',
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Unlock'));
      await tester.pumpAndSettle();
      expect(session.status, VaultStatus.unlocked);
    });
  });

  group('saving a login through the interface', () {
    appTest('it appears in the list and survives a lock', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await createVault(tester, 'the master password');

      await tester.tap(find.widgetWithText(FloatingActionButton, 'Add'));
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Name'),
        'My Bank',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Username'),
        'gurpreet',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'A-Strong-Password-99',
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      // Stored in the vault, not merely on screen.
      expect(session.data!.liveItems.length, 1);
      expect(session.data!.liveItems.single.title, 'My Bank');

      // And really written, so it comes back after locking.
      session.lock();
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byType(TextField).first,
        'the master password',
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Unlock'));
      await tester.pumpAndSettle();

      expect(session.data!.liveItems.single.title, 'My Bank');
    });

    appTest('a login with no name is refused', (WidgetTester tester) async {
      await start(tester);
      await createVault(tester, 'the master password');

      await tester.tap(find.widgetWithText(FloatingActionButton, 'Add'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      expect(find.text('Give this entry a name'), findsOneWidget);
      expect(session.data!.liveItems, isEmpty);
    });
  });

  group('secrets are not left on screen', () {
    appTest('a saved password is masked until revealed', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await createVault(tester, 'the master password');

      await tester.tap(find.widgetWithText(FloatingActionButton, 'Add'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Name'),
        'My Bank',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'TopSecret-99-Password',
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      // Saving returns to whichever section the Add button was pressed from,
      // which here is the dashboard - and the dashboard deliberately shows
      // counts only, never entry names. So go to the list to open the entry.
      await tapVisible(tester, find.text('All Items'));
      await tapVisible(tester, find.text('My Bank'));

      expect(
        find.text('TopSecret-99-Password'),
        findsNothing,
        reason: 'a password must not be on screen before it is revealed',
      );

      await tester.tap(find.byTooltip('Show'));
      await tester.pumpAndSettle();
      expect(find.text('TopSecret-99-Password'), findsOneWidget);
    });
  });

  group('locking', () {
    appTest('the lock button closes the vault and hides everything', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await createVault(tester, 'the master password');

      await tester.tap(find.byTooltip('Lock vault'));
      await tester.pumpAndSettle();

      expect(session.status, VaultStatus.locked);
      expect(session.data, isNull);
      expect(find.text('Enter your master password'), findsOneWidget);
    });
  });

  group('the generator', () {
    appTest('produces something and can be reached from the shell', (
      WidgetTester tester,
    ) async {
      await start(tester);
      await createVault(tester, 'the master password');

      await tester.tap(find.byTooltip('Password generator'));
      await tester.pumpAndSettle();

      expect(find.text('Generator'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.byType(SelectableText), findsOneWidget);
      final SelectableText shown = tester.widget<SelectableText>(
        find.byType(SelectableText),
      );
      expect(shown.data, isNotNull);
      expect(shown.data!.length, greaterThanOrEqualTo(8));
    });
  });
}
