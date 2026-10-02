import { useReducedMotion } from 'motion/react'
import { Link } from 'react-router-dom'
import { FreightScene, type Box } from '../landing/FreightScene'
import { HeroDrop } from '../landing/HeroDrop'
import { WarningScene } from '../landing/WarningScene'
import { ZipScene } from '../landing/ZipScene'

/** Brutalist scroll story for the homepage. The product itself keeps the calmer Ember style. */

const BOXES: Box[] = [
  { week: 'WK02', label: 'WORKLOAD 5/5', color: 'concrete' },
  { week: 'WK03', label: 'ZERO DAYS OFF', color: 'white' },
  { week: 'WK05', label: 'LATE NIGHTS ×4', color: 'black' },
  { week: 'WK08', label: 'SLEEP 5.5H', color: 'orange' },
]

const TICKER = ['Sleep 5.5h +6.1', 'Workload 5/5 +5.0', 'Late nights +4.2', "Can't switch off +3.4", 'Zero days off +2.8', 'Early warning · week 3', 'Teams under 5 stay hidden']

export default function Landing() {
  const reduce = useReducedMotion()
  return (
    <div className="story-light">
      <HeroDrop />
      <Index />
      <Ticker />
      {reduce ? (
        <StaticStory />
      ) : (
        <>
          <FreightScene
            id="load"
            mode="load"
            section="§01 — The load"
            boxes={BOXES}
            events={4}
            scores={[32, 36, 41, 54, 74]}
            weeks={['WK01', 'WK02', 'WK03', 'WK05', 'WK08']}
            captions={[
              { at: 0, title: 'Week 1. A bit much. Fine.', body: 'One more project lands. Everyone’s busy. You’ll catch up at the weekend.' },
              { at: 1, title: 'The weekend didn’t happen.', body: 'Workload maxes out. The catch-up never comes.' },
              { at: 2, title: 'Week 3. Still “fine”.', body: 'Score 41. Nothing feels wrong. But BurnoutAI flags the trend: crossing the line in about 2 weeks.' },
              { at: 3, title: 'Week 5. Over the line.', body: 'Late nights become normal. Now it’s measurable burnout.' },
              { at: 4, title: 'Week 8. It’s a fire.', body: 'Sleep goes. The stack is about to fall.' },
            ]}
          />
          <ZipScene />
          <WarningScene />
          <FreightScene
            id="unload"
            mode="unload"
            section="§04 — The unload"
            boxes={BOXES}
            events={2}
            heightVh={360}
            scores={[74, 61, 48]}
            weeks={['Now', '+2 weeks', '+4 weeks']}
            captions={[
              { at: 0, title: 'Now unload it.', body: 'BurnoutAI names your biggest levers, and exactly how many points each one takes off.' },
              { at: 1, title: 'Sleep 7.5h. −13.', body: 'First truck: protect sleep. The heaviest container goes.' },
              { at: 2, title: 'No late nights. Below the line.', body: 'Score 48. Same job. Same person. Different load.' },
            ]}
          />
        </>
      )}
      <Privacy />
      <Cta />
    </div>
  )
}

function Index() {
  return (
    <ol className="grid grid-cols-2 border-b-2 border-ink md:grid-cols-4">
      {[['01', 'The load', '#load'], ['02', 'What’s inside', '#inside'], ['03', 'The warning', '#warning'], ['04', 'The unload', '#unload']].map(([n, t, href], i) => (
        <li key={n} className={`border-ink ${i % 2 === 0 ? 'border-r-2' : 'md:border-r-2'} ${i < 2 ? 'max-md:border-b-2' : ''} last:border-r-0`}>
          <a href={href} className="group flex items-baseline justify-between gap-3 px-4 py-4 hover:bg-ink hover:text-paper sm:px-6">
            <span className="font-mono text-xs">§{n}</span>
            <span className="b-display text-2xl sm:text-3xl">{t}</span>
            <span className="font-mono text-xs transition-transform group-hover:translate-y-1">↓</span>
          </a>
        </li>
      ))}
    </ol>
  )
}

function Ticker() {
  const row = [...TICKER, ...TICKER]
  return (
    <div className="overflow-hidden border-b-2 border-ink bg-ink py-3 text-paper" aria-hidden>
      <div className="marquee flex w-max gap-10 whitespace-nowrap">
        {row.map((t, i) => (
          <span key={i} className="b-display flex items-center gap-10 text-2xl sm:text-3xl">
            {t}<span className="inline-block h-3 w-3 bg-hot" />
          </span>
        ))}
      </div>
    </div>
  )
}

function Privacy() {
  return (
    <section className="grid border-b-2 border-ink md:grid-cols-3">
      {[
        ['Measured', 'A validated 13-question burnout inventory. A real score, not a vibe.'],
        ['Explained', 'Every point traced to a cause: sleep, workload, late nights, support.'],
        ['Private', 'Employers and schools see team heat only. Groups under five stay hidden. Always.'],
      ].map(([t, b], i) => (
        <div key={t} className={`p-6 sm:p-10 ${i < 2 ? 'border-b-2 border-ink md:border-b-0 md:border-r-2' : ''} ${i === 2 ? 'bg-hot' : ''}`}>
          <div className="b-mono">0{i + 1}</div>
          <div className="b-display mt-10 text-5xl sm:text-6xl">{t}.</div>
          <p className="mt-3 max-w-sm">{b}</p>
        </div>
      ))}
    </section>
  )
}

function Cta() {
  return (
    <section className="border-b-2 border-ink">
      <Link to="/signup" className="group relative block overflow-hidden px-4 py-14 sm:px-6 sm:py-20">
        <span className="absolute inset-0 origin-bottom scale-y-0 bg-ink transition-transform duration-500 ease-[cubic-bezier(.16,1,.3,1)] group-hover:scale-y-100" />
        <span className="relative block">
          <span className="b-mono transition-colors group-hover:text-paper">1 minute a day · private · free</span>
          <span className="b-display mt-4 flex items-end justify-between gap-6 text-[clamp(3.6rem,12vw,13rem)] leading-[0.8] transition-colors group-hover:text-hot">
            Start free<span className="transition-transform duration-500 group-hover:translate-x-4">→</span>
          </span>
        </span>
      </Link>
      <div className="grid border-t-2 border-ink sm:grid-cols-2">
        <Link to="/pricing" className="border-b-2 border-ink p-6 font-mono text-xs uppercase tracking-[0.16em] hover:bg-ink hover:text-paper sm:border-b-0 sm:border-r-2">For companies & schools → plans & pricing</Link>
        <Link to="/signup" className="p-6 font-mono text-xs uppercase tracking-[0.16em] hover:bg-ink hover:text-paper">Create a free account →</Link>
      </div>
    </section>
  )
}

/** Reduced-motion fallback: the story as still frames. */
function StaticStory() {
  return (
    <section className="grid border-b-2 border-ink md:grid-cols-4">
      {[
        ['§01', 'The load', 'Workload, zero days off, late nights, lost sleep. Week by week the stack grows.'],
        ['§02', 'What’s inside', 'Every point of the score traced to a cause.'],
        ['§03', 'The warning', 'Week 3, score 41: flagged five weeks before the line.'],
        ['§04', 'The unload', 'Sleep back to 7.5h, late nights gone: 74 → 48.'],
      ].map(([n, t, b]) => (
        <div key={n} className="border-b-2 border-ink p-6 md:border-b-0 md:border-r-2">
          <div className="b-mono">{n}</div>
          <div className="b-display mt-6 text-4xl">{t}</div>
          <p className="mt-2 text-sm">{b}</p>
        </div>
      ))}
    </section>
  )
}
