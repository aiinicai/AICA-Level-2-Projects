import 'package:flutter/widgets.dart';

import 'vault_session.dart';

/// Makes the one [VaultSession] available to the whole widget tree.
///
/// Flutter's own [InheritedNotifier] rather than a state-management package.
/// There is exactly one piece of shared state in this application, and adding
/// a dependency to carry it would be weight for its own sake. See
/// docs/decisions-and-risks.md, decision D-005.
class SessionScope extends InheritedNotifier<VaultSession> {
  const SessionScope({
    required VaultSession session,
    required super.child,
    super.key,
  }) : super(notifier: session);

  /// The session, rebuilding the caller when it changes.
  static VaultSession of(BuildContext context) {
    final SessionScope? scope = context
        .dependOnInheritedWidgetOfExactType<SessionScope>();
    assert(scope != null, 'No SessionScope found in the widget tree');
    return scope!.notifier!;
  }

  /// The session, without subscribing to changes.
  ///
  /// For callbacks that only need to call a method, so that a button press
  /// does not make its whole subtree rebuild.
  static VaultSession read(BuildContext context) {
    final SessionScope? scope = context
        .getInheritedWidgetOfExactType<SessionScope>();
    assert(scope != null, 'No SessionScope found in the widget tree');
    return scope!.notifier!;
  }
}
