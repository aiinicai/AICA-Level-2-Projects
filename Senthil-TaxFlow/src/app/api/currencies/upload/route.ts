import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { getActiveContextFromRequest } from "@/lib/auth-context"
import { newId, now } from "@/lib/db"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { orgId } = getActiveContextFromRequest(request)
    if (!orgId) {
      return NextResponse.json({ error: "No active organization" }, { status: 400 })
    }

    const { items } = await request.json()
    if (!items || !Array.isArray(items) || items.length === 0) {
      return NextResponse.json({ error: "Items array is required" }, { status: 400 })
    }

    let inserted = 0
    let skipped = 0
    const errors: string[] = []

    for (const item of items) {
      const { code, name, symbol, decimals, isBase } = item

      if (!code || !name) {
        skipped++
        errors.push(`Missing required fields for ${code || "unknown"}`)
        continue
      }

      const { data: existing } = await supabaseAdmin
        .from("currencies")
        .select("id")
        .eq("orgId", orgId)
        .eq("code", code.toUpperCase())
        .maybeSingle()

      if (existing) {
        const { error: updateError } = await supabaseAdmin
          .from("currencies")
          .update({
            name,
            symbol: symbol || null,
            decimals: parseInt(decimals) || 2,
            isBase: isBase === true || isBase === "true",
            updatedAt: now(),
          })
          .eq("id", existing.id)

        if (updateError) {
          errors.push(`Update failed for ${code}: ${updateError.message}`)
        } else {
          inserted++
        }
      } else {
        const { error: insertError } = await supabaseAdmin
          .from("currencies")
          .insert({
            id: newId(),
            orgId,
            code: code.toUpperCase(),
            name,
            symbol: symbol || null,
            decimals: parseInt(decimals) || 2,
            isBase: isBase === true || isBase === "true",
            updatedAt: now(),
          })

        if (insertError) {
          errors.push(`Insert failed for ${code}: ${insertError.message}`)
        } else {
          inserted++
        }
      }
    }

    return NextResponse.json({
      data: { inserted, skipped, total: items.length, errors: errors.length > 0 ? errors : undefined },
    })
  } catch (error) {
    console.error("POST /api/currencies/upload error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
