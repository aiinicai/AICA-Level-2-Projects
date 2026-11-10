/// How strong a master password looks.
enum PasswordStrength {
  /// Would not survive a determined guess.
  veryWeak('Very weak', 0.15),

  /// Better than nothing, not much better.
  weak('Weak', 0.35),

  /// Acceptable for an ordinary account, thin for a master password.
  fair('Fair', 0.6),

  /// A sensible master password.
  good('Good', 0.8),

  /// Comfortably strong.
  strong('Strong', 1);

  const PasswordStrength(this.label, this.fraction);

  /// Plain-language label.
  final String label;

  /// Position on a 0-to-1 meter.
  final double fraction;
}

/// Judges a master password, for the meter shown while someone types one.
///
/// This is intentionally a rough guide and says so in the interface. It is not
/// an entropy calculation, because the only honest entropy figure needs to
/// know how the password was chosen, which the application cannot see. What it
/// does reliably is catch the choices that are actually dangerous: something
/// short, something all one kind of character, or something with an obvious
/// pattern in it.
///
/// Length is weighted far above variety, because it matters far more. A long
/// passphrase of plain words beats a short password with punctuation in it,
/// and a meter that said otherwise would push people towards the weaker one.
abstract final class MasterPasswordStrength {
  /// Shortest master password the interface will accept.
  ///
  /// Not a judgement about what is good, only a floor below which the vault
  /// would be trivially opened by anyone who took the file.
  static const int minimumLength = 10;

  /// Strength of [password].
  static PasswordStrength of(String password) {
    if (password.length < minimumLength) {
      return PasswordStrength.veryWeak;
    }
    if (_hasObviousPattern(password)) {
      return PasswordStrength.veryWeak;
    }

    final int variety = _variety(password);
    final int length = password.length;

    // A long passphrase scores well on length alone, which is the point.
    if (length >= 20) {
      return variety >= 2 ? PasswordStrength.strong : PasswordStrength.good;
    }
    if (length >= 16) {
      return variety >= 3 ? PasswordStrength.strong : PasswordStrength.good;
    }
    if (length >= 14) {
      return variety >= 3 ? PasswordStrength.good : PasswordStrength.fair;
    }
    if (length >= 12) {
      return variety >= 3 ? PasswordStrength.fair : PasswordStrength.weak;
    }
    return variety >= 3 ? PasswordStrength.weak : PasswordStrength.veryWeak;
  }

  /// One line of advice, or null when the password needs none.
  static String? adviceFor(String password) {
    if (password.isEmpty) {
      return null;
    }
    if (password.length < minimumLength) {
      return 'Too short. A master password needs at least '
          '$minimumLength characters.';
    }
    if (_hasObviousPattern(password)) {
      return 'This has an obvious pattern in it, which guessing programs try '
          'first.';
    }
    final PasswordStrength strength = of(password);
    if (strength == PasswordStrength.strong) {
      return null;
    }
    if (password.length < 16) {
      return 'Longer is the easiest way to make this stronger. Four or five '
          'unrelated words are easier to remember than a short jumble, and '
          'harder to guess.';
    }
    return 'Good. Adding a number or a symbol would make it stronger still.';
  }

  static int _variety(String password) {
    final bool lower = password.contains(RegExp('[a-z]'));
    final bool upper = password.contains(RegExp('[A-Z]'));
    final bool digit = password.contains(RegExp('[0-9]'));
    final bool symbol = password.contains(RegExp(r'[^A-Za-z0-9]'));
    return (lower ? 1 : 0) +
        (upper ? 1 : 0) +
        (digit ? 1 : 0) +
        (symbol ? 1 : 0);
  }

  static bool _hasObviousPattern(String password) {
    final String lower = password.toLowerCase();

    // The same character over and over.
    if (password.isNotEmpty &&
        password.split('').every((String c) => c == password[0])) {
      return true;
    }

    // A straight run up or down the character set.
    bool run = true;
    for (int i = 1; i < password.length; i++) {
      if (password.codeUnitAt(i) - password.codeUnitAt(i - 1) != 1) {
        run = false;
        break;
      }
    }
    if (run && password.length >= 4) {
      return true;
    }

    for (final String pattern in <String>[
      'password',
      'qwerty',
      '123456',
      'letmein',
      'welcome',
      'iloveyou',
      'admin',
    ]) {
      if (lower.contains(pattern)) {
        return true;
      }
    }
    return false;
  }
}
