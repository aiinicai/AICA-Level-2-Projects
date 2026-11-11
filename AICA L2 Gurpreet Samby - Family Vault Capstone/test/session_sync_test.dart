import 'dart:typed_data';

import 'package:family_vault/src/app/vault_session.dart';
import 'package:family_vault/src/domain/vault_data.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:family_vault/src/vault/vault_codec.dart';
import 'package:family_vault/src/vault/vault_sync.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';
import 'support/in_memory_device_settings.dart';
import 'support/in_memory_sync_folder.dart';
import 'support/in_memory_vault_repository.dart';

/// Shared-folder sync as the session drives it.
///
/// vault_sync_test.dart tests the merge-through-a-folder logic. This tests
/// the things only the session can get wrong: generating the sync secret
/// once rather than every time, re-sealing the merged vault under the
/// vault's OWN key rather than the sync secret, and refusing to do any of it
/// while locked.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeCryptoService crypto;
  late InMemoryVaultRepository repository;
  late InMemoryDeviceSettingsStore deviceStore;
  late InMemorySyncFolder folder;
  late VaultSession session;

  setUp(() {
    crypto = FakeCryptoService();
    repository = InMemoryVaultRepository();
    deviceStore = InMemoryDeviceSettingsStore();
    folder = InMemorySyncFolder();
    session = VaultSession(
      crypto: crypto,
      repository: repository,
      deviceSettings: deviceStore,
    );
  });

  tearDown(() => session.dispose());

  const String masterPassword = 'master password for the test';

  VaultItem login(String title) => VaultItem.create(
    type: VaultItemType.login,
    title: title,
    fields: <String, String>{ItemField.password: 'password-for-$title'},
  );

  Future<void> openVaultWithSyncOn() async {
    await session.createVault(masterPassword);
    await session.loadDeviceSettings();
    await session.enableSync(folder: '/shared', deviceName: 'laptop');
  }

  group('setting sync up', () {
    test('refuses while the vault is locked', () async {
      expect(
        await session.enableSync(folder: '/shared', deviceName: 'laptop'),
        isFalse,
      );
      expect(session.lastError, contains('Unlock'));
    });

    test('refuses a blank device name', () async {
      await session.createVault(masterPassword);

      expect(
        await session.enableSync(folder: '/shared', deviceName: '   '),
        isFalse,
      );
      expect(session.lastError, contains('name'));
      expect(deviceStore.stored.syncConfigured, isFalse);
    });

    test('generates a sync secret and keeps it inside the vault', () async {
      await openVaultWithSyncOn();

      final String? secret = session.data!.syncSecret;
      expect(secret, isNotNull);
      expect(secret, hasLength(64));
      expect(secret, matches(RegExp(r'^[0-9a-f]{64}$')));
      expect(session.syncReady, isTrue);
    });

    test('keeps the same secret when set up again', () async {
      // Generating a new one would orphan every file already in the folder,
      // and the other device would silently stop being readable.
      await openVaultWithSyncOn();
      final String first = session.data!.syncSecret!;

      await session.enableSync(folder: '/elsewhere', deviceName: 'laptop');

      expect(session.data!.syncSecret, first);
      expect(session.device.syncFolder, '/elsewhere');
    });

    test(
      'stores the folder and name on the device, not in the vault',
      () async {
        await openVaultWithSyncOn();

        expect(deviceStore.stored.syncFolder, '/shared');
        expect(deviceStore.stored.deviceName, 'laptop');
        // The vault payload must not carry them, or each device would overwrite
        // the other's at every merge.
        final String payload = String.fromCharCodes(session.data!.encode());
        expect(payload, isNot(contains('/shared')));
        expect(payload, isNot(contains('laptop')));
      },
    );
  });

  group('syncing', () {
    test('refuses when no folder has been chosen', () async {
      await session.createVault(masterPassword);

      expect(await session.syncNow(folderOverride: folder), isNull);
      expect(session.lastError, contains('shared folder'));
    });

    test('refuses while the vault is locked', () async {
      await openVaultWithSyncOn();
      session.lock();

      expect(await session.syncNow(folderOverride: folder), isNull);
      expect(session.lastError, contains('Unlock'));
    });

    test('merges another device in and saves the result', () async {
      await openVaultWithSyncOn();
      await session.saveItem(login('Bank'));

      // The other device, holding the same sync secret because it was set up
      // from this vault.
      final VaultCodec codec = VaultCodec(crypto);
      folder.files['vault-phone.fvault'] = codec.seal(
        masterPassword: session.data!.syncSecret!,
        payload: VaultData(
          items: <VaultItem>[login('Email')],
          syncSecret: session.data!.syncSecret,
        ).encode(),
      );

      final SyncReport? report = await session.syncNow(folderOverride: folder);

      expect(report, isNotNull, reason: session.lastError);
      expect(report!.failures, isEmpty);
      expect(
        session.data!.liveItems.map((VaultItem i) => i.title),
        containsAll(<String>['Bank', 'Email']),
      );
    });

    test('leaves the vault openable with its own master password', () async {
      // The merged vault must be re-sealed with the vault's key, not with the
      // sync secret. Getting this wrong would lock the user out of their own
      // vault with a 64-character string they have never seen.
      await openVaultWithSyncOn();
      final VaultCodec codec = VaultCodec(crypto);
      final String secret = session.data!.syncSecret!;
      folder.files['vault-phone.fvault'] = codec.seal(
        masterPassword: secret,
        payload: VaultData(
          items: <VaultItem>[login('Email')],
          syncSecret: secret,
        ).encode(),
      );

      await session.syncNow(folderOverride: folder);
      session.lock();

      expect(await session.unlock(secret), isFalse);
      expect(await session.unlock(masterPassword), isTrue);
      expect(session.data!.liveItems, hasLength(1));
    });

    test('does not rewrite the vault when nothing changed', () async {
      await openVaultWithSyncOn();
      await session.saveItem(login('Bank'));
      await session.syncNow(folderOverride: folder);
      final int writes = repository.writes;

      final SyncReport? again = await session.syncNow(folderOverride: folder);

      expect(again!.localChanged, isFalse);
      expect(repository.writes, writes);
    });

    test('records when it last ran', () async {
      await openVaultWithSyncOn();
      expect(session.device.lastSyncedAt, isNull);

      await session.syncNow(folderOverride: folder);

      expect(session.device.lastSyncedAt, isNotNull);
      expect(deviceStore.stored.lastSyncedAt, isNotNull);
    });

    test('reports a folder it cannot reach without pretending to succeed', () async {
      await openVaultWithSyncOn();
      folder.listFailure = StateError('the drive is not connected');

      final SyncReport? report = await session.syncNow(folderOverride: folder);

      expect(report, isNull);
      expect(session.lastError, isNotNull);
      // The message carries the failure's type, never a path or file contents.
      expect(session.lastError, contains('Syncing failed'));
      expect(session.lastError, isNot(contains('/shared')));
    });

    test('leaks no derived key', () async {
      await openVaultWithSyncOn();
      await session.saveItem(login('Bank'));
      await session.syncNow(folderOverride: folder);
      session.lock();

      expect(crypto.keysDisposed, crypto.keysDerived);
    });
  });

  group('turning sync off', () {
    test('clears this device\'s settings', () async {
      await openVaultWithSyncOn();

      expect(await session.disableSync(), isTrue);

      expect(session.device.syncConfigured, isFalse);
      expect(deviceStore.stored.syncConfigured, isFalse);
    });

    test('leaves the files in the folder alone', () async {
      // Deleting them would be a destructive act on a folder the other device
      // is also using, and this device cannot know what it still needs.
      await openVaultWithSyncOn();
      await session.syncNow(folderOverride: folder);
      final int before = folder.files.length;

      await session.disableSync();

      expect(folder.files, hasLength(before));
    });

    test(
      'keeps the vault\'s sync secret, so turning it back on works',
      () async {
        await openVaultWithSyncOn();
        final String secret = session.data!.syncSecret!;

        await session.disableSync();
        await session.enableSync(folder: '/shared', deviceName: 'laptop');

        expect(session.data!.syncSecret, secret);
      },
    );
  });

  group('the secret travels with the vault, not through the folder', () {
    test('a backup carries it, so the other device can be set up', () async {
      // This is the whole mechanism: one manual import gives the second
      // device the secret, and from then on neither needs a password to read
      // the other's exchange file.
      await openVaultWithSyncOn();
      final String secret = session.data!.syncSecret!;
      final Uint8List backup = session.exportEncrypted('the backup password')!;

      await session.deleteVault();
      await session.createFromBackup(
        file: backup,
        password: 'the backup password',
      );

      expect(session.data!.syncSecret, secret);
      expect(session.syncReady, isTrue);
    });

    test('a vault that has never set sync up has no secret', () async {
      await session.createVault(masterPassword);
      expect(session.data!.syncSecret, isNull);
      expect(session.syncReady, isFalse);
    });
  });
}
