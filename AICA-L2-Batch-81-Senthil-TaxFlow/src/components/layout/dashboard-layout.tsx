"use client"

import { useState, useCallback } from "react"
import { usePathname } from "next/navigation"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { AppHeader } from "@/components/layout/app-header"
import { useSidebarCollapsed } from "@/lib/hooks"

export default function DashboardLayout({
  children,
  title,
}: {
  children: React.ReactNode
  title?: string
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed] = useSidebarCollapsed()
  const pathname = usePathname()

  const handleMenuToggle = useCallback(() => {
    setSidebarOpen((prev) => !prev)
  }, [])

  const handleSidebarClose = useCallback(() => {
    setSidebarOpen(false)
  }, [])

  return (
    <div className="min-h-screen bg-[var(--color-background)]">
      <AppSidebar open={sidebarOpen} onClose={handleSidebarClose} />

      <div
        className="transition-all duration-300 max-lg:ml-0"
        style={{ marginLeft: collapsed ? "4rem" : "16rem" }}
      >
        <AppHeader onMenuToggle={handleMenuToggle} title={title} />

        <main className="p-4 lg:p-6 max-w-[1600px] mx-auto">
          <div key={pathname} className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
