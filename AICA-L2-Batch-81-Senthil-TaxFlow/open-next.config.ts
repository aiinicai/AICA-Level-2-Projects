import { defineCloudflareConfig } from "@opennextjs/cloudflare";

const config = defineCloudflareConfig({});
config.edgeExternals = [
  "node:async_hooks",
  "node:crypto",
  "node:fs",
  "node:fs/promises",
  "node:http",
  "node:http2",
  "node:https",
  "node:buffer",
  "node:events",
  "node:process",
  "node:os",
  "node:path",
  "node:stream",
  "node:url",
  "node:util",
  "node:zlib",
  "node:vm",
  "@prisma/client",
  "pg",
];
export default config;
