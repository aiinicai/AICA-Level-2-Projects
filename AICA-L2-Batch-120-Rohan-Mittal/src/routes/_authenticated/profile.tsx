import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bell,
  Check,
  CheckCircle2,
  Key,
  Link as LinkIcon,
  Loader2,
  LogOut,
  Mail,
  Phone,
  ShieldAlert,
  Trash2,
  User,
} from "lucide-react";
import { toast } from "sonner";
import {
  updatePassword,
  sendEmailVerification,
  reauthenticateWithCredential,
  EmailAuthProvider,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import {
  updateUserProfile,
  linkEmailPasswordAccount,
  checkCanCloseAccount,
  closeAccount,
  markNotificationAsRead,
} from "@/lib/fairlyshareDb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MemberAvatar, useSignOut } from "@/components/AppShell";
import { errMsg, formatDay, useNotifications, useUser } from "@/lib/app";
import { formatMoney } from "@/lib/currencies";

export const Route = createFileRoute("/_authenticated/profile")({
  head: () => ({
    meta: [
      { title: "Profile & Settings — Fair Share" },
      {
        name: "description",
        content: "Manage your Fair Share profile, security, and account settings.",
      },
      { property: "og:title", content: "Profile & Settings — Fair Share" },
      {
        property: "og:description",
        content: "Manage your Fair Share profile, security, and account settings.",
      },
    ],
  }),
  component: ProfilePage,
});

function ProfilePage() {
  const { data: me } = useUser();
  const { data: notifs } = useNotifications();
  const qc = useQueryClient();
  const signOut = useSignOut();
  const navigate = useNavigate();

  // Profile fields
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [avatar, setAvatar] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  // Password / Provider linking
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  // Close account modal
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [checkingClosure, setCheckingClosure] = useState(false);
  const [blockingBalances, setBlockingBalances] = useState<
    Array<{ label: string; currency: string; netUnits: number }>
  >([]);
  const [canClose, setCanClose] = useState(false);
  const [closingBusy, setClosingBusy] = useState(false);
  const [reauthPassword, setReauthPassword] = useState("");

  // Push notifications state
  const [pushStatus, setPushStatus] = useState<string>("default");

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setPushStatus(Notification.permission);
    }
  }, []);

  useEffect(() => {
    if (me) {
      setName(me.name || "");
      setPhone(me.phone_number || "");
      setAvatar(me.avatar || "");
    }
  }, [me]);

  const hasPasswordProvider = auth.currentUser?.providerData.some(
    (p) => p.providerId === "password",
  );
  const isGoogleUser = auth.currentUser?.providerData.some((p) => p.providerId === "google.com");

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!me?.id) return;
    setSavingProfile(true);
    try {
      await updateUserProfile(me.id, {
        display_name: name,
        phone_number: phone,
        avatar_url: avatar,
      });
      toast.success("Profile updated");
      qc.invalidateQueries({ queryKey: ["me"] });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 6) {
      return toast.error("Password must be at least 6 characters");
    }
    if (newPassword !== confirmPassword) {
      return toast.error("Passwords do not match");
    }
    setSavingPassword(true);
    try {
      if (hasPasswordProvider && auth.currentUser) {
        await updatePassword(auth.currentUser, newPassword);
        toast.success("Password changed successfully");
      } else {
        // Link email/password credential to existing Google account (One Identity)
        await linkEmailPasswordAccount(newPassword);
        toast.success("Password set! You can now sign in with Google or Email/Password.");
      }
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setSavingPassword(false);
    }
  }

  async function resendEmailVerification() {
    if (!auth.currentUser) return;
    try {
      await sendEmailVerification(auth.currentUser);
      toast.success("Verification link sent. Please check your email inbox.");
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function requestPushPermission() {
    if (typeof window === "undefined" || !("Notification" in window)) {
      return toast.info("Push notifications are not supported in this browser.");
    }
    try {
      const perm = await Notification.requestPermission();
      setPushStatus(perm);
      if (perm === "granted") {
        toast.success("Push notifications enabled!");
      } else {
        toast.info("Push notifications were not enabled.");
      }
    } catch (err) {
      toast.error(errMsg(err));
    }
  }

  async function openCloseAccountDialog() {
    if (!me?.id) return;
    setCheckingClosure(true);
    setCloseDialogOpen(true);
    try {
      const res = await checkCanCloseAccount(me.id);
      setCanClose(res.canClose);
      setBlockingBalances(res.blockingBalances);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setCheckingClosure(false);
    }
  }

  async function handleConfirmCloseAccount() {
    if (!me?.id) return;
    setClosingBusy(true);
    try {
      // Reauthenticate if user has password
      if (hasPasswordProvider && auth.currentUser && me.email && reauthPassword) {
        const cred = EmailAuthProvider.credential(me.email, reauthPassword);
        await reauthenticateWithCredential(auth.currentUser, cred);
      }
      await closeAccount(me.id);
      toast.success("Your account has been closed.");
      await signOut();
      navigate({ to: "/auth", search: { redirect: undefined } });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setClosingBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      {/* Profile Header */}
      <div className="flex flex-col items-center rounded-3xl border bg-card p-6 shadow-soft text-center">
        <MemberAvatar name={me?.name ?? ""} src={me?.avatar} className="h-20 w-20" />
        <h1 className="mt-3 text-xl font-bold text-foreground">{me?.name}</h1>
        <p className="text-sm text-muted-foreground">{me?.email}</p>
        <div className="mt-2 flex items-center gap-2">
          {me?.email_verified ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-owed-soft px-2.5 py-0.5 text-xs font-semibold text-owed">
              <CheckCircle2 className="h-3.5 w-3.5" /> Verified Email
            </span>
          ) : (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-owe-soft px-2.5 py-0.5 text-xs font-semibold text-owe">
                <AlertTriangle className="h-3.5 w-3.5" /> Unverified
              </span>
              <button
                type="button"
                onClick={resendEmailVerification}
                className="text-xs font-semibold text-primary underline"
              >
                Resend verification email
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Edit Profile Form */}
      <form
        onSubmit={handleSaveProfile}
        className="space-y-4 rounded-3xl border bg-card p-5 shadow-soft"
      >
        <h2 className="text-base font-bold text-foreground flex items-center gap-2">
          <User className="h-4 w-4 text-primary" /> Profile Details
        </h2>
        <div className="space-y-1.5">
          <Label htmlFor="displayName">Display Name</Label>
          <Input
            id="displayName"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Alex Morgan"
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="phone">Mobile Number (profile field)</Label>
          <Input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+1 555-0199"
          />
          <p className="text-xs text-muted-foreground">
            Used for friends to recognize you. SMS auth not required.
          </p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="avatarUrl">Avatar URL (optional)</Label>
          <Input
            id="avatarUrl"
            type="url"
            value={avatar}
            onChange={(e) => setAvatar(e.target.value)}
            placeholder="https://..."
          />
        </div>
        <Button type="submit" disabled={savingProfile || !name.trim()}>
          {savingProfile && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save Profile
        </Button>
      </form>

      {/* Security & Password / One Identity Linking */}
      <form
        onSubmit={handlePasswordSubmit}
        className="space-y-4 rounded-3xl border bg-card p-5 shadow-soft"
      >
        <h2 className="text-base font-bold text-foreground flex items-center gap-2">
          <Key className="h-4 w-4 text-primary" />
          {hasPasswordProvider ? "Change Password" : "Set Password (Link Account)"}
        </h2>
        <p className="text-xs text-muted-foreground">
          {hasPasswordProvider
            ? "Update your existing account password."
            : "You signed in with Google. Set a password to also allow email/password login to this exact same account."}
        </p>
        <div className="space-y-1.5">
          <Label htmlFor="newPw">New Password</Label>
          <Input
            id="newPw"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={6}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirmPw">Confirm Password</Label>
          <Input
            id="confirmPw"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={6}
            required
          />
        </div>
        <Button type="submit" variant="outline" disabled={savingPassword || !newPassword}>
          {savingPassword && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {hasPasswordProvider ? "Update Password" : "Set Password & Link"}
        </Button>
      </form>

      {/* Notifications Section */}
      <div className="space-y-4 rounded-3xl border bg-card p-5 shadow-soft">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" /> In-App Notifications
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={requestPushPermission}
            className="text-xs text-primary"
          >
            {pushStatus === "granted" ? "Push: Enabled" : "Enable Browser Push"}
          </Button>
        </div>

        {!notifs?.length ? (
          <p className="text-xs text-muted-foreground">No notifications right now.</p>
        ) : (
          <div className="divide-y rounded-xl border">
            {notifs.slice(0, 10).map((n) => (
              <div
                key={n.id}
                className={`flex items-start justify-between p-3 text-xs ${
                  !n.is_read ? "bg-badge/40 font-medium" : ""
                }`}
              >
                <div className="space-y-0.5">
                  <div className="font-semibold text-foreground">{n.title}</div>
                  <div className="text-muted-foreground">{n.message}</div>
                  <div className="text-[10px] text-muted-foreground">
                    {formatDay(n.created_at.slice(0, 10))}
                  </div>
                </div>
                {!n.is_read && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-[10px]"
                    onClick={async () => {
                      await markNotificationAsRead(n.id);
                      qc.invalidateQueries({ queryKey: ["notifications"] });
                    }}
                  >
                    Mark read
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Danger Zone: Close Account */}
      <div className="rounded-3xl border border-destructive/20 bg-destructive/5 p-5 space-y-3">
        <h2 className="text-base font-bold text-destructive flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" /> Danger Zone
        </h2>
        <p className="text-xs text-muted-foreground">
          Closing your account permanently deletes your credentials and anonymizes your personal
          info. It is only permitted if all your balances across all currencies and groups are
          completely settled.
        </p>
        <Button variant="destructive" size="sm" onClick={openCloseAccountDialog}>
          <Trash2 className="mr-1.5 h-4 w-4" /> Close Account
        </Button>
      </div>

      {/* Sign Out Button */}
      <Button variant="outline" className="w-full" onClick={signOut}>
        <LogOut className="mr-2 h-4 w-4" />
        Sign out
      </Button>

      {/* Close Account Verification Dialog */}
      <Dialog open={closeDialogOpen} onOpenChange={setCloseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Close Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {checkingClosure ? (
              <div className="flex items-center justify-center p-6 text-sm text-muted-foreground">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Checking outstanding debts across
                all currencies…
              </div>
            ) : !canClose ? (
              <div className="space-y-3">
                <div className="rounded-xl bg-owe-soft p-3 text-xs text-owe space-y-1">
                  <p className="font-semibold">Account closure blocked by outstanding balances:</p>
                  <p>
                    You cannot close your account until all direct and group balances in every
                    currency are zero.
                  </p>
                </div>
                <div className="divide-y rounded-xl border bg-card">
                  {blockingBalances.map((b, i) => (
                    <div key={i} className="flex justify-between p-2.5 text-xs">
                      <span>{b.label}</span>
                      <span className="money font-semibold text-foreground">
                        {formatMoney(b.netUnits, b.currency)}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Please settle up with your friends or flatmates first, then return to close your
                  account.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="rounded-xl bg-owed-soft p-3 text-xs text-owed">
                  All balances are settled (0.00 in all currencies). You are clear to close your
                  account.
                </div>
                <p className="text-xs text-muted-foreground">
                  Your past transactions will be preserved for other participants under the label
                  "Deleted user". Your email, mobile number, and authentication records will be
                  deleted.
                </p>
                {hasPasswordProvider && (
                  <div className="space-y-1.5">
                    <Label htmlFor="reauth">Confirm password to proceed</Label>
                    <Input
                      id="reauth"
                      type="password"
                      value={reauthPassword}
                      onChange={(e) => setReauthPassword(e.target.value)}
                      placeholder="Your current password"
                    />
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseDialogOpen(false)}>
              Cancel
            </Button>
            {canClose && (
              <Button
                variant="destructive"
                onClick={handleConfirmCloseAccount}
                disabled={closingBusy || (hasPasswordProvider && !reauthPassword)}
              >
                {closingBusy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Confirm Deletion
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
