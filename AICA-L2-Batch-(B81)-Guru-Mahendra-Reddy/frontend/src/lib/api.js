// Thin fetch wrapper. Holds the token, adds the entity/as-on the whole app is
// looking at, and turns a failure into a readable sentence rather than a stack
// trace — a CFO should never see "TypeError: undefined".

const TOKEN_KEY = 'cashrunway.token'

export const getToken = () => {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export const setToken = (t) => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) } catch { /* private mode */ }
}

let scope = { entity_id: null, as_on: null }
export const setScope = (s) => { scope = { ...scope, ...s } }
export const getScope = () => scope

// A board response carries `_restricted_labels` — what the CFO's policy held
// back on that screen. The shell renders it, so the reader is told rather than
// left to notice a gap.
let restrictedListener = null
export const onRestricted = (fn) => { restrictedListener = fn }

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.status = status
    this.body = body
  }
}

function url(path, params = {}, withScope = true) {
  const u = new URL(path, window.location.origin)
  const all = withScope
    ? { ...(scope.entity_id ? { entity_id: scope.entity_id } : {}),
        ...(scope.as_on ? { as_on: scope.as_on } : {}), ...params }
    : params
  Object.entries(all).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') u.searchParams.set(k, v)
  })
  return u.pathname + u.search
}

async function handle(res, { isLogin = false } = {}) {
  // A 401 from the login endpoint means the credentials were refused — it is
  // not an expired session, and saying so sends the reader looking for the
  // wrong fault. Let the server's own sentence through.
  if (res.status === 401 && !isLogin) {
    setToken(null)
    if (!window.location.pathname.startsWith('/login')) window.location.href = '/login'
    throw new ApiError('Your session has expired. Please sign in again.', 401)
  }
  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const body = isJson ? await res.json().catch(() => null) : await res.blob()
  if (!res.ok) {
    const detail = isJson ? (body?.detail ?? body?.message) : null
    throw new ApiError(
      typeof detail === 'string' ? detail : `The server returned ${res.status}.`,
      res.status, body)
  }
  if (restrictedListener && body && typeof body === 'object' && !Array.isArray(body)) {
    restrictedListener(body._restricted_labels || [])
  }
  return body
}

const authHeaders = () => {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

export const api = {
  async get(path, params, { scoped = true } = {}) {
    return handle(await fetch(url(path, params, scoped), { headers: authHeaders() }))
  },
  async post(path, body, params) {
    return handle(await fetch(url(path, params), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body ?? {}),
    }))
  },
  // PUT is what the three "save the whole thing" endpoints use — the Tally
  // ledger mapping, the sync schedule and the board-visibility policy all
  // replace a set rather than amend a field. It was missing from this object
  // while three screens called it, so each failed with "put is not a function"
  // at the moment of saving: the work was done, the server never heard about
  // it, and nothing said why.
  async put(path, body, params) {
    return handle(await fetch(url(path, params), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body ?? {}),
    }))
  },
  async patch(path, body, params) {
    return handle(await fetch(url(path, params), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body ?? {}),
    }))
  },
  async del(path, params) {
    return handle(await fetch(url(path, params), {
      method: 'DELETE', headers: authHeaders(),
    }))
  },
  async form(path, formData, params) {
    return handle(await fetch(url(path, params), {
      method: 'POST', headers: authHeaders(), body: formData,
    }))
  },
  async download(path, filename, params) {
    const res = await fetch(url(path, params), { headers: authHeaders() })
    const blob = await handle(res)
    const href = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = href
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(href)
  },
  async login(email, password) {
    const res = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const body = await handle(res, { isLogin: true })
    setToken(body.access_token)
    return body.user
  },
  logout() { setToken(null) },
}
