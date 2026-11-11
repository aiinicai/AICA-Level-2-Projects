import 'dart:convert';
import 'dart:typed_data';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/crypto/kdf_parameters.dart';
import 'package:family_vault/src/vault/vault_codec.dart';
import 'package:family_vault/src/vault/vault_header.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/fake_crypto_service.dart';

/// Tests for how a vault file is assembled and taken apart.
///
/// These use FakeCryptoService, which is not cryptography. They test the
/// plumbing: field layout, ordering of operations, truncation handling, nonce
/// freshness and key disposal. Whether the cipher actually resists tampering
/// is a property of libsodium and is tested in crypto_security_test.dart.
void main() {
  late FakeCryptoService crypto;
  late VaultCodec codec;

  setUp(() {
    crypto = FakeCryptoService();
    codec = VaultCodec(crypto);
  });

  Uint8List payloadOf(String text) => Uint8List.fromList(utf8.encode(text));

  group('sealing and opening', () {
    test('round-trips a payload', () {
      final Uint8List payload = payloadOf('{"items":[]}');
      final Uint8List file = codec.seal(
        masterPassword: 'correct horse battery staple',
        payload: payload,
      );
      final Uint8List opened = codec.open(
        file: file,
        masterPassword: 'correct horse battery staple',
      );
      expect(opened, payload);
    });

    test('round-trips an empty payload', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: Uint8List(0),
      );
      expect(codec.open(file: file, masterPassword: 'pw'), isEmpty);
    });

    test('produces a file that starts with a readable header', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      final VaultHeader header = codec.inspect(file);
      expect(header.formatVersion, VaultHeader.currentFormatVersion);
      expect(header.kdfAlgorithm, KdfAlgorithmId.argon2id13);
      expect(header.cipher, CipherId.xChaCha20Poly1305Ietf);
      expect(header.salt.length, crypto.saltLength);
      expect(header.nonce.length, crypto.nonceLength);
    });

    test('the file is exactly the header followed by the sealed payload', () {
      final Uint8List payload = payloadOf('hello');
      final Uint8List file = codec.seal(masterPassword: 'pw', payload: payload);
      final VaultHeader header = codec.inspect(file);
      expect(file.length, header.length + payload.length + crypto.tagLength);
    });

    test('can be inspected without the master password', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('secret'),
      );
      expect(() => codec.inspect(file), returnsNormally);
    });
  });

  // Nonce reuse under one key is the classic way to break a stream cipher.
  // The codec must draw a new nonce on every write, not once per vault.
  group('nonce handling', () {
    test('uses a fresh nonce for every write', () {
      final Uint8List first = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('same'),
      );
      final Uint8List second = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('same'),
        reuseSalt: codec.inspect(first).salt,
      );
      expect(codec.inspect(second).nonce, isNot(codec.inspect(first).nonce));
    });

    test('identical payloads do not produce identical files', () {
      final Uint8List first = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('same'),
      );
      final Uint8List second = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('same'),
      );
      expect(first, isNot(second));
    });

    test('asks for a nonce of exactly the cipher length', () {
      codec.seal(masterPassword: 'pw', payload: payloadOf('x'));
      expect(crypto.randomCallLengths, contains(crypto.nonceLength));
    });
  });

  group('salt handling', () {
    test('a new vault gets a new salt', () {
      final Uint8List first = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('a'),
      );
      final Uint8List second = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('a'),
      );
      expect(codec.inspect(second).salt, isNot(codec.inspect(first).salt));
    });

    test('re-sealing an existing vault keeps its salt', () {
      final Uint8List first = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('a'),
      );
      final Uint8List salt = codec.inspect(first).salt;
      final Uint8List second = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('b'),
        reuseSalt: salt,
      );
      expect(codec.inspect(second).salt, salt);
      expect(codec.open(file: second, masterPassword: 'pw'), payloadOf('b'));
    });

    test('rejects a salt of the wrong length', () {
      expect(
        () => codec.seal(
          masterPassword: 'pw',
          payload: payloadOf('a'),
          reuseSalt: Uint8List(3),
        ),
        throwsA(isA<VaultFormatFailure>()),
      );
    });
  });

  // A derived key that is not wiped sits in memory until the process ends.
  // The codec derives a key per operation, so every operation must dispose it,
  // including the ones that throw.
  group('key hygiene', () {
    test('disposes the key after sealing', () {
      codec.seal(masterPassword: 'pw', payload: payloadOf('x'));
      expect(crypto.keysDerived, 1);
      expect(crypto.keysDisposed, crypto.keysDerived);
    });

    test('disposes the key after opening', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      codec.open(file: file, masterPassword: 'pw');
      expect(crypto.keysDisposed, crypto.keysDerived);
    });

    test('disposes the key even when opening fails', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      file[file.length - 1] ^= 0xFF;
      expect(
        () => codec.open(file: file, masterPassword: 'pw'),
        throwsA(isA<VaultAuthenticationFailure>()),
      );
      expect(
        crypto.keysDisposed,
        crypto.keysDerived,
        reason: 'a failed open must not leave a derived key in memory',
      );
    });
  });

  group('rejects damaged files', () {
    test('a file with no payload at all', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      final Uint8List headerOnly = Uint8List.fromList(
        file.sublist(0, codec.inspect(file).length),
      );
      expect(
        () => codec.open(file: headerOnly, masterPassword: 'pw'),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a file whose sealed section is shorter than a tag', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      final int cut = codec.inspect(file).length + crypto.tagLength - 1;
      expect(
        () => codec.open(
          file: Uint8List.fromList(file.sublist(0, cut)),
          masterPassword: 'pw',
        ),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a file that is not a vault at all', () {
      expect(
        () => codec.open(
          file: Uint8List.fromList(utf8.encode('just some text')),
          masterPassword: 'pw',
        ),
        throwsA(isA<VaultFormatFailure>()),
      );
    });
  });

  group('cost parameters', () {
    test('defaults to the library recommendation', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      expect(codec.inspect(file).kdfParameters, crypto.recommendedParameters);
    });

    test('honours explicit parameters and stores them in the header', () {
      const Argon2idParameters custom = Argon2idParameters(
        opsLimit: 3,
        memLimitBytes: 32 * 1024 * 1024,
      );
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
        parameters: custom,
      );
      expect(codec.inspect(file).kdfParameters, custom);
    });

    test('refuses to write parameters outside the permitted range', () {
      expect(
        () => codec.seal(
          masterPassword: 'pw',
          payload: payloadOf('x'),
          parameters: const Argon2idParameters(
            opsLimit: 1,
            memLimitBytes: 1024,
          ),
        ),
        throwsA(isA<VaultParameterFailure>()),
      );
    });
  });
}
