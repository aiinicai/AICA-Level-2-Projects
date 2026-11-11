import 'dart:io' as io;
import 'dart:typed_data';

import 'package:family_vault/src/domain/vault_data.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:family_vault/src/vault/vault_codec.dart';
import 'package:family_vault/src/vault/vault_sync.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';
import 'support/in_memory_sync_folder.dart';

/// Syncing through a folder both devices can see.
///
/// The risks this is written against, in order of how much damage each would
/// do: a device reading its own file back and fighting itself; one bad file
/// stopping the whole sync; a device's file going missing from the folder so
/// the others stop seeing it; and a three-device family where two devices
/// never meet directly.
void main() {
  const String secret =
      '00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff';
  const String otherSecret =
      'ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100';

  late FakeCryptoService crypto;
  late VaultCodec codec;
  late InMemorySyncFolder folder;

  setUp(() {
    crypto = FakeCryptoService();
    codec = VaultCodec(crypto);
    folder = InMemorySyncFolder();
  });

  VaultItem login(String title, {int minute = 0}) {
    final DateTime stamp = DateTime.utc(
      2026,
      11,
      1,
      12,
    ).add(Duration(minutes: minute));
    return VaultItem.create(
      type: VaultItemType.login,
      title: title,
      fields: <String, String>{ItemField.password: 'password-for-$title'},
      now: stamp,
    );
  }

  VaultData vaultWith(List<VaultItem> items) =>
      VaultData(items: items, syncSecret: secret);

  /// Puts a device's file in the folder, sealed as that device would seal it.
  void placeFile(
    String deviceName,
    VaultData data, {
    String sealWith = secret,
  }) {
    folder.files[VaultSync.fileNameFor(deviceName)] = codec.seal(
      masterPassword: sealWith,
      payload: data.encode(),
    );
  }

  VaultSync syncFor() => VaultSync(codec: codec, folder: folder);

  Future<SyncReport> run(VaultData local, {String device = 'laptop'}) =>
      syncFor().run(local: local, syncSecret: secret, deviceName: device);

  group('naming a device\'s file', () {
    test('turns a name into something a file system accepts', () {
      expect(VaultSync.fileNameFor('laptop'), 'vault-laptop.fvault');
      expect(
        VaultSync.fileNameFor('Gurpreet\'s Phone'),
        'vault-gurpreet-s-phone.fvault',
      );
      expect(
        VaultSync.fileNameFor('  spaced  out  '),
        'vault-spaced-out.fvault',
      );
    });

    test('never produces an empty or path-bearing name', () {
      // A name made only of punctuation, or one containing a separator, must
      // not become a file that escapes the folder.
      expect(VaultSync.fileNameFor('***'), 'vault-device.fvault');
      expect(VaultSync.fileNameFor('../../etc/passwd'), isNot(contains('/')));
      expect(VaultSync.fileNameFor('..\\..\\windows'), isNot(contains('\\')));
    });

    test('is stable, so a device keeps writing the same file', () {
      expect(VaultSync.fileNameFor('phone'), VaultSync.fileNameFor('phone'));
    });
  });

  group('a folder with nobody else in it', () {
    test('writes this device\'s file and says so', () async {
      final SyncReport report = await run(
        vaultWith(<VaultItem>[login('Bank')]),
      );

      expect(report.peers, isEmpty);
      expect(report.wroteOwnFile, isTrue);
      expect(folder.written, <String>['vault-laptop.fvault']);
      expect(report.summary, contains('No other device'));
      expect(report.localChanged, isFalse);
    });

    test(
      'writes a file the other device can open with the same secret',
      () async {
        await run(vaultWith(<VaultItem>[login('Bank')]));

        final Uint8List written = folder.files['vault-laptop.fvault']!;
        final VaultData read = VaultData.decode(
          codec.open(file: written, masterPassword: secret),
        ).data;
        expect(read.liveItems.single.title, 'Bank');
      },
    );

    test('writes even when there was nothing to merge', () async {
      // A device whose file is missing from the folder is invisible to the
      // others, so skipping the write on a no-op would be the one failure
      // that quietly stops sync working at all.
      await run(VaultData(syncSecret: secret));
      expect(folder.files, contains('vault-laptop.fvault'));
    });
  });

  group('two devices', () {
    test('each gains what only the other had', () async {
      placeFile('phone', vaultWith(<VaultItem>[login('Email', minute: 5)]));

      final SyncReport report = await run(
        vaultWith(<VaultItem>[login('Bank')]),
      );

      expect(report.failures, isEmpty);
      expect(report.localChanged, isTrue);
      expect(
        report.merged.liveItems.map((VaultItem i) => i.title),
        containsAll(<String>['Bank', 'Email']),
      );
      expect(report.peers.single.itemsTaken, 1);
    });

    test('the device never reads its own file back', () async {
      // Reading its own file would mean merging with a copy of itself. Mostly
      // harmless, but it would report changes that did not happen and would
      // resurrect anything deleted since that file was written.
      final VaultData mine = vaultWith(<VaultItem>[login('Bank')]);
      await run(mine);

      final SyncReport second = await run(mine);

      expect(second.peers, isEmpty, reason: 'own file must be skipped');
      expect(second.localChanged, isFalse);
    });

    test('a deletion here survives the other device\'s older copy', () async {
      final VaultItem gone = login('Old');
      final VaultData before = vaultWith(<VaultItem>[gone]);
      placeFile('phone', before);

      final VaultData after = before
          .trashItem(gone.id, now: DateTime.utc(2026, 11, 1, 13))
          .purgeItem(gone.id, now: DateTime.utc(2026, 11, 1, 13, 1));

      final SyncReport report = await run(after);

      expect(report.merged.items, isEmpty);
      expect(report.merged.tombstones, hasLength(1));
    });

    test('syncing twice changes nothing the second time', () async {
      placeFile('phone', vaultWith(<VaultItem>[login('Email', minute: 5)]));
      final SyncReport first = await run(vaultWith(<VaultItem>[login('Bank')]));

      final SyncReport second = await run(first.merged);

      expect(second.localChanged, isFalse);
      expect(second.outcome?.hadChanges ?? false, isFalse);
    });
  });

  group('three devices that never meet directly', () {
    test('the third picks up the first through the second', () async {
      // phone and tablet have never synced with each other. The laptop syncs
      // with both, and writes the merged result back, so the next device to
      // sync sees everything.
      placeFile('phone', vaultWith(<VaultItem>[login('Email', minute: 5)]));
      placeFile('tablet', vaultWith(<VaultItem>[login('Shop', minute: 6)]));

      await run(vaultWith(<VaultItem>[login('Bank')]), device: 'laptop');

      final VaultData laptopFile = VaultData.decode(
        codec.open(
          file: folder.files['vault-laptop.fvault']!,
          masterPassword: secret,
        ),
      ).data;

      expect(
        laptopFile.liveItems.map((VaultItem i) => i.title),
        containsAll(<String>['Bank', 'Email', 'Shop']),
      );
    });

    test(
      'the combined report counts every device, not just the last',
      () async {
        placeFile('phone', vaultWith(<VaultItem>[login('Email', minute: 5)]));
        placeFile('tablet', vaultWith(<VaultItem>[login('Shop', minute: 6)]));

        final SyncReport report = await run(
          vaultWith(<VaultItem>[login('Bank')]),
        );

        expect(report.peers, hasLength(2));
        expect(report.outcome!.itemsAdded, 2);
      },
    );
  });

  group('a file that cannot be used', () {
    test('does not stop the others being merged', () async {
      // This is the behaviour that decides whether sync is usable at all. A
      // sync client can easily be caught mid-upload, and a sync that gives up
      // on the first unreadable file would fail most of the time.
      placeFile(
        'phone',
        vaultWith(<VaultItem>[login('Email', minute: 5)]),
        sealWith: otherSecret,
      );
      placeFile('tablet', vaultWith(<VaultItem>[login('Shop', minute: 6)]));

      final SyncReport report = await run(
        vaultWith(<VaultItem>[login('Bank')]),
      );

      expect(report.failures, hasLength(1));
      expect(report.failures.single.fileName, 'vault-phone.fvault');
      expect(report.failures.single.problem, PeerProblem.unreadable);
      expect(
        report.merged.liveItems.map((VaultItem i) => i.title),
        containsAll(<String>['Bank', 'Shop']),
      );
      expect(
        report.merged.liveItems.map((VaultItem i) => i.title),
        isNot(contains('Email')),
      );
    });

    test(
      'is reported with both explanations, not just the alarming one',
      () async {
        placeFile(
          'phone',
          vaultWith(<VaultItem>[login('Email')]),
          sealWith: otherSecret,
        );

        final SyncReport report = await run(VaultData(syncSecret: secret));

        // A different sync secret and a part-written file are indistinguishable
        // here by design, so the message must offer both rather than accusing
        // the user of a setup mistake that may not have happened.
        expect(report.failures.single.message, contains('Set up sharing'));
        expect(report.failures.single.message, contains('part-written'));
      },
    );

    test(
      'a file that vanishes between listing and reading is tolerated',
      () async {
        placeFile('phone', vaultWith(<VaultItem>[login('Email')]));
        placeFile('tablet', vaultWith(<VaultItem>[login('Shop', minute: 3)]));
        folder.unreadable.add('vault-phone.fvault');

        final SyncReport report = await run(VaultData(syncSecret: secret));

        expect(report.failures, hasLength(1));
        expect(
          report.merged.liveItems.map((VaultItem i) => i.title),
          contains('Shop'),
        );
        expect(folder.written, contains('vault-laptop.fvault'));
      },
    );

    test(
      'a payload from a newer app is named as such, not as damage',
      () async {
        folder.files['vault-phone.fvault'] = codec.seal(
          masterPassword: secret,
          payload: Uint8List.fromList(
            '{"schemaVersion":99,"items":[]}'.codeUnits,
          ),
        );

        final SyncReport report = await run(VaultData(syncSecret: secret));

        expect(report.failures.single.problem, PeerProblem.tooNew);
        expect(report.failures.single.message, contains('newer version'));
      },
    );

    test('an unrelated file in the folder is left alone', () async {
      folder.files['holiday-photo.jpg'] = Uint8List.fromList(<int>[1, 2, 3]);
      placeFile('phone', vaultWith(<VaultItem>[login('Email')]));

      final SyncReport report = await run(VaultData(syncSecret: secret));

      expect(report.peers, hasLength(1));
      expect(report.peers.single.fileName, 'vault-phone.fvault');
    });
  });

  group('a folder that is not there', () {
    test('fails rather than pretending the sync worked', () async {
      folder.listFailure = const io.FileSystemException('no such directory');

      await expectLater(
        run(VaultData(syncSecret: secret)),
        throwsA(isA<io.FileSystemException>()),
      );
      expect(folder.written, isEmpty);
    });
  });

  group('the real directory implementation', () {
    late io.Directory temporary;

    setUp(() {
      temporary = io.Directory.systemTemp.createTempSync('fv-sync-test');
    });

    tearDown(() {
      if (temporary.existsSync()) {
        temporary.deleteSync(recursive: true);
      }
    });

    test('writes, lists and reads a real file', () async {
      final DirectorySyncFolder real = DirectorySyncFolder(temporary.path);
      final Uint8List bytes = Uint8List.fromList(<int>[9, 8, 7]);

      await real.write('vault-phone.fvault', bytes);

      expect(await real.list(), <String>['vault-phone.fvault']);
      expect(await real.read('vault-phone.fvault'), bytes);
    });

    test('leaves no temporary file behind', () async {
      final DirectorySyncFolder real = DirectorySyncFolder(temporary.path);
      await real.write('vault-phone.fvault', Uint8List.fromList(<int>[1]));

      final List<String> all = temporary
          .listSync()
          .map((io.FileSystemEntity e) => e.uri.pathSegments.last)
          .toList();
      expect(all, <String>['vault-phone.fvault']);
    });

    test('ignores files that are not vaults', () async {
      final DirectorySyncFolder real = DirectorySyncFolder(temporary.path);
      io.File('${temporary.path}${io.Platform.pathSeparator}notes.txt')
          .writeAsStringSync('hello');
      await real.write('vault-phone.fvault', Uint8List.fromList(<int>[1]));

      expect(await real.list(), <String>['vault-phone.fvault']);
    });

    test('says plainly that a missing folder is missing', () async {
      final DirectorySyncFolder gone = DirectorySyncFolder(
        '${temporary.path}${io.Platform.pathSeparator}not-here',
      );

      await expectLater(gone.list(), throwsA(isA<Object>()));
    });

    test('a replaced file is fully replaced, not appended to', () async {
      final DirectorySyncFolder real = DirectorySyncFolder(temporary.path);
      await real.write(
        'vault-phone.fvault',
        Uint8List.fromList(List<int>.filled(100, 1)),
      );
      await real.write('vault-phone.fvault', Uint8List.fromList(<int>[2, 2]));

      expect(await real.read('vault-phone.fvault'), <int>[2, 2]);
    });
  });

  group('keys', () {
    test('no derived key is left unwiped by a sync', () async {
      placeFile('phone', vaultWith(<VaultItem>[login('Email', minute: 5)]));
      placeFile(
        'tablet',
        vaultWith(<VaultItem>[login('Shop')]),
        sealWith: otherSecret,
      );

      await run(vaultWith(<VaultItem>[login('Bank')]));

      expect(
        crypto.keysDisposed,
        crypto.keysDerived,
        reason:
            'sealing and opening each file must wipe its key, including '
            'on the file that failed to open',
      );
    });
  });
}
