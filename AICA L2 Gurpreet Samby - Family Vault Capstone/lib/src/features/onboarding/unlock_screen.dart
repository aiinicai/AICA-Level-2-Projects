import 'package:flutter/material.dart';

import '../../app/build_info.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';

/// Asks for the master password to open an existing vault.
class UnlockScreen extends StatefulWidget {
  const UnlockScreen({super.key});

  @override
  State<UnlockScreen> createState() => _UnlockScreenState();
}

class _UnlockScreenState extends State<UnlockScreen> {
  final TextEditingController _password = TextEditingController();
  bool _reveal = false;
  bool _submitting = false;

  @override
  void dispose() {
    _password.dispose();
    super.dispose();
  }

  Future<void> _unlock() async {
    if (_password.text.isEmpty || _submitting) {
      return;
    }
    setState(() => _submitting = true);
    final VaultSession session = SessionScope.read(context);
    final bool opened = await session.unlock(_password.text);
    if (!mounted) {
      return;
    }
    setState(() => _submitting = false);
    if (opened) {
      _password.clear();
    } else {
      // Keep the field focused and select what is there, so a correction does
      // not need a tap first.
      _password.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _password.text.length,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final VaultSession session = SessionScope.of(context);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
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
                    appName,
                    style: theme.textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Enter your master password',
                    style: theme.textTheme.bodyMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 28),

                  TextField(
                    controller: _password,
                    obscureText: !_reveal,
                    autofocus: true,
                    onSubmitted: (_) => _unlock(),
                    decoration: InputDecoration(
                      labelText: 'Master password',
                      border: const OutlineInputBorder(),
                      errorText: session.lastError,
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
                    onChanged: (_) {
                      if (session.lastError != null) {
                        session.clearError();
                      }
                    },
                  ),
                  const SizedBox(height: 20),

                  FilledButton(
                    onPressed: _submitting || session.isBusy ? null : _unlock,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: _submitting || session.isBusy
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Unlock'),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Your vault is on this device only. Nothing is sent '
                    'anywhere, and no one else can open it.',
                    style: theme.textTheme.bodySmall,
                    textAlign: TextAlign.center,
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
