import { supabaseAdmin } from "@/lib/supabase"

export async function generateTemplateNumber(
  taxType: string,
  countryCode: string,
  orgId: string
): Promise<string> {
  const prefix = `TPL-${taxType}-${countryCode}`

  const { data: existing } = await supabaseAdmin
    .from("compliance_templates")
    .select("templateNumber")
    .eq("orgId", orgId)
    .ilike("templateNumber", `${prefix}-%`)
    .order("templateNumber", { ascending: false })
    .limit(1)

  let seq = 1
  if (existing && existing.length > 0) {
    const last = existing[0].templateNumber as string
    const parts = last.split("-")
    const lastNum = parseInt(parts[parts.length - 1], 10)
    if (!isNaN(lastNum)) seq = lastNum + 1
  }

  return `${prefix}-${String(seq).padStart(3, "0")}`
}
