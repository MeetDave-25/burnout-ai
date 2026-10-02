import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState, type ReactNode } from 'react'
import { api, type AssessmentRecord, type DailyKey, type Drivers, type Forecast, type Prediction, type WhatIf } from '../lib/api'
import { useAsync, useDebounced } from '../lib/hooks'
import { ForcesChart } from './ForcesChart'
import { LoadGauge } from './LoadGauge'
import { TimeChart } from './TimeChart'
import { LevelBadge } from './ui'

/**
 * One reading, kept short: the score, the 3 things adding weight, 3 things to do, and the trend.
 * Everything else (full breakdown, what-if lab) is one click away, closed by default.
 */

const HEADLINES = ['Light load.', 'Heavy load.', 'Overloaded.']

export function Reading({ prediction: p, drivers, forecast, history, top }: {
  prediction: Prediction
  drivers: Drivers
  forecast?: Forecast | null
  history?: AssessmentRecord[] | null
  top?: ReactNode
}) {
  const e = p.explanation
  const headline = forecast?.early_warning ? 'Heating up. Fast.' : forecast?.status === 'rising' && p.level > 0 ? 'Heavy, and rising.' : HEADLINES[p.level]
  const weight = e.contributions.filter((c) => c.impact >= 0.5 && c.value !== 'typical').slice(0, 3)
  const actions = [
    ...p.levers.map((l) => ({ text: `${l.label}: ${l.change}`, pts: l.expected_change })),
    ...p.recommendations.filter((r) => !/^Your pattern/.test(r)).map((r) => ({ text: r, pts: null as number | null })),
  ].slice(0, 3)

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 pb-20 sm:px-6">
      {top}

      {/* 1 · Score */}
      <section className="grid items-end gap-8 border-2 border-line bg-surface p-6 sm:p-8 md:grid-cols-[auto_1fr]">
        <div className="mx-auto"><LoadGauge score={p.score} width={200} /></div>
        <div>
          <div className="b-mono text-ink-3">
            {p.score_source === 'measured' ? 'Measured this week · burnout inventory' : `Today’s estimate · likely ${e.interval[0]}–${e.interval[1]}`}
          </div>
          <h1 className="b-display mt-2 text-[clamp(2.8rem,6vw,5rem)] leading-[0.88]">{headline}</h1>
          <div className="mt-4 flex flex-wrap items-end gap-x-5 gap-y-2">
            <span className="b-display text-[clamp(5rem,12vw,9rem)] leading-[0.78]" style={{ color: p.level >= 1 ? 'var(--heat)' : undefined }}>{Math.round(p.score)}</span>
            <span className="pb-2"><LevelBadge level={p.level} label={`${p.label} · out of 100`} /></span>
          </div>
          {forecast && forecast.status !== 'insufficient_data' && <p className="mt-4 max-w-xl text-ink-2">{forecast.summary}</p>}
        </div>
      </section>

      {/* 2 · Why */}
      <section>
        <h2 className="b-display text-4xl">What’s adding weight</h2>
        <div className="mt-4 grid sm:grid-cols-3">
          {weight.length === 0 && <p className="text-ink-2">Nothing stands out. Your answers are close to typical.</p>}
          {weight.map((c, i) => (
            <div key={c.feature} className={`border-2 border-line bg-surface p-5 ${i ? 'max-sm:-mt-[2px] sm:-ml-[2px]' : ''}`}>
              <div className="b-display text-5xl leading-none text-heat">+{c.impact.toFixed(0)}</div>
              <div className="mt-3 font-bold uppercase">{c.label}</div>
              <div className="b-mono mt-1 text-ink-3">You said {typeof c.value === 'number' ? `${+c.value.toFixed(1)}${c.unit}` : c.value}</div>
            </div>
          ))}
        </div>
        <Expand label="See every factor">
          <div className="mt-4 border-2 border-line bg-surface p-5 sm:p-7">
            <p className="mb-6 max-w-3xl text-sm text-ink-2">{e.summary}</p>
            <ForcesChart contributions={e.contributions} base={e.base_score} estimate={e.estimated_score} />
          </div>
        </Expand>
      </section>

      {/* 3 · Do this */}
      <section>
        <h2 className="b-display text-4xl">Do this</h2>
        <ol className="mt-4 border-2 border-line bg-ink text-bg">
          {actions.map((a, i) => (
            <li key={i} className={`flex items-start gap-5 p-5 ${i ? 'border-t-2 border-bg/20' : ''}`}>
              <span className="b-display text-4xl leading-none text-hot">{i + 1}</span>
              <span className="flex-1 pt-1">{a.text}</span>
              {a.pts != null && <span className="b-mono shrink-0 bg-cool px-2 py-1 text-white">{a.pts.toFixed(1)} pts</span>}
            </li>
          ))}
        </ol>
        <Expand label="Try a change: what-if lab">
          <CoolDownLab drivers={drivers} prediction={p} />
        </Expand>
      </section>

      {/* 4 · Trend */}
      {history && history.length >= 2 && (
        <section>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="b-display text-4xl">Your trend</h2>
            {forecast?.early_warning && <span className="b-mono border-2 border-line bg-hot px-3 py-1.5 text-[#0b0b0b]">▲ Early warning</span>}
          </div>
          <div className="mt-4 border-2 border-line bg-surface p-5 sm:p-7">
            <TimeChart
              points={history.map((h) => ({ date: new Date(h.created_at), value: h.score, measured: h.score_source === 'measured' }))}
              projection={projection(forecast, history)}
              label="Your burnout score over time"
              showSourceLegend
            />
          </div>
        </section>
      )}

      <p className="b-mono mx-auto max-w-3xl text-center leading-relaxed text-ink-3">
        A risk signal, not a diagnosis · model {p.model.version}, ±{p.model.mae} pts · if you’re struggling, talk to someone today.
      </p>
    </div>
  )
}

function projection(f: Forecast | null | undefined, history: AssessmentRecord[]) {
  if (!f || f.projected == null || !f.projected_interval || f.current == null) return null
  const last = new Date(history[history.length - 1].created_at)
  return {
    from: { date: last, value: f.current },
    to: { date: new Date(last.getTime() + f.horizon_weeks * 6048e5), value: f.projected, lo: f.projected_interval[0], hi: f.projected_interval[1] },
    rising: f.status === 'rising',
  }
}

function Expand({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-3">
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="b-mono border-b-2 border-line pb-0.5 hover:text-heat">
        {open ? '− Hide' : '+'} {label}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/** Drag the six daily answers; the model re-estimates instantly. */
function CoolDownLab({ drivers, prediction }: { drivers: Drivers; prediction: Prediction }) {
  const instrument = useAsync(() => api.instrument(), [])
  const [changes, setChanges] = useState<Partial<Record<DailyKey, number>>>({})
  const debounced = useDebounced(changes, 200)
  const [result, setResult] = useState<WhatIf | null>(null)

  useEffect(() => {
    if (!Object.keys(debounced).length) {
      setResult(null)
      return
    }
    let alive = true
    api.whatIf(drivers, debounced).then((r) => alive && setResult(r)).catch(() => {})
    return () => { alive = false }
  }, [JSON.stringify(debounced)]) // eslint-disable-line react-hooks/exhaustive-deps

  const before = prediction.explanation.estimated_score
  const after = result?.after ?? before
  return (
    <div className="mt-4 grid gap-6 border-2 border-line bg-surface p-5 sm:p-7 lg:grid-cols-[1.5fr_1fr]">
      <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
        {(instrument.data?.sliders ?? []).map((s) => {
          const current = drivers[s.id]
          const v = changes[s.id] ?? current
          return (
            <label key={s.id} className="block">
              <div className="flex items-baseline justify-between text-sm">
                <span className={changes[s.id] != null ? 'font-bold' : ''}>{s.label}</span>
                <span className="b-mono">{v}{s.unit && ` ${s.unit}`}</span>
              </div>
              <input type="range" className="plain-range" min={s.min} max={s.id === 'work_hours_per_day' ? 16 : s.max} step={s.step} value={v}
                onChange={(ev) => setChanges((c) => ({ ...c, [s.id]: Number(ev.target.value) }))} />
            </label>
          )
        })}
      </div>
      <div className="flex flex-col items-center justify-center border-2 border-line bg-surface-2 p-5">
        <div className="flex items-baseline gap-3">
          <span className="b-display text-3xl text-ink-3 line-through">{Math.round(before)}</span>
          <span className="b-display text-7xl leading-none">{Math.round(after)}</span>
        </div>
        <div className="b-mono mt-1 text-ink-3">estimated score</div>
        {result && Math.abs(result.change) >= 0.5 && (
          <div className={`b-mono mt-3 px-2 py-1 ${result.change < 0 ? 'bg-cool text-white' : 'bg-hot text-[#0b0b0b]'}`}>
            {result.change < 0 ? '▼' : '▲'} {Math.abs(result.change).toFixed(1)} points
          </div>
        )}
        {Object.keys(changes).length > 0 && <button onClick={() => setChanges({})} className="btn mt-4">Reset</button>}
      </div>
    </div>
  )
}
