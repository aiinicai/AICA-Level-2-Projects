import 'dart:convert';

import 'package:meta/meta.dart';

import '../domain/folder.dart';
import '../domain/vault_data.dart';
import '../domain/vault_item.dart';
import '../domain/vault_settings.dart';

/// What a merge did.
@immutable
final class MergeOutcome {
  const MergeOutcome({
    required this.merged,
    this.itemsAdded = 0,
    this.itemsUpdated = 0,
    this.itemsRemoved = 0,
    this.foldersAdded = 0,
    this.foldersUpdated = 0,
    this.foldersRemoved = 0,
    this.conflicts = 0,
    this.settingsTakenFromOther = false,
    this.clockSkewSuspected = false,
  });

  /// The combined vault.
  final VaultData merged;

  /// Entries the other side had and this one did not.
  final int itemsAdded;

  /// Entries where the other side's version was newer.
  final int itemsUpdated;

  /// Entries removed because a deletion reached this device.
  final int itemsRemoved;

  /// Folders gained from the other side.
  final int foldersAdded;

  /// Folders whose name came from the other side.
  final int foldersUpdated;

  /// Folders removed because a deletion reached this device.
  final int foldersRemoved;

  /// Entries that both sides had changed, where one version had to be chosen.
  ///
  /// Not an error — the newer edit is kept — but worth telling the user,
  /// because the older edit is gone and only they know whether it mattered.
  final int conflicts;

  /// Whether the other device's settings were newer and were taken.
  final bool settingsTakenFromOther;

  /// Whether a timestamp was found far enough in the future to suggest a
  /// device's clock is wrong.
  ///
  /// This matters: the whole merge decides what is newer by comparing
  /// timestamps, so a device whose clock is days ahead silently wins every
  /// conflict. The user can only be told.
  final bool clockSkewSuspected;

  /// True when the merge changed anything at all.
  bool get hadChanges =>
      itemsAdded > 0 ||
      itemsUpdated > 0 ||
      itemsRemoved > 0 ||
      foldersAdded > 0 ||
      foldersUpdated > 0 ||
      foldersRemoved > 0 ||
      settingsTakenFromOther;

  /// One sentence a non-technical user can act on.
  String get summary {
    if (!hadChanges) {
      return 'Already up to date.';
    }
    final List<String> parts = <String>[
      if (itemsAdded > 0) '$itemsAdded added',
      if (itemsUpdated > 0) '$itemsUpdated updated',
      if (itemsRemoved > 0) '$itemsRemoved removed',
      if (foldersAdded + foldersUpdated + foldersRemoved > 0)
        '${foldersAdded + foldersUpdated + foldersRemoved} folder changes',
    ];
    final String detail = parts.isEmpty ? 'settings updated' : parts.join(', ');
    if (conflicts == 0) {
      return '$detail.';
    }
    return conflicts == 1
        ? '$detail. 1 entry had been changed on both devices; the more '
              'recent change was kept.'
        : '$detail. $conflicts entries had been changed on both devices; the '
              'more recent change of each was kept.';
  }
}

/// Combines two versions of the same vault.
///
/// Used when two devices have both been edited since they last agreed. A vault
/// is a single encrypted file, so there is no merging it at the file level: a
/// cloud drive sees only opaque bytes, and taking whichever file was written
/// last would silently throw away everything the other device did. Merging
/// therefore happens here, inside the decrypted payload, entry by entry.
///
/// Three properties make this safe to run on two devices that cannot talk to
/// each other, and all three are tested:
///
/// **Convergence.** `merge(a, b)` and `merge(b, a)` produce an identical
/// result. Each device merges on its own and they still end up the same, which
/// is what makes this work without a server to arbitrate.
///
/// **Idempotence.** Merging a result with either of its inputs again changes
/// nothing, so a sync that runs twice is harmless.
///
/// **No silent resurrection.** A permanent deletion carries a tombstone, so
/// emptying the trash on one device is not undone by another device that still
/// has those entries.
///
/// The cost, stated plainly: where both devices changed the same entry, the
/// newer change wins and the older one is lost. There is no way to keep both
/// without asking the user about every clash, and for a family password
/// manager a reliable automatic answer is worth more than a correct question.
abstract final class VaultMerge {
  /// A timestamp this far ahead of now suggests a device's clock is wrong.
  static const Duration clockSkewTolerance = Duration(days: 1);

