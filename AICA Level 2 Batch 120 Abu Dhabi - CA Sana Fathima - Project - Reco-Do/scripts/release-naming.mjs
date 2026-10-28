// Pure naming rules for the files in release/ (used by scripts/package.mjs, tested in tests/platform).
//
//   release/RecoDo-Setup.exe                               the installer of the current build
//   release/RecoDo.exe                                     the current app itself (portable, no install)
//   release/previous-versions/RecoDo-Setup-v<ver>.exe      older installers, one per version
//   release/previous-versions/RecoDo-v<ver>.exe            older portable apps, one per version

/** The two current release files and the base name their backups use. */
export const RELEASE_FILES = [
  { file: 'RecoDo-Setup.exe', base: 'RecoDo-Setup' },
  { file: 'RecoDo.exe', base: 'RecoDo' }
]

/** Builds before 1.1.2 used these names; they are moved into previous-versions with the new naming. */
const LEGACY = /^Reco-Do-(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)-(Installer|Portable-NoInstall)\.exe$/

const VERSION = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/

/**
 * A version as it should appear in a file name: "1.1.2" stays, a Windows file version "1.1.2.0" becomes "1.1.2".
 * Returns null for anything that is not a version.
 */
export function cleanVersion(raw) {
  if (typeof raw !== 'string') return null
  let v = raw.trim().replace(/^v/i, '')
  if (/^\d+\.\d+\.\d+\.0$/.test(v)) v = v.slice(0, -2)
  return VERSION.test(v) ? v : null
}

/** The version recorded in release/VERSION.txt ("Reco-Do 1.1.2, built 18-Oct-2026 23:10"), or null. */
export function versionFromVersionFile(text) {
  if (typeof text !== 'string') return null
  const m = /^Reco-Do\s+v?(\S+?),/m.exec(text)
  return m ? cleanVersion(m[1]) : null
}

/** The text written to release/VERSION.txt. */
export function versionFileText(version, builtAt) {
  return `Reco-Do ${version}, built ${builtAt}\n`
}

/**
 * The backup file name for `base` at `version` that is not already taken: RecoDo-v1.1.1.exe, then
 * RecoDo-v1.1.1-2.exe, -3 and so on. An existing backup is never overwritten. `taken` holds the names already in
 * previous-versions (compared without regard to case, as Windows does).
 */
export function backupName(base, version, taken) {
  const used = new Set(Array.from(taken, (n) => n.toLowerCase()))
  const stem = `${base}-v${version}`
  if (!used.has(`${stem}.exe`.toLowerCase())) return `${stem}.exe`
  for (let n = 2; ; n++) {
    const name = `${stem}-${n}.exe`
    if (!used.has(name.toLowerCase())) return name
  }
}

/** For a pre-1.1.2 release file name, the backup base and version ({ base, version }); otherwise null. */
export function legacyRelease(fileName) {
  const m = LEGACY.exec(fileName)
  if (!m) return null
  return { base: m[2] === 'Installer' ? 'RecoDo-Setup' : 'RecoDo', version: m[1] }
}
