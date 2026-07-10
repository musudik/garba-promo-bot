import { useEffect, useState } from 'react'
import { api, getToken, setToken, url } from './api'

const STATUS_TABS = [
  { key: 'pending_review', label: 'To Review' },
  { key: 'approved', label: 'Approved' },
  { key: 'posted', label: 'Posted' },
  { key: 'rejected', label: 'Rejected' },
]

const CONTENT_TYPES = [
  'countdown', 'early_bird', 'selling_fast',
  'sponsor_spotlight', 'food_stall', 'sponsorship_open',
]

export default function App() {
  const [items, setItems] = useState([])
  const [tab, setTab] = useState('pending_review')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [needsToken, setNeedsToken] = useState(false)
  const [showCompose, setShowCompose] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const data = await api.listQueue(tab)
      setItems(data)
      setNeedsToken(false)
    } catch (e) {
      if (String(e).includes('401')) setNeedsToken(true)
      else setError(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [tab])

  async function refresh() {
    setLoading(true)
    try {
      await api.refresh()
      await load()
    } catch (e) {
      setError(String(e.message || e))
      setLoading(false)
    }
  }

  if (needsToken) return <TokenGate onSet={() => load()} />

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">F4</span>
          <div>
            <div className="brand-name">Garba 2026 · Promo Review</div>
            <div className="brand-sub">Sharad Purnima Raas Garba · Fusion4Events</div>
          </div>
        </div>
        <div className="topbar-actions">
          <button className="btn ghost" onClick={refresh} disabled={loading}>
            Pull due posts
          </button>
          <button className="btn gold" onClick={() => setShowCompose(true)}>
            + New post
          </button>
        </div>
      </header>

      <nav className="tabs">
        {STATUS_TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {error && <div className="banner error">{error}</div>}
      {loading && <div className="banner">Loading…</div>}
      {!loading && items.length === 0 && (
        <div className="empty">
          <p>Nothing here yet.</p>
          {tab === 'pending_review' && (
            <p className="empty-hint">Hit “Pull due posts” to load anything scheduled for today, or create one with “New post.”</p>
          )}
        </div>
      )}

      <div className="grid">
        {items.map((item) => (
          <PostCard key={item.id} item={item} onChange={load} />
        ))}
      </div>

      {showCompose && (
        <ComposeModal
          onClose={() => setShowCompose(false)}
          onCreated={() => { setShowCompose(false); setTab('pending_review'); load() }}
        />
      )}
    </div>
  )
}

