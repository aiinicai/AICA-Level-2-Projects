"use client"

import { useState, useRef } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"

import {
  Menu,
  Search,
  Bell,
  User,
  Settings,
  LogOut,
  ChevronDown,
  Command,
  Shield,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu"

function getInitials(name: string | null | undefined): string {
  if (!name) return "U"
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

interface AppHeaderProps {
  onMenuToggle: () => void
  title?: string
}

export function AppHeader({ onMenuToggle, title }: AppHeaderProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { user: sessionUser, refresh } = useAuth()
  const [searchQuery, setSearchQuery] = useState("")
  const searchRef = useRef<HTMLInputElement>(null)

  const pageTitle =
    title ||
    pathname
      .split("/")
      .filter(Boolean)
      .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
      .join(" / ")

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery("")
    }
  }

  const user = sessionUser
  const userName = user?.name || user?.username || "User"
  const userEmail = user?.email || ""
  const userImage = user?.image || null

  return (
    <header className="sticky top-0 z-30 h-16 bg-white/90 backdrop-blur-lg border-b border-[var(--color-border)]">
      <div className="flex items-center justify-between h-full px-4 lg:px-6 gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuToggle}
            className="lg:hidden h-9 w-9 text-[var(--color-muted-foreground)]"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="text-lg font-semibold text-[var(--color-foreground)]">
            {pageTitle}
          </h1>
        </div>

        <div className="hidden sm:flex items-center flex-1 max-w-md mx-auto">
          <form onSubmit={handleSearch} className="relative w-full">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted-foreground)]" />
            <Input
              ref={searchRef}
              type="text"
              placeholder="Search compliances, entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-9 bg-[var(--color-muted)] border-0 text-sm rounded-xl w-full focus-visible:ring-2 focus-visible:ring-[var(--color-ring)]/30 placeholder:text-[var(--color-muted-foreground)]"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-1 text-[10px] text-[var(--color-muted-foreground)]">
              <Command className="h-3 w-3" />
              <span>K</span>
            </div>
          </form>
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 text-[var(--color-muted-foreground)] hover:bg-[var(--color-muted)] rounded-xl relative"
            asChild
          >
            <Link href="/notifications">
              <Bell className="h-4 w-4" />
              <span className="absolute top-2 right-2 h-2 w-2 bg-[var(--color-primary)] rounded-full ring-2 ring-white" />
            </Link>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="flex items-center gap-2 h-9 pl-2 pr-3 rounded-xl hover:bg-[var(--color-muted)]"
              >
                <Avatar className="h-7 w-7">
                  {userImage ? <AvatarImage src={userImage} alt={userName} /> : null}
                  <AvatarFallback className="text-[10px] bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                    {getInitials(userName)}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden md:inline text-sm font-medium text-[var(--color-foreground)] max-w-[120px] truncate">
                  {userName}
                </span>
                <ChevronDown className="hidden md:inline h-3.5 w-3.5 text-[var(--color-muted-foreground)]" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56 rounded-xl border-[var(--color-border)] shadow-lg" align="end" sideOffset={8}>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{userName}</p>
                  <p className="text-xs leading-none text-muted-foreground">{userEmail}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                <DropdownMenuItem asChild>
                  <Link href="/settings" className="cursor-pointer">
                    <User className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings" className="cursor-pointer">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <Shield className="mr-2 h-4 w-4" />
                  <span>Role: <span className="font-medium">{user?.role || "PREPARER"}</span></span>
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  <DropdownMenuRadioGroup
                    value={user?.role || "PREPARER"}
                    onValueChange={async (role) => {
                      try {
                        const res = await fetch("/api/users/me/role", {
                          method: "PUT",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ role }),
                        })
                        if (res.ok) {
                          await refresh()
                        }
                      } catch {}
                    }}
                  >
                    <DropdownMenuRadioItem value="PREPARER">Preparer</DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="ADMINISTRATOR">Administrator</DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="REVIEWER">Reviewer</DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="APPROVER">Approver</DropdownMenuRadioItem>
                  </DropdownMenuRadioGroup>
                </DropdownMenuSubContent>
              </DropdownMenuSub>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-red-600 focus:text-red-600"
                onClick={async () => { await fetch("/api/auth/logout", { method: "POST" }); window.location.href = "/login" }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
