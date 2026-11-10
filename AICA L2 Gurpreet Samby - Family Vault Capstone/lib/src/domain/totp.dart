import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:meta/meta.dart';

import 'base32.dart';

/// Hash functions a TOTP key can specify.
enum TotpAlgorithm {
  /// SHA-1. The default, and what almost every site issues.
  sha1('SHA1'),

  /// SHA-256.
  sha256('SHA256'),

  /// SHA-512.
  sha512('SHA512');

  const TotpAlgorithm(this.label);

  /// Name as it appears in an `otpauth://` link.
  final String label;

  /// Maps a name from a link, defaulting to SHA-1 as RFC 6238 does.
  static TotpAlgorithm fromLabel(String? label) {
    if (label == null) {
      return TotpAlgorithm.sha1;
    }
    final String upper = label.toUpperCase();
    for (final TotpAlgorithm algorithm in TotpAlgorithm.values) {
      if (algorithm.label == upper) {
        return algorithm;
      }
    }
    return TotpAlgorithm.sha1;
  }
}

/// A time-based one-time-password configuration.
///
/// This is for the user's *other* accounts. It is not, and must not be
/// confused with, protection for the vault itself: a code checked inside this
/// app could be bypassed by anyone holding the vault file, so the vault's own
/// optional second factor is key material instead. See decision D-010.
@immutable
final class TotpConfig {
  const TotpConfig({
    required this.secret,
    this.algorithm = TotpAlgorithm.sha1,
    this.digits = 6,
    this.period = 30,
    this.issuer,
    this.account,
  });

  /// The shared secret, already decoded from base32.
  final Uint8List secret;

  /// Hash function.
  final TotpAlgorithm algorithm;

  /// How many digits the code has. Six is near-universal.
  final int digits;

  /// How many seconds a code lasts. Thirty is near-universal.
  final int period;

  /// Service name from an `otpauth://` link, if there was one.
  final String? issuer;

  /// Account name from an `otpauth://` link, if there was one.
  final String? account;

  /// Reads a configuration from a base32 setup key.
  ///
  /// Throws [FormatException] when the key is not valid base32.
  factory TotpConfig.fromBase32(
    String key, {
    TotpAlgorithm algorithm = TotpAlgorithm.sha1,
    int digits = 6,
    int period = 30,
  }) => TotpConfig(
    secret: Base32.decode(key),
    algorithm: algorithm,
    digits: digits,
    period: period,
  );

  /// Reads a configuration from an `otpauth://totp/...` link.
  ///
  /// Many sites offer the whole link behind their QR code, so accepting it
  /// saves the user picking the key out by hand.
  ///
  /// Throws [FormatException] when the link is not a usable TOTP link.
  factory TotpConfig.fromUri(String uri) {
    final Uri? candidate = Uri.tryParse(uri.trim());
    if (candidate == null) {
      throw FormatException('This is not a valid authenticator link.', uri);
    }
    final Uri parsed = candidate;
    if (parsed.scheme.toLowerCase() != 'otpauth' ||
        parsed.host.toLowerCase() != 'totp') {
      throw FormatException(
        'This link is not a time-based authenticator link.',
        uri,
      );
    }
    final String? secret = parsed.queryParameters['secret'];
    if (secret == null || secret.isEmpty) {
      throw FormatException('This link carries no secret key.', uri);
    }

    // Label is "Issuer:account" or just "account".
    String? issuer = parsed.queryParameters['issuer'];
    String? account;
    final String label = parsed.path.startsWith('/')
        ? parsed.path.substring(1)
        : parsed.path;
    if (label.isNotEmpty) {
      final int colon = label.indexOf(':');
      if (colon > 0) {
        issuer ??= label.substring(0, colon);
        account = label.substring(colon + 1);
      } else {
        account = label;
      }
    }

    final int digits =
        int.tryParse(parsed.queryParameters['digits'] ?? '') ?? 6;
    final int period =
        int.tryParse(parsed.queryParameters['period'] ?? '') ?? 30;

    return TotpConfig(
      secret: Base32.decode(secret),
      algorithm: TotpAlgorithm.fromLabel(parsed.queryParameters['algorithm']),
      digits: digits < 6 || digits > 10 ? 6 : digits,
      period: period < 1 || period > 300 ? 30 : period,
      issuer: issuer,
      account: account,
    );
  }

