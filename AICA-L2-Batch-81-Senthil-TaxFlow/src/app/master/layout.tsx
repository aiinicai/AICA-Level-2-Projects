"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import DashboardLayout from "@/components/layout/dashboard-layout"
import { cn } from "@/lib/utils"
import {
  Globe,
  Building2,
  BookOpen,
  Users,
  DollarSign,
} from "lucide-react"

const navItems = [
  { href: "/master/countries", label: "Countries", icon: Globe },
  { href: "/master/entities", label: "Entities", icon: Building2 },
  { href: "/master/forms", label: "Forms", icon: BookOpen },
  { href: "/master/employees", label: "Employees", icon: Users },
  { href: "/master/exchange-rates", label: "Exchange Rates", icon: DollarSign },
]

export default function MasterLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const isComplianceTemplates = pathname.startsWith("/master/compliance-templates")

  return (
    <DashboardLayout title={isComplianceTemplates ? "Recurring Templates" : undefined}>
      <div className="space-y-6">
        {!isComplianceTemplates && (
          <>
            <div>
              <h2 className="text-2xl font-bold text-slate-900">
                Master Data Management
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Manage reference data across the platform
              </p>
            </div>

            <nav className="flex gap-1 border-b border-slate-200 pb-0">
              {navItems.map((item) => {
                const isActive = pathname.startsWith(item.href)
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
                      isActive
                        ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                        : "border-transparent text-slate-500 hover:text-slate-700"
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                )
              })}
            </nav>
          </>
        )}

        {children}
      </div>
    </DashboardLayout>
  )
}
