"use client"

import { useState, useCallback, type ComponentType } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import { useHydrated, useSidebarCollapsed } from "@/lib/hooks"

import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  CalendarCheck,
  Database,
  BarChart3,
  Calendar,
  Bell,
  Search,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Globe,
  Building,
  FileType,
  Files,
  Users,
  DollarSign,
  Coins,
  Tag,
  LogOut,
  Plus,
  Check,
  ClipboardList,
  ClipboardPlus,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@radix-ui/react-collapsible"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const navItems: {
  title: string
  href?: string
  icon: ComponentType<{ className?: string }>
  children?: {
    title: string
    href: string
    icon: ComponentType<{ className?: string }>
    children?: { title: string; href: string; icon: ComponentType<{ className?: string }> }[]
  }[]
}[] = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  {
    title: "Compliance Home",
    icon: CalendarCheck,
    children: [
      {
        title: "Obligations Tracker",
        href: "/compliance",
        icon: ClipboardList,
        children: [
          { title: "Ad-hoc Templates", href: "/compliance/ad-hoc", icon: ClipboardPlus },
          { title: "Recurring Templates", href: "/master/compliance-templates", icon: FileType },
        ],
      },
    ],
  },
  {
    title: "Master Data",
    icon: Database,
    children: [
      { title: "Countries", href: "/master/countries", icon: Globe },
      { title: "Entities", href: "/master/entities", icon: Building },
      { title: "Tax Types", href: "/master/tax-types", icon: Tag },
      { title: "Forms", href: "/master/forms", icon: Files },
      { title: "Employees", href: "/master/employees", icon: Users },
      { title: "Currencies", href: "/master/currencies", icon: Coins },
      { title: "Exchange Rates", href: "/master/exchange-rates", icon: DollarSign },
    ],
  },
  { title: "Reports", href: "/reports", icon: BarChart3 },
  { title: "Calendar View", href: "/calendar", icon: Calendar },
  { title: "Notifications", href: "/notifications", icon: Bell },
  { title: "Search", href: "/search", icon: Search },
  { title: "Settings", href: "/settings", icon: Settings },
]

