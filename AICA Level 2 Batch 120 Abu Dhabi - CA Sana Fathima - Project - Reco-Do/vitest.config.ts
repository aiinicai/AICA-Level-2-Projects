import { resolve } from 'path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve('src/renderer/src'),
      '@shared': resolve('src/shared'),
      '@engine': resolve('src/engine'),
      '@tools': resolve('src/tools'),
      '@export': resolve('src/export')
    }
  },
  test: { include: ['tests/**/*.test.ts'] }
})
