import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { rates } = body as { rates: { fromCurrency: string; rate: number; date: string }[] }

    if (!rates || !Array.isArray(rates) || rates.length === 0) {
      return NextResponse.json({ error: "Rates array is required" }, { status: 400 })
    }

    let inserted = 0
    let skipped = 0
    const errors: string[] = []

    for (const item of rates) {
      const { fromCurrency, rate, date } = item

      if (!fromCurrency || rate === undefined || !date) {
        skipped++
        errors.push(`Missing fields for ${fromCurrency || "unknown"} on ${date || "unknown"}`)
        continue
      }

      const { data: existing } = await supabaseAdmin
        .from("exchange_rates")
        .select("id")
        .eq("fromCurrency", fromCurrency.toUpperCase())
        .eq("date", date)
        .maybeSingle()

      if (existing) {
        const { error: updateError } = await supabaseAdmin
          .from("exchange_rates")
          .update({ rate })
          .eq("id", existing.id)

        if (updateError) {
          errors.push(`Update failed for ${fromCurrency} on ${date}: ${updateError.message}`)
        } else {
          inserted++
        }
      } else {
        const { error: insertError } = await supabaseAdmin
          .from("exchange_rates")
          .insert({
            fromCurrency: fromCurrency.toUpperCase(),
            toCurrency: "USD",
            rate,
            date,
          })

        if (insertError) {
          errors.push(`Insert failed for ${fromCurrency} on ${date}: ${insertError.message}`)
        } else {
          inserted++
        }
      }
    }

    return NextResponse.json({
      data: { inserted, skipped, total: rates.length, errors: errors.length > 0 ? errors : undefined },
    })
  } catch (error) {
    console.error("POST /api/exchange-rates/upload error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
