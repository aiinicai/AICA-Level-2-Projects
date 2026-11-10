import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/vault_data.dart';
import '../../domain/vault_item.dart';

/// Deleted entries, restorable until the trash is emptied.
///
/// Trashed entries stay inside the encrypted vault, so "deleted" never means
/// "written somewhere in the clear".
class TrashView extends StatelessWidget {
  const TrashView({super.key});

  Future<void> _confirmPurge(BuildContext context, VaultItem item) async {
    final bool? yes = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Delete for good?'),
        content: Text(
          '"${item.title}" will be gone permanently. This cannot be undone.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete for good'),
          ),
        ],
      ),
    );
    if (yes == true && context.mounted) {
      await SessionScope.read(context).purgeItem(item.id);
    }
  }

  Future<void> _confirmEmpty(BuildContext context, int count) async {
    final bool? yes = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Empty the trash?'),
        content: Text(
          count == 1
              ? '1 entry will be deleted permanently. This cannot be undone.'
              : '$count entries will be deleted permanently. This cannot be '
                    'undone.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Empty trash'),
          ),
        ],
      ),
    );
    if (yes == true && context.mounted) {
      await SessionScope.read(context).emptyTrash();
    }
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      return const SizedBox.shrink();
    }
    final ThemeData theme = Theme.of(context);
    final List<VaultItem> items = data.trashedItems;

    if (items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(
                Icons.delete_outline,
                size: 48,
                color: theme.colorScheme.outline,
              ),
              const SizedBox(height: 12),
              Text('The trash is empty.', style: theme.textTheme.bodyMedium),
            ],
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
      children: <Widget>[
        Text(
          'Entries here are still encrypted inside your vault. Restore them '
          'or delete them for good.',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () => _confirmEmpty(context, items.length),
          icon: const Icon(Icons.delete_forever_outlined),
          label: const Text('Empty trash'),
        ),
        const SizedBox(height: 16),
        for (final VaultItem item in items)
          Card(
            child: ListTile(
              title: Text(item.title),
              subtitle: Text(item.type.label),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  IconButton(
                    tooltip: 'Restore',
                    icon: const Icon(Icons.restore),
                    onPressed: () => session.restoreItem(item.id),
                  ),
                  IconButton(
                    tooltip: 'Delete for good',
                    icon: const Icon(Icons.delete_forever_outlined),
                    onPressed: () => _confirmPurge(context, item),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
