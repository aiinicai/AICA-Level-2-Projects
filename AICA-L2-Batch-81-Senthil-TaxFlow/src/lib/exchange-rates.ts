import { supabaseAdmin } from "./supabase"

export async function convertToUSD(
  amount: number | null | undefined,
  fromCurrency: string | null | undefined,
  date: string | Date | null | undefined
): Promise<number | null> {
  if (!amount || !fromCurrency || fromCurrency.toUpperCase() === "USD") return amount ?? null

  const targetDate = date ? new Date(date) : new Date()

  const year = targetDate.getFullYear()
  const month = String(targetDate.getMonth() + 1).padStart(2, "0")
  const monthStart = `${year}-${month}-01`
  const monthEnd = `${year}-${month}-31`

  const { data: exactRate } = await supabaseAdmin
    .from("exchange_rates")
    .select("rate")
    .eq("fromCurrency", fromCurrency.toUpperCase())
    .eq("toCurrency", "USD")
    .gte("date", monthStart)
    .lte("date", monthEnd)
    .order("date", { ascending: false })
    .limit(1)
    .maybeSingle()

  if (exactRate) {
    return amount / Number(exactRate.rate)
  }

  const { data: latestRate } = await supabaseAdmin
    .from("exchange_rates")
    .select("rate")
    .eq("fromCurrency", fromCurrency.toUpperCase())
    .eq("toCurrency", "USD")
    .lte("date", monthEnd)
    .order("date", { ascending: false })
    .limit(1)
    .maybeSingle()

  if (latestRate) {
    return amount / Number(latestRate.rate)
  }

  return null
}

export async function fetchExchangeRatesForDate(date: string): Promise<Record<string, number>> {
  const targetDate = new Date(date)
  const year = targetDate.getFullYear()
  const month = String(targetDate.getMonth() + 1).padStart(2, "0")
  const monthStart = `${year}-${month}-01`
  const monthEnd = `${year}-${month}-31`

  const { data: monthRates } = await supabaseAdmin
    .from("exchange_rates")
    .select("fromCurrency, rate")
    .eq("toCurrency", "USD")
    .gte("date", monthStart)
    .lte("date", monthEnd)
    .order("date", { ascending: false })

  if (monthRates && monthRates.length > 0) {
    const map: Record<string, number> = {}
    for (const r of monthRates) {
      if (!map[r.fromCurrency]) {
        map[r.fromCurrency] = Number(r.rate)
      }
    }
    return map
  }

  const { data: allRates } = await supabaseAdmin
    .from("exchange_rates")
    .select("fromCurrency, rate")
    .eq("toCurrency", "USD")
    .lte("date", monthEnd)
    .order("date", { ascending: false })

  if (allRates) {
    const map: Record<string, number> = {}
    for (const r of allRates) {
      if (!map[r.fromCurrency]) {
        map[r.fromCurrency] = Number(r.rate)
      }
    }
    return map
  }

  return {}
}
