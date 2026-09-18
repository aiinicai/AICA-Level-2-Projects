import { supabaseAdmin } from "@/lib/supabase"
import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data, error } = await supabaseAdmin
      .from("exchange_rates")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (error) throw error

    if (!data) {
      return NextResponse.json({ error: "Exchange rate not found" }, { status: 404 })
    }

    return NextResponse.json({ data })
  } catch (error) {
    console.error("GET /api/exchange-rates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params
    const body = await request.json()
    const { fromCurrency, rate, date } = body

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("exchange_rates")
      .select("*")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Exchange rate not found" }, { status: 404 })
    }

    const newCurrency = fromCurrency ? fromCurrency.toUpperCase() : existing.fromCurrency
    const newDate = date || existing.date

    if (newCurrency !== existing.fromCurrency || newDate !== existing.date) {
      const { data: conflict } = await supabaseAdmin
        .from("exchange_rates")
        .select("id")
        .eq("fromCurrency", newCurrency)
        .eq("date", newDate)
        .neq("id", id)
        .maybeSingle()

      if (conflict) {
        return NextResponse.json({ error: "Exchange rate for this currency and date already exists" }, { status: 400 })
      }
    }

    const { data, error } = await supabaseAdmin
      .from("exchange_rates")
      .update({
        ...(fromCurrency !== undefined && { fromCurrency: fromCurrency.toUpperCase() }),
        ...(rate !== undefined && { rate }),
        ...(date !== undefined && { date }),
      })
      .eq("id", id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json({ data })
  } catch (error) {
    console.error("PUT /api/exchange-rates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth()
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { id } = await params

    const { data: existing, error: fetchError } = await supabaseAdmin
      .from("exchange_rates")
      .select("id")
      .eq("id", id)
      .maybeSingle()

    if (fetchError) throw fetchError

    if (!existing) {
      return NextResponse.json({ error: "Exchange rate not found" }, { status: 404 })
    }

    const { error } = await supabaseAdmin
      .from("exchange_rates")
      .delete()
      .eq("id", id)

    if (error) throw error

    return NextResponse.json({ data: { message: "Exchange rate deleted successfully" } })
  } catch (error) {
    console.error("DELETE /api/exchange-rates/[id] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
