import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { KeyRound, Loader2, ShieldCheck } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Field, PageHeader } from '@/components/common'
import { useAuth } from '@/components/auth-provider'
import { friendlyError, supabase } from '@/lib/supabase'
import { formatDate, initials, toDateInput } from '@/lib/utils'

export default function ProfilePage() {
  const { profile, isAdmin, refreshProfile } = useAuth()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [saving, setSaving] = useState(false)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordErrors, setPasswordErrors] = useState<{
    current?: string
    next?: string
    confirm?: string
  }>({})
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    setFullName(profile?.full_name ?? '')
    setPhone(profile?.phone ?? '')
  }, [profile])

  async function handleSave(event: React.FormEvent) {
    event.preventDefault()
    if (!profile) return
    if (!fullName.trim()) {
      toast.error('Full name cannot be blank.')
      return
    }

    setSaving(true)
    const { error } = await supabase
      .from('profiles')
      .update({ full_name: fullName.trim(), phone: phone.trim() || null })
      .eq('id', profile.id)
    setSaving(false)

    if (error) {
      toast.error(friendlyError(error))
      return
    }
    await refreshProfile()
    toast.success('Profile updated')
  }

  async function handleChangePassword(event: React.FormEvent) {
    event.preventDefault()
    if (!profile) return

    const next: typeof passwordErrors = {}
    if (!currentPassword) next.current = 'Enter your current password.'
    if (newPassword.length < 8) next.next = 'New password must be at least 8 characters.'
    if (newPassword && newPassword === currentPassword) {
      next.next = 'The new password must be different from the current one.'
    }
    if (newPassword !== confirmPassword) next.confirm = 'Passwords do not match.'
    setPasswordErrors(next)
    if (Object.keys(next).length) return

    setChangingPassword(true)

    // Supabase does not ask for the current password on updateUser, so verify
    // it ourselves. Otherwise anyone at an unlocked desk could change it.
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: profile.email,
      password: currentPassword,
    })

    if (signInError) {
      setChangingPassword(false)
      setPasswordErrors({ current: 'Current password is incorrect.' })
      return
    }

    const { error } = await supabase.auth.updateUser({ password: newPassword })
    setChangingPassword(false)

    if (error) {
      toast.error(friendlyError(error))
      return
    }

    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setPasswordErrors({})
    toast.success('Password changed')
  }

  return (
    <div className="space-y-5">
      <PageHeader title="Profile" description="Your details as they appear across the firm." />

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardContent className="flex flex-col items-center gap-3 pt-2 text-center">
            <Avatar className="size-16">
              <AvatarFallback className="bg-primary text-primary-foreground text-lg font-semibold">
                {initials(profile?.full_name)}
              </AvatarFallback>
            </Avatar>
            <div>
              <p className="font-semibold">{profile?.full_name}</p>
              <p className="text-muted-foreground text-sm">{profile?.email}</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              <Badge variant="secondary">{profile?.designation}</Badge>
              {isAdmin ? (
                <Badge className="gap-1">
                  <ShieldCheck className="size-3" />
                  Administrator
                </Badge>
              ) : (
                <Badge variant="outline">Employee</Badge>
              )}
            </div>
            <dl className="text-muted-foreground mt-2 w-full space-y-1 text-left text-sm">
              <div className="flex justify-between gap-2">
                <dt>Date of joining</dt>
                <dd className="text-foreground">{formatDate(profile?.date_of_joining)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Status</dt>
                <dd className="text-foreground">{profile?.is_active ? 'Active' : 'Inactive'}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Member since</dt>
                <dd className="text-foreground">{formatDate(profile?.created_at)}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Edit details</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSave}>
              <Field label="Full Name" htmlFor="profile-name" required>
                <Input
                  id="profile-name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </Field>
              <Field label="Phone" htmlFor="profile-phone">
                <Input
                  id="profile-phone"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 …"
                />
              </Field>
              <Field
                label="Email"
                htmlFor="profile-email"
                hint="Your login email cannot be changed here."
              >
                <Input id="profile-email" value={profile?.email ?? ''} disabled />
              </Field>
              <Field
                label="Designation"
                htmlFor="profile-designation"
                hint="Only an administrator can change this."
              >
                <Input id="profile-designation" value={profile?.designation ?? ''} disabled />
              </Field>
              <Field
                label="Date of Joining"
                htmlFor="profile-doj"
                hint="Set by your administrator."
                className="sm:col-span-2 sm:max-w-xs"
              >
                <Input
                  id="profile-doj"
                  type="date"
                  value={toDateInput(profile?.date_of_joining)}
                  disabled
                />
              </Field>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={saving}>
                  {saving ? <Loader2 className="size-4 animate-spin" /> : null}
                  Save changes
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2 lg:col-start-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRound className="size-4" />
              Change password
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleChangePassword} noValidate>
              <Field
                label="Current Password"
                htmlFor="current-password"
                error={passwordErrors.current}
                className="sm:col-span-2 sm:max-w-sm"
                required
              >
                <Input
                  id="current-password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </Field>
              <Field
                label="New Password"
                htmlFor="new-password"
                error={passwordErrors.next}
                hint="Minimum 8 characters."
                required
              >
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </Field>
              <Field
                label="Confirm New Password"
                htmlFor="confirm-new-password"
                error={passwordErrors.confirm}
                required
              >
                <Input
                  id="confirm-new-password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </Field>
              <div className="sm:col-span-2">
                <Button type="submit" disabled={changingPassword}>
                  {changingPassword ? <Loader2 className="size-4 animate-spin" /> : null}
                  Change password
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
