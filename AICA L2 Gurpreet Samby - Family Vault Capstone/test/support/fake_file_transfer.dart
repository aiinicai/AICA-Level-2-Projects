import 'package:family_vault/src/platform/file_transfer.dart';
import 'package:flutter/foundation.dart';

/// A file picker that answers from memory.
///
/// A system save or open dialog cannot be answered by a widget test: it is
/// drawn by the operating system, outside Flutter's tree. This stands in for
/// it, so the export and import flows can be driven end to end — and so a
/// test can hand the import exactly the bytes a real export produced, which
/// is the only way to prove the two halves fit together.
final class FakeFileTransfer implements FileTransfer {
  FakeFileTransfer({this.hasSaveDialog = true});

  @override
  final bool hasSaveDialog;

  /// What [pick] returns next. Null means the user cancels.
  PickedFile? nextPick;

  /// What [pickFolder] returns next.
  String? nextFolder;

  /// True to make [save] report that the user backed out.
  bool cancelSave = false;

  /// Everything [save] was given, newest last.
  final List<({String name, Uint8List bytes})> saved =
      <({String name, Uint8List bytes})>[];

  /// How many times [pick] was called.
  int pickCount = 0;

  @override
  Future<SaveResult> save({
    required String suggestedName,
    required Uint8List bytes,
  }) async {
    if (cancelSave) {
      return const SaveResult.cancelled();
    }
    saved.add((name: suggestedName, bytes: bytes));
    return hasSaveDialog
        ? SaveResult.savedTo('/test/$suggestedName')
        : const SaveResult.shared();
  }

  @override
  Future<PickedFile?> pick() async {
    pickCount += 1;
    return nextPick;
  }

  @override
  Future<String?> pickFolder() async => nextFolder;

  /// Feeds the most recently saved file back in, as if the user had carried it
  /// to another device and picked it there.
  void offerLastSavedForPicking() {
    final ({String name, Uint8List bytes}) last = saved.last;
    nextPick = PickedFile(name: last.name, bytes: last.bytes);
  }
}
