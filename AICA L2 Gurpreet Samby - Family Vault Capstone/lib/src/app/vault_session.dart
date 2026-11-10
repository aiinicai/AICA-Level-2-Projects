import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';

import '../core/failures.dart';
import '../crypto/crypto_service.dart';
import '../domain/folder.dart';
import '../domain/vault_data.dart';
import '../domain/vault_item.dart';
import '../domain/vault_settings.dart';
import '../platform/device_settings.dart';
import '../vault/vault_codec.dart';
import '../vault/vault_header.dart';
import '../vault/vault_merge.dart';
import '../vault/vault_repository.dart';
import '../vault/vault_sync.dart';

/// What state the vault is in.
enum VaultStatus {
  /// Still working out whether a vault exists.
  starting,

  /// No vault on this device yet; the user needs to create one.
  absent,

  /// A vault exists and is locked.
  locked,

  /// A vault is open and its contents are in memory.
  unlocked,
}

/// A backup file that has been decrypted and understood, but not applied.
///
/// Holding this means the password was right and the contents parsed. It is
/// plaintext in memory, so the interface drops it as soon as the user has
/// either applied it or backed out.
@immutable
final class BackupContents {
  const BackupContents({
    required this.data,
    required this.dropped,
    required this.fileName,
    required this.formatVersion,
  });

  /// What the file contained.
  final VaultData data;

  /// Entries the decoder could not understand and left out. Normally zero;
  /// anything else is reported, because silently losing an entry during an
  /// import is exactly the failure a password manager must not have.
  final int dropped;

  /// The file's name, for showing back to the user.
  final String fileName;

  /// The vault format version the file was written at.
  final int formatVersion;

  /// Entries not in the trash.
  int get liveItems => data.liveItems.length;

  /// Entries in the trash. Counted separately because a backup that is mostly
  /// trash is a sign the user picked the wrong file.
  int get trashedItems => data.trashedItems.length;

  /// Folders in the file.
  int get folders => data.folders.length;
}

/// Holds the vault's state for the whole application.
///
/// One instance, created at startup. While unlocked it holds the decrypted
/// contents and the derived key; while locked it holds neither.
///
/// It deliberately does not keep the master password. The password is used
/// once, at unlock, to derive a key, and that key then lives in memory the
/// cryptographic library locks and can wipe. A Dart [String] cannot be wiped,
/// so keeping the password around would leave it on the heap for as long as
/// the process ran.
class VaultSession extends ChangeNotifier with WidgetsBindingObserver {
  VaultSession({
    required CryptoService crypto,
    required this.repository,
    required this.deviceSettings,
  }) : _codec = VaultCodec(crypto),
       _crypto = crypto;

  final VaultCodec _codec;
  final CryptoService _crypto;

  /// Where the vault is stored. Public because a private field cannot be a
  /// named initializing formal in Dart.
  final VaultRepository repository;

  /// Settings belonging to this device rather than to the vault: the shared
  /// sync folder and this device's name. Injected rather than defaulted,
  /// because a quietly-in-memory store would make sync forget its folder at
  /// every restart and look like a bug in sync itself.
  final DeviceSettingsStore deviceSettings;

  VaultStatus _status = VaultStatus.starting;
  VaultData? _data;
  VaultKeyring? _keyring;
  String? _lastError;
  bool _busy = false;
  int _droppedOnOpen = 0;

  Timer? _lockTimer;
  Timer? _clipboardTimer;
  String? _clipboardValue;

  /// Current state.
  VaultStatus get status => _status;

  /// The decrypted vault, or null unless [status] is unlocked.
  VaultData? get data => _data;

  /// The last thing that went wrong, in plain language, or null.
  String? get lastError => _lastError;

  /// True while an operation that should block the interface is running.
  bool get isBusy => _busy;

  /// True when the vault is open.
  bool get isUnlocked => _status == VaultStatus.unlocked && _data != null;

  /// How many unreadable entries were dropped when the vault was opened.
  ///
  /// Non-zero means the file was damaged and the user should be told.
  int get droppedOnOpen => _droppedOnOpen;

  /// Settings of the open vault, or the defaults when locked.
  VaultSettings get settings => _data?.settings ?? const VaultSettings();

  /// Works out whether a vault exists. Call once at startup.
  Future<void> initialise() async {
    WidgetsBinding.instance.addObserver(this);
    _status = await repository.exists()
        ? VaultStatus.locked
        : VaultStatus.absent;
    notifyListeners();
  }

