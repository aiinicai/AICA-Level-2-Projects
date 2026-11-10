import 'package:flutter/widgets.dart';

import '../platform/file_transfer.dart';

/// Makes the file picker available to the backup screens.
///
/// Separate from [SessionScope] because it holds no state and never changes;
/// an [InheritedWidget] is enough. It exists so the widget tests can supply a
/// picker that returns bytes from memory instead of opening a system dialog,
/// which a test has no way to answer.
class FileTransferScope extends InheritedWidget {
  const FileTransferScope({
    required this.transfer,
    required super.child,
    super.key,
  });

  /// How files leave and enter the application.
  final FileTransfer transfer;

  /// The picker for this part of the tree.
  static FileTransfer of(BuildContext context) {
    final FileTransferScope? scope = context
        .dependOnInheritedWidgetOfExactType<FileTransferScope>();
    assert(scope != null, 'No FileTransferScope found in the widget tree');
    return scope!.transfer;
  }

  @override
  bool updateShouldNotify(FileTransferScope oldWidget) =>
      transfer != oldWidget.transfer;
}
