import 'dart:convert';
import 'dart:math';

import 'package:family_vault/src/domain/folder.dart';
import 'package:family_vault/src/domain/vault_data.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:family_vault/src/domain/vault_settings.dart';
import 'package:family_vault/src/vault/vault_merge.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for merging two devices' vaults.
///
/// This is the most dangerous code in the project. Everything else either
/// works or visibly fails; a merge that is subtly wrong deletes a password
/// quietly, and the user finds out weeks later when they cannot sign in to
/// something. So these tests go after the specific ways it could go wrong
/// rather than the happy path.
void main() {
  final DateTime t0 = DateTime.utc(2026, 11, 1, 12);
  DateTime at(int minutes) => t0.add(Duration(minutes: minutes));
  final DateTime now = at(1000);

  VaultItem item(
    String title, {
    required int minute,
    String password = 'a-good-password-99',
    String? folderId,
    String id = '',
  }) {
    final VaultItem created = VaultItem.create(
      type: VaultItemType.login,
      title: title,
      fields: <String, String>{ItemField.password: password},
      folderId: folderId,
      now: at(minute),
    );
    if (id.isEmpty) {
      return created;
    }
    // A fixed identifier, so both sides can hold "the same" entry.
    return VaultItem(
      id: id,
      type: created.type,
      title: created.title,
      fields: created.fields,
      folderId: created.folderId,
      createdAt: created.createdAt,
      updatedAt: created.updatedAt,
      passwordUpdatedAt: created.passwordUpdatedAt,
    );
  }

  const String idA = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
  const String idB = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
  const String folderId = 'ffffffffffffffffffffffffffffffff';

  VaultData vault({
    List<VaultItem> items = const <VaultItem>[],
    List<Folder> folders = const <Folder>[],
    List<Tombstone> tombstones = const <Tombstone>[],
    VaultSettings? settings,
    DateTime? settingsAt,
  }) => VaultData(
    items: items,
    folders: folders,
    tombstones: tombstones,
    settings: settings ?? const VaultSettings(),
    settingsUpdatedAt: settingsAt,
  );

  String encoded(VaultData data) => jsonEncode(data.toJson());

  MergeOutcome mergeOf(VaultData a, VaultData b) =>
      VaultMerge.merge(local: a, other: b, now: now);

  // ------------------------------------------------------------------ basics

  group('nothing to do', () {
    test('two empty vaults', () {
      final MergeOutcome result = mergeOf(VaultData.empty, VaultData.empty);
      expect(result.hadChanges, isFalse);
      expect(result.merged.items, isEmpty);
      expect(result.summary, 'Already up to date.');
    });

    test('two identical vaults', () {
      final VaultData a = vault(items: <VaultItem>[item('Bank', minute: 0)]);
      final MergeOutcome result = mergeOf(a, a);
      expect(result.hadChanges, isFalse);
      expect(result.merged.items.length, 1);
      expect(result.conflicts, 0);
    });
  });

  group('entries only one side has', () {
    test('are brought across', () {
      final VaultItem mine = item('Bank', minute: 0, id: idA);
      final VaultItem theirs = item('Shop', minute: 1, id: idB);
      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[mine]),
        vault(items: <VaultItem>[theirs]),
      );
      expect(result.merged.items.length, 2);
      expect(result.itemsAdded, 1);
      expect(result.itemsRemoved, 0);
      expect(result.conflicts, 0);
    });
  });

  group('the same entry changed on both devices', () {
    test('the newer change wins and the clash is reported', () {
      final VaultItem older = item(
        'Bank',
        minute: 0,
        password: 'old-password-1',
        id: idA,
      );
      final VaultItem newer = item(
        'Bank',
        minute: 60,
        password: 'new-password-2',
        id: idA,
      );
      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[older]),
        vault(items: <VaultItem>[newer]),
      );
      expect(result.merged.items.single.password, 'new-password-2');
      expect(result.itemsUpdated, 1);
      expect(result.conflicts, 1);
      expect(result.summary, contains('changed on both devices'));
    });

    test('the local change wins when it is the newer one', () {
      final VaultItem mine = item(
        'Bank',
        minute: 60,
        password: 'mine-is-newer',
        id: idA,
      );
      final VaultItem theirs = item(
        'Bank',
        minute: 0,
        password: 'theirs-is-older',
        id: idA,
      );
      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[mine]),
        vault(items: <VaultItem>[theirs]),
      );
      expect(result.merged.items.single.password, 'mine-is-newer');
      expect(result.itemsUpdated, 0);
      expect(result.conflicts, 1);
    });
  });

  // A deletion that does not travel is the worst bug available here: the user
  // deletes a password on their phone, syncs, and it quietly comes back.
  group('deletions travel', () {
    test('an entry deleted for good on one device does not come back', () {
      final VaultItem gone = item('Old', minute: 0, id: idA);
      final VaultData withIt = vault(items: <VaultItem>[gone]);
      final VaultData purged = withIt
          .trashItem(gone.id, now: at(10))
          .purgeItem(gone.id, now: at(20));

      expect(purged.items, isEmpty);
      expect(purged.tombstones.length, 1);

      final MergeOutcome result = mergeOf(withIt, purged);
      expect(
        result.merged.items,
        isEmpty,
        reason: 'the deletion must reach this device',
      );
      expect(result.itemsRemoved, 1);
    });

    test('emptying the trash does not bring the entries back', () {
      final VaultItem a = item('One', minute: 0, id: idA);
      final VaultItem b = item('Two', minute: 1, id: idB);
      final VaultData withBoth = vault(items: <VaultItem>[a, b]);
      final VaultData emptied = withBoth
          .trashItem(a.id, now: at(10))
          .trashItem(b.id, now: at(11))
          .emptyTrash(now: at(20));

      expect(emptied.items, isEmpty);
      final MergeOutcome result = mergeOf(withBoth, emptied);
      expect(result.merged.items, isEmpty);
      expect(result.itemsRemoved, 2);
    });

    // The other side of the same coin: a deletion must not undo a later edit.
    test('an entry edited after the deletion survives', () {
      final VaultItem original = item('Bank', minute: 0, id: idA);
      final VaultData purged = vault(items: <VaultItem>[original])
          .purgeItem(original.id, now: at(10));

      final VaultItem editedLater = item(
        'Bank',
        minute: 50,
        password: 'changed-after-the-delete',
        id: idA,
      );
      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[editedLater]),
        purged,
      );
      expect(
        result.merged.items.single.password,
        'changed-after-the-delete',
        reason: 'a later edit is a newer intention than an older deletion',
      );
    });

    test('a trashed entry still syncs as trashed, not as missing', () {
      final VaultItem it = item('Bank', minute: 0, id: idA);
      final VaultData trashed = vault(items: <VaultItem>[it])
          .trashItem(it.id, now: at(10));

      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[it]),
        trashed,
      );
      expect(result.merged.items.length, 1);
      expect(result.merged.trashedItems.length, 1);
      expect(result.merged.liveItems, isEmpty);
    });
  });

  group('folders', () {
    test('a rename on both devices settles on the newer one', () {
      final Folder mine = Folder(
        id: folderId,
        name: 'Bank',
        createdAt: at(0),
        updatedAt: at(5),
      );
      final Folder theirs = Folder(
        id: folderId,
        name: 'Banking',
        createdAt: at(0),
        updatedAt: at(50),
      );
      final MergeOutcome result = mergeOf(
        vault(folders: <Folder>[mine]),
        vault(folders: <Folder>[theirs]),
      );
      expect(result.merged.folders.single.name, 'Banking');
      expect(result.foldersUpdated, 1);
    });

    test('a folder deleted on one device goes, and its entries stay', () {
      final Folder folder = Folder(
        id: folderId,
        name: 'Bank',
        createdAt: at(0),
        updatedAt: at(0),
      );
      final VaultItem inside = item(
        'Barclays',
        minute: 1,
        folderId: folderId,
        id: idA,
      );
      final VaultData withFolder = vault(
        items: <VaultItem>[inside],
        folders: <Folder>[folder],
      );
      final VaultData deleted = withFolder.deleteFolder(folderId, now: at(30));

      final MergeOutcome result = mergeOf(withFolder, deleted);
      expect(result.merged.folders, isEmpty);
      expect(
        result.merged.items.length,
        1,
        reason: 'deleting a folder must never delete what was in it',
      );
      expect(result.merged.items.single.folderId, isNull);
      expect(result.foldersRemoved, 1);
    });

    test('an entry pointing at a folder that did not survive is unfiled', () {
      final VaultItem orphan = item(
        'Barclays',
        minute: 1,
        folderId: folderId,
        id: idA,
      );
      // Neither side has the folder, but the entry still refers to it.
      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[orphan]),
        VaultData.empty,
      );
      expect(result.merged.items.single.folderId, isNull);
    });
  });

  group('settings', () {
    test('the more recently changed settings win', () {
      final VaultData mine = vault(
        settings: const VaultSettings(autoLockMinutes: 5),
        settingsAt: at(10),
      );
      final VaultData theirs = vault(
        settings: const VaultSettings(autoLockMinutes: 30),
        settingsAt: at(100),
      );
      final MergeOutcome result = mergeOf(mine, theirs);
      expect(result.merged.settings.autoLockMinutes, 30);
      expect(result.settingsTakenFromOther, isTrue);
    });

    test('settings never changed lose to settings that were', () {
      final MergeOutcome result = mergeOf(
        vault(),
        vault(
          settings: const VaultSettings(autoLockMinutes: 30),
          settingsAt: at(10),
        ),
      );
      expect(result.merged.settings.autoLockMinutes, 30);
    });

    test('local settings are kept when they are the newer ones', () {
      final MergeOutcome result = mergeOf(
        vault(
          settings: const VaultSettings(autoLockMinutes: 1),
          settingsAt: at(100),
        ),
        vault(
          settings: const VaultSettings(autoLockMinutes: 30),
          settingsAt: at(10),
        ),
      );
      expect(result.merged.settings.autoLockMinutes, 1);
      expect(result.settingsTakenFromOther, isFalse);
    });

    test('two unstamped sides still agree on one answer', () {
      // Both files predate schema 2, or neither user ever changed a setting,
      // so there is no clock to compare. Keeping "mine" in that case looks
      // harmless and is not: each device keeps its own and they never agree.
      // This is the case the convergence property caught in CI run
      // 42795423782.
      final VaultData mine = vault(
        settings: const VaultSettings(autoLockMinutes: 5),
      );
      final VaultData theirs = vault(
        settings: const VaultSettings(autoLockMinutes: 30),
      );

      expect(
        encoded(mergeOf(mine, theirs).merged),
        encoded(mergeOf(theirs, mine).merged),
      );
    });
  });

  // ------------------------------------------------- the properties that matter

  group('convergence: both devices reach the same answer alone', () {
    test('merging in either direction gives an identical vault', () {
      final VaultData a = vault(
        items: <VaultItem>[
          item('Bank', minute: 0, password: 'p1', id: idA),
          item('Only mine', minute: 5),
        ],
        folders: <Folder>[
          Folder(
            id: folderId,
            name: 'Mine',
            createdAt: at(0),
            updatedAt: at(1),
          ),
        ],
        settings: const VaultSettings(autoLockMinutes: 5),
        settingsAt: at(3),
      );
      final VaultData b = vault(
        items: <VaultItem>[
          item('Bank', minute: 60, password: 'p2', id: idA),
          item('Only theirs', minute: 7, id: idB),
        ],
        folders: <Folder>[
          Folder(
            id: folderId,
            name: 'Theirs',
            createdAt: at(0),
            updatedAt: at(40),
          ),
        ],
        settings: const VaultSettings(autoLockMinutes: 30),
        settingsAt: at(9),
      );

      expect(encoded(mergeOf(a, b).merged), encoded(mergeOf(b, a).merged));
    });

    test('holds when the two sides have identical timestamps', () {
      // The nastiest tie: same entry, same change time, different contents.
      // Without a symmetric tiebreak the two devices would disagree for ever.
      final VaultItem mine = item('Bank', minute: 10, password: 'aaa', id: idA);
      final VaultItem theirs = item(
        'Bank',
        minute: 10,
        password: 'zzz',
        id: idA,
      );
      final VaultData a = vault(items: <VaultItem>[mine]);
      final VaultData b = vault(items: <VaultItem>[theirs]);

      expect(encoded(mergeOf(a, b).merged), encoded(mergeOf(b, a).merged));
    });

    test('holds across a hundred random pairs of vaults', () {
      final Random random = Random(20261110);
      for (int round = 0; round < 100; round++) {
        final VaultData a = _randomVault(random, at, idA, idB, folderId);
        final VaultData b = _randomVault(random, at, idA, idB, folderId);
        expect(
          encoded(mergeOf(a, b).merged),
          encoded(mergeOf(b, a).merged),
          reason: 'diverged on round $round',
        );
      }
    });
  });

  group('idempotence: syncing twice is harmless', () {
    test('merging the result with either input changes nothing', () {
      final VaultData a = vault(
        items: <VaultItem>[
          item('Bank', minute: 0, password: 'p1', id: idA),
          item('Mine', minute: 5),
        ],
      );
      final VaultData b = vault(
        items: <VaultItem>[
          item('Bank', minute: 60, password: 'p2', id: idA),
          item('Theirs', minute: 7, id: idB),
        ],
      );
      final VaultData once = mergeOf(a, b).merged;

      expect(encoded(mergeOf(once, b).merged), encoded(once));
      expect(encoded(mergeOf(once, a).merged), encoded(once));
      expect(mergeOf(once, b).hadChanges, isFalse);
    });

    test('holds across a hundred random pairs', () {
      final Random random = Random(99);
      for (int round = 0; round < 100; round++) {
        final VaultData a = _randomVault(random, at, idA, idB, folderId);
        final VaultData b = _randomVault(random, at, idA, idB, folderId);
        final VaultData once = mergeOf(a, b).merged;
        expect(
          encoded(mergeOf(once, b).merged),
          encoded(once),
          reason: 'not idempotent on round $round',
        );
      }
    });
  });

  group('a wrong clock is reported rather than trusted', () {
    test('a timestamp far in the future is flagged', () {
      final VaultItem fromTheFuture = item(
        'Bank',
        minute: 60 * 24 * 30,
        id: idA,
      );
      final MergeOutcome result = mergeOf(
        VaultData.empty,
        vault(items: <VaultItem>[fromTheFuture]),
      );
      expect(result.clockSkewSuspected, isTrue);
    });

    test('ordinary timestamps are not flagged', () {
      final MergeOutcome result = mergeOf(
        vault(items: <VaultItem>[item('Bank', minute: 0, id: idA)]),
        vault(items: <VaultItem>[item('Shop', minute: 10, id: idB)]),
      );
      expect(result.clockSkewSuspected, isFalse);
    });
  });

  group('tombstones do not accumulate for ever', () {
    test('one older than the keep-for window is dropped', () {
      final DateTime longAgo = now.subtract(
        Tombstone.keepFor + const Duration(days: 1),
      );
      final MergeOutcome result = mergeOf(
        vault(
          tombstones: <Tombstone>[Tombstone(id: idA, purgedAt: longAgo)],
        ),
        VaultData.empty,
      );
      expect(result.merged.tombstones, isEmpty);
    });

    test('a recent one is kept, so the deletion can still travel', () {
      final MergeOutcome result = mergeOf(
        vault(
          tombstones: <Tombstone>[Tombstone(id: idA, purgedAt: at(0))],
        ),
        VaultData.empty,
      );
      expect(result.merged.tombstones.single.id, idA);
    });
  });

  group('the merged payload', () {
    test('is written at the current schema version', () {
      final MergeOutcome result = mergeOf(VaultData.empty, VaultData.empty);
      final VaultDataDecoding back = VaultData.decode(result.merged.encode());
      expect(back.data.schemaVersion, VaultData.currentSchemaVersion);
      expect(back.hadLosses, isFalse);
    });

    test('survives a round trip through encryption-ready bytes', () {
      final VaultData merged = mergeOf(
        vault(items: <VaultItem>[item('Bank', minute: 0, id: idA)]),
        vault(
          items: <VaultItem>[item('Shop', minute: 1, id: idB)],
          tombstones: <Tombstone>[
            Tombstone(id: 'cccccccccccccccccccccccccccccccc', purgedAt: at(2)),
          ],
        ),
      ).merged;

      final VaultData back = VaultData.decode(merged.encode()).data;
      expect(encoded(back), encoded(merged));
    });
  });
}

