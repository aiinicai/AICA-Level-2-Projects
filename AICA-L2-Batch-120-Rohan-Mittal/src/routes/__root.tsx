import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
  type ErrorComponentProps,
} from "@tanstack/react-router";
import { useEffect, useRef, type ReactNode } from "react";
import { WifiOff } from "lucide-react";
import { onAuthStateChanged } from "firebase/auth";

import appCss from "../styles.css?url";
import { Toaster } from "@/components/ui/sonner";
import { auth } from "@/lib/firebase";
import { setupServiceWorker } from "@/lib/pwa";
import { useOnline } from "@/lib/app";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: ErrorComponentProps) {
  console.error(error);
  const router = useRouter();
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold text-foreground">This page didn't load</h1>
        <p className="mt-2 text-sm text-muted-foreground">Something went wrong. Try refreshing.</p>
        <button
          onClick={() => {
            router.invalidate();
            reset();
          }}
          className="mt-6 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
      { title: "Fair Share — Group Expense Sharing & Bill Splitter" },
      {
        name: "description",
        content:
          "Split group and personal expenses fairly with friends, roommates, and travel groups.",
      },
      { property: "og:title", content: "Fair Share — Group Expense Sharing & Bill Splitter" },
      {
        property: "og:description",
        content:
          "Split group and personal expenses fairly with friends, roommates, and travel groups.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "theme-color", content: "#0F2744" },
      { name: "apple-mobile-web-app-capable", content: "yes" },
      { name: "apple-mobile-web-app-title", content: "Fair Share" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", type: "image/svg+xml", href: "/favicon.svg?v=friends-rm-3" },
      { rel: "icon", type: "image/png", href: "/favicon.png?v=friends-rm-3" },
      { rel: "manifest", href: "/manifest.webmanifest", crossOrigin: "use-credentials" },
      { rel: "apple-touch-icon", sizes: "180x180", href: "/icons/apple-touch-icon.png?v=friends-rm-3" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const router = useRouter();
  const online = useOnline();
  const lastUidRef = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    setupServiceWorker();
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      const nextUid = user?.uid ?? null;
      const prevUid = lastUidRef.current;
      lastUidRef.current = nextUid;

      // Only invalidate router when auth state transitions after initial mount
      if (prevUid !== undefined && prevUid !== nextUid) {
        router.invalidate();
      }
      if (!user) {
        if (prevUid !== undefined && prevUid !== null) {
          queryClient.clear();
        }
      } else if (prevUid !== nextUid) {
        queryClient.invalidateQueries();
      }
    });
    return () => unsubscribe();
  }, [router, queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      {!online && (
        <div className="sticky top-0 z-50 flex items-center justify-center gap-2 bg-owe-soft px-4 py-2 text-xs font-medium text-owe">
          <WifiOff className="h-3.5 w-3.5" /> You're offline, changes need a connection
        </div>
      )}
      <Outlet />
      <Toaster position="top-center" richColors />
    </QueryClientProvider>
  );
}
