import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:convert';
import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:material_ui/material_ui.dart';

import '../services/backup_service.dart';

class BackupRecovery extends StatefulWidget {
  const BackupRecovery({super.key});

  @override
  State<BackupRecovery> createState() =>
      _BackupRecoveryState();
}

class _BackupRecoveryState extends State<BackupRecovery> {
  final BackupService service = BackupService();

  int recordCount = 0;
  bool isLoading = true;
  String? storageError;

  @override
  void initState() {
    super.initState();
    loadStorageInformation();
  }

  Future<void> loadStorageInformation() async {
    try {
      final count = await service.getRecordCount();

      if (!mounted) return;

      setState(() {
        recordCount = count;
        isLoading = false;
        storageError = null;
      });
    } catch (_) {
      if (!mounted) return;

      setState(() {
        isLoading = false;
        storageError = 'Unable to read storage information.';
      });
    }
  }
  bool isExporting = false;

  Future<void> exportBackup() async {
    if (isExporting || isValidating) return;

    setState(() => isExporting = true);

    try {
      final backup = await service.createBackup();

      service.validateForRestore(backup);

      final bytes = Uint8List.fromList(
        utf8.encode(backup),
      );

      final timestamp = DateTime.now()
          .toIso8601String()
          .replaceAll(':', '-')
          .replaceAll('.', '-');

      final result = await FilePicker.saveFile(
        dialogTitle: 'Save LIFE360 AI Backup',
        fileName: 'LIFE360_AI_Backup_$timestamp.json',
                bytes: bytes,
      );

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            kIsWeb
    ? 'Backup prepared. Please check your browser downloads.'
    : result == null
        ? 'Backup save cancelled or not confirmed.'
        : 'Backup exported successfully.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Unable to export backup. Please try again.',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => isExporting = false);
      }
    }
  }

  bool isValidating = false;

  Future<void> validateBackupFile() async {
    if (isValidating || isExporting) return;

    setState(() => isValidating = true);

    try {
            final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
      );

      if (result.isEmpty || !mounted) return;

      final file = result.single;
      final bytes = await file.readAsBytes();

      if (bytes.isEmpty) {
        throw const FormatException(
          'Unable to read backup file.',
        );
      }

      final backup = utf8.decode(bytes);
      final records = service.validateForRestore(backup);

      if (!mounted) return;

      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            icon: const Icon(
              Icons.verified_user,
              color: Colors.teal,
              size: 48,
            ),
            title: const Text('Backup Validation Successful'),
            content: Text(
              'File: ${file.name}\n\n'
              'Valid records: ${records.length}\n\n'
              'This backup is compatible with LIFE360 AI.\n\n'
              'No existing data has been modified.',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop();
                },
                child: const Text('Close'),
              ),
            ],
          );
        },
      );
    } catch (_) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Invalid or incompatible backup file. '
            'No data has been modified.',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => isValidating = false);
      }
    }
  }

  bool isRestoring = false;
  bool hasRestored = false;

  Future<void> restoreBackupFile() async {
    if (isRestoring || isExporting || isValidating) return;

    setState(() => isRestoring = true);

    try {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
      );

      if (result.isEmpty || !mounted) return;

      final file = result.single;
      final bytes = await file.readAsBytes();

      if (bytes.isEmpty) {
        throw const FormatException('Empty backup file.');
      }

      final backup = utf8.decode(bytes);
      final records = service.validateForRestore(backup);

      if (!mounted) return;

      final confirmed = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) {
          return AlertDialog(
            icon: const Icon(
              Icons.warning_amber_rounded,
              color: Colors.orange,
              size: 48,
            ),
            title: const Text('Confirm Backup Restoration'),
            content: Text(
              'File: ${file.name}\n\n'
              'Records to restore: ${records.length}\n\n'
              'Matching existing records will be overwritten. '
              'Other records will be preserved.\n\n'
              'Do you want to continue?',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop(false);
                },
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop(true);
                },
                child: const Text('Restore'),
              ),
            ],
          );
        },
      );

      if (confirmed != true || !mounted) return;

      final restored = await service.restoreBackup(backup);

      if (!mounted) return;

      hasRestored = true;

      await loadStorageInformation();

      if (!mounted) return;

      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            icon: const Icon(
              Icons.verified_user,
              color: Colors.teal,
              size: 48,
            ),
            title: const Text('Backup Restoration Successful'),
            content: Text(
              '$restored records restored successfully.\n\n'
              'Records outside the backup have been preserved.',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop();
                },
                child: const Text('Close'),
              ),
            ],
          );
        },
      );
    } on FormatException {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Invalid or incompatible backup. '
            'No records have been restored.',
          ),
        ),
      );
    } catch (_) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Restore could not be completed. '
            'Please verify your records before retrying.',
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => isRestoring = false);
      }
    }
  }


  Widget buildActionCard({
    required IconData icon,
    required Color color,
    required String title,
    required String description,
    VoidCallback? onTap,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: CircleAvatar(
          backgroundColor: color.withValues(alpha: 0.12),
          child: Icon(icon, color: color),
        ),
        title: Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Text(description),
        trailing: Icon(
          onTap == null
              ? Icons.lock_outline
              : Icons.chevron_right,
        ),
        onTap: onTap,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Backup & Recovery'),
        backgroundColor:
            Theme.of(context).colorScheme.primaryContainer,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 750),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const Icon(
                Icons.verified_user_outlined,
                size: 64,
                color: Colors.teal,
              ),
              const SizedBox(height: 12),
              const Text(
                'Protect Your Personal Data',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Manage your activity history, planner '
                'and wellness reminder settings.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const Icon(
                        Icons.storage,
                        size: 36,
                        color: Colors.teal,
                      ),
                      const SizedBox(height: 10),
                      const Text(
                        'Local Storage',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 12),
                      if (isLoading)
                        const CircularProgressIndicator()
                      else if (storageError != null)
                        Text(storageError!)
                      else
                        Text(
                          '$recordCount stored records',
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      const SizedBox(height: 8),
                      TextButton.icon(
                        onPressed: isLoading
                            ? null
                            : loadStorageInformation,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Refresh'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
buildActionCard(
  icon: Icons.download,
                color: Colors.teal,
                title: 'Create Backup',
                description: isExporting
                    ? 'Preparing your backup...'
                    : 'Export your records as a JSON file.',
                onTap: isLoading ||
                        isExporting ||
                        isValidating ||
                        isRestoring ||
                        storageError != null
                    ? null
                    : exportBackup,
              ),
              buildActionCard(
                icon: Icons.upload,
                color: Colors.blue,
                title: 'Restore Backup',
                description: isRestoring
                    ? 'Processing backup restoration...'
                    : 'Recover your saved personal records.',
                onTap: isLoading ||
                        isExporting ||
                        isValidating ||
                        isRestoring ||
                        storageError != null
                    ? null
                    : restoreBackupFile,
              ),
              buildActionCard(
                icon: Icons.verified_outlined,
                color: Colors.purple,
                title: 'Validate Backup',
                description: isValidating
                    ? 'Checking backup file...'
                    : 'Verify backup integrity and compatibility.',
                onTap: isLoading ||
                        isExporting ||
                        isValidating ||
                        isRestoring
                    ? null
                    : validateBackupFile,
              ),    
              const SizedBox(height: 16),
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    'Privacy Notice: Your application data '
                    'is stored locally. Keep exported backup '
                    'files in a secure location.',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