  /// Where the vault file is, for display in settings.
  Future<String> vaultLocation() => repository.location();

  /// Creates a new vault protected by [masterPassword].
  ///
  /// Returns true on success. Refuses if a vault already exists, so an
  /// accidental second creation cannot overwrite a real one.
  Future<bool> createVault(String masterPassword) async {
    if (await repository.exists()) {
      _fail('A vault already exists on this device.');
      return false;
    }
    return _guard(() async {
      final VaultKeyring keyring = _codec.createKeyring(
        masterPassword: masterPassword,
      );
      const VaultData fresh = VaultData.empty;
      await repository.write(
        _codec.sealWith(keyring: keyring, payload: fresh.encode()),
      );
      _keyring = keyring;
      _data = fresh;
      _droppedOnOpen = 0;
      _status = VaultStatus.unlocked;
      _restartLockTimer();
      return true;
    });
  }

  /// Opens the vault with [masterPassword]. Returns true on success.
  Future<bool> unlock(String masterPassword) => _guard(() async {
    final Uint8List file = await repository.read();
    final OpenedVault opened = _codec.unlock(
      file: file,
      masterPassword: masterPassword,
    );
    try {
      final VaultDataDecoding decoded = VaultData.decode(opened.payload);
      _keyring = opened.keyring;
      _data = decoded.data;
      _droppedOnOpen = decoded.droppedItems + decoded.droppedFolders;
      _status = VaultStatus.unlocked;
      _restartLockTimer();
      return true;
    } on Object {
      // The payload decrypted but could not be understood, so the key is of
      // no use and must not be kept.
      opened.keyring.dispose();
      rethrow;
    }
  });

  /// Closes the vault, wiping the key and the decrypted contents.
  void lock() {
    _lockTimer?.cancel();
    _lockTimer = null;
    _keyring?.dispose();
    _keyring = null;
    _data = null;
    _droppedOnOpen = 0;
    _lastError = null;
    if (_status == VaultStatus.unlocked) {
      _status = VaultStatus.locked;
    }
    notifyListeners();
  }

  /// Records that the user did something, restarting the inactivity timer.
  ///
  /// Called from a wrapper around the whole interface, so any touch, key press
  /// or scroll counts.
  void touch() {
    if (_status == VaultStatus.unlocked) {
      _restartLockTimer();
    }
  }

  /// Deletes the vault from this device for good.
  ///
  /// The interface asks for confirmation before calling this; there is no way
  /// back from it.
  Future<bool> deleteVault() => _guard(() async {
    await repository.delete();
    _keyring?.dispose();
    _keyring = null;
    _data = null;
    _status = VaultStatus.absent;
    return true;
  });

  // ---------------------------------------------------------------- contents

  /// Adds or replaces an item and saves.
  Future<bool> saveItem(VaultItem item) =>
      _mutate((VaultData d) => d.upsertItem(item));

  /// Moves an item to the trash and saves.
  Future<bool> trashItem(String id) =>
      _mutate((VaultData d) => d.trashItem(id));

  /// Takes an item out of the trash and saves.
  Future<bool> restoreItem(String id) =>
      _mutate((VaultData d) => d.restoreItem(id));

  /// Deletes an item for good and saves.
  Future<bool> purgeItem(String id) =>
      _mutate((VaultData d) => d.purgeItem(id));

  /// Empties the trash and saves.
  Future<bool> emptyTrash() => _mutate((VaultData d) => d.emptyTrash());

  /// Turns an item's favourite flag on or off and saves.
  Future<bool> toggleFavourite(String id) => _mutate((VaultData d) {
    final VaultItem? item = d.itemById(id);
    if (item == null) {
      return d;
    }
    return d.upsertItem(item.copyWith(favourite: !item.favourite));
  });

  /// Creates a folder and saves.
  Future<bool> addFolder(String name) =>
      _mutate((VaultData d) => d.addFolder(Folder.create(name)));

  /// Renames a folder and saves.
  Future<bool> renameFolder(String id, String name) =>
      _mutate((VaultData d) => d.renameFolder(id, name));

  /// Deletes a folder, keeping its items, and saves.
  Future<bool> deleteFolder(String id) =>
      _mutate((VaultData d) => d.deleteFolder(id));

