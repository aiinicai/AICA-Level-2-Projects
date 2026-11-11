import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/folder.dart';
import '../../domain/vault_data.dart';

/// Lists folders, with suggestions when there are none yet.
class FoldersView extends StatelessWidget {
  const FoldersView({required this.onOpenFolder, super.key});

  /// Opens a folder's contents.
  final void Function(String folderId) onOpenFolder;

  /// Offered on an empty folder list, so a new user does not face a blank
  /// screen and an empty text box.
  static const List<String> suggestions = <String>[
    'Banking',
    'Shopping',
    'Social Media',
    'Email',
    'Work',
    'Government',
    'Family',
    'Travel',
  ];

  Future<void> _promptForName(BuildContext context, {Folder? existing}) async {
    final TextEditingController controller = TextEditingController(
      text: existing?.name ?? '',
    );
    final String? name = await showDialog<String>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: Text(existing == null ? 'New folder' : 'Rename folder'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(
            labelText: 'Folder name',
            border: OutlineInputBorder(),
          ),
          onSubmitted: (String value) =>
              Navigator.of(context).pop(value.trim()),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text.trim()),
            child: Text(existing == null ? 'Create' : 'Rename'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (name == null || name.isEmpty || !context.mounted) {
      return;
    }
    final VaultSession session = SessionScope.read(context);
    if (existing == null) {
      await session.addFolder(name);
    } else {
      await session.renameFolder(existing.id, name);
    }
  }

  Future<void> _confirmDelete(
    BuildContext context,
    Folder folder,
    int itemCount,
  ) async {
    final bool? yes = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: Text('Delete "${folder.name}"?'),
        content: Text(
          itemCount == 0
              ? 'The folder is empty, so nothing else changes.'
              : itemCount == 1
              ? 'The 1 entry in it will be kept and simply left without a '
                    'folder. Nothing is deleted.'
              : 'The $itemCount entries in it will be kept and simply left '
                    'without a folder. Nothing is deleted.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete folder'),
          ),
        ],
      ),
    );
    if (yes == true && context.mounted) {
      await SessionScope.read(context).deleteFolder(folder.id);
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
    final List<Folder> folders = List<Folder>.of(data.folders)
      ..sort(
        (Folder a, Folder b) =>
            a.name.toLowerCase().compareTo(b.name.toLowerCase()),
      );
    final int unfiled = data.itemsInFolder(null).length;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
      children: <Widget>[
        FilledButton.icon(
          onPressed: () => _promptForName(context),
          icon: const Icon(Icons.create_new_folder_outlined),
          label: const Text('New folder'),
        ),
        const SizedBox(height: 16),

        if (folders.isEmpty) ...<Widget>[
          Text(
            'Folders keep things findable once you have more than a handful '
            'of entries. Common ones:',
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              for (final String name in suggestions)
                ActionChip(
                  avatar: const Icon(Icons.add, size: 18),
                  label: Text(name),
                  onPressed: () => SessionScope.read(context).addFolder(name),
                ),
            ],
          ),
          const SizedBox(height: 16),
        ],

        for (final Folder folder in folders)
          Card(
            child: ListTile(
              leading: const Icon(Icons.folder_outlined),
              title: Text(folder.name),
              subtitle: Text(
                _describeCount(data.itemsInFolder(folder.id).length),
              ),
              onTap: () => onOpenFolder(folder.id),
              trailing: PopupMenuButton<String>(
                tooltip: 'Folder options',
                onSelected: (String action) {
                  if (action == 'rename') {
                    _promptForName(context, existing: folder);
                  } else if (action == 'delete') {
                    _confirmDelete(
                      context,
                      folder,
                      data.itemsInFolder(folder.id).length,
                    );
                  }
                },
                itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
                  const PopupMenuItem<String>(
                    value: 'rename',
                    child: Text('Rename'),
                  ),
                  const PopupMenuItem<String>(
                    value: 'delete',
                    child: Text('Delete'),
                  ),
                ],
              ),
            ),
          ),

        if (unfiled > 0) ...<Widget>[
          const SizedBox(height: 8),
          Text(
            '${_describeCount(unfiled)} not in any folder.',
            style: theme.textTheme.bodySmall,
          ),
        ],
      ],
    );
  }

  static String _describeCount(int count) =>
      count == 1 ? '1 entry' : '$count entries';
}
