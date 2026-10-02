import { motion, useScroll, useSpring, useTransform, type MotionValue } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import student from '../assets/student.webp'
import studentSm from '../assets/student-sm.webp'
import { ZipPullArt } from './assets'

/**
 * The page unzips down the middle. The two black halves open into a V behind the pull tab and
 * reveal what's inside the load: the person, and every point of their burnout explained.
 */

const FORCES = [
  { label: 'Sleep 5.5h', v: 6.1 },
  { label: 'Workload 5/5', v: 5.0 },
  { label: 'Late nights ×4', v: 4.2 },
  { label: "Can't switch off", v: 3.4 },
  { label: 'Zero days off', v: 2.8 },
  { label: 'Manager support', v: -1.4 },
]
const TEETH = 18 // seam width in px

export function ZipScene() {
  const ref = useRef<HTMLElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 1440, h: 900 })
  const sizeRef = useRef(size)
  sizeRef.current = size

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  const p = useSpring(scrollYProgress, { stiffness: 150, damping: 32, mass: 0.3 })

  useEffect(() => {
    const el = stage.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => {
      setSize({ w: e.contentRect.width, h: e.contentRect.height })
      p.jump(p.get())
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [p])

  // zipY: how far the pull has travelled; gap: how wide the V is at the top; part: halves leaving.
  const zipY = useTransform(p, (v) => Math.min(1, Math.max(0, (v - 0.06) / 0.62)) * sizeRef.current.h * 1.08)
  const gap = useTransform(p, (v) => Math.pow(Math.min(1, Math.max(0, (v - 0.06) / 0.62)), 1.4) * sizeRef.current.w * 0.95)
  const part = useTransform(p, [0.72, 0.92], [0, 1])

  const leftClip = useTransform([zipY, gap], ([z, g]: number[]) => {
    const c = sizeRef.current.w / 2
    return `polygon(0 0, ${c - g / 2}px 0, ${c}px ${z}px, ${c}px 100%, 0 100%)`
  })
  const rightClip = useTransform([zipY, gap], ([z, g]: number[]) => {
    const c = sizeRef.current.w / 2
    return `polygon(${c + g / 2}px 0, 100% 0, 100% 100%, ${c}px 100%, ${c}px ${z}px)`
  })
  const leftX = useTransform(part, (t) => `${-t * 60}vw`)
  const rightX = useTransform(part, (t) => `${t * 60}vw`)
  const edgeLen = useTransform([zipY, gap], ([z, g]: number[]) => Math.hypot(g / 2, z))
  const edgeAngle = useTransform([zipY, gap], ([z, g]: number[]) => (Math.atan2(g / 2, Math.max(z, 1)) * 180) / Math.PI)
  const leftEdgeX = useTransform(gap, (g) => sizeRef.current.w / 2 - g / 2 - TEETH / 2)
  const rightEdgeX = useTransform(gap, (g) => sizeRef.current.w / 2 + g / 2)
  const negAngle = useTransform(edgeAngle, (a) => -a)
  const closedTop = useTransform(zipY, (z) => z)
  const pullOpacity = useTransform(p, [0.66, 0.72], [1, 0])
  const coverOpacity = useTransform(p, [0.9, 0.96], [1, 0])
  const hint = useTransform(p, [0, 0.08], [1, 0])

  return (
    <section ref={ref} id="inside" className="relative h-[420vh]">
      <div ref={stage} className="sticky top-[var(--nav-h)] h-[calc(100svh-var(--nav-h))] overflow-hidden border-b-2 border-ink">
        <Inside p={p} />

        <motion.div style={{ opacity: coverOpacity }} className="pointer-events-none absolute inset-0 z-20">
          <motion.div style={{ clipPath: leftClip, x: leftX }} className="absolute inset-0"><CoverHalf side="left" /></motion.div>
          <motion.div style={{ clipPath: rightClip, x: rightX }} className="absolute inset-0"><CoverHalf side="right" /></motion.div>

          {/* teeth: open edges follow the V; the closed seam runs below the pull */}
          <motion.div className="zip-teeth absolute top-0" style={{ left: leftEdgeX, x: leftX, width: TEETH / 2, height: edgeLen, rotate: negAngle, transformOrigin: 'top right' }} />
          <motion.div className="zip-teeth zip-teeth-r absolute top-0" style={{ left: rightEdgeX, x: rightX, width: TEETH / 2, height: edgeLen, rotate: edgeAngle, transformOrigin: 'top left' }} />
          <motion.div className="zip-seam absolute bottom-0" style={{ top: closedTop, left: size.w / 2 - TEETH / 2, width: TEETH }} />

          <motion.div className="absolute z-10 h-[190px] w-[54px] drop-shadow-[0_8px_14px_rgba(0,0,0,.55)]" style={{ left: size.w / 2 - 27, y: zipY, top: -22, opacity: pullOpacity }}>
            <ZipPullArt />
          </motion.div>
        </motion.div>

        <motion.div style={{ opacity: hint }} className="pointer-events-none absolute bottom-6 left-1/2 z-30 -translate-x-1/2 bg-paper px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-ink">
          ↓ Scroll to unzip
        </motion.div>
      </div>
    </section>
  )
}

function CoverHalf({ side }: { side: 'left' | 'right' }) {
  return (
    <div className="absolute inset-0 bg-ink text-paper">
      <div className="brutal-grid-dark absolute inset-0" />
      <div className="absolute inset-x-0 top-[18%] flex justify-center">
        <div className="b-display text-center text-[clamp(4.5rem,17vw,17rem)] leading-[0.82]">
          WHAT'S<br />INSIDE<br /><span className="text-hot">THE LOAD?</span>
        </div>
      </div>
      <div className={`absolute bottom-6 font-mono text-[11px] uppercase tracking-[0.18em] text-paper/60 ${side === 'left' ? 'left-6' : 'right-6'}`}>
        {side === 'left' ? '§02 — Inside' : 'Every point explained →'}
      </div>
    </div>
  )
}

function Inside({ p }: { p: MotionValue<number> }) {
  const imgScale = useTransform(p, [0.1, 0.9], [1.15, 1])
  const max = Math.max(...FORCES.map((f) => Math.abs(f.v)))
  return (
    <div className="absolute inset-0 grid grid-rows-[38%_62%] bg-hot text-ink md:grid-cols-[1fr_1.1fr] md:grid-rows-1">
      <div className="relative overflow-hidden border-ink md:border-r-2">
        <div className="absolute inset-0 bg-[radial-gradient(70%_60%_at_50%_45%,#ffb27a,transparent_70%)]" />
        <motion.img
          src={student}
          srcSet={`${studentSm} 683w, ${student} 1024w`}
          sizes="(max-width: 768px) 90vw, 45vw"
          alt="A student with their head in their hands, their brain smouldering"
          style={{ scale: imgScale }}
          className="absolute inset-x-0 bottom-0 mx-auto h-[92%] w-auto object-contain"
        />
        <div className="b-mono absolute left-4 top-4 bg-ink px-2 py-1 text-paper">Subject 014 · Week 8 · Score 74</div>
      </div>
      <div className="relative flex flex-col justify-center overflow-hidden border-t-2 border-ink bg-paper p-5 sm:p-10 md:border-t-0">
        <div className="b-mono">§02 — What's inside</div>
        <h2 className="b-display mt-3 text-[clamp(2rem,5.5vw,5.5rem)] leading-[0.88]">Every point,<br />accounted for.</h2>
        <p className="mt-4 max-w-md text-sm max-sm:hidden sm:text-base">Not a vibe. Not a black box. Each factor's exact share of the score, so you know what to change first.</p>
        <div className="mt-6 space-y-2 sm:mt-8">
          {FORCES.map((f) => (
            <div key={f.label} className="grid grid-cols-[8.5rem_1fr_3.5rem] items-center gap-3 border-t-2 border-ink pt-2 sm:grid-cols-[11rem_1fr_4rem]">
              <span className="text-sm font-semibold uppercase">{f.label}</span>
              <div className="h-5 border-2 border-ink">
                <div className={f.v > 0 ? 'h-full bg-hot' : 'hazard-cool h-full'} style={{ width: `${(Math.abs(f.v) / max) * 100}%` }} />
              </div>
              <span className="b-display text-right text-xl">{f.v > 0 ? '+' : '−'}{Math.abs(f.v).toFixed(1)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
