import 'dart:typed_data';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/vault/vault_repository.dart';

/// A repository that keeps the vault in memory.
///
/// Storage itself is tested against the real file system in
/// vault_repository_test.dart; this one keeps the session tests fast and lets
/// a write failure be simulated.
final class InMemoryVaultRepository implements VaultRepository {
  Uint8List? _file;
  Uint8List? _backup;

  /// Set to make the next write fail, standing in for a full disk.
  bool failNextWrite = false;

  /// How many times a write was attempted.
  int writes = 0;

  @override
  Future<bool> exists() async => _file != null;

  @override
  Future<Uint8List> read() async {
    final Uint8List? current = _file;
    if (current == null) {
      throw const VaultFormatFailure('There is no vault on this device yet.');
    }
    return current;
  }

  @override
  Future<void> write(Uint8List bytes) async {
    writes++;
    if (failNextWrite) {
      failNextWrite = false;
      throw const VaultFormatFailure('Could not write the vault.');
    }
    _backup = _file;
    _file = bytes;
  }

  @override
  Future<void> delete() async {
    _file = null;
    _backup = null;
  }

  @override
  Future<String> location() async => 'memory://vault.fvault';

  @override
  Future<bool> hasBackup() async => _backup != null;

  @override
  Future<bool> restoreBackup() async {
    final Uint8List? previous = _backup;
    if (previous == null) {
      return false;
    }
    _file = previous;
    _backup = null;
    return true;
  }
}
