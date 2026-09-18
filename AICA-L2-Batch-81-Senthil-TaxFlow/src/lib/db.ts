export function newId(): string {
  return crypto.randomUUID()
}

export function now(): string {
  return new Date().toISOString()
}
