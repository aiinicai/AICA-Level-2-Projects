import 'package:flutter/material.dart';

/// Asks for a password in a dialog, and returns it.
///
/// A [StatefulWidget] rather than a controller created next to a
/// [showDialog] call, which is the obvious way to write this and is wrong:
/// disposing the controller when the dialog's future completes disposes it
/// while the dialog is still animating out, and the field rebuilds one more
/// time against a disposed controller. Owning the controller here ties its
/// life to the dialog's own, animation included.
class PasswordPrompt extends StatefulWidget {
  const PasswordPrompt({
    required this.title,
    required this.explanation,
    required this.confirmLabel,
    required this.fieldKey,
    this.subject,
    super.key,
  });

  /// Dialog heading.
  final String title;

  /// Why the password is being asked for, and what will be done with it.
  final String explanation;

  /// Label on the button that accepts.
  final String confirmLabel;

  /// Key on the password field, so a test can find the right one.
  final Key fieldKey;

  /// A file name or other context shown above the explanation.
  final String? subject;

  /// Shows the prompt. Null when the user cancels.
  static Future<String?> show(
    BuildContext context, {
    required String title,
    required String explanation,
    required String confirmLabel,
    Key fieldKey = const Key('transfer-password'),
    String? subject,
  }) {
    return showDialog<String>(
      context: context,
      builder: (BuildContext context) => PasswordPrompt(
        title: title,
        explanation: explanation,
        confirmLabel: confirmLabel,
        fieldKey: fieldKey,
        subject: subject,
      ),
    );
  }

  @override
  State<PasswordPrompt> createState() => _PasswordPromptState();
}

class _PasswordPromptState extends State<PasswordPrompt> {
  final TextEditingController _field = TextEditingController();

  @override
  void dispose() {
    _field.dispose();
    super.dispose();
  }

  void _accept() => Navigator.of(context).pop(_field.text);

  @override
  Widget build(BuildContext context) {
    final String? subject = widget.subject;
    return AlertDialog(
      title: Text(widget.title),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (subject != null) ...<Widget>[
              Text(
                subject,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
            ],
            Text(widget.explanation),
            const SizedBox(height: 16),
            TextField(
              key: widget.fieldKey,
              controller: _field,
              obscureText: true,
              autofocus: true,
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _accept(),
            ),
          ],
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _accept, child: Text(widget.confirmLabel)),
      ],
    );
  }
}
