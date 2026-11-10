// Backup and transfer.
//
// This screen is the only way vault data legitimately leaves the device, and
// the only way data from another device gets in. Three rules shape it:
//
//   1. What leaves is encrypted before it is written. The file handed to the
//      share sheet or saved to disk is the same format as the live vault, so
//      an unencrypted copy never exists, not even briefly.
//   2. An import is read, described, and only then applied. The user sees
//      what is in the file before anything on this device changes.
//   3. An import merges; it does not overwrite. Per entry the more recent
//      change wins, and an entry only disappears if the other device
//      recorded that it was deleted for good. See VaultMerge.

import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../app/build_info.dart';
import '../../app/file_transfer_scope.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../platform/file_transfer.dart';
import '../../vault/vault_merge.dart';
import 'password_prompt.dart';
import 'sync_card.dart';

/// Export and import, on one screen.
class BackupView extends StatefulWidget {
  const BackupView({super.key});

  @override
  State<BackupView> createState() => _BackupViewState();
}

class _BackupViewState extends State<BackupView> {
  bool _ownPassword = false;
  final TextEditingController _password = TextEditingController();
  final TextEditingController _confirm = TextEditingController();
  bool _working = false;
  String? _notice;

  @override
  void dispose() {
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final FileTransfer transfer = FileTransferScope.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        _ExportCard(
          ownPassword: _ownPassword,
          password: _password,
          confirm: _confirm,
          working: _working,
          hasSaveDialog: transfer.hasSaveDialog,
          onOwnPasswordChanged: (bool value) =>
              setState(() => _ownPassword = value),
          onExport: _working ? null : () => _export(transfer),
        ),
        const SizedBox(height: 16),
        _ImportCard(
          working: _working,
          onImport: _working ? null : () => _import(transfer),
        ),
        if (_notice != null) ...<Widget>[
          const SizedBox(height: 16),
          Card(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(_notice!, key: const Key('backup-notice')),
            ),
          ),
        ],
        const SizedBox(height: 16),
        // The public demonstration runs in a browser, which gives a page
        // access to files the user picks but never to a folder it can list
        // and write to later. Showing a sync card that cannot work would be
        // worse than not showing one.
        if (!isDemoBuild) ...<Widget>[
          const SyncCard(),
          const SizedBox(height: 16),
        ],
        const _TransferAdvice(),
      ],
    );
  }

  // ------------------------------------------------------------------ export

  Future<void> _export(FileTransfer transfer) async {
    final VaultSession session = SessionScope.read(context);

    String password;
    if (_ownPassword) {
      if (_password.text.isEmpty) {
        setState(() => _notice = 'Enter a password for the backup file.');
        return;
      }
      if (_password.text != _confirm.text) {
        setState(() => _notice = 'The two backup passwords do not match.');
        return;
      }
      password = _password.text;
    } else {
      final String? entered = await _askPassword(
        title: 'Confirm your master password',
        hint:
            'The backup will be protected by this password, the same one that '
            'opens this vault.',
      );
      if (entered == null) {
        return;
      }
      // Checked by trying it: deriving a key from a mistyped password would
      // produce a file the user could never open, and they would not find out
      // until the day they needed it.
      if (!await session.verifyMasterPassword(entered)) {
        if (!mounted) {
          return;
        }
        setState(
          () => _notice = 'That is not the master password for this vault.',
        );
        return;
      }
      password = entered;
    }

    setState(() {
      _working = true;
      _notice = null;
    });
    try {
      final Uint8List? bytes = session.exportEncrypted(password);
      if (bytes == null) {
        setState(() => _notice = session.lastError ?? 'Backup failed.');
        return;
      }
      final SaveResult result = await transfer.save(
        suggestedName: _suggestedName(),
        bytes: bytes,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _notice = result.cancelled
            ? result.message
            : '${result.message} It can only be opened with the password you '
                  'just gave. Keep that password somewhere other than this '
                  'vault.';
        if (!result.cancelled) {
          _password.clear();
          _confirm.clear();
        }
      });
    } finally {
      if (mounted) {
        setState(() => _working = false);
      }
    }
  }

  /// A name that sorts by date and says what the file is.
  static String _suggestedName() {
    final DateTime now = DateTime.now();
    String two(int value) => value.toString().padLeft(2, '0');
    return 'family-vault-${now.year}-${two(now.month)}-${two(now.day)}'
        '.$vaultExtension';
  }

  // ------------------------------------------------------------------ import

  Future<void> _import(FileTransfer transfer) async {
    final VaultSession session = SessionScope.read(context);

    final PickedFile? chosen = await transfer.pick();
    if (chosen == null || !mounted) {
      return;
    }

    final String? password = await _askPassword(
      title: 'Password for ${chosen.name}',
      hint:
          'The password that was set when this backup was made. It may differ '
          'from the password for this vault.',
    );
    if (password == null || !mounted) {
      return;
    }

    setState(() {
      _working = true;
      _notice = null;
    });
    try {
      final BackupContents? backup = await session.readBackup(
        file: chosen.bytes,
        password: password,
        fileName: chosen.name,
      );
      if (!mounted) {
        return;
      }
      if (backup == null) {
        setState(
          () => _notice = session.lastError ?? 'That file would not open.',
        );
        return;
      }

      final bool go = await _confirmMerge(backup) ?? false;
      if (!go || !mounted) {
        setState(() => _notice = 'Import cancelled. Nothing was changed.');
        return;
      }

      final MergeOutcome? outcome = await session.mergeBackup(backup);
      if (!mounted) {
        return;
      }
      setState(
        () => _notice = outcome == null
            ? session.lastError ?? 'The merge could not be saved.'
            : outcome.summary,
      );
    } finally {
      if (mounted) {
        setState(() => _working = false);
      }
    }
  }

  Future<bool?> _confirmMerge(BackupContents backup) {
    return showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Merge this backup in?'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                backup.fileName,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              Text(_count(backup.liveItems, 'entry', 'entries')),
              if (backup.trashedItems > 0)
                Text(
                  '${_count(backup.trashedItems, 'entry', 'entries')} '
                  'in its trash',
                ),
              if (backup.folders > 0)
                Text(_count(backup.folders, 'folder', 'folders')),
              if (backup.dropped > 0) ...<Widget>[
                const SizedBox(height: 8),
                Text(
                  '${backup.dropped} entries in the file could not be read and '
                  'will be left out.',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 12),
              const Text(
                'Nothing in this vault is overwritten. Where the same entry '
                'exists on both sides, the more recent change is kept. Entries '
                'deleted for good on the other device are removed here too.',
              ),
            ],
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Merge'),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------ shared

  /// "1 entry", "3 entries". Worth the four lines: a dialog that says
  /// "1 entries" reads as carelessness in the one screen whose whole job is
  /// to be trusted with the only copy of someone's passwords.
  static String _count(int n, String one, String many) =>
      '$n ${n == 1 ? one : many}';

  Future<String?> _askPassword({
    required String title,
    required String hint,
    String? subject,
  }) => PasswordPrompt.show(
    context,
    title: title,
    explanation: hint,
    confirmLabel: 'Continue',
    subject: subject,
  );
}

