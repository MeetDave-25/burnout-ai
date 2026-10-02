import { motion, useScroll, useTransform } from 'motion/react'
import { useRef } from 'react'

/** "WK03. WE SAW IT." The forecast draws itself as you scroll past. */

const WEEKS = [32, 36, 41, 47, 54, 61, 68, 74]
const W = 640
const H = 320
const PAD = { l: 44, r: 16, t: 16, b: 34 }
const x = (i: number) => PAD.l + (i / (WEEKS.length - 1)) * (W - PAD.l - PAD.r)
const y = (v: number) => PAD.t + (1 - v / 100) * (H - PAD.t - PAD.b)

export function WarningScene() {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.8', 'end 0.6'] })
  const draw = useTransform(scrollYProgress, [0.05, 0.75], [0, 1])
  const flag = useTransform(scrollYProgress, [0.3, 0.38], [0, 1])
  const path = WEEKS.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join('')

  return (
    <section ref={ref} id="warning" className="border-b-2 border-ink bg-ink text-paper">
      <div className="grid md:grid-cols-[1.05fr_1fr]">
        <div className="relative overflow-hidden border-paper/20 p-6 sm:p-10 md:border-r-2">
          <div className="b-mono text-paper/60">§03 — The warning</div>
          <div className="b-display mt-4 text-[clamp(6rem,17vw,17rem)] leading-[0.78] text-hot">WK03</div>
          <div className="b-display mt-4 text-[clamp(2.6rem,6vw,6rem)] leading-[0.88]">We saw it.<br />Five weeks early.</div>
          <p className="mt-6 max-w-md text-paper/75">
            At week 3 the score was only 41. Nothing felt wrong. But the trend was climbing 6 points a week,
            straight at the burnout line. That's when BurnoutAI flags it, with the reasons.
          </p>
        </div>
        <div className="flex flex-col justify-center p-6 sm:p-10">
          <div className="border-2 border-paper bg-[#121212] p-3 sm:p-5">
            <div className="mb-3 flex justify-between font-mono text-[11px] uppercase tracking-[0.16em] text-paper/60">
              <span>Burnout score · 8 weeks</span><span>Subject 014</span>
            </div>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Burnout score rising from 32 in week 1 to 74 in week 8; the early warning fires at week 3 with a score of 41">
              {[0, 25, 50, 75, 100].map((v) => (
                <g key={v}>
                  <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="#2a2a2a" strokeWidth="1" />
                  <text x={PAD.l - 10} y={y(v)} dy="0.32em" textAnchor="end" className="fill-[#8a8a8a] font-mono text-[11px]">{v}</text>
                </g>
              ))}
              <defs>
                <pattern id="hz" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <rect width="7" height="14" fill="#ff4a00" />
                </pattern>
              </defs>
              <rect x={PAD.l} y={y(50) - 4} width={W - PAD.l - PAD.r} height="8" fill="url(#hz)" />
              <text x={W - PAD.r} y={y(50) - 10} textAnchor="end" className="fill-[#ece9e2] font-mono text-[11px] uppercase">Burnout line</text>
              <motion.path d={path} fill="none" stroke="#ece9e2" strokeWidth="5" strokeLinejoin="miter" style={{ pathLength: draw }} />
              {WEEKS.map((_, i) => (
                <text key={i} x={x(i)} y={H - 10} textAnchor="middle" className="fill-[#8a8a8a] font-mono text-[11px]">W{i + 1}</text>
              ))}
              <motion.g style={{ opacity: flag }}>
                <rect x={x(2) - 9} y={y(WEEKS[2]) - 9} width="18" height="18" fill="#ff4a00" stroke="#0b0b0b" strokeWidth="3" />
                <rect x={x(2) - 6} y={y(WEEKS[2]) - 64} width="196" height="34" fill="#ff4a00" />
                <text x={x(2) + 4} y={y(WEEKS[2]) - 42} className="fill-[#0b0b0b] font-mono text-[13px] font-bold uppercase">▲ Early warning · 41</text>
                <line x1={x(2)} x2={x(2)} y1={y(WEEKS[2]) - 30} y2={y(WEEKS[2]) - 9} stroke="#ff4a00" strokeWidth="3" />
              </motion.g>
            </svg>
          </div>
          <div className="mt-4 grid grid-cols-3 border-2 border-paper text-center">
            {[['+6.1', 'pts / week'], ['WK05', 'projected cross'], ['3', 'reasons named']].map(([a, b]) => (
              <div key={b} className="border-r-2 border-paper p-3 last:border-r-0">
                <div className="b-display text-3xl text-hot">{a}</div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-paper/60">{b}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
