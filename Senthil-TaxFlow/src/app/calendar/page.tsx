"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import {
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  List,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface ComplianceItem {
  id: string
  complianceId: string
  entity: { entityName: string }
  country: { name: string; code: string }
  complianceType: { name: string }
  dueDate: string
  status: string
  priority: string
}

const STATUS_COLORS: Record<string, string> = {
  OVERDUE: "bg-red-500",
  DUE_TODAY: "bg-orange-500",
  COMPLETED: "bg-green-500",
  PENDING: "bg-blue-500",
  REJECTED: "bg-red-500",
}

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-800",
  PENDING_ADMIN_APPROVAL: "bg-amber-100 text-amber-800",
  PENDING_REVIEW: "bg-cyan-100 text-cyan-800",
  PENDING_PREPARATION: "bg-yellow-100 text-yellow-800",
  PREPARED: "bg-blue-100 text-blue-800",
  PENDING_APPROVAL: "bg-purple-100 text-purple-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  FILED: "bg-emerald-100 text-emerald-800",
  PAID: "bg-teal-100 text-teal-800",
  CLOSED: "bg-slate-100 text-slate-800",
}

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay()
}

function isOverdue(dueDate: string): boolean {
  return new Date(dueDate) < new Date(new Date().toDateString())
}

function isToday(dueDate: string): boolean {
  const d = new Date(dueDate)
  const today = new Date()
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  )
}

function getDateStatus(item: ComplianceItem): string {
  if (["APPROVED", "FILED", "PAID", "CLOSED"].includes(item.status)) return "COMPLETED"
  if (item.status === "REJECTED") return "REJECTED"
  if (isOverdue(item.dueDate)) return "OVERDUE"
  if (isToday(item.dueDate)) return "DUE_TODAY"
  return "PENDING"
}

function CalendarSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: 35 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
    </div>
  )
}

