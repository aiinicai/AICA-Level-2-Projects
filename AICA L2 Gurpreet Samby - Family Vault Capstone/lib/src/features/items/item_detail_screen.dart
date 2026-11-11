import 'dart:async';

import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/totp.dart';
import '../../domain/vault_data.dart';
import '../../domain/vault_item.dart';
import 'item_editor_screen.dart';

/// Shows one item, with its secrets hidden until asked for.
///
/// Secrets are masked by default and revealed one at a time. The point is not
/// to stop the owner seeing their own password, but to stop it being on screen
/// when someone glances over, and to keep it out of screenshots.
class ItemDetailScreen extends StatefulWidget {
  const ItemDetailScreen({required this.itemId, super.key});

  final String itemId;

  @override
  State<ItemDetailScreen> createState() => _ItemDetailScreenState();
}

class _ItemDetailScreenState extends State<ItemDetailScreen> {
  final Set<String> _revealed = <String>{};

  Future<void> _copy(String label, String value) async {
    final VaultSession session = SessionScope.read(context);
    await session.copyToClipboard(value);
    if (!mounted) {
      return;
    }
    final int seconds = session.settings.clipboardClearSeconds;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          seconds > 0
              ? '$label copied. The clipboard clears in $seconds seconds.'
              : '$label copied.',
        ),
      ),
    );
  }

  Future<void> _confirmDelete(VaultItem item) async {
    final bool? yes = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Move to trash?'),
        content: Text(
          '"${item.title}" goes to the trash. You can restore it from there '
          'until you empty it.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Move to trash'),
          ),
        ],
      ),
    );
    if (yes != true || !mounted) {
      return;
    }
    final NavigatorState navigator = Navigator.of(context);
    await SessionScope.read(context).trashItem(item.id);
    if (mounted) {
      navigator.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    final VaultItem? item = data?.itemById(widget.itemId);
    if (data == null || item == null) {
      // The vault locked, or the item was deleted elsewhere.
      return const Scaffold(body: SizedBox.shrink());
    }

    final ThemeData theme = Theme.of(context);
    final String? folderName = data.folderById(item.folderId)?.name;

    return Scaffold(
      appBar: AppBar(
        title: Text(item.title, overflow: TextOverflow.ellipsis),
        actions: <Widget>[
          IconButton(
            tooltip: item.favourite ? 'Remove favourite' : 'Add favourite',
            icon: Icon(item.favourite ? Icons.star : Icons.star_outline),
            onPressed: () => session.toggleFavourite(item.id),
          ),
          IconButton(
            tooltip: 'Edit',
            icon: const Icon(Icons.edit_outlined),
            onPressed: () => Navigator.of(context).push<void>(
              MaterialPageRoute<void>(
                builder: (BuildContext context) =>
                    ItemEditorScreen(itemId: item.id),
              ),
            ),
          ),
          IconButton(
            tooltip: 'Move to trash',
            icon: const Icon(Icons.delete_outline),
            onPressed: () => _confirmDelete(item),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          Text(item.type.label, style: theme.textTheme.labelLarge),
          if (folderName != null) ...<Widget>[
            const SizedBox(height: 4),
            Row(
              children: <Widget>[
                const Icon(Icons.folder_outlined, size: 16),
                const SizedBox(width: 6),
                Text(folderName, style: theme.textTheme.bodySmall),
              ],
            ),
          ],
          const SizedBox(height: 16),

          for (final ItemFieldSpec spec in item.type.fields)
            if (item.field(spec.key).isNotEmpty)
              if (spec.input == FieldInput.totpSecret)
                _AuthenticatorCard(secret: item.field(spec.key))
              else
                _FieldRow(
                  spec: spec,
                  value: item.field(spec.key),
                  revealed: _revealed.contains(spec.key),
                  onToggleReveal: () => setState(() {
                    if (!_revealed.remove(spec.key)) {
                      _revealed.add(spec.key);
                    }
                  }),
                  onCopy: () => _copy(spec.label, item.field(spec.key)),
                ),

          if (item.notes.isNotEmpty) ...<Widget>[
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Notes', style: theme.textTheme.labelMedium),
                    const SizedBox(height: 6),
                    SelectableText(item.notes),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 16),
          Text(
            'Added ${_formatDate(item.createdAt)} · '
            'last changed ${_formatDate(item.updatedAt)}',
            style: theme.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  static String _formatDate(DateTime when) {
    final DateTime local = when.toLocal();
    const List<String> months = <String>[
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${local.day} ${months[local.month - 1]} ${local.year}';
  }
}

/// One field, with copy and reveal.
class _FieldRow extends StatelessWidget {
  const _FieldRow({
    required this.spec,
    required this.value,
    required this.revealed,
    required this.onToggleReveal,
    required this.onCopy,
  });

  final ItemFieldSpec spec;
  final String value;
  final bool revealed;
  final VoidCallback onToggleReveal;
  final VoidCallback onCopy;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final bool hidden = spec.isSecret && !revealed;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 8, 10),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(spec.label, style: theme.textTheme.labelMedium),
                  const SizedBox(height: 4),
                  hidden
                      ? Text(
                          '•' * (value.length.clamp(8, 24)),
                          style: theme.textTheme.bodyLarge,
                        )
                      : SelectableText(
                          value,
                          style: spec.isSecret
                              ? theme.textTheme.bodyLarge?.copyWith(
                                  fontFamily: 'monospace',
                                )
                              : theme.textTheme.bodyLarge,
                        ),
                ],
              ),
            ),
            if (spec.isSecret)
              IconButton(
                tooltip: revealed ? 'Hide' : 'Show',
                icon: Icon(
                  revealed
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                ),
                onPressed: onToggleReveal,
              ),
            IconButton(
              tooltip: 'Copy',
              icon: const Icon(Icons.copy_outlined),
              onPressed: onCopy,
            ),
          ],
        ),
      ),
    );
  }
}

