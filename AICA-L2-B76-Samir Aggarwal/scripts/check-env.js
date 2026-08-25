/**
 * Build-time guard.
 *
 * Vite inlines VITE_* variables into the bundle at build time. If they are
 * absent the build still "succeeds" and produces an artifact that can never
 * reach Supabase — a green tick in Railway hiding a dead app. This fails the
 * build loudly instead, before anything gets deployed.
 *
 * Uses Vite's own loadEnv so it reads exactly what the build will read:
 * .env files locally, and platform-injected variables on Railway.
 */

import { loadEnv } from 'vite'

const env = loadEnv('production', process.cwd(), 'VITE_')
const problems = []

const url = env.VITE_SUPABASE_URL?.trim()
const key = env.VITE_SUPABASE_ANON_KEY?.trim()

if (!url) {
  problems.push('VITE_SUPABASE_URL is not set.')
} else if (!/^https:\/\/[a-z0-9-]+\.supabase\.co\/?$/.test(url)) {
  problems.push(
    `VITE_SUPABASE_URL does not look like a Supabase project URL: "${url}"\n` +
      '     Expected https://<project-ref>.supabase.co',
  )
}

if (!key) {
  problems.push('VITE_SUPABASE_ANON_KEY is not set.')
} else if (/^sb_secret_/.test(key) || key.includes('service_role')) {
  // This one is worth failing hard for: the service key bypasses every RLS
  // policy, and putting it in a browser bundle would expose the whole database.
  problems.push(
    'VITE_SUPABASE_ANON_KEY looks like a SECRET / service_role key.\n' +
      '     Never ship that to the browser — it bypasses row-level security.\n' +
      '     Use the anon / publishable key (sb_publishable_… or the anon JWT).',
  )
} else if (/placeholder|replace-me|your-anon/i.test(key)) {
  problems.push('VITE_SUPABASE_ANON_KEY is still a placeholder value.')
}

if (problems.length) {
  console.error('\n\x1b[31m\x1b[1mBuild stopped: Supabase configuration is missing or wrong.\x1b[0m\n')
  for (const problem of problems) console.error(`  \x1b[31m✗\x1b[0m ${problem}`)
  console.error(
    '\n  Fix it:\n' +
      '    Locally  — copy .env.example to .env and fill both values in.\n' +
      '    Railway  — Service → Variables (environment: production), then redeploy.\n' +
      '               Project-level "Shared Variables" are NOT inherited by a\n' +
      '               service automatically; add them on the service itself.\n' +
      '\n  Both values live in Supabase → Project Settings → API.\n',
  )
  process.exit(1)
}

console.log(`✓ Supabase configuration present (${url})`)
