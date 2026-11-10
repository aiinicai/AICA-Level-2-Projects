import 'dart:convert';
import 'dart:typed_data';

import 'package:meta/meta.dart';

import '../core/failures.dart';
import 'folder.dart';
import 'ids.dart';
import 'vault_item.dart';
import 'vault_settings.dart';

/// Everything a vault contains: the plaintext payload that gets encrypted.
///
/// Immutable. Every change returns a new instance, which is what lets the
/// session hold exactly one current value and write it out atomically.
@immutable
final class VaultData {
  const VaultData({
    this.schemaVersion = currentSchemaVersion,
    this.folders = const <Folder>[],
    this.items = const <VaultItem>[],
    this.settings = const VaultSettings(),
    this.tombstones = const <Tombstone>[],
    this.settingsUpdatedAt,
    this.syncSecret,
  });

  /// Schema version of the payload, separate from the file format version.
  ///
  /// The file format describes how bytes are protected; this describes what
  /// the decrypted contents mean. They change for different reasons, so they
  /// are versioned separately.
  /// Schema 2 added [tombstones] and [settingsUpdatedAt], both needed to
  /// merge two devices. A schema 1 payload still reads: it simply has no
  /// tombstones and no settings timestamp.
  static const int currentSchemaVersion = 2;

  /// An empty vault.
  static const VaultData empty = VaultData();

  /// Payload schema version.
  final int schemaVersion;

  /// Folders, in no particular order.
  final List<Folder> folders;

  /// Every item, including those in the trash.
  final List<VaultItem> items;

  /// Per-vault preferences.
  final VaultSettings settings;

  /// Records of things deleted for good.
  ///
  /// Kept so that a permanent deletion can travel to another device. Without
  /// them, emptying the trash here and then merging with a device that still
  /// has those entries would simply bring them all back.
  final List<Tombstone> tombstones;

  /// When [settings] last changed, or null if they never have.
  ///
  /// Settings live in the vault so they follow it between devices, which means
  /// a merge has to decide whose settings win. This is how.
  final DateTime? settingsUpdatedAt;

  /// A shared secret used to seal the files two devices exchange, as 64
  /// lowercase hexadecimal characters, or null if shared-folder sync has
  /// never been set up.
  ///
  /// Why this exists rather than reusing the master password: the session
  /// never keeps the master password, only a key derived with this vault
  /// file's own salt. A file written by another device has a different salt,
  /// so that key cannot open it, and nothing in memory can. Asking for the
  /// master password on every sync would defeat the point of automatic sync,
  /// and requiring both devices to share a master password would be a
  /// constraint the rest of the design does not impose.
  ///
  /// It lives inside the encrypted payload, so it travels with the vault on
  /// the first manual import and is never written out in the clear. Two
  /// devices come to hold the same secret by that one manual transfer; from
  /// then on neither needs a password to read the other's exchange file.
  ///
  /// It is NOT a second way into the vault. The vault file itself is still
  /// sealed with a key derived from the master password; this secret only
  /// protects the copies placed in a shared folder.
  final String? syncSecret;

  /// Live tombstones, with ones older than [Tombstone.keepFor] dropped.
  ///
  /// They cannot be kept forever or the vault would grow without limit, and
  /// they cannot be dropped quickly either: a device that has been offline
  /// longer than this will reintroduce entries that were deleted while it was
  /// away. [Tombstone.keepFor] is the compromise.
  List<Tombstone> prunedTombstones({DateTime? now}) {
    final DateTime at = now ?? DateTime.now();
    return tombstones
        .where((Tombstone t) => at.difference(t.purgedAt) <= Tombstone.keepFor)
        .toList();
  }

  /// Items not in the trash.
  List<VaultItem> get liveItems =>
      items.where((VaultItem i) => !i.isDeleted).toList();

  /// Items in the trash.
  List<VaultItem> get trashedItems =>
      items.where((VaultItem i) => i.isDeleted).toList();

  /// Live items of one kind.
  List<VaultItem> itemsOfType(VaultItemType type) =>
      liveItems.where((VaultItem i) => i.type == type).toList();

  /// Live items in a folder, or with no folder when [folderId] is null.
  List<VaultItem> itemsInFolder(String? folderId) =>
      liveItems.where((VaultItem i) => i.folderId == folderId).toList();

