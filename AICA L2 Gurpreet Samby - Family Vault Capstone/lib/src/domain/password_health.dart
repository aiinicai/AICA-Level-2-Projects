import 'package:meta/meta.dart';

import 'vault_data.dart';
import 'vault_item.dart';

/// How serious a password problem is.
enum HealthSeverity {
  /// Worth fixing, but not urgent.
  low('Worth a look'),

  /// Should be fixed soon.
  medium('Should be changed'),

  /// Fix this first.
  high('Change this now');

  const HealthSeverity(this.label);

  /// Plain-language label.
  final String label;
}

/// A kind of password problem.
enum HealthIssueKind {
  /// Short, or drawn from too few kinds of character.
  weak('Weak password', HealthSeverity.high),

  /// The same password is used on more than one entry.
  reused('Reused password', HealthSeverity.high),

  /// Not changed in a long time.
  old('Old password', HealthSeverity.low),

  /// No password at all on an entry that should have one.
  missing('No password saved', HealthSeverity.medium),

  /// Two-factor authentication could be switched on for this account.
  noTwoFactor('Two-factor available', HealthSeverity.low);

  const HealthIssueKind(this.label, this.severity);

  /// Plain-language label.
  final String label;

  /// How serious this kind of problem is.
  final HealthSeverity severity;
}

/// One problem found with one item.
@immutable
final class HealthIssue {
  const HealthIssue({
    required this.item,
    required this.kind,
    required this.advice,
  });

  /// The item the problem is on.
  final VaultItem item;

  /// What the problem is.
  final HealthIssueKind kind;

  /// What to do about it, in plain language.
  final String advice;

  /// How serious it is.
  HealthSeverity get severity => kind.severity;
}

/// The result of checking a vault's passwords.
@immutable
final class HealthReport {
  const HealthReport({
    required this.issues,
    required this.passwordsChecked,
    required this.generatedAt,
  });

  /// Everything found, worst first.
  final List<HealthIssue> issues;

  /// How many passwords were examined.
  final int passwordsChecked;

  /// When the check ran.
  final DateTime generatedAt;

  /// Issues of one kind.
  List<HealthIssue> ofKind(HealthIssueKind kind) =>
      issues.where((HealthIssue i) => i.kind == kind).toList();

  /// How many problems of one kind were found.
  int countOf(HealthIssueKind kind) => ofKind(kind).length;

  /// True when nothing needs attention.
  bool get isClean => issues.isEmpty;

  /// A score out of 100, for a single glance.
  ///
  /// Deliberately blunt: high-severity problems cost much more than low ones,
  /// so one reused password cannot be hidden behind a long list of clean
  /// entries. An empty vault scores 100 because there is nothing wrong with it.
  int get score {
    if (passwordsChecked == 0) {
      return 100;
    }
    int penalty = 0;
    for (final HealthIssue issue in issues) {
      penalty += switch (issue.severity) {
        HealthSeverity.high => 12,
        HealthSeverity.medium => 5,
        HealthSeverity.low => 2,
      };
    }
    final int raw = 100 - penalty;
    return raw < 0 ? 0 : raw;
  }

  /// One sentence summarising the state of things.
  String get summary {
    if (passwordsChecked == 0) {
      return 'No passwords saved yet.';
    }
    if (isClean) {
      return passwordsChecked == 1
          ? 'Your one saved password looks good.'
          : 'All $passwordsChecked saved passwords look good.';
    }
    final int high = issues
        .where((HealthIssue i) => i.severity == HealthSeverity.high)
        .length;
    if (high > 0) {
      return high == 1
          ? '1 password needs changing now.'
          : '$high passwords need changing now.';
    }
    return issues.length == 1
        ? '1 password is worth a look.'
        : '${issues.length} passwords are worth a look.';
  }
}

/// Checks the passwords in a vault.
///
/// Runs entirely on the decrypted vault in memory. Nothing is sent anywhere,
/// and no password is hashed and submitted to any service: the optional
/// breach check that does talk to the network is a separate, off-by-default
/// Phase 2 feature.
abstract final class PasswordHealth {
  /// A password shorter than this counts as weak however varied it is.
  static const int minimumReasonableLength = 12;

  /// Age at which a password is flagged as old.
  static const Duration oldAfter = Duration(days: 365);

