// Production server for Railway.
//
// Vite emits a static SPA into dist/. Railway needs a process that listens on
// $PORT, and any client-side route (/tasks/<uuid>, /dashboard …) must return
// index.html rather than a 404 — that is all this file does.

import path from 'node:path'
import { fileURLToPath } from 'node:url'
import express from 'express'
import compression from 'compression'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const dist = path.join(__dirname, 'dist')
const port = process.env.PORT || 8080

const app = express()

app.disable('x-powered-by')
app.use(compression())

// Hashed asset filenames can be cached hard; index.html never can, or a deploy
// would keep serving the previous bundle.
app.use(
  express.static(dist, {
    index: false,
    setHeaders(res, filePath) {
      if (filePath.endsWith('index.html')) {
        res.setHeader('Cache-Control', 'no-cache')
      } else if (filePath.includes(`${path.sep}assets${path.sep}`)) {
        res.setHeader('Cache-Control', 'public, max-age=31536000, immutable')
      }
    },
  }),
)

app.get('/healthz', (_req, res) => {
  res.status(200).json({ status: 'ok' })
})

// SPA fallback. Registered as middleware rather than app.get('*') because
// Express 5 no longer accepts a bare '*' path pattern.
app.use((req, res, next) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') return next()
  res.setHeader('Cache-Control', 'no-cache')
  res.sendFile(path.join(dist, 'index.html'))
})

app.listen(port, '0.0.0.0', () => {
  console.log(`Aggarwal Samir & Co task app listening on :${port}`)
})
