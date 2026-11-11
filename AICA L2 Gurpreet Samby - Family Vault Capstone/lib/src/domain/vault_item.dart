import 'package:meta/meta.dart';

import 'ids.dart';

/// How a field should be presented and typed in the interface.
///
/// Deliberately not a Flutter type: the domain layer describes intent, and the
/// interface layer decides which keyboard or widget that means.
enum FieldInput {
  /// Ordinary single-line text.
  text,

  /// Email address.
  email,

  /// Web address.
  url,

  /// Telephone number.
  phone,

  /// Digits, such as a card number.
  number,

  /// Several lines of text.
  multiline,

  /// A secret: masked until revealed, and never shown in a list.
  secret,

  /// A one-time-password secret, which also drives the authenticator.
  totpSecret,
}

/// One field of an item: its storage key, its label, and how to present it.
@immutable
final class ItemFieldSpec {
  const ItemFieldSpec({
    required this.key,
    required this.label,
    this.input = FieldInput.text,
    this.hint,
  });

  /// Key this field is stored under.
  final String key;

  /// Label the user reads.
  final String label;

  /// How to present and type it.
  final FieldInput input;

  /// Optional help text, in plain language.
  final String? hint;

  /// True when the value must be masked and kept out of lists.
  bool get isSecret =>
      input == FieldInput.secret || input == FieldInput.totpSecret;
}

/// Storage keys for item fields.
///
/// Constants rather than literals because these keys go into the vault file:
/// changing one would orphan existing data.
abstract final class ItemField {
  static const String username = 'username';
  static const String email = 'email';
  static const String password = 'password';
  static const String url = 'url';
  static const String totpSecret = 'totp';
  static const String content = 'content';
  static const String cardholder = 'cardholder';
  static const String cardNumber = 'cardNumber';
  static const String expiry = 'expiry';
  static const String securityCode = 'securityCode';
  static const String fullName = 'fullName';
  static const String address = 'address';
  static const String phone = 'phone';
  static const String dateOfBirth = 'dateOfBirth';
}

/// The four kinds of thing a vault holds.
///
/// Each type carries its own field list, so one form in the interface can
/// render every type and a fifth type needs no new screen. This is what
/// requirement B3.5, "extensible to future item types", comes to in practice.
enum VaultItemType {
  login('login', 'Login', <ItemFieldSpec>[
    ItemFieldSpec(key: ItemField.username, label: 'Username'),
    ItemFieldSpec(
      key: ItemField.email,
      label: 'Email',
      input: FieldInput.email,
    ),
    ItemFieldSpec(
      key: ItemField.password,
      label: 'Password',
      input: FieldInput.secret,
    ),
    ItemFieldSpec(
      key: ItemField.url,
      label: 'Website',
      input: FieldInput.url,
      hint: 'Used to match this login when filling forms',
    ),
    ItemFieldSpec(
      key: ItemField.totpSecret,
      label: 'Authenticator key',
      input: FieldInput.totpSecret,
      hint: 'Paste the setup key to get six-digit codes here',
    ),
  ]),

  secureNote('note', 'Secure Note', <ItemFieldSpec>[
    ItemFieldSpec(
      key: ItemField.content,
      label: 'Note',
      input: FieldInput.multiline,
    ),
  ]),

  paymentCard('card', 'Payment Card', <ItemFieldSpec>[
    ItemFieldSpec(key: ItemField.cardholder, label: 'Name on card'),
    ItemFieldSpec(
      key: ItemField.cardNumber,
      label: 'Card number',
      input: FieldInput.secret,
    ),
    ItemFieldSpec(key: ItemField.expiry, label: 'Expires', hint: 'MM/YY'),
    ItemFieldSpec(
      key: ItemField.securityCode,
      label: 'Security code',
      input: FieldInput.secret,
    ),
  ]),

