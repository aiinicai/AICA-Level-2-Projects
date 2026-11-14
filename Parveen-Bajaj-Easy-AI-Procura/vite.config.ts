// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  vite: {
    plugins: [
      // Offline support for the published app only. Registration happens from
      // src/lib/pwa.ts, which refuses to run in dev and in Lovable previews.
      VitePWA({
        strategies: "generateSW",
        registerType: "autoUpdate",
        filename: "sw.js",
        // The wrapper module is the only registrar.
        injectRegister: null,
        // No service worker emitted while the dev server runs.
        devOptions: { enabled: false },
        // The app ships its own manifest at public/manifest.webmanifest.
        manifest: false,
        workbox: {
          globPatterns: ["**/*.{js,css,html,png,svg,ico,woff,woff2}"],
          // No cache-first HTML: navigations are served NetworkFirst below.
          navigateFallback: null,
          runtimeCaching: [
            {
              // OAuth hops must never be replayed from cache.
              urlPattern: ({ url, sameOrigin }) =>
                sameOrigin && url.pathname.startsWith("/~oauth"),
              handler: "NetworkOnly",
            },
            {
              // HTML navigations: always try the network, cache as fallback.
              urlPattern: ({ request }) => request.mode === "navigate",
              handler: "NetworkFirst",
              options: {
                cacheName: "pages",
                networkTimeoutSeconds: 5,
                expiration: { maxEntries: 32, maxAgeSeconds: 60 * 60 * 24 * 7 },
              },
            },
            {
              urlPattern: ({ url, sameOrigin }) =>
                sameOrigin && /\.(?:js|css|woff2?|ttf)$/.test(url.pathname),
              handler: "CacheFirst",
              options: {
                cacheName: "assets",
                expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 },
              },
            },
            {
              urlPattern: ({ url, sameOrigin }) =>
                sameOrigin && /\.(?:png|jpe?g|svg|webp|ico|gif)$/.test(url.pathname),
              handler: "CacheFirst",
              options: {
                cacheName: "images",
                expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 30 },
              },
            },
          ],
        },
      }),
    ],
  },
});