function getInitials(name: string | null | undefined): string {
  if (!name) return "U"
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

interface AppSidebarProps {
  open: boolean
  onClose: () => void
}

function OrgSwitcher({ collapsed }: { collapsed: boolean }) {
  const { user, activeOrgId, activeRole, setActiveContext } = useAuth()
  const router = useRouter()

  const currentOrg = user?.orgs?.find((o) => o.id === activeOrgId)
  const availableRoles = currentOrg?.roles || []

  if (collapsed) {
    return (
      <div className="px-2 py-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-10 w-10 mx-auto text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/10">
              <Building className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" sideOffset={8} className="w-56">
            {user?.orgs?.map((org) => (
              <DropdownMenuItem
                key={org.id}
                className={cn("cursor-pointer", org.id === activeOrgId && "bg-[var(--color-primary)]/10 text-[var(--color-primary)]")}
                onClick={() => {
                  const role = org.roles.includes(activeRole) ? activeRole : org.roles[0] || "PREPARER"
                  setActiveContext(org.id, role)
                  router.refresh()
                }}
              >
                <Building className="h-4 w-4 mr-2" />
                <span className="flex-1">{org.name}</span>
                {org.id === activeOrgId && <Check className="h-4 w-4" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    )
  }

  return (
    <div className="px-3 py-2 border-b border-[var(--color-border)]">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="flex items-center gap-2 w-full h-9 px-2 rounded-lg hover:bg-[var(--color-primary)]/10 text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)]"
          >
            <Building className="h-4 w-4 shrink-0" />
            <span className="flex-1 text-left text-sm font-medium truncate">
              {currentOrg?.name || "Select Org"}
            </span>
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[var(--color-muted-foreground)]" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" sideOffset={4}>
          <DropdownMenuLabel>Organizations</DropdownMenuLabel>
          <DropdownMenuGroup>
            {user?.orgs?.map((org) => (
              <DropdownMenuItem
                key={org.id}
                className={cn("cursor-pointer", org.id === activeOrgId && "bg-[var(--color-primary)]/10 text-[var(--color-primary)]")}
                onClick={() => {
                  const role = org.roles.includes(activeRole) ? activeRole : org.roles[0] || "PREPARER"
                  setActiveContext(org.id, role)
                  router.refresh()
                }}
              >
                <Building className="h-4 w-4 mr-2" />
                <span className="flex-1">{org.name}</span>
                {org.id === activeOrgId && <Check className="h-4 w-4" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/dashboard" className="cursor-pointer">
              <Plus className="h-4 w-4 mr-2" />
              Create Organization
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {currentOrg && availableRoles.length > 1 && (
        <div className="mt-2.5">
          <div className="flex items-center justify-between px-0.5 mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-muted-foreground)]">
              Active Role
            </span>
            <span className="text-[10px] font-medium text-[var(--color-primary)]">
              {activeRole === "ADMINISTRATOR" ? "Admin" : activeRole.charAt(0) + activeRole.slice(1).toLowerCase()}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-1 p-1 bg-black/5 dark:bg-white/5 rounded-lg border border-[var(--color-border)]">
            {availableRoles.map((r) => {
              const isSelected = activeRole === r
              const label = r === "ADMINISTRATOR" ? "Admin" : r.charAt(0) + r.slice(1).toLowerCase()
              return (
                <button
                  key={r}
                  type="button"
                  onClick={() => {
                    if (activeOrgId) {
                      setActiveContext(activeOrgId, r)
                      router.refresh()
                    }
                  }}
                  className={cn(
                    "flex items-center justify-center text-xs font-medium py-1.5 px-2 rounded-md transition-all text-center truncate",
                    isSelected
                      ? "bg-white dark:bg-zinc-800 text-[var(--color-primary)] font-semibold shadow-xs border border-[var(--color-border)]"
                      : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-black/5 dark:hover:bg-white/5"
                  )}
                  title={r}
                >
                  <span className="truncate">{label}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function NavItems({ collapsed, onClose }: { collapsed: boolean; onClose: () => void }) {
  const pathname = usePathname()
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({})

  const isActive = useCallback(
    (href: string) => {
      if (href === "/dashboard") return pathname === href
      return pathname.startsWith(href)
    },
    [pathname]
  )

  const isParentActive = useCallback(
    (children: { href: string; children?: { href: string }[] }[]): boolean =>
      children.some((c) => {
        if (c.children?.length) {
          return pathname.startsWith(c.href) || isParentActive(c.children)
        }
        return pathname.startsWith(c.href)
      }),
    [pathname]
  )

  const [prevPathname, setPrevPathname] = useState(pathname)
  if (pathname !== prevPathname) {
    setPrevPathname(pathname)
    setOpenMenus((prev) => {
      const next = { ...prev }
      for (const item of navItems) {
        if (item.children && isParentActive(item.children)) {
          next[item.title] = true
        }
      }
      return next
    })
  }

  const toggleMenu = (title: string) => {
    setOpenMenus((prev) => ({ ...prev, [title]: !prev[title] }))
  }

  return (
    <>
      {navItems.map((item) => {
        if (item.children) {
          const parentActive = isParentActive(item.children)
          const isOpen = openMenus[item.title] ?? parentActive

          if (collapsed) {
            return (
              <div key={item.title} className="relative group">
                <div
                  className={cn(
                    "flex items-center justify-center h-10 w-10 mx-auto rounded-lg transition-colors",
                    parentActive
                      ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                      : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/10"
                  )}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                </div>
                <div className="absolute left-full ml-2 top-0 hidden group-hover:block z-50">
                  <div className="bg-[var(--color-popover)] border border-[var(--color-border)] rounded-lg shadow-xl py-1 min-w-[160px]">
                    <div className="px-3 py-2 text-xs font-semibold text-[var(--color-muted-foreground)] uppercase tracking-wider">
                      {item.title}
                    </div>
                    {item.children.map((child) => (
                      <div key={child.href} className="space-y-0.5">
                        {child.children ? (
                          <>
                            <Link
                              href={child.href}
                              onClick={onClose}
                              className={cn(
                                "flex items-center gap-2 px-3 py-1.5 text-sm font-medium transition-colors",
                                pathname === child.href
                                  ? "text-[var(--color-primary)] bg-[var(--color-primary)]/10"
                                  : "text-[var(--color-muted-foreground)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5"
                              )}
                            >
                              <child.icon className="h-4 w-4 shrink-0" />
                              {child.title}
                            </Link>
                            <div className="ml-2 pl-3 border-l border-[var(--color-border)] space-y-0.5">
                              {child.children.map((sub) => (
                                <Link
                                  key={sub.href}
                                  href={sub.href}
                                  onClick={onClose}
                                  className={cn(
                                    "flex items-center gap-2 px-3 py-1.5 text-sm transition-colors",
                                    pathname.startsWith(sub.href)
                                      ? "text-[var(--color-primary)] bg-[var(--color-primary)]/10"
                                      : "text-[var(--color-foreground)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5"
                                  )}
                                >
                                  <sub.icon className="h-4 w-4 shrink-0" />
                                  {sub.title}
                                </Link>
                              ))}
                            </div>
                          </>
                        ) : (
                          <Link
                            href={child.href}
                            onClick={onClose}
                            className={cn(
                              "flex items-center gap-2 px-3 py-1.5 text-sm transition-colors",
                              pathname === child.href
                                ? "text-[var(--color-primary)] bg-[var(--color-primary)]/10"
                                : "text-[var(--color-foreground)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5"
                            )}
                          >
                            <child.icon className="h-4 w-4 shrink-0" />
                            {child.title}
                          </Link>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          }

          return (
            <Collapsible
              key={item.title}
              open={isOpen}
              onOpenChange={() => toggleMenu(item.title)}
            >
              <CollapsibleTrigger asChild>
                <button
                  className={cn(
                    "flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    parentActive
                      ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                      : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/10"
                  )}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  <span className="flex-1 text-left">{item.title}</span>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 transition-transform duration-200",
                      isOpen && "rotate-180"
                    )}
                  />
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                <div className="ml-3 pl-4 border-l border-[var(--color-border)] mt-1 space-y-0.5">
                  {item.children.map((child) => (
                    <div key={child.href} className="space-y-0.5">
                      <Link
                        href={child.href}
                        onClick={onClose}
                        className={cn(
                          "flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-colors",
                          child.children ? "font-medium" : "",
                          pathname === child.href
                            ? "text-[var(--color-primary)] bg-[var(--color-primary)]/10 font-medium"
                            : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/5"
                        )}
                      >
                        <child.icon className="h-4 w-4 shrink-0" />
                        {child.title}
                      </Link>
                      {child.children && (
                        <div className="ml-3 pl-4 border-l border-[var(--color-border)] space-y-0.5">
                          {child.children.map((sub) => (
                            <Link
                              key={sub.href}
                              href={sub.href}
                              onClick={onClose}
                              className={cn(
                                "flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm transition-colors",
                                pathname.startsWith(sub.href)
                                  ? "text-[var(--color-primary)] bg-[var(--color-primary)]/10 font-medium"
                                  : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/5"
                              )}
                            >
                              <sub.icon className="h-4 w-4 shrink-0" />
                              {sub.title}
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )
        }

        return collapsed ? (
          <Link
            key={item.href}
            href={item.href!}
            onClick={onClose}
            className={cn(
              "flex items-center justify-center h-10 w-10 mx-auto rounded-lg transition-colors",
              isActive(item.href!)
                ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/10"
            )}
            title={item.title}
          >
            <item.icon className="h-5 w-5 shrink-0" />
          </Link>
        ) : (
          <Link
            key={item.href}
            href={item.href!}
            onClick={onClose}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              isActive(item.href!)
                ? "bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                : "text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/10"
            )}
          >
            <item.icon className="h-5 w-5 shrink-0" />
            <span>{item.title}</span>
          </Link>
        )
      })}
    </>
  )
}

export function AppSidebar({ open, onClose }: AppSidebarProps) {
  const { user: sessionUser, activeRole } = useAuth()
  const [collapsed, setCollapsed] = useSidebarCollapsed()
  const mounted = useHydrated()

  const toggleCollapsed = useCallback(() => {
    setCollapsed(!collapsed)
  }, [collapsed, setCollapsed])

  const user = sessionUser
  const userName = user?.name || user?.username || "User"
  const userEmail = user?.email || ""
  const userImage = user?.image || null

  if (!mounted) return null

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden" onClick={onClose} />
      )}

      <aside
        className={cn(
          "fixed top-0 left-0 z-50 flex flex-col h-full bg-[var(--color-sidebar)] border-r border-[var(--color-border)] transition-all duration-300 ease-in-out",
          collapsed ? "w-16" : "w-64",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div
          className={cn(
            "flex items-center h-16 px-4 border-b border-[var(--color-border)]",
            collapsed ? "justify-center" : "justify-between"
          )}
        >
          {!collapsed && (
            <Link href="/dashboard" className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-brand flex items-center justify-center shadow-lg shadow-orange-200/60">
                <span className="text-white font-bold text-sm">T</span>
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-[var(--color-foreground)] leading-tight">TaxFlow</span>
                <span className="text-[10px] text-[var(--color-muted-foreground)] leading-tight">Compliance Platform</span>
              </div>
            </Link>
          )}
          {collapsed && (
            <Link href="/dashboard">
              <div className="h-8 w-8 rounded-lg bg-gradient-brand flex items-center justify-center shadow-lg shadow-orange-200/60">
                <span className="text-white font-bold text-sm">T</span>
              </div>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleCollapsed}
            className="hidden lg:flex h-7 w-7 shrink-0 text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)] hover:bg-[var(--color-primary)]/10"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>

        <OrgSwitcher collapsed={collapsed} />

        <ScrollArea className="flex-1 px-2 py-3">
          <nav className="flex flex-col gap-1">
            <NavItems collapsed={collapsed} onClose={onClose} />
          </nav>
        </ScrollArea>

        <div className="border-t border-[var(--color-border)] p-3">
          {collapsed ? (
            <div className="flex flex-col items-center gap-2">
              <Avatar className="h-8 w-8">
                {userImage ? <AvatarImage src={userImage} alt={userName} /> : null}
                <AvatarFallback className="text-xs bg-[var(--color-primary)]/20 text-[var(--color-primary)]">
                  {getInitials(userName)}
                </AvatarFallback>
              </Avatar>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-[var(--color-muted-foreground)] hover:text-red-500 hover:bg-red-500/10"
                onClick={async () => { await fetch("/api/auth/logout", { method: "POST" }); window.location.href = "/login" }}
                title="Sign Out"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <Avatar className="h-8 w-8 shrink-0">
                  {userImage ? <AvatarImage src={userImage} alt={userName} /> : null}
                  <AvatarFallback className="text-xs bg-[var(--color-primary)]/20 text-[var(--color-primary)]">
                    {getInitials(userName)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-medium text-[var(--color-foreground)] truncate">{userName}</span>
                  <span className="text-xs text-[var(--color-muted-foreground)] truncate">{userEmail}</span>
                  <Badge
                    variant="outline"
                    className="mt-0.5 w-fit text-[10px] px-1.5 py-0 h-4 text-[var(--color-muted-foreground)] border-[var(--color-border)]"
                  >
                    {activeRole === "ADMINISTRATOR" ? "Admin" : activeRole?.charAt(0) + activeRole?.slice(1).toLowerCase()}
                  </Badge>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-[var(--color-muted-foreground)] hover:text-red-500 hover:bg-red-500/10 shrink-0"
                onClick={async () => { await fetch("/api/auth/logout", { method: "POST" }); window.location.href = "/login" }}
                title="Sign Out"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
