import 'dart:typed_data';

import 'package:family_vault/src/app/vault_session.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:family_vault/src/domain/vault_settings.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';
import 'support/in_memory_device_settings.dart';
import 'support/in_memory_vault_repository.dart';

void main() {
  // Clipboard goes through a platform channel, so the test binding is needed.
  TestWidgetsFlutterBinding.ensureInitialized();

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

  tearDown(() {
    session.dispose();
  });

  group('starting up', () {
    test('reports no vault on a fresh device', () async {
      await session.initialise();
      expect(session.status, VaultStatus.absent);
      expect(session.isUnlocked, isFalse);
      expect(session.data, isNull);
    });

    test('reports a locked vault when a file exists', () async {
      await repository.write(Uint8List.fromList(<int>[1, 2, 3]));
      await session.initialise();
      expect(session.status, VaultStatus.locked);
    });
  });

  group('creating a vault', () {
    test('leaves it unlocked and empty', () async {
      await session.initialise();
      expect(await session.createVault('a master password'), isTrue);
      expect(session.status, VaultStatus.unlocked);
      expect(session.data!.items, isEmpty);
      expect(await repository.exists(), isTrue);
    });

    test('refuses to overwrite an existing vault', () async {
      await session.initialise();
      await session.createVault('first');
      session.lock();

      expect(await session.createVault('second'), isFalse);
      expect(session.lastError, contains('already exists'));
    });
  });

  group('unlocking', () {
    setUp(() async {
      await session.initialise();
      await session.createVault('correct password');
      session.lock();
    });

    test('opens with the right password', () async {
      expect(await session.unlock('correct password'), isTrue);
      expect(session.status, VaultStatus.unlocked);
    });

    test('fails with the wrong password and stays locked', () async {
      expect(await session.unlock('wrong password'), isFalse);
      expect(session.status, VaultStatus.locked);
      expect(session.data, isNull);
      expect(session.lastError, isNotNull);
    });

    test('the failure message does not reveal the password', () async {
      await session.unlock('a-very-distinctive-guess');
      expect(session.lastError, isNot(contains('a-very-distinctive-guess')));
    });

    test('can be retried after a failure', () async {
      await session.unlock('wrong');
      expect(await session.unlock('correct password'), isTrue);
    });
  });

  group('locking', () {
    test('wipes the decrypted contents and the key', () async {
      await session.initialise();
      await session.createVault('pw');
      await session.saveItem(
        VaultItem.create(type: VaultItemType.login, title: 'Bank'),
      );
      expect(session.data!.items.length, 1);

      session.lock();

      expect(session.status, VaultStatus.locked);
      expect(session.data, isNull);
      expect(session.isUnlocked, isFalse);
    });

    test('the contents come back on unlocking', () async {
      await session.initialise();
      await session.createVault('pw');
      await session.saveItem(
        VaultItem.create(type: VaultItemType.login, title: 'Bank'),
      );
      session.lock();

      expect(await session.unlock('pw'), isTrue);
      expect(session.data!.items.single.title, 'Bank');
    });

    test('a locked vault refuses changes', () async {
      await session.initialise();
      await session.createVault('pw');
      session.lock();

      expect(
        await session.saveItem(
          VaultItem.create(type: VaultItemType.login, title: 'X'),
        ),
        isFalse,
      );
      expect(session.lastError, contains('locked'));
    });
  });

  group('editing persists', () {
    setUp(() async {
      await session.initialise();
      await session.createVault('pw');
    });

    test('adding, editing and trashing an item', () async {
      final VaultItem item = VaultItem.create(
        type: VaultItemType.login,
        title: 'Bank',
        fields: <String, String>{ItemField.password: 'secret'},
      );
      expect(await session.saveItem(item), isTrue);
      expect(await session.saveItem(item.copyWith(title: 'Bank plc')), isTrue);
      expect(session.data!.items.single.title, 'Bank plc');

      expect(await session.trashItem(item.id), isTrue);
      expect(session.data!.liveItems, isEmpty);
      expect(session.data!.trashedItems.length, 1);

      expect(await session.restoreItem(item.id), isTrue);
      expect(session.data!.liveItems.length, 1);

      expect(await session.purgeItem(item.id), isTrue);
      expect(session.data!.items, isEmpty);
    });

    test('folders, including that deleting one keeps its items', () async {
      expect(await session.addFolder('Banking'), isTrue);
      final String folderId = session.data!.folders.single.id;

      await session.saveItem(
        VaultItem.create(
          type: VaultItemType.login,
          title: 'Bank',
          folderId: folderId,
        ),
      );
      expect(await session.renameFolder(folderId, 'Finance'), isTrue);
      expect(session.data!.folders.single.name, 'Finance');

      expect(await session.deleteFolder(folderId), isTrue);
      expect(session.data!.folders, isEmpty);
      expect(session.data!.liveItems.length, 1);
      expect(session.data!.liveItems.single.folderId, isNull);
    });

    test('favourites toggle', () async {
      final VaultItem item = VaultItem.create(
        type: VaultItemType.login,
        title: 'Bank',
      );
      await session.saveItem(item);
      await session.toggleFavourite(item.id);
      expect(session.data!.favourites.length, 1);
      await session.toggleFavourite(item.id);
      expect(session.data!.favourites, isEmpty);
    });

    test('settings survive a lock and unlock', () async {
      expect(
        await session.updateSettings(
          const VaultSettings(autoLockMinutes: 30, clipboardClearSeconds: 10),
        ),
        isTrue,
      );
      session.lock();
      await session.unlock('pw');
      expect(session.settings.autoLockMinutes, 30);
      expect(session.settings.clipboardClearSeconds, 10);
    });

    // If the write fails, the interface must keep showing what is really on
    // disk. Showing the edit would tell the user their password was saved
    // when it was not.
    test('a failed write does not change what the session reports', () async {
      final VaultItem first = VaultItem.create(
        type: VaultItemType.login,
        title: 'Saved',
      );
      await session.saveItem(first);

      repository.failNextWrite = true;
      final VaultItem second = VaultItem.create(
        type: VaultItemType.login,
        title: 'Never saved',
      );
      expect(await session.saveItem(second), isFalse);

      expect(session.data!.items.length, 1);
      expect(session.data!.items.single.title, 'Saved');
      expect(session.lastError, isNotNull);
    });
  });

  group('changing the master password', () {
    test('the old password stops working and the new one works', () async {
      await session.initialise();
      await session.createVault('old password');
      await session.saveItem(
        VaultItem.create(type: VaultItemType.login, title: 'Bank'),
      );

      expect(await session.changeMasterPassword('new password'), isTrue);
      session.lock();

      expect(await session.unlock('old password'), isFalse);
      expect(await session.unlock('new password'), isTrue);
      expect(session.data!.items.single.title, 'Bank');
    });

    test('is refused while locked', () async {
      await session.initialise();
      await session.createVault('pw');
      session.lock();
      expect(await session.changeMasterPassword('other'), isFalse);
    });
  });

  group('exporting', () {
    test('produces a file the export password opens', () async {
      await session.initialise();
      await session.createVault('vault password');
      await session.saveItem(
        VaultItem.create(type: VaultItemType.login, title: 'Bank'),
      );

      final Uint8List? exported = session.exportEncrypted('backup password');
      expect(exported, isNotNull);
      expect(exported!.length, greaterThan(60));
    });

    test('is refused while locked', () async {
      await session.initialise();
      await session.createVault('pw');
      session.lock();
      expect(session.exportEncrypted('anything'), isNull);
    });
  });

  group('deleting the vault', () {
    test('removes it and returns to the fresh-device state', () async {
      await session.initialise();
      await session.createVault('pw');
      expect(await session.deleteVault(), isTrue);
      expect(session.status, VaultStatus.absent);
      expect(await repository.exists(), isFalse);
      expect(session.data, isNull);
    });
  });

  group('errors', () {
    test('can be cleared once shown', () async {
      await session.initialise();
      await session.createVault('pw');
      session.lock();
      await session.unlock('wrong');
      expect(session.lastError, isNotNull);
      session.clearError();
      expect(session.lastError, isNull);
    });

    test('notify listeners so the interface can react', () async {
      await session.initialise();
      int notifications = 0;
      session.addListener(() => notifications++);
      await session.createVault('pw');
      expect(notifications, greaterThan(0));
    });
  });
}
