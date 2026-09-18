"use client"

import { useAuth } from "@/components/layout/providers"
import { useState } from "react"
import {
  User,
  Shield,
  Building,
  Hash,
  Mail,
  AtSign,
} from "lucide-react"
import DashboardLayout from "@/components/layout/dashboard-layout"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"

function SettingSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <Skeleton className="h-16 w-16 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-48" />
            </div>
          </div>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    </div>
  )
}

export default function SettingsPage() {
  const { user: sessionUser, loading, refresh } = useAuth()
  const [updatingRole, setUpdatingRole] = useState(false)
  const [updateMsg, setUpdateMsg] = useState<{ type: "success" | "error"; text: string } | null>(null)

  const user = sessionUser

  if (loading) {
    return (
      <DashboardLayout title="Settings">
        <SettingSkeleton />
      </DashboardLayout>
    )
  }

  async function handleRoleChange(role: string) {
    setUpdatingRole(true)
    setUpdateMsg(null)
    try {
      const res = await fetch("/api/users/me/role", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      })
      if (!res.ok) {
        const err = await res.json()
        setUpdateMsg({ type: "error", text: err.error || "Failed to update role" })
        return
      }
      await refresh()
      setUpdateMsg({ type: "success", text: "Role updated successfully" })
    } catch {
      setUpdateMsg({ type: "error", text: "Something went wrong" })
    } finally {
      setUpdatingRole(false)
    }
  }

  return (
    <DashboardLayout title="Settings">
      <div className="max-w-2xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <User className="h-5 w-5 text-[var(--color-muted-foreground)]" />
              Profile
            </CardTitle>
            <CardDescription>
              Your personal information and account details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                {user?.image ? (
                  <AvatarImage src={user.image} alt={user?.name || ""} />
                ) : (
                  <AvatarFallback className="text-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                    {(user?.name || "U").charAt(0).toUpperCase()}
                  </AvatarFallback>
                )}
              </Avatar>
              <div>
                <p className="font-medium text-[var(--color-foreground)]">
                  {user?.name || "Unnamed User"}
                </p>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  {user?.email}
                </p>
              </div>
            </div>

            <Separator />

            <div className="grid gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="name" className="text-xs text-[var(--color-muted-foreground)]">
                  Full Name
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
                  <Input
                    id="name"
                    value={user?.name || ""}
                    readOnly
                    className="pl-9"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-xs text-[var(--color-muted-foreground)]">
                    Email
                  </Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
                    <Input
                      id="email"
                      value={user?.email || ""}
                      readOnly
                      className="pl-9"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="username" className="text-xs text-[var(--color-muted-foreground)]">
                    Username
                  </Label>
                  <div className="relative">
                    <AtSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
                    <Input
                      id="username"
                      value={user?.username || ""}
                      readOnly
                      className="pl-9"
                    />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-[var(--color-muted-foreground)]" />
              Account
            </CardTitle>
            <CardDescription>
              Your role and organizational details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs text-[var(--color-muted-foreground)]">
                  Role
                </Label>
                <div className="relative">
                  <Shield className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
                  <Select
                    value={user?.role || "PREPARER"}
                    onValueChange={handleRoleChange}
                    disabled={updatingRole}
                  >
                    <SelectTrigger className="w-full pl-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ADMINISTRATOR">Administrator</SelectItem>
                      <SelectItem value="PREPARER">Preparer</SelectItem>
                      <SelectItem value="REVIEWER">Reviewer</SelectItem>
                      <SelectItem value="APPROVER">Approver</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {updatingRole && (
                  <p className="text-xs text-[var(--color-muted-foreground)]">Updating...</p>
                )}
                {updateMsg && (
                  <p
                    className={`text-xs ${
                      updateMsg.type === "success" ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {updateMsg.text}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-[var(--color-muted-foreground)]">
                  Department
                </Label>
                <div className="relative">
                  <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
                  <Input
                    value={user?.department || "—"}
                    readOnly
                    className="pl-9"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs text-[var(--color-muted-foreground)]">
                Employee ID
              </Label>
              <div className="relative">
                <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
                <Input
                  value={user?.employeeId || "—"}
                  readOnly
                  className="pl-9"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}