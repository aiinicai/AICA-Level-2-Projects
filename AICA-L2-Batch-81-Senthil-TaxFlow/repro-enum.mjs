import { readFileSync } from "node:fs"
import { createClient } from "@supabase/supabase-js"

const env = {}
for (const line of readFileSync("C:/apps/Lucid/TaxFlow/.env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Z0-9_]+)\s*=\s*(.*)$/)
  if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "")
}
const supabase = createClient(env.NEXT_PUBLIC_SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, { auth: { persistSession: false } })

const { data, error } = await supabase.from("template_change_requests").select("id").limit(1)
if (error && error.code === "42P01") {
  console.error("TABLE MISSING")
  process.exit(1)
}

const { data: sched, error: schedErr } = await supabase.from("compliance_schedules").select("status").limit(1)
if (schedErr) {
  console.error("SCHEDULE QUERY FAILED:", schedErr.message)
  process.exit(1)
}
console.log("TABLE OK; enum check sample status:", sched?.[0]?.status ?? null)