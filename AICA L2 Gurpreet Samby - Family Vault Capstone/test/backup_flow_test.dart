import 'package:family_vault/src/app/family_vault_app.dart';
import 'package:family_vault/src/app/vault_session.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';
import 'support/fake_file_transfer.dart';
import 'support/in_memory_device_settings.dart';
import 'support/in_memory_vault_repository.dart';

/// The backup screen, driven the way a person would drive it.
///
/// What this is really for: proving that the file the export writes is the
/// file the import reads. Both halves can look correct on their own and still
/// not fit together, and the day that is discovered is the day someone needs
/// their backup.
void main() {
  late InMemoryVaultRepository repository;
  late InMemoryDeviceSettingsStore deviceStore;
  late VaultSession session;
  late FakeFileTransfer files;

  setUp(() {
    repository = InMemoryVaultRepository();
    deviceStore = InMemoryDeviceSettingsStore();
    session = VaultSession(
      crypto: FakeCryptoService(),
      repository: repository,
      deviceSettings: deviceStore,
    );
    files = FakeFileTransfer();
  });

  /// See the note in app_flow_test.dart: an unlocked vault holds a live
  /// auto-lock timer, and a pending timer fails the test before any tearDown
  /// gets a chance to run.
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

  Future<void> start(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1400, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      FamilyVaultApp(sessionOverride: session, fileTransferOverride: files),
    );
    await tester.pumpAndSettle();
  }

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  /// Creates the vault through the interface, as a first-time user would.
  ///
  /// It has to be the interface rather than a direct session call: the app's
  /// own startup calls VaultSession.initialise, which sets the status from
  /// whether a vault file exists - so a vault created before the app starts
  /// comes back as locked and the test lands on the unlock screen.
  Future<void> createVaultThroughUi(
    WidgetTester tester,
    String password,
  ) async {
    await tester.enterText(find.byType(TextField).first, password);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(1), password);
    await tester.pumpAndSettle();
    await tapVisible(tester, find.text('I understand'));
    await tapVisible(tester, find.text('Create my vault'));
  }

  Future<void> openBackupScreen(WidgetTester tester) async {
    await start(tester);
    await createVaultThroughUi(tester, 'master password for the test');
    await session.saveItem(
      VaultItem.create(
        type: VaultItemType.login,
        title: 'Bank',
        fields: const <String, String>{ItemField.password: 'a-password-99'},
      ),
    );
    await tester.pumpAndSettle();
    await tapVisible(tester, find.text('Backup & Transfer'));
  }

  /// Fills the two separate-password fields and saves.
  Future<void> exportWithSeparatePassword(
    WidgetTester tester,
    String password,
  ) async {
    await tapVisible(tester, find.byKey(const Key('backup-own-password')));
    await tester.enterText(find.byKey(const Key('backup-password')), password);
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('backup-password-confirm')),
      password,
    );
    await tester.pumpAndSettle();
    await tapVisible(tester, find.byKey(const Key('backup-export')));
  }

  String notice(WidgetTester tester) =>
      tester.widget<Text>(find.byKey(const Key('backup-notice'))).data!;

  group('the backup screen', () {
    appTest('explains what the file is before anything is written', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);

      expect(find.text('Make a backup'), findsOneWidget);
      expect(find.textContaining('encrypted copy'), findsOneWidget);
      expect(
        find.textContaining('Nothing is uploaded anywhere'),
        findsOneWidget,
        reason: 'the user must be told the app does not send their vault off',
      );
    });

    appTest('offers to save on a platform that has a save dialog', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);
      expect(find.text('Save a copy'), findsOneWidget);
    });

    appTest('offers to share where there is no save dialog, as on Android', (
      WidgetTester tester,
    ) async {
      files = FakeFileTransfer(hasSaveDialog: false);
      await openBackupScreen(tester);
      expect(find.text('Share a copy'), findsOneWidget);
      expect(find.text('Save a copy'), findsNothing);
    });
  });

  group('exporting', () {
    appTest('writes a file and says where it went', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);
      await exportWithSeparatePassword(tester, 'the separate backup password');

      expect(files.saved, hasLength(1));
      expect(files.saved.single.name, endsWith('.fvault'));
      expect(files.saved.single.bytes, isNotEmpty);
      expect(notice(tester), contains('Backup saved to'));
    });

    appTest('will not write anything when the two passwords differ', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);
      await tapVisible(tester, find.byKey(const Key('backup-own-password')));
      await tester.enterText(
        find.byKey(const Key('backup-password')),
        'one password',
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('backup-password-confirm')),
        'a different one',
      );
      await tester.pumpAndSettle();
      await tapVisible(tester, find.byKey(const Key('backup-export')));

      expect(files.saved, isEmpty);
      expect(notice(tester), contains('do not match'));
    });

    appTest('reports a cancelled save as having written nothing', (
      WidgetTester tester,
    ) async {
      files.cancelSave = true;
      await openBackupScreen(tester);
      await exportWithSeparatePassword(tester, 'the separate backup password');

      expect(files.saved, isEmpty);
      expect(notice(tester), contains('Nothing was written'));
    });
  });

  group('importing what was exported', () {
    appTest('reads the file back and merges it', (WidgetTester tester) async {
      await openBackupScreen(tester);
      await exportWithSeparatePassword(tester, 'the separate backup password');
      files.offerLastSavedForPicking();

      await tapVisible(tester, find.byKey(const Key('backup-import')));
      await tester.enterText(
        find.byKey(const Key('transfer-password')),
        'the separate backup password',
      );
      await tester.pumpAndSettle();
      await tapVisible(tester, find.widgetWithText(FilledButton, 'Continue'));

      // The file is described before anything is applied.
      expect(find.text('Merge this backup in?'), findsOneWidget);
      expect(find.text('1 entry'), findsOneWidget);

      await tapVisible(tester, find.widgetWithText(FilledButton, 'Merge'));

      // Merging a vault with its own backup must be a no-op, which is the
      // cheapest available proof that the round trip is lossless.
      expect(notice(tester), 'Already up to date.');
      expect(session.data!.liveItems, hasLength(1));
    });

    appTest('changes nothing when the user backs out of the merge', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);
      await exportWithSeparatePassword(tester, 'the separate backup password');
      files.offerLastSavedForPicking();

      await tapVisible(tester, find.byKey(const Key('backup-import')));
      await tester.enterText(
        find.byKey(const Key('transfer-password')),
        'the separate backup password',
      );
      await tester.pumpAndSettle();
      await tapVisible(tester, find.widgetWithText(FilledButton, 'Continue'));
      await tapVisible(tester, find.widgetWithText(TextButton, 'Cancel'));

      expect(notice(tester), contains('Nothing was changed'));
    });

    appTest('refuses the wrong password and applies nothing', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);
      await exportWithSeparatePassword(tester, 'the separate backup password');
      files.offerLastSavedForPicking();

      await tapVisible(tester, find.byKey(const Key('backup-import')));
      await tester.enterText(
        find.byKey(const Key('transfer-password')),
        'not the backup password',
      );
      await tester.pumpAndSettle();
      await tapVisible(tester, find.widgetWithText(FilledButton, 'Continue'));

      expect(find.text('Merge this backup in?'), findsNothing);
      expect(find.byKey(const Key('backup-notice')), findsOneWidget);
    });

    appTest('does nothing at all when no file is chosen', (
      WidgetTester tester,
    ) async {
      await openBackupScreen(tester);
      files.nextPick = null;

      await tapVisible(tester, find.byKey(const Key('backup-import')));

      expect(files.pickCount, 1);
      expect(find.byKey(const Key('backup-notice')), findsNothing);
    });
  });

  group('the shared-folder card', () {
    appTest('is shown on a normal build', (WidgetTester tester) async {
      await openBackupScreen(tester);
      expect(
        find.text('Keep two devices in step through a shared folder'),
        findsOneWidget,
      );
    });

    appTest('does nothing when no folder is chosen', (
      WidgetTester tester,
    ) async {
      // On the web this is the only outcome: a browser gives a page access to
      // files the user picks, never to a folder it can list and write to
      // later.
      files.nextFolder = null;
      await openBackupScreen(tester);

      await tapVisible(tester, find.byKey(const Key('sync-choose-folder')));

      expect(find.byKey(const Key('sync-device-name')), findsNothing);
      expect(session.device.syncConfigured, isFalse);
    });

    appTest('sets up sharing once a folder and a name are given', (
      WidgetTester tester,
    ) async {
      files.nextFolder = '/shared/FamilyVault';
      await openBackupScreen(tester);

      await tapVisible(tester, find.byKey(const Key('sync-choose-folder')));
      await tester.enterText(
        find.byKey(const Key('sync-device-name')),
        'laptop',
      );
      await tester.pumpAndSettle();
      await tapVisible(
        tester,
        find.widgetWithText(FilledButton, 'Use this name'),
      );

      expect(session.device.syncFolder, '/shared/FamilyVault');
      expect(session.device.deviceName, 'laptop');
      expect(
        session.data!.syncSecret,
        isNotNull,
        reason: 'the sync secret is generated when sharing is set up',
      );
      // Setting up runs a sync straight away, which cannot reach a folder
      // that does not exist, so the failure is reported rather than hidden.
      expect(find.byKey(const Key('sync-notice')), findsOneWidget);
    });
  });

  group('restoring on a device with no vault', () {
    appTest('is offered on the setup screen', (WidgetTester tester) async {
      await start(tester);
      expect(
        find.byKey(const Key('create-restore')),
        findsOneWidget,
        reason:
            'a replaced device reaches the setup screen and nowhere else, so '
            'restoring has to be reachable from here',
      );
    });

    appTest('rebuilds the vault from a backup file', (
      WidgetTester tester,
    ) async {
      // Make a backup, then wipe the device and restore onto it.
      await openBackupScreen(tester);
      await exportWithSeparatePassword(tester, 'the separate backup password');
      files.offerLastSavedForPicking();
      await session.deleteVault();
      await tester.pumpAndSettle();

      expect(find.text('Set up Family Vault'), findsOneWidget);

      await tapVisible(tester, find.byKey(const Key('create-restore')));
      await tester.enterText(
        find.byKey(const Key('restore-password')),
        'the separate backup password',
      );
      await tester.pumpAndSettle();
      await tapVisible(tester, find.widgetWithText(FilledButton, 'Restore'));

      expect(session.status, VaultStatus.unlocked);
      expect(session.data!.liveItems, hasLength(1));
      expect(session.data!.liveItems.single.title, 'Bank');
    });
  });
}
