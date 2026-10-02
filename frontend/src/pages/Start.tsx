import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Field, Notice, PageHead } from '../components/ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

/** Onboarding fork: just me / set up an organisation / join with an invite. */
export default function Start() {
  const { me, refresh } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'org' | 'join' | null>(null)
  const [org, setOrg] = useState({ name: '', kind: 'company' as 'company' | 'school', groups: '' })
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const createOrg = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const groups = org.groups.split(/[\n,]/).map((g) => g.trim()).filter(Boolean)
      const created = await api.createOrg(org.name, org.kind, groups)
      await refresh()
      navigate(`/org/${created.id}/settings`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const join = (e: FormEvent) => {
    e.preventDefault()
    const c = code.trim().split('/').filter(Boolean).pop()
    if (c) navigate(`/join/${c}`)
  }

  const inOrg = !!me?.membership
  const options = [
    { id: 'me', n: '01', title: 'Just me', body: 'A 1-minute check-in a day, your trend and your levers. Free, private.', cta: 'Take my first check-in →' },
    { id: 'org', n: '02', title: org.kind === 'school' ? 'My school' : 'My company', body: 'Team-level heat maps for HR, managers or student wellbeing. Groups under 5 stay hidden.', cta: 'Set up an organisation →' },
    { id: 'join', n: '03', title: 'I have an invite', body: 'Your organisation sent you a link or a code.', cta: 'Join with a code →' },
  ] as const

  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
      <PageHead eyebrow={`Welcome${me ? `, ${me.user.name.split(' ')[0]}` : ''}`} title={<>How will you<br />use <span className="text-hot">BurnoutAI?</span></>}>
        You can always add a team later. Your personal check-ins stay yours either way.
      </PageHead>
      {inOrg && <div className="mt-6"><Notice>You’re already in <b>{me!.membership!.org_name}</b>. Leave it from Account to create or join another.</Notice></div>}

      <div className="mt-8 grid md:grid-cols-3">
        {options.map((o, i) => (
          <button
            key={o.id}
            disabled={inOrg && o.id !== 'me'}
            onClick={() => (o.id === 'me' ? navigate('/check-in') : setMode(o.id))}
            className={`group flex min-h-[260px] flex-col justify-between border-2 border-line p-6 text-left transition-colors disabled:opacity-40 ${i ? 'md:-ml-[2px]' : ''} max-md:-mt-[2px] ${
              mode === o.id ? 'bg-ink text-bg' : 'bg-surface hover:bg-hot hover:text-[#0b0b0b]'
            }`}
          >
            <div className="b-mono opacity-70">{o.n}</div>
            <div>
              <div className="b-display text-5xl leading-none">{o.title}</div>
              <p className="mt-3 text-sm opacity-80">{o.body}</p>
              <div className="b-mono mt-6">{o.cta}</div>
            </div>
          </button>
        ))}
      </div>

      {error && <div className="mt-6"><Notice tone="error">{error}</Notice></div>}

      {mode === 'org' && (
        <form onSubmit={createOrg} className="mt-8 grid gap-5 border-2 border-line bg-surface p-6 md:grid-cols-2">
          <Field label="Organisation name"><input className="field" required value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} /></Field>
          <Field label="Type">
            <div className="grid grid-cols-2">
              {(['company', 'school'] as const).map((k, i) => (
                <button type="button" key={k} onClick={() => setOrg({ ...org, kind: k })} aria-pressed={org.kind === k}
                  className={`border-2 border-line py-3 font-mono text-[11px] uppercase tracking-[0.12em] ${i ? '-ml-[2px]' : ''} ${org.kind === k ? 'bg-ink text-bg' : 'bg-surface'}`}>
                  {k}
                </button>
              ))}
            </div>
          </Field>
          <div className="md:col-span-2">
            <Field label={org.kind === 'school' ? 'Classes or cohorts' : 'Teams or departments'} hint="One per line or comma-separated. You can add more later.">
              <textarea className="field min-h-28" value={org.groups} onChange={(e) => setOrg({ ...org, groups: e.target.value })}
                placeholder={org.kind === 'school' ? 'CS Final Year\nDesign Year 2' : 'Engineering\nCustomer Support\nSales'} />
            </Field>
          </div>
          <div className="md:col-span-2 flex flex-wrap items-center justify-between gap-4">
            <p className="max-w-lg text-xs text-ink-3">You’ll be the owner. You’ll see team-level aggregates only, never an individual’s answers.</p>
            <button className="btn btn-hot" disabled={busy}>{busy ? 'Creating…' : 'Create organisation →'}</button>
          </div>
        </form>
      )}

      {mode === 'org' && (
        <p className="b-mono mt-4 text-ink-3">
          Want to see it first? <a href="/org" className="border-b-2 border-line text-ink">Open a sample company →</a>
        </p>
      )}

      {mode === 'join' && (
        <form onSubmit={join} className="mt-8 flex flex-wrap gap-0 border-2 border-line bg-surface p-6">
          <div className="min-w-0 flex-1"><Field label="Invite link or code"><input className="field" required value={code} onChange={(e) => setCode(e.target.value)} placeholder="https://…/join/AbC123xyz or AbC123xyz" /></Field></div>
          <button className="btn btn-ink mt-[26px] self-start">Continue →</button>
        </form>
      )}
    </div>
  )
}
