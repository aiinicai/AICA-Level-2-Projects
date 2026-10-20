// npm run dist: builds Reco-Do and puts the two Windows files in release/, keeping the previous build.
//
//   node scripts/package.mjs [--out <folder>]
//
// 1. electron-vite build.
// 2. electron-builder (installer + portable) into a separate output folder: --out <folder>, or by default a folder
//    in the system temp directory. On CI (CI=true) it builds straight into release/ and stops there.
// 3. If release/RecoDo-Setup.exe and release/RecoDo.exe exist, they move to release/previous-versions/ as
//    RecoDo-Setup-v<old version>.exe and RecoDo-v<old version>.exe (version from release/VERSION.txt, else from the
//    file's Windows version). Pre-1.1.2 files (Reco-Do-<version>-Installer.exe / -Portable-NoInstall.exe) move
//    there too. An existing backup is never overwritten: a second backup of one version gets -2, -3, ...
// 4. The new RecoDo-Setup.exe and RecoDo.exe are copied into release/.
// 5. release/VERSION.txt records "Reco-Do <version>, built <date>".

import { spawnSync, execFileSync } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, renameSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { RELEASE_FILES, backupName, cleanVersion, legacyRelease, versionFileText, versionFromVersionFile } from './release-naming.mjs'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const RELEASE = join(ROOT, 'release')
const PREVIOUS = join(RELEASE, 'previous-versions')
const VERSION_FILE = join(RELEASE, 'VERSION.txt')
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function fail(message) {
  console.error(`\npackage: ${message}`)
  process.exit(1)
}

function parseArgs(argv) {
  let out = null
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--out') {
      out = argv[++i]
      if (!out) fail('--out needs a folder.')
    } else if (argv[i].startsWith('--out=')) {
      out = argv[i].slice('--out='.length)
    } else {
      fail(`unknown argument "${argv[i]}". Usage: node scripts/package.mjs [--out <folder>]`)
    }
  }
  return out
}

/** Runs a package's CLI with this Node, from the project folder (no shell, so paths with spaces are safe). */
function runCli(label, script, args) {
  console.log(`\n> ${label}`)
  const r = spawnSync(process.execPath, [join(ROOT, 'node_modules', script), ...args], { cwd: ROOT, stdio: 'inherit' })
  if (r.error) fail(`${label} could not start: ${r.error.message}`)
  if (r.status !== 0) fail(`${label} failed (exit code ${r.status}).`)
}

function stamp(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getDate())}-${MONTHS[d.getMonth()]}-${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** The product version in an .exe's Windows properties ("1.1.1"), or null. */
function exeVersion(file) {
  if (process.platform !== 'win32') return null
  try {
    const out = execFileSync(
      'powershell.exe',
      ['-NoProfile', '-NonInteractive', '-Command', '$i = (Get-Item -LiteralPath $env:RECODO_EXE).VersionInfo; if ($i.ProductVersion) { $i.ProductVersion } else { $i.FileVersion }'],
      { env: { ...process.env, RECODO_EXE: file }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }
    )
    return cleanVersion(out)
  } catch {
    return null
  }
}

function recordedVersion() {
  return existsSync(VERSION_FILE) ? versionFromVersionFile(readFileSync(VERSION_FILE, 'utf8')) : null
}

/** Moves `from` into previous-versions under the next free name for base + version. */
function backUp(from, base, version) {
  mkdirSync(PREVIOUS, { recursive: true })
  const name = backupName(base, version, readdirSync(PREVIOUS))
  renameSync(from, join(PREVIOUS, name))
  console.log(`  kept ${name}`)
}

const outArg = parseArgs(process.argv.slice(2))
const onCi = !!process.env.CI && process.env.CI !== 'false'
const outDir = resolve(ROOT, outArg ?? (onCi ? 'release' : join(tmpdir(), 'reco-do-dist-out')))
const version = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8')).version
const builtAt = new Date()

runCli('electron-vite build', 'electron-vite/bin/electron-vite.js', ['build'])
runCli(`electron-builder (output: ${outDir})`, 'electron-builder/cli.js', ['--win', '--x64', '--publish', 'never', `--config.directories.output=${outDir}`])

for (const { file } of RELEASE_FILES) {
  if (!existsSync(join(outDir, file))) fail(`electron-builder did not produce ${file} in ${outDir}.`)
}

mkdirSync(RELEASE, { recursive: true })
if (outDir.toLowerCase() !== RELEASE.toLowerCase()) {
  console.log('\n> Keeping the previous build in release/previous-versions')
  // Pre-1.1.2 names carry their version in the name.
  for (const name of readdirSync(RELEASE)) {
    const legacy = legacyRelease(name)
    if (legacy) backUp(join(RELEASE, name), legacy.base, legacy.version)
  }
  const recorded = recordedVersion()
  for (const { file, base } of RELEASE_FILES) {
    const current = join(RELEASE, file)
    if (!existsSync(current)) continue
    const old = recorded ?? exeVersion(current)
    if (!old) fail(`the version of release/${file} is unknown (no release/VERSION.txt and no file version). Move it away by hand and run again.`)
    backUp(current, base, old)
  }
  console.log('\n> Copying the new build into release/')
  for (const { file } of RELEASE_FILES) {
    copyFileSync(join(outDir, file), join(RELEASE, file))
    console.log(`  release/${file}`)
  }
}

writeFileSync(VERSION_FILE, versionFileText(version, stamp(builtAt)))
console.log(`  release/VERSION.txt (Reco-Do ${version})`)
console.log(`\nDone: Reco-Do ${version}. RecoDo-Setup.exe installs it; RecoDo.exe runs it without installing.`)
