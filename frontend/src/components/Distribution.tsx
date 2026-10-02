import { useState } from 'react'

export interface Segment { key: string; label: string; value: number; color: string; icon?: string; text?: string }

/** Part-to-whole bar: 2px surface gaps between segments, direct labels only where they fit, legend always. */
export function Distribution({ segments, unit = 'people' }: { segments: Segment[]; unit?: string }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  const [hover, setHover] = useState<string | null>(null)
  if (!total) return <div className="text-sm text-ink-3">No data yet.</div>
  const visible = segments.filter((s) => s.value > 0)

  return (
    <div>
      <div className="flex h-10 gap-[2px] overflow-hidden border-2 border-line bg-line" role="img"
        aria-label={segments.map((s) => `${s.label}: ${s.value} ${unit}`).join(', ')}>
        {visible.map((s) => {
          const pct = (s.value / total) * 100
          return (
            <div
              key={s.key}
              tabIndex={0}
              onPointerEnter={() => setHover(s.key)}
              onPointerLeave={() => setHover(null)}
              onFocus={() => setHover(s.key)}
              onBlur={() => setHover(null)}
              title={`${s.label}: ${s.value} ${unit} (${pct.toFixed(0)}%)`}
              className="flex items-center justify-center text-xs font-semibold transition-opacity"
              style={{
                width: `${pct}%`,
                background: s.color,
                color: s.text ?? '#fff',
                textShadow: s.text ? undefined : '0 1px 2px rgb(0 0 0 / .35)',
                opacity: hover && hover !== s.key ? 0.45 : 1,
              }}
            >
              {pct >= 14 ? s.value : ''}
            </div>
          )
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-2">
        {segments.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5">
            {s.icon ? <span aria-hidden style={{ color: s.color }}>{s.icon}</span>
              : <i aria-hidden className="h-2.5 w-2.5" style={{ background: s.color }} />}
            {s.label} <span className="tabular text-ink">{s.value}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
