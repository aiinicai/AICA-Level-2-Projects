import 'package:family_vault/src/domain/password_health.dart';
import 'package:family_vault/src/domain/vault_data.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the password-health check.
///
/// The judgements this makes are advice a non-technical person will act on, so
/// they have to be right in the ways that matter: length must count for more
/// than character variety, reuse must be reported on every entry involved
/// rather than just one, and nothing may leave the device.
void main() {
  final DateTime now = DateTime.utc(2026, 11, 9);

  VaultItem login(
    String title,
    String password, {
    String url = 'https://example.com',
    String totp = '',
    DateTime? passwordAge,
  }) => VaultItem.create(
    type: VaultItemType.login,
    title: title,
    fields: <String, String>{
      ItemField.password: password,
      ItemField.url: url,
      if (totp.isNotEmpty) ItemField.totpSecret: totp,
    },
    now: passwordAge ?? now,
  );

  VaultData vaultOf(List<VaultItem> items) {
    VaultData data = VaultData.empty;
    for (final VaultItem item in items) {
      data = data.upsertItem(item);
    }
    return data;
  }

  group('an empty vault', () {
    test('is clean and scores 100', () {
      final HealthReport report = PasswordHealth.check(
        VaultData.empty,
        now: now,
      );
      expect(report.isClean, isTrue);
      expect(report.score, 100);
      expect(report.passwordsChecked, 0);
      expect(report.summary, 'No passwords saved yet.');
    });
  });

  group('weak passwords', () {
    test('flags one that is far too short', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'abc12')]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.weak), 1);
      expect(
        report.ofKind(HealthIssueKind.weak).single.severity,
        HealthSeverity.high,
      );
    });

    test('flags a single repeated character', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'aaaaaaaaaaaaaa')]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.weak), 1);
    });

    test('flags a simple sequence', () {
      for (final String sequence in <String>['123456789012', 'abcdefghijkl']) {
        final HealthReport report = PasswordHealth.check(
          vaultOf(<VaultItem>[login('Bank', sequence)]),
          now: now,
        );
        expect(
          report.countOf(HealthIssueKind.weak),
          1,
          reason: 'should flag "$sequence"',
        );
      }
    });

    // This is the judgement that matters most. Length beats variety: a long
    // all-lowercase passphrase is stronger than a short password with a
    // symbol in it, and a checker that said otherwise would push people
    // towards the weaker choice.
    test('accepts a long passphrase of only lower-case letters', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'correcthorsebatterystaple')]),
        now: now,
      );
      expect(
        report.countOf(HealthIssueKind.weak),
        0,
        reason: 'a 25-character passphrase is not weak',
      );
    });

    test('accepts a generated-looking password', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', r'K7#mQ2$vLp9!xRt4')]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.weak), 0);
    });

    test('flags a short password even with mixed character types', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'Ab1!')]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.weak), 1);
    });
  });

  group('reused passwords', () {
    test('are reported on every entry involved, not just one', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login('Bank', 'SharedPassword99!'),
          login('Shop', 'SharedPassword99!'),
          login('Email', 'SharedPassword99!'),
        ]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.reused), 3);
    });

    test('say how many others share it', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login('Bank', 'SharedPassword99!'),
          login('Shop', 'SharedPassword99!'),
        ]),
        now: now,
      );
      expect(
        report.ofKind(HealthIssueKind.reused).first.advice,
        contains('one other entry'),
      );
    });

    test('are not reported when every password is unique', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login('Bank', 'UniqueOne99!xyz'),
          login('Shop', 'UniqueTwo99!xyz'),
        ]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.reused), 0);
    });

    test('a trashed entry does not count as reuse', () {
      VaultData data = vaultOf(<VaultItem>[
        login('Bank', 'SharedPassword99!'),
        login('Old', 'SharedPassword99!'),
      ]);
      data = data.trashItem(data.search('Old').first.id);
      final HealthReport report = PasswordHealth.check(data, now: now);
      expect(
        report.countOf(HealthIssueKind.reused),
        0,
        reason: 'a deleted entry is not an account you still hold',
      );
    });
  });

  group('old passwords', () {
    test('are flagged after a year', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login(
            'Bank',
            'StillAGoodPassword99!',
            passwordAge: now.subtract(const Duration(days: 400)),
          ),
        ]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.old), 1);
      expect(
        report.ofKind(HealthIssueKind.old).single.severity,
        HealthSeverity.low,
      );
    });

    test('are not flagged when recent', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login(
            'Bank',
            'StillAGoodPassword99!',
            passwordAge: now.subtract(const Duration(days: 30)),
          ),
        ]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.old), 0);
    });
  });

  group('missing passwords and two-factor', () {
    test('a login with no password is flagged', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', '')]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.missing), 1);
      expect(report.passwordsChecked, 0);
    });

    test('a site login with no authenticator key is noted gently', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'AGoodPassword99!xyz')]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.noTwoFactor), 1);
      expect(
        report.ofKind(HealthIssueKind.noTwoFactor).single.severity,
        HealthSeverity.low,
      );
    });

    test('an authenticator key already stored is not flagged', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login('Bank', 'AGoodPassword99!xyz', totp: 'GEZDGNBVGY3TQOJQ'),
        ]),
        now: now,
      );
      expect(report.countOf(HealthIssueKind.noTwoFactor), 0);
    });
  });

  group('other item types', () {
    test('notes, cards and identities are not judged as passwords', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          VaultItem.create(
            type: VaultItemType.secureNote,
            title: 'placeholder',
          ),
        ]),
        now: now,
      );
      expect(report.issues, isEmpty);
    });
  });

  group('the score and summary', () {
    test('drops sharply for a high-severity problem', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'abc12')]),
        now: now,
      );
      expect(report.score, lessThan(95));
    });

    test('never goes below zero', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          for (int i = 0; i < 40; i++) login('Site $i', 'abc12'),
        ]),
        now: now,
      );
      expect(report.score, 0);
    });

    test('is 100 for a clean vault', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login('Bank', r'K7#mQ2$vLp9!xRt4', totp: 'GEZDGNBVGY3TQOJQ'),
        ]),
        now: now,
      );
      expect(report.isClean, isTrue);
      expect(report.score, 100);
    });

    test('summarises in plain language, with no jargon', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[login('Bank', 'abc12')]),
        now: now,
      );
      expect(report.summary, '1 password needs changing now.');
    });
  });

  group('ordering', () {
    test('puts the worst problems first', () {
      final HealthReport report = PasswordHealth.check(
        vaultOf(<VaultItem>[
          login('Weak', 'abc12'),
          login(
            'Old',
            'StillAGoodPassword99!',
            passwordAge: now.subtract(const Duration(days: 500)),
          ),
        ]),
        now: now,
      );
      expect(report.issues.first.severity, HealthSeverity.high);
      expect(report.issues.last.severity, HealthSeverity.low);
    });
  });
}
