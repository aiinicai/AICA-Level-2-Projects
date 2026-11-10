import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/vault_data.dart';
import '../../domain/vault_item.dart';
import 'item_detail_screen.dart';

/// A searchable list of items.
///
/// Serves every list destination — all items, each type, favourites and a
/// folder — because the only thing that differs is which items it is given.
class ItemListView extends StatefulWidget {
  const ItemListView({
    required this.items,
    required this.emptyMessage,
    super.key,
  });

  /// The items to show before any search is typed.
  final List<VaultItem> items;

  /// What to say when there are none.
  final String emptyMessage;

  @override
  State<ItemListView> createState() => _ItemListViewState();
}

class _ItemListViewState extends State<ItemListView> {
  final TextEditingController _search = TextEditingController();

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      return const SizedBox.shrink();
    }

    final String query = _search.text.trim();
    // Searching runs against the whole vault, then is narrowed to the items
    // this destination covers, so a search inside Logins stays inside Logins.
    final List<VaultItem> visible;
    if (query.isEmpty) {
      visible = widget.items;
    } else {
      final Set<String> allowed = widget.items
          .map((VaultItem i) => i.id)
          .toSet();
      visible = data
          .search(query)
          .where((VaultItem i) => allowed.contains(i.id))
          .toList();
    }

    final List<VaultItem> sorted = List<VaultItem>.of(visible)
      ..sort(
        (VaultItem a, VaultItem b) =>
            a.title.toLowerCase().compareTo(b.title.toLowerCase()),
      );

    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            controller: _search,
            decoration: InputDecoration(
              hintText: 'Search',
              prefixIcon: const Icon(Icons.search),
              border: const OutlineInputBorder(),
              isDense: true,
              suffixIcon: query.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      tooltip: 'Clear',
                      onPressed: () {
                        _search.clear();
                        setState(() {});
                      },
                    ),
            ),
            onChanged: (_) => setState(() {}),
          ),
        ),
        if (session.droppedOnOpen > 0)
          _DamageNotice(count: session.droppedOnOpen),
        Expanded(
          child: sorted.isEmpty
              ? _Empty(
                  message: query.isEmpty
                      ? widget.emptyMessage
                      : 'Nothing matches "$query".',
                )
              : ListView.separated(
                  padding: const EdgeInsets.only(bottom: 88),
                  itemCount: sorted.length,
                  separatorBuilder: (BuildContext context, int index) =>
                      const Divider(height: 1),
                  itemBuilder: (BuildContext context, int index) =>
                      ItemTile(item: sorted[index], data: data),
                ),
        ),
      ],
    );
  }
}

/// One row in a list of items.
class ItemTile extends StatelessWidget {
  const ItemTile({required this.item, required this.data, super.key});

  final VaultItem item;
  final VaultData data;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final String? folderName = data.folderById(item.folderId)?.name;
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: theme.colorScheme.secondaryContainer,
        child: Icon(
          _iconFor(item.type),
          size: 20,
          color: theme.colorScheme.onSecondaryContainer,
        ),
      ),
      title: Text(item.title, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        folderName == null ? item.subtitle : '${item.subtitle} · $folderName',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: item.favourite
          ? Icon(Icons.star, size: 18, color: theme.colorScheme.primary)
          : null,
      onTap: () => Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => ItemDetailScreen(itemId: item.id),
        ),
      ),
    );
  }

  static IconData _iconFor(VaultItemType type) => switch (type) {
    VaultItemType.login => Icons.login_outlined,
    VaultItemType.secureNote => Icons.sticky_note_2_outlined,
    VaultItemType.paymentCard => Icons.credit_card_outlined,
    VaultItemType.identity => Icons.badge_outlined,
  };
}

class _Empty extends StatelessWidget {
  const _Empty({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(
              Icons.inbox_outlined,
              size: 48,
              color: theme.colorScheme.outline,
            ),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

/// Tells the user when entries had to be dropped as unreadable.
///
/// Silence here would be worse than an alarming message: the user would have
/// no idea an entry had gone.
class _DamageNotice extends StatelessWidget {
  const _DamageNotice({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.warning_amber_outlined, color: scheme.onErrorContainer),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              count == 1
                  ? '1 entry in this vault could not be read and was left '
                        'out. The rest opened normally.'
                  : '$count entries in this vault could not be read and were '
                        'left out. The rest opened normally.',
              style: TextStyle(color: scheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
