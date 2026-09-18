"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/layout/providers"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Loader2, Lock, Mail, ArrowRight } from "lucide-react"

export default function LoginPage() {
  const router = useRouter()
  const { refresh } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setLoading(true)
    setError("")

    const formData = new FormData(e.currentTarget)
    const email = formData.get("email") as string
    const password = formData.get("password") as string

    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    const data = await res.json()

    if (!res.ok) {
      setError(data.error || "Login failed")
      setLoading(false)
      return
    }

    // The session cookie was set by the server. The client-side auth context
    // only fetches /api/auth/me on mount and on onAuthStateChange, neither of
    // which fires for a server-side form login. Without an explicit refresh
    // here, `user` stays null and the router guard bounces the just-logged-in
    // user straight back to /login (the login loop).
    await refresh()

    router.replace("/dashboard")
    router.refresh()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-background)] p-4 relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 opacity-[0.07]">
          <div className="w-full h-full rounded-full bg-gradient-brand blur-3xl" />
        </div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 opacity-[0.07]">
          <div className="w-full h-full rounded-full bg-gradient-brand blur-3xl" />
        </div>
      </div>
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="flex">
              <div className="h-10 w-10 rounded-lg bg-gradient-brand flex items-center justify-center shadow-lg shadow-orange-200/60">
                <span className="text-white font-bold text-lg">T</span>
              </div>
            </div>
            <span className="text-2xl font-bold tracking-tight text-[var(--color-foreground)]">
              TaxFlow
            </span>
          </div>
          <p className="text-muted-foreground text-sm">Enterprise Tax Compliance Platform</p>
        </div>

        <Card className="border-0 shadow-[0_2px_20px_rgba(0,0,0,0.04),0_1px_3px_rgba(0,0,0,0.02)] rounded-2xl">
          <CardHeader className="space-y-1 pb-6 pt-8">
            <CardTitle className="text-xl font-semibold text-center">Sign in to your account</CardTitle>
            <CardDescription className="text-center text-sm">
              Sign in with your LucidShare credentials
            </CardDescription>
          </CardHeader>
          <CardContent className="pb-8 px-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-10 h-11 rounded-xl border-[var(--color-border)] bg-white focus:border-[var(--color-primary)] focus:ring-[var(--color-primary)]/20 transition-all"
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    placeholder="Enter your password"
                    className="pl-10 h-11 rounded-xl border-[var(--color-border)] bg-white focus:border-[var(--color-primary)] focus:ring-[var(--color-primary)]/20 transition-all"
                    required
                  />
                </div>
              </div>
              {error && (
                <div className="bg-red-50 text-red-600 text-sm p-3 rounded-xl border border-red-200 flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0" />
                  {error}
                </div>
              )}
              <Button
                type="submit"
                className="w-full h-11 text-base rounded-xl bg-[var(--color-primary)] hover:bg-[var(--color-primary)]/90 text-white shadow-md shadow-orange-200/60 transition-all"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-xs text-center text-muted-foreground mt-8">
          &copy; 2026 TaxFlow. All rights reserved.
        </p>
      </div>
    </div>
  )
}