  /// Merges [other] into [local].
  ///
  /// The counts in the result are from [local]'s point of view: "added" means
  /// entries [other] had that [local] did not.
  static MergeOutcome merge({
    required VaultData local,
    required VaultData other,
    DateTime? now,
  }) {
    final DateTime at = now ?? DateTime.now();

    // Tombstones first: the merged set decides what may survive below.
    final Map<String, DateTime> graves = <String, DateTime>{};
    for (final Tombstone t in <Tombstone>[
      ...local.tombstones,
      ...other.tombstones,
    ]) {
      final DateTime? existing = graves[t.id];
      if (existing == null || t.purgedAt.isAfter(existing)) {
        graves[t.id] = t.purgedAt;
      }
    }

    bool skew = _isFuture(at, graves.values);

    // Items.
    final Map<String, VaultItem> localItems = <String, VaultItem>{
      for (final VaultItem i in local.items) i.id: i,
    };
    final Map<String, VaultItem> otherItems = <String, VaultItem>{
      for (final VaultItem i in other.items) i.id: i,
    };
    skew =
        skew ||
        _isFuture(at, localItems.values.map((VaultItem i) => i.updatedAt)) ||
        _isFuture(at, otherItems.values.map((VaultItem i) => i.updatedAt));

    int added = 0;
    int updated = 0;
    int removed = 0;
    int conflicts = 0;
    final List<VaultItem> mergedItems = <VaultItem>[];

    for (final String id in <String>{...localItems.keys, ...otherItems.keys}) {
      final VaultItem? mine = localItems[id];
      final VaultItem? theirs = otherItems[id];
      final VaultItem winner = _pickItem(mine, theirs);

      if (mine != null && theirs != null && _differs(mine, theirs)) {
        conflicts++;
      }

      // A permanent deletion wins unless the entry was edited after it. If it
      // was, somebody deliberately changed it later and that intent is newer.
      final DateTime? grave = graves[id];
      if (grave != null && !winner.updatedAt.isAfter(grave)) {
        if (mine != null) {
          removed++;
        }
        continue;
      }

      if (mine == null) {
        added++;
      } else if (_differs(winner, mine)) {
        updated++;
      }
      mergedItems.add(winner);
    }

    // Folders.
    final Map<String, Folder> localFolders = <String, Folder>{
      for (final Folder f in local.folders) f.id: f,
    };
    final Map<String, Folder> otherFolders = <String, Folder>{
      for (final Folder f in other.folders) f.id: f,
    };

    int foldersAdded = 0;
    int foldersUpdated = 0;
    int foldersRemoved = 0;
    final List<Folder> mergedFolders = <Folder>[];

    for (final String id in <String>{
      ...localFolders.keys,
      ...otherFolders.keys,
    }) {
      final Folder? mine = localFolders[id];
      final Folder? theirs = otherFolders[id];
      final Folder winner = _pickFolder(mine, theirs);

      final DateTime? grave = graves[id];
      if (grave != null && !winner.updatedAt.isAfter(grave)) {
        if (mine != null) {
          foldersRemoved++;
        }
        continue;
      }

      if (mine == null) {
        foldersAdded++;
      } else if (winner != mine) {
        foldersUpdated++;
      }
      mergedFolders.add(winner);
      // Folder equality covers every field, so == is enough above.
    }

    // An entry whose folder did not survive would otherwise point at nothing.
    final Set<String> survivingFolders = mergedFolders
        .map((Folder f) => f.id)
        .toSet();
    final List<VaultItem> reparented = mergedItems
        .map(
          (VaultItem i) =>
              i.folderId != null && !survivingFolders.contains(i.folderId)
              ? i.copyWith(clearFolder: true, now: i.updatedAt)
              : i,
        )
        .toList();

    // Settings. Whichever was changed more recently wins.
    final bool takeOtherSettings = _otherSettingsWin(local, other);

    // Sorting by identifier is not cosmetic: it makes the encoded payload
    // identical on both devices, which is what lets the convergence property
    // be asserted by comparing bytes.
    reparented.sort((VaultItem a, VaultItem b) => a.id.compareTo(b.id));
    mergedFolders.sort((Folder a, Folder b) => a.id.compareTo(b.id));

    final List<Tombstone> mergedGraves =
        graves.entries
            .map(
              (MapEntry<String, DateTime> e) =>
                  Tombstone(id: e.key, purgedAt: e.value),
            )
            .toList()
          ..sort((Tombstone a, Tombstone b) => a.id.compareTo(b.id));

    // Pruned on the way out, so an old tombstone does not ride along for ever
    // and the list cannot grow without limit.
    final VaultData merged = VaultData(
      folders: mergedFolders,
      items: reparented,
      settings: takeOtherSettings ? other.settings : local.settings,
      settingsUpdatedAt: takeOtherSettings
          ? other.settingsUpdatedAt
          : local.settingsUpdatedAt,
      tombstones: mergedGraves,
    );

    return MergeOutcome(
      merged: merged.copyWith(tombstones: merged.prunedTombstones(now: at)),
      itemsAdded: added,
      itemsUpdated: updated,
      itemsRemoved: removed,
      foldersAdded: foldersAdded,
      foldersUpdated: foldersUpdated,
      foldersRemoved: foldersRemoved,
      conflicts: conflicts,
      settingsTakenFromOther:
          takeOtherSettings && other.settings != local.settings,
      clockSkewSuspected: skew,
    );
  }

