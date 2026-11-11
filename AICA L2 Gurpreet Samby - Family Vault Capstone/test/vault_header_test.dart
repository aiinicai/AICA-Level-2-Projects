import 'dart:typed_data';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/crypto/kdf_parameters.dart';
import 'package:family_vault/src/vault/vault_header.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the vault file header.
///
/// Pure Dart: no cryptographic library is involved, which is the point. The
/// header parser is the first thing an untrusted file meets, so it is tested
/// on its own and must reject bad input without the help of anything else.
void main() {
  Uint8List bytesOf(int length, int fill) =>
      Uint8List(length)..fillRange(0, length, fill);

  VaultHeader sampleHeader({
    int opsLimit = 2,
    int memLimitBytes = 64 * 1024 * 1024,
  }) => VaultHeader(
    formatVersion: VaultHeader.currentFormatVersion,
    kdfAlgorithm: KdfAlgorithmId.argon2id13,
    cipher: CipherId.xChaCha20Poly1305Ietf,
    kdfParameters: Argon2idParameters(
      opsLimit: opsLimit,
      memLimitBytes: memLimitBytes,
    ),
    salt: bytesOf(16, 0xAB),
    nonce: bytesOf(24, 0xCD),
  );

  group('encoding', () {
    test('round-trips every field unchanged', () {
      final VaultHeader original = sampleHeader();
      final VaultHeader decoded = VaultHeader.decode(original.encode());

      expect(decoded.formatVersion, original.formatVersion);
      expect(decoded.kdfAlgorithm, KdfAlgorithmId.argon2id13);
      expect(decoded.cipher, CipherId.xChaCha20Poly1305Ietf);
      expect(decoded.kdfParameters, original.kdfParameters);
      expect(decoded.salt, original.salt);
      expect(decoded.nonce, original.nonce);
    });

    test('starts with the magic bytes so the file type is recognisable', () {
      final Uint8List encoded = sampleHeader().encode();
      expect(encoded.sublist(0, 4), VaultHeader.magic);
    });

    test('length matches the fixed part plus salt and nonce', () {
      final VaultHeader header = sampleHeader();
      expect(header.length, VaultHeader.fixedLength + 16 + 24);
      expect(header.encode().length, header.length);
    });

    test('is deterministic, because it doubles as associated data', () {
      final VaultHeader header = sampleHeader();
      expect(header.encode(), header.encode());
    });

    // The header is plaintext by necessity, so it is worth asserting that it
    // leaks nothing beyond format and cost. Anything else appearing here later
    // should break this test.
    test('contains nothing but format, cost, salt and nonce', () {
      final Uint8List encoded = sampleHeader().encode();
      final Uint8List body = encoded.sublist(0, VaultHeader.fixedLength);
      // 4 magic + 2 version + 1 kdf + 1 cipher + 4 ops + 4 mem + 1 + 1 + 2
      expect(body.length, 20);
      // The two reserved bytes must be zero, not a place to smuggle data.
      expect(body[18], 0);
      expect(body[19], 0);
    });

    test('copies the salt, so later changes to the source do not leak in', () {
      final Uint8List salt = bytesOf(16, 0x01);
      final Uint8List encoded = VaultHeader(
        formatVersion: VaultHeader.currentFormatVersion,
        kdfAlgorithm: KdfAlgorithmId.argon2id13,
        cipher: CipherId.xChaCha20Poly1305Ietf,
        kdfParameters: const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: 64 * 1024 * 1024,
        ),
        salt: salt,
        nonce: bytesOf(24, 0x02),
      ).encode();

      final VaultHeader decoded = VaultHeader.decode(encoded);
      encoded.fillRange(
        VaultHeader.fixedLength,
        VaultHeader.fixedLength + 16,
        0xFF,
      );
      expect(decoded.salt.every((int b) => b == 0x01), isTrue);
    });
  });

  group('rejects a file that is not ours', () {
    test('empty input', () {
      expect(
        () => VaultHeader.decode(Uint8List(0)),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('input shorter than the fixed header', () {
      expect(
        () => VaultHeader.decode(bytesOf(VaultHeader.fixedLength - 1, 0)),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('wrong magic bytes', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[0] = 0x00;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a plausible-looking file of zeros', () {
      expect(
        () => VaultHeader.decode(bytesOf(128, 0)),
        throwsA(isA<VaultFormatFailure>()),
      );
    });
  });

  group('rejects unsupported descriptions', () {
    test('a newer format version, and says so distinctly', () {
      final Uint8List encoded = sampleHeader().encode();
      ByteData.sublistView(encoded).setUint16(4, 99);
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(
          isA<VaultVersionFailure>().having(
            (VaultVersionFailure f) => f.fileVersion,
            'fileVersion',
            99,
          ),
        ),
      );
    });

    test('an unknown key-derivation algorithm', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[6] = 77;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('an unknown cipher', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[7] = 77;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('content in the reserved field', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[18] = 0x01;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });
  });

  group('rejects malformed lengths without a RangeError escaping', () {
    test('a declared salt length longer than the data', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[16] = 200;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a declared nonce length longer than the data', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[17] = 200;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a zero-length salt', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[16] = 0;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a zero-length nonce', () {
      final Uint8List encoded = sampleHeader().encode();
      encoded[17] = 0;
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('truncation anywhere in the header is a typed failure', () {
      final Uint8List full = sampleHeader().encode();
      for (int cut = 0; cut < full.length; cut++) {
        expect(
          () => VaultHeader.decode(Uint8List.fromList(full.sublist(0, cut))),
          throwsA(isA<VaultFailure>()),
          reason: 'truncating to $cut bytes should fail cleanly',
        );
      }
    });
  });

  // This is the denial-of-service guard from decision D-009. The parameters
  // come from a file, so a file can ask for an absurd allocation. It must be
  // refused while it is still just a number.
  group('rejects hostile cost parameters before allocating', () {
    test('a memory cost far beyond any real device', () {
      final Uint8List encoded = sampleHeader().encode();
      // 4 TiB expressed in kibibytes.
      const int fourTibInKib = 4 * 1024 * 1024;
      ByteData.sublistView(encoded).setUint32(12, fourTibInKib);
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('a memory cost below the security floor', () {
      final Uint8List encoded = sampleHeader().encode();
      ByteData.sublistView(encoded).setUint32(12, 1);
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('an absurd number of passes', () {
      final Uint8List encoded = sampleHeader().encode();
      ByteData.sublistView(encoded).setUint32(8, 4000000);
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('zero passes', () {
      final Uint8List encoded = sampleHeader().encode();
      ByteData.sublistView(encoded).setUint32(8, 0);
      expect(
        () => VaultHeader.decode(encoded),
        throwsA(isA<VaultParameterFailure>()),
      );
    });
  });
}
