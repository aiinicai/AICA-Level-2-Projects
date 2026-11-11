import 'package:flutter/material.dart';

import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/password_health.dart';
import '../../domain/vault_data.dart';
import '../items/item_detail_screen.dart';

/// The password-health report.
///
/// Runs on the decrypted vault in memory. No password, and no hash of one,
/// leaves the device: the optional breach check that does use the network is a
/// separate, off-by-default Phase 2 feature.
class HealthView extends StatelessWidget {
  const HealthView({super.key});

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      return const SizedBox.shrink();
    }
    final ThemeData theme = Theme.of(context);
    final HealthReport report = PasswordHealth.check(data);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        report.passwordsChecked == 0
                            ? 'Nothing to check yet'
                            : '${report.score} out of 100',
                        style: theme.textTheme.headlineMedium,
                      ),
                    ),
                    Icon(
                      report.isClean
                          ? Icons.verified_outlined
                          : Icons.shield_outlined,
                      size: 40,
                      color: report.isClean
                          ? theme.colorScheme.primary
                          : theme.colorScheme.error,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(report.summary, style: theme.textTheme.bodyLarge),
                const SizedBox(height: 12),
                Text(
                  'Checked on this device. Nothing was sent anywhere.',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        if (report.issues.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 24),
            child: Column(
              children: <Widget>[
                Icon(
                  Icons.check_circle_outline,
                  size: 48,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(height: 12),
                Text(
                  report.passwordsChecked == 0
                      ? 'Save some logins and this report will tell you which '
                            'passwords need attention.'
                      : 'Nothing needs attention. Worth checking again after '
                            'you add new accounts.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          )
        else
          for (final HealthIssue issue in report.issues)
            _IssueCard(issue: issue),
      ],
    );
  }
}

class _IssueCard extends StatelessWidget {
  const _IssueCard({required this.issue});

  final HealthIssue issue;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color colour = switch (issue.severity) {
      HealthSeverity.high => theme.colorScheme.error,
      HealthSeverity.medium => theme.colorScheme.tertiary,
      HealthSeverity.low => theme.colorScheme.outline,
    };

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (BuildContext context) =>
                ItemDetailScreen(itemId: issue.item.id),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: colour.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      issue.kind.label,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: colour,
                      ),
                    ),
                  ),
                  const Spacer(),
                  Text(issue.severity.label, style: theme.textTheme.labelSmall),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                issue.item.title,
                style: theme.textTheme.titleMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(issue.advice, style: theme.textTheme.bodyMedium),
            ],
          ),
        ),
      ),
    );
  }
}