  /// Checks [data] and returns what it found, worst first.
  static HealthReport check(VaultData data, {DateTime? now}) {
    final DateTime at = now ?? DateTime.now();
    final List<VaultItem> logins = data
        .itemsOfType(VaultItemType.login)
        .toList();

    // Count how many live items share each password, so reuse can be reported
    // on every item involved rather than only the second one found.
    final Map<String, int> passwordCounts = <String, int>{};
    for (final VaultItem item in data.liveItems) {
      final String password = item.password;
      if (password.isNotEmpty) {
        passwordCounts[password] = (passwordCounts[password] ?? 0) + 1;
      }
    }

    final List<HealthIssue> issues = <HealthIssue>[];
    int checked = 0;

    for (final VaultItem item in logins) {
      final String password = item.password;

      if (password.isEmpty) {
        issues.add(
          HealthIssue(
            item: item,
            kind: HealthIssueKind.missing,
            advice:
                'This login has no password saved. Add one so you are not '
                'relying on remembering it.',
          ),
        );
        continue;
      }

      checked++;

      if ((passwordCounts[password] ?? 0) > 1) {
        final int others = passwordCounts[password]! - 1;
        issues.add(
          HealthIssue(
            item: item,
            kind: HealthIssueKind.reused,
            advice: others == 1
                ? 'This password is used on one other entry. If either site '
                      'is breached, both accounts are exposed. Give each its '
                      'own password.'
                : 'This password is used on $others other entries. If any of '
                      'those sites is breached, all of them are exposed. Give '
                      'each its own password.',
          ),
        );
      }

      final String? weakness = _weakness(password);
      if (weakness != null) {
        issues.add(
          HealthIssue(item: item, kind: HealthIssueKind.weak, advice: weakness),
        );
      }

      final DateTime? changed = item.passwordUpdatedAt;
      if (changed != null && at.difference(changed) > oldAfter) {
        final int years = at.difference(changed).inDays ~/ 365;
        issues.add(
          HealthIssue(
            item: item,
            kind: HealthIssueKind.old,
            advice: years >= 1
                ? 'This password has not changed in over '
                      '${years == 1 ? 'a year' : '$years years'}. Changing it '
                      'occasionally limits the damage from a breach you never '
                      'hear about.'
                : 'This password has not changed in a long time.',
          ),
        );
      }

      if (item.totpSecret.isEmpty && item.url.isNotEmpty) {
        issues.add(
          HealthIssue(
            item: item,
            kind: HealthIssueKind.noTwoFactor,
            advice:
                'No authenticator key is saved for this account. If the site '
                'offers two-factor sign-in, turning it on is the single '
                'biggest improvement you can make.',
          ),
        );
      }
    }

    issues.sort((HealthIssue a, HealthIssue b) {
      final int bySeverity = b.severity.index.compareTo(a.severity.index);
      return bySeverity != 0
          ? bySeverity
          : a.item.title.toLowerCase().compareTo(b.item.title.toLowerCase());
    });

    return HealthReport(
      issues: issues,
      passwordsChecked: checked,
      generatedAt: at,
    );
  }

  /// Why [password] is weak, or null when it is not.
  ///
  /// Length first, because it matters far more than character variety: a long
  /// passphrase of only lowercase letters is stronger than a short password
  /// with a symbol in it, and a checker that said otherwise would push people
  /// towards the worse choice.
  static String? _weakness(String password) {
    if (password.length < 8) {
      return 'This password is only ${password.length} characters. Short '
          'passwords can be guessed by a computer very quickly. Use the '
          'generator to make a longer one.';
    }

    final bool hasLower = password.contains(RegExp('[a-z]'));
    final bool hasUpper = password.contains(RegExp('[A-Z]'));
    final bool hasDigit = password.contains(RegExp('[0-9]'));
    final bool hasSymbol = password.contains(RegExp(r'[^A-Za-z0-9]'));
    final int variety =
        (hasLower ? 1 : 0) +
        (hasUpper ? 1 : 0) +
        (hasDigit ? 1 : 0) +
        (hasSymbol ? 1 : 0);

    if (password.length < minimumReasonableLength && variety < 3) {
      return 'This password is short and uses only $variety kind'
          '${variety == 1 ? '' : 's'} of character. Use the generator to make '
          'a stronger one.';
    }

    if (_isSingleRepeatedCharacter(password)) {
      return 'This password is the same character repeated, which is no '
          'harder to guess than that one character.';
    }

    if (_looksSequential(password)) {
      return 'This password is a simple sequence, which is one of the first '
          'things a guessing program tries.';
    }

    return null;
  }

  static bool _isSingleRepeatedCharacter(String password) {
    if (password.isEmpty) {
      return false;
    }
    for (int i = 1; i < password.length; i++) {
      if (password[i] != password[0]) {
        return false;
      }
    }
    return true;
  }

  /// Longest run of consecutive characters that counts as a pattern.
  ///
  /// Five, not the whole password. An earlier version required the entire
  /// password to be one unbroken run, which let "123456789012" through
  /// because it wraps from 9 back to 0 - obviously guessable, and missed.
  ///
  /// Five is safe against false alarms: for a generated password to contain
  /// five consecutive characters by chance is vanishingly unlikely, so this
  /// does not punish good passwords.
  static const int _sequenceRunLength = 5;

  /// True when the password contains a straight run up or down the character
  /// set, as "123456" and "abcdef" do.
  static bool _looksSequential(String password) {
    if (password.length < _sequenceRunLength) {
      return false;
    }
    int ascending = 1;
    int descending = 1;
    for (int i = 1; i < password.length; i++) {
      final int step = password.codeUnitAt(i) - password.codeUnitAt(i - 1);
      ascending = step == 1 ? ascending + 1 : 1;
      descending = step == -1 ? descending + 1 : 1;
      if (ascending >= _sequenceRunLength || descending >= _sequenceRunLength) {
        return true;
      }
    }
    return false;
  }
}
