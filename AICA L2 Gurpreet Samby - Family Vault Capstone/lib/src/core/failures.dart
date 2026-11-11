/// Failures that vault operations can report.
///
/// Every message here is safe to show a user and safe to write to a log: none
/// of them carries a password, a key, a nonce or any vault content. That is a
/// deliberate constraint, not a convention — an error path is one of the
/// easiest ways for a secret to escape into a crash report.
library;

/// Base type for anything that can go wrong opening or writing a vault.
///
/// Sealed, so that handling code can be checked for completeness by the
/// compiler rather than by inspection.
sealed class VaultFailure implements Exception {
  const VaultFailure(this.message);

  /// Plain-language description, safe to display and safe to log.
  final String message;

  @override
  String toString() => '$runtimeType: $message';
}

/// The file is not a Family Vault file, or its structure is damaged.
final class VaultFormatFailure extends VaultFailure {
  const VaultFormatFailure(super.message);
}

/// The file was written by a newer version of Family Vault than this one
/// understands.
///
/// Distinct from [VaultFormatFailure] because the remedy is different: the user
/// needs a newer build, not a repaired file.
final class VaultVersionFailure extends VaultFailure {
  const VaultVersionFailure(super.message, {required this.fileVersion});

  /// The format version found in the file.
  final int fileVersion;
}

/// A key-derivation parameter in the file is outside the range this build will
/// act on.
///
/// This is a security control, not a tidiness check. Parameters are read from
/// a file, and a file can be hostile: a header claiming many gigabytes of
/// memory cost would otherwise hang or crash the application the moment
/// someone opened it. See docs/decisions-and-risks.md, decision D-009.
final class VaultParameterFailure extends VaultFailure {
  const VaultParameterFailure(super.message);
}

/// Decryption did not authenticate.
///
/// Means one of two things, and deliberately does not distinguish between
/// them: the password was wrong, or the file was altered. Saying which would
/// tell an attacker holding the file whether a guessed password was close.
final class VaultAuthenticationFailure extends VaultFailure {
  const VaultAuthenticationFailure([
    super.message =
        'Could not open the vault. The master password may be wrong, or the '
        'file may have been changed or damaged.',
  ]);
}
