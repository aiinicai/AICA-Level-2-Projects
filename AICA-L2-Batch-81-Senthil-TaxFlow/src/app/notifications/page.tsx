"use client"

import { useState, useEffect, useCallback } from "react"
import {
  CheckCheck,
  Info,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Inbox,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn, formatDateTime } from "@/lib/utils"

interface Notification {
  id: string
  userId: string
  title: string
  message: string
  type: string
  read: boolean
  link: string | null
  createdAt: string
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  INFO: Info,
  SUCCESS: CheckCircle2,
  WARNING: AlertTriangle,
  ERROR: XCircle,
  REMINDER: Clock,
  STATUS: FileText,
}

const TYPE_COLORS: Record<string, string> = {
  INFO: "text-blue-500 bg-blue-50",
  SUCCESS: "text-green-500 bg-green-50",
  WARNING: "text-amber-500 bg-amber-50",
  ERROR: "text-red-500 bg-red-50",
  REMINDER: "text-purple-500 bg-purple-50",
  STATUS: "text-sky-500 bg-sky-50",
}

function timeAgo(dateStr: string): string {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDateTime(dateStr)
}

function NotificationSkeleton() {
  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <Skeleton className="h-9 w-9 rounded-full shrink-0" />
      <div className="flex-1 space-y-2 min-w-0">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  )
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [marking, setMarking] = useState(false)

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/notifications")
      if (!res.ok) throw new Error("Failed to fetch")
      const json = await res.json()
      setNotifications(json.data || [])
      setUnreadCount(json.unreadCount || 0)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching is async
    fetchNotifications()
  }, [fetchNotifications])

  const markAllAsRead = useCallback(async () => {
    try {
      setMarking(true)
      const res = await fetch("/api/notifications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ all: true }),
      })
      if (!res.ok) throw new Error("Failed to mark all as read")
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
      setUnreadCount(0)
    } catch (err) {
      console.error(err)
    } finally {
      setMarking(false)
    }
  }, [])

  const markAsRead = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/notifications/${id}`, {
        method: "PUT",
      })
      if (!res.ok) throw new Error("Failed to mark as read")
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      )
      setUnreadCount((prev) => Math.max(0, prev - 1))
    } catch (err) {
      console.error(err)
    }
  }, [])

  return (
    <DashboardLayout title="Notifications">
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">
              Notifications
            </h2>
            {unreadCount > 0 && (
              <Badge variant="default" className="rounded-full px-2 py-0.5 text-xs">
                {unreadCount} unread
              </Badge>
            )}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={markAllAsRead}
              disabled={marking}
            >
              <CheckCheck className="h-4 w-4 mr-1.5" />
              {marking ? "Marking..." : "Mark all as read"}
            </Button>
          )}
        </div>

        <Card>
          <CardContent className="p-0 divide-y divide-[var(--color-border)]">
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <NotificationSkeleton key={i} />
              ))
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Inbox className="h-16 w-16 text-[var(--color-muted-foreground)] mb-4 opacity-40" />
                <h3 className="text-base font-medium text-[var(--color-foreground)] mb-1">
                  No notifications
                </h3>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  You&apos;re all caught up
                </p>
              </div>
            ) : (
              notifications.map((notification) => {
                const Icon = TYPE_ICONS[notification.type] || Info
                const iconColor = TYPE_COLORS[notification.type] || TYPE_COLORS.INFO
                return (
                  <button
                    key={notification.id}
                    onClick={() => !notification.read && markAsRead(notification.id)}
                    className={cn(
                      "flex items-start gap-3 px-4 py-3.5 w-full text-left transition-colors hover:bg-[var(--color-accent)]",
                      !notification.read && "bg-blue-50/50"
                    )}
                  >
                    <div
                      className={cn(
                        "h-9 w-9 rounded-full flex items-center justify-center shrink-0",
                        iconColor
                      )}
                    >
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p
                          className={cn(
                            "text-sm truncate",
                            !notification.read
                              ? "font-semibold text-[var(--color-foreground)]"
                              : "text-[var(--color-foreground)]"
                          )}
                        >
                          {notification.title}
                        </p>
                        {!notification.read && (
                          <span className="h-2 w-2 rounded-full bg-blue-500 shrink-0 mt-1.5" />
                        )}
                      </div>
                      <p className="text-xs text-[var(--color-muted-foreground)] mt-0.5 line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="text-[11px] text-[var(--color-muted-foreground)] mt-1">
                        {timeAgo(notification.createdAt)}
                      </p>
                    </div>
                  </button>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
