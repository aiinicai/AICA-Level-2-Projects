import 'dart:convert';
import 'dart:typed_data';

import 'package:family_vault/src/core/failures.dart';
import 'package:family_vault/src/domain/folder.dart';
import 'package:family_vault/src/domain/ids.dart';
import 'package:family_vault/src/domain/vault_data.dart';
import 'package:family_vault/src/domain/vault_item.dart';
import 'package:family_vault/src/domain/vault_settings.dart';
import 'package:flutter_test/flutter_test.dart';

/// Tests for the vault payload: the data that gets encrypted.
///
/// Two themes run through these. First, a round trip must be lossless, because
/// anything dropped here is a password the user has lost. Second, a damaged
/// entry must cost the user only that entry — refusing to open the whole vault
/// because one item is malformed would be the worst possible response.
void main() {
  VaultItem loginNamed(String title, {String password = 'Str0ng!passw0rd'}) =>
      VaultItem.create(
        type: VaultItemType.login,
        title: title,
        fields: <String, String>{
          ItemField.username: '${title.toLowerCase()}@example.com',
          ItemField.password: password,
          ItemField.url: 'https://${title.toLowerCase()}.example.com',
        },
      );

  group('round trips', () {
    test('an empty vault', () {
      final VaultDataDecoding decoded = VaultData.decode(
        VaultData.empty.encode(),
      );
      expect(decoded.data.items, isEmpty);
      expect(decoded.data.folders, isEmpty);
      expect(decoded.hadLosses, isFalse);
    });

    test('every item type, with all its fields intact', () {
      VaultData data = VaultData.empty;
      for (final VaultItemType type in VaultItemType.values) {
        final Map<String, String> fields = <String, String>{
          for (final ItemFieldSpec spec in type.fields)
            spec.key: 'value for ${spec.key}',
        };
        data = data.upsertItem(
          VaultItem.create(
            type: type,
            title: 'A ${type.label}',
            fields: fields,
            notes: 'notes for ${type.key}',
          ),
        );
      }

      final VaultData back = VaultData.decode(data.encode()).data;
      expect(back.items.length, VaultItemType.values.length);
      for (final VaultItem original in data.items) {
        final VaultItem? restored = back.itemById(original.id);
        expect(restored, isNotNull, reason: original.title);
        expect(restored!.type, original.type);
        expect(restored.title, original.title);
        expect(restored.notes, original.notes);
        expect(restored.fields, original.fields);
      }
    });

    test('folders, favourites, trash and settings', () {
      final Folder folder = Folder.create('Banking');
      VaultData data = VaultData.empty
          .addFolder(folder)
          .withSettings(
            const VaultSettings(
              autoLockMinutes: 15,
              clipboardClearSeconds: 10,
              lockWhenHidden: false,
            ),
          );
      final VaultItem kept = loginNamed('Bank').copyWith(favourite: true);
      final VaultItem binned = loginNamed('Old');
      data = data.upsertItem(kept).upsertItem(binned);
      data = data.trashItem(binned.id);

      final VaultData back = VaultData.decode(data.encode()).data;
      expect(back.folders.single.name, 'Banking');
      expect(back.settings.autoLockMinutes, 15);
      expect(back.settings.clipboardClearSeconds, 10);
      expect(back.settings.lockWhenHidden, isFalse);
      expect(back.favourites.single.title, 'Bank');
      expect(back.trashedItems.single.title, 'Old');
      expect(back.liveItems.single.title, 'Bank');
    });

    test('unicode in titles, notes and passwords', () {
      final VaultItem item = VaultItem.create(
        type: VaultItemType.secureNote,
        title: 'गुरप्रीत का नोट',
        fields: <String, String>{ItemField.content: 'पासवर्ड: ünïcø∂é 🔐'},
        notes: 'Ünicode — em dash, emoji 🗝️',
      );
      final VaultData back = VaultData.decode(
        VaultData.empty.upsertItem(item).encode(),
      ).data;
      expect(back.itemById(item.id)!.title, 'गुरप्रीत का नोट');
      expect(
        back.itemById(item.id)!.field(ItemField.content),
        'पासवर्ड: ünïcø∂é 🔐',
      );
      expect(back.itemById(item.id)!.notes, 'Ünicode — em dash, emoji 🗝️');
    });
  });

  group('survives damage without losing the rest', () {
    test('drops an item with no identifier and counts it', () {
      final VaultItem good = loginNamed('Good');
      final Map<String, Object?> payload = <String, Object?>{
        'schemaVersion': 1,
        'folders': <Object?>[],
        'items': <Object?>[
          good.toJson(),
          <String, Object?>{'type': 'login', 'title': 'No id'},
        ],
        'settings': const VaultSettings().toJson(),
      };
      final VaultDataDecoding decoded = VaultData.decode(
        Uint8List.fromList(utf8.encode(jsonEncode(payload))),
      );
      expect(decoded.data.items.single.title, 'Good');
      expect(decoded.droppedItems, 1);
      expect(decoded.hadLosses, isTrue);
    });

    test('drops an item of an unknown type rather than guessing', () {
      final Map<String, Object?> payload = <String, Object?>{
        'items': <Object?>[
          <String, Object?>{
            'id': Ids.generate(),
            'type': 'cryptocurrency-wallet',
            'title': 'From a future version',
          },
        ],
      };
      final VaultDataDecoding decoded = VaultData.decode(
        Uint8List.fromList(utf8.encode(jsonEncode(payload))),
      );
      expect(decoded.data.items, isEmpty);
      expect(decoded.droppedItems, 1);
    });

    test('tolerates a payload missing whole sections', () {
      final VaultDataDecoding decoded = VaultData.decode(
        Uint8List.fromList(utf8.encode('{"schemaVersion":1}')),
      );
      expect(decoded.data.items, isEmpty);
      expect(decoded.data.settings, const VaultSettings());
    });

    test('falls back to defaults for out-of-range settings', () {
      final VaultDataDecoding decoded = VaultData.decode(
        Uint8List.fromList(utf8.encode('{"settings":{"autoLockMinutes":-5}}')),
      );
      expect(
        decoded.data.settings.autoLockMinutes,
        VaultSettings.defaultAutoLockMinutes,
      );
    });
  });

  group('refuses what it must', () {
    test('a payload that is not JSON at all', () {
      expect(
        () => VaultData.decode(Uint8List.fromList(utf8.encode('not json'))),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a payload that is JSON but not an object', () {
      expect(
        () => VaultData.decode(Uint8List.fromList(utf8.encode('[1,2,3]'))),
        throwsA(isA<VaultFormatFailure>()),
      );
    });

    test('a payload from a newer schema, distinctly', () {
      expect(
        () => VaultData.decode(
          Uint8List.fromList(utf8.encode('{"schemaVersion":99}')),
        ),
        throwsA(isA<VaultVersionFailure>()),
      );
    });
  });

  group('items', () {
    test('upsert replaces rather than duplicating', () {
      final VaultItem item = loginNamed('Bank');
      final VaultData data = VaultData.empty
          .upsertItem(item)
          .upsertItem(item.copyWith(title: 'Bank renamed'));
      expect(data.items.length, 1);
      expect(data.items.single.title, 'Bank renamed');
    });

    test('trash, restore and purge', () {
      final VaultItem item = loginNamed('Bank');
      VaultData data = VaultData.empty.upsertItem(item);
      expect(data.liveItems.length, 1);

      data = data.trashItem(item.id);
      expect(data.liveItems, isEmpty);
      expect(data.trashedItems.length, 1);
      expect(data.itemById(item.id)!.isDeleted, isTrue);

      data = data.restoreItem(item.id);
      expect(data.liveItems.length, 1);
      expect(data.itemById(item.id)!.isDeleted, isFalse);

      data = data.trashItem(item.id).purgeItem(item.id);
      expect(data.items, isEmpty);
    });

    test('emptying the trash leaves live items alone', () {
      final VaultItem kept = loginNamed('Keep');
      final VaultItem binned = loginNamed('Bin');
      final VaultData data = VaultData.empty
          .upsertItem(kept)
          .upsertItem(binned)
          .trashItem(binned.id)
          .emptyTrash();
      expect(data.items.single.title, 'Keep');
    });

    test('editing the title does not make an old password look fresh', () {
      final DateTime longAgo = DateTime.utc(2020);
      final VaultItem item = VaultItem.create(
        type: VaultItemType.login,
        title: 'Bank',
        fields: <String, String>{ItemField.password: 'original'},
        now: longAgo,
      );
      expect(item.passwordUpdatedAt, longAgo);

      final VaultItem renamed = item.copyWith(title: 'Bank plc');
      expect(renamed.passwordUpdatedAt, longAgo);

      final VaultItem rotated = item.copyWith(
        fields: <String, String>{ItemField.password: 'different'},
      );
      expect(rotated.passwordUpdatedAt, isNot(longAgo));
    });

    test('subtitle falls back from username to email to the type name', () {
      expect(
        VaultItem.create(
          type: VaultItemType.login,
          title: 'A',
          fields: <String, String>{ItemField.username: 'user'},
        ).subtitle,
        'user',
      );
      expect(
        VaultItem.create(
          type: VaultItemType.login,
          title: 'A',
          fields: <String, String>{ItemField.email: 'a@b.com'},
        ).subtitle,
        'a@b.com',
      );
      expect(
        VaultItem.create(type: VaultItemType.login, title: 'A').subtitle,
        'Login',
      );
    });
  });

  group('folders', () {
    test('deleting a folder keeps its items, with no folder', () {
      final Folder folder = Folder.create('Banking');
      final VaultItem item = loginNamed('Bank');
      VaultData data = VaultData.empty
          .addFolder(folder)
          .upsertItem(item.copyWith(folderId: folder.id));
      expect(data.itemsInFolder(folder.id).length, 1);

      data = data.deleteFolder(folder.id);
      expect(data.folders, isEmpty);
      expect(
        data.items.single.folderId,
        isNull,
        reason: 'the item must survive its folder being deleted',
      );
      expect(data.liveItems.length, 1);
    });

    test('renaming a folder leaves its items attached', () {
      final Folder folder = Folder.create('Bankng');
      VaultData data = VaultData.empty
          .addFolder(folder)
          .upsertItem(loginNamed('Bank').copyWith(folderId: folder.id));
      data = data.renameFolder(folder.id, 'Banking');
      expect(data.folderById(folder.id)!.name, 'Banking');
      expect(data.itemsInFolder(folder.id).length, 1);
    });
  });

  group('search', () {
    late VaultData data;

    setUp(() {
      final Folder folder = Folder.create('Banking');
      data = VaultData.empty
          .addFolder(folder)
          .upsertItem(loginNamed('Barclays').copyWith(folderId: folder.id))
          .upsertItem(loginNamed('Netflix'))
          .upsertItem(
            VaultItem.create(
              type: VaultItemType.secureNote,
              title: 'Passport details',
              notes: 'kept for travel',
            ),
          );
    });

    test('an empty query returns everything live', () {
      expect(data.search('   ').length, 3);
    });

    test('matches a title, case-insensitively', () {
      expect(data.search('netflix').single.title, 'Netflix');
    });

    test('matches a username and a website', () {
      expect(data.search('barclays@example.com').length, 1);
      expect(data.search('netflix.example.com').length, 1);
    });

    test('matches a folder name', () {
      expect(data.search('Banking').single.title, 'Barclays');
    });

    test('matches notes', () {
      expect(data.search('travel').single.title, 'Passport details');
    });

    // Searching secrets would let someone confirm a guessed password by
    // typing it into the search box.
    test('does not match on a password', () {
      expect(data.search('Str0ng!passw0rd'), isEmpty);
    });

    test('excludes trashed items', () {
      final VaultItem netflix = data.search('Netflix').single;
      expect(data.trashItem(netflix.id).search('Netflix'), isEmpty);
    });
  });

  group('identifiers', () {
    test('are 32 hex characters and unique', () {
      final Set<String> seen = <String>{};
      for (int i = 0; i < 500; i++) {
        final String id = Ids.generate();
        expect(Ids.isValid(id), isTrue);
        expect(id.length, 32);
        seen.add(id);
      }
      expect(seen.length, 500);
    });

    test('reject anything that is not one', () {
      for (final String bad in <String>[
        '',
        'short',
        'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ',
        'abcdef',
      ]) {
        expect(Ids.isValid(bad), isFalse, reason: bad);
      }
    });
  });
}
