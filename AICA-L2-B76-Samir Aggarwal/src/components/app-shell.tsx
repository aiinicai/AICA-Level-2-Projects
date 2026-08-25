import { NavLink, useLocation } from 'react-router-dom'
import {
  Building2,
  ClipboardList,
  FileText,
  KanbanSquare,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Repeat,
  TriangleAlert,
  Users,
  UserCircle,
  ListTodo,
} from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { useAuth } from '@/components/auth-provider'
import { FIRM_INITIALS, FIRM_NAME } from '@/lib/constants'
import { initials } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const ADMIN_WORK: NavItem[] = [
  { to: '/dashboard', label: 'Status Board', icon: LayoutDashboard },
  { to: '/board', label: 'Board', icon: KanbanSquare },
  { to: '/tasks', label: 'All Tasks', icon: ClipboardList },
  { to: '/need-help', label: 'Need Help', icon: TriangleAlert },
]

const ADMIN_MASTERS: NavItem[] = [
  { to: '/clients', label: 'Clients', icon: Building2 },
  { to: '/employees', label: 'Employees', icon: Users },
  { to: '/task-master', label: 'Task Master', icon: ListChecks },
  { to: '/recurring', label: 'Recurring', icon: Repeat },
]

const ADMIN_REPORTS: NavItem[] = [
  { to: '/client-status', label: 'Client Status', icon: FileText },
]

const EMPLOYEE_NAV: NavItem[] = [
  { to: '/my-tasks', label: 'My Tasks', icon: ListTodo },
  { to: '/board', label: 'Board', icon: KanbanSquare },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const { profile, isAdmin, signOut } = useAuth()
  const location = useLocation()

  const groups: { label: string; items: NavItem[] }[] = isAdmin
    ? [
        { label: 'Work', items: [...ADMIN_WORK, ...EMPLOYEE_NAV.slice(0, 1)] },
        { label: 'Masters', items: ADMIN_MASTERS },
        { label: 'Reports', items: ADMIN_REPORTS },
      ]
    : [{ label: 'Workspace', items: EMPLOYEE_NAV }]

  return (
    <SidebarProvider>
      <Sidebar collapsible="icon">
        <SidebarHeader>
          <div className="flex items-center gap-2 px-1 py-1.5">
            <div className="bg-sidebar-primary text-sidebar-primary-foreground grid size-8 shrink-0 place-items-center rounded-md text-[11px] font-bold">
              {FIRM_INITIALS}
            </div>
            <div className="grid min-w-0 leading-tight group-data-[collapsible=icon]:hidden">
              <span className="truncate text-sm font-semibold">{FIRM_NAME}</span>
              <span className="text-sidebar-foreground/60 truncate text-xs">
                {isAdmin ? 'Administrator' : 'Employee'}
              </span>
            </div>
          </div>
        </SidebarHeader>

        <SidebarContent>
          {groups.map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.items.map((item) => (
                    <SidebarMenuItem key={item.to}>
                      <SidebarMenuButton
                        asChild
                        isActive={location.pathname.startsWith(item.to)}
                        tooltip={item.label}
                      >
                        <NavLink to={item.to}>
                          <item.icon className="size-4" />
                          <span>{item.label}</span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}
        </SidebarContent>

        <SidebarFooter>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                isActive={location.pathname === '/profile'}
                tooltip="Profile"
              >
                <NavLink to="/profile">
                  <UserCircle className="size-4" />
                  <span>Profile</span>
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton onClick={() => void signOut()} tooltip="Sign Out">
                <LogOut className="size-4" />
                <span>Sign Out</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

      {/* min-w-0: without it this flex pane cannot shrink below its content
          width, so a wide table blocks the whole page instead of scrolling
          inside its own container when the sidebar is open. */}
      <SidebarInset className="min-w-0">
        <header className="bg-background/95 sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b px-4 backdrop-blur">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-1 !h-5" />
          <span className="truncate text-sm font-medium sm:hidden">{FIRM_NAME}</span>
          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right leading-tight sm:block">
              <p className="text-sm font-medium">{profile?.full_name ?? '—'}</p>
              <Badge variant="secondary" className="mt-0.5 h-4 px-1.5 text-[10px] font-normal">
                {profile?.designation ?? '—'}
              </Badge>
            </div>
            <Avatar className="size-8">
              <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                {initials(profile?.full_name)}
              </AvatarFallback>
            </Avatar>
            <Button
              variant="ghost"
              size="icon"
              className="sm:hidden"
              onClick={() => void signOut()}
              aria-label="Sign out"
            >
              <LogOut className="size-4" />
            </Button>
          </div>
        </header>
        <main className="min-w-0 flex-1 space-y-5 overflow-x-hidden p-4 sm:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  )
}