  /// Picks between two versions of one entry.
  ///
  /// Newer wins. When the timestamps are identical but the contents differ —
  /// two devices editing within the same millisecond, or a clock set to the
  /// same value — the choice falls back to comparing the encoded form. That
  /// looks arbitrary, and is, but it is *symmetric*: both devices make the
  /// same choice without talking to each other, which is the whole point.
  static VaultItem _pickItem(VaultItem? mine, VaultItem? theirs) {
    if (mine == null) {
      return theirs!;
    }
    if (theirs == null) {
      return mine;
    }
    if (theirs.updatedAt.isAfter(mine.updatedAt)) {
      return theirs;
    }
    if (mine.updatedAt.isAfter(theirs.updatedAt)) {
      return mine;
    }
    return jsonEncode(mine.toJson()).compareTo(jsonEncode(theirs.toJson())) <= 0
        ? mine
        : theirs;
  }

  static Folder _pickFolder(Folder? mine, Folder? theirs) {
    if (mine == null) {
      return theirs!;
    }
    if (theirs == null) {
      return mine;
    }
    if (theirs.updatedAt.isAfter(mine.updatedAt)) {
      return theirs;
    }
    if (mine.updatedAt.isAfter(theirs.updatedAt)) {
      return mine;
    }
    return jsonEncode(mine.toJson()).compareTo(jsonEncode(theirs.toJson())) <= 0
        ? mine
        : theirs;
  }

  /// Whether the other side's settings should be taken.
  ///
  /// Symmetric, like the entry comparison: a vault whose settings were never
  /// changed loses to one whose were, and an exact tie is broken on the
  /// encoded form so both devices agree.
  static bool _otherSettingsWin(VaultData local, VaultData other) {
    final VaultSettings mineSettings = local.settings;
    final VaultSettings theirSettings = other.settings;
    final DateTime? mine = local.settingsUpdatedAt;
    final DateTime? theirs = other.settingsUpdatedAt;

    // Neither side has ever stamped its settings - both files were written
    // before schema 2, or neither user has changed a setting. There is no
    // clock to compare, so the tiebreak has to decide, and it has to be the
    // SAME tiebreak on both devices. Returning false here (keep mine) looks
    // harmless and is the bug the convergence test caught: each device would
    // keep its own settings for ever and the two would never agree.
    if (mine == null && theirs == null) {
      return _otherSettingsSortFirst(mineSettings, theirSettings);
    }

    // One side has a stamp and the other does not: the stamped one wins. This
    // is symmetric, because the test is "does the other side have a stamp
    // when I do not", which only one device can answer yes to.
    if (theirs == null) {
      return false;
    }
    if (mine == null) {
      return true;
    }

    if (theirs.isAfter(mine)) {
      return true;
    }
    if (mine.isAfter(theirs)) {
      return false;
    }
    return _otherSettingsSortFirst(mineSettings, theirSettings);
  }

  /// Breaks a settings tie the same way on both devices.
  ///
  /// Comparing the encoded form is arbitrary but symmetric, which is the only
  /// property that matters: an arbitrary rule both devices apply leaves them
  /// agreeing, where a sensible rule each applies to its own side does not.
  static bool _otherSettingsSortFirst(
    VaultSettings mine,
    VaultSettings other,
  ) => jsonEncode(other.toJson()).compareTo(jsonEncode(mine.toJson())) < 0;

  /// True when two versions of an entry differ in any field.
  ///
  /// [VaultItem] compares only its identifier and change time, which cannot
  /// see an edit that somehow kept the same timestamp. The encoded form can.
  static bool _differs(VaultItem a, VaultItem b) =>
      jsonEncode(a.toJson()) != jsonEncode(b.toJson());

  static bool _isFuture(DateTime now, Iterable<DateTime> stamps) {
    final DateTime limit = now.add(clockSkewTolerance);
    for (final DateTime stamp in stamps) {
      if (stamp.isAfter(limit)) {
        return true;
      }
    }
    return false;
  }
}
