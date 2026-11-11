import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

import '../core/failures.dart';

/// Where a vault file lives and how it is read and written.
///
/// An interface so that tests can use a temporary directory, and so that
/// Phase 2's cloud synchronisation can wrap this rather than reach past it.
abstract interface class VaultRepository {
  /// True when a vault file is already present.
  Future<bool> exists();

  /// Reads the vault file.
  ///
  /// Throws [VaultFormatFailure] when there is no file to read.
  Future<Uint8List> read();

  /// Writes the vault file.
  ///
  /// Must not leave a half-written file behind if the process stops partway,
  /// and must keep the previous version recoverable.
  Future<void> write(Uint8List bytes);

  /// Deletes the vault file and its backup.
  Future<void> delete();

  /// Where the file is, for showing the user.
  Future<String> location();

  /// True when a recoverable backup of the previous save exists.
  Future<bool> hasBackup();

  /// Restores the previous save, if there is one.
  ///
  /// Returns false when there was nothing to restore.
  Future<bool> restoreBackup();
}

/// Stores the vault as a file in the application's own directory.
///
/// Writing is done in three steps rather than one, because a password manager
/// that corrupts its vault has destroyed everything the user put in it:
///
/// 1. the new vault is written to a temporary file and flushed to disk,
/// 2. the existing vault, if any, is moved aside as a backup,
/// 3. the temporary file is renamed into place.
///
/// A rename within one directory is atomic on every platform this targets, so
/// at no point is the real vault file partially written. If the process dies
/// between steps 2 and 3, the backup still holds the last good vault.
final class FileVaultRepository implements VaultRepository {
  FileVaultRepository({
    required this.directory,
    this.fileName = 'vault.fvault',
  });

  /// Uses the platform's private application-support directory.
  ///
  /// On Android this is inside the app's sandbox, which other apps cannot
  /// read. On Windows it is under the user's own profile.
  static Future<FileVaultRepository> forPlatform() async {
    final Directory directory = await getApplicationSupportDirectory();
    if (!directory.existsSync()) {
      await directory.create(recursive: true);
    }
    return FileVaultRepository(directory: directory);
  }

  /// Directory the vault lives in.
  final Directory directory;

  /// Name of the vault file inside [directory].
  final String fileName;

  File get _file => File('${directory.path}${Platform.pathSeparator}$fileName');

  File get _temporary =>
      File('${directory.path}${Platform.pathSeparator}$fileName.writing');

  File get _backup =>
      File('${directory.path}${Platform.pathSeparator}$fileName.previous');

  @override
  Future<bool> exists() => _file.exists();

  @override
  Future<String> location() async => _file.path;

  @override
  Future<bool> hasBackup() => _backup.exists();

  @override
  Future<Uint8List> read() async {
    if (!await _file.exists()) {
      throw const VaultFormatFailure('There is no vault on this device yet.');
    }
    return _file.readAsBytes();
  }

  @override
  Future<void> write(Uint8List bytes) async {
    if (!directory.existsSync()) {
      await directory.create(recursive: true);
    }

    // Step 1: write and flush, so the bytes are really on disk before
    // anything existing is touched.
    final RandomAccessFile handle = await _temporary.open(
      mode: FileMode.writeOnly,
    );
    try {
      await handle.writeFrom(bytes);
      await handle.flush();
    } finally {
      await handle.close();
    }

    // Step 2: move the current vault aside rather than overwriting it.
    if (await _file.exists()) {
      if (await _backup.exists()) {
        await _backup.delete();
      }
      await _file.rename(_backup.path);
    }

    // Step 3: atomically put the new vault in place.
    await _temporary.rename(_file.path);
  }

  @override
  Future<bool> restoreBackup() async {
    if (!await _backup.exists()) {
      return false;
    }
    if (await _file.exists()) {
      await _file.delete();
    }
    await _backup.rename(_file.path);
    return true;
  }

  @override
  Future<void> delete() async {
    for (final File file in <File>[_file, _backup, _temporary]) {
      if (await file.exists()) {
        await file.delete();
      }
    }
  }
}
