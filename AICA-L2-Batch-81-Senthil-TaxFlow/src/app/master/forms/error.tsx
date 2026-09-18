"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"

export default function FormsPageError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Forms page error:", error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="text-sm text-muted-foreground max-w-md text-center">
        {error.message || "An unexpected error occurred"}
      </p>
      <Button onClick={() => reset()}>Try again</Button>
    </div>
  )
}
