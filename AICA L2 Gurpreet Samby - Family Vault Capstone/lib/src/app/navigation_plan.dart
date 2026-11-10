import 'package:flutter/material.dart';

import '../domain/vault_item.dart';

/// The sections of the application, in navigation order.
///
/// The shell renders this list directly, so the navigation and this definition
/// cannot drift apart. Sections that show one kind of item carry that kind in
/// [itemType], which is what lets a single list view serve four destinations.
enum AppSection {
  dashboard(Icons.dashboard_outlined, Icons.dashboard, 'Dashboard'),
  allItems(Icons.list_alt_outlined, Icons.list_alt, 'All Items'),
  logins(
    Icons.login_outlined,
    Icons.login,
    'Logins',
    itemType: VaultItemType.login,
  ),
  notes(
    Icons.sticky_note_2_outlined,
    Icons.sticky_note_2,
    'Secure Notes',
    itemType: VaultItemType.secureNote,
  ),
  cards(
    Icons.credit_card_outlined,
    Icons.credit_card,
    'Payment Cards',
    itemType: VaultItemType.paymentCard,
  ),
  identities(
    Icons.badge_outlined,
    Icons.badge,
    'Identities',
    itemType: VaultItemType.identity,
  ),
  folders(Icons.folder_outlined, Icons.folder, 'Folders'),
  favourites(Icons.star_outline, Icons.star, 'Favourites'),
  authenticator(Icons.timer_outlined, Icons.timer, 'Authenticator'),
  health(
    Icons.health_and_safety_outlined,
    Icons.health_and_safety,
    'Password Health',
  ),
  trash(Icons.delete_outline, Icons.delete, 'Trash'),
  backup(Icons.backup_outlined, Icons.backup, 'Backup & Transfer'),
  settings(Icons.settings_outlined, Icons.settings, 'Settings');

  const AppSection(this.icon, this.selectedIcon, this.label, {this.itemType});

  /// Icon when not selected.
  final IconData icon;

  /// Icon when selected.
  final IconData selectedIcon;

  /// Name the user reads.
  final String label;

  /// The kind of item this section lists, when it lists one kind.
  final VaultItemType? itemType;

  /// True when this section is a list of one kind of item.
  bool get isTypeList => itemType != null;
}
