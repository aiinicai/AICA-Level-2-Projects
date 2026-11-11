// Synchronising through a folder both devices can see.
//
// There is no server in this design and there is not going to be one. What
// there is, on almost every device already, is a folder that some other
// program keeps in step: Google Drive, OneDrive, Dropbox, Syncthing, a
// network share, even a USB stick carried between two machines. This works
// through any of them and knows about none of them. No account, no sign-in,
// no API key, no paid tier, and nothing here can tell which one is in use.
//
// How it works. Each device writes one file into the folder, holding its own
// copy of the vault. A sync reads every OTHER device's file, merges them all
// in, and then writes its own file back out carrying the merged result - so a
// third device picks up everything at its next sync without ever meeting the
// first one directly.
//
// What the folder's owner can see. Only encrypted files. The provider stores
// ciphertext and a header; it holds no key and no password, which is the same
// reason a backup is safe on a cloud drive.
//
// What a failure looks like. One unreadable file never stops a sync. It is
// reported by name and the others are merged anyway, because the common cause
// is a file half-written by the sync client at that moment, which will be
// whole by the next run.

import 'dart:io';

import 'package:flutter/foundation.dart';

import '../core/failures.dart';
import '../domain/vault_data.dart';
import 'vault_codec.dart';
import 'vault_merge.dart';

/// A folder that holds the files devices exchange.
///
/// An interface so the tests can run against a map in memory rather than a
/// real directory, and so a future provider-specific implementation has
/// somewhere to go without touching the merge.
abstract interface class SyncFolder {
  /// The names of the exchange files present, without paths.
  Future<List<String>> list();

  /// Reads one file.
  Future<Uint8List> read(String name);

  /// Writes one file, replacing any file of that name.
  Future<void> write(String name, Uint8List bytes);

  /// Where this folder is, for showing to the user.
  String describe();
}

/// A [SyncFolder] backed by a real directory.
final class DirectorySyncFolder implements SyncFolder {
  const DirectorySyncFolder(this.path);

  /// The folder's full path.
  final String path;

  @override
  Future<List<String>> list() async {
    final Directory directory = Directory(path);
    if (!directory.existsSync()) {
      throw VaultFormatFailure(
        'The shared folder is no longer there. It may be on a drive that is '
        'not connected, or it may have been moved or renamed.',
      );
    }
    final List<String> names = <String>[];
    for (final FileSystemEntity entry in directory.listSync()) {
      if (entry is File && entry.path.endsWith('.$syncFileExtension')) {
        names.add(entry.uri.pathSegments.last);
      }
    }
    names.sort();
    return names;
  }

  @override
  Future<Uint8List> read(String name) =>
      File('$path${Platform.pathSeparator}$name').readAsBytes();

  /// Writes through a temporary file and renames it into place.
  ///
  /// A sync client watching the folder would otherwise be free to upload a
  /// half-written file, and the other device would read exactly that.
  @override
  Future<void> write(String name, Uint8List bytes) async {
    final String separator = Platform.pathSeparator;
    final File temporary = File('$path$separator$name.writing');
    await temporary.writeAsBytes(bytes, flush: true);
    await temporary.rename('$path$separator$name');
  }

  @override
  String describe() => path;
}

/// The extension exchange files use.
const String syncFileExtension = 'fvault';

/// Why one device's file could not be used.
enum PeerProblem {
  /// It would not decrypt. Either it was written by a vault that does not
  /// share this one's sync secret, or it was damaged.
  unreadable,

  /// It decrypted but its contents made no sense.
  unintelligible,

  /// It was written by a newer version of the app.
  tooNew,
}

/// One device's file, and what happened to it.
@immutable
final class PeerResult {
  const PeerResult.merged(this.fileName)
    : problem = null,
      itemsTaken = 0,
      dropped = 0;

  const PeerResult.mergedWith(
    this.fileName, {
    required this.itemsTaken,
    required this.dropped,
  }) : problem = null;

  const PeerResult.failed(this.fileName, this.problem)
    : itemsTaken = 0,
      dropped = 0;

