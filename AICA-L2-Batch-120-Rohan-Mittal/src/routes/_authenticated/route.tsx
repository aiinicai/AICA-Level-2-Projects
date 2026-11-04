import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { type User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { AppHeader, BottomNav } from "@/components/AppShell";

function getCurrentUser(): Promise<User | null> {
  return new Promise((resolve) => {
    if (auth.currentUser) return resolve(auth.currentUser);
    const unsub = auth.onAuthStateChanged((user) => {
      unsub();
      resolve(user);
    });
  });
}

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async ({ location }) => {
    const user = await getCurrentUser();
    if (!user) {
      throw redirect({ to: "/auth", search: { redirect: location.href } });
    }
  },
  component: () => (
    <div className="min-h-screen pb-24 md:pb-8">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-5">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  ),
});
