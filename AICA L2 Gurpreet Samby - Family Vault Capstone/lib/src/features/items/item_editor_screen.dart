import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/base32.dart';
import '../../domain/folder.dart';
import '../../domain/password_generator.dart';
import '../../domain/totp.dart';
import '../../domain/vault_data.dart';
import '../../domain/vault_item.dart';

/// Adds or edits an item.
///
/// One form serves all four kinds of item, because each [VaultItemType]
/// carries its own field list with labels and input kinds. Adding a fifth kind
/// needs no change here.
class ItemEditorScreen extends StatefulWidget {
  const ItemEditorScreen({
    super.key,
    this.itemId,
    this.initialType,
    this.initialFolderId,
  });

  /// The item being edited, or null when adding a new one.
  final String? itemId;

  /// Which kind to create. Ignored when editing.
  final VaultItemType? initialType;

  /// Folder to put a new item in.
  final String? initialFolderId;

  @override
  State<ItemEditorScreen> createState() => _ItemEditorScreenState();
}

class _ItemEditorScreenState extends State<ItemEditorScreen> {
  final GlobalKey<FormState> _form = GlobalKey<FormState>();
  final TextEditingController _title = TextEditingController();
  final TextEditingController _notes = TextEditingController();
  final Map<String, TextEditingController> _fields =
      <String, TextEditingController>{};
  final Set<String> _revealed = <String>{};
  final PasswordGenerator _generator = PasswordGenerator();

  VaultItemType _type = VaultItemType.login;
  String? _folderId;
  bool _saving = false;
  bool _loaded = false;

