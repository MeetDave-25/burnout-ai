import { AnimatePresence, motion } from 'motion/react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LoadGauge } from '../components/LoadGauge'
import { ErrorNote, Notice, Spinner } from '../components/ui'
import { api, type DailyKey, type Drivers, type Question } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync, useDebounced } from '../lib/hooks'

/**
 * Today's check-in: 6 single-tap questions (~1 minute), plus the 6-question weekly measure once a week.
 * One per day; afterwards this page just says so.
 */

const TYPICAL: Record<DailyKey, number> = {
  sleep_hours: 7.5, work_hours_per_day: 9, after_hours_per_week: 1.5, workload: 3, can_disconnect: 3, support: 3,
}

export default function CheckIn() {
  const { me, refresh } = useAuth()
  const navigate = useNavigate()
  const instrument = useAsync(() => api.instrument(), [])
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [index, setIndex] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const daily = instrument.data?.questions ?? []
  const weekly = instrument.data?.weekly_due ? instrument.data.weekly : []
  const all: (Question & { weekly: boolean })[] = useMemo(
    () => [...daily.map((q) => ({ ...q, weekly: false })), ...weekly.map((q) => ({ ...q, weekly: true }))],
    [daily, weekly],
  )
  const q = all[index]

  const drivers = useMemo<Drivers>(() => {
    const d = { ...TYPICAL }
    for (const k of Object.keys(TYPICAL) as DailyKey[]) if (answers[k] != null) d[k] = answers[k]
    return { ...d, role_type: me?.role_type ?? 'employee', remote_work: false }
  }, [answers, me?.role_type])
  const weeklyAnswers = useMemo(
    () => Object.fromEntries(weekly.filter((w) => answers[w.id] != null).map((w) => [w.id, answers[w.id]])),
    [answers, weekly],
  )

  // Live estimate as you tap.
  const debounced = useDebounced(drivers, 250)
  const [estimate, setEstimate] = useState<number | null>(null)
  const answeredDaily = daily.filter((d) => answers[d.id] != null).length
  useEffect(() => {
    if (!answeredDaily) return
    let alive = true
    api.predict(debounced).then((p) => alive && setEstimate(p.explanation.estimated_score)).catch(() => {})
    return () => { alive = false }
  }, [JSON.stringify(debounced)]) // eslint-disable-line react-hooks/exhaustive-deps
  const weeklyVals = Object.values(weeklyAnswers)
  const live = q?.weekly && weeklyVals.length ? (weeklyVals.reduce((a, b) => a + b, 0) / weeklyVals.length) * 25 : estimate ?? 0

  const submit = useCallback(async (finalAnswers: Record<string, number>) => {
    setSubmitting(true)
    setError(null)
    try {
      const d = { ...drivers }
      for (const k of Object.keys(TYPICAL) as DailyKey[]) if (finalAnswers[k] != null) d[k] = finalAnswers[k]
      const cbi = Object.fromEntries(weekly.map((w) => [w.id, finalAnswers[w.id]]).filter(([, v]) => v != null))
      await api.myCheckIn(d, Object.keys(cbi).length ? cbi : null)
      await refresh()
      navigate('/me', { state: { fresh: true } })
    } catch (e) {
      setError((e as Error).message)
      setSubmitting(false)
    }
  }, [drivers, weekly, refresh, navigate])

  const choose = useCallback((value: number) => {
    if (!q || submitting) return
    const next = { ...answers, [q.id]: value }
    setAnswers(next)
    if (index === all.length - 1) void submit(next)
    else setTimeout(() => setIndex((i) => i + 1), 150)
  }, [q, answers, index, all.length, submit, submitting])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const n = Number(e.key)
      if (q && n >= 1 && n <= q.options.length) choose(q.options[n - 1].value)
      else if (e.key === 'ArrowLeft' || e.key === 'Backspace') setIndex((i) => Math.max(0, i - 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [q, choose])

  if (me?.today.done) return <DoneToday nextAt={me.today.next_at} />

  const minutes = all.length > 6 ? '~2 min' : '~1 min'
  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <div className="grid h-14 grid-cols-[auto_1fr_auto] border-b-2 border-line">
        <Link to="/me" className="flex items-center border-r-2 border-line px-4 font-mono text-[11px] uppercase tracking-[0.14em] hover:bg-ink hover:text-bg sm:px-6">← Exit</Link>
        <div className="b-mono flex items-center px-4 text-ink-2 sm:px-6">
          {all.length ? `Question ${index + 1} of ${all.length} · ${minutes}` : 'Today’s check-in'}
        </div>
        <div className="b-mono flex items-center border-l-2 border-line px-4 max-sm:hidden sm:px-6">Saved to your account</div>
      </div>
      <div className="h-3 border-b-2 border-line bg-surface">
        <motion.div className="hazard h-full" animate={{ width: `${all.length ? (index / all.length) * 100 : 0}%` }} />
      </div>

      <div className="grid flex-1 md:grid-cols-[1.5fr_1fr]">
        <div className="order-2 border-line px-4 py-10 sm:px-10 md:order-1 md:border-r-2 md:py-14">
          {instrument.error && <ErrorNote message={instrument.error} onRetry={instrument.reload} />}
          {!instrument.data && !instrument.error && <Spinner />}
          {error && <div className="mb-6"><Notice tone="error">{error}</Notice></div>}
          <AnimatePresence mode="wait">
            {q && (
              <motion.div key={q.id} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.18 }}>
                <div className="b-mono text-ink-3">
                  {q.weekly ? `Weekly check · how you’ve felt lately${index === daily.length ? ' · 6 more taps' : ''}` : 'Today'}
                </div>
                <h1 className="b-display mt-3 max-w-3xl text-[clamp(2.4rem,5vw,4.4rem)] leading-[0.92]">{q.text}</h1>
                <div className="mt-8 grid max-w-2xl">
                  {q.options.map((o, i) => {
                    const selected = answers[q.id] === o.value
                    return (
                      <button
                        key={o.label}
                        onClick={() => choose(o.value)}
                        disabled={submitting}
                        className={`-mt-[2px] flex items-center gap-4 border-2 border-line px-5 py-4 text-left text-lg font-semibold transition-colors first:mt-0 ${
                          selected ? 'bg-ink text-bg' : 'bg-surface hover:bg-hot hover:text-[#0b0b0b]'
                        }`}
                      >
                        <span className="b-mono w-5 font-normal opacity-60">{i + 1}</span>
                        {o.label}
                      </button>
                    )
                  })}
                </div>
                <div className="mt-8 flex items-center gap-4">
                  {index > 0 && <button onClick={() => setIndex((i) => i - 1)} className="btn">← Back</button>}
                  <span className="b-mono text-ink-3">Tap an answer or press 1–5</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          {submitting && <div className="mt-8"><Spinner label="Weighing your load" /></div>}
        </div>

        <aside className="order-1 flex items-center justify-center gap-6 border-b-2 border-line bg-surface px-4 py-6 md:order-2 md:flex-col md:border-b-0">
          <LoadGauge score={answeredDaily ? live : 0} width={150} />
          <div className="text-center">
            <div className="b-display text-[clamp(3.5rem,8vw,7rem)] leading-[0.8]">{answeredDaily ? Math.round(live) : '—'}</div>
            <div className="b-mono mt-2 text-ink-3">{answeredDaily ? 'live estimate' : 'answer to see it move'}</div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function DoneToday({ nextAt }: { nextAt: string | null }) {
  const next = nextAt ? new Date(nextAt) : null
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  const when = !next || next.toDateString() === tomorrow.toDateString()
    ? 'tomorrow'
    : `on ${next.toLocaleDateString(undefined, { weekday: 'long' })}`
  return (
    <div className="grid min-h-screen place-items-center bg-bg px-4">
      <div className="w-full max-w-xl border-2 border-line bg-surface shadow-hard">
        <div className="hazard h-3" />
        <div className="p-8">
          <div className="b-mono text-ink-3">Today’s check-in</div>
          <h1 className="b-display mt-3 text-6xl leading-[0.9]">Done for<br /><span className="text-hot">today.</span></h1>
          <p className="mt-4 text-ink-2">One reading a day keeps the trend honest. Your next check-in opens {when}.</p>
          <div className="mt-8 flex flex-wrap gap-0">
            <Link to="/me" className="btn btn-hot">See my pulse →</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
