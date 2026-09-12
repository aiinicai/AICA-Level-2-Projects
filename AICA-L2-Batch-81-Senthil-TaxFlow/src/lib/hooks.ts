"use client"

import { useCallback, useSyncExternalStore } from "react"

const SIDEBAR_COLLAPSED_KEY = "sidebar-collapsed"
const SIDEBAR_COLLAPSED_EVENT = "taxflow:sidebar-collapsed"

function sidebarSubscribe(callback: () => void) {
  window.addEventListener(SIDEBAR_COLLAPSED_EVENT, callback)
  return () => window.removeEventListener(SIDEBAR_COLLAPSED_EVENT, callback)
}

export function useHydrated(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  )
}

export function useSidebarCollapsed(): [boolean, (next: boolean) => void] {
  const collapsed = useSyncExternalStore(
    sidebarSubscribe,
    () => window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true",
    () => false
  )

  const setCollapsed = useCallback((next: boolean) => {
    window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next))
    window.dispatchEvent(new Event(SIDEBAR_COLLAPSED_EVENT))
  }, [])

  return [collapsed, setCollapsed]
}