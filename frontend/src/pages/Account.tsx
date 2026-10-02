import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Field, Notice, PageHead, Section } from '../components/ui'
import { api, type Me, type Role } from '../lib/api'
import { isAdmin, useAuth } from '../lib/auth'
import { useAsync } from '../lib/hooks'

/** Profile, organisation sharing, security and data rights, all in one place. */
export default function Account() {
  const { me, setMe, logout } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const m = me!.membership
  const org = useAsync(() => (m ? api.org(m.org_id) : Promise.resolve(null)), [m?.org_id])
  const [group, setGroup] = useState<number | null>(null)

  const run = async (fn: () => Promise<Me>, done?: string, confirmText?: string) => {
    if (confirmText && !window.confirm(confirmText)) return
    setBusy(true)
    setError(null)
    setSaved(null)
    try {
      setMe(await fn())
      if (done) setSaved(done)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 pb-20 sm:px-6">
      <PageHead eyebrow="Account & privacy" title={me!.user.name}
        aside={<button onClick={async () => { await logout(); navigate('/') }} className="btn">Log out</button>}>
        {me!.user.email} · {me!.check_ins} check-in{me!.check_ins === 1 ? '' : 's'} · times shown in {me!.timezone}
      </PageHead>
      {error && <Notice tone="error">{error}</Notice>}
      {saved && <Notice tone="hot">{saved}</Notice>}

      <Section eyebrow="Profile" title="Your check-in">
        <div className="space-y-6">
          <div>
            <div className="b-mono mb-2 text-ink-3">Questions are worded for</div>
            <div className="flex flex-wrap">
              {(['employee', 'student', 'general'] as Role[]).map((r) => (
                <button key={r} onClick={() => run(() => api.updateProfile({ role_type: r }), 'Saved.')} disabled={busy} aria-pressed={me!.role_type === r}
                  className={`-ml-[2px] border-2 border-line px-5 py-3 font-mono text-[11px] uppercase tracking-[0.12em] first:ml-0 ${me!.role_type === r ? 'bg-ink text-bg' : 'bg-surface hover:bg-surface-2'}`}>
                  {r === 'employee' ? 'Work' : r === 'student' ? 'Study' : 'Other'}
                </button>
              ))}
            </div>
          </div>
          <label className="flex cursor-pointer items-start gap-3">
            <input type="checkbox" className="mt-1 h-5 w-5 accent-[var(--hot)]" checked={me!.user.reminders} disabled={busy}
              onChange={(e) => run(() => api.updateProfile({ reminders: e.target.checked }), e.target.checked ? 'Daily reminders on.' : 'Daily reminders off.')} />
            <span>
              <span className="font-semibold">Email me a daily reminder</span>
              <span className="block text-sm text-ink-2">One email around 9am your time, only on days you haven’t checked in yet.</span>
            </span>
          </label>
        </div>
      </Section>

      <Section eyebrow="Organisation" title={m ? m.org_name : 'Not part of an organisation'}>
        {!m ? (
          <div className="flex flex-wrap items-center gap-4">
            <p className="mr-auto text-ink-2">Your check-ins are visible only to you.</p>
            <Link to="/start" className="btn btn-hot">Add your team or school</Link>
          </div>
        ) : (
          <div className="space-y-6">
            <dl className="grid border-2 border-line sm:grid-cols-3">
              {[
                ['Your role', m.role],
                [m.org_kind === 'school' ? 'Class' : 'Team', m.group_name ?? '—'],
                ['Sharing since', m.sharing_since ? new Date(m.sharing_since).toLocaleDateString() : 'Not sharing'],
              ].map(([k, v], i) => (
                <div key={k} className={`p-4 ${i ? 'border-line max-sm:border-t-2 sm:border-l-2' : ''}`}>
                  <dt className="b-mono text-ink-3">{k}</dt>
                  <dd className="b-display mt-1 text-3xl">{v}</dd>
                </div>
              ))}
            </dl>
            {m.sharing_since ? (
              <div className="flex flex-wrap items-center gap-4 border-2 border-line bg-surface-2 p-4">
                <p className="mr-auto max-w-xl text-sm">
                  Check-ins since {new Date(m.sharing_since).toLocaleDateString()} count toward {m.org_name}’s team-level averages (never individually).
                </p>
                <button className="btn" disabled={busy} onClick={() => run(api.stopSharing, 'You’ve stopped sharing.', `Stop sharing with ${m.org_name}? Your history stays yours.`)}>Stop sharing</button>
              </div>
            ) : isAdmin(me) && org.data && org.data.groups.length > 0 ? (
              <div className="flex flex-wrap items-center gap-3 border-2 border-line bg-surface-2 p-4">
                <p className="mr-auto max-w-lg text-sm">As an admin you don’t take part by default. Add your own check-ins to a team’s average?</p>
                <select className="field w-auto" value={group ?? ''} onChange={(e) => setGroup(Number(e.target.value) || null)}>
                  <option value="">Choose…</option>
                  {org.data.groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
                <button className="btn btn-ink" disabled={!group || busy} onClick={() => run(() => api.startSharing(group!), 'Now sharing.')}>Start sharing</button>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-3">
              {isAdmin(me) && <Link to={`/org/${m.org_id}/settings`} className="btn">Invite people</Link>}
              <button className="btn" disabled={busy} onClick={() => run(api.leaveOrg, `You left ${m.org_name}.`, `Leave ${m.org_name}? They’ll stop seeing your check-ins immediately.`)}>
                Leave {m.org_name}
              </button>
            </div>
          </div>
        )}
      </Section>

      <PasswordSection onSaved={(next) => { setMe(next); setSaved('Password changed. Other devices were signed out.') }} />

      <Section eyebrow="Your data" title="Yours. Full stop.">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="b-display text-2xl">Download everything</h3>
            <p className="mt-2 text-sm text-ink-2">Your account details and every check-in, with its explanation, as a JSON file.</p>
            <a href={api.exportUrl} download className="btn mt-4">Download my data</a>
          </div>
          <DeleteSection onDeleted={() => { setMe(null); navigate('/', { replace: true }) }} />
        </div>
      </Section>

      <p className="b-mono text-center text-ink-3">
        <Link to="/privacy" className="border-b-2 border-line">Privacy policy</Link> · <Link to="/terms" className="border-b-2 border-line">Terms</Link>
      </p>
    </div>
  )
}

function PasswordSection({ onSaved }: { onSaved: (me: Me) => void }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onSaved(await api.changePassword(current, next))
      setCurrent('')
      setNext('')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Section eyebrow="Security" title="Password">
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <Field label="Current password"><input className="field" type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} /></Field>
        <Field label="New password"><input className="field" type="password" autoComplete="new-password" required minLength={8} value={next} onChange={(e) => setNext(e.target.value)} /></Field>
        <button className="btn btn-ink" disabled={busy}>{busy ? 'Saving…' : 'Change password'}</button>
      </form>
      {error && <div className="mt-4"><Notice tone="error">{error}</Notice></div>}
    </Section>
  )
}

function DeleteSection({ onDeleted }: { onDeleted: () => void }) {
  const { me } = useAuth()
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const soleOwner = me?.membership?.role === 'owner'
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.deleteAccount(password)
      onDeleted()
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }
  return (
    <div>
      <h3 className="b-display text-2xl">Delete my account</h3>
      <p className="mt-2 text-sm text-ink-2">Permanently erases your account and every check-in. This can’t be undone.</p>
      {!open ? (
        <button onClick={() => setOpen(true)} className="btn mt-4 border-[var(--critical)] text-[var(--critical)]">Delete account…</button>
      ) : (
        <form onSubmit={submit} className="mt-4 space-y-3 border-2 border-line bg-surface-2 p-4">
          {soleOwner && (
            <Notice tone="hot">You own {me!.membership!.org_name}. Deleting your account also closes the organisation. Its members keep their own accounts.</Notice>
          )}
          <Field label='Type DELETE to confirm'><input className="field" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></Field>
          <Field label="Your password"><input className="field" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          {error && <Notice tone="error">{error}</Notice>}
          <div className="flex gap-3">
            <button className="btn btn-ink" disabled={busy || confirm !== 'DELETE'}>{busy ? 'Deleting…' : 'Delete forever'}</button>
            <button type="button" className="btn" onClick={() => setOpen(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}
