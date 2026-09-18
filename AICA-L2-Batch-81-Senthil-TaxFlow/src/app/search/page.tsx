"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import {
  Search,
  Building2,
  Globe,
  FileText,
  Users,
  CalendarCheck,
  Loader2,
  ArrowRight,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface SearchResult {
  type: string
  id: string
  title: string
  subtitle: string
  url: string
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  Entity: Building2,
  Country: Globe,
  "Compliance Schedule": CalendarCheck,
  Form: FileText,
  Employee: Users,
}

const TYPE_COLORS: Record<string, string> = {
  Entity: "text-blue-500 bg-blue-50",
  Country: "text-emerald-500 bg-emerald-50",
  "Compliance Schedule": "text-purple-500 bg-purple-50",
  Form: "text-amber-500 bg-amber-50",
  Employee: "text-rose-500 bg-rose-50",
}

const GROUP_ORDER = [
  "Compliance Schedule",
  "Entity",
  "Country",
  "Form",
  "Employee",
]

function SearchSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5">
          <Skeleton className="h-9 w-9 rounded-lg shrink-0" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function SearchPage() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const [prevQuery, setPrevQuery] = useState(query)
  if (query !== prevQuery) {
    setPrevQuery(query)
    if (query.length < 2) {
      setResults([])
      setSearched(false)
    }
  }

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (query.length >= 2) {
      const timer = setTimeout(async () => {
        setLoading(true)
        setSearched(true)
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
          if (!res.ok) throw new Error("Search failed")
          const json = await res.json()
          setResults(json.results || [])
        } catch {
          setResults([])
        } finally {
          setLoading(false)
        }
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [query])

  const grouped = GROUP_ORDER.map((type) => ({
    type,
    items: results.filter((r) => r.type === type),
  })).filter((g) => g.items.length > 0)

  const totalResults = results.length
  const hasResults = totalResults > 0

  return (
    <DashboardLayout title="Search">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--color-muted-foreground)]" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search entities, countries, compliance schedules, forms, employees..."
            className="pl-10 h-12 text-base"
          />
          {loading && (
            <Loader2 className="absolute right-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--color-muted-foreground)] animate-spin" />
          )}
        </div>

        {searched && !loading && !hasResults && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Search className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
            <h3 className="text-base font-medium text-[var(--color-foreground)] mb-1">
              No results found
            </h3>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              No matches for &quot;{query}&quot;. Try a different search term.
            </p>
          </div>
        )}

        {loading && searched && <SearchSkeleton />}

        {hasResults && !loading && (
          <div className="space-y-6">
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Found {totalResults} result{totalResults !== 1 ? "s" : ""} for &quot;{query}&quot;
            </p>
            {grouped.map((group) => {
              const Icon = TYPE_ICONS[group.type] || Search
              const iconColor = TYPE_COLORS[group.type] || TYPE_COLORS.Entity
              return (
                <div key={group.type}>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="rounded-sm px-2 py-0.5 text-xs font-normal">
                      {group.type}
                    </Badge>
                    <span className="text-xs text-[var(--color-muted-foreground)]">
                      {group.items.length}
                    </span>
                  </div>
                  <Card>
                    <CardContent className="p-0 divide-y divide-[var(--color-border)]">
                      {group.items.map((item) => (
                        <button
                          key={`${item.type}-${item.id}`}
                          onClick={() => router.push(item.url)}
                          className="flex items-center gap-3 px-4 py-3 w-full text-left transition-colors hover:bg-[var(--color-accent)]"
                        >
                          <div
                            className={cn(
                              "h-9 w-9 rounded-lg flex items-center justify-center shrink-0",
                              iconColor
                            )}
                          >
                            <Icon className="h-4.5 w-4.5" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[var(--color-foreground)] truncate">
                              {item.title}
                            </p>
                            {item.subtitle && (
                              <p className="text-xs text-[var(--color-muted-foreground)] truncate">
                                {item.subtitle}
                              </p>
                            )}
                          </div>
                          <ArrowRight className="h-4 w-4 text-[var(--color-muted-foreground)] shrink-0" />
                        </button>
                      ))}
                    </CardContent>
                  </Card>
                </div>
              )
            })}
          </div>
        )}

        {!searched && query.length < 2 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Search className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-20" />
            <h3 className="text-base font-medium text-[var(--color-foreground)] mb-1">
              Global Search
            </h3>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Type at least 2 characters to search across the platform
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