  /// Live favourites.
  List<VaultItem> get favourites =>
      liveItems.where((VaultItem i) => i.favourite).toList();

  /// Live items with an authenticator key stored.
  List<VaultItem> get authenticatorItems =>
      liveItems.where((VaultItem i) => i.totpSecret.isNotEmpty).toList();

  /// The folder with this identifier, or null.
  Folder? folderById(String? id) {
    if (id == null) {
      return null;
    }
    for (final Folder folder in folders) {
      if (folder.id == id) {
        return folder;
      }
    }
    return null;
  }

  /// The item with this identifier, or null.
  VaultItem? itemById(String id) {
    for (final VaultItem item in items) {
      if (item.id == id) {
        return item;
      }
    }
    return null;
  }

  /// Live items matching [query] by title, username, email, website or folder.
  ///
  /// Matching runs here, on already-decrypted data in memory. Nothing is sent
  /// anywhere: there is no search service to send it to.
  ///
  /// Passwords and other secrets are deliberately not searched. Matching on a
  /// secret would let someone confirm a guessed value by typing it in.
  List<VaultItem> search(String query) {
    final String needle = query.trim().toLowerCase();
    if (needle.isEmpty) {
      return liveItems;
    }
    return liveItems.where((VaultItem item) {
      if (item.title.toLowerCase().contains(needle)) {
        return true;
      }
      for (final String key in <String>[
        ItemField.username,
        ItemField.email,
        ItemField.url,
        ItemField.fullName,
        ItemField.cardholder,
      ]) {
        if (item.field(key).toLowerCase().contains(needle)) {
          return true;
        }
      }
      if (item.notes.toLowerCase().contains(needle)) {
        return true;
      }
      final Folder? folder = folderById(item.folderId);
      return folder != null && folder.name.toLowerCase().contains(needle);
    }).toList();
  }

  /// Adds an item, or replaces the existing one with the same identifier.
  VaultData upsertItem(VaultItem item) {
    final List<VaultItem> next = List<VaultItem>.of(items);
    final int index = next.indexWhere((VaultItem i) => i.id == item.id);
    if (index >= 0) {
      next[index] = item;
    } else {
      next.add(item);
    }
    return copyWith(items: next);
  }

  /// Moves an item to the trash. Its contents stay encrypted in the file.
  VaultData trashItem(String id, {DateTime? now}) {
    final VaultItem? item = itemById(id);
    if (item == null || item.isDeleted) {
      return this;
    }
    return upsertItem(
      item.copyWith(deletedAt: now ?? DateTime.now(), now: now),
    );
  }

  /// Takes an item back out of the trash.
  VaultData restoreItem(String id, {DateTime? now}) {
    final VaultItem? item = itemById(id);
    if (item == null || !item.isDeleted) {
      return this;
    }
    return upsertItem(item.copyWith(restore: true, now: now));
  }

  /// Removes an item for good, leaving a tombstone behind.
  VaultData purgeItem(String id, {DateTime? now}) {
    if (itemById(id) == null) {
      return this;
    }
    return copyWith(
      items: items.where((VaultItem i) => i.id != id).toList(),
      tombstones: <Tombstone>[
        ...tombstones,
        Tombstone(id: id, purgedAt: now ?? DateTime.now()),
      ],
    );
  }

  /// Empties the trash, leaving a tombstone for each entry removed.
  VaultData emptyTrash({DateTime? now}) {
    final DateTime at = now ?? DateTime.now();
    final List<VaultItem> removed = trashedItems;
    if (removed.isEmpty) {
      return this;
    }
    return copyWith(
      items: liveItems,
      tombstones: <Tombstone>[
        ...tombstones,
        for (final VaultItem item in removed)
          Tombstone(id: item.id, purgedAt: at),
      ],
    );
  }

  /// Adds a folder.
  VaultData addFolder(Folder folder) =>
      copyWith(folders: <Folder>[...folders, folder]);

  /// Renames a folder.
  VaultData renameFolder(String id, String name, {DateTime? now}) => copyWith(
    folders: folders
        .map((Folder f) => f.id == id ? f.renamed(name, now: now) : f)
        .toList(),
  );

