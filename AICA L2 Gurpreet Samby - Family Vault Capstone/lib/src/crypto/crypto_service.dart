import 'dart:typed_data';

import 'kdf_parameters.dart';

/// A derived encryption key, held so that it can be wiped.
///
/// The underlying bytes live in memory the cryptographic library locks and
/// zeroes on [dispose]. Nothing in this project copies a key out of one of
/// these: the key is used in place and then discarded.
abstract interface class VaultKey {
  /// Length of the key in bytes.
  int get length;

  /// Wipes the key material. Safe to call more than once.
  void dispose();
}

/// The cryptographic operations a vault needs, and nothing else.
///
/// This interface exists so that the rest of the application never imports a
/// cryptography library directly. Two consequences matter:
///
/// The vault format, the repository and the interface layers can be read and
/// reviewed without knowing which library is underneath, and the library can
/// be replaced without touching them.
///
/// Nothing above this line can reach a primitive it should not, such as a
/// raw cipher without authentication.
///
/// Implementations must never write key material, password text or plaintext
/// to a log, and must never implement a primitive themselves.
abstract interface class CryptoService {
  /// Required salt length in bytes, as the key-derivation function defines it.
  int get saltLength;

  /// Required nonce length in bytes, as the cipher defines it.
  int get nonceLength;

  /// Derived key length in bytes.
  int get keyLength;

  /// Length of the authentication tag the cipher appends, in bytes.
  int get tagLength;

  /// Cost parameters this build uses for a new vault.
  ///
  /// Taken from the cryptographic library's own guidance rather than
  /// hard-coded here, so that it tracks that guidance as the library is
  /// updated.
  Argon2idParameters get recommendedParameters;

  /// Cryptographically secure random bytes.
  ///
  /// Used for salts and nonces. Never for anything that needs to be
  /// reproducible.
  Uint8List randomBytes(int length);

  /// Derives a key from a master password using Argon2id.
  ///
  /// [parameters] must already have been validated. Callers get a key they own
  /// and must dispose.
  VaultKey deriveKey({
    required String masterPassword,
    required Uint8List salt,
    required Argon2idParameters parameters,
  });

  /// Encrypts [plaintext], authenticating [associatedData] alongside it.
  ///
  /// [associatedData] is the vault header. It is not encrypted — it cannot be,
  /// since it carries the parameters needed to derive the key — but including
  /// it here means any change to it invalidates the file.
  ///
  /// The returned bytes include the authentication tag.
  Uint8List seal({
    required Uint8List plaintext,
    required Uint8List nonce,
    required VaultKey key,
    required Uint8List associatedData,
  });

  /// Decrypts [ciphertext], verifying it and [associatedData].
  ///
  /// Throws `VaultAuthenticationFailure` if verification fails, for any
  /// reason. Implementations must not report *why* it failed and must never
  /// return unverified plaintext.
  Uint8List open({
    required Uint8List ciphertext,
    required Uint8List nonce,
    required VaultKey key,
    required Uint8List associatedData,
  });
}
