import { motion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { LEVELS } from '../lib/heat'

/** Brutalist primitives shared by every app page. */

export function LevelBadge({ level, label }: { level: number; label?: string }) {
  const l = LEVELS[Math.max(0, Math.min(2, level))]
  return (
    <span className="inline-flex items-center gap-2 border-2 border-line bg-surface px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink">
      <span aria-hidden style={{ color: l.token }}>{l.icon}</span>
      {label ?? l.label}
    </span>
  )
}

export function TableToggle({ chart, table }: { chart: ReactNode; table: ReactNode }) {
  const [asTable, setAsTable] = useState(false)
  return (
    <div>
      {asTable ? table : chart}
      <div className="mt-3 flex justify-end">
        <button onClick={() => setAsTable((v) => !v)} className="b-mono border-b-2 border-line text-ink-3 hover:text-ink">
          {asTable ? 'View as chart' : 'View as table'}
        </button>
      </div>
    </div>
  )
}

export function Section({ eyebrow, title, aside, children, className = '', tone = 'surface' }: {
  eyebrow: string
  title: ReactNode
  aside?: ReactNode
  children: ReactNode
  className?: string
  tone?: 'surface' | 'ink' | 'hot'
}) {
  const toneCls = tone === 'ink' ? 'bg-ink text-bg' : tone === 'hot' ? 'bg-hot text-[#0b0b0b]' : 'bg-surface'
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className={`border-2 border-line ${toneCls} ${className}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b-2 border-line px-5 py-4 sm:px-7">
        <div>
          <div className={`b-mono ${tone === 'surface' ? 'text-ink-3' : 'opacity-70'}`}>{eyebrow}</div>
          <h2 className="b-display mt-1 text-[clamp(1.8rem,3.6vw,3rem)] leading-[0.92]">{title}</h2>
        </div>
        {aside}
      </div>
      <div className="p-5 sm:p-7">{children}</div>
    </motion.section>
  )
}

export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: 'hot' | 'ink' }) {
  const cls = tone === 'hot' ? 'bg-hot text-[#0b0b0b]' : tone === 'ink' ? 'bg-ink text-bg' : 'bg-surface'
  return (
    <div className={`border-2 border-line p-4 ${cls}`}>
      <div className="b-mono opacity-80">{label}</div>
      <div className="b-display mt-2 text-5xl leading-none">{value}</div>
      {hint && <div className="mt-2 text-xs opacity-80">{hint}</div>}
    </div>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="b-mono flex items-center gap-3 text-ink-3" role="status">
      <span className="h-3 w-3 animate-pulse bg-hot" />
      {label}…
    </div>
  )
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="mx-auto max-w-lg border-2 border-line bg-surface p-6">
      <div className="b-display text-2xl">Engine unreachable</div>
      <div className="mt-2 text-sm text-ink-2">{message}. Is the API running on port 8000?</div>
      {onRetry && <button onClick={onRetry} className="btn btn-ink mt-4">Try again</button>}
    </div>
  )
}

export function Notice({ children, tone = 'surface' }: { children: ReactNode; tone?: 'surface' | 'hot' | 'error' }) {
  const cls = tone === 'hot' ? 'bg-hot text-[#0b0b0b]' : tone === 'error' ? 'bg-ink text-bg' : 'bg-surface'
  return <div role={tone === 'error' ? 'alert' : undefined} className={`border-2 border-line px-4 py-3 text-sm ${cls}`}>{children}</div>
}

export function Pill({ children, active, onClick }: { children: ReactNode; active?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`border-2 border-line px-4 py-2 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors ${
        active ? 'bg-ink text-bg' : 'bg-surface text-ink hover:bg-surface-2'
      }`}
    >
      {children}
    </button>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="b-mono mb-2 block text-ink-2">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-xs text-ink-3">{hint}</span>}
    </label>
  )
}

/** Page header block used across the app. */
export function PageHead({ eyebrow, title, children, aside }: { eyebrow: string; title: ReactNode; children?: ReactNode; aside?: ReactNode }) {
  return (
    <header className="grid gap-6 border-b-2 border-line pb-8 pt-10 md:grid-cols-[1fr_auto] md:items-end">
      <div>
        <div className="b-mono text-ink-3">{eyebrow}</div>
        <h1 className="b-display mt-3 text-[clamp(3rem,8vw,7rem)] leading-[0.86]">{title}</h1>
        {children && <div className="mt-4 max-w-2xl text-ink-2">{children}</div>}
      </div>
      {aside}
    </header>
  )
}