  @override
  void dispose() {
    _title.dispose();
    _notes.dispose();
    for (final TextEditingController controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  void _loadOnce(VaultData data) {
    if (_loaded) {
      return;
    }
    _loaded = true;
    final VaultItem? existing = widget.itemId == null
        ? null
        : data.itemById(widget.itemId!);
    if (existing != null) {
      _type = existing.type;
      _title.text = existing.title;
      _notes.text = existing.notes;
      _folderId = existing.folderId;
      for (final ItemFieldSpec spec in _type.fields) {
        _fields[spec.key] = TextEditingController(
          text: existing.field(spec.key),
        );
      }
    } else {
      _type = widget.initialType ?? VaultItemType.login;
      _folderId = widget.initialFolderId;
      for (final ItemFieldSpec spec in _type.fields) {
        _fields[spec.key] = TextEditingController();
      }
    }
  }

  void _changeType(VaultItemType next) {
    setState(() {
      _type = next;
      for (final ItemFieldSpec spec in next.fields) {
        _fields.putIfAbsent(spec.key, TextEditingController.new);
      }
    });
  }

  void _generatePassword(String key) {
    final String generated = _generator.password(const PasswordRecipe());
    setState(() {
      _fields[key]?.text = generated;
      _revealed.add(key);
    });
  }

  /// Accepts either a bare base32 key or a whole otpauth link.
  void _normaliseAuthenticatorKey(String key) {
    final String raw = _fields[key]?.text.trim() ?? '';
    if (!raw.toLowerCase().startsWith('otpauth://')) {
      return;
    }
    try {
      final TotpConfig config = TotpConfig.fromUri(raw);
      setState(() {
        _fields[key]?.text = Base32.encode(config.secret);
      });
    } on FormatException {
      // Left as typed; validation reports it when saving.
    }
  }

  Future<void> _save(VaultData data) async {
    if (!(_form.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _saving = true);

    final Map<String, String> values = <String, String>{};
    for (final ItemFieldSpec spec in _type.fields) {
      final String value = _fields[spec.key]?.text.trim() ?? '';
      if (value.isNotEmpty) {
        values[spec.key] = value;
      }
    }

    final VaultSession session = SessionScope.read(context);
    final NavigatorState navigator = Navigator.of(context);
    final VaultItem? existing = widget.itemId == null
        ? null
        : data.itemById(widget.itemId!);

    final VaultItem item = existing == null
        ? VaultItem.create(
            type: _type,
            title: _title.text.trim(),
            fields: values,
            folderId: _folderId,
            notes: _notes.text.trim(),
          )
        : existing.copyWith(
            title: _title.text.trim(),
            fields: values,
            notes: _notes.text.trim(),
            folderId: _folderId,
            clearFolder: _folderId == null,
          );

    final bool saved = await session.saveItem(item);
    if (!mounted) {
      return;
    }
    setState(() => _saving = false);
    if (saved) {
      navigator.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      return const Scaffold(body: SizedBox.shrink());
    }
    _loadOnce(data);

    final bool isNew = widget.itemId == null;

    return Scaffold(
      appBar: AppBar(
        title: Text(isNew ? 'New ${_type.label}' : 'Edit'),
        actions: <Widget>[
          TextButton(
            onPressed: _saving ? null : () => _save(data),
            child: Text(_saving ? 'Saving…' : 'Save'),
          ),
        ],
      ),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: <Widget>[
            if (isNew) ...<Widget>[
              Text('Kind', style: Theme.of(context).textTheme.labelMedium),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: <Widget>[
                  for (final VaultItemType type in VaultItemType.values)
                    ChoiceChip(
                      label: Text(type.label),
                      selected: _type == type,
                      onSelected: (_) => _changeType(type),
                    ),
                ],
              ),
              const SizedBox(height: 20),
            ],

            TextFormField(
              controller: _title,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Name',
                helperText: 'What you will recognise this by',
                border: OutlineInputBorder(),
              ),
              validator: (String? value) =>
                  (value == null || value.trim().isEmpty)
                  ? 'Give this entry a name'
                  : null,
            ),
            const SizedBox(height: 16),

            for (final ItemFieldSpec spec in _type.fields) ...<Widget>[
              _buildField(spec),
              const SizedBox(height: 16),
            ],

            DropdownButtonFormField<String?>(
              initialValue: _folderId,
              decoration: const InputDecoration(
                labelText: 'Folder',
                border: OutlineInputBorder(),
              ),
              items: <DropdownMenuItem<String?>>[
                const DropdownMenuItem<String?>(child: Text('No folder')),
                for (final Folder folder in data.folders)
                  DropdownMenuItem<String?>(
                    value: folder.id,
                    child: Text(folder.name),
                  ),
              ],
              onChanged: (String? value) => setState(() => _folderId = value),
            ),
            const SizedBox(height: 16),

            TextFormField(
              controller: _notes,
              minLines: 3,
              maxLines: 8,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Notes',
                alignLabelWithHint: true,
                border: OutlineInputBorder(),
              ),
            ),

            if (session.lastError != null) ...<Widget>[
              const SizedBox(height: 16),
              Text(
                session.lastError!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildField(ItemFieldSpec spec) {
    final TextEditingController controller = _fields.putIfAbsent(
      spec.key,
      TextEditingController.new,
    );
    final bool hidden = spec.isSecret && !_revealed.contains(spec.key);

    return TextFormField(
      controller: controller,
      obscureText: hidden,
      minLines: spec.input == FieldInput.multiline ? 4 : 1,
      maxLines: spec.input == FieldInput.multiline ? 12 : 1,
      keyboardType: switch (spec.input) {
        FieldInput.email => TextInputType.emailAddress,
        FieldInput.url => TextInputType.url,
        FieldInput.phone => TextInputType.phone,
        FieldInput.number => TextInputType.number,
        FieldInput.multiline => TextInputType.multiline,
        _ => TextInputType.text,
      },
      decoration: InputDecoration(
        labelText: spec.label,
        helperText: spec.hint,
        helperMaxLines: 2,
        alignLabelWithHint: spec.input == FieldInput.multiline,
        border: const OutlineInputBorder(),
        suffixIcon: _suffixFor(spec),
      ),
      validator: spec.input == FieldInput.totpSecret
          ? (String? value) {
              final String key = value?.trim() ?? '';
              if (key.isEmpty || Base32.isValid(key)) {
                return null;
              }
              return 'This does not look like an authenticator key';
            }
          : null,
      onChanged: spec.input == FieldInput.totpSecret
          ? (_) => _normaliseAuthenticatorKey(spec.key)
          : null,
    );
  }

  Widget? _suffixFor(ItemFieldSpec spec) {
    final List<Widget> buttons = <Widget>[];
    if (spec.isSecret) {
      buttons.add(
        IconButton(
          tooltip: _revealed.contains(spec.key) ? 'Hide' : 'Show',
          icon: Icon(
            _revealed.contains(spec.key)
                ? Icons.visibility_off_outlined
                : Icons.visibility_outlined,
          ),
          onPressed: () => setState(() {
            if (!_revealed.remove(spec.key)) {
              _revealed.add(spec.key);
            }
          }),
        ),
      );
    }
    if (spec.key == ItemField.password) {
      buttons.add(
        IconButton(
          tooltip: 'Generate a strong password',
          icon: const Icon(Icons.casino_outlined),
          onPressed: () => _generatePassword(spec.key),
        ),
      );
    }
    if (buttons.isEmpty) {
      return null;
    }
    return Row(mainAxisSize: MainAxisSize.min, children: buttons);
  }
}
