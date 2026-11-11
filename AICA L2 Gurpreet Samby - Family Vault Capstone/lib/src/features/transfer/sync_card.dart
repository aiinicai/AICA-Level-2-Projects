// The shared-folder sync card.
//
// What this screen has to get across, because getting it wrong loses data or
// loses trust:
//
//   1. The folder is any folder both devices can see. The app does not know
//      or care which cloud service keeps it in step, and asks for no account.
//   2. Only encrypted files go in it.
//   3. The other device must have been set up from this vault - by one manual
//      import - or it cannot read what is written here. That is a consequence
//      of the vault's sync secret living inside the encrypted payload, and it
//      is better stated plainly than discovered as a mysterious failure.
//   4. Nothing happens on its own. Sync runs when the button is pressed.

import 'package:flutter/material.dart';

import '../../app/file_transfer_scope.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../platform/device_settings.dart';
import '../../platform/file_transfer.dart';
import '../../vault/vault_sync.dart';

/// Setting up and running the shared-folder sync.
class SyncCard extends StatefulWidget {
  const SyncCard({super.key});

  @override
  State<SyncCard> createState() => _SyncCardState();
}

class _SyncCardState extends State<SyncCard> {
  bool _working = false;
  SyncReport? _report;
  String? _notice;

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final DeviceSettings device = session.device;
    final ThemeData theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Keep two devices in step through a shared folder',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Point both devices at the same folder — your Google Drive, '
              'OneDrive or Dropbox folder on this device, a network share, or '
              'even a USB stick. Each device keeps its own copy of the vault '
              'there, encrypted, and a sync merges the others in.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'No account and no sign-in. This app never talks to the cloud '
              'service; whatever already keeps that folder in step does the '
              'moving, and only ever sees encrypted files.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            if (device.syncConfigured)
              _configured(context, session, device)
            else
              _notConfigured(context, session),
            if (_notice != null) ...<Widget>[
              const SizedBox(height: 16),
              Text(_notice!, key: const Key('sync-notice')),
            ],
            if (_report != null && _report!.failures.isNotEmpty) ...<Widget>[
              const SizedBox(height: 12),
              for (final PeerResult failure in _report!.failures)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    failure.message,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.error,
                    ),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _notConfigured(BuildContext context, VaultSession session) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            'Set this up on the device that already holds your passwords '
            'first. Then make a backup there, import it on the other device, '
            'and set the folder up there too. That one manual import is what '
            'lets the two read each other’s files afterwards; without it '
            'they cannot.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            key: const Key('sync-choose-folder'),
            onPressed: _working ? null : () => _chooseFolder(session),
            icon: const Icon(Icons.folder_open_outlined),
            label: const Text('Choose a shared folder'),
          ),
        ),
      ],
    );
  }

  Widget _configured(
    BuildContext context,
    VaultSession session,
    DeviceSettings device,
  ) {
    final ThemeData theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _Line(label: 'Folder', value: device.syncFolder!),
        _Line(label: 'This device', value: device.deviceName!),
        _Line(
          label: 'Last synced',
          value: device.lastSyncedAt == null
              ? 'never'
              : _describe(device.lastSyncedAt!),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 8,
          children: <Widget>[
            FilledButton.icon(
              key: const Key('sync-now'),
              onPressed: _working ? null : () => _syncNow(session),
              icon: _working
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.sync),
              label: const Text('Sync now'),
            ),
            OutlinedButton(
              key: const Key('sync-change-folder'),
              onPressed: _working ? null : () => _chooseFolder(session),
              child: const Text('Change folder'),
            ),
            TextButton(
              key: const Key('sync-stop'),
              onPressed: _working ? null : () => _stop(session),
              child: const Text('Stop sharing on this device'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Syncing happens when you press the button. Nothing runs in the '
          'background.',
          style: theme.textTheme.bodySmall,
        ),
      ],
    );
  }

  Future<void> _chooseFolder(VaultSession session) async {
    final FileTransfer transfer = FileTransferScope.of(context);
    final String? folder = await transfer.pickFolder();
    if (folder == null || !mounted) {
      return;
    }
    final String? name = await showDialog<String>(
      context: context,
      builder: (BuildContext context) =>
          _DeviceNameDialog(initial: session.device.deviceName),
    );
    if (name == null || name.trim().isEmpty || !mounted) {
      return;
    }

    setState(() {
      _working = true;
      _notice = null;
    });
    final bool ok = await session.enableSync(folder: folder, deviceName: name);
    if (!mounted) {
      return;
    }
    setState(() {
      _working = false;
      _notice = ok
          ? 'Sharing set up. Press Sync now, then set the same folder up on '
                'your other device.'
          : session.lastError ?? 'Could not set that up.';
    });
    if (ok) {
      await _syncNow(session);
    }
  }

  Future<void> _syncNow(VaultSession session) async {
    setState(() {
      _working = true;
      _notice = null;
    });
    final SyncReport? report = await session.syncNow();
    if (!mounted) {
      return;
    }
    setState(() {
      _working = false;
      _report = report;
      _notice = report?.summary ?? session.lastError ?? 'Sync failed.';
    });
  }

  Future<void> _stop(VaultSession session) async {
    final bool? go = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Stop sharing on this device?'),
        content: const Text(
          'This device will stop reading and writing the shared folder. Your '
          'vault here is untouched, and the files already in the folder are '
          'left alone — your other device may still be using them.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Stop sharing'),
          ),
        ],
      ),
    );
    if (go != true || !mounted) {
      return;
    }
    await session.disableSync();
    if (mounted) {
      setState(() {
        _report = null;
        _notice = 'This device is no longer sharing through a folder.';
      });
    }
  }

  static String _describe(DateTime when) {
    final Duration ago = DateTime.now().difference(when);
    if (ago.inMinutes < 1) {
      return 'just now';
    }
    if (ago.inHours < 1) {
      final int m = ago.inMinutes;
      return '$m ${m == 1 ? 'minute' : 'minutes'} ago';
    }
    if (ago.inDays < 1) {
      final int h = ago.inHours;
      return '$h ${h == 1 ? 'hour' : 'hours'} ago';
    }
    final int d = ago.inDays;
    return '$d ${d == 1 ? 'day' : 'days'} ago';
  }
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 104,
            child: Text(label, style: theme.textTheme.bodySmall),
          ),
          Expanded(child: Text(value, style: theme.textTheme.bodyMedium)),
        ],
      ),
    );
  }
}

/// Asks what to call this device.
class _DeviceNameDialog extends StatefulWidget {
  const _DeviceNameDialog({this.initial});

  final String? initial;

  @override
  State<_DeviceNameDialog> createState() => _DeviceNameDialogState();
}

class _DeviceNameDialogState extends State<_DeviceNameDialog> {
  late final TextEditingController _field = TextEditingController(
    text: widget.initial ?? '',
  );

  @override
  void dispose() {
    _field.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('What should this device be called?'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            'It becomes the name of this device’s file in the shared '
            'folder, so you can tell whose copy is whose. Something like '
            '"phone" or "laptop".',
          ),
          const SizedBox(height: 16),
          TextField(
            key: const Key('sync-device-name'),
            controller: _field,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Device name',
              border: OutlineInputBorder(),
            ),
            onSubmitted: (String value) => Navigator.of(context).pop(value),
          ),
        ],
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(_field.text),
          child: const Text('Use this name'),
        ),
      ],
    );
  }
}
