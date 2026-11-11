import 'dart:typed_data';

import 'package:family_vault/src/app/vault_session.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:family_vault/src/vault/vault_merge.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';
import 'support/in_memory_device_settings.dart';
import 'support/in_memory_vault_repository.dart';

/// Export, read back, and merge — the three steps of moving a vault between
/// devices, tested as one chain.
///
/// Testing them separately would miss the failure that matters: an export
/// that writes something the import cannot read. So every test here starts
/// from bytes that a real export actually produced.
void main() {
  // VaultSession registers itself as a WidgetsBindingObserver so it can lock
  // when the app goes to the background, and dispose() unregisters it. Both
  // need a binding, even in a test with no widgets.
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeCryptoService crypto;
  late InMemoryVaultRepository repository;
  late InMemoryDeviceSettingsStore deviceStore;
  late VaultSession session;

  setUp(() {
    crypto = FakeCryptoService();
    repository = InMemoryVaultRepository();
    deviceStore = InMemoryDeviceSettingsStore();
    session = VaultSession(
      crypto: crypto,
      repository: repository,
      deviceSettings: deviceStore,
    );
  });

  tearDown(() => session.dispose());

  VaultItem login(String title, {String password = 'a-good-password-99'}) =>
      VaultItem.create(
        type: VaultItemType.login,
        title: title,
        fields: <String, String>{ItemField.password: password},
      );

  /// A vault with [titles] in it, exported under [password].
  Future<Uint8List> exportWith({
    required String password,
    List<String> titles = const <String>['Bank'],
  }) async {
    await session.createVault('master password for the test');
    for (final String title in titles) {
      await session.saveItem(login(title));
    }
    final Uint8List? bytes = session.exportEncrypted(password);
    expect(
      bytes,
      isNotNull,
      reason: session.lastError ?? 'export returned null',
    );
    return bytes!;
  }

  group('export', () {
    test('refuses while the vault is locked', () async {
      expect(session.exportEncrypted('anything'), isNull);
      expect(session.lastError, contains('Unlock'));
    });

    test('writes a file the import can read', () async {
      final Uint8List file = await exportWith(
        password: 'the backup password',
        titles: <String>['Bank', 'Email'],
      );

      final BackupContents? read = await session.readBackup(
        file: file,
        password: 'the backup password',
        fileName: 'test.fvault',
      );

      expect(read, isNotNull, reason: session.lastError);
      expect(read!.liveItems, 2);
      expect(read.dropped, 0, reason: 'nothing may be silently lost');
      expect(read.fileName, 'test.fvault');
    });

    test('can use a password of its own, not the vault\'s', () async {
      final Uint8List file = await exportWith(password: 'separate backup one');

      expect(
        await session.readBackup(file: file, password: 'separate backup one'),
        isNotNull,
      );
      expect(
        await session.readBackup(
          file: file,
          password: 'master password for the test',
        ),
        isNull,
        reason: 'the vault password must not open a separately-keyed backup',
      );
    });

    test('leaks no key, whether the password is right or wrong', () async {
      final Uint8List file = await exportWith(password: 'the backup password');
      await session.readBackup(file: file, password: 'the backup password');
      await session.readBackup(file: file, password: 'the wrong one');
      session.lock();

      expect(
        crypto.keysDisposed,
        crypto.keysDerived,
        reason: 'every derived key must be wiped',
      );
    });
  });

  group('reading a backup', () {
    test(
      'rejects the wrong password without saying which part was wrong',
      () async {
        final Uint8List file = await exportWith(
          password: 'right password here',
        );

        expect(
          await session.readBackup(file: file, password: 'wrong password here'),
          isNull,
        );
        // The message must leave the two causes indistinguishable. "Wrong
        // password" would confirm to someone holding a stolen file that the
        // file itself is intact and worth attacking; "file damaged" would
        // send an honest user hunting for a corruption that is not there. So
        // it names both and commits to neither.
        expect(session.lastError, contains('password may be wrong'));
        expect(session.lastError, contains('changed or damaged'));
      },
    );

    test('rejects a file that is not a vault at all', () async {
      await session.createVault('master password for the test');

      expect(
        await session.readBackup(
          file: Uint8List.fromList(List<int>.filled(64, 7)),
          password: 'anything',
        ),
        isNull,
      );
      expect(session.lastError, isNotNull);
    });

    test('changes nothing in the open vault', () async {
      final Uint8List file = await exportWith(
        password: 'the backup password',
        titles: <String>['Bank'],
      );
      await session.saveItem(login('Added after the export'));
      final int before = repository.writes;

      await session.readBackup(file: file, password: 'the backup password');

      expect(session.data!.liveItems, hasLength(2));
      expect(repository.writes, before, reason: 'reading must not save');
    });
  });

  group('merging a backup in', () {
    test('brings across what only the other device had', () async {
      final Uint8List file = await exportWith(
        password: 'the backup password',
        titles: <String>['Bank', 'Email'],
      );
      // Stand in for the other device: start again, with one of its own.
      await session.deleteVault();
      await session.createVault('master password for the test');
      await session.saveItem(login('Only here'));

      final BackupContents backup = (await session.readBackup(
        file: file,
        password: 'the backup password',
      ))!;
      final MergeOutcome? outcome = await session.mergeBackup(backup);

      expect(outcome, isNotNull, reason: session.lastError);
      expect(outcome!.itemsAdded, 2);
      expect(
        session.data!.liveItems.map((VaultItem i) => i.title),
        containsAll(<String>['Bank', 'Email', 'Only here']),
      );
    });

    test('keeps the vault openable with its own password afterwards', () async {
      // The merged result must be sealed under the vault's key, not the
      // backup's. Getting this wrong locks the user out of their own vault
      // with a password they never chose.
      final Uint8List file = await exportWith(
        password: 'the backup password',
        titles: <String>['Bank'],
      );
      await session.deleteVault();
      await session.createVault('master password for the test');

      final BackupContents backup = (await session.readBackup(
        file: file,
        password: 'the backup password',
      ))!;
      await session.mergeBackup(backup);
      session.lock();

      expect(await session.unlock('the backup password'), isFalse);
      expect(await session.unlock('master password for the test'), isTrue);
      expect(session.data!.liveItems, hasLength(1));
    });

    test('is safe to repeat: the second merge changes nothing', () async {
      final Uint8List file = await exportWith(
        password: 'the backup password',
        titles: <String>['Bank', 'Email'],
      );
      await session.deleteVault();
      await session.createVault('master password for the test');

      final BackupContents backup = (await session.readBackup(
        file: file,
        password: 'the backup password',
      ))!;
      await session.mergeBackup(backup);
      final int writesAfterFirst = repository.writes;

      final MergeOutcome? again = await session.mergeBackup(backup);

      expect(again!.hadChanges, isFalse);
      expect(again.summary, 'Already up to date.');
      expect(
        repository.writes,
        writesAfterFirst,
        reason: 'a no-op merge must not rewrite the vault',
      );
    });

    test('refuses while the vault is locked', () async {
      final Uint8List file = await exportWith(password: 'the backup password');
      final BackupContents backup = (await session.readBackup(
        file: file,
        password: 'the backup password',
      ))!;
      session.lock();

      expect(await session.mergeBackup(backup), isNull);
      expect(session.lastError, contains('Unlock'));
    });
  });

  group('restoring onto a device with no vault', () {
    test(
      'rebuilds the vault from the file, keyed by the backup password',
      () async {
        final Uint8List file = await exportWith(
          password: 'the backup password',
          titles: <String>['Bank', 'Email'],
        );
        await session.deleteVault();
        expect(session.status, VaultStatus.absent);

        final bool restored = await session.createFromBackup(
          file: file,
          password: 'the backup password',
        );

        expect(restored, isTrue, reason: session.lastError);
        expect(session.status, VaultStatus.unlocked);
        expect(session.data!.liveItems, hasLength(2));

        session.lock();
        expect(await session.unlock('the backup password'), isTrue);
      },
    );

    test(
      'refuses when a vault already exists, rather than overwriting it',
      () async {
        final Uint8List file = await exportWith(
          password: 'the backup password',
          titles: <String>['Bank'],
        );
        await session.saveItem(login('Must survive'));

        final bool restored = await session.createFromBackup(
          file: file,
          password: 'the backup password',
        );

        expect(restored, isFalse);
        expect(session.lastError, contains('already exists'));
        expect(
          session.data!.liveItems.map((VaultItem i) => i.title),
          contains('Must survive'),
        );
      },
    );

    test('refuses a wrong password without creating a vault', () async {
      final Uint8List file = await exportWith(password: 'right password here');
      await session.deleteVault();

      expect(
        await session.createFromBackup(
          file: file,
          password: 'wrong password here',
        ),
        isFalse,
      );
      expect(await repository.exists(), isFalse);
      expect(session.status, VaultStatus.absent);
    });
  });

  group('verifying the master password before a backup', () {
    test('accepts the right one and rejects the wrong one', () async {
      await session.createVault('master password for the test');

      expect(
        await session.verifyMasterPassword('master password for the test'),
        isTrue,
      );
      expect(await session.verifyMasterPassword('something else'), isFalse);
    });

    test('leaves the session unlocked and its key intact', () async {
      await session.createVault('master password for the test');
      await session.saveItem(login('Bank'));

      await session.verifyMasterPassword('master password for the test');
      await session.verifyMasterPassword('wrong');

      expect(session.isUnlocked, isTrue);
      // Still able to save, which it could not do with a disposed key.
      expect(await session.saveItem(login('Email')), isTrue);
      expect(session.data!.liveItems, hasLength(2));
    });
  });
}
