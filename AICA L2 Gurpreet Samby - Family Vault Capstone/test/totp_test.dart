import 'dart:convert';
import 'dart:typed_data';

import 'package:family_vault/src/domain/totp.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the built-in authenticator, against the RFCs' own test vectors.
///
/// This matters more than it looks. A TOTP implementation that is slightly
/// wrong produces six digits that look exactly like a valid code and are
/// rejected by the site, with no clue why — so the only way to know it is
/// right is to reproduce the published vectors exactly.
///
/// RFC 6238 Appendix B and RFC 4226 Appendix D are both covered. Note the
/// RFC 6238 errata: the text says one shared secret is used for all three
/// hash functions, which is wrong — each uses a secret of its own hash length.
void main() {
  Uint8List secretOf(String ascii) => Uint8List.fromList(utf8.encode(ascii));

  // RFC 6238 Appendix B secrets, per the errata.
  final Uint8List sha1Secret = secretOf('12345678901234567890');
  final Uint8List sha256Secret = secretOf('12345678901234567890123456789012');
  final Uint8List sha512Secret = secretOf(
    '1234567890123456789012345678901234567890123456789012345678901234',
  );

  DateTime at(int unixSeconds) =>
      DateTime.fromMillisecondsSinceEpoch(unixSeconds * 1000, isUtc: true);

  group('RFC 4226 Appendix D - HOTP test values', () {
    // Secret "12345678901234567890", six digits, counter 0 through 9.
    const List<String> expected = <String>[
      '755224',
      '287082',
      '359152',
      '969429',
      '338314',
      '254676',
      '287922',
      '162583',
      '399871',
      '520489',
    ];

    for (int counter = 0; counter < expected.length; counter++) {
      test('counter $counter gives ${expected[counter]}', () {
        final TotpConfig config = TotpConfig(secret: sha1Secret);
        expect(Totp.generateForCounter(config, counter), expected[counter]);
      });
    }
  });

  group('RFC 6238 Appendix B - TOTP with SHA-1', () {
    const Map<int, String> vectors = <int, String>{
      59: '94287082',
      1111111109: '07081804',
      1111111111: '14050471',
      1234567890: '89005924',
      2000000000: '69279037',
      20000000000: '65353130',
    };

    vectors.forEach((int seconds, String code) {
      test('at $seconds seconds gives $code', () {
        final TotpConfig config = TotpConfig(secret: sha1Secret, digits: 8);
        expect(Totp.generate(config, time: at(seconds)), code);
      });
    });
  });

  group('RFC 6238 Appendix B - TOTP with SHA-256', () {
    const Map<int, String> vectors = <int, String>{
      59: '46119246',
      20000000000: '77737706',
    };

    vectors.forEach((int seconds, String code) {
      test('at $seconds seconds gives $code', () {
        final TotpConfig config = TotpConfig(
          secret: sha256Secret,
          algorithm: TotpAlgorithm.sha256,
          digits: 8,
        );
        expect(Totp.generate(config, time: at(seconds)), code);
      });
    });
  });

  group('RFC 6238 Appendix B - TOTP with SHA-512', () {
    const Map<int, String> vectors = <int, String>{
      59: '90693936',
      20000000000: '47863826',
    };

    vectors.forEach((int seconds, String code) {
      test('at $seconds seconds gives $code', () {
        final TotpConfig config = TotpConfig(
          secret: sha512Secret,
          algorithm: TotpAlgorithm.sha512,
          digits: 8,
        );
        expect(Totp.generate(config, time: at(seconds)), code);
      });
    });
  });

  group('six-digit codes, which is what sites actually issue', () {
    test('are the last six digits of the eight-digit code', () {
      final TotpConfig eight = TotpConfig(secret: sha1Secret, digits: 8);
      final TotpConfig six = TotpConfig(secret: sha1Secret);
      final DateTime when = at(59);
      expect(Totp.generate(six, time: when), '287082');
      expect(
        Totp.generate(
          eight,
          time: when,
        ).endsWith(Totp.generate(six, time: when)),
        isTrue,
      );
    });

    test('are padded to six characters when the value is small', () {
      // The code is a number modulo a million, so it can legitimately be
      // smaller than six digits and must be padded, not shortened.
      final TotpConfig config = TotpConfig(secret: sha1Secret);
      for (int counter = 0; counter < 500; counter++) {
        expect(Totp.generateForCounter(config, counter).length, 6);
      }
    });
  });

  group('the countdown', () {
    test('counts down within a period', () {
      final TotpConfig config = TotpConfig(secret: sha1Secret);
      expect(Totp.secondsRemaining(config, time: at(0)), 30);
      expect(Totp.secondsRemaining(config, time: at(1)), 29);
      expect(Totp.secondsRemaining(config, time: at(29)), 1);
      expect(Totp.secondsRemaining(config, time: at(30)), 30);
    });

    test('respects a non-standard period', () {
      final TotpConfig config = TotpConfig(secret: sha1Secret, period: 60);
      expect(Totp.secondsRemaining(config, time: at(0)), 60);
      expect(Totp.secondsRemaining(config, time: at(59)), 1);
    });

    test('the code is stable for the whole period and then changes', () {
      final TotpConfig config = TotpConfig(secret: sha1Secret);
      final String first = Totp.generate(config, time: at(30));
      expect(Totp.generate(config, time: at(59)), first);
      expect(Totp.generate(config, time: at(60)), isNot(first));
    });
  });

  group('reading a setup key', () {
    test('accepts a base32 key', () {
      final TotpConfig config = TotpConfig.fromBase32('GEZDGNBVGY3TQOJQ');
      expect(config.secret, secretOf('1234567890'));
      expect(config.isUsable, isTrue);
    });

    test('rejects a key that is not base32', () {
      expect(
        () => TotpConfig.fromBase32('not a key!'),
        throwsA(isA<FormatException>()),
      );
    });
  });

  group('reading an otpauth link', () {
    test('takes the secret, issuer and account from a typical link', () {
      final TotpConfig config = TotpConfig.fromUri(
        'otpauth://totp/Example:alice@example.com'
        '?secret=GEZDGNBVGY3TQOJQ&issuer=Example',
      );
      expect(config.issuer, 'Example');
      expect(config.account, 'alice@example.com');
      expect(config.digits, 6);
      expect(config.period, 30);
      expect(config.algorithm, TotpAlgorithm.sha1);
    });

    test('reads a non-default algorithm, digit count and period', () {
      final TotpConfig config = TotpConfig.fromUri(
        'otpauth://totp/Acme:bob?secret=GEZDGNBVGY3TQOJQ'
        '&algorithm=SHA256&digits=8&period=60',
      );
      expect(config.algorithm, TotpAlgorithm.sha256);
      expect(config.digits, 8);
      expect(config.period, 60);
    });

    test(
      'defaults to SHA-1 when the algorithm is unknown, as the RFC does',
      () {
        final TotpConfig config = TotpConfig.fromUri(
          'otpauth://totp/A:b?secret=GEZDGNBVGY3TQOJQ&algorithm=SHA3',
        );
        expect(config.algorithm, TotpAlgorithm.sha1);
      },
    );

    test('falls back to sane values for absurd digits or period', () {
      final TotpConfig config = TotpConfig.fromUri(
        'otpauth://totp/A:b?secret=GEZDGNBVGY3TQOJQ&digits=99&period=0',
      );
      expect(config.digits, 6);
      expect(config.period, 30);
    });

    test('rejects a link that is not an otpauth link', () {
      expect(
        () => TotpConfig.fromUri('https://example.com'),
        throwsA(isA<FormatException>()),
      );
    });

    test('rejects a counter-based hotp link', () {
      expect(
        () => TotpConfig.fromUri(
          'otpauth://hotp/A:b?secret=GEZDGNBVGY3TQOJQ&counter=1',
        ),
        throwsA(isA<FormatException>()),
      );
    });

    test('rejects a link with no secret', () {
      expect(
        () => TotpConfig.fromUri('otpauth://totp/A:b?issuer=A'),
        throwsA(isA<FormatException>()),
      );
    });
  });
}
