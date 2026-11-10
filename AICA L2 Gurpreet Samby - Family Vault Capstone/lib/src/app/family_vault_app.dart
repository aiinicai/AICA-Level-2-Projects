import 'package:flutter/material.dart';

import '../crypto/crypto_service.dart';
import '../crypto/sodium_crypto_service.dart';
import '../features/home/home_shell.dart';
import '../features/onboarding/create_vault_screen.dart';
import '../features/onboarding/unlock_screen.dart';
import '../platform/device_settings.dart';
import '../platform/file_transfer.dart';
import '../vault/vault_repository.dart';
import 'build_info.dart';
import 'file_transfer_scope.dart';
import 'session_scope.dart';
import 'theme.dart';
import 'vault_session.dart';

/// Root widget.
///
/// Starting up means two things that can fail: initialising libsodium and
/// finding somewhere to keep the vault. Both happen here, once, and a failure
/// is reported plainly rather than leaving a blank screen.
class FamilyVaultApp extends StatefulWidget {
  const FamilyVaultApp({
    super.key,
    this.sessionOverride,
    this.fileTransferOverride,
  });

  /// Replaces the real session. For tests and for the web demonstration, so
  /// neither has to initialise libsodium or touch a real vault file.
  final VaultSession? sessionOverride;

  /// Replaces the real file picker, so a test can answer a save or open
  /// dialog that it otherwise could not.
  final FileTransfer? fileTransferOverride;

  @override
  State<FamilyVaultApp> createState() => _FamilyVaultAppState();
}

class _FamilyVaultAppState extends State<FamilyVaultApp> {
  VaultSession? _session;
  String? _startupError;

  @override
  void initState() {
    super.initState();
    final VaultSession? provided = widget.sessionOverride;
    if (provided != null) {
      _session = provided;
      provided.initialise();
      provided.loadDeviceSettings();
    } else {
      _start();
    }
  }

  Future<void> _start() async {
    try {
      final CryptoService crypto = await SodiumCryptoService.initialise();
      final VaultRepository repository =
          await FileVaultRepository.forPlatform();
      final DeviceSettingsStore deviceSettings =
          await FileDeviceSettingsStore.forPlatform();
      final VaultSession session = VaultSession(
        crypto: crypto,
        repository: repository,
        deviceSettings: deviceSettings,
      );
      await session.initialise();
      await session.loadDeviceSettings();
      if (mounted) {
        setState(() => _session = session);
      }
    } on Object catch (error) {
      // The type only: a startup failure must not put anything from the vault
      // or the environment on screen.
      if (mounted) {
        setState(() => _startupError = error.runtimeType.toString());
      }
    }
  }

  @override
  void dispose() {
    if (widget.sessionOverride == null) {
      _session?.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession? session = _session;

    final Widget app = MaterialApp(
      title: appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      home: _buildHome(),
    );

    // SessionScope goes ABOVE MaterialApp, not inside it.
    //
    // MaterialApp builds the Navigator, so anything passed as `home` sits
    // below that Navigator — and a route pushed onto it is a sibling of
    // `home`, not a descendant. With the scope inside, every pushed screen
    // (the item editor, the generator) could not find the session and threw
    // while building. Above the Navigator, every route reaches it.
    if (session == null) {
      return app;
    }
    return FileTransferScope(
      transfer: widget.fileTransferOverride ?? const PlatformFileTransfer(),
      child: SessionScope(session: session, child: app),
    );
  }

  Widget _buildHome() {
    final String? error = _startupError;
    if (error != null) {
      return _StartupFailure(detail: error);
    }
    if (_session == null) {
      return const _Starting();
    }
    return const _SessionRouter();
  }
}

/// Chooses a screen from the session's state.
class _SessionRouter extends StatelessWidget {
  const _SessionRouter();

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    return switch (session.status) {
      VaultStatus.starting => const _Starting(),
      VaultStatus.absent => const CreateVaultScreen(),
      VaultStatus.locked => const UnlockScreen(),
      VaultStatus.unlocked => const HomeShell(),
    };
  }
}

class _Starting extends StatelessWidget {
  const _Starting();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}

class _StartupFailure extends StatelessWidget {
  const _StartupFailure({required this.detail});

  final String detail;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Icon(
                  Icons.error_outline,
                  size: 48,
                  color: theme.colorScheme.error,
                ),
                const SizedBox(height: 16),
                Text(
                  '$appName could not start',
                  style: theme.textTheme.titleLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'Your vault has not been touched and is still safe. Please '
                  'close the app and open it again. If this keeps happening, '
                  'report it with the detail below.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                SelectableText(detail, style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
