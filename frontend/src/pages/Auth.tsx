import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { LoadGauge } from '../components/LoadGauge'
import { OtpInput } from '../components/OtpInput'
import { Field, Notice } from '../components/ui'
import { api, type Role } from '../lib/api'
import { useAuth } from '../lib/auth'

function Shell({ title, sub, children }: { title: ReactNode; sub: string; children: ReactNode }) {
  return (
    <div className="grid min-h-[calc(100svh-var(--nav-h))] lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden overflow-hidden border-r-2 border-line bg-[#0b0b0b] p-10 text-[#ece9e2] lg:flex lg:flex-col lg:justify-between">
        <div className="brutal-grid-dark absolute inset-0" />
        <div className="relative">
          <div className="b-mono text-[#ece9e2]/60">BurnoutAI · early warning</div>
          <div className="b-display mt-6 text-[clamp(3.5rem,6.5vw,7rem)] leading-[0.84]">{title}</div>
          <p className="mt-6 max-w-md text-[#ece9e2]/75">{sub}</p>
        </div>
        <div className="relative flex items-end justify-between gap-8">
          <ul className="b-mono space-y-2 text-[#ece9e2]/70">
            <li>■ Validated burnout inventory</li>
            <li>■ Every point explained</li>
            <li>■ Teams under 5 stay hidden</li>
          </ul>
          <div className="[--ink-2:#c4c0b8] [--line:#ece9e2]"><LoadGauge score={58} width={200} /></div>
        </div>
      </aside>
      <div className="flex items-center justify-center px-4 py-12 sm:px-10">{children}</div>
    </div>
  )
}

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const m = await login(email, password)
      const next = params.get('next') || '/me'
      navigate(m.user.email_verified ? next : `/verify?next=${encodeURIComponent(next)}`, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title={<>Welcome<br />back.</>} sub="Your timeline, your forecast and your levers are where you left them.">
      <form onSubmit={submit} className="w-full max-w-md space-y-5">
        <div>
          <div className="b-mono text-ink-3">Log in</div>
          <h1 className="b-display mt-2 text-6xl leading-none">Log in</h1>
        </div>
        {error && <Notice tone="error">{error}</Notice>}
        <Field label="Email"><input className="field" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Password"><input className="field" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <div className="-mt-2 text-right"><Link to={`/forgot${email ? `?email=${encodeURIComponent(email)}` : ''}`} className="b-mono border-b-2 border-line">Forgot password?</Link></div>
        <button className="btn btn-hot w-full" disabled={busy}>{busy ? 'Checking…' : 'Log in →'}</button>
        <p className="text-sm text-ink-2">
          New here? <Link to={`/signup${params.get('next') ? `?next=${encodeURIComponent(params.get('next')!)}` : ''}`} className="border-b-2 border-line font-semibold">Create an account</Link>
        </p>
      </form>
    </Shell>
  )
}

const ROLES: { id: Role; label: string }[] = [
  { id: 'employee', label: 'I work' },
  { id: 'student', label: 'I study' },
  { id: 'general', label: 'Other' },
]