/// Builds an arbitrary but reproducible vault, for the property tests.
///
/// Deliberately reuses a small pool of identifiers so that the two vaults
/// collide often — a generator that produced unique identifiers every time
/// would never exercise the conflict paths, which are the ones worth testing.
VaultData _randomVault(
  Random random,
  DateTime Function(int minutes) at,
  String idA,
  String idB,
  String folderId,
) {
  final List<String> pool = <String>[idA, idB];
  final List<VaultItem> items = <VaultItem>[];
  final List<Tombstone> graves = <Tombstone>[];

  for (final String id in pool) {
    final int roll = random.nextInt(4);
    if (roll == 0) {
      continue; // absent on this side
    }
    final int minute = random.nextInt(120);
    final VaultItem built = VaultItem(
      id: id,
      type: VaultItemType.login,
      title: 'Entry $id',
      fields: <String, String>{
        ItemField.password: 'password-${random.nextInt(5)}',
      },
      folderId: random.nextBool() ? folderId : null,
      createdAt: at(0),
      updatedAt: at(minute),
      deletedAt: roll == 3 ? at(minute) : null,
    );
    items.add(built);
    if (roll == 2) {
      graves.add(Tombstone(id: id, purgedAt: at(random.nextInt(120))));
    }
  }

  return VaultData(
    items: items,
    folders: random.nextBool()
        ? <Folder>[
            Folder(
              id: folderId,
              name: 'Folder ${random.nextInt(3)}',
              createdAt: at(0),
              updatedAt: at(random.nextInt(120)),
            ),
          ]
        : const <Folder>[],
    tombstones: graves,
    settings: VaultSettings(autoLockMinutes: random.nextBool() ? 5 : 30),
    settingsUpdatedAt: random.nextBool() ? at(random.nextInt(120)) : null,
  );
}
