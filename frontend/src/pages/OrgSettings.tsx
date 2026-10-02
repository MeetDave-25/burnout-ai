import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErrorNote, Notice, PageHead, Section, Spinner, Stat } from '../components/ui'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'

/** Admin console: teams/classes, invite links, and the privacy rules in force. */
export default function OrgSettings() {
  const orgId = Number(useParams().orgId)
  const admin = useAsync(() => api.orgAdmin(orgId), [orgId])
  const [groupName, setGroupName] = useState('')
  const [invite, setInvite] = useState<{ role: 'member' | 'admin'; group_id: number | null }>({ role: 'member', group_id: null })
  const [copied, setCopied] = useState<string | null>(null)
  const [emails, setEmails] = useState('')
  const [sent, setSent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (admin.error) return <div className="px-4 py-20"><ErrorNote message={admin.error} /></div>
  if (!admin.data) return <div className="grid place-items-center py-32"><Spinner /></div>
  const { org, groups, invites, role, admins } = admin.data
  const unit = org.kind === 'school' ? 'class' : 'team'
  const units = org.kind === 'school' ? 'classes' : 'teams'
  const people = groups.reduce((s, g) => s + g.members, 0)

  const act = async (fn: () => Promise<unknown>) => {
    setError(null)
    try {
      await fn()
      admin.reload()
    } catch (err) {
      setError((err as Error).message)
    }
  }
  const addGroup = (e: FormEvent) => {
    e.preventDefault()
    if (groupName.trim()) void act(async () => { await api.addGroup(orgId, groupName); setGroupName('') })
  }
  const sendEmails = (e: FormEvent) => {
    e.preventDefault()
    const list = emails.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean)
    if (!list.length) return
    void act(async () => {
      const r = await api.inviteEmails(orgId, { emails: list, role: invite.role, group_id: invite.group_id })
      setSent(`Invitation sent to ${r.sent} ${r.sent === 1 ? 'person' : 'people'}.`)
      setEmails('')
    })
  }
  const link = (code: string) => `${window.location.origin}/join/${code}`
  const copy = async (code: string) => {
    try {
      await navigator.clipboard.writeText(link(code))
      setCopied(code)
      setTimeout(() => setCopied(null), 1600)
    } catch {
      window.prompt('Copy this invite link', link(code))
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 pb-20 sm:px-6">
      <PageHead eyebrow={`Organisation settings · you are ${role}`} title={org.name}
        aside={<Link to={`/org/${org.id}`} className="btn btn-hot">Open org pulse →</Link>}>
        Invite people, organise {units}, and see the privacy rules that protect them.
      </PageHead>
      {error && <Notice tone="error">{error}</Notice>}

      <div className="grid gap-0 sm:grid-cols-3">
        <Stat label="People sharing" value={people} hint="across all groups" />
        <div className="max-sm:-mt-[2px] sm:-ml-[2px]"><Stat label={units} value={groups.length} /></div>
        <div className="max-sm:-mt-[2px] sm:-ml-[2px]"><Stat label="Admins" value={admins} tone="ink" /></div>
      </div>

      <Section eyebrow="Invite" title="Invite people" tone="hot">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block">
            <span className="b-mono mb-2 block">Role</span>
            <select className="field w-auto" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value as 'member' | 'admin' })}>
              <option value="member">Member (takes check-ins)</option>
              {role === 'owner' && <option value="admin">Admin (sees aggregates)</option>}
            </select>
          </label>
          <label className="block">
            <span className="b-mono mb-2 block">{unit}</span>
            <select className="field w-auto" value={invite.group_id ?? ''} onChange={(e) => setInvite({ ...invite, group_id: Number(e.target.value) || null })}>
              <option value="">{invite.role === 'member' ? `They choose their ${unit}` : 'None'}</option>
              {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </label>
          <button className="btn btn-ink" onClick={() => act(() => api.createInvite(orgId, invite))}>Create invite link</button>
        </div>
        <p className="mt-4 text-sm">Each link works for 14 days. Anyone with it can join, after reading exactly what you can and can’t see.</p>
        <form onSubmit={sendEmails} className="mt-6 border-t-2 border-[#0b0b0b] pt-6">
          <label className="block">
            <span className="b-mono mb-2 block">Or email the invitation (up to 50 addresses)</span>
            <textarea className="field min-h-24" value={emails} onChange={(e) => setEmails(e.target.value)}
              placeholder={'asha@company.com, dev@company.com\nmaya@company.com'} />
          </label>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <button className="btn btn-ink">Send invitations</button>
            {sent && <span className="b-mono">■ {sent}</span>}
          </div>
        </form>
      </Section>

      <Section eyebrow="Active links" title={`${invites.length} invite link${invites.length === 1 ? '' : 's'}`}>
        {invites.length === 0 ? <p className="text-ink-2">No active links yet. Create one above.</p> : (
          <div className="border-t-2 border-line">
            {invites.map((i) => (
              <div key={i.code} className="grid items-center gap-3 border-b-2 border-line py-3 md:grid-cols-[1fr_auto_auto_auto]">
                <code className="truncate font-mono text-sm">{link(i.code)}</code>
                <span className="b-mono text-ink-3">
                  {i.role} · {groups.find((g) => g.id === i.group_id)?.name ?? `any ${unit}`} · {i.uses} joined · until {new Date(i.expires_at).toLocaleDateString()}
                </span>
                <button className="btn" onClick={() => copy(i.code)}>{copied === i.code ? 'Copied ✓' : 'Copy'}</button>
                <button className="btn" onClick={() => act(() => api.revokeInvite(orgId, i.code))}>Revoke</button>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section eyebrow={units} title={`Your ${units}`}>
        <div className="border-t-2 border-line">
          {groups.map((g) => (
            <div key={g.id} className="flex items-center justify-between border-b-2 border-line py-3">
              <span className="font-semibold">{g.name}</span>
              <span className="b-mono text-ink-3">
                {g.members} sharing {g.members < 5 && <span className="ml-2 bg-ink px-1.5 py-0.5 text-bg">hidden until 5</span>}
              </span>
            </div>
          ))}
        </div>
        <form onSubmit={addGroup} className="mt-5 flex flex-wrap gap-3">
          <input className="field max-w-sm" placeholder={`New ${unit} name`} value={groupName} onChange={(e) => setGroupName(e.target.value)} />
          <button className="btn btn-ink">Add {unit}</button>
        </form>
      </Section>

      <Section eyebrow="Privacy rules in force" title="What you can never see" tone="ink">
        <ul className="grid gap-3 text-sm sm:grid-cols-2">
          <li>■ Any individual’s score, answers, forecast or history.</li>
          <li>■ Any {unit} with fewer than 5 people answering. It shows as locked.</li>
          <li>■ Anything from before someone joined, or after they stop sharing.</li>
          <li>■ Use for performance reviews is prohibited by our terms.</li>
        </ul>
      </Section>
    </div>
  )
}
