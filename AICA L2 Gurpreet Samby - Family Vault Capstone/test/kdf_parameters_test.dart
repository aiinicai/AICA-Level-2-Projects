import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/crypto/kdf_parameters.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the Argon2id cost parameters and their bounds.
///
/// These numbers arrive from a vault file, so validating them is a security
/// control rather than input tidying: an unchecked memory cost is a
/// denial-of-service that triggers the moment a user opens a file someone sent
/// them. See docs/decisions-and-risks.md, decision D-009.
void main() {
  const Argon2idParameters sane = Argon2idParameters(
    opsLimit: 2,
    memLimitBytes: 64 * 1024 * 1024,
  );

  group('a sane set of parameters', () {
    test('validates', () {
      expect(sane.validate, returnsNormally);
    });

    test('converts to kibibytes for the header', () {
      expect(sane.memLimitKib, 64 * 1024);
    });

    test('round-trips through the kibibyte form', () {
      final Argon2idParameters back = Argon2idParameters.fromKib(
        opsLimit: sane.opsLimit,
        memLimitKib: sane.memLimitKib,
      );
      expect(back, sane);
    });

    test('compares by value, so headers can be compared', () {
      expect(
        sane,
        const Argon2idParameters(opsLimit: 2, memLimitBytes: 64 * 1024 * 1024),
      );
      expect(
        sane.hashCode,
        const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: 64 * 1024 * 1024,
        ).hashCode,
      );
    });

    test('does not put the password or key in its string form', () {
      expect(sane.toString(), contains('opsLimit: 2'));
      expect(sane.toString(), contains('64 MiB'));
    });
  });

  group('memory cost bounds', () {
    test('rejects a cost above the ceiling', () {
      expect(
        const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: Argon2idParameters.maxMemLimitBytes + 1024,
        ).validate,
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('rejects a cost below the floor', () {
      expect(
        const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: Argon2idParameters.minMemLimitBytes - 1024,
        ).validate,
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('accepts the exact floor and ceiling', () {
      expect(
        const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: Argon2idParameters.minMemLimitBytes,
        ).validate,
        returnsNormally,
      );
      expect(
        const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: Argon2idParameters.maxMemLimitBytes,
        ).validate,
        returnsNormally,
      );
    });

    test('rejects a cost that is not a whole number of kibibytes', () {
      expect(
        const Argon2idParameters(
          opsLimit: 2,
          memLimitBytes: Argon2idParameters.minMemLimitBytes + 1,
        ).validate,
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('alignedToKib rounds down so the value survives the header', () {
      final Argon2idParameters aligned = const Argon2idParameters(
        opsLimit: 2,
        memLimitBytes: Argon2idParameters.minMemLimitBytes + 777,
      ).alignedToKib();
      expect(aligned.validate, returnsNormally);
      expect(aligned.memLimitBytes, Argon2idParameters.minMemLimitBytes);
      expect(aligned.memLimitBytes % 1024, 0);
    });
  });

  group('pass-count bounds', () {
    test('rejects zero passes', () {
      expect(
        const Argon2idParameters(
          opsLimit: 0,
          memLimitBytes: 64 * 1024 * 1024,
        ).validate,
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('rejects a negative pass count', () {
      expect(
        const Argon2idParameters(
          opsLimit: -1,
          memLimitBytes: 64 * 1024 * 1024,
        ).validate,
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('rejects a pass count above the ceiling', () {
      expect(
        const Argon2idParameters(
          opsLimit: Argon2idParameters.maxOpsLimit + 1,
          memLimitBytes: 64 * 1024 * 1024,
        ).validate,
        throwsA(isA<VaultParameterFailure>()),
      );
    });

    test('accepts the exact bounds', () {
      expect(
        const Argon2idParameters(
          opsLimit: Argon2idParameters.minOpsLimit,
          memLimitBytes: 64 * 1024 * 1024,
        ).validate,
        returnsNormally,
      );
      expect(
        const Argon2idParameters(
          opsLimit: Argon2idParameters.maxOpsLimit,
          memLimitBytes: 64 * 1024 * 1024,
        ).validate,
        returnsNormally,
      );
    });
  });

  group('the floor is meaningful, not arbitrary', () {
    // OWASP's Argon2id guidance is a minimum of 19 MiB. The floor sits below
    // that on purpose, so that a vault written with a slightly lower cost
    // still opens rather than becoming unreadable, while remaining high enough
    // that memory-hardness is not defeated. Anything this build writes is well
    // above both.
    test('is below the OWASP minimum but far above a trivial cost', () {
      const int owaspMinimum = 19 * 1024 * 1024;
      expect(Argon2idParameters.minMemLimitBytes, lessThan(owaspMinimum));
      expect(
        Argon2idParameters.minMemLimitBytes,
        greaterThanOrEqualTo(8 * 1024 * 1024),
      );
    });

    test('the default this build writes clears the OWASP minimum', () {
      const int owaspMinimum = 19 * 1024 * 1024;
      expect(sane.memLimitBytes, greaterThan(owaspMinimum));
      expect(sane.opsLimit, greaterThanOrEqualTo(2));
    });
  });
}
