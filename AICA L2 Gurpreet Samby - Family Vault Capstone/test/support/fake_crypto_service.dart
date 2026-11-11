import 'dart:convert';
import 'dart:typed_data';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/crypto/crypto_service.dart';
import 'package:family_vault/src/crypto/kdf_parameters.dart';

/// A stand-in [CryptoService] for testing the vault format's plumbing.
///
/// THIS IS NOT CRYPTOGRAPHY AND MUST NEVER BE USED OUTSIDE A TEST.
///
/// It exists so that the parts of the format that have nothing to do with
/// cryptography — field layout, bounds checking, truncation handling, ordering
/// of operations, whether keys get disposed — can be tested quickly and
/// deterministically, without a native library.
///
/// It deliberately does not stand in for a security test. Whether tampering is
/// actually detected, and whether a wrong password actually fails, are
/// properties of the real cipher and are tested against real libsodium in
/// crypto_security_test.dart. A fake can only show that the wiring is right.
final class FakeCryptoService implements CryptoService {
  FakeCryptoService({this.randomFill = 0x11});

  /// Byte used to fill "random" output, so salts and nonces are predictable.
  int randomFill;

  /// Every call made to [randomBytes], in order, for assertions about nonce
  /// freshness.
  final List<int> randomCallLengths = <int>[];

  /// Number of keys derived, and how many were disposed. A difference means a
  /// key was leaked, which is the bug this exists to catch.
  int keysDerived = 0;
  int keysDisposed = 0;

  @override
  int get saltLength => 16;

  @override
  int get nonceLength => 24;

  @override
  int get keyLength => 32;

  @override
  int get tagLength => 16;

  @override
  Argon2idParameters get recommendedParameters =>
      const Argon2idParameters(opsLimit: 2, memLimitBytes: 64 * 1024 * 1024);

  @override
  Uint8List randomBytes(int length) {
    randomCallLengths.add(length);
    // Varies with each call so a repeated nonce is visible in a test.
    final int fill = (randomFill + randomCallLengths.length) & 0xFF;
    return Uint8List(length)..fillRange(0, length, fill);
  }

  @override
  VaultKey deriveKey({
    required String masterPassword,
    required Uint8List salt,
    required Argon2idParameters parameters,
  }) {
    parameters.validate();
    if (salt.length != saltLength) {
      throw VaultFormatFailure(
        'The vault salt is ${salt.length} bytes; $saltLength were expected.',
      );
    }
    keysDerived++;
    return _FakeVaultKey(
      _fold(utf8.encode(masterPassword)) ^ _fold(salt),
      () => keysDisposed++,
    );
  }

  @override
  Uint8List seal({
    required Uint8List plaintext,
    required Uint8List nonce,
    required VaultKey key,
    required Uint8List associatedData,
  }) {
    final int mask = (key as _FakeVaultKey).mask & 0xFF;
    final Uint8List out = Uint8List(plaintext.length + tagLength);
    for (int i = 0; i < plaintext.length; i++) {
      out[i] = plaintext[i] ^ mask;
    }
    final int tag = _fold(associatedData) ^ _fold(plaintext) ^ mask;
    for (int i = 0; i < tagLength; i++) {
      out[plaintext.length + i] = (tag >> (i % 4 * 8)) & 0xFF;
    }
    return out;
  }

  @override
  Uint8List open({
    required Uint8List ciphertext,
    required Uint8List nonce,
    required VaultKey key,
    required Uint8List associatedData,
  }) {
    if (ciphertext.length < tagLength) {
      throw const VaultFormatFailure('Too short to carry a tag.');
    }
    final int mask = (key as _FakeVaultKey).mask & 0xFF;
    final int bodyLength = ciphertext.length - tagLength;
    final Uint8List body = Uint8List(bodyLength);
    for (int i = 0; i < bodyLength; i++) {
      body[i] = ciphertext[i] ^ mask;
    }
    final int expected = _fold(associatedData) ^ _fold(body) ^ mask;
    for (int i = 0; i < tagLength; i++) {
      final int want = (expected >> (i % 4 * 8)) & 0xFF;
      if (ciphertext[bodyLength + i] != want) {
        throw const VaultAuthenticationFailure();
      }
    }
    return body;
  }

  /// A small non-cryptographic fold, standing in for a real tag.
  static int _fold(List<int> data) {
    int h = 0x811C9DC5;
    for (final int b in data) {
      h = ((h ^ b) * 0x01000193) & 0x7FFFFFFF;
    }
    return h;
  }
}

final class _FakeVaultKey implements VaultKey {
  _FakeVaultKey(this.mask, this._onDispose);

  final int mask;
  final void Function() _onDispose;
  bool _disposed = false;

  @override
  int get length => 32;

  @override
  void dispose() {
    if (!_disposed) {
      _disposed = true;
      _onDispose();
    }
  }
}