export function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [form, setForm] = useState({ name: '', email: '', password: '', role_type: 'employee' as Role })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const m = await signup(form)
      const next = params.get('next') || '/check-in'
      navigate(m.user.email_verified ? next : `/verify?next=${encodeURIComponent(next)}`, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title={<>See it<br /><span className="text-hot">coming.</span></>} sub="Free for individuals. One 1-minute check-in a day becomes a trend, and the trend becomes an early warning.">
      <form onSubmit={submit} className="w-full max-w-md space-y-5">
        <div>
          <div className="b-mono text-ink-3">Create account · free</div>
          <h1 className="b-display mt-2 text-6xl leading-none">Start free</h1>
        </div>
        {error && <Notice tone="error">{error}</Notice>}
        <Field label="Your name"><input className="field" autoComplete="name" required value={form.name} onChange={set('name')} /></Field>
        <Field label="Email"><input className="field" type="email" autoComplete="email" required value={form.email} onChange={set('email')} /></Field>
        <Field label="Password" hint="At least 8 characters.">
          <input className="field" type="password" autoComplete="new-password" required minLength={8} value={form.password} onChange={set('password')} />
        </Field>
        <fieldset>
          <legend className="b-mono mb-2 text-ink-2">Right now I mostly…</legend>
          <div className="grid grid-cols-3">
            {ROLES.map((r, i) => (
              <button
                type="button"
                key={r.id}
                onClick={() => setForm((f) => ({ ...f, role_type: r.id }))}
                aria-pressed={form.role_type === r.id}
                className={`border-2 border-line py-3 font-mono text-[11px] uppercase tracking-[0.12em] ${i ? '-ml-[2px]' : ''} ${form.role_type === r.id ? 'bg-ink text-bg' : 'bg-surface hover:bg-surface-2'}`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </fieldset>
        <button className="btn btn-hot w-full" disabled={busy}>{busy ? 'Creating…' : 'Create account →'}</button>
        <p className="text-xs text-ink-3">Your check-ins are private to you. Organisations only ever see team-level heat, and only if you join one.</p>
        <p className="text-sm text-ink-2">
          Have an account? <Link to={`/login${params.get('next') ? `?next=${encodeURIComponent(params.get('next')!)}` : ''}`} className="border-b-2 border-line font-semibold">Log in</Link>
        </p>
      </form>
    </Shell>
  )
}

/** Step 2 of sign-up: the 6-digit code we emailed. */
export function Verify() {
  const { me, ready, setMe } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') || '/check-in'
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [wait, setWait] = useState(45)

  useEffect(() => {
    if (wait <= 0) return
    const id = setTimeout(() => setWait((w) => w - 1), 1000)
    return () => clearTimeout(id)
  }, [wait])

  if (!ready) return null
  if (!me) return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />
  if (me.user.email_verified) return <Navigate to={next} replace />

  const submit = async (c = code) => {
    if (c.length !== 6) return
    setBusy(true)
    setError(null)
    try {
      setMe(await api.verify(c))
      navigate(next, { replace: true })
    } catch (err) {
      setError((err as Error).message)
      setCode('')
    } finally {
      setBusy(false)
    }
  }
  const resend = async () => {
    setError(null)
    try {
      await api.resendCode()
      setInfo(`New code sent to ${me.user.email}.`)
      setWait(45)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <Shell title={<>Check your<br /><span className="text-hot">inbox.</span></>} sub="One quick step so your account (and your data) is really yours.">
      <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="w-full max-w-md space-y-6">
        <div>
          <div className="b-mono text-ink-3">Step 2 of 2 · verify email</div>
          <h1 className="b-display mt-2 text-6xl leading-none">Enter the code</h1>
          <p className="mt-3 text-ink-2">We sent a 6-digit code to <b className="text-ink">{me.user.email}</b>. It expires in 10 minutes.</p>
        </div>
        {error && <Notice tone="error">{error}</Notice>}
        {info && !error && <Notice>{info}</Notice>}
        <OtpInput value={code} onChange={setCode} onComplete={(c) => void submit(c)} disabled={busy} />
        <button className="btn btn-hot w-full" disabled={busy || code.length !== 6}>{busy ? 'Checking…' : 'Verify →'}</button>
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <button type="button" onClick={resend} disabled={wait > 0} className="b-mono border-b-2 border-line disabled:border-transparent disabled:text-ink-3">
            {wait > 0 ? `Resend code in ${wait}s` : 'Resend code'}
          </button>
          <span className="text-ink-3">Not in your inbox? Check spam.</span>
        </div>
      </form>
    </Shell>
  )
}

/** Forgot password: email → 6-digit code + new password. */
export function Forgot() {
  const { setMe } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [step, setStep] = useState<'email' | 'reset'>('email')
  const [email, setEmail] = useState(params.get('email') ?? '')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const send = async (e?: FormEvent) => {
    e?.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.forgot(email)
      setStep('reset')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const reset = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setMe(await api.reset(email, code, password))
      navigate('/me', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Shell title={<>Locked<br /><span className="text-hot">out?</span></>} sub="It happens. We’ll email you a code to set a new password.">
      {step === 'email' ? (
        <form onSubmit={send} className="w-full max-w-md space-y-5">
          <div>
            <div className="b-mono text-ink-3">Reset password · step 1 of 2</div>
            <h1 className="b-display mt-2 text-6xl leading-none">Forgot password</h1>
          </div>
          {error && <Notice tone="error">{error}</Notice>}
          <Field label="Your account email"><input className="field" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <button className="btn btn-hot w-full" disabled={busy}>{busy ? 'Sending…' : 'Email me a code →'}</button>
          <p className="text-sm text-ink-2">Remembered it? <Link to="/login" className="border-b-2 border-line font-semibold">Log in</Link></p>
        </form>
      ) : (
        <form onSubmit={reset} className="w-full max-w-md space-y-5">
          <div>
            <div className="b-mono text-ink-3">Reset password · step 2 of 2</div>
            <h1 className="b-display mt-2 text-6xl leading-none">New password</h1>
            <p className="mt-3 text-ink-2">If <b className="text-ink">{email}</b> has an account, a 6-digit code is on its way.</p>
          </div>
          {error && <Notice tone="error">{error}</Notice>}
          <OtpInput value={code} onChange={setCode} disabled={busy} />
          <Field label="New password" hint="At least 8 characters. You’ll be signed out everywhere else.">
            <input className="field" type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <button className="btn btn-hot w-full" disabled={busy || code.length !== 6}>{busy ? 'Saving…' : 'Set new password →'}</button>
          <button type="button" onClick={() => send()} className="b-mono border-b-2 border-line">Send another code</button>
        </form>
      )}
    </Shell>
  )
}