  /// The file this is about.
  final String fileName;

  /// What went wrong, or null if nothing did.
  final PeerProblem? problem;

  /// Entries taken from this device that were not here already.
  final int itemsTaken;

  /// Entries in the file that could not be read and were left out.
  final int dropped;

  /// True when the file was merged.
  bool get ok => problem == null;

  /// What to tell the user about this file.
  String get message => switch (problem) {
    null =>
      dropped == 0
          ? '$fileName: merged.'
          : '$fileName: merged, but $dropped '
                '${dropped == 1 ? 'entry' : 'entries'} in it could not be read '
                'and were left out.',
    PeerProblem.unreadable =>
      '$fileName: could not be opened. Set up sharing on that device from '
          'this one, or it may have been part-written and will be readable '
          'next time.',
    PeerProblem.unintelligible =>
      '$fileName: opened but its contents were damaged. It was left alone.',
    PeerProblem.tooNew =>
      '$fileName: written by a newer version of Family Vault. Update this '
          'device to read it.',
  };
}

/// What a whole sync did.
@immutable
final class SyncReport {
  const SyncReport({
    required this.merged,
    required this.peers,
    required this.outcome,
    required this.wroteOwnFile,
  });

  /// The vault after merging everything that could be read.
  final VaultData merged;

  /// One entry per other device's file found in the folder.
  final List<PeerResult> peers;

  /// The combined effect on this device's vault, or null when there was
  /// nothing to merge.
  final MergeOutcome? outcome;

  /// Whether this device's own file was written out.
  final bool wroteOwnFile;

  /// Files that could not be used.
  List<PeerResult> get failures =>
      peers.where((PeerResult p) => !p.ok).toList();

  /// True when this device's own vault changed.
  bool get localChanged => outcome?.hadChanges ?? false;

  /// One line for the user.
  String get summary {
    if (peers.isEmpty) {
      return wroteOwnFile
          ? 'No other device has shared a vault here yet. This device’s '
                'copy is now in the folder, ready for the other one.'
          : 'Nothing to do.';
    }
    final int ok = peers.length - failures.length;
    final String devices = '$ok ${ok == 1 ? 'device' : 'devices'}';
    final String change = outcome == null || !outcome!.hadChanges
        ? 'already up to date'
        : outcome!.summary.replaceAll(RegExp(r'\.$'), '');
    final String problems = failures.isEmpty
        ? ''
        : ' ${failures.length} file${failures.length == 1 ? '' : 's'} could '
              'not be used.';
    return 'Synced with $devices: $change.$problems';
  }
}

/// Merging through a shared folder.
final class VaultSync {
  const VaultSync({required this.codec, required this.folder});

  /// Seals and opens the exchange files. Public because a private field
  /// cannot be a named initializing formal in Dart.
  final VaultCodec codec;

  /// The folder both devices can see.
  final SyncFolder folder;

  /// The file name a device with this name writes.
  ///
  /// Derived from the name rather than stored, so a device that is renamed
  /// leaves its old file behind for the others to merge once more rather than
  /// orphaning its contents.
  static String fileNameFor(String deviceName) {
    final StringBuffer slug = StringBuffer();
    for (final int unit in deviceName.toLowerCase().codeUnits) {
      final bool letter = unit >= 0x61 && unit <= 0x7a;
      final bool digit = unit >= 0x30 && unit <= 0x39;
      slug.write(letter || digit ? String.fromCharCode(unit) : '-');
      if (slug.length >= 32) {
        break;
      }
    }
    final String trimmed = slug
        .toString()
        .replaceAll(RegExp('-+'), '-')
        .replaceAll(RegExp(r'^-|-$'), '');
    return 'vault-${trimmed.isEmpty ? 'device' : trimmed}.$syncFileExtension';
  }

