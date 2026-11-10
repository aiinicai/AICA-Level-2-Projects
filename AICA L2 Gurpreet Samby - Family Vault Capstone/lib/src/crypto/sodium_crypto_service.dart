import 'dart:typed_data';

import 'package:sodium/sodium_sumo.dart';

import '../core/failures.dart';
import 'crypto_service.dart';
import 'kdf_parameters.dart';

/// [CryptoService] backed by libsodium.
///
/// libsodium was chosen over a pure-Dart implementation for two reasons.
/// It is the most widely reviewed general-purpose cryptographic library
/// available, and this project implements no primitive of its own. And
/// Argon2id is memory-hard by design, so a pure-Dart implementation would make
/// unlocking slow on a phone — and lowering the cost to compensate is exactly
/// the wrong trade for a password manager.
///
/// Argon2id is reached through libsodium's "sumo" interface, which is where
/// its password-hashing functions live.
///
/// See docs/decisions-and-risks.md, decision D-003.
final class SodiumCryptoService implements CryptoService {
  /// Wraps an already-initialised libsodium instance.
  SodiumCryptoService(this._sodium);

  /// Initialises libsodium and returns a service using it.
  ///
  /// Asynchronous because `SodiumSumoInit.init()` returns `FutureOr`: on the
  /// Dart VM libsodium ships with the application and is ready immediately,
  /// but on the web the WebAssembly module has to load first. Awaiting covers
  /// both, so this one call site works on every target.
  ///
  /// Call it once, at startup, and hold the result. Initialising per operation
  /// would be wasteful and, on the web, slow.
  static Future<SodiumCryptoService> initialise() async =>
      SodiumCryptoService(await SodiumSumoInit.init());

  final SodiumSumo _sodium;

  Aead get _aead => _sodium.crypto.aeadXChaCha20Poly1305IETF;

  Pwhash get _pwhash => _sodium.crypto.pwhash;

  @override
  int get saltLength => _pwhash.saltBytes;

  @override
  int get nonceLength => _aead.nonceBytes;

  @override
  int get keyLength => _aead.keyBytes;

  @override
  int get tagLength => _aead.aBytes;

  @override
  Argon2idParameters get recommendedParameters {
    // libsodium's "interactive" profile is its guidance for a value a person
    // waits on, and it is already above the OWASP Argon2id minimum. Taken from
    // the library rather than hard-coded so it follows the library's advice as
    // that advice changes.
    //
    // Aligned to a whole kibibyte because the header stores kibibytes, so an
    // unaligned value would not survive a round trip through the file.
    return Argon2idParameters(
      opsLimit: _pwhash.opsLimitInteractive,
      memLimitBytes: _pwhash.memLimitInteractive,
    ).alignedToKib();
  }

  @override
  Uint8List randomBytes(int length) => _sodium.randombytes.buf(length);

  @override
  VaultKey deriveKey({
    required String masterPassword,
    required Uint8List salt,
    required Argon2idParameters parameters,
  }) {
    // Validated again here, not only at the call site. This is the last point
    // before memory is allocated on the strength of a number that came out of
    // a file, so it is the one place the check must not be skippable.
    parameters.validate();

    if (salt.length != saltLength) {
      throw VaultFormatFailure(
        'The vault salt is ${salt.length} bytes; '
        '$saltLength were expected.',
      );
    }

    // Argon2id is named explicitly. libsodium's default happens to be
    // Argon2id, but a password manager should not depend on a library default
    // for which key-derivation function protects the vault: the same call also
    // offers Argon2i, which is not what this project specified.
    final SecureKey key = _pwhash.callStr(
      outLen: keyLength,
      password: masterPassword,
      salt: salt,
      opsLimit: parameters.opsLimit,
      memLimit: parameters.memLimitBytes,
      alg: CryptoPwhashAlgorithm.argon2id13,
    );
    return _SodiumVaultKey(key);
  }

  @override
  Uint8List seal({
    required Uint8List plaintext,
    required Uint8List nonce,
    required VaultKey key,
    required Uint8List associatedData,
  }) {
    _requireNonceLength(nonce);
    return _aead.encrypt(
      message: plaintext,
      nonce: nonce,
      key: _unwrap(key),
      additionalData: associatedData,
    );
  }

  @override
  Uint8List open({
    required Uint8List ciphertext,
    required Uint8List nonce,
    required VaultKey key,
    required Uint8List associatedData,
  }) {
    _requireNonceLength(nonce);
    if (ciphertext.length < tagLength) {
      throw const VaultFormatFailure(
        'This vault file is truncated: the encrypted section is too short to '
        'carry an authentication tag.',
      );
    }
    try {
      return _aead.decrypt(
        cipherText: ciphertext,
        nonce: nonce,
        key: _unwrap(key),
        additionalData: associatedData,
      );
    } on SodiumException {
      // Deliberately collapsed into one failure. A wrong password and an
      // altered file are indistinguishable here on purpose: telling them apart
      // would tell an attacker holding the file whether a guess was close.
      throw const VaultAuthenticationFailure();
    }
  }

  void _requireNonceLength(Uint8List nonce) {
    if (nonce.length != nonceLength) {
      throw VaultFormatFailure(
        'The vault nonce is ${nonce.length} bytes; '
        '$nonceLength were expected.',
      );
    }
  }

  SecureKey _unwrap(VaultKey key) {
    if (key is _SodiumVaultKey) {
      return key._key;
    }
    throw ArgumentError.value(
      key,
      'key',
      'This key was not produced by SodiumCryptoService',
    );
  }
}

/// A libsodium [SecureKey] presented as a [VaultKey].
///
/// libsodium keeps this key in memory it locks against being swapped to disk
/// and zeroes when disposed, which is why key material is never copied out of
/// it.
final class _SodiumVaultKey implements VaultKey {
  _SodiumVaultKey(this._key);

  final SecureKey _key;

  @override
  int get length => _key.length;

  @override
  void dispose() => _key.dispose();
}
