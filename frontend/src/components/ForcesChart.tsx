import { motion } from 'motion/react'
import { useState } from 'react'
import type { Contribution } from '../lib/api'
import { TableToggle } from './ui'

const fmtValue = (c: Contribution) => (typeof c.value === 'number' ? `${+c.value.toFixed(1)}${c.unit}` : c.value)
const signed = (n: number) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n).toFixed(1)}`

/**
 * Diverging "tug of war": each factor pushes the score up (warm, right) or pulls it down (cool, left)
 * from the average person's score. Bars grow from a single centre baseline.
 */
export function ForcesChart({
  contributions,
  base,
  estimate,
  limit = 8,
}: {
  contributions: Contribution[]
  base: number
  estimate: number
  limit?: number
}) {
  const [showAll, setShowAll] = useState(false)
  const [hover, setHover] = useState<string | null>(null)
  const shown = showAll ? contributions : contributions.slice(0, limit)
  const rest = contributions.slice(limit)
  const restNet = rest.reduce((s, c) => s + c.impact, 0)
  const max = Math.max(4, ...contributions.map((c) => Math.abs(c.impact)))

  const chart = (
    <div role="list" className="space-y-1.5">
      {shown.map((c, i) => {
        const pct = (Math.abs(c.impact) / max) * 50
        const up = c.impact > 0
        const active = hover === c.feature
        return (
          <div
            key={c.feature}
            role="listitem"
            tabIndex={0}
            aria-label={`${c.label} ${fmtValue(c)}: ${signed(c.impact)} points`}
            onPointerEnter={() => setHover(c.feature)}
            onPointerLeave={() => setHover(null)}
            onFocus={() => setHover(c.feature)}
            onBlur={() => setHover(null)}
            className="group grid grid-cols-[minmax(0,10.5rem)_1fr] items-center gap-3 px-2 py-1.5 outline-none transition-colors hover:bg-surface-2 focus-visible:bg-surface-2 sm:grid-cols-[minmax(0,13rem)_1fr]"
          >
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-ink">{c.label}</div>
              <div className="font-mono text-[11px] text-ink-3">{fmtValue(c)}</div>
            </div>
            <div className="relative h-7">
              <div className="absolute inset-y-0 left-1/2 w-px bg-line" />
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${pct}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: i * 0.04, ease: [0.2, 0.8, 0.2, 1] }}
                className="absolute top-1/2 h-3.5 -translate-y-1/2"
                style={{
                  [up ? 'left' : 'right']: '50%',
                  background: up ? 'var(--heat)' : 'var(--cool)',
                  borderRadius: 0,
                  opacity: hover && !active ? 0.35 : 1,
                }}
              />
              <span
                className="tabular absolute top-1/2 -translate-y-1/2 whitespace-nowrap font-mono text-xs text-ink-2"
                style={up ? { left: `calc(50% + ${pct}% + 8px)` } : { right: `calc(50% + ${pct}% + 8px)` }}
              >
                {signed(c.impact)}
              </span>
            </div>
          </div>
        )
      })}
      {rest.length > 0 && (
        <button
          onClick={() => setShowAll((v) => !v)}
          className="b-mono ml-2 mt-2 border-b-2 border-line text-ink-3 hover:text-ink"
        >
          {showAll ? 'Show fewer' : `+ ${rest.length} smaller factors (net ${signed(restNet)})`}
        </button>
      )}
    </div>
  )

  const table = (
    <table className="w-full text-sm">
      <thead className="text-left text-ink-3">
        <tr><th className="py-1 font-normal">Factor</th><th className="font-normal">Your value</th><th className="text-right font-normal">Points</th></tr>
      </thead>
      <tbody className="tabular">
        {contributions.map((c) => (
          <tr key={c.feature} className="border-t border-line">
            <td className="py-1.5">{c.label}</td><td>{fmtValue(c)}</td><td className="text-right">{signed(c.impact)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-4 text-xs text-ink-2">
          <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5" style={{ background: 'var(--cool)' }} />Protecting you</span>
          <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5" style={{ background: 'var(--heat)' }} />Pushing burnout up</span>
        </div>
        <div className="font-mono text-xs text-ink-3">
          average person <span className="text-ink">{base.toFixed(0)}</span> → your patterns <span className="text-ink">{estimate.toFixed(0)}</span>
        </div>
      </div>
      <TableToggle chart={chart} table={table} />
    </div>
  )
}
