export function getCookieDomain(host: string): string | undefined {
  if (host.endsWith(".lucid-exp.com") || host === "lucid-exp.com") {
    return ".lucid-exp.com"
  }
  return undefined
}
