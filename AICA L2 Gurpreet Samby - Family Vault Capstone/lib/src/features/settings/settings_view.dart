import 'package:flutter/material.dart';

import '../../app/build_info.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/master_password_strength.dart';
import '../../domain/vault_settings.dart';

/// Security settings, master-password change and vault deletion.
class SettingsView extends StatelessWidget {
  const SettingsView({super.key});

  String _describeMinutes(int minutes) => switch (minutes) {
    0 => 'Only when I lock it',
    1 => 'After 1 minute',
    60 => 'After 1 hour',
    _ => 'After $minutes minutes',
  };

  String _describeSeconds(int seconds) =>
      seconds == 0 ? 'Never clear it' : 'After $seconds seconds';

  Future<void> _changePassword(BuildContext context) async {
    final TextEditingController password = TextEditingController();
    final TextEditingController confirm = TextEditingController();
    final bool? proceed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) =>
          _ChangePasswordDialog(password: password, confirm: confirm),
    );
    final String value = password.text;
    password.dispose();
    confirm.dispose();
    if (proceed != true || !context.mounted) {
      return;
    }
    final VaultSession session = SessionScope.read(context);
    final bool changed = await session.changeMasterPassword(value);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            changed
                ? 'Master password changed. Use the new one from now on.'
                : session.lastError ?? 'Could not change the password.',
          ),
        ),
      );
    }
  }

  Future<void> _deleteVault(BuildContext context) async {
    final bool? first = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Delete this vault?'),
        content: const Text(
          'Everything in it is deleted from this device. There is no undo, '
          'and no copy unless you exported one yourself.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Continue'),
          ),
        ],
      ),
    );
    if (first != true || !context.mounted) {
      return;
    }

    // A second, differently-worded confirmation. One tap away from losing
    // every password you own is not enough distance.
    final TextEditingController typed = TextEditingController();
    final bool? second = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('Type DELETE to confirm'),
        content: TextField(
          controller: typed,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Type DELETE',
            border: OutlineInputBorder(),
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.of(context).pop(typed.text.trim() == 'DELETE'),
            child: const Text('Delete everything'),
          ),
        ],
      ),
    );
    typed.dispose();
    if (second == true && context.mounted) {
      await SessionScope.read(context).deleteVault();
    }
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultSettings settings = session.settings;
    final ThemeData theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
      children: <Widget>[
        Text('Locking', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: <Widget>[
              ListTile(
                title: const Text('Lock after inactivity'),
                subtitle: Text(_describeMinutes(settings.autoLockMinutes)),
                trailing: DropdownButton<int>(
                  value: settings.autoLockMinutes,
                  underline: const SizedBox.shrink(),
                  items: <DropdownMenuItem<int>>[
                    for (final int choice in VaultSettings.autoLockChoices)
                      DropdownMenuItem<int>(
                        value: choice,
                        child: Text(choice == 0 ? 'Never' : '$choice min'),
                      ),
                  ],
                  onChanged: (int? value) {
                    if (value != null) {
                      session.updateSettings(
                        settings.copyWith(autoLockMinutes: value),
                      );
                    }
                  },
                ),
              ),
              const Divider(height: 1),
              SwitchListTile(
                title: const Text('Lock when the app is hidden'),
                subtitle: const Text(
                  'Locks as soon as you switch to something else',
                ),
                value: settings.lockWhenHidden,
                onChanged: (bool value) => session.updateSettings(
                  settings.copyWith(lockWhenHidden: value),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        Text('Clipboard', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            title: const Text('Clear copied passwords'),
            subtitle: Text(_describeSeconds(settings.clipboardClearSeconds)),
            trailing: DropdownButton<int>(
              value: settings.clipboardClearSeconds,
              underline: const SizedBox.shrink(),
              items: <DropdownMenuItem<int>>[
                for (final int choice in VaultSettings.clipboardChoices)
                  DropdownMenuItem<int>(
                    value: choice,
                    child: Text(choice == 0 ? 'Never' : '${choice}s'),
                  ),
              ],
              onChanged: (int? value) {
                if (value != null) {
                  session.updateSettings(
                    settings.copyWith(clipboardClearSeconds: value),
                  );
                }
              },
            ),
          ),
        ),
        const SizedBox(height: 20),

        Text('Master password', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            leading: const Icon(Icons.key_outlined),
            title: const Text('Change master password'),
            subtitle: const Text('Re-encrypts the whole vault with a new key'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _changePassword(context),
          ),
        ),
        const SizedBox(height: 20),

        Text('This vault', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: <Widget>[
              FutureBuilder<String>(
                future: session.vaultLocation(),
                builder:
                    (BuildContext context, AsyncSnapshot<String> snapshot) =>
                        ListTile(
                          leading: const Icon(Icons.folder_outlined),
                          title: const Text('Where your vault is kept'),
                          subtitle: Text(snapshot.data ?? 'Checking…'),
                        ),
              ),
              const Divider(height: 1),
              ListTile(
                leading: Icon(
                  Icons.delete_forever_outlined,
                  color: theme.colorScheme.error,
                ),
                title: Text(
                  'Delete this vault',
                  style: TextStyle(color: theme.colorScheme.error),
                ),
                subtitle: const Text('Permanent. There is no undo.'),
                onTap: () => _deleteVault(context),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('$appName $appVersion', style: theme.textTheme.titleSmall),
                const SizedBox(height: 8),
                Text(
                  'Your vault is encrypted on this device with a key made '
                  'from your master password. It is never sent anywhere, and '
                  'no one else can read it.',
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  'Not yet built: syncing between devices, autofill on '
                  'Android, importing from another password manager, and a '
                  'printable recovery sheet.',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// Asks for a new master password, with the same strength guidance as setup.
class _ChangePasswordDialog extends StatefulWidget {
  const _ChangePasswordDialog({required this.password, required this.confirm});

  final TextEditingController password;
  final TextEditingController confirm;

  @override
  State<_ChangePasswordDialog> createState() => _ChangePasswordDialogState();
}

class _ChangePasswordDialogState extends State<_ChangePasswordDialog> {
  @override
  Widget build(BuildContext context) {
    final String value = widget.password.text;
    final bool matches = value.isNotEmpty && value == widget.confirm.text;
    final bool longEnough =
        value.length >= MasterPasswordStrength.minimumLength;
    final String? advice = MasterPasswordStrength.adviceFor(value);

    return AlertDialog(
      title: const Text('Change master password'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text(
              'The vault is re-encrypted with the new password. The old one '
              'stops working immediately, so write the new one down first.',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: widget.password,
              obscureText: true,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: 'New master password',
                border: OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: widget.confirm,
              obscureText: true,
              decoration: InputDecoration(
                labelText: 'Type it again',
                border: const OutlineInputBorder(),
                errorText: widget.confirm.text.isNotEmpty && !matches
                    ? 'These do not match'
                    : null,
              ),
              onChanged: (_) => setState(() {}),
            ),
            if (advice != null) ...<Widget>[
              const SizedBox(height: 12),
              Text(advice, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: matches && longEnough
              ? () => Navigator.of(context).pop(true)
              : null,
          child: const Text('Change it'),
        ),
      ],
    );
  }
}
