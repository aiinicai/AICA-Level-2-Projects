import 'package:flutter/material.dart';

import '../../app/build_info.dart';
import '../../app/file_transfer_scope.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/master_password_strength.dart';
import '../../domain/password_generator.dart';
import '../../platform/file_transfer.dart';
import '../transfer/password_prompt.dart';

/// First-run screen: choose a master password and create the vault.
///
/// The warning about losing the password is given prominence and has to be
/// acknowledged. That is not a formality: there is no recovery, and someone
/// who has not understood that can lose everything they put in. Better to be
/// blunt once here than to explain it after the fact.
class CreateVaultScreen extends StatefulWidget {
  const CreateVaultScreen({super.key});

  @override
  State<CreateVaultScreen> createState() => _CreateVaultScreenState();
}

class _CreateVaultScreenState extends State<CreateVaultScreen> {
  final TextEditingController _password = TextEditingController();
  final TextEditingController _confirm = TextEditingController();
  final PasswordGenerator _generator = PasswordGenerator();
  bool _reveal = false;
  bool _understood = false;
  bool _submitting = false;

  @override
  void dispose() {
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  bool get _matches =>
      _password.text.isNotEmpty && _password.text == _confirm.text;

  bool get _longEnough =>
      _password.text.length >= MasterPasswordStrength.minimumLength;

  bool get _canCreate => _matches && _longEnough && _understood && !_submitting;

  Future<void> _create() async {
    setState(() => _submitting = true);
    final VaultSession session = SessionScope.read(context);
    final bool created = await session.createVault(_password.text);
    if (!mounted) {
      return;
    }
    setState(() => _submitting = false);
    if (created) {
      // Clear the fields rather than leaving the password in two controllers
      // for as long as this screen stays in memory.
      _password.clear();
      _confirm.clear();
    }
  }

  /// Rebuilds this device's vault from a backup file.
  ///
  /// The restored vault keeps the backup's own password, which the user
  /// already knows, so there is no new password to invent at the one moment
  /// they are least able to think of a good one. It can be changed afterwards
  /// from Settings.
  Future<void> _restore() async {
    final FileTransfer transfer = FileTransferScope.of(context);
    final VaultSession session = SessionScope.read(context);

    final PickedFile? chosen = await transfer.pick();
    if (chosen == null || !mounted) {
      return;
    }
    final String? password = await PasswordPrompt.show(
      context,
      title: 'Password for this backup',
      explanation:
          'The restored vault will keep this password. You can change it '
          'afterwards from Settings.',
      confirmLabel: 'Restore',
      fieldKey: const Key('restore-password'),
      subject: chosen.name,
    );
    if (password == null || password.isEmpty || !mounted) {
      return;
    }

    setState(() => _submitting = true);
    await session.createFromBackup(file: chosen.bytes, password: password);
    if (mounted) {
      setState(() => _submitting = false);
    }
  }

  void _suggestPassphrase() {
    final String suggestion = _generator.passphrase(
      const PassphraseRecipe(wordCount: 5, includeNumber: true),
    );
    setState(() {
      _password.text = suggestion;
      _confirm.text = suggestion;
      _reveal = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final VaultSession session = SessionScope.of(context);
    final PasswordStrength strength = MasterPasswordStrength.of(_password.text);
    final String? advice = MasterPasswordStrength.adviceFor(_password.text);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  Icon(
                    Icons.lock_outline,
                    size: 56,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Set up $appName',
                    style: theme.textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Choose one master password. It is the only way into your '
                    'vault, and it never leaves this device.',
                    style: theme.textTheme.bodyMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),

                  TextField(
                    controller: _password,
                    obscureText: !_reveal,
                    autofocus: true,
                    decoration: InputDecoration(
                      labelText: 'Master password',
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        tooltip: _reveal ? 'Hide' : 'Show',
                        icon: Icon(
                          _reveal
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                        ),
                        onPressed: () => setState(() => _reveal = !_reveal),
                      ),
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),

                  _StrengthMeter(strength: strength, advice: advice),
                  const SizedBox(height: 12),

                  TextField(
                    controller: _confirm,
                    obscureText: !_reveal,
                    decoration: InputDecoration(
                      labelText: 'Type it again',
                      border: const OutlineInputBorder(),
                      errorText: _confirm.text.isNotEmpty && !_matches
                          ? 'These do not match'
                          : null,
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 8),

                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      icon: const Icon(Icons.casino_outlined),
                      label: const Text('Suggest a passphrase'),
                      onPressed: _suggestPassphrase,
                    ),
                  ),
                  const SizedBox(height: 16),

                  _LossWarning(
                    understood: _understood,
                    onChanged: (bool value) =>
                        setState(() => _understood = value),
                  ),
                  const SizedBox(height: 20),

                  if (session.lastError != null) ...<Widget>[
                    _ErrorBanner(message: session.lastError!),
                    const SizedBox(height: 12),
                  ],

                  FilledButton(
                    onPressed: _canCreate ? _create : null,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: _submitting || session.isBusy
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Create my vault'),
                    ),
                  ),

                  const SizedBox(height: 12),
                  // Restoring belongs here rather than in Settings: a replaced
                  // or wiped device reaches this screen and nowhere else, and
                  // this is the one moment when the vault can be rebuilt from
                  // a backup without any risk of overwriting a live one.
                  TextButton.icon(
                    key: const Key('create-restore'),
                    onPressed: _submitting ? null : _restore,
                    icon: const Icon(Icons.restore),
                    label: const Text('Restore from a backup file instead'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A meter plus one line of advice.
class _StrengthMeter extends StatelessWidget {
  const _StrengthMeter({required this.strength, this.advice});

  final PasswordStrength strength;
  final String? advice;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color colour = switch (strength) {
      PasswordStrength.veryWeak => theme.colorScheme.error,
      PasswordStrength.weak => theme.colorScheme.error,
      PasswordStrength.fair => theme.colorScheme.tertiary,
      PasswordStrength.good => theme.colorScheme.primary,
      PasswordStrength.strong => theme.colorScheme.primary,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: strength.fraction,
                  minHeight: 6,
                  backgroundColor: theme.colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation<Color>(colour),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Text(strength.label, style: theme.textTheme.labelMedium),
          ],
        ),
        if (advice != null) ...<Widget>[
          const SizedBox(height: 6),
          Text(advice!, style: theme.textTheme.bodySmall),
        ],
      ],
    );
  }
}

/// The one thing a new user must understand before going further.
class _LossWarning extends StatelessWidget {
  const _LossWarning({required this.understood, required this.onChanged});

  final bool understood;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Card(
      color: scheme.errorContainer,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'If you forget this password, your vault cannot be opened '
              'again. Not by you, and not by us. There is no reset. Write it '
              'down and keep it somewhere safe.',
              style: TextStyle(color: scheme.onErrorContainer),
            ),
            CheckboxListTile(
              value: understood,
              onChanged: (bool? value) => onChanged(value ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(
                'I understand',
                style: TextStyle(color: scheme.onErrorContainer),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Shows a failure message from the session.
class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.error_outline, color: scheme.onErrorContainer, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: scheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}
