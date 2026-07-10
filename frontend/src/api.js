// Thin API client. Token (if set) is kept in localStorage and sent as a
// Bearer header. Same-origin in production (served by FastAPI), proxied in dev.

// The app is served under a base path (e.g. /dashboard). Vite injects the
// build-time base as import.meta.env.BASE_URL (with trailing slash), so API
// calls resolve to <base>/api/... and match the backend mount point.
const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
export const url = (path) => `${BASE}${path}`

const tokenKey = 'garba_dashboard_token'

export function getToken() {
  return localStorage.getItem(tokenKey) || ''
}
export function setToken(t) {
  localStorage.setItem(tokenKey, t)
}

function headers(extra = {}) {
  const h = { ...extra }
  const t = getToken()
  if (t) h['Authorization'] = `Bearer ${t}`
  return h
}

async function handle(res) {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  listQueue: (status) =>
    fetch(url(`/api/queue${status ? `?status=${status}` : ''}`), { headers: headers() }).then(handle),

  refresh: () =>
    fetch(url('/api/queue/refresh'), { method: 'POST', headers: headers() }).then(handle),

  createManual: (data) =>
    fetch(url('/api/queue/manual'), {
      method: 'POST',
      headers: headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handle),

  regenerate: (id) =>
    fetch(url(`/api/queue/${id}/preview`), { method: 'POST', headers: headers() }).then(handle),

  edit: (id, data) =>
    fetch(url(`/api/queue/${id}`), {
      method: 'PATCH',
      headers: headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handle),

  approve: (id) =>
    fetch(url(`/api/queue/${id}/approve`), { method: 'POST', headers: headers() }).then(handle),

  reject: (id) =>
    fetch(url(`/api/queue/${id}/reject`), { method: 'POST', headers: headers() }).then(handle),

  backgrounds: () =>
    fetch(url('/api/backgrounds'), { headers: headers() }).then(handle),

  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(url('/api/upload'), { method: 'POST', headers: headers(), body: form }).then(handle)
  },
}
