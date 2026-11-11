import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/password_generator.dart';

/// Makes a password, a passphrase or a username.
class GeneratorScreen extends StatefulWidget {
  const GeneratorScreen({super.key});

  @override
  State<GeneratorScreen> createState() => _GeneratorScreenState();
}

class _GeneratorScreenState extends State<GeneratorScreen> {
  final PasswordGenerator _generator = PasswordGenerator();

  int _mode = 0;
  PasswordRecipe _password = const PasswordRecipe();
  PassphraseRecipe _passphrase = const PassphraseRecipe();
  String _value = '';
  String? _problem;

  @override
  void initState() {
    super.initState();
    _regenerate();
  }

  void _regenerate() {
    setState(() {
      _problem = null;
      try {
        _value = switch (_mode) {
          0 => _generator.password(_password),
          1 => _generator.passphrase(_passphrase),
          _ => _generator.username(),
        };
      } on ArgumentError catch (error) {
        _value = '';
        _problem = error.message.toString();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Generator')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          SegmentedButton<int>(
            segments: const <ButtonSegment<int>>[
              ButtonSegment<int>(value: 0, label: Text('Password')),
              ButtonSegment<int>(value: 1, label: Text('Passphrase')),
              ButtonSegment<int>(value: 2, label: Text('Username')),
            ],
            selected: <int>{_mode},
            onSelectionChanged: (Set<int> selection) {
              setState(() => _mode = selection.first);
              _regenerate();
            },
          ),
          const SizedBox(height: 20),

          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: <Widget>[
                  SelectableText(
                    _problem ?? _value,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontFamily: 'monospace',
                      color: _problem == null ? null : theme.colorScheme.error,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: <Widget>[
                      OutlinedButton.icon(
                        onPressed: _regenerate,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Again'),
                      ),
                      const SizedBox(width: 12),
                      FilledButton.icon(
                        onPressed: _value.isEmpty
                            ? null
                            : () async {
                                final VaultSession session = SessionScope.read(
                                  context,
                                );
                                await session.copyToClipboard(_value);
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Copied.')),
                                  );
                                }
                              },
                        icon: const Icon(Icons.copy_outlined),
                        label: const Text('Copy'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          if (_mode == 0) ..._passwordOptions(theme),
          if (_mode == 1) ..._passphraseOptions(theme),
          if (_mode == 2)
            Text(
              'A username made of two unrelated words and a number. Useful '
              'where a site wants a username you will not reuse elsewhere.',
              style: theme.textTheme.bodyMedium,
            ),
        ],
      ),
    );
  }

  List<Widget> _passwordOptions(ThemeData theme) => <Widget>[
    Text('Length: ${_password.length}', style: theme.textTheme.labelLarge),
    Slider(
      value: _password.length.toDouble(),
      min: PasswordRecipe.minLength.toDouble(),
      max: 64,
      divisions: 64 - PasswordRecipe.minLength,
      label: '${_password.length}',
      onChanged: (double value) {
        setState(() => _password = _password.copyWith(length: value.round()));
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Capital letters'),
      value: _password.uppercase,
      onChanged: (bool value) {
        setState(() => _password = _password.copyWith(uppercase: value));
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Small letters'),
      value: _password.lowercase,
      onChanged: (bool value) {
        setState(() => _password = _password.copyWith(lowercase: value));
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Numbers'),
      value: _password.digits,
      onChanged: (bool value) {
        setState(() => _password = _password.copyWith(digits: value));
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Symbols'),
      value: _password.symbols,
      onChanged: (bool value) {
        setState(() => _password = _password.copyWith(symbols: value));
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Avoid look-alike characters'),
      subtitle: const Text('Leaves out l, I, 1, O, 0 and o'),
      value: _password.avoidAmbiguous,
      onChanged: (bool value) {
        setState(() => _password = _password.copyWith(avoidAmbiguous: value));
        _regenerate();
      },
    ),
  ];

  List<Widget> _passphraseOptions(ThemeData theme) => <Widget>[
    Text('Words: ${_passphrase.wordCount}', style: theme.textTheme.labelLarge),
    Slider(
      value: _passphrase.wordCount.toDouble(),
      min: PassphraseRecipe.minWords.toDouble(),
      max: PassphraseRecipe.maxWords.toDouble(),
      divisions: PassphraseRecipe.maxWords - PassphraseRecipe.minWords,
      label: '${_passphrase.wordCount}',
      onChanged: (double value) {
        setState(
          () => _passphrase = _passphrase.copyWith(wordCount: value.round()),
        );
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Capitalise each word'),
      value: _passphrase.capitalise,
      onChanged: (bool value) {
        setState(() => _passphrase = _passphrase.copyWith(capitalise: value));
        _regenerate();
      },
    ),
    SwitchListTile(
      title: const Text('Add a number'),
      subtitle: const Text('Some sites insist on one'),
      value: _passphrase.includeNumber,
      onChanged: (bool value) {
        setState(
          () => _passphrase = _passphrase.copyWith(includeNumber: value),
        );
        _regenerate();
      },
    ),
    const SizedBox(height: 8),
    Text(
      'A passphrase of unrelated words is easier to remember than a jumble '
      'and, if it is long enough, harder to guess. Good for a master '
      'password.',
      style: theme.textTheme.bodySmall,
    ),
  ];
}