  /// Reads every other device's file, merges them in, and writes this
  /// device's own file back out carrying the result.
  ///
  /// [syncSecret] seals and opens the exchange files. It is not the master
  /// password and does not open the vault itself; see
  /// [VaultData.syncSecret].
  Future<SyncReport> run({
    required VaultData local,
    required String syncSecret,
    required String deviceName,
    DateTime? now,
  }) async {
    final String ownFile = fileNameFor(deviceName);
    final List<String> names = await folder.list();

    VaultData accumulated = local;
    MergeOutcome? combined;
    final List<PeerResult> peers = <PeerResult>[];

    for (final String name in names) {
      if (name == ownFile) {
        continue;
      }
      final PeerRead read = await _readPeer(name, syncSecret);
      final VaultData? theirs = read.data;
      if (theirs == null) {
        peers.add(PeerResult.failed(name, read.problem!));
        continue;
      }
      final MergeOutcome outcome = VaultMerge.merge(
        local: accumulated,
        other: theirs,
        now: now,
      );
      accumulated = outcome.merged;
      combined = _combine(combined, outcome);
      peers.add(
        PeerResult.mergedWith(
          name,
          itemsTaken: outcome.itemsAdded,
          dropped: read.dropped,
        ),
      );
    }

    // Written even when nothing changed, and written last. A device whose
    // file is missing from the folder is invisible to the others, so the one
    // thing this must not do is skip the write because the merge was a no-op.
    await folder.write(
      ownFile,
      codec.seal(masterPassword: syncSecret, payload: accumulated.encode()),
    );

    return SyncReport(
      merged: accumulated,
      peers: peers,
      outcome: combined,
      wroteOwnFile: true,
    );
  }

  Future<PeerRead> _readPeer(String name, String syncSecret) async {
    try {
      final Uint8List bytes = await folder.read(name);
      final Uint8List payload = codec.open(
        file: bytes,
        masterPassword: syncSecret,
      );
      final VaultDataDecoding decoded = VaultData.decode(payload);
      return PeerRead(
        data: decoded.data,
        dropped: decoded.droppedItems + decoded.droppedFolders,
      );
    } on VaultVersionFailure {
      return const PeerRead.failed(PeerProblem.tooNew);
    } on VaultFormatFailure {
      return const PeerRead.failed(PeerProblem.unintelligible);
    } on VaultFailure {
      // Authentication failure, which covers both a different sync secret and
      // a tampered or part-written file. They are indistinguishable by
      // design, so the message offers both explanations.
      return const PeerRead.failed(PeerProblem.unreadable);
    } on Object {
      // A read error from the folder itself - a file that vanished between
      // being listed and being read, which a sync client can easily cause.
      return const PeerRead.failed(PeerProblem.unreadable);
    }
  }

  /// Adds up the effect of merging several devices, so the user is told what
  /// happened overall rather than once per file.
  static MergeOutcome _combine(MergeOutcome? running, MergeOutcome next) {
    if (running == null) {
      return next;
    }
    return MergeOutcome(
      merged: next.merged,
      itemsAdded: running.itemsAdded + next.itemsAdded,
      itemsUpdated: running.itemsUpdated + next.itemsUpdated,
      itemsRemoved: running.itemsRemoved + next.itemsRemoved,
      foldersAdded: running.foldersAdded + next.foldersAdded,
      foldersUpdated: running.foldersUpdated + next.foldersUpdated,
      foldersRemoved: running.foldersRemoved + next.foldersRemoved,
      conflicts: running.conflicts + next.conflicts,
      settingsTakenFromOther:
          running.settingsTakenFromOther || next.settingsTakenFromOther,
      clockSkewSuspected: running.clockSkewSuspected || next.clockSkewSuspected,
    );
  }
}

/// The result of trying to read one peer's file.
@immutable
final class PeerRead {
  const PeerRead({required this.data, required this.dropped}) : problem = null;

  const PeerRead.failed(this.problem) : data = null, dropped = 0;

  /// What the file contained, or null if it could not be read.
  final VaultData? data;

  /// Entries in it that could not be understood.
  final int dropped;

  /// Why it could not be read.
  final PeerProblem? problem;
}
