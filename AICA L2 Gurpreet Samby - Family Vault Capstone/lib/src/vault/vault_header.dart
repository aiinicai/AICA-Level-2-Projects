import 'dart:typed_data';

import 'package:meta/meta.dart';

import '../core/failures.dart';
import '../crypto/kdf_parameters.dart';

/// The plaintext header at the start of every vault file.
///
/// Layout, big-endian, all offsets in bytes:
///
/// ```text
///  offset size field
///       0    4 magic, "FVLT"
///       4    2 format version
///       6    1 key-derivation algorithm id
///       7    1 cipher id
///       8    4 Argon2id passes (opsLimit)
///      12    4 Argon2id memory cost, kibibytes
///      16    1 salt length
///      17    1 nonce length
///      18    2 reserved, must be zero
///      20    N salt
///    20+N    M nonce
/// ```
///
/// Two deliberate choices:
///
/// Nothing here describes the vault's contents. No title, no URL, no item
/// count. Only what is needed to derive the key and recognise the format.
///
/// Memory cost is stored in kibibytes rather than bytes so the field fits in
/// 32 bits. The web has no 64-bit integers, and the public demonstration is a
/// web build, so a 64-bit field would not survive there.
///
/// The whole header is passed to the cipher as associated data, so changing
/// any byte of it makes the file fail to authenticate. That matters most for
/// the cost parameters: an attacker cannot lower them to make guessing
/// cheaper. See docs/decisions-and-risks.md, decision D-008.
@immutable
final class VaultHeader {
  const VaultHeader({
    required this.formatVersion,
    required this.kdfAlgorithm,
    required this.cipher,
    required this.kdfParameters,
    required this.salt,
    required this.nonce,
  });

  /// Magic bytes identifying a Family Vault file: `FVLT`.
  static const List<int> magic = <int>[0x46, 0x56, 0x4C, 0x54];

  /// Format version this build writes.
  static const int currentFormatVersion = 1;

  /// Fixed part of the header, before the salt and nonce.
  static const int fixedLength = 20;

  /// Offsets of each fixed field.
  static const int _offsetVersion = 4;
  static const int _offsetKdfAlgorithm = 6;
  static const int _offsetCipher = 7;
  static const int _offsetOpsLimit = 8;
  static const int _offsetMemLimitKib = 12;
  static const int _offsetSaltLength = 16;
  static const int _offsetNonceLength = 17;
  static const int _offsetReserved = 18;

  /// Version of the on-disk layout.
  final int formatVersion;

  /// Which key-derivation function produced the key.
  final KdfAlgorithmId kdfAlgorithm;

  /// Which authenticated cipher sealed the payload.
  final CipherId cipher;

  /// Argon2id cost parameters.
  final Argon2idParameters kdfParameters;

  /// Per-vault random salt. Never reused between vaults.
  final Uint8List salt;

  /// Per-write random nonce. Never reused under the same key.
  final Uint8List nonce;

  /// Total length of this header once encoded.
  int get length => fixedLength + salt.length + nonce.length;

  /// Encodes the header to bytes.
  ///
  /// The result is both the start of the file and the associated data handed to
  /// the cipher, so this must be deterministic.
  Uint8List encode() {
    final Uint8List bytes = Uint8List(length);
    final ByteData view = ByteData.sublistView(bytes);

    bytes.setRange(0, magic.length, magic);
    view.setUint16(_offsetVersion, formatVersion);
    bytes[_offsetKdfAlgorithm] = kdfAlgorithm.id;
    bytes[_offsetCipher] = cipher.id;
    view.setUint32(_offsetOpsLimit, kdfParameters.opsLimit);
    view.setUint32(_offsetMemLimitKib, kdfParameters.memLimitKib);
    bytes[_offsetSaltLength] = salt.length;
    bytes[_offsetNonceLength] = nonce.length;
    // Reserved bytes stay zero; Uint8List is zero-filled on creation.
    view.setUint16(_offsetReserved, 0);
    bytes.setRange(fixedLength, fixedLength + salt.length, salt);
    bytes.setRange(
      fixedLength + salt.length,
      fixedLength + salt.length + nonce.length,
      nonce,
    );
    return bytes;
  }

