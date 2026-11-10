// Moving vault files between the application and the outside world.
//
// The two platforms do not have the same capabilities, and the difference is
// not cosmetic:
//
//   - Windows, macOS and Linux have a real save dialog. The user picks a
//     path and the application writes to it.
//   - Android has no save dialog. file_selector_android implements
//     openFile and getDirectoryPath but not getSaveLocation - verified by
//     reading the resolved package in CI run 42790776305, not from memory -
//     because the Android system chooser hands back a content:// URI rather
//     than a file path. Saving therefore goes through the share sheet, where
//     the user picks Drive, Files, a messaging app or anything else that
//     accepts a file.
//
// Opening a file is the same call everywhere, which is why import needs no
// branching and export does.
//
// Nothing here knows what is inside the bytes. The vault is already encrypted
// before it reaches this layer, which is what makes handing it to an arbitrary
// share target acceptable.

import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// The file extension Family Vault uses for both the live vault and backups.
const String vaultExtension = 'fvault';

/// What happened to a save request.
enum SaveMethod {
  /// Written to a path the user chose.
  savedToPath,

  /// Handed to the system share sheet; where it went is up to the user.
  handedToShareSheet,

  /// The user backed out. Nothing was written.
  cancelled,
}

/// The outcome of a save, in terms the interface can report.
@immutable
final class SaveResult {
  const SaveResult.savedTo(this.path) : method = SaveMethod.savedToPath;

  const SaveResult.shared()
    : method = SaveMethod.handedToShareSheet,
      path = null;

  const SaveResult.cancelled() : method = SaveMethod.cancelled, path = null;

  /// How the file left the application.
  final SaveMethod method;

  /// Where it was written, when a path was chosen.
  final String? path;

  /// True when nothing left the application.
  bool get cancelled => method == SaveMethod.cancelled;

  /// A sentence for the user. Deliberately does not promise more than it
  /// knows: after a share there is no way to find out which app took the file.
  String get message => switch (method) {
    SaveMethod.savedToPath => 'Backup saved to ${path ?? 'the chosen file'}.',
    SaveMethod.handedToShareSheet =>
      'Backup handed to the share sheet. Check the app you sent it to.',
    SaveMethod.cancelled => 'Backup cancelled. Nothing was written.',
  };
}

/// A file the user chose, read into memory.
@immutable
final class PickedFile {
  const PickedFile({required this.name, required this.bytes});

  /// The file's name, for showing back to the user.
  final String name;

  /// Its contents.
  final Uint8List bytes;
}

/// Reading and writing files the user picks.
///
/// An interface because the widget tests must not open a system dialog.
abstract interface class FileTransfer {
  /// True when this platform can write to a path the user chooses, so the
  /// interface can say "Save a copy" rather than "Share a copy".
  bool get hasSaveDialog;

  /// Offers [bytes] to the user as a file named [suggestedName].
  Future<SaveResult> save({
    required String suggestedName,
    required Uint8List bytes,
  });

  /// Asks the user for a file and reads it. Null when they cancel.
  Future<PickedFile?> pick();

  /// Asks the user for a folder. Null when they cancel.
  ///
  /// Used for the shared-folder sync, where a path has to be remembered
  /// rather than used once.
  Future<String?> pickFolder();
}

/// The real implementation, backed by file_selector and share_plus.
final class PlatformFileTransfer implements FileTransfer {
  const PlatformFileTransfer();

  /// Android has no save dialog; every other platform this project builds
  /// for does. Checked through [defaultTargetPlatform] rather than
  /// [Platform] so the web demonstration does not crash on a missing
  /// dart:io.
  @override
  bool get hasSaveDialog =>
      !kIsWeb && defaultTargetPlatform != TargetPlatform.android;

  /// A filter for the save and open dialogs.
  ///
  /// Only used on the platforms that have those dialogs. Android is excluded
  /// because .fvault has no registered MIME type, and file_selector_android
  /// rejects a type group it cannot translate into one.
  static const List<XTypeGroup> _vaultFiles = <XTypeGroup>[
    XTypeGroup(
      label: 'Family Vault backup',
      extensions: <String>[vaultExtension],
    ),
  ];

  @override
  Future<SaveResult> save({
    required String suggestedName,
    required Uint8List bytes,
  }) async {
    if (kIsWeb) {
      // No file system to stage through, so the bytes are shared straight
      // from memory. share_plus falls back to a browser download when the
      // browser has no share target, which is what the public demonstration
      // build needs.
      final ShareResult result = await SharePlus.instance.share(
        ShareParams(
          files: <XFile>[
            XFile.fromData(
              bytes,
              name: suggestedName,
              mimeType: 'application/octet-stream',
            ),
          ],
          fileNameOverrides: <String>[suggestedName],
          subject: suggestedName,
          downloadFallbackEnabled: true,
        ),
      );
      return result.status == ShareResultStatus.dismissed
          ? const SaveResult.cancelled()
          : const SaveResult.shared();
    }

    if (hasSaveDialog) {
      final FileSaveLocation? where = await getSaveLocation(
        suggestedName: suggestedName,
        acceptedTypeGroups: _vaultFiles,
      );
      if (where == null) {
        return const SaveResult.cancelled();
      }
      final File file = File(where.path);
      await file.writeAsBytes(bytes, flush: true);
      return SaveResult.savedTo(where.path);
    }

    // Android: stage the file where the share sheet can reach it, then let
    // the user choose the destination. The staging directory is cleared
    // first rather than afterwards, because the receiving app may still be
    // reading the file when share() returns.
    final Directory staging = Directory(
      '${(await getTemporaryDirectory()).path}${Platform.pathSeparator}outgoing',
    );
    if (staging.existsSync()) {
      staging.deleteSync(recursive: true);
    }
    staging.createSync(recursive: true);

    final File staged = File(
      '${staging.path}${Platform.pathSeparator}$suggestedName',
    );
    await staged.writeAsBytes(bytes, flush: true);

    final ShareResult result = await SharePlus.instance.share(
      ShareParams(
        files: <XFile>[
          XFile(staged.path, mimeType: 'application/octet-stream'),
        ],
        fileNameOverrides: <String>[suggestedName],
        subject: suggestedName,
      ),
    );
    return result.status == ShareResultStatus.dismissed
        ? const SaveResult.cancelled()
        : const SaveResult.shared();
  }

  @override
  Future<PickedFile?> pick() async {
    final XFile? chosen = await openFile(
      acceptedTypeGroups: hasSaveDialog ? _vaultFiles : const <XTypeGroup>[],
    );
    if (chosen == null) {
      return null;
    }
    return PickedFile(name: chosen.name, bytes: await chosen.readAsBytes());
  }

  /// Asks the user for a folder.
  ///
  /// Returns null on the web, where there is no folder to pick: the browser
  /// gives a page access to files the user chooses, never to a directory it
  /// can list and write to later, which is what the shared-folder sync needs.
  @override
  Future<String?> pickFolder() async => kIsWeb ? null : getDirectoryPath();
}