  /// Replaces the vault's settings and saves.
  Future<bool> updateSettings(VaultSettings next) async {
    final bool saved = await _mutate((VaultData d) => d.withSettings(next));
    if (saved) {
      // The new timeout takes effect at once rather than after the next unlock.
      _restartLockTimer();
    }
    return saved;
  }

  /// Changes the master password, re-encrypting the whole vault.
  ///
  /// The contents are unchanged; a new salt and key are derived, so the old
  /// password cannot open the new file.
  Future<bool> changeMasterPassword(String newPassword) {
    final VaultData? current = _data;
    if (current == null) {
      _fail('Unlock the vault before changing its password.');
      return Future<bool>.value(false);
    }
    return _guard(() async {
      final VaultKeyring replacement = _codec.createKeyring(
        masterPassword: newPassword,
      );
      await repository.write(
        _codec.sealWith(keyring: replacement, payload: current.encode()),
      );
      _keyring?.dispose();
      _keyring = replacement;
      return true;
    });
  }

  /// Produces an encrypted copy of the vault, for the user to keep elsewhere.
  ///
  /// Protected by its own password, so a backup can be given a different one.
  Uint8List? exportEncrypted(String password) {
    final VaultData? current = _data;
    if (current == null) {
      _fail('Unlock the vault before exporting it.');
      return null;
    }
    try {
      return _codec.seal(masterPassword: password, payload: current.encode());
    } on VaultFailure catch (failure) {
      _fail(failure.message);
      return null;
    }
  }

  /// Checks [password] against the vault file on disk.
  ///
  /// Used before writing a backup protected by the master password: deriving
  /// a key from a mistyped password would produce a file nobody could ever
  /// open, and the user would not discover it until the day they needed it.
  ///
  /// Deliberately not [unlock]. Unlocking again while already unlocked would
  /// replace the live keyring and leave the old one unwiped. This derives a
  /// key, throws it away, and leaves the session untouched.
  Future<bool> verifyMasterPassword(String password) async {
    try {
      final Uint8List file = await repository.read();
      final OpenedVault opened = _codec.unlock(
        file: file,
        masterPassword: password,
      );
      opened.keyring.dispose();
      return true;
    } on Object {
      return false;
    }
  }

  // ------------------------------------------------------------------ import

  /// Decrypts and decodes a backup file without applying it.
  ///
  /// Reading and applying are deliberately two steps. The user is shown what
  /// the file contains and told what applying it would do before anything
  /// touches the vault on this device, because both outcomes - a merge and a
  /// replacement - are hard to undo once the file has been written.
  ///
  /// The key derived here is wiped before this returns: it was needed only to
  /// read the file, and the merged result is saved under the vault's own key.
  Future<BackupContents?> readBackup({
    required Uint8List file,
    required String password,
    String fileName = 'backup',
  }) async {
    _lastError = null;
    try {
      final VaultHeader header = _codec.inspect(file);
      final Uint8List payload = _codec.open(
        file: file,
        masterPassword: password,
      );
      final VaultDataDecoding decoded = VaultData.decode(payload);
      notifyListeners();
      return BackupContents(
        data: decoded.data,
        dropped: decoded.droppedItems + decoded.droppedFolders,
        fileName: fileName,
        formatVersion: header.formatVersion,
      );
    } on VaultFailure catch (failure) {
      _fail(failure.message);
      return null;
    } on FormatException {
      _fail('That file is not a Family Vault backup.');
      return null;
    }
  }

  /// Merges a backup into the open vault, entry by entry, and saves.
  ///
  /// Nothing is overwritten wholesale: for each entry the more recent change
  /// wins, and an entry only disappears if the backup records that it was
  /// deleted for good. Returns the outcome so the interface can report what
  /// changed, or null if the merge could not be saved.
  Future<MergeOutcome?> mergeBackup(BackupContents backup) async {
    final VaultData? current = _data;
    if (current == null) {
      _fail('Unlock the vault before importing into it.');
      return null;
    }
    final MergeOutcome outcome = VaultMerge.merge(
      local: current,
      other: backup.data,
    );
    if (!outcome.hadChanges) {
      return outcome;
    }
    final bool saved = await _mutate((VaultData _) => outcome.merged);
    return saved ? outcome : null;
  }

