import 'package:flutter/material.dart';

import '../../app/navigation_plan.dart';
import '../../app/session_scope.dart';
import '../../app/vault_session.dart';
import '../../domain/password_health.dart';
import '../../domain/vault_data.dart';

/// Counts and the one thing most worth doing next.
///
/// Deliberately shows no secret and no entry name: a dashboard is what is on
/// screen when someone else walks past, so it carries numbers only.
class DashboardView extends StatelessWidget {
  const DashboardView({required this.onGo, super.key});

  /// Moves to another section when a card is tapped.
  final void Function(AppSection section) onGo;

  @override
  Widget build(BuildContext context) {
    final VaultSession session = SessionScope.of(context);
    final VaultData? data = session.data;
    if (data == null) {
      return const SizedBox.shrink();
    }
    final ThemeData theme = Theme.of(context);
    final HealthReport health = PasswordHealth.check(data);

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 88),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Your vault', style: theme.textTheme.titleMedium),
                const SizedBox(height: 4),
                Text(
                  data.liveItems.isEmpty
                      ? 'Nothing saved yet. Tap Add to save your first '
                            'password.'
                      : health.summary,
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: <Widget>[
            _CountCard(
              label: 'Items',
              value: '${data.liveItems.length}',
              icon: Icons.list_alt_outlined,
              onTap: () => onGo(AppSection.allItems),
            ),
            _CountCard(
              label: 'Folders',
              value: '${data.folders.length}',
              icon: Icons.folder_outlined,
              onTap: () => onGo(AppSection.folders),
            ),
            _CountCard(
              label: 'Favourites',
              value: '${data.favourites.length}',
              icon: Icons.star_outline,
              onTap: () => onGo(AppSection.favourites),
            ),
            _CountCard(
              label: 'Codes',
              value: '${data.authenticatorItems.length}',
              icon: Icons.timer_outlined,
              onTap: () => onGo(AppSection.authenticator),
            ),
          ],
        ),
        const SizedBox(height: 16),

        Text('Password health', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Card(
          child: InkWell(
            onTap: () => onGo(AppSection.health),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: Text(
                          health.passwordsChecked == 0
                              ? 'No passwords to check yet'
                              : 'Score ${health.score} out of 100',
                          style: theme.textTheme.titleLarge,
                        ),
                      ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _HealthRow(
                    label: 'Weak',
                    count: health.countOf(HealthIssueKind.weak),
                  ),
                  _HealthRow(
                    label: 'Reused',
                    count: health.countOf(HealthIssueKind.reused),
                  ),
                  _HealthRow(
                    label: 'Not changed in a year',
                    count: health.countOf(HealthIssueKind.old),
                  ),
                  _HealthRow(
                    label: 'Could add two-factor',
                    count: health.countOf(HealthIssueKind.noTwoFactor),
                  ),
                ],
              ),
            ),
          ),
        ),

        if (data.trashedItems.isNotEmpty) ...<Widget>[
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.delete_outline),
              title: Text(
                data.trashedItems.length == 1
                    ? '1 item in the trash'
                    : '${data.trashedItems.length} items in the trash',
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => onGo(AppSection.trash),
            ),
          ),
        ],
      ],
    );
  }
}

class _CountCard extends StatelessWidget {
  const _CountCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final String value;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return SizedBox(
      width: 160,
      child: Card(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Icon(icon, color: theme.colorScheme.primary),
                const SizedBox(height: 8),
                Text(value, style: theme.textTheme.headlineMedium),
                Text(label, style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HealthRow extends StatelessWidget {
  const _HealthRow({required this.label, required this.count});

  final String label;
  final int count;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: <Widget>[
          Icon(
            count == 0 ? Icons.check_circle_outline : Icons.error_outline,
            size: 18,
            color: count == 0
                ? theme.colorScheme.primary
                : theme.colorScheme.error,
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: theme.textTheme.bodyMedium)),
          Text('$count', style: theme.textTheme.labelLarge),
        ],
      ),
    );
  }
}
