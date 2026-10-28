import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";
import type { Plugin } from "vite";

function resilientDevClientEntryPlugin(): Plugin {
  return {
    name: "fairshare:resilient-dev-client-entry",
    enforce: "post",
    transform(code, id) {
      if (id.includes("vite/dist/client/client.mjs") && code.includes("vite:ws:disconnect")) {
        return code.replace(
          /if\s*\(payload\.event\s*===\s*["']vite:ws:disconnect["']\)\s*\{[\s\S]*?location\.reload\(\);\s*\}\s*\}/,
          'if (payload.event === "vite:ws:disconnect") { /* WebSocket reload disabled for static auth state */ }',
        );
      }
      if (id.includes("tanstack-start-dev-client-entry") && code.includes("await import(")) {
        const cwd = process.cwd().replace(/\\/g, "/");
        return code.replace(/await\s+import\("([^"]+)"\)/, (_match, rawPath: string) => {
          const webPath = rawPath.startsWith(cwd) ? rawPath.slice(cwd.length) : rawPath;
          return `await (async () => {
              for (let __i = 0; __i < 4; __i++) {
                try {
                  if (__i === 0) {
                    await import(${JSON.stringify(rawPath)});
                  } else {
                    await import(/* @vite-ignore */ ${JSON.stringify(webPath)} + "?t=" + Date.now() + "&retry=" + __i);
                  }
                  return;
                } catch (__err) {
                  if (__i < 3) {
                    await new Promise((__r) => setTimeout(__r, 350 * (__i + 1)));
                  } else {
                    console.error(__err);
                  }
                }
              }
            })()`;
        });
      }
      return null;
    },
  };
}

export default defineConfig(({ command }) => {
  const isBuild = command === "build";
  return {
    css: {
      transformer: "lightningcss",
    },
    resolve: {
      dedupe: [
        "react",
        "react-dom",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
        "@tanstack/react-query",
        "@tanstack/query-core",
      ],
    },
    server: {
      host: "0.0.0.0",
      port: 3000,
      strictPort: true,
      hmr: {
        overlay: false,
      },
      warmup: {
        clientFiles: [
          "./node_modules/@tanstack/react-start/dist/plugin/default-entry/client.tsx",
          "./src/router.tsx",
          "./src/routeTree.gen.ts",
          "./src/routes/**/*.tsx",
          "./src/components/**/*.tsx",
          "./src/lib/**/*.ts",
        ],
      },
    },
    optimizeDeps: {
      ignoreOutdatedRequests: true,
      include: [
        "react",
        "react-dom",
        "react-dom/client",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
        "@tanstack/react-query",
        "@tanstack/react-store",
        "@tanstack/react-router",
        "@radix-ui/react-avatar",
        "@radix-ui/react-checkbox",
        "@radix-ui/react-dialog",
        "@radix-ui/react-dropdown-menu",
        "@radix-ui/react-label",
        "@radix-ui/react-select",
        "@radix-ui/react-slot",
        "@radix-ui/react-tabs",
        "class-variance-authority",
        "clsx",
        "firebase/app",
        "firebase/auth",
        "firebase/firestore",
        "lucide-react",
        "sonner",
        "tailwind-merge",
        "xlsx",
      ],
    },
    plugins: [
      tsconfigPaths(),
      tailwindcss(),
      tanstackStart({
        server: { entry: "server" },
      }),
      react(),
      ...(isBuild ? [nitro({ preset: "cloudflare-module" })] : []),
      resilientDevClientEntryPlugin(),
    ],
  };
});
