import { useMemo, useState } from 'react'
import { useWidth } from '../lib/hooks'
import { TableToggle } from './ui'

export interface TimePoint { date: Date; value: number | null; measured?: boolean }
export interface Projection { from: { date: Date; value: number }; to: { date: Date; value: number; lo: number; hi: number }; rising: boolean }

const fmtDate = (d: Date) => d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
const M = { l: 34, r: 64, t: 18, b: 30 }

/**
 * Burnout score over time on a fixed 0–100 axis, with the 50-point "burnout line",
 * an optional 4-week projection cone, and a snapping crosshair.
 */
export function TimeChart({
  points,
  projection,
  height = 260,
  label,
  showSourceLegend = false,
}: {
  points: TimePoint[]
  projection?: Projection | null
  height?: number
  label: string
  showSourceLegend?: boolean
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)

  const t0 = points[0]?.date.getTime() ?? 0
  const t1 = (projection?.to.date ?? points[points.length - 1]?.date)?.getTime() ?? 1
  const iw = Math.max(10, width - M.l - M.r)
  const ih = height - M.t - M.b
  const x = (d: Date) => M.l + ((d.getTime() - t0) / Math.max(1, t1 - t0)) * iw
  const y = (v: number) => M.t + (1 - v / 100) * ih

  const segments = useMemo(() => {
    const segs: TimePoint[][] = []
    let cur: TimePoint[] = []
    points.forEach((p) => {
      if (p.value == null) {
        if (cur.length) segs.push(cur)
        cur = []
      } else cur.push(p)
    })
    if (cur.length) segs.push(cur)
    return segs
  }, [points])

  const targets = [
    ...points.filter((p) => p.value != null).map((p) => ({ date: p.date, value: p.value as number, kind: p.measured === false ? 'Estimated' : p.measured ? 'Measured' : '' })),
    ...(projection ? [{ date: projection.to.date, value: projection.to.value, kind: `Projected (${Math.round(projection.to.lo)}–${Math.round(projection.to.hi)})` }] : []),
  ]

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = e.clientX - rect.left
    let best = 0
    targets.forEach((t, i) => {
      if (Math.abs(x(t.date) - px) < Math.abs(x(targets[best].date) - px)) best = i
    })
    setHover(targets.length ? best : null)
  }

  const h = hover != null ? targets[hover] : null
  const last = targets.filter((t) => !t.kind.startsWith('Projected')).at(-1)

  const chart = (
    <div ref={ref} className="relative select-none">
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={label}
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
          className="touch-none overflow-visible"
        >
          {[0, 25, 50, 75, 100].map((v) => (
            <g key={v}>
              <line x1={M.l} x2={M.l + iw} y1={y(v)} y2={y(v)} stroke="var(--grid)" />
              <text x={M.l - 10} y={y(v)} dy="0.32em" textAnchor="end" className="tabular fill-[var(--ink-3)] font-mono text-[10px]">{v}</text>
            </g>
          ))}

          {/* burnout line */}
          <line x1={M.l} x2={M.l + iw} y1={y(50)} y2={y(50)} stroke="var(--heat)" strokeOpacity="0.55" />
          <text x={M.l + 6} y={y(50) - 7} className="fill-[var(--ink-2)] font-mono text-[10px] uppercase tracking-wider">burnout line</text>

          {projection && (
            <g>
              <path
                d={`M${x(projection.from.date)},${y(projection.from.value)} L${x(projection.to.date)},${y(projection.to.hi)} L${x(projection.to.date)},${y(projection.to.lo)} Z`}
                fill={projection.rising ? 'var(--heat-wash)' : 'var(--cool-wash)'}
              />
              <line
                x1={x(projection.from.date)} y1={y(projection.from.value)}
                x2={x(projection.to.date)} y2={y(projection.to.value)}
                stroke={projection.rising ? 'var(--heat)' : 'var(--cool)'} strokeWidth="2" strokeDasharray="5 5" strokeLinecap="round"
              />
              <circle cx={x(projection.to.date)} cy={y(projection.to.value)} r="5" fill={projection.rising ? 'var(--heat)' : 'var(--cool)'} stroke="var(--surface)" strokeWidth="2" />
              <text x={x(projection.to.date) + 10} y={y(projection.to.value)} dy="0.32em" className="fill-[var(--ink)] font-mono text-[11px]">
                ≈{Math.round(projection.to.value)}
              </text>
            </g>
          )}

          {segments.map((seg, i) => (
            <path
              key={i}
              d={seg.map((p, j) => `${j ? 'L' : 'M'}${x(p.date)},${y(p.value as number)}`).join('')}
              fill="none" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"
            />
          ))}
          {points.map((p, i) =>
            p.value == null ? null : (
              <circle
                key={i} cx={x(p.date)} cy={y(p.value)} r="4.5"
                fill={p.measured === false ? 'var(--surface)' : 'var(--ink)'}
                stroke={p.measured === false ? 'var(--ink)' : 'var(--surface)'} strokeWidth="2"
              />
            ),
          )}
          {last && !projection && (
            <text x={x(last.date) + 10} y={y(last.value)} dy="0.32em" className="fill-[var(--ink)] font-mono text-[11px]">{Math.round(last.value)}</text>
          )}

          {[points[0], points[Math.floor(points.length / 2)], points.at(-1)]
            .filter((p, i, a): p is TimePoint => !!p && a.indexOf(p) === i)
            .map((p) => (
              <text key={p.date.getTime()} x={x(p.date)} y={height - 8} textAnchor="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">{fmtDate(p.date)}</text>
            ))}
          {projection && (
            <text x={x(projection.to.date)} y={height - 8} textAnchor="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">+{Math.round((projection.to.date.getTime() - projection.from.date.getTime()) / 6048e5)} wk</text>
          )}

          {h && (
            <g pointerEvents="none">
              <line x1={x(h.date)} x2={x(h.date)} y1={M.t} y2={M.t + ih} stroke="var(--ink-3)" />
              <circle cx={x(h.date)} cy={y(h.value)} r="7" fill="none" stroke="var(--ink)" strokeWidth="1.5" />
            </g>
          )}
        </svg>
      )}
      {h && width > 0 && (
        <div
          className="pointer-events-none absolute top-0 z-10 border-2 border-line bg-surface px-3 py-2 text-xs shadow-hard"
          style={{ left: Math.min(Math.max(0, x(h.date) - 70), width - 150), transform: 'translateY(-4px)' }}
        >
          <div className="text-base font-semibold text-ink">{h.value.toFixed(1)}</div>
          <div className="text-ink-3">{fmtDate(h.date)}{h.kind && ` · ${h.kind}`}</div>
        </div>
      )}
      {showSourceLegend && (
        <div className="mt-2 flex gap-4 text-xs text-ink-2">
          <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 bg-ink" />Measured (questionnaire)</span>
          <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full border-2 border-ink" />Estimated (work patterns)</span>
        </div>
      )}
    </div>
  )

  const table = (
    <table className="w-full text-sm">
      <thead className="text-left text-ink-3"><tr><th className="py-1 font-normal">Date</th><th className="font-normal">Score</th><th className="font-normal">Type</th></tr></thead>
      <tbody className="tabular">
        {targets.map((t, i) => (
          <tr key={i} className="border-t border-line"><td className="py-1.5">{fmtDate(t.date)}</td><td>{t.value.toFixed(1)}</td><td>{t.kind || '—'}</td></tr>
        ))}
      </tbody>
    </table>
  )

  return <TableToggle chart={chart} table={table} />
}

/** Shape-only trend: scaled to its own range (min span 20 points) so small teams' movement stays visible. */
export function Sparkline({ values, width = 120, height = 32, color = 'currentColor' }: { values: (number | null)[]; width?: number; height?: number; color?: string }) {
  const nums = values.filter((v): v is number => v != null)
  const mid = (Math.max(...nums) + Math.min(...nums)) / 2
  const span = Math.max(20, Math.max(...nums) - Math.min(...nums))
  const lo = mid - span / 2
  const pts = values.map((v, i) => (v == null ? null : [(i / Math.max(1, values.length - 1)) * (width - 6) + 3, height - 3 - ((v - lo) / span) * (height - 6)] as const))
  const d = pts.reduce((acc, p, i) => (p ? acc + `${acc && pts[i - 1] ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}` : acc), '')
  const end = [...pts].reverse().find(Boolean)
  return (
    <svg width={width} height={height} aria-hidden className="overflow-visible">
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {end && <circle cx={end[0]} cy={end[1]} r="3.5" fill={color} />}
    </svg>
  )
}
