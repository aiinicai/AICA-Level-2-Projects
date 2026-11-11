import 'dart:convert';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/crypto/crypto_service.dart';
import 'package:family_vault/src/crypto/kdf_parameters.dart';
import 'package:family_vault/src/crypto/sodium_crypto_service.dart';
import 'package:family_vault/src/vault/vault_codec.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

/// Security tests against the real cryptographic library.
///
/// Nothing here is faked. These assert the properties the whole product rests
/// on: that a wrong password cannot open a vault, that a single altered bit
/// anywhere in the file is refused, and that nothing unverified is ever
/// returned.
///
/// They are deliberately not skippable. If libsodium cannot be initialised in
/// this environment, these tests fail rather than quietly pass, because a
/// security test that silently does not run is worse than no test at all.
void main() {
  late CryptoService crypto;
  late VaultCodec codec;

  // Fast but still valid costs, used for the tests that run hundreds of
  // derivations. The costs this build actually writes are checked separately
  // below.
  const Argon2idParameters fastCosts = Argon2idParameters(
    opsLimit: Argon2idParameters.minOpsLimit,
    memLimitBytes: Argon2idParameters.minMemLimitBytes,
  );

  setUpAll(() async {
    crypto = await SodiumCryptoService.initialise();
    codec = VaultCodec(crypto);
  });

  Uint8List payloadOf(String text) => Uint8List.fromList(utf8.encode(text));

  group('the library is really there', () {
    test('reports the lengths libsodium defines', () {
      // XChaCha20-Poly1305-IETF: 32-byte key, 24-byte nonce, 16-byte tag.
      // Argon2id in libsodium: 16-byte salt.
      expect(crypto.keyLength, 32);
      expect(crypto.nonceLength, 24);
      expect(crypto.tagLength, 16);
      expect(crypto.saltLength, 16);
    });

    test('produces different random bytes each time', () {
      final Uint8List a = crypto.randomBytes(32);
      final Uint8List b = crypto.randomBytes(32);
      expect(a.length, 32);
      expect(a, isNot(b));
    });

    test('random output is not all one value', () {
      final Uint8List bytes = crypto.randomBytes(64);
      expect(bytes.toSet().length, greaterThan(1));
    });
  });

  group('key derivation', () {
    test('derives a key of the cipher key length', () {
      final Uint8List salt = crypto.randomBytes(crypto.saltLength);
      final VaultKey key = crypto.deriveKey(
        masterPassword: 'a master password',
        salt: salt,
        parameters: fastCosts,
      );
      addTearDown(key.dispose);
      expect(key.length, crypto.keyLength);
    });

    test('is deterministic: the same inputs open what they sealed', () {
      final Uint8List file = codec.seal(
        masterPassword: 'repeatable',
        payload: payloadOf('determinism'),
        parameters: fastCosts,
      );
      expect(
        codec.open(file: file, masterPassword: 'repeatable'),
        payloadOf('determinism'),
      );
    });

    test('rejects a salt of the wrong length', () {
      expect(
        () => crypto.deriveKey(
          masterPassword: 'pw',
          salt: Uint8List(crypto.saltLength - 1),
          parameters: fastCosts,
        ),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('refuses hostile cost parameters even when called directly', () {
      expect(
        () => crypto.deriveKey(
          masterPassword: 'pw',
          salt: crypto.randomBytes(crypto.saltLength),
          parameters: const Argon2idParameters(
            opsLimit: 2,
            memLimitBytes: Argon2idParameters.maxMemLimitBytes + 1024,
          ),
        ),
        throwsA(isA<VaultParameterFailure>()),
      );
    });
  });

  group('a vault round-trips with the costs this build writes', () {
    test('seals and opens with the recommended parameters', () {
      final Uint8List payload = payloadOf('{"items":[{"name":"Bank"}]}');
      final Stopwatch watch = Stopwatch()..start();
      final Uint8List file = codec.seal(
        masterPassword: 'a long enough master password',
        payload: payload,
      );
      final int sealMs = watch.elapsedMilliseconds;
      watch.reset();
      final Uint8List opened = codec.open(
        file: file,
        masterPassword: 'a long enough master password',
      );
      final int openMs = watch.elapsedMilliseconds;

      expect(opened, payload);

      // Informational, not asserted: CI hardware differs from a phone, so a
      // timing assertion would be flaky. Printed so the figure is on record
      // when the default costs are tuned.
      debugPrint(
        'Argon2id ${crypto.recommendedParameters}: '
        'seal ${sealMs}ms, open ${openMs}ms',
      );
    });

    test('the recommended cost clears the OWASP Argon2id minimum', () {
      const int owaspMinimumMemory = 19 * 1024 * 1024;
      expect(
        crypto.recommendedParameters.memLimitBytes,
        greaterThanOrEqualTo(owaspMinimumMemory),
      );
      expect(crypto.recommendedParameters.opsLimit, greaterThanOrEqualTo(1));
      expect(crypto.recommendedParameters.validate, returnsNormally);
    });

    test('the recommended cost survives a header round trip unchanged', () {
      final Uint8List file = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
      );
      expect(codec.inspect(file).kdfParameters, crypto.recommendedParameters);
    });
  });

  group('a wrong password cannot open a vault', () {
    late Uint8List file;

    setUpAll(() {
      file = codec.seal(
        masterPassword: 'the real password',
        payload: payloadOf('sensitive contents'),
        parameters: fastCosts,
      );
    });

    test('a completely different password fails', () {
      expect(
        () => codec.open(file: file, masterPassword: 'something else'),
        throwsA(isA<VaultAuthenticationFailure>()),
      );
    });

    test('a password differing by one character fails', () {
      expect(
        () => codec.open(file: file, masterPassword: 'the real passwore'),
        throwsA(isA<VaultAuthenticationFailure>()),
      );
    });

    test('an empty password fails', () {
      expect(
        () => codec.open(file: file, masterPassword: ''),
        throwsA(isA<VaultAuthenticationFailure>()),
      );
    });

    test('the failure does not say whether the password was close', () {
      // A message that distinguished "wrong password" from "damaged file"
      // would tell an attacker holding the file whether a guess was close.
      String messageFor(String password) {
        try {
          codec.open(file: file, masterPassword: password);
          fail('expected the open to fail');
        } on VaultAuthenticationFailure catch (failure) {
          return failure.message;
        }
      }

      expect(messageFor('wrong one'), messageFor('a totally different guess'));
    });
  });

  // This is the property that matters most. The authentication tag covers the
  // header as associated data as well as the payload, so there should be no
  // byte anywhere in the file that an attacker can change without the file
  // being refused.
  group('no single altered bit anywhere in the file is accepted', () {
    test('flipping one bit at every byte position is always refused', () {
      final Uint8List original = codec.seal(
        masterPassword: 'tamper test',
        payload: payloadOf('0123456789abcdef'),
        parameters: fastCosts,
      );

      int refused = 0;
      for (int i = 0; i < original.length; i++) {
        final Uint8List altered = Uint8List.fromList(original);
        altered[i] ^= 0x01;
        try {
          codec.open(file: altered, masterPassword: 'tamper test');
          fail(
            'altering byte $i of ${original.length} produced a vault that '
            'still opened',
          );
        } on VaultFailure {
          refused++;
        }
      }
      expect(refused, original.length);
    });

    test('truncating the file at any point is refused', () {
      final Uint8List original = codec.seal(
        masterPassword: 'truncation test',
        payload: payloadOf('0123456789'),
        parameters: fastCosts,
      );
      for (int cut = 0; cut < original.length; cut++) {
        expect(
          () => codec.open(
            file: Uint8List.fromList(original.sublist(0, cut)),
            masterPassword: 'truncation test',
          ),
          throwsA(isA<VaultFailure>()),
          reason: 'a file cut to $cut bytes must not open',
        );
      }
    });

    test('appending bytes to the file is refused', () {
      final Uint8List original = codec.seal(
        masterPassword: 'append test',
        payload: payloadOf('payload'),
        parameters: fastCosts,
      );
      final Uint8List extended = Uint8List.fromList(<int>[...original, 0x00]);
      expect(
        () => codec.open(file: extended, masterPassword: 'append test'),
        throwsA(isA<VaultFailure>()),
      );
    });

    test('swapping in another vault\'s sealed section is refused', () {
      final Uint8List a = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('vault a'),
        parameters: fastCosts,
      );
      final Uint8List b = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('vault b'),
        parameters: fastCosts,
      );
      final int headerLength = codec.inspect(a).length;
      // a's header with b's ciphertext: the nonce and salt no longer match the
      // sealed data, so this must fail.
      final Uint8List spliced = Uint8List.fromList(<int>[
        ...a.sublist(0, headerLength),
        ...b.sublist(headerLength),
      ]);
      expect(
        () => codec.open(file: spliced, masterPassword: 'pw'),
        throwsA(isA<VaultFailure>()),
      );
    });
  });

  group('each vault is sealed independently', () {
    test('two vaults with the same password get different salts', () {
      final Uint8List a = codec.seal(
        masterPassword: 'same password',
        payload: payloadOf('x'),
        parameters: fastCosts,
      );
      final Uint8List b = codec.seal(
        masterPassword: 'same password',
        payload: payloadOf('x'),
        parameters: fastCosts,
      );
      expect(codec.inspect(a).salt, isNot(codec.inspect(b).salt));
    });

    test('one vault cannot be opened with another vault\'s header', () {
      final Uint8List a = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
        parameters: fastCosts,
      );
      final Uint8List b = codec.seal(
        masterPassword: 'pw',
        payload: payloadOf('x'),
        parameters: fastCosts,
      );
      final int headerLength = codec.inspect(a).length;
      final Uint8List spliced = Uint8List.fromList(<int>[
        ...b.sublist(0, headerLength),
        ...a.sublist(headerLength),
      ]);
      expect(
        () => codec.open(file: spliced, masterPassword: 'pw'),
        throwsA(isA<VaultFailure>()),
      );
    });
  });

  group('nothing secret reaches an error message', () {
    test('failure messages carry no password, key or payload text', () {
      const String password = 'uniquePasswordString';
      const String secret = 'uniqueSecretPayload';
      final Uint8List file = codec.seal(
        masterPassword: password,
        payload: payloadOf(secret),
        parameters: fastCosts,
      );
      final Uint8List altered = Uint8List.fromList(file);
      altered[altered.length - 1] ^= 0xFF;

      try {
        codec.open(file: altered, masterPassword: password);
        fail('expected the open to fail');
      } on VaultFailure catch (failure) {
        final String text = failure.toString();
        expect(text, isNot(contains(password)));
        expect(text, isNot(contains(secret)));
      }
    });
  });
}
