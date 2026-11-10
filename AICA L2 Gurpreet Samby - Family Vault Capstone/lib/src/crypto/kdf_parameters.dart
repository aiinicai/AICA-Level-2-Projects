import 'package:meta/meta.dart';

import '../core/failures.dart';

/// Argon2id cost parameters for turning a master password into a key.
///
/// These are stored in the vault header in plain text, because they are what
/// tells the application how to re-derive the key. They are covered by the
/// authentication tag, so altering them invalidates the file rather than
/// weakening it (decision D-008).
///
/// Values are validated against the bounds below before any memory is
/// allocated, because they arrive from a file and a file can be hostile
/// (decision D-009).
@immutable
final class Argon2idParameters {
  const Argon2idParameters({
    required this.opsLimit,
    required this.memLimitBytes,
  });

  /// Number of passes. Argon2's time cost.
  final int opsLimit;

  /// Memory cost in bytes. Argon2's defence against custom hardware: an
  /// attacker needs this much memory per guess, not merely this much compute.
  final int memLimitBytes;

  /// Smallest number of passes this build will act on.
  static const int minOpsLimit = 1;

  /// Largest number of passes this build will act on.
  ///
  /// A ceiling rather than a recommendation. Argon2 guidance is to raise
  /// memory before passes, so a header asking for hundreds of passes is more
  /// likely hostile or corrupt than deliberate.
  static const int maxOpsLimit = 64;

  /// Smallest memory cost this build will act on: 8 MiB.
  ///
  /// Below this, Argon2id's memory-hardness stops being meaningful. libsodium
  /// itself permits far less, but nothing this application writes will ever be
  /// that low, so a file below the floor is either corrupt or was not written
  /// by Family Vault.
  static const int minMemLimitBytes = 8 * 1024 * 1024;

  /// Largest memory cost this build will act on: 1 GiB.
  ///
  /// This is the denial-of-service guard. Without it, a header could ask the
  /// application to allocate more memory than the device has, and merely
  /// opening a file would crash it.
  static const int maxMemLimitBytes = 1024 * 1024 * 1024;

  /// Memory cost rounded to whole kibibytes.
  ///
  /// The header stores kibibytes rather than bytes so the field fits in 32
  /// bits. 64-bit integers are not available on the web, and the public
  /// demonstration is a web build.
  int get memLimitKib => memLimitBytes ~/ 1024;

  /// Builds parameters from a kibibyte value read from a header.
  factory Argon2idParameters.fromKib({
    required int opsLimit,
    required int memLimitKib,
  }) =>
      Argon2idParameters(opsLimit: opsLimit, memLimitBytes: memLimitKib * 1024);

  /// Throws [VaultParameterFailure] unless both values are within the bounds
  /// above and the memory cost is a whole number of kibibytes.
  ///
  /// Call this before allocating anything.
  void validate() {
    if (opsLimit < minOpsLimit || opsLimit > maxOpsLimit) {
      throw VaultParameterFailure(
        'The vault asks for $opsLimit key-derivation passes, which is outside '
        'the supported range of $minOpsLimit to $maxOpsLimit.',
      );
    }
    if (memLimitBytes < minMemLimitBytes || memLimitBytes > maxMemLimitBytes) {
      throw VaultParameterFailure(
        'The vault asks for ${memLimitBytes ~/ (1024 * 1024)} MiB of '
        'key-derivation memory, which is outside the supported range of '
        '${minMemLimitBytes ~/ (1024 * 1024)} to '
        '${maxMemLimitBytes ~/ (1024 * 1024)} MiB.',
      );
    }
    if (memLimitBytes % 1024 != 0) {
      throw const VaultParameterFailure(
        'The key-derivation memory cost must be a whole number of kibibytes.',
      );
    }
  }

  /// A copy with the memory cost rounded down to a whole kibibyte, so that it
  /// survives a round trip through the header unchanged.
  Argon2idParameters alignedToKib() => Argon2idParameters(
    opsLimit: opsLimit,
    memLimitBytes: (memLimitBytes ~/ 1024) * 1024,
  );

  @override
  bool operator ==(Object other) =>
      other is Argon2idParameters &&
      other.opsLimit == opsLimit &&
      other.memLimitBytes == memLimitBytes;

  @override
  int get hashCode => Object.hash(opsLimit, memLimitBytes);

  @override
  String toString() =>
      'Argon2idParameters(opsLimit: $opsLimit, '
      'memLimit: ${memLimitBytes ~/ (1024 * 1024)} MiB)';
}