  /// Creates this device's vault from a backup file.
  ///
  /// For a new or reset device, where there is nothing to merge with. The new
  /// vault is protected by the backup's own password, which the user already
  /// knows; they can change it afterwards from Settings. Refuses if a vault
  /// already exists, so this can never silently replace one.
  Future<bool> createFromBackup({
    required Uint8List file,
    required String password,
  }) async {
    if (await repository.exists()) {
      _fail(
        'A vault already exists on this device. Import into it instead, or '
        'delete it first.',
      );
      return false;
    }
    final BackupContents? backup = await readBackup(
      file: file,
      password: password,
    );
    if (backup == null) {
      return false;
    }
    return _guard(() async {
      final VaultKeyring keyring = _codec.createKeyring(
        masterPassword: password,
      );
      await repository.write(
        _codec.sealWith(keyring: keyring, payload: backup.data.encode()),
      );
      _keyring = keyring;
      _data = backup.data;
      _droppedOnOpen = backup.dropped;
      _status = VaultStatus.unlocked;
      _restartLockTimer();
      return true;
    });
  }

  // -------------------------------------------------------- shared-folder sync

  DeviceSettings _device = DeviceSettings.none;

  /// This device's own sync settings.
  DeviceSettings get device => _device;

  /// True when this vault carries a sync secret, so another device set up
  /// through it can read this device's exchange file without a password.
  bool get syncReady => _data?.syncSecret != null;

  /// Loads this device's settings. Called once at startup.
  Future<void> loadDeviceSettings() async {
    _device = await deviceSettings.read();
    notifyListeners();
  }

  /// Points this device at a shared folder and names it.
  ///
  /// Generates the vault's sync secret if it does not have one yet. The
  /// secret is 32 random bytes from the cryptographic generator, held as hex
  /// so it can be used wherever a password is expected, and it lives inside
  /// the encrypted payload - so the second device receives it through the one
  /// manual import that sets sharing up, and never through the folder.
  Future<bool> enableSync({
    required String folder,
    required String deviceName,
  }) async {
    final VaultData? current = _data;
    if (current == null) {
      _fail('Unlock the vault before setting up sharing.');
      return false;
    }
    final String trimmed = deviceName.trim();
    if (trimmed.isEmpty) {
      _fail('Give this device a name, so you can tell the two apart.');
      return false;
    }
    if (current.syncSecret == null) {
      final bool saved = await _mutate(
        (VaultData d) => d.withSyncSecret(_newSyncSecret()),
      );
      if (!saved) {
        return false;
      }
    }
    _device = _device.copyWith(syncFolder: folder, deviceName: trimmed);
    await deviceSettings.write(_device);
    notifyListeners();
    return true;
  }

  /// Stops using the shared folder on this device.
  ///
  /// Leaves the vault's sync secret in place and leaves the files in the
  /// folder alone: deleting them would be a destructive act on a folder other
  /// devices are also using, and this device cannot know whether they still
  /// need what is there.
  Future<bool> disableSync() async {
    _device = _device.copyWith(clearSync: true);
    await deviceSettings.write(_device);
    notifyListeners();
    return true;
  }

