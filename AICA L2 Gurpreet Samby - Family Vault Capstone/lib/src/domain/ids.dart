import 'dart:math';

/// Generates identifiers for items and folders.
///
/// Uses [Random.secure] rather than the default generator. These identifiers
/// are not secrets, but they do go into a file that syncs between devices, and
/// a predictable sequence would make two devices more likely to mint the same
/// identifier for different things during an offline edit.
abstract final class Ids {
  static final Random _random = Random.secure();

  static const String _alphabet = '0123456789abcdef';

  /// A 32-character hexadecimal identifier, 128 bits of randomness.
  static String generate() {
    final StringBuffer buffer = StringBuffer();
    for (int i = 0; i < 32; i++) {
      buffer.write(_alphabet[_random.nextInt(16)]);
    }
    return buffer.toString();
  }

  /// True if [value] looks like an identifier this application minted.
  ///
  /// Used when reading a vault file, so that a damaged or hand-edited file is
  /// rejected rather than loaded with nonsense keys.
  static bool isValid(String value) {
    if (value.length != 32) {
      return false;
    }
    for (int i = 0; i < value.length; i++) {
      if (!_alphabet.contains(value[i])) {
        return false;
      }
    }
    return true;
  }
}
