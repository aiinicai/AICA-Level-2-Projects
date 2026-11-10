import 'dart:typed_data';

import 'package:meta/meta.dart';

import '../core/failures.dart';
import '../crypto/crypto_service.dart';
import '../crypto/kdf_parameters.dart';
import 'vault_header.dart';

/// A derived key together with everything needed to write the vault again.
///
/// This exists so that an unlocked vault does not have to keep the master
/// password in memory. A Dart [String] cannot be wiped — it stays on the heap
/// until the garbage collector happens to reclaim it, and may be copied as it
/// moves — whereas the key inside [key] lives in memory the cryptographic
/// library locks against swapping and zeroes on demand.
///
/// So the password is used once, at unlock, and then only this survives.
final class VaultKeyring {
  VaultKeyring({
    required this.key,
    required this.salt,
    required this.parameters,
  });

  /// The derived key. Not copyable out.
  final VaultKey key;

  /// The vault's salt, kept so the same key can be re-derived if needed.
  final Uint8List salt;

  /// The cost parameters this vault was written with.
  final Argon2idParameters parameters;

  bool _disposed = false;

  /// True once [dispose] has run.
  bool get isDisposed => _disposed;

  /// Wipes the key. Safe to call more than once.
  void dispose() {
    if (!_disposed) {
      _disposed = true;
      key.dispose();
    }
  }
}

/// The result of unlocking a vault file.
@immutable
final class OpenedVault {
  const OpenedVault({required this.keyring, required this.payload});

  /// Key material for writing the vault again. The caller owns it and must
  /// dispose it when the vault locks.
  final VaultKeyring keyring;

  /// The decrypted payload.
  final Uint8List payload;
}

/// Turns a plaintext payload into a sealed vault file, and back.
///
/// The only place that knows how the two halves of a vault file fit together.
/// Holds no state of its own.
final class VaultCodec {
  const VaultCodec(this._crypto);

  final CryptoService _crypto;

  /// Derives key material for a brand-new vault.
  ///
  /// The salt is fresh, so this starts a new vault rather than continuing an
  /// existing one.
  VaultKeyring createKeyring({
    required String masterPassword,
    Argon2idParameters? parameters,
  }) {
    final Argon2idParameters costs =
        (parameters ?? _crypto.recommendedParameters).alignedToKib();
    costs.validate();
    final Uint8List salt = _crypto.randomBytes(_crypto.saltLength);
    return VaultKeyring(
      key: _crypto.deriveKey(
        masterPassword: masterPassword,
        salt: salt,
        parameters: costs,
      ),
      salt: salt,
      parameters: costs,
    );
  }

  /// Seals [payload] using key material already derived.
  ///
  /// A fresh nonce is drawn on every call, which is what keeps repeated writes
  /// under one key safe. With a 192-bit nonce, drawing it at random needs no
  /// counter — the reason this project uses XChaCha20-Poly1305.
  Uint8List sealWith({
    required VaultKeyring keyring,
    required Uint8List payload,
  }) {
    if (keyring.isDisposed) {
      throw StateError('The vault key has been wiped; unlock again to save.');
    }
    final Uint8List nonce = _crypto.randomBytes(_crypto.nonceLength);
    final Uint8List headerBytes = VaultHeader(
      formatVersion: VaultHeader.currentFormatVersion,
      kdfAlgorithm: KdfAlgorithmId.argon2id13,
      cipher: CipherId.xChaCha20Poly1305Ietf,
      kdfParameters: keyring.parameters,
      salt: keyring.salt,
      nonce: nonce,
    ).encode();

    final Uint8List ciphertext = _crypto.seal(
      plaintext: payload,
      nonce: nonce,
      key: keyring.key,
      associatedData: headerBytes,
    );
    final Uint8List file = Uint8List(headerBytes.length + ciphertext.length);
    file.setRange(0, headerBytes.length, headerBytes);
    file.setRange(headerBytes.length, file.length, ciphertext);
    return file;
  }

  /// Opens a vault file and keeps the key material for writing it again.
  ///
  /// The caller owns the returned keyring and must dispose it when locking.
  OpenedVault unlock({
    required Uint8List file,
    required String masterPassword,
  }) {
    final VaultHeader header = VaultHeader.decode(file);
    final int headerLength = header.length;
    if (file.length < headerLength + _crypto.tagLength) {
      throw const VaultFormatFailure(
        'This vault file is truncated: there is no complete encrypted section '
        'after the header.',
      );
    }

    // Authenticate the header bytes exactly as they appear on disk rather than
    // a re-encoded copy, so verification covers the real file.
    final Uint8List headerBytes = Uint8List.fromList(
      file.sublist(0, headerLength),
    );
    final Uint8List ciphertext = Uint8List.fromList(file.sublist(headerLength));

    final VaultKey key = _crypto.deriveKey(
      masterPassword: masterPassword,
      salt: header.salt,
      parameters: header.kdfParameters,
    );
    try {
      final Uint8List payload = _crypto.open(
        ciphertext: ciphertext,
        nonce: header.nonce,
        key: key,
        associatedData: headerBytes,
      );
      return OpenedVault(
        keyring: VaultKeyring(
          key: key,
          salt: header.salt,
          parameters: header.kdfParameters,
        ),
        payload: payload,
      );
    } on Object {
      // The caller never receives the keyring on failure, so this is the only
      // place that can wipe the key.
      key.dispose();
      rethrow;
    }
  }

  /// Seals [payload] into a complete vault file, deriving a key as it goes.
  ///
  /// Convenient for one-off writes such as an export. For ordinary saving use
  /// [createKeyring] once and then [sealWith], so the password is not needed
  /// again and the cost of key derivation is paid once.
  Uint8List seal({
    required String masterPassword,
    required Uint8List payload,
    Argon2idParameters? parameters,
    Uint8List? reuseSalt,
  }) {
    final Argon2idParameters costs =
        (parameters ?? _crypto.recommendedParameters).alignedToKib();
    costs.validate();
    final Uint8List salt = reuseSalt ?? _crypto.randomBytes(_crypto.saltLength);
    if (salt.length != _crypto.saltLength) {
      throw VaultFormatFailure(
        'The vault salt is ${salt.length} bytes; '
        '${_crypto.saltLength} were expected.',
      );
    }
    final VaultKeyring keyring = VaultKeyring(
      key: _crypto.deriveKey(
        masterPassword: masterPassword,
        salt: salt,
        parameters: costs,
      ),
      salt: salt,
      parameters: costs,
    );
    try {
      return sealWith(keyring: keyring, payload: payload);
    } finally {
      keyring.dispose();
    }
  }

  /// Opens a vault file and returns only its payload, wiping the key.
  ///
  /// For reading a vault once, such as an import.
  Uint8List open({required Uint8List file, required String masterPassword}) {
    final OpenedVault opened = unlock(
      file: file,
      masterPassword: masterPassword,
    );
    try {
      return opened.payload;
    } finally {
      opened.keyring.dispose();
    }
  }

  /// Reads a vault's header without needing the master password.
  ///
  /// Reveals nothing about the contents: the header holds only format and cost
  /// information.
  VaultHeader inspect(Uint8List file) => VaultHeader.decode(file);
}