  /// Reads a header from the start of [bytes].
  ///
  /// Validates before trusting: magic, version, algorithm identifiers,
  /// reserved bytes, declared lengths against the available data, and the
  /// Argon2id cost parameters against their permitted range. Every failure is
  /// a typed [VaultFailure], never a [RangeError] escaping from a short read.
  static VaultHeader decode(Uint8List bytes) {
    if (bytes.length < fixedLength) {
      throw const VaultFormatFailure(
        'This file is too short to be a Family Vault file.',
      );
    }
    for (int i = 0; i < magic.length; i++) {
      if (bytes[i] != magic[i]) {
        throw const VaultFormatFailure('This is not a Family Vault file.');
      }
    }

    final ByteData view = ByteData.sublistView(bytes);
    final int version = view.getUint16(_offsetVersion);
    if (version != currentFormatVersion) {
      throw VaultVersionFailure(
        version > currentFormatVersion
            ? 'This vault was created by a newer version of Family Vault. '
                  'Please update the app to open it.'
            : 'This vault uses an old format (version $version) that this '
                  'build no longer reads.',
        fileVersion: version,
      );
    }

    final KdfAlgorithmId kdf = KdfAlgorithmId.fromId(
      bytes[_offsetKdfAlgorithm],
    );
    final CipherId cipher = CipherId.fromId(bytes[_offsetCipher]);

    if (view.getUint16(_offsetReserved) != 0) {
      throw const VaultFormatFailure(
        'This vault file has unexpected content in a reserved field.',
      );
    }

    final int saltLength = bytes[_offsetSaltLength];
    final int nonceLength = bytes[_offsetNonceLength];
    if (saltLength == 0 || nonceLength == 0) {
      throw const VaultFormatFailure(
        'This vault file declares an empty salt or nonce.',
      );
    }
    final int headerLength = fixedLength + saltLength + nonceLength;
    if (bytes.length < headerLength) {
      throw const VaultFormatFailure(
        'This vault file is truncated: its header is incomplete.',
      );
    }

    // Parameters are validated before they are ever used to size an
    // allocation. See decision D-009.
    final Argon2idParameters parameters = Argon2idParameters.fromKib(
      opsLimit: view.getUint32(_offsetOpsLimit),
      memLimitKib: view.getUint32(_offsetMemLimitKib),
    )..validate();

    return VaultHeader(
      formatVersion: version,
      kdfAlgorithm: kdf,
      cipher: cipher,
      kdfParameters: parameters,
      // Copied rather than viewed: a view would stay tied to the caller's
      // buffer, so mutating that buffer would silently change the header.
      salt: Uint8List.fromList(
        bytes.sublist(fixedLength, fixedLength + saltLength),
      ),
      nonce: Uint8List.fromList(
        bytes.sublist(fixedLength + saltLength, headerLength),
      ),
    );
  }
}

/// Key-derivation functions this format can describe.
enum KdfAlgorithmId {
  /// Argon2id, version 1.3. The only one this build writes.
  argon2id13(1);

  const KdfAlgorithmId(this.id);

  /// Value stored in the header.
  final int id;

  /// Maps a stored value back to an algorithm, rejecting anything unknown.
  static KdfAlgorithmId fromId(int id) {
    for (final KdfAlgorithmId value in KdfAlgorithmId.values) {
      if (value.id == id) {
        return value;
      }
    }
    throw VaultFormatFailure(
      'This vault uses an unknown key-derivation algorithm (id $id).',
    );
  }
}

/// Authenticated ciphers this format can describe.
enum CipherId {
  /// XChaCha20-Poly1305, IETF construction. The only one this build writes.
  ///
  /// Chosen over AES-256-GCM for its 192-bit nonce: a nonce that long can be
  /// generated at random for every write without a realistic chance of repeat,
  /// which removes the counter-management mistake that breaks GCM.
  xChaCha20Poly1305Ietf(1);

  const CipherId(this.id);

  /// Value stored in the header.
  final int id;

  /// Maps a stored value back to a cipher, rejecting anything unknown.
  static CipherId fromId(int id) {
    for (final CipherId value in CipherId.values) {
      if (value.id == id) {
        return value;
      }
    }
    throw VaultFormatFailure(
      'This vault uses an unknown encryption algorithm (id $id).',
    );
  }
}
