/// Compile-time facts about this build.
///
/// Nothing here is secret and nothing here is read from a vault. These values
/// exist so the interface can state plainly what the user is looking at.
library;

/// Product name, shown in the title bar and about screen.
const String appName = 'Family Vault';

/// Human-readable version. Kept in step with `version:` in pubspec.yaml.
const String appVersion = '0.5.0';

/// Development stage currently delivered. Used by the shell so the interface
/// never implies a feature exists before it does.
const String appStage =
    'Phase 1 - encrypted vault with backup and shared-folder sync';

/// True only in the public web demonstration build, which is compiled with
/// `--dart-define=FAMILY_VAULT_DEMO=true`.
///
/// A demo build is seeded with synthetic data and must never be able to open a
/// real vault file. This is a compile-time constant rather than a setting so
/// that the demo build physically cannot be switched into real-vault mode.
/// See docs/decisions-and-risks.md, decision D-007.
const bool isDemoBuild = bool.fromEnvironment('FAMILY_VAULT_DEMO');