  /// Deletes a folder, leaving its items in place with no folder.
  ///
  /// Items are never deleted along with a folder. Losing entries because a
  /// folder was tidied away would be the worst kind of surprise in a password
  /// manager.
  VaultData deleteFolder(String id, {DateTime? now}) {
    final List<VaultItem> movedOut = items
        .map(
          (VaultItem i) =>
              i.folderId == id ? i.copyWith(clearFolder: true, now: now) : i,
        )
        .toList();
    if (folderById(id) == null) {
      return this;
    }
    return copyWith(
      folders: folders.where((Folder f) => f.id != id).toList(),
      items: movedOut,
      // A deleted folder needs a tombstone too, or another device would
      // recreate it on the next merge.
      tombstones: <Tombstone>[
        ...tombstones,
        Tombstone(id: id, purgedAt: now ?? DateTime.now()),
      ],
    );
  }

  /// Replaces the settings, stamping when that happened.
  VaultData withSettings(VaultSettings next, {DateTime? now}) =>
      copyWith(settings: next, settingsUpdatedAt: now ?? DateTime.now());

  /// A copy with the given changes.
  VaultData copyWith({
    List<Folder>? folders,
    List<VaultItem>? items,
    VaultSettings? settings,
    List<Tombstone>? tombstones,
    DateTime? settingsUpdatedAt,
    String? syncSecret,
  }) => VaultData(
    schemaVersion: schemaVersion,
    folders: folders ?? this.folders,
    items: items ?? this.items,
    settings: settings ?? this.settings,
    tombstones: tombstones ?? this.tombstones,
    settingsUpdatedAt: settingsUpdatedAt ?? this.settingsUpdatedAt,
    syncSecret: syncSecret ?? this.syncSecret,
  );

  /// A copy carrying [secret] as the shared-folder sync secret.
  VaultData withSyncSecret(String secret) => copyWith(syncSecret: secret);

  /// Reads a sync secret from stored form, rejecting anything malformed.
  ///
  /// A short or non-hexadecimal value would weaken every exchange file
  /// without the user being told, so a damaged one is treated as absent and
  /// sync simply has to be set up again.
  static String? _validSyncSecret(Object? raw) {
    if (raw is! String || raw.length != 64) {
      return null;
    }
    const String hex = '0123456789abcdef';
    for (int i = 0; i < raw.length; i++) {
      if (!hex.contains(raw[i])) {
        return null;
      }
    }
    return raw;
  }

  /// Stored form.
  Map<String, Object?> toJson() => <String, Object?>{
    'schemaVersion': currentSchemaVersion,
    'folders': folders.map((Folder f) => f.toJson()).toList(),
    'items': items.map((VaultItem i) => i.toJson()).toList(),
    'settings': settings.toJson(),
    'tombstones': tombstones.map((Tombstone t) => t.toJson()).toList(),
    'settingsUpdatedAt': settingsUpdatedAt?.toUtc().toIso8601String(),
    'syncSecret': syncSecret,
  };

  /// Serialises the payload to the bytes that get encrypted.
  Uint8List encode() => Uint8List.fromList(utf8.encode(jsonEncode(toJson())));

  /// Reads a payload from decrypted bytes.
  ///
  /// Throws [VaultFormatFailure] only when the payload as a whole is
  /// unusable. Individual items or folders that cannot be read are dropped and
  /// counted, so one damaged entry never costs the user the rest of the vault.
  /// Parses the decrypted bytes as JSON.
  ///
  /// Separated out so that a malformed payload and malformed UTF-8 both arrive
  /// as the same typed failure, rather than as a raw [FormatException] from
  /// somewhere inside the decoder.
  static Object? _parseJson(Uint8List bytes) {
    try {
      return jsonDecode(utf8.decode(bytes));
    } on FormatException {
      throw const VaultFormatFailure(
        'The vault opened but its contents could not be read.',
      );
    }
  }