class _ExportCard extends StatelessWidget {
  const _ExportCard({
    required this.ownPassword,
    required this.password,
    required this.confirm,
    required this.working,
    required this.hasSaveDialog,
    required this.onOwnPasswordChanged,
    required this.onExport,
  });

  final bool ownPassword;
  final TextEditingController password;
  final TextEditingController confirm;
  final bool working;
  final bool hasSaveDialog;
  final ValueChanged<bool> onOwnPasswordChanged;
  final VoidCallback? onExport;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('Make a backup', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              'Writes an encrypted copy of everything in this vault. The copy '
              'is useless to anyone without its password, so it is safe to '
              'keep on a cloud drive or a USB stick.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'A backup is also how you move this vault to another device: '
              'make one here, then import it there.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              key: const Key('backup-own-password'),
              contentPadding: EdgeInsets.zero,
              value: ownPassword,
              onChanged: working ? null : onOwnPasswordChanged,
              title: const Text('Protect the backup with a separate password'),
              subtitle: const Text(
                'Off: the backup uses this vault’s master password.',
              ),
            ),
            if (ownPassword) ...<Widget>[
              const SizedBox(height: 8),
              TextField(
                key: const Key('backup-password'),
                controller: password,
                obscureText: true,
                enabled: !working,
                decoration: const InputDecoration(
                  labelText: 'Backup password',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('backup-password-confirm'),
                controller: confirm,
                obscureText: true,
                enabled: !working,
                decoration: const InputDecoration(
                  labelText: 'Repeat the backup password',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'There is no way to recover this password. A backup whose '
                'password is lost is gone.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.error,
                ),
              ),
            ],
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.icon(
                key: const Key('backup-export'),
                onPressed: onExport,
                icon: Icon(hasSaveDialog ? Icons.save_alt : Icons.ios_share),
                label: Text(hasSaveDialog ? 'Save a copy' : 'Share a copy'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ImportCard extends StatelessWidget {
  const _ImportCard({required this.working, required this.onImport});

  final bool working;
  final VoidCallback? onImport;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Import a backup from another device',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Reads a backup file and merges it into this vault. Entries are '
              'compared one by one: whichever side changed an entry more '
              'recently wins, and entries you deleted stay deleted.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'You will see what the file contains before anything changes.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                key: const Key('backup-import'),
                onPressed: onImport,
                icon: const Icon(Icons.file_open_outlined),
                label: const Text('Choose a backup file'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TransferAdvice extends StatelessWidget {
  const _TransferAdvice();

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Card(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Keeping two devices in step',
              style: theme.textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Export on one device, import on the other, and repeat in the '
              'other direction. Because the merge keeps the more recent change '
              'to each entry, doing it in both directions leaves both devices '
              'holding the same thing, and doing it twice changes nothing the '
              'second time.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Text(
              'Nothing is uploaded anywhere by this app. A backup file goes '
              'only where you send it.',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
