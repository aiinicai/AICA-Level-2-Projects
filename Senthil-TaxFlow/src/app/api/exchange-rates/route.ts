import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function GET(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const search = searchParams.get("search") || ""

    let query = supabaseAdmin
      .from("exchange_rates")
      .select("*", { count: "exact", head: false })

    if (search) {
      const pattern = `*${search}*`
      query = query.or(`fromCurrency.ilike.${pattern},toCurrency.ilike.${pattern}`)
    }

    query = query.order("date", { ascending: false })

    const { data, count, error } = await query

    if (error) throw error

    return NextResponse.json({ data: data || [], total: count ?? 0 })
  } catch (error) {
    console.error("GET /api/exchange-rates error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { fromCurrency, rate, date } = body

    if (!fromCurrency || rate === undefined || !date) {
      return NextResponse.json({ error: "fromCurrency, rate, and date are required" }, { status: 400 })
    }

    const { data: existing } = await supabaseAdmin
      .from("exchange_rates")
      .select("id")
      .eq("fromCurrency", fromCurrency.toUpperCase())
      .eq("date", date)
      .maybeSingle()

    if (existing) {
      return NextResponse.json({ error: "Exchange rate for this currency and date already exists" }, { status: 400 })
    }

    const { data, error } = await supabaseAdmin
      .from("exchange_rates")
      .insert({
        fromCurrency: fromCurrency.toUpperCase(),
        toCurrency: "USD",
        rate,
        date,
      })
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ data }, { status: 201 })
  } catch (error) {
    console.error("POST /api/exchange-rates error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
