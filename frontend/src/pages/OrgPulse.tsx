import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Distribution, type Segment } from '../components/Distribution'
import { Sparkline, TimeChart } from '../components/TimeChart'
import { ErrorNote, LevelBadge, Notice, PageHead, Pill, Section, Spinner, Stat } from '../components/ui'
import { api, type DriverAgg, type DriverChange, type GroupInsight, type OrgInsights } from '../lib/api'
import { isAdmin, useAuth } from '../lib/auth'
import { heatColor, inkOn, LEVELS } from '../lib/heat'
import { useAsync, useIsDark } from '../lib/hooks'

const levelOf = (s: number) => (s >= 75 ? 2 : s >= 50 ? 1 : 0)
const signed = (n: number) => `${n > 0 ? '+' : '−'}${Math.abs(n).toFixed(1)}`

export default function OrgPulse() {
  const { orgId } = useParams()
  const navigate = useNavigate()
  const { me, ready } = useAuth()
  const orgs = useAsync(() => api.orgs(), [me?.membership?.org_id])
  const id = orgId ? Number(orgId) : undefined
  const insights = useAsync(() => (id ? api.insights(id) : Promise.resolve(null)), [id])
  const [selected, setSelected] = useState<number | null>(null)
  useEffect(() => setSelected(null), [id])

  if (!id) {
    if (!ready || !orgs.data) return <div className="grid place-items-center py-40"><Spinner /></div>
    const target = isAdmin(me) ? me!.membership!.org_id : orgs.data.find((o) => o.is_demo)?.id
    return target ? <Navigate to={`/org/${target}`} replace /> : <div className="px-4 py-20"><Notice>No organisations yet.</Notice></div>
  }
  if (orgs.error) return <div className="px-4 py-20"><ErrorNote message={orgs.error} onRetry={orgs.reload} /></div>

  const summary = orgs.data?.find((o) => o.id === id)
  const switchable = orgs.data?.filter((o) => o.is_demo || o.role !== 'member') ?? []
  const data = insights.data
  const visibleGroups = data?.groups.filter((g) => !g.suppressed) ?? []
  const group = data?.groups.find((g) => g.group_id === selected) ?? null
  const canManage = !!summary && !summary.is_demo && (summary.role === 'owner' || summary.role === 'admin')

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 pb-24 sm:px-6">
      {data ? (
        <PageHead
          eyebrow={`Org pulse · last 30 days${summary?.is_demo ? ' · public demo' : ''}`}
          title={data.org_name}
          aside={canManage ? <Link to={`/org/${id}/settings`} className="btn btn-ink">Settings & invites</Link>
            : summary?.is_demo ? <Link to="/signup?next=/start" className="btn btn-hot">Set up your own →</Link> : null}
        >
          Team-level heat only. Individual answers never appear here; any group with fewer than {data.min_group_size} people responding stays locked.
        </PageHead>
      ) : <div className="pt-10" />}

      {switchable.length > 1 && (
        <div className="flex flex-wrap">
          {switchable.map((o) => (
            <span key={o.id} className="-ml-[2px] first:ml-0">
              <Pill active={o.id === id} onClick={() => navigate(`/org/${o.id}`)}>{o.name}{o.is_demo ? '' : ` · ${o.role}`}</Pill>
            </span>
          ))}
        </div>
      )}

      {!data && insights.loading && <div className="py-32"><Spinner label="Taking the team's temperature" /></div>}
      {insights.error && (
        <Notice tone="error">
          {insights.error.includes('admins') ? 'Only organisation admins can see this pulse. Members see their own data under My pulse.' : insights.error}
        </Notice>
      )}

      {data && (
        <div className={`space-y-6 transition-opacity ${insights.loading ? 'opacity-60' : ''}`}>
          <div className="grid grid-cols-2 md:grid-cols-4">
            <Stat label="Average" value={data.avg_score != null ? Math.round(data.avg_score) : '—'}
              hint={data.avg_score != null ? <LevelBadge level={levelOf(data.avg_score)} /> : 'too few responses yet'} />
            <div className="-ml-[2px]"><Stat label="Responding" value={data.respondents} hint="last 30 days" /></div>
            <div className="max-md:-mt-[2px] md:-ml-[2px]"><Stat label="Trending up" value={data.rising_count ?? '—'} hint="people rising" tone="ink" /></div>
            <div className="-ml-[2px] max-md:-mt-[2px]"><Stat label="Early warnings" value={data.early_warning_count ?? '—'} hint="heading for the line" tone="hot" /></div>
          </div>

          {data.respondents === 0 && canManage && (
            <Notice tone="hot">Nobody has checked in yet. <Link to={`/org/${id}/settings`} className="border-b-2 border-[#0b0b0b] font-semibold">Create an invite link</Link> and share it with your teams.</Notice>
          )}

          <section className="border-2 border-line bg-surface">
            <div className="flex flex-wrap items-end justify-between gap-4 border-b-2 border-line px-5 py-4 sm:px-7">
              <div>
                <div className="b-mono text-ink-3">Thermal map</div>
                <h2 className="b-display mt-1 text-4xl">Where the weight is</h2>
              </div>
              <HeatLegend />
            </div>
            <div className="flex flex-wrap p-5 sm:p-7">
              {data.groups.map((g, i) => (
                <GroupTile key={g.group_id} g={g} i={i} selected={g.group_id === selected} onSelect={() => setSelected(g.group_id === selected ? null : g.group_id)} />
              ))}
            </div>
            <div className="b-mono border-t-2 border-line px-5 py-3 text-ink-3 sm:px-7">Tile size = people responding · select a team for its breakdown</div>
          </section>

          <AnimatePresence mode="wait">
            {group && !group.suppressed ? (
              <motion.div key={group.group_id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <GroupDetail g={group} />
              </motion.div>
            ) : (
              <motion.div key="org" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <OrgOverview data={data} groups={visibleGroups} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}

function HeatLegend() {
  const dark = useIsDark()
  const stops = Array.from({ length: 11 }, (_, i) => heatColor(i * 10, dark)).join(', ')
  return (
    <div className="w-56">
      <div className="h-3 border-2 border-line" style={{ background: `linear-gradient(90deg, ${stops})` }} />
      <div className="b-mono relative mt-1.5 h-3 text-[10px] text-ink-3">
        <span className="absolute left-0">0</span>
        <span className="absolute left-1/2 -translate-x-1/2">50</span>
        <span className="absolute left-3/4 -translate-x-1/2">75</span>
        <span className="absolute right-0">100</span>
      </div>
    </div>
  )
}

function GroupTile({ g, i, selected, onSelect }: { g: GroupInsight; i: number; selected: boolean; onSelect: () => void }) {
  const dark = useIsDark()
  const grow = Math.max(g.member_count, 3)
  const base = '-ml-[2px] -mt-[2px] relative flex min-h-[180px] min-w-[160px] flex-col justify-between border-2 border-line p-4 text-left'
  if (g.suppressed) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
        className={`${base} hazard-cool`} style={{ flexGrow: grow, flexBasis: 0 }}>
        <div className="bg-surface px-1 text-sm font-semibold">{g.group_name}</div>
        <div className="bg-surface p-2">
          <div className="b-display text-2xl">Locked</div>
          <div className="text-xs text-ink-2">{g.member_count} of 5 responses needed to protect privacy</div>
        </div>
      </motion.div>
    )
  }
  const score = g.avg_score ?? 0
  const ink = inkOn(score, dark)
  return (
    <motion.button
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={`${g.group_name}: average ${Math.round(score)}, ${g.rising_count} rising`}
      className={`${base} transition-transform hover:z-10 hover:-translate-x-1 hover:-translate-y-1 hover:shadow-hard ${selected ? 'z-10 -translate-x-1 -translate-y-1 shadow-hard outline outline-4 outline-[var(--line)]' : ''}`}
      style={{ flexGrow: grow, flexBasis: 0, background: heatColor(score, dark), color: ink }}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-bold uppercase">{g.group_name}</span>
        <span className="b-mono opacity-80">{g.member_count} ppl</span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="b-display text-6xl leading-none">{Math.round(score)}</div>
          {!!g.rising_count && <div className="b-mono mt-2">▲ {g.rising_count} rising{g.early_warning_count ? ` · ${g.early_warning_count} warn` : ''}</div>}
        </div>
        <Sparkline values={g.weekly_trend?.map((t) => t.avg_score) ?? []} width={84} height={30} color={ink} />
      </div>
    </motion.button>
  )
}

function DriverBars({ drivers, title }: { drivers: DriverAgg[]; title: string }) {
  const max = Math.max(1, ...drivers.map((d) => d.avg_impact))
  return (
    <div>
      <div className="b-mono mb-3 text-ink-3">{title}</div>
      {drivers.length === 0 && <div className="text-sm text-ink-3">No factor is adding weight above average.</div>}
      <div className="space-y-2">
        {drivers.map((d) => (
          <div key={d.feature} className="grid grid-cols-[9rem_1fr] items-center gap-3" title={`${d.label}: +${d.avg_impact} points on average`}>
            <span className="truncate text-sm font-semibold">{d.label}</span>
            <div className="flex items-center gap-2">
              <motion.div initial={{ width: 0 }} whileInView={{ width: `${(d.avg_impact / max) * 80}%` }} viewport={{ once: true }}
                className="h-4 border-2 border-line bg-hot" />
              <span className="tabular font-mono text-xs">+{d.avg_impact.toFixed(1)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ChangeBars({ changes }: { changes: DriverChange[] }) {
  const max = Math.max(1, ...changes.map((c) => Math.abs(c.change)))
  return (
    <div>
      <div className="b-mono mb-3 text-ink-3">What changed · first 2 weeks vs last 2</div>
      {changes.length === 0 && <div className="text-sm text-ink-3">No meaningful shifts, or not enough responses in both periods.</div>}
      <div className="space-y-2">
        {changes.map((c) => {
          const up = c.change > 0
          const pct = (Math.abs(c.change) / max) * 45
          return (
            <div key={c.feature} className="grid grid-cols-[9rem_1fr] items-center gap-3">
              <span className="truncate text-sm font-semibold">{c.label}</span>
              <div className="relative h-6">
                <div className="absolute inset-y-0 left-1/2 w-[2px] bg-line" />
                <motion.div initial={{ width: 0 }} whileInView={{ width: `${pct}%` }} viewport={{ once: true }}
                  className="absolute top-1/2 h-4 -translate-y-1/2 border-2 border-line"
                  style={{ [up ? 'left' : 'right']: '50%', background: up ? 'var(--heat)' : 'var(--cool)' }} />
                <span className="tabular absolute top-1/2 -translate-y-1/2 font-mono text-xs"
                  style={up ? { left: `calc(50% + ${pct}% + 6px)` } : { right: `calc(50% + ${pct}% + 6px)` }}>
                  {signed(c.change)}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function levelSegments(dist: Record<string, number>): Segment[] {
  return LEVELS.map((l) => ({ key: l.label, label: l.label, value: dist[l.label] ?? 0, color: l.token, icon: l.icon, text: l.level === 1 ? '#0b0b0b' : undefined }))
}

const PATTERN_COLORS: Record<string, string> = { Frenetic: 'var(--cat-1)', 'Worn-Out': 'var(--cat-2)', 'Under-Challenged': 'var(--cat-3)' }

function GroupDetail({ g }: { g: GroupInsight }) {
  const trend = (g.weekly_trend ?? []).map((t) => ({ date: new Date(t.week_ending), value: t.avg_score }))
  const patterns = Object.entries(PATTERN_COLORS).map(([k, color]) => ({ key: k, label: k, value: g.pattern_distribution?.[k] ?? 0, color }))
  const low = g.pattern_distribution?.None ?? 0
  return (
    <div className="space-y-6">
      <Section eyebrow={`Team · ${g.member_count} people`} title={<>{g.group_name}: <span className="text-hot">why the weight?</span></>}
        aside={g.avg_score != null && <LevelBadge level={levelOf(g.avg_score)} label={`Avg ${Math.round(g.avg_score)}`} />}>
        <TimeChart points={trend} label={`${g.group_name} weekly average burnout score`} height={240} />
        <div className="mt-10 grid gap-10 md:grid-cols-2">
          <DriverBars drivers={g.top_drivers ?? []} title="Top factors adding weight (avg points)" />
          <ChangeBars changes={g.what_changed ?? []} />
        </div>
      </Section>
      <div className="grid gap-6 md:grid-cols-2">
        <Section eyebrow="Levels" title="How people are doing"><Distribution segments={levelSegments(g.level_distribution ?? {})} /></Section>
        <Section eyebrow="Patterns" title="What kind of burnout">
          <Distribution segments={patterns} />
          {low > 0 && <div className="mt-3 text-xs text-ink-3">{low} people are in the low range, so no pattern is assigned.</div>}
        </Section>
      </div>
    </div>
  )
}

function OrgOverview({ data, groups }: { data: OrgInsights; groups: GroupInsight[] }) {
  if (data.avg_score == null) return null
  const ranked = [...groups].sort((a, b) => (b.avg_score ?? 0) - (a.avg_score ?? 0))
  return (
    <div className="grid gap-6 md:grid-cols-[1.2fr_1fr]">
      <Section eyebrow="Organisation-wide" title="What drives the weight">
        <DriverBars drivers={data.top_drivers} title="Average points added across everyone" />
        <div className="mt-8">
          <div className="b-mono mb-3 text-ink-3">Levels across {data.respondents} people</div>
          <Distribution segments={levelSegments(data.level_distribution)} />
        </div>
      </Section>
      <Section eyebrow="Watchlist" title="Talk to first" tone="ink">
        <ul>
          {ranked.map((g, i) => (
            <li key={g.group_id} className={`flex items-center justify-between gap-4 py-3 ${i ? 'border-t-2 border-bg/25' : ''}`}>
              <div>
                <div className="font-bold uppercase">{g.group_name}</div>
                <div className="text-xs opacity-75">
                  {g.top_drivers?.[0] ? `Mainly ${g.top_drivers[0].label.toLowerCase()}` : 'No standout factor'}
                  {g.rising_count ? ` · ${g.rising_count} rising` : ''}
                </div>
              </div>
              <span className="b-display text-4xl" style={{ color: (g.avg_score ?? 0) >= 50 ? 'var(--hot)' : undefined }}>{Math.round(g.avg_score ?? 0)}</span>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}
