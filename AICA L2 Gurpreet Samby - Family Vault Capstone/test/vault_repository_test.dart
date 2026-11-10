import 'dart:io';
import 'dart:typed_data';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/vault/vault_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for vault storage.
///
/// The property under test is the one that matters most in the whole project:
/// a save that is interrupted must not destroy the vault. A password manager
/// that corrupts its own file has lost everything the user entrusted to it,
/// and there is no recovering from that.
void main() {
  late Directory directory;
  late FileVaultRepository repository;

  setUp(() async {
    directory = await Directory.systemTemp.createTemp('family_vault_test');
    repository = FileVaultRepository(directory: directory);
  });

  tearDown(() async {
    if (directory.existsSync()) {
      await directory.delete(recursive: true);
    }
  });

  Uint8List bytesOf(int fill, [int length = 64]) =>
      Uint8List(length)..fillRange(0, length, fill);

  File fileIn(String name) =>
      File('${directory.path}${Platform.pathSeparator}$name');

  group('a fresh device', () {
    test('reports no vault', () async {
      expect(await repository.exists(), isFalse);
    });

    test(
      'refuses to read what is not there, with a readable message',
      () async {
        await expectLater(
          repository.read(),
          throwsA(isA<VaultFormatFailure>()),
        );
      },
    );

    test('has no backup', () async {
      expect(await repository.hasBackup(), isFalse);
      expect(await repository.restoreBackup(), isFalse);
    });
  });

  group('writing and reading', () {
    test('round-trips the exact bytes', () async {
      final Uint8List written = bytesOf(0xAB, 1024);
      await repository.write(written);
      expect(await repository.exists(), isTrue);
      expect(await repository.read(), written);
    });

    test('handles an empty vault file', () async {
      await repository.write(Uint8List(0));
      expect(await repository.read(), isEmpty);
    });

    test('creates the directory if it is missing', () async {
      await directory.delete(recursive: true);
      await repository.write(bytesOf(0x01));
      expect(await repository.exists(), isTrue);
    });

    test('reports where the file is, for the settings screen', () async {
      expect(await repository.location(), contains('vault.fvault'));
    });
  });

  group('the previous save is always recoverable', () {
    test('a second write keeps the first as a backup', () async {
      await repository.write(bytesOf(0x11));
      await repository.write(bytesOf(0x22));

      expect(await repository.read(), bytesOf(0x22));
      expect(await repository.hasBackup(), isTrue);
    });

    test('the backup can be restored, undoing the last save', () async {
      await repository.write(bytesOf(0x11));
      await repository.write(bytesOf(0x22));

      expect(await repository.restoreBackup(), isTrue);
      expect(await repository.read(), bytesOf(0x11));
    });

    test('many writes keep exactly one backup, not a growing pile', () async {
      for (int i = 1; i <= 5; i++) {
        await repository.write(bytesOf(i));
      }
      final List<String> names = directory
          .listSync()
          .map((FileSystemEntity e) => e.uri.pathSegments.last)
          .toList();
      expect(names.where((String n) => n.contains('previous')).length, 1);
      expect(await repository.read(), bytesOf(5));
    });
  });

  group('a write never leaves the vault half-written', () {
    test('no temporary file survives a completed write', () async {
      await repository.write(bytesOf(0x33));
      expect(
        fileIn('vault.fvault.writing').existsSync(),
        isFalse,
        reason: 'the temporary file should have been renamed into place',
      );
    });

    test('a leftover temporary file from a crash is harmless', () async {
      // Simulates the process dying during step 1, before anything existing
      // was touched: the real vault must be untouched and still readable.
      await repository.write(bytesOf(0x44));
      await fileIn('vault.fvault.writing').writeAsBytes(bytesOf(0x99));

      expect(await repository.read(), bytesOf(0x44));

      // And the next successful write must clear it rather than trip over it.
      await repository.write(bytesOf(0x55));
      expect(await repository.read(), bytesOf(0x55));
      expect(fileIn('vault.fvault.writing').existsSync(), isFalse);
    });

    test(
      'the vault is readable at every point across repeated writes',
      () async {
        await repository.write(bytesOf(0x01));
        for (int i = 2; i <= 10; i++) {
          await repository.write(bytesOf(i));
          // After every single write the file must be complete and current,
          // never a partial mixture of old and new.
          final Uint8List read = await repository.read();
          expect(read.length, 64);
          expect(
            read.every((int b) => b == i),
            isTrue,
            reason: 'after write $i',
          );
        }
      },
    );
  });

  group('deleting', () {
    test('removes the vault, its backup and any temporary file', () async {
      await repository.write(bytesOf(0x11));
      await repository.write(bytesOf(0x22));
      await fileIn('vault.fvault.writing').writeAsBytes(bytesOf(0x99));

      await repository.delete();

      expect(await repository.exists(), isFalse);
      expect(await repository.hasBackup(), isFalse);
      expect(fileIn('vault.fvault.writing').existsSync(), isFalse);
    });

    test('is safe to call when there is nothing to delete', () async {
      await expectLater(repository.delete(), completes);
    });
  });
}