  /// True when this configuration can actually produce codes.
  bool get isUsable =>
      secret.isNotEmpty && digits >= 6 && digits <= 10 && period > 0;
}

/// Generates time-based one-time passwords, RFC 6238.
///
/// TOTP is HOTP (RFC 4226) with the counter set to the number of time steps
/// since the Unix epoch. The HMAC itself comes from `package:crypto`, which is
/// maintained by the Dart team; what is implemented here is the counter and
/// truncation around it, which the RFCs specify exactly and publish test
/// vectors for. Those vectors are asserted in the tests, for all three hash
/// functions.
abstract final class Totp {
  /// The code for [config] at [time], defaulting to now.
  static String generate(TotpConfig config, {DateTime? time}) {
    final DateTime at = time ?? DateTime.now();
    final int seconds = at.toUtc().millisecondsSinceEpoch ~/ 1000;
    return generateForCounter(config, seconds ~/ config.period);
  }

  /// The code for an explicit step counter. Exposed for the RFC test vectors.
  static String generateForCounter(TotpConfig config, int counter) {
    final Uint8List message = _counterBytes(counter);
    final Hmac hmac = Hmac(_digestFor(config.algorithm), config.secret);
    final List<int> mac = hmac.convert(message).bytes;

    // Dynamic truncation, RFC 4226 section 5.3: the low nibble of the last
    // byte picks where to read the four-byte value from.
    final int offset = mac[mac.length - 1] & 0x0F;
    final int binary =
        ((mac[offset] & 0x7F) << 24) |
        ((mac[offset + 1] & 0xFF) << 16) |
        ((mac[offset + 2] & 0xFF) << 8) |
        (mac[offset + 3] & 0xFF);

    final int modulus = _powerOfTen(config.digits);
    return (binary % modulus).toString().padLeft(config.digits, '0');
  }

  /// Seconds until the current code is replaced.
  ///
  /// Drives the countdown in the interface, so that a user does not type a
  /// code that is about to stop working.
  static int secondsRemaining(TotpConfig config, {DateTime? time}) {
    final DateTime at = time ?? DateTime.now();
    final int seconds = at.toUtc().millisecondsSinceEpoch ~/ 1000;
    return config.period - (seconds % config.period);
  }

  /// The counter as eight big-endian bytes.
  ///
  /// Built from two 32-bit halves rather than with `setUint64`, because the
  /// web has no 64-bit integers and the public demonstration is a web build.
  static Uint8List _counterBytes(int counter) {
    final Uint8List bytes = Uint8List(8);
    final int high = counter ~/ 0x100000000;
    final int low = counter % 0x100000000;
    bytes[0] = (high >> 24) & 0xFF;
    bytes[1] = (high >> 16) & 0xFF;
    bytes[2] = (high >> 8) & 0xFF;
    bytes[3] = high & 0xFF;
    bytes[4] = (low >> 24) & 0xFF;
    bytes[5] = (low >> 16) & 0xFF;
    bytes[6] = (low >> 8) & 0xFF;
    bytes[7] = low & 0xFF;
    return bytes;
  }

  static Hash _digestFor(TotpAlgorithm algorithm) => switch (algorithm) {
    TotpAlgorithm.sha1 => sha1,
    TotpAlgorithm.sha256 => sha256,
    TotpAlgorithm.sha512 => sha512,
  };

  static int _powerOfTen(int exponent) {
    int result = 1;
    for (int i = 0; i < exponent; i++) {
      result *= 10;
    }
    return result;
  }
}
