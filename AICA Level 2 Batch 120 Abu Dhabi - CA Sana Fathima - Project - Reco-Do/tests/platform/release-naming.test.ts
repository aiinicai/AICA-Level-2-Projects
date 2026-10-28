import { describe, expect, it } from 'vitest'
import { backupName, cleanVersion, legacyRelease, versionFileText, versionFromVersionFile } from '../../scripts/release-naming.mjs'

describe('release naming', () => {
  it('names a backup with its exact version', () => {
    expect(backupName('RecoDo-Setup', '1.1.1', [])).toBe('RecoDo-Setup-v1.1.1.exe')
    expect(backupName('RecoDo', '1.1.1', ['RecoDo-Setup-v1.1.1.exe'])).toBe('RecoDo-v1.1.1.exe')
  })

  it('never reuses an existing backup name (case-insensitive)', () => {
    expect(backupName('RecoDo', '1.1.2', ['recodo-v1.1.2.exe'])).toBe('RecoDo-v1.1.2-2.exe')
    expect(backupName('RecoDo', '1.1.2', ['RecoDo-v1.1.2.exe', 'RecoDo-v1.1.2-2.exe'])).toBe('RecoDo-v1.1.2-3.exe')
  })

  it('reads versions from VERSION.txt and Windows file versions', () => {
    const text = versionFileText('1.1.2', '18-Oct-2026 23:10')
    expect(text).toBe('Reco-Do 1.1.2, built 18-Oct-2026 23:10\n')
    expect(versionFromVersionFile(text)).toBe('1.1.2')
    expect(versionFromVersionFile('something else')).toBeNull()
    expect(cleanVersion('1.1.1.0')).toBe('1.1.1')
    expect(cleanVersion(' v2.0.0-beta.1 ')).toBe('2.0.0-beta.1')
    expect(cleanVersion('')).toBeNull()
    expect(cleanVersion('1.1')).toBeNull()
  })

  it('maps the pre-1.1.2 file names to the new backup names', () => {
    expect(legacyRelease('Reco-Do-1.1.1-Installer.exe')).toEqual({ base: 'RecoDo-Setup', version: '1.1.1' })
    expect(legacyRelease('Reco-Do-1.1.1-Portable-NoInstall.exe')).toEqual({ base: 'RecoDo', version: '1.1.1' })
    expect(legacyRelease('RecoDo.exe')).toBeNull()
    expect(legacyRelease('Reco-Do-1.1.1-Installer.exe.blockmap')).toBeNull()
  })
})
