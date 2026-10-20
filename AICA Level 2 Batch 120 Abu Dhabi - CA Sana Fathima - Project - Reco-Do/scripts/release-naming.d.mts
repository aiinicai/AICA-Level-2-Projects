// Types for scripts/release-naming.mjs (so the Vitest tests are type-checked).

export declare const RELEASE_FILES: ReadonlyArray<{ file: string; base: string }>
export declare function cleanVersion(raw: unknown): string | null
export declare function versionFromVersionFile(text: unknown): string | null
export declare function versionFileText(version: string, builtAt: string): string
export declare function backupName(base: string, version: string, taken: Iterable<string>): string
export declare function legacyRelease(fileName: string): { base: string; version: string } | null
