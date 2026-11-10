import 'dart:typed_data';

import 'package:family_vault/src/vault/vault_sync.dart';

/// A shared folder that lives in a map.
///
/// Real directory behaviour - the temporary-file write, a missing folder, the
/// extension filter - is tested against the real file system in
/// vault_sync_test.dart. This is for the merge logic, where going through
/// disk would only add latency and a cleanup step.
final class InMemorySyncFolder implements SyncFolder {
  InMemorySyncFolder([Map<String, Uint8List>? initial])
    : files = <String, Uint8List>{...?initial};

  /// Everything in the folder, by name.
  final Map<String, Uint8List> files;

  /// Set to make [list] fail, standing in for a disconnected drive.
  Object? listFailure;

  /// Names [read] should fail on, standing in for a file that vanished
  /// between being listed and being read.
  final Set<String> unreadable = <String>{};

  /// Every name written, in order.
  final List<String> written = <String>[];

  @override
  Future<List<String>> list() async {
    final Object? failure = listFailure;
    if (failure != null) {
      throw failure;
    }
    return files.keys.where((String n) => n.endsWith('.fvault')).toList()
      ..sort();
  }

  @override
  Future<Uint8List> read(String name) async {
    if (unreadable.contains(name)) {
      throw StateError('$name vanished between being listed and being read');
    }
    final Uint8List? bytes = files[name];
    if (bytes == null) {
      throw StateError('$name is not in this folder');
    }
    return bytes;
  }

  @override
  Future<void> write(String name, Uint8List bytes) async {
    written.add(name);
    files[name] = bytes;
  }

  @override
  String describe() => 'in memory';
}