  static VaultDataDecoding decode(Uint8List bytes) {
    final Object? root = _parseJson(bytes);
    if (root is! Map<String, Object?>) {
      throw const VaultFormatFailure(
        'The vault opened but its contents were not in the expected form.',
      );
    }

    final Object? version = root['schemaVersion'];
    if (version is int && version > currentSchemaVersion) {
      throw VaultVersionFailure(
        'This vault was saved by a newer version of Family Vault. Please '
        'update the app to open it.',
        fileVersion: version,
      );
    }

    int droppedFolders = 0;
    final List<Folder> folders = <Folder>[];
    final Object? rawFolders = root['folders'];
    if (rawFolders is List<Object?>) {
      for (final Object? entry in rawFolders) {
        final Folder? folder = entry is Map<String, Object?>
            ? Folder.fromJson(entry)
            : null;
        if (folder == null) {
          droppedFolders++;
        } else {
          folders.add(folder);
        }
      }
    }

    int droppedItems = 0;
    final List<VaultItem> items = <VaultItem>[];
    final Object? rawItems = root['items'];
    if (rawItems is List<Object?>) {
      for (final Object? entry in rawItems) {
        final VaultItem? item = entry is Map<String, Object?>
            ? VaultItem.fromJson(entry)
            : null;
        if (item == null) {
          droppedItems++;
        } else {
          items.add(item);
        }
      }
    }

    final List<Tombstone> tombstones = <Tombstone>[];
    final Object? rawTombstones = root['tombstones'];
    if (rawTombstones is List<Object?>) {
      for (final Object? entry in rawTombstones) {
        final Tombstone? tombstone = entry is Map<String, Object?>
            ? Tombstone.fromJson(entry)
            : null;
        if (tombstone != null) {
          tombstones.add(tombstone);
        }
      }
    }

    final Object? rawSettingsStamp = root['settingsUpdatedAt'];
    final Object? rawSettings = root['settings'];
    return VaultDataDecoding(
      data: VaultData(
        folders: folders,
        items: items,
        settings: rawSettings is Map<String, Object?>
            ? VaultSettings.fromJson(rawSettings)
            : const VaultSettings(),
        tombstones: tombstones,
        settingsUpdatedAt: rawSettingsStamp is String
            ? DateTime.tryParse(rawSettingsStamp)
            : null,
        syncSecret: _validSyncSecret(root['syncSecret']),
      ),
      droppedItems: droppedItems,
      droppedFolders: droppedFolders,
    );
  }
}

/// The result of reading a payload, including anything that had to be dropped.
@immutable
final class VaultDataDecoding {
  const VaultDataDecoding({
    required this.data,
    this.droppedItems = 0,
    this.droppedFolders = 0,
  });

  /// What was read successfully.
  final VaultData data;

  /// Items that could not be read and were left out.
  final int droppedItems;

  /// Folders that could not be read and were left out.
  final int droppedFolders;

  /// True when something had to be dropped, so the user can be told.
  bool get hadLosses => droppedItems > 0 || droppedFolders > 0;
}

/// A record that something was deleted for good.
///
/// Only an identifier and a time. A tombstone says nothing about what the
/// entry was — not its title, not its kind — so the record of a deletion
/// reveals nothing even to someone who could read the payload.
@immutable
final class Tombstone {
  const Tombstone({required this.id, required this.purgedAt});

  /// How long a tombstone is kept.
  ///
  /// Six months. They cannot be kept forever or the vault grows without
  /// limit, and they cannot be dropped quickly either: a device offline for
  /// longer than this will bring back entries deleted while it was away. Six
  /// months is long enough that a phone left in a drawer over a holiday is
  /// still safe, and short enough that the list stays small.
  static const Duration keepFor = Duration(days: 182);

  /// Identifier of the deleted item or folder.
  ///
  /// Item and folder identifiers are both 128-bit random values, so one list
  /// can hold either without ambiguity.
  final String id;

  /// When it was deleted.
  final DateTime purgedAt;

  /// Stored form.
  Map<String, Object?> toJson() => <String, Object?>{
    'id': id,
    'purgedAt': purgedAt.toUtc().toIso8601String(),
  };

  /// Reads a tombstone, or null when it cannot be understood.
  static Tombstone? fromJson(Map<String, Object?> json) {
    final Object? id = json['id'];
    final Object? purgedAt = json['purgedAt'];
    if (id is! String || !Ids.isValid(id) || purgedAt is! String) {
      return null;
    }
    final DateTime? at = DateTime.tryParse(purgedAt);
    return at == null ? null : Tombstone(id: id, purgedAt: at);
  }

  @override
  bool operator ==(Object other) =>
      other is Tombstone && other.id == id && other.purgedAt == purgedAt;

  @override
  int get hashCode => Object.hash(id, purgedAt);
}