  /// Merges every other device's file in the shared folder, then writes this
  /// device's own file back out carrying the result.
  Future<SyncReport?> syncNow({SyncFolder? folderOverride}) async {
    final VaultData? current = _data;
    if (current == null) {
      _fail('Unlock the vault before syncing.');
      return null;
    }
    final String? secret = current.syncSecret;
    final String? name = _device.deviceName;
    final String? path = _device.syncFolder;
    if (secret == null ||
        name == null ||
        (path == null && folderOverride == null)) {
      _fail('Set up a shared folder first.');
      return null;
    }

    _busy = true;
    _lastError = null;
    notifyListeners();
    try {
      final VaultSync sync = VaultSync(
        codec: _codec,
        folder: folderOverride ?? DirectorySyncFolder(path!),
      );
      final SyncReport report = await sync.run(
        local: current,
        syncSecret: secret,
        deviceName: name,
      );
      if (report.localChanged) {
        // Saved through the normal path, so the vault on this device is
        // re-sealed with its own key and written atomically, exactly as any
        // other change is.
        final bool saved = await _saveMerged(report.merged);
        if (!saved) {
          return null;
        }
      }
      _device = _device.copyWith(lastSyncedAt: DateTime.now());
      await deviceSettings.write(_device);
      _restartLockTimer();
      return report;
    } on VaultFailure catch (failure) {
      _fail(failure.message);
      return null;
    } on Object catch (error) {
      // The type only: a sync failure must not put a path or file contents on
      // screen.
      _fail('Syncing failed (${error.runtimeType}).');
      return null;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Writes an already-merged vault, without merging again.
  Future<bool> _saveMerged(VaultData merged) async {
    final VaultKeyring? keyring = _keyring;
    if (keyring == null) {
      _fail('The vault locked while syncing. Unlock it and sync again.');
      return false;
    }
    try {
      await repository.write(
        _codec.sealWith(keyring: keyring, payload: merged.encode()),
      );
      _data = merged;
      return true;
    } on VaultFailure catch (failure) {
      _fail(failure.message);
      return false;
    }
  }

  /// 32 random bytes as 64 hexadecimal characters.
  String _newSyncSecret() {
    final Uint8List bytes = _crypto.randomBytes(32);
    final StringBuffer out = StringBuffer();
    for (final int byte in bytes) {
      out.write(byte.toRadixString(16).padLeft(2, '0'));
    }
    return out.toString();
  }

  // --------------------------------------------------------------- clipboard

  /// Copies [value] to the clipboard and schedules it to be cleared.
  ///
  /// Clearing only happens if the clipboard still holds this value, so it
  /// never wipes something the user copied in the meantime.
  Future<void> copyToClipboard(String value) async {
    await Clipboard.setData(ClipboardData(text: value));
    _clipboardTimer?.cancel();
    _clipboardValue = value;
    final int seconds = settings.clipboardClearSeconds;
    if (seconds <= 0) {
      return;
    }
    _clipboardTimer = Timer(Duration(seconds: seconds), _clearClipboard);
  }

  Future<void> _clearClipboard() async {
    final String? expected = _clipboardValue;
    _clipboardValue = null;
    if (expected == null) {
      return;
    }
    final ClipboardData? current = await Clipboard.getData('text/plain');
    if (current?.text == expected) {
      await Clipboard.setData(const ClipboardData(text: ''));
    }
  }

  // ------------------------------------------------------------- app lifecyle

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Locked when the app leaves the screen, not merely when it loses focus:
    // on a desktop, clicking another window should not lock the vault, but a
    // phone going back to its home screen should.
    final bool offScreen =
        state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.detached;
    if (offScreen && isUnlocked && settings.lockWhenHidden) {
      lock();
    }
  }

  // ----------------------------------------------------------------- plumbing

  void _restartLockTimer() {
    _lockTimer?.cancel();
    final int minutes = settings.autoLockMinutes;
    if (minutes <= 0) {
      _lockTimer = null;
      return;
    }
    _lockTimer = Timer(Duration(minutes: minutes), lock);
  }

  /// Applies [change] to the open vault and writes the result.
  ///
  /// The in-memory copy is only replaced after the write succeeds, so a failed
  /// save leaves the interface showing what is actually on disk rather than an
  /// edit that was never stored.
  Future<bool> _mutate(VaultData Function(VaultData data) change) {
    final VaultData? current = _data;
    final VaultKeyring? keyring = _keyring;
    if (current == null || keyring == null) {
      _fail('The vault is locked.');
      return Future<bool>.value(false);
    }
    return _guard(() async {
      final VaultData next = change(current);
      await repository.write(
        _codec.sealWith(keyring: keyring, payload: next.encode()),
      );
      _data = next;
      _restartLockTimer();
      return true;
    });
  }

  /// Runs [action], turning any failure into a message a user can read.
  Future<bool> _guard(Future<bool> Function() action) async {
    _busy = true;
    _lastError = null;
    notifyListeners();
    try {
      return await action();
    } on VaultFailure catch (failure) {
      _lastError = failure.message;
      return false;
    } on StateError catch (error) {
      _lastError = error.message;
      return false;
    } on Object catch (error) {
      // Nothing here includes the vault contents or the password: only the
      // type of what went wrong, so a log cannot leak a secret.
      _lastError = 'Something went wrong: ${error.runtimeType}.';
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  void _fail(String message) {
    _lastError = message;
    notifyListeners();
  }

  /// Clears the last error, after the interface has shown it.
  void clearError() {
    if (_lastError != null) {
      _lastError = null;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _lockTimer?.cancel();
    _clipboardTimer?.cancel();
    _keyring?.dispose();
    _data = null;
    super.dispose();
  }
}