/// Live six-digit code with a countdown.
class _AuthenticatorCard extends StatefulWidget {
  const _AuthenticatorCard({required this.secret});

  final String secret;

  @override
  State<_AuthenticatorCard> createState() => _AuthenticatorCardState();
}

class _AuthenticatorCardState extends State<_AuthenticatorCard> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(
      const Duration(seconds: 1),
      (_) => setState(() {}),
    );
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    TotpConfig? config;
    try {
      config = TotpConfig.fromBase32(widget.secret);
    } on FormatException {
      config = null;
    }

    if (config == null || !config.isUsable) {
      return Card(
        color: theme.colorScheme.errorContainer,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'The authenticator key saved here is not valid, so no codes can '
            'be generated. Edit this entry and paste the key again.',
            style: TextStyle(color: theme.colorScheme.onErrorContainer),
          ),
        ),
      );
    }

    final String code = Totp.generate(config);
    final int remaining = Totp.secondsRemaining(config);
    final String spaced = code.length == 6
        ? '${code.substring(0, 3)} ${code.substring(3)}'
        : code;

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Authenticator code',
                    style: theme.textTheme.labelMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    spaced,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontFamily: 'monospace',
                      letterSpacing: 2,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: <Widget>[
                      SizedBox(
                        width: 80,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(3),
                          child: LinearProgressIndicator(
                            value: remaining / config.period,
                            minHeight: 4,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        remaining == 1
                            ? 'changes in 1 second'
                            : 'changes in $remaining seconds',
                        style: theme.textTheme.bodySmall,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: 'Copy code',
              icon: const Icon(Icons.copy_outlined),
              onPressed: () async {
                final VaultSession session = SessionScope.read(context);
                await session.copyToClipboard(code);
                if (context.mounted) {
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(const SnackBar(content: Text('Code copied.')));
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}