  identity('identity', 'Identity', <ItemFieldSpec>[
    ItemFieldSpec(key: ItemField.fullName, label: 'Full name'),
    ItemFieldSpec(
      key: ItemField.address,
      label: 'Address',
      input: FieldInput.multiline,
    ),
    ItemFieldSpec(
      key: ItemField.email,
      label: 'Email',
      input: FieldInput.email,
    ),
    ItemFieldSpec(
      key: ItemField.phone,
      label: 'Phone',
      input: FieldInput.phone,
    ),
    ItemFieldSpec(key: ItemField.dateOfBirth, label: 'Date of birth'),
  ]);

  const VaultItemType(this.key, this.label, this.fields);

  /// Value stored in the vault file. Never change these.
  final String key;

  /// Name the user reads.
  final String label;

  /// Fields this type has, in the order they should be shown.
  final List<ItemFieldSpec> fields;

  /// Maps a stored value back to a type, or null if unrecognised.
  static VaultItemType? fromKey(String key) {
    for (final VaultItemType type in VaultItemType.values) {
      if (type.key == key) {
        return type;
      }
    }
    return null;
  }
}

/// One entry in the vault.
///
/// Common properties are typed; the parts that differ by kind live in [fields],
/// keyed by the constants in [ItemField]. That keeps one class rather than
/// four near-identical ones, lets the interface render any type from
/// [VaultItemType.fields], and means a new kind of item needs no change here.
///
/// Immutable: every edit produces a new instance, so a half-applied change
/// cannot be left in memory.
@immutable
final class VaultItem {
  const VaultItem({
    required this.id,
    required this.type,
    required this.title,
    required this.fields,
    required this.createdAt,
    required this.updatedAt,
    this.folderId,
    this.favourite = false,
    this.notes = '',
    this.deletedAt,
    this.passwordUpdatedAt,
  });

  /// Creates a new item with a fresh identifier.
  factory VaultItem.create({
    required VaultItemType type,
    required String title,
    Map<String, String> fields = const <String, String>{},
    String? folderId,
    String notes = '',
    DateTime? now,
  }) {
    final DateTime stamp = now ?? DateTime.now();
    return VaultItem(
      id: Ids.generate(),
      type: type,
      title: title,
      fields: Map<String, String>.unmodifiable(fields),
      folderId: folderId,
      notes: notes,
      createdAt: stamp,
      updatedAt: stamp,
      passwordUpdatedAt: (fields[ItemField.password] ?? '').isEmpty
          ? null
          : stamp,
    );
  }

  /// Unique identifier.
  final String id;

  /// Which kind of item this is.
  final VaultItemType type;

  /// Name the user gave it.
  final String title;

  /// Folder it belongs to, or null for no folder.
  final String? folderId;

  /// Whether the user marked it a favourite.
  final bool favourite;

  /// Free-text notes, available on every type.
  final String notes;

  /// Type-specific values, keyed by [ItemField] constants.
  final Map<String, String> fields;

  /// When the item was created.
  final DateTime createdAt;

  /// When it was last changed.
  final DateTime updatedAt;

  /// When it was moved to the trash, or null if it is live.
  final DateTime? deletedAt;

  /// When the password last changed, used by the health report to spot
  /// passwords that have not been rotated in a long time.
  ///
  /// Null when the item has no password, or when it predates this field.
  final DateTime? passwordUpdatedAt;

  /// True when the item is in the trash.
  bool get isDeleted => deletedAt != null;

  /// Value of [key], or an empty string when absent.
  String field(String key) => fields[key] ?? '';

  /// The password, or an empty string for items that have none.
  String get password => field(ItemField.password);

  /// The authenticator key, or an empty string when none is stored.
  String get totpSecret => field(ItemField.totpSecret);

  /// The website, or an empty string.
  String get url => field(ItemField.url);

  /// The username, falling back to the email address when there is no
  /// username, since that is what the user would recognise in a list.
  String get subtitle {
    final String username = field(ItemField.username);
    if (username.isNotEmpty) {
      return username;
    }
    final String email = field(ItemField.email);
    if (email.isNotEmpty) {
      return email;
    }
    return type.label;
  }