function PostCard({ item, onChange }) {
  const [headline, setHeadline] = useState(item.headline)
  const [subtext, setSubtext] = useState(item.subtext)
  const [caption, setCaption] = useState(item.caption)
  const [background, setBackground] = useState(item.background || '')
  const [backgrounds, setBackgrounds] = useState([])
  const [busy, setBusy] = useState('')
  const [preview, setPreview] = useState(item.preview_path)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.backgrounds().then(setBackgrounds).catch(() => {})
    if (!preview) regen()
    // eslint-disable-next-line
  }, [])

  const isGenerated = String(item.media_file).toUpperCase() === 'GENERATE'
  const readOnly = ['posted', 'rejected'].includes(item.status)

  async function saveAndRegen() {
    setBusy('regen'); setMsg('')
    try {
      const updated = await api.edit(item.id, { headline, subtext, caption, background })
      setPreview(updated.preview_path + '?t=' + Date.now())
    } catch (e) { setMsg(String(e.message || e)) }
    finally { setBusy('') }
  }
  async function regen() {
    setBusy('regen')
    try {
      const r = await api.regenerate(item.id)
      setPreview(r.preview_path + '?t=' + Date.now())
    } catch (e) { setMsg(String(e.message || e)) }
    finally { setBusy('') }
  }
  async function approve() {
    setBusy('approve'); setMsg('')
    try {
      // Persist any edits first, then post
      await api.edit(item.id, { headline, subtext, caption, background })
      await api.approve(item.id)
      onChange()
    } catch (e) { setMsg(String(e.message || e)); setBusy('') }
  }
  async function reject() {
    setBusy('reject')
    try { await api.reject(item.id); onChange() }
    catch (e) { setMsg(String(e.message || e)); setBusy('') }
  }

  return (
    <div className={`card status-${item.status}`}>
      <div className="card-preview">
        {preview ? (
          <img src={preview.startsWith('http') ? preview : url(preview)} alt="preview" />
        ) : (
          <div className="preview-placeholder">Generating preview…</div>
        )}
        <span className={`chip type-${item.content_type}`}>{item.content_type.replace(/_/g, ' ')}</span>
      </div>

      <div className="card-body">
        <div className="meta">
          <span>{item.city || 'All cities'}</span>
          <span>·</span>
          <span>{item.scheduled_for}</span>
          <span>·</span>
          <span className="platform">{item.platform}</span>
        </div>

        {isGenerated && !readOnly && (
          <>
            <label className="field">
              <span>Headline</span>
              <input value={headline} onChange={(e) => setHeadline(e.target.value)} />
            </label>
            <label className="field">
              <span>Subtext</span>
              <input value={subtext} onChange={(e) => setSubtext(e.target.value)} />
            </label>
            <label className="field">
              <span>Background photo</span>
              <select value={background} onChange={(e) => setBackground(e.target.value)}>
                <option value="">Brand gradient (no photo)</option>
                {backgrounds.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </label>
          </>
        )}

        <label className="field">
          <span>Caption</span>
          <textarea rows={6} value={caption} onChange={(e) => setCaption(e.target.value)} disabled={readOnly} />
        </label>

        {msg && <div className="card-msg">{msg}</div>}

        {!readOnly && (
          <div className="card-actions">
            {isGenerated && (
              <button className="btn ghost" onClick={saveAndRegen} disabled={!!busy}>
                {busy === 'regen' ? 'Regenerating…' : 'Regenerate image'}
              </button>
            )}
            <button className="btn danger" onClick={reject} disabled={!!busy}>Reject</button>
            <button className="btn gold" onClick={approve} disabled={!!busy}>
              {busy === 'approve' ? 'Posting…' : 'Approve & post'}
            </button>
          </div>
        )}
        {item.status === 'posted' && <div className="posted-note">Posted {item.posted_at}</div>}
        {item.status === 'error' && <div className="card-msg">Last error: {item.note}</div>}
      </div>
    </div>
  )
}

function ComposeModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    content_type: 'countdown', city: '', headline: '', subtext: '',
    caption: '', background: '', scheduled_for: '',
  })
  const [backgrounds, setBackgrounds] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { api.backgrounds().then(setBackgrounds).catch(() => {}) }, [])
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  async function create() {
    setBusy(true); setErr('')
    try {
      await api.createManual({ ...form, media_file: 'GENERATE', platform: 'facebook' })
      onCreated()
    } catch (e) { setErr(String(e.message || e)); setBusy(false) }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>New post</h2>
        <label className="field">
          <span>Type</span>
          <select value={form.content_type} onChange={(e) => set('content_type', e.target.value)}>
            {CONTENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
        </label>
        <label className="field"><span>City (optional)</span>
          <input value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="Munich" />
        </label>
        <label className="field"><span>Headline</span>
          <input value={form.headline} onChange={(e) => set('headline', e.target.value)} placeholder="45 DAYS TO GO" />
        </label>
        <label className="field"><span>Subtext</span>
          <input value={form.subtext} onChange={(e) => set('subtext', e.target.value)} placeholder="Apexa Pandya Live" />
        </label>
        <label className="field"><span>Background photo</span>
          <select value={form.background} onChange={(e) => set('background', e.target.value)}>
            <option value="">Brand gradient (no photo)</option>
            {backgrounds.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </label>
        <label className="field"><span>Caption</span>
          <textarea rows={5} value={form.caption} onChange={(e) => set('caption', e.target.value)} />
        </label>
        <label className="field"><span>Schedule for (optional)</span>
          <input value={form.scheduled_for} onChange={(e) => set('scheduled_for', e.target.value)} placeholder="2026-08-04 11:00" />
        </label>
        {err && <div className="card-msg">{err}</div>}
        <div className="modal-actions">
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn gold" onClick={create} disabled={busy}>
            {busy ? 'Creating…' : 'Create for review'}
          </button>
        </div>
      </div>
    </div>
  )
}

function TokenGate({ onSet }) {
  const [val, setVal] = useState(getToken())
  return (
    <div className="gate">
      <div className="gate-box">
        <span className="brand-mark big">F4</span>
        <h1>Promo Review</h1>
        <p>Enter your dashboard access token to continue.</p>
        <input
          type="password"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder="Dashboard token"
        />
        <button className="btn gold" onClick={() => { setToken(val); onSet() }}>Enter</button>
      </div>
    </div>
  )
}
