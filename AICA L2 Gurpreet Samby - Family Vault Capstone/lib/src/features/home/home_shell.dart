import 'package:flutter/material.dart';

import '../../app/build_info.dart';
import '../../app/navigation_plan.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/vault_data.dart';
import '../authenticator/authenticator_view.dart';
import '../folders/folders_view.dart';
import '../generator/generator_screen.dart';
import '../health/health_view.dart';
import '../items/item_editor_screen.dart';
import '../items/item_list_view.dart';
import '../settings/settings_view.dart';
import '../transfer/backup_view.dart';
import '../trash/trash_view.dart';
import 'dashboard_view.dart';

/// The main interface once a vault is open.
///
/// One layout, two shapes: a permanent sidebar on a wide window and a drawer
/// on a narrow one. The section list comes from [AppSection] so navigation
/// cannot drift from the definition.
///
/// Everything is wrapped so that any pointer or key event tells the session
/// the user is still here, which is what keeps the inactivity timer honest.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  /// Width past which the sidebar is always visible.
  static const double _wideBreakpoint = 900;

  AppSection _section = AppSection.dashboard;
  String? _folderFilter;

  void _go(AppSection section, {String? folderId}) {
    setState(() {
      _section = section;
      _folderFilter = folderId;
    });
  }

  Future<void> _addItem() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ItemEditorScreen(
          initialType: _section.itemType,
          initialFolderId: _folderFilter,
        ),
      ),
    );
  }

  Future<void> _openGenerator() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => const GeneratorScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      // Locked while this screen was on top; the router replaces it next
      // frame, so nothing is drawn from a vault that is no longer open.
      return const Scaffold(body: SizedBox.shrink());
    }

    final bool wide = MediaQuery.sizeOf(context).width >= _wideBreakpoint;

    return Listener(
      // Any interaction counts as activity, so the vault does not lock while
      // someone is reading a long note.
      onPointerDown: (_) => session.touch(),
      onPointerSignal: (_) => session.touch(),
      child: Focus(
        onKeyEvent: (FocusNode node, KeyEvent event) {
          session.touch();
          return KeyEventResult.ignored;
        },
        child: Scaffold(
          appBar: AppBar(
            title: Text(_titleFor(data)),
            actions: <Widget>[
              IconButton(
                tooltip: 'Password generator',
                icon: const Icon(Icons.casino_outlined),
                onPressed: _openGenerator,
              ),
              IconButton(
                tooltip: 'Lock vault',
                icon: const Icon(Icons.lock_outline),
                onPressed: session.lock,
              ),
            ],
          ),
          drawer: wide
              ? null
              : Drawer(
                  child: SafeArea(
                    child: _SectionList(
                      current: _section,
                      data: data,
                      onSelected: (AppSection section) {
                        Navigator.of(context).pop();
                        _go(section);
                      },
                    ),
                  ),
                ),
          body: Row(
            children: <Widget>[
              if (wide)
                SizedBox(
                  width: 248,
                  child: Material(
                    color: Theme.of(context).colorScheme.surfaceContainerLow,
                    child: SafeArea(
                      child: _SectionList(
                        current: _section,
                        data: data,
                        onSelected: (AppSection section) => _go(section),
                      ),
                    ),
                  ),
                ),
              if (wide) const VerticalDivider(width: 1),
              Expanded(child: SafeArea(child: _buildSection(data))),
            ],
          ),
          floatingActionButton: _showsAddButton
              ? FloatingActionButton.extended(
                  onPressed: _addItem,
                  icon: const Icon(Icons.add),
                  label: const Text('Add'),
                )
              : null,
        ),
      ),
    );
  }

  bool get _showsAddButton => switch (_section) {
    AppSection.dashboard ||
    AppSection.allItems ||
    AppSection.logins ||
    AppSection.notes ||
    AppSection.cards ||
    AppSection.identities ||
    AppSection.favourites => true,
    _ => false,
  };

  String _titleFor(VaultData data) {
    if (_folderFilter != null) {
      return data.folderById(_folderFilter)?.name ?? 'Folder';
    }
    return _section == AppSection.dashboard ? appName : _section.label;
  }

  Widget _buildSection(VaultData data) {
    if (_folderFilter != null) {
      return ItemListView(
        items: data.itemsInFolder(_folderFilter),
        emptyMessage: 'Nothing in this folder yet.',
      );
    }
    return switch (_section) {
      AppSection.dashboard => DashboardView(onGo: _go),
      AppSection.allItems => ItemListView(
        items: data.liveItems,
        emptyMessage:
            'Your vault is empty. Tap Add to save your first password.',
      ),
      AppSection.logins ||
      AppSection.notes ||
      AppSection.cards ||
      AppSection.identities => ItemListView(
        items: data.itemsOfType(_section.itemType!),
        emptyMessage: 'No ${_section.label.toLowerCase()} saved yet.',
      ),
      AppSection.favourites => ItemListView(
        items: data.favourites,
        emptyMessage:
            'No favourites yet. Star an entry to find it quickly here.',
      ),
      AppSection.folders => FoldersView(
        onOpenFolder: (String id) => _go(AppSection.folders, folderId: id),
      ),
      AppSection.authenticator => const AuthenticatorView(),
      AppSection.health => const HealthView(),
      AppSection.trash => const TrashView(),
      AppSection.backup => const BackupView(),
      AppSection.settings => const SettingsView(),
    };
  }
}

/// The navigation list, used both in the sidebar and in the drawer.
class _SectionList extends StatelessWidget {
  const _SectionList({
    required this.current,
    required this.data,
    required this.onSelected,
  });

  final AppSection current;
  final VaultData data;
  final ValueChanged<AppSection> onSelected;

  int? _countFor(AppSection section) => switch (section) {
    AppSection.allItems => data.liveItems.length,
    AppSection.logins => data.itemsOfType(section.itemType!).length,
    AppSection.notes => data.itemsOfType(section.itemType!).length,
    AppSection.cards => data.itemsOfType(section.itemType!).length,
    AppSection.identities => data.itemsOfType(section.itemType!).length,
    AppSection.favourites => data.favourites.length,
    AppSection.folders => data.folders.length,
    AppSection.authenticator => data.authenticatorItems.length,
    AppSection.trash => data.trashedItems.length,
    _ => null,
  };

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: <Widget>[
        for (final AppSection section in AppSection.values)
          _SectionTile(
            section: section,
            selected: section == current,
            count: _countFor(section),
            onTap: () => onSelected(section),
          ),
        const Divider(),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Text('$appName $appVersion', style: theme.textTheme.bodySmall),
        ),
      ],
    );
  }
}

class _SectionTile extends StatelessWidget {
  const _SectionTile({
    required this.section,
    required this.selected,
    required this.onTap,
    this.count,
  });

  final AppSection section;
  final bool selected;
  final VoidCallback onTap;
  final int? count;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return ListTile(
      selected: selected,
      leading: Icon(selected ? section.selectedIcon : section.icon),
      title: Text(section.label),
      trailing: count != null && count! > 0
          ? Text('$count', style: theme.textTheme.labelMedium)
          : null,
      onTap: onTap,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.horizontal(right: Radius.circular(24)),
      ),
    );
  }
}
