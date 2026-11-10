import 'dart:async';

import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/totp.dart';
import '../../domain/vault_data.dart';
import '../../domain/vault_item.dart';

/// Every stored authenticator code on one screen, counting down together.
///
/// These codes are for the user's *other* accounts. They are not protection
/// for this vault: a code checked inside this app could be bypassed by anyone
/// holding the vault file, so the vault's own optional second factor is key
/// material instead. See decision D-010.
class AuthenticatorView extends StatefulWidget {
  const AuthenticatorView({super.key});

  @override
  State<AuthenticatorView> createState() => _AuthenticatorViewState();
}

class _AuthenticatorViewState extends State<AuthenticatorView> {
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
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      return const SizedBox.shrink();
    }
    final ThemeData theme = Theme.of(context);
    final List<VaultItem> items = data.authenticatorItems;

    if (items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              Icon(
                Icons.timer_outlined,
                size: 48,
                color: theme.colorScheme.outline,
              ),
              const SizedBox(height: 12),
              Text(
                'No authenticator codes yet',
                style: theme.textTheme.titleMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'When a website offers two-factor sign-in, paste its setup '
                'key into that login\'s "Authenticator key" field. The '
                'six-digit codes then appear here.',
                style: theme.textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
      itemCount: items.length,
      itemBuilder: (BuildContext context, int index) =>
          _CodeTile(item: items[index]),
    );
  }
}

class _CodeTile extends StatelessWidget {
  const _CodeTile({required this.item});

  final VaultItem item;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    TotpConfig? config;
    try {
      config = TotpConfig.fromBase32(item.totpSecret);
    } on FormatException {
      config = null;
    }

    if (config == null || !config.isUsable) {
      return Card(
        color: theme.colorScheme.errorContainer,
        child: ListTile(
          leading: Icon(
            Icons.error_outline,
            color: theme.colorScheme.onErrorContainer,
          ),
          title: Text(
            item.title,
            style: TextStyle(color: theme.colorScheme.onErrorContainer),
          ),
          subtitle: Text(
            'The saved key is not valid, so no code can be made.',
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
      child: ListTile(
        title: Text(item.title),
        subtitle: Text(item.subtitle),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Text(
                  spaced,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontFamily: 'monospace',
                    letterSpacing: 1.5,
                  ),
                ),
                Text('${remaining}s', style: theme.textTheme.bodySmall),
              ],
            ),
            const SizedBox(width: 8),
            SizedBox(
              height: 28,
              width: 28,
              child: CircularProgressIndicator(
                value: remaining / config.period,
                strokeWidth: 3,
              ),
            ),
          ],
        ),
        onTap: () async {
          final VaultSession session = SessionScope.read(context);
          await session.copyToClipboard(code);
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Code for ${item.title} copied.')),
            );
          }
        },
      ),
    );
  }
}
