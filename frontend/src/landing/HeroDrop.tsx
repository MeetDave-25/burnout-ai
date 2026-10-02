import {
  motion,
  useAnimate,
  useAnimationFrame,
  useMotionValue,
  useMotionValueEvent,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from 'motion/react'
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import student from '../assets/student.webp'
import studentSm from '../assets/student-sm.webp'
import { ContainerArt, stencilStyle } from './assets'

/**
 * The headline is missing a word until the load arrives.
 * "YOU'RE ____ MORE THAN YOU THINK." A real container stencilled CARRYING hangs from a crane,
 * swings, is lowered by your scroll, then drops into the gap and crushes MORE THAN.
 */

const LOWERED = 0.52 // scroll progress when the crane has lowered it to just above the gap
const IMPACT = 0.6 // ...and when it hits
const CRUSH = 0.6 // MORE THAN is squashed to this height on impact

interface Geo { u: number; mobile: boolean; slotTop: number; slotLeft: number; cw: number; ch: number; line3H: number }

export function HeroDrop() {
  const reduce = useReducedMotion()
  const section = useRef<HTMLElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const head = useRef<HTMLDivElement>(null)
  const slot = useRef<HTMLDivElement>(null)
  const line3 = useRef<HTMLSpanElement>(null)
  const [u, setU] = useState(12)
  const [mobile, setMobile] = useState(false)
  const [geo, setGeo] = useState<Geo | null>(null)
  const geoRef = useRef(geo)
  geoRef.current = geo

  const { scrollYProgress } = useScroll({ target: section, offset: ['start start', 'end end'] })
  const p = useSpring(scrollYProgress, { stiffness: 170, damping: 30, mass: 0.3 })

  // Size everything from one unit so the composition holds at every viewport.
  useLayoutEffect(() => {
    const el = stage.current
    if (!el) return
    const measure = () => {
      const w = el.clientWidth
      const h = el.clientHeight
      const m = w < 760
      setMobile(m)
      setU(m ? w / 62 : Math.min(w / 100, (h - 30) / 64))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useLayoutEffect(() => {
    const st = stage.current, s = slot.current, l3 = line3.current, hd = head.current
    if (!st || !s || !l3 || !hd) return
    const measure = () => {
      // offsetTop/Left are unaffected by the shake transform and the crush scale.
      let top = 0, left = 0, el: HTMLElement | null = s
      while (el && el !== st) { top += el.offsetTop; left += el.offsetLeft; el = el.offsetParent as HTMLElement | null }
      setGeo({ u, mobile, slotTop: top, slotLeft: left, cw: s.offsetWidth, ch: s.offsetHeight, line3H: l3.offsetHeight })
      p.jump(p.get())
    }
    measure()
    document.fonts?.ready.then(measure)
    const ro = new ResizeObserver(measure)
    ro.observe(hd)
    return () => ro.disconnect()
  }, [u, mobile, p])

  const F = u * 12 // headline size
  const CW = u * 46 // container width (aspect 2.51 → height)
  const CH = CW / 2.51

  // Crane: lower, then drop.
  const containerY = useTransform(p, (v) => {
    const g = geoRef.current
    if (!g) return -9999
    const start = -g.ch * 0.72
    const hover = g.slotTop - g.u * 2.5
    const land = g.slotTop + g.line3H * (1 - CRUSH)
    if (reduce) return land
    if (v <= LOWERED) {
      const t = v / LOWERED
      return start + (hover - start) * (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2)
    }
    if (v <= IMPACT) {
      const t = (v - LOWERED) / (IMPACT - LOWERED)
      return hover + (land - hover) * t * t
    }
    return land
  })
  const crush = useTransform(p, [IMPACT - 0.012, IMPACT, IMPACT + 0.02, IMPACT + 0.05], [1, CRUSH * 0.88, CRUSH * 1.04, CRUSH])
  const crushReduced = useMotionValue(CRUSH)
  const ghost = useTransform(p, [LOWERED - 0.1, IMPACT], [1, 0])
  const cableOpacity = useTransform(p, [IMPACT + 0.04, IMPACT + 0.12], [1, 0])
  const cableH = useTransform(containerY, (v) => Math.max(0, v + (geoRef.current?.u ?? 12) * 6))
  const hint = useTransform(p, [0, 0.08], [1, 0])
  const after = useTransform(p, [IMPACT, IMPACT + 0.06], [0, 1])
  const before = useTransform(after, (a) => 1 - a)
  const studentFilter = useTransform(p, (v) => {
    const t = Math.min(1, Math.max(0, (v - IMPACT + 0.02) / 0.08))
    return `grayscale(${(1 - t).toFixed(2)}) brightness(${(0.78 + 0.22 * t).toFixed(2)}) contrast(1.05)`
  })

  // Pendulum swing, damped as it's lowered, nudged by the pointer.
  const swing = useMotionValue(0)
  const pointer = useSpring(0, { stiffness: 40, damping: 12 })
  useAnimationFrame((t) => {
    if (reduce) return
    const amp = Math.max(0, 1 - p.get() / LOWERED)
    swing.set(amp * (2.2 * Math.sin(t / 620) + pointer.get() * 3))
  })
  useEffect(() => {
    const onMove = (e: PointerEvent) => pointer.set((e.clientX / window.innerWidth - 0.5) * 2)
    window.addEventListener('pointermove', onMove)
    return () => window.removeEventListener('pointermove', onMove)
  }, [pointer])

  // Impact: shake the stage and kick up dust (once per pass, forward only).
  const [scope, animate] = useAnimate()
  const [impacts, setImpacts] = useState(0)
  const was = useRef(false)
  useMotionValueEvent(p, 'change', (v) => {
    const hit = v >= IMPACT
    if (hit && !was.current && !reduce) {
      animate(scope.current, { x: [0, -10, 9, -6, 4, -2, 0], y: [0, 7, -5, 3, -1, 0] }, { duration: 0.5 })
      setImpacts((n) => n + 1)
    }
    was.current = hit
  })

  const cx = geo ? geo.slotLeft + CW / 2 : 0

  return (
    <section ref={section} className={reduce ? 'relative' : 'relative h-[190vh]'} aria-label="You're carrying more than you think">
      <div ref={stage} className={`${reduce ? 'relative' : 'sticky top-[var(--nav-h)]'} h-[calc(100svh-var(--nav-h))] overflow-hidden border-b-2 border-ink`}>
        <motion.div ref={scope} className="absolute inset-0">
          <div className="brutal-grid pointer-events-none absolute inset-0" />

          {/* Headline with a gap where the load goes */}
          <div ref={head} className="absolute" style={{ left: u * 4, top: mobile ? u * 9 : u * 6 }}>
            <h1 className="b-display" style={{ fontSize: F, lineHeight: 0.8 }}>
              <Line i={0}>You’re</Line>
              <div ref={slot} className="relative" style={{ width: CW, height: CH }}>
                <motion.span
                  aria-hidden
                  style={{ opacity: ghost, fontSize: CH * 0.56, WebkitTextStroke: '2px var(--ink)' }}
                  className="absolute inset-0 flex items-center px-[7%] text-transparent"
                >
                  Carrying
                </motion.span>
                <span className="sr-only">carrying</span>
              </div>
              <motion.span ref={line3} className="block origin-bottom text-hot" style={{ scaleY: reduce ? crushReduced : crush }}>
                <LineInner i={2}>More than</LineInner>
              </motion.span>
              <Line i={3}>You think.</Line>
            </h1>
          </div>

          {/* The load, on the crane */}
          {geo && (
            <motion.div
              className="absolute top-0 z-20"
              style={{ left: geo.slotLeft, width: CW, rotate: swing, transformOrigin: `50% ${-u * 6}px` }}
            >
              <motion.div className="absolute left-1/2 w-[3px] -translate-x-1/2 bg-ink" style={{ top: -u * 6, height: cableH, opacity: cableOpacity }} />
              <motion.div className="absolute left-0" style={{ y: containerY, width: CW, height: CH }}>
                <div className="relative h-full w-full shadow-[0_30px_40px_-24px_rgba(0,0,0,.55)]">
                  <ContainerArt color="orange" />
                  <div className="absolute inset-0" style={stencilStyle('orange')}>
                    <span className="b-display absolute inset-0 flex items-center px-[7%] leading-none" style={{ fontSize: CH * 0.56 }}>Carrying</span>
                    <span className="absolute left-[7%] top-[9%] whitespace-nowrap font-mono uppercase" style={{ fontSize: Math.max(8, CH * 0.07), letterSpacing: '0.12em' }}>BNAU 074228 · 4</span>
                    <span className="absolute bottom-[9%] right-[7%] whitespace-nowrap text-right font-mono uppercase" style={{ fontSize: Math.max(8, CH * 0.07), letterSpacing: '0.12em' }}>Max gross 30,480 kg · wk 01→08</span>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}

          {/* Dust on impact */}
          {geo && impacts > 0 && <Dust key={impacts} x={cx} y={geo.slotTop + geo.line3H * (1 - CRUSH) + CH} w={CW} />}

          {/* The student, sitting on the last line */}
          <motion.img
            src={student}
            srcSet={`${studentSm} 683w, ${student} 1024w`}
            sizes="(max-width: 760px) 70vw, 30vw"
            alt="A student with their head in their hands, their brain smouldering"
            fetchPriority="high"
            style={{
              filter: reduce ? undefined : studentFilter,
              height: mobile ? u * 46 : u * 56,
              ...(mobile ? { left: '50%', x: '-50%' } : { right: u * 3 }),
            }}
            className="absolute bottom-0 z-10 w-auto select-none object-contain"
            draggable={false}
          />

          {/* HUD */}
          <div className="b-mono absolute right-4 top-4 z-30 text-right sm:right-6">
            <div>Crane 07 · Dock 07</div>
            <motion.div style={{ opacity: before }}>Load suspended · 28.6 t</motion.div>
            <motion.div style={{ opacity: after }} className="text-hot">■ Load delivered · score 74</motion.div>
          </div>
          <motion.div style={{ opacity: hint }} className="b-mono absolute bottom-4 left-4 z-30 flex items-center gap-2 bg-paper px-2 py-1 sm:left-6">
            <span className="inline-block h-2 w-2 animate-pulse bg-hot" /> Scroll to lower the load ↓
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}

function LineInner({ i, children }: { i: number; children: ReactNode }) {
  return (
    <span className="block overflow-hidden pb-[0.02em]">
      <motion.span
        className="block"
        initial={{ y: '105%' }}
        animate={{ y: 0 }}
        transition={{ duration: 0.9, delay: 0.1 + i * 0.09, ease: [0.16, 1, 0.3, 1] }}
      >
        {children}
      </motion.span>
    </span>
  )
}

function Line({ i, children }: { i: number; children: ReactNode }) {
  return <LineInner i={i}>{children}</LineInner>
}

function Dust({ x, y, w }: { x: number; y: number; w: number }) {
  return (
    <div className="pointer-events-none absolute z-30" style={{ left: x, top: y }} aria-hidden>
      {Array.from({ length: 22 }, (_, i) => {
        const side = i % 2 ? 1 : -1
        const spread = (w / 2) * (0.7 + (i % 5) * 0.12)
        return (
          <motion.span
            key={i}
            className="absolute block rounded-full bg-[#9d988e]"
            style={{ width: 4 + (i % 4) * 3, height: 4 + (i % 4) * 3 }}
            initial={{ x: side * (w / 2) * 0.9, y: 0, opacity: 0.9, scale: 1 }}
            animate={{ x: side * spread * (1.2 + (i % 3) * 0.25), y: -30 - (i % 6) * 14, opacity: 0, scale: 2.4 }}
            transition={{ duration: 0.9 + (i % 4) * 0.15, ease: 'easeOut' }}
          />
        )
      })}
    </div>
  )
}
