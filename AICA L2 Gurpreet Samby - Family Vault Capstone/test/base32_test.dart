import 'dart:convert';
import 'dart:typed_data';

import 'package:family_vault/src/domain/base32.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for base32, against RFC 4648's own test vectors.
///
/// Authenticator setup keys are base32, so a decoder that is subtly wrong
/// produces codes that are confidently wrong — the worst failure mode
/// available, because the user would be locked out of an account with no
/// explanation. Hence known-answer tests rather than round-trip tests alone.
void main() {
  String decodeToText(String encoded) => utf8.decode(Base32.decode(encoded));

  Uint8List bytesOf(String text) => Uint8List.fromList(utf8.encode(text));

  group('RFC 4648 section 10 test vectors', () {
    // These are the vectors published in the RFC itself.
    const Map<String, String> vectors = <String, String>{
      '': '',
      'f': 'MY======',
      'fo': 'MZXQ====',
      'foo': 'MZXW6===',
      'foob': 'MZXW6YQ=',
      'fooba': 'MZXW6YTB',
      'foobar': 'MZXW6YTBOI======',
    };

    vectors.forEach((String plain, String encoded) {
      test('decodes "$encoded" to "$plain"', () {
        expect(decodeToText(encoded), plain);
      });

      test('encodes "$plain" to "$encoded" without padding', () {
        expect(Base32.encode(bytesOf(plain)), encoded.replaceAll('=', ''));
      });
    });
  });

  group('tolerates how people actually paste keys', () {
    test('accepts a key with no padding', () {
      expect(decodeToText('MZXW6YTBOI'), 'foobar');
    });

    test('accepts a key grouped with spaces, as sites display them', () {
      expect(decodeToText('MZXW 6YTB OI'), 'foobar');
    });

    test('accepts a key grouped with hyphens', () {
      expect(decodeToText('MZXW-6YTB-OI'), 'foobar');
    });

    test('accepts lower case', () {
      expect(decodeToText('mzxw6ytboi'), 'foobar');
    });

    test('accepts a mixture of all of those', () {
      expect(decodeToText('mzxw-6YTB oi==='), 'foobar');
    });
  });

  group('rejects what it cannot decode', () {
    test('a character outside the alphabet', () {
      expect(() => Base32.decode('MZXW6YTB!'), throwsA(isA<FormatException>()));
    });

    test('the digits 0, 1 and 8, which base32 does not use', () {
      for (final String bad in <String>['MZXW0', 'MZXW1', 'MZXW8']) {
        expect(
          () => Base32.decode(bad),
          throwsA(isA<FormatException>()),
          reason: '"$bad" should not decode',
        );
      }
    });

    test('a key truncated part-way through a byte', () {
      // A single symbol carries five bits, which cannot make a whole byte.
      expect(() => Base32.decode('M'), throwsA(isA<FormatException>()));
    });

    test('non-zero padding bits, which mean the key was cut short', () {
      // 'MZXW6YTBOJ' differs from the valid 'MZXW6YTBOI' only in bits that
      // should be zero padding.
      expect(
        () => Base32.decode('MZXW6YTBOJ'),
        throwsA(isA<FormatException>()),
      );
    });
  });

  group('isValid', () {
    test('accepts a real key', () {
      expect(Base32.isValid('MZXW6YTBOI'), isTrue);
    });

    test('rejects a key containing a character outside the alphabet', () {
      expect(Base32.isValid('MZXW6YTB!'), isFalse);
      expect(Base32.isValid('hello world'), isFalse);
    });

    // Worth stating plainly: base32 carries no checksum, so a typo that
    // happens to land inside the alphabet cannot be detected. "not a key"
    // becomes NOTAKEY once spaces are stripped, and every one of those
    // letters is valid base32, so it decodes. Nothing can catch that.
    test('cannot detect a typo that is still valid base32', () {
      expect(Base32.isValid('not a key'), isTrue);
    });

    test('rejects an empty key, since it produces no codes', () {
      expect(Base32.isValid(''), isFalse);
    });
  });

  group('round trips', () {
    test('every byte value survives encoding and decoding', () {
      final Uint8List all = Uint8List.fromList(
        List<int>.generate(256, (int i) => i),
      );
      expect(Base32.decode(Base32.encode(all)), all);
    });

    test('every length from 1 to 40 bytes round-trips', () {
      for (int length = 1; length <= 40; length++) {
        final Uint8List bytes = Uint8List.fromList(
          List<int>.generate(length, (int i) => (i * 7 + 3) & 0xFF),
        );
        expect(
          Base32.decode(Base32.encode(bytes)),
          bytes,
          reason: 'failed at length $length',
        );
      }
    });
  });
}