  /// A copy with the given changes, stamping [updatedAt].
  ///
  /// [passwordUpdatedAt] is advanced only when the password actually changed,
  /// so that editing a title does not make an old password look fresh.
  VaultItem copyWith({
    String? title,
    Map<String, String>? fields,
    String? folderId,
    bool clearFolder = false,
    bool? favourite,
    String? notes,
    DateTime? deletedAt,
    bool restore = false,
    DateTime? now,
  }) {
    final DateTime stamp = now ?? DateTime.now();
    final Map<String, String> nextFields = fields == null
        ? this.fields
        : Map<String, String>.unmodifiable(fields);
    final String nextPassword = nextFields[ItemField.password] ?? '';
    final bool passwordChanged = nextPassword != password;
    return VaultItem(
      id: id,
      type: type,
      title: title ?? this.title,
      fields: nextFields,
      folderId: clearFolder ? null : (folderId ?? this.folderId),
      favourite: favourite ?? this.favourite,
      notes: notes ?? this.notes,
      createdAt: createdAt,
      updatedAt: stamp,
      deletedAt: restore ? null : (deletedAt ?? this.deletedAt),
      passwordUpdatedAt: passwordChanged && nextPassword.isNotEmpty
          ? stamp
          : passwordUpdatedAt,
    );
  }

  /// Stored form.
  Map<String, Object?> toJson() => <String, Object?>{
    'id': id,
    'type': type.key,
    'title': title,
    'folderId': folderId,
    'favourite': favourite,
    'notes': notes,
    'fields': fields,
    'createdAt': createdAt.toUtc().toIso8601String(),
    'updatedAt': updatedAt.toUtc().toIso8601String(),
    'deletedAt': deletedAt?.toUtc().toIso8601String(),
    'passwordUpdatedAt': passwordUpdatedAt?.toUtc().toIso8601String(),
  };

  /// Reads an item from its stored form.
  ///
  /// Returns null when the entry cannot be understood, so that one damaged
  /// item does not make the whole vault unreadable. The caller counts what it
  /// dropped and tells the user.
  static VaultItem? fromJson(Map<String, Object?> json) {
    final Object? id = json['id'];
    final Object? typeKey = json['type'];
    final Object? title = json['title'];
    if (id is! String || !Ids.isValid(id) || typeKey is! String) {
      return null;
    }
    final VaultItemType? type = VaultItemType.fromKey(typeKey);
    if (type == null) {
      return null;
    }

    final Map<String, String> fields = <String, String>{};
    final Object? rawFields = json['fields'];
    if (rawFields is Map<Object?, Object?>) {
      for (final MapEntry<Object?, Object?> entry in rawFields.entries) {
        final Object? key = entry.key;
        final Object? value = entry.value;
        if (key is String && value is String) {
          fields[key] = value;
        }
      }
    }

    DateTime? parse(Object? value) =>
        value is String ? DateTime.tryParse(value) : null;

    final DateTime created =
        parse(json['createdAt']) ??
        DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
    final Object? folderId = json['folderId'];
    final Object? notes = json['notes'];
    final Object? favourite = json['favourite'];

    return VaultItem(
      id: id,
      type: type,
      title: title is String ? title : '',
      fields: Map<String, String>.unmodifiable(fields),
      folderId: folderId is String && Ids.isValid(folderId) ? folderId : null,
      favourite: favourite is bool && favourite,
      notes: notes is String ? notes : '',
      createdAt: created,
      updatedAt: parse(json['updatedAt']) ?? created,
      deletedAt: parse(json['deletedAt']),
      passwordUpdatedAt: parse(json['passwordUpdatedAt']),
    );
  }

  @override
  bool operator ==(Object other) =>
      other is VaultItem && other.id == id && other.updatedAt == updatedAt;

  @override
  int get hashCode => Object.hash(id, updatedAt);
}
