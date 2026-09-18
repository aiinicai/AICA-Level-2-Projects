import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { items } = await request.json()
    if (!items || !Array.isArray(items) || items.length === 0) {
      return NextResponse.json({ error: "Items array is required" }, { status: 400 })
    }

    let inserted = 0
    let skipped = 0
    const errors: string[] = []

    for (const item of items) {
      const { name, code, region } = item

      if (!name || !code) {
        skipped++
        errors.push(`Missing required fields for ${name || "unknown"}`)
        continue
      }

      const { data: existing } = await supabaseAdmin
        .from("countries")
        .select("id")
        .or(`name.eq.${name},code.eq.${code}`)
        .maybeSingle()

      if (existing) {
        const { error: updateError } = await supabaseAdmin
          .from("countries")
          .update({ region })
          .eq("id", existing.id)

        if (updateError) {
          errors.push(`Update failed for ${name}: ${updateError.message}`)
        } else {
          inserted++
        }
      } else {
        const { error: insertError } = await supabaseAdmin
          .from("countries")
          .insert({
            name,
            code: code.toUpperCase(),
            region,
          })

        if (insertError) {
          errors.push(`Insert failed for ${name}: ${insertError.message}`)
        } else {
          inserted++
        }
      }
    }

    return NextResponse.json({
      data: { inserted, skipped, total: items.length, errors: errors.length > 0 ? errors : undefined },
    })
  } catch (error) {
    console.error("POST /api/countries/upload error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