export default function CalendarPage() {
  const [compliances, setCompliances] = useState<ComplianceItem[]>([])
  const [loading, setLoading] = useState(true)
  const [currentDate, setCurrentDate] = useState(new Date())
  const [view, setView] = useState("month")

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  const fetchCompliances = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/compliance?limit=100")
      if (!res.ok) throw new Error("Failed to fetch")
      const json = await res.json()
      setCompliances(json.data || [])
    } catch {
      setCompliances([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchCompliances()
  }, [fetchCompliances])

  const navigateMonth = useCallback((dir: number) => {
    setCurrentDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + dir, 1))
  }, [])

  const navigateWeek = useCallback((dir: number) => {
    setCurrentDate((prev) => new Date(prev.getFullYear(), prev.getMonth(), prev.getDate() + 7 * dir))
  }, [])

  const daysInMonth = getDaysInMonth(year, month)
  const firstDay = getFirstDayOfMonth(year, month)

  const calendarDays = useMemo(() => {
    const days: { date: Date; items: ComplianceItem[] }[] = []

    for (let i = 0; i < firstDay; i++) {
      const prevMonthDate = new Date(year, month, -firstDay + i + 1)
      days.push({ date: prevMonthDate, items: [] })
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, month, d)
      const items = compliances.filter((c) => {
        const due = new Date(c.dueDate)
        return (
          due.getFullYear() === date.getFullYear() &&
          due.getMonth() === date.getMonth() &&
          due.getDate() === date.getDate()
        )
      })
      days.push({ date, items })
    }

    const remaining = 42 - days.length
    for (let i = 1; i <= remaining; i++) {
      const nextMonthDate = new Date(year, month + 1, i)
      days.push({ date: nextMonthDate, items: [] })
    }

    return days
  }, [year, month, daysInMonth, firstDay, compliances])

  const weekDays = useMemo(() => {
    const startOfWeek = new Date(currentDate)
    startOfWeek.setDate(startOfWeek.getDate() - startOfWeek.getDay())
    const days: { date: Date; items: ComplianceItem[] }[] = []
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek)
      date.setDate(startOfWeek.getDate() + i)
      const items = compliances.filter((c) => {
        const due = new Date(c.dueDate)
        return (
          due.getFullYear() === date.getFullYear() &&
          due.getMonth() === date.getMonth() &&
          due.getDate() === date.getDate()
        )
      })
      days.push({ date, items })
    }
    return days
  }, [currentDate, compliances])

  const agendaItems = useMemo(() => {
    return [...compliances]
      .filter((c) => {
        const due = new Date(c.dueDate)
        const today = new Date()
        today.setHours(0, 0, 0, 0)
        return due >= today
      })
      .sort((a, b) => new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime())
      .slice(0, 50)
  }, [compliances])

  return (
    <DashboardLayout title="Calendar">
      <div className="space-y-4">
        <Tabs value={view} onValueChange={setView}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {view === "week" ? (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={() => navigateWeek(-1)}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <h2 className="text-lg font-semibold text-[var(--color-foreground)]">
                    {weekDays[0]?.date.toLocaleDateString("en-US", { month: "short", day: "numeric" })} -{" "}
                    {weekDays[6]?.date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </h2>
                  <Button variant="ghost" size="icon" onClick={() => navigateWeek(1)}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={() => navigateMonth(-1)}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <h2 className="text-lg font-semibold text-[var(--color-foreground)]">
                    {MONTHS[month]} {year}
                  </h2>
                  <Button variant="ghost" size="icon" onClick={() => navigateMonth(1)}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
            <TabsList>
              <TabsTrigger value="month" className="flex items-center gap-1.5">
                <CalendarDays className="h-4 w-4" />
                Month
              </TabsTrigger>
              <TabsTrigger value="week" className="flex items-center gap-1.5">
                <CalendarDays className="h-4 w-4" />
                Week
              </TabsTrigger>
              <TabsTrigger value="agenda" className="flex items-center gap-1.5">
                <List className="h-4 w-4" />
                Agenda
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="month" className="mt-4">
            {loading ? (
              <CalendarSkeleton />
            ) : (
              <>
                <div className="grid grid-cols-7 gap-px bg-[var(--color-border)] rounded-lg overflow-hidden">
                  {DAYS.map((day) => (
                    <div
                      key={day}
                      className="bg-[var(--color-card)] px-2 py-1.5 text-center text-xs font-medium text-[var(--color-muted-foreground)]"
                    >
                      {day}
                    </div>
                  ))}
                  {calendarDays.map((day, i) => {
                    const isCurrentMonth = day.date.getMonth() === month
                    const isTodayDate = isToday(day.date.toISOString())
                    return (
                      <div
                        key={i}
                        className={cn(
                          "bg-[var(--color-card)] min-h-[100px] p-1.5 transition-colors",
                          !isCurrentMonth && "opacity-40",
                          isTodayDate && "ring-2 ring-blue-500/40 ring-inset"
                        )}
                      >
                        <span
                          className={cn(
                            "inline-flex items-center justify-center h-6 w-6 text-xs rounded-full",
                            isTodayDate &&
                              "bg-blue-500 text-white font-semibold"
                          )}
                        >
                          {day.date.getDate()}
                        </span>
                        <div className="mt-1 space-y-0.5">
                          {day.items.slice(0, 3).map((item) => {
                            const status = getDateStatus(item)
                            return (
                              <div
                                key={item.id}
                                className="flex items-center gap-1 px-1 py-0.5 rounded cursor-pointer hover:bg-[var(--color-accent)]"
                                title={`${item.complianceId} - ${item.entity.entityName}`}
                              >
                                <span
                                  className={cn(
                                    "h-1.5 w-1.5 rounded-full shrink-0",
                                    STATUS_COLORS[status]
                                  )}
                                />
                                <span className="text-[11px] truncate text-[var(--color-foreground)]">
                                  {item.complianceId}
                                </span>
                              </div>
                            )
                          })}
                          {day.items.length > 3 && (
                            <span className="text-[11px] text-[var(--color-muted-foreground)] pl-1">
                              +{day.items.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
                <Legend />
              </>
            )}
          </TabsContent>

          <TabsContent value="week" className="mt-4">
            {loading ? (
              <CalendarSkeleton />
            ) : (
              <>
                <div className="grid grid-cols-7 gap-px bg-[var(--color-border)] rounded-lg overflow-hidden">
                  {DAYS.map((day) => (
                    <div
                      key={day}
                      className="bg-[var(--color-card)] px-2 py-1.5 text-center text-xs font-medium text-[var(--color-muted-foreground)]"
                    >
                      {day}
                    </div>
                  ))}
                  {weekDays.map((day, i) => {
                    const isTodayDate = isToday(day.date.toISOString())
                    return (
                      <div
                        key={i}
                        className={cn(
                          "bg-[var(--color-card)] min-h-[200px] p-1.5 transition-colors",
                          isTodayDate && "ring-2 ring-blue-500/40 ring-inset"
                        )}
                      >
                        <span
                          className={cn(
                            "inline-flex items-center justify-center h-6 w-6 text-xs rounded-full",
                            isTodayDate &&
                              "bg-blue-500 text-white font-semibold"
                          )}
                        >
                          {day.date.getDate()}
                        </span>
                        <div className="mt-1 space-y-0.5">
                          {day.items.map((item) => {
                            const status = getDateStatus(item)
                            return (
                              <div
                                key={item.id}
                                className="flex items-center gap-1 px-1 py-0.5 rounded cursor-pointer hover:bg-[var(--color-accent)]"
                              >
                                <span
                                  className={cn(
                                    "h-1.5 w-1.5 rounded-full shrink-0",
                                    STATUS_COLORS[status]
                                  )}
                                />
                                <span className="text-[11px] truncate text-[var(--color-foreground)]">
                                  {item.complianceId}
                                </span>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                </div>
                <Legend />
              </>
            )}
          </TabsContent>

          <TabsContent value="agenda" className="mt-4">
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-lg" />
                ))}
              </div>
            ) : agendaItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <CalendarDays className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
                <h3 className="text-base font-medium text-[var(--color-foreground)] mb-1">
                  No upcoming compliances
                </h3>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  All compliances are completed or up to date
                </p>
              </div>
            ) : (
              <Card>
                <CardContent className="p-0 divide-y divide-[var(--color-border)]">
                  {agendaItems.map((item) => {
                    const dueDate = new Date(item.dueDate)
                    const overdue = isOverdue(item.dueDate)
                    const today = isToday(item.dueDate)
                    return (
                      <div
                        key={item.id}
                        className="flex items-center gap-4 px-4 py-3 hover:bg-[var(--color-accent)] transition-colors"
                      >
                        <div className="flex flex-col items-center justify-center w-12 shrink-0">
                          <span className="text-lg font-bold text-[var(--color-foreground)] leading-tight">
                            {dueDate.getDate()}
                          </span>
                          <span className="text-[11px] text-[var(--color-muted-foreground)]">
                            {MONTHS[dueDate.getMonth()].slice(0, 3)}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-[var(--color-foreground)] truncate">
                            {item.complianceId}
                          </p>
                          <p className="text-xs text-[var(--color-muted-foreground)] truncate">
                            {item.entity?.entityName} &middot; {item.country?.name}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs",
                              STATUS_BADGE[item.status] || ""
                            )}
                          >
                            {item.status.replace(/_/g, " ")}
                          </Badge>
                          {overdue && (
                            <Badge variant="destructive" className="text-xs">
                              Overdue
                            </Badge>
                          )}
                          {today && !overdue && (
                            <Badge className="text-xs bg-orange-500 text-white hover:bg-orange-600">
                              Today
                            </Badge>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}

function Legend() {
  const items = [
    { label: "Overdue", color: "bg-red-500" },
    { label: "Due Today", color: "bg-orange-500" },
    { label: "Completed", color: "bg-green-500" },
    { label: "Pending", color: "bg-blue-500" },
    { label: "Rejected", color: "bg-red-500" },
  ]
  return (
    <div className="flex flex-wrap items-center gap-4 mt-4 px-1">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span className={cn("h-2.5 w-2.5 rounded-full", item.color)} />
          <span className="text-xs text-[var(--color-muted-foreground)]">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  )
}
