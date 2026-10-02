import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Notice, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync } from '../lib/hooks'

/** Accept an organisation invite, after reading exactly what is (and isn't) shared. */
export default function Join() {
  const { code = '' } = useParams()
  const { me, ready, setMe } = useAuth()
  const navigate = useNavigate()
  const invite = useAsync(() => api.invite(code), [code])
  const [group, setGroup] = useState<number | null>(null)
  const [agree, setAgree] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (invite.error) return <div className="px-4 py-20"><Notice tone="error">{invite.error}</Notice></div>
  if (!invite.data || !ready) return <div className="grid place-items-center py-32"><Spinner /></div>
  const inv = invite.data
  const needsGroup = inv.role === 'member' && inv.group_id == null
  const fixedGroup = inv.groups.find((g) => g.id === inv.group_id)
  const unit = inv.org_kind === 'school' ? 'class' : 'team'

  const accept = async () => {
    setBusy(true)
    setError(null)
    try {
      const m = await api.acceptInvite(code, needsGroup ? group : null)
      setMe(m)
      navigate(inv.role === 'admin' ? `/org/${m.membership!.org_id}` : '/check-in')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 pb-20 pt-10 sm:px-6">
      <div className="b-mono text-ink-3">Invitation · {inv.role === 'admin' ? 'admin access' : 'member'}</div>
      <h1 className="b-display mt-3 text-[clamp(3rem,8vw,6.5rem)] leading-[0.86]">Join <span className="text-hot">{inv.org_name}</span></h1>

      <div className="mt-10 grid md:grid-cols-2">
        <div className="border-2 border-line bg-surface p-6">
          <div className="b-display text-3xl">What {inv.org_name} sees</div>
          <ul className="mt-4 space-y-3 text-sm">
            <li>■ The average burnout level of your {unit}, its trend, and the main factors driving it.</li>
            <li>■ Only when at least <b>{inv.min_group_size} people</b> in the {unit} have answered. Smaller groups stay hidden.</li>
            <li>■ Only check-ins you make <b>after</b> joining.</li>
          </ul>
        </div>
        <div className="-mt-[2px] border-2 border-line bg-ink p-6 text-bg md:-ml-[2px] md:mt-0">
          <div className="b-display text-3xl">What it never sees</div>
          <ul className="mt-4 space-y-3 text-sm opacity-90">
            <li>■ Your individual score, answers, forecast or history.</li>
            <li>■ Anything from before you joined.</li>
            <li>■ Anything at all once you stop sharing or leave. You can do either at any time.</li>
          </ul>
        </div>
      </div>

      {inv.role === 'admin' && (
        <div className="mt-6"><Notice tone="hot">You’re invited as an <b>admin</b>: you’ll see team-level aggregates and manage invites. You won’t take part unless you choose to.</Notice></div>
      )}

      {!me ? (
        <div className="mt-8 flex flex-wrap items-center gap-3 border-2 border-line bg-surface p-6">
          <span className="mr-auto">Create a free account (or log in) to accept.</span>
          <Link to={`/signup?next=/join/${code}`} className="btn btn-hot">Create account</Link>
          <Link to={`/login?next=/join/${code}`} className="btn">Log in</Link>
        </div>
      ) : (
        <div className="mt-8 border-2 border-line bg-surface p-6">
          {needsGroup && (
            <fieldset className="mb-6">
              <legend className="b-mono mb-3 text-ink-2">Your {unit}</legend>
              <div className="flex flex-wrap">
                {inv.groups.map((g) => (
                  <button key={g.id} type="button" onClick={() => setGroup(g.id)} aria-pressed={group === g.id}
                    className={`-ml-[2px] -mt-[2px] border-2 border-line px-4 py-3 text-sm first:ml-0 ${group === g.id ? 'bg-ink text-bg' : 'bg-surface hover:bg-surface-2'}`}>
                    {g.name}
                  </button>
                ))}
              </div>
            </fieldset>
          )}
          {fixedGroup && <p className="b-mono mb-4 text-ink-2">{unit}: {fixedGroup.name}</p>}
          <label className="flex cursor-pointer items-start gap-3 text-sm">
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5 h-5 w-5 accent-[var(--hot)]" />
            I understand what {inv.org_name} can and can’t see, and I agree to share my check-ins as team-level aggregates.
          </label>
          {error && <div className="mt-4"><Notice tone="error">{error}</Notice></div>}
          <button onClick={accept} disabled={!agree || busy || (needsGroup && group == null)} className="btn btn-hot mt-6">
            {busy ? 'Joining…' : `Join ${inv.org_name} →`}
          </button>
        </div>
      )}
    </div>
  )
}
