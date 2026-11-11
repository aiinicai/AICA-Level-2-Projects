import 'dart:typed_data';

/// Base32 decoding, RFC 4648, for authenticator setup keys.
///
/// This is an encoding, not a cryptographic primitive, so implementing it here
/// is not a departure from the rule against writing cryptography. It is
/// checked against the RFC's own test vectors.
///
/// Authenticator keys are shown to people as base32 and are routinely copied
/// with spaces in them and without padding, so decoding is deliberately
/// tolerant of both while still rejecting characters that are not base32 at
/// all.
abstract final class Base32 {
  static const String _alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

  /// Decodes [input], ignoring spaces, hyphens and padding, and accepting
  /// either case.
  ///
  /// Throws [FormatException] when a character is not part of the base32
  /// alphabet, or when the length cannot represent whole bytes.
  static Uint8List decode(String input) {
    final StringBuffer cleaned = StringBuffer();
    for (int i = 0; i < input.length; i++) {
      final String character = input[i];
      if (character == ' ' || character == '-' || character == '=') {
        continue;
      }
      cleaned.write(character.toUpperCase());
    }
    final String symbols = cleaned.toString();
    if (symbols.isEmpty) {
      return Uint8List(0);
    }

    int buffer = 0;
    int bitsHeld = 0;
    final List<int> output = <int>[];
    for (int i = 0; i < symbols.length; i++) {
      final int value = _alphabet.indexOf(symbols[i]);
      if (value < 0) {
        throw FormatException(
          'Not a valid base32 character: "${symbols[i]}"',
          input,
          i,
        );
      }
      buffer = (buffer << 5) | value;
      bitsHeld += 5;
      if (bitsHeld >= 8) {
        bitsHeld -= 8;
        output.add((buffer >> bitsHeld) & 0xFF);
      }
    }

    // Whatever is left must be padding bits, and padding bits must be zero.
    // A non-zero remainder means the string was truncated mid-byte.
    if (bitsHeld >= 5 || (buffer & ((1 << bitsHeld) - 1)) != 0) {
      throw FormatException(
        'This authenticator key is incomplete.',
        input,
        symbols.length,
      );
    }
    return Uint8List.fromList(output);
  }

  /// Encodes [bytes] as base32 without padding.
  ///
  /// Used when showing a key back to the user, not for storage.
  static String encode(Uint8List bytes) {
    if (bytes.isEmpty) {
      return '';
    }
    final StringBuffer output = StringBuffer();
    int buffer = 0;
    int bitsHeld = 0;
    for (final int byte in bytes) {
      buffer = (buffer << 8) | byte;
      bitsHeld += 8;
      while (bitsHeld >= 5) {
        bitsHeld -= 5;
        output.write(_alphabet[(buffer >> bitsHeld) & 0x1F]);
      }
    }
    if (bitsHeld > 0) {
      output.write(_alphabet[(buffer << (5 - bitsHeld)) & 0x1F]);
    }
    return output.toString();
  }

  /// True when [input] can be decoded.
  ///
  /// Used by the interface to tell someone their pasted key is wrong while
  /// they are still looking at the field, rather than when a code fails to
  /// work.
  static bool isValid(String input) {
    try {
      return decode(input).isNotEmpty;
    } on FormatException {
      return false;
    }
  }
}
