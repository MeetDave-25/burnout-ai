import {
  motion,
  useMotionValueEvent,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { ART, ContainerArt, TruckArt, stencilStyle, type ContainerColor } from './assets'

/**
 * Pinned freight yard. Trucks drive in as you scroll; a crane moves containers between the truck
 * deck and the stack. `load` builds the stack (burnout piling up), `unload` hauls it away (levers).
 */

export interface Box { week: string; label: string; color: ContainerColor }
export interface Caption { at: number; title: string; body: string }

interface Props {
  id: string
  mode: 'load' | 'unload'
  boxes: Box[] // bottom → top
  events: number // how many trucks arrive
  scores: number[] // score before first event, then after each event
  weeks: string[]
  captions: Caption[]
  section: string
  heightVh?: number
}

const T_IN = 0.36
const T_LIFT_END = 0.64
const LINE_LEVEL = 2.4 // burnout line height, in containers
const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)
const easeIn = (t: number) => t * t * t
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
const lerp = (a: number, b: number, t: number) => a + (b - a) * t

function geometry(w: number, h: number, hud = 200) {
  const mobile = w < 760
  const groundFrac = mobile ? 0.84 : 0.88
  // The full stack (4 containers on the dock) must fit between the HUD and the ground.
  const fit = (h * groundFrac - hud - 24) / (ART.bedHeight / ART.truckAspect + 4 * (ART.bedWidth * 0.95) / ART.containerAspect)
  const truckW = Math.min(mobile ? w * 0.96 : w * 0.46, fit, 760)
  const truckH = truckW / ART.truckAspect
  const deckW = truckW * ART.bedWidth
  const cW = deckW * 0.95
  const cH = cW / ART.containerAspect
  const groundY = h * groundFrac
  const baseY = groundY - truckH * ART.bedHeight
  const stackLeft = mobile ? (w - cW) / 2 : w * 0.62 - cW / 2
  const deckOffset = truckW * ART.bedLeft + (deckW - cW) / 2
  return { w, h, mobile, truckW, truckH, cW, cH, groundY, baseY, stackLeft, deckOffset, stopX: stackLeft - deckOffset }
}
type Geo = ReturnType<typeof geometry>

export function FreightScene({ id, mode, boxes, events, scores, weeks, captions, section, heightVh = 520 }: Props) {
  const ref = useRef<HTMLElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const hud = useRef<HTMLDivElement>(null)
  const [geo, setGeo] = useState<Geo>(() => geometry(1440, 900))
  const geoRef = useRef(geo)
  geoRef.current = geo

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
  const p = useSpring(scrollYProgress, { stiffness: 150, damping: 32, mass: 0.3 })

  useEffect(() => {
    const el = stage.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      setGeo(geometry(el.clientWidth, el.clientHeight, hud.current?.offsetHeight ?? 200))
      p.jump(p.get())
    })
    ro.observe(el)
    if (hud.current) ro.observe(hud.current)
    return () => ro.disconnect()
  }, [p])

  // Event windows spread across the scroll, leaving a lead-in and an outro.
  const span = 0.84 / events
  const windows = Array.from({ length: events }, (_, i) => [0.06 + i * span, 0.06 + (i + 1) * span] as const)
  const landAt = windows.map(([a, b]) => a + (b - a) * T_LIFT_END)

  const truckX = (v: number) => {
    const g = geoRef.current
    for (const [a, b] of windows) {
      if (v >= a && v <= b) {
        const t = (v - a) / (b - a)
        if (t < T_IN) return lerp(-g.truckW - 60, g.stopX, easeOut(t / T_IN))
        if (t < T_LIFT_END) return g.stopX
        return lerp(g.stopX, g.w + 60, easeIn((t - T_LIFT_END) / (1 - T_LIFT_END)))
      }
    }
    return -g.truckW - 200
  }

  // Position of container k at progress v.
  const boxPos = (k: number, v: number) => {
    const g = geoRef.current
    const slotY = (level: number) => g.baseY - (level + 1) * g.cH
    const deckY = g.baseY - g.cH
    const event = mode === 'load' ? k : boxes.length - 1 - k
    const level = k
    if (event < 0 || event >= events) return { x: g.stackLeft, y: slotY(level), slotted: true }
    const [a, b] = windows[event]
    const t = clamp01((v - a) / (b - a))
    const onTruck = { x: truckX(v) + g.deckOffset, y: deckY, slotted: false }
    const inSlot = { x: g.stackLeft, y: slotY(level), slotted: true }
    const lift = (from: number, to: number) => {
      const u = easeInOut((t - T_IN) / (T_LIFT_END - T_IN))
      return { x: g.stackLeft, y: lerp(from, to, u) - Math.sin(Math.PI * u) * g.cH * 0.55, slotted: false }
    }
    if (mode === 'load') {
      if (v < a) return { x: -9999, y: deckY, slotted: false }
      if (t < T_IN) return onTruck
      if (t < T_LIFT_END) return lift(deckY, slotY(level))
      return inSlot
    }
    if (v < a || t < T_IN) return inSlot
    if (t < T_LIFT_END) return lift(slotY(level), deckY)
    if (v > b) return { x: -9999, y: deckY, slotted: false }
    return onTruck
  }

  const tx = useTransform(p, truckX)
  const spin = useTransform(tx, (x) => (x / (geo.truckH * 0.13)) * (180 / Math.PI))

  const cable = useTransform(p, (v) => {
    for (let e = 0; e < events; e++) {
      const [a, b] = windows[e]
      const t = (v - a) / (b - a)
      if (t > T_IN - 0.02 && t < T_LIFT_END + 0.02) {
        const k = mode === 'load' ? e : boxes.length - 1 - e
        return Math.max(0, boxPos(k, v).y)
      }
    }
    return 0
  })
  const cableOpacity = useTransform(cable, (c) => (c > 0 ? 1 : 0))

  const score = useTransform(p, [0, ...landAt], scores)
  const scoreText = useTransform(score, (v) => Math.round(v).toString())

  const [done, setDone] = useState(0)
  useMotionValueEvent(p, 'change', (v) => setDone(landAt.filter((l) => v >= l).length))
  const stackCount = mode === 'load' ? done : boxes.length - done
  const crossed = stackCount > LINE_LEVEL
  const strained = mode === 'load' && done === events
  const caption = [...captions].reverse().find((c) => done >= c.at) ?? captions[0]
  const lineY = geo.baseY - LINE_LEVEL * geo.cH
  const roadShift = useTransform(p, (v) => `${-v * 3000}px 0`)

  return (
    <section ref={ref} id={id} className="relative" style={{ height: `${heightVh}vh` }}>
      <div ref={stage} className="sticky top-[var(--nav-h)] h-[calc(100svh-var(--nav-h))] overflow-hidden border-b-2 border-ink bg-paper">
        {/* grid backdrop */}
        <div className="brutal-grid pointer-events-none absolute inset-0" />

        {/* HUD */}
        <div ref={hud} className="absolute inset-x-0 top-0 z-30 grid grid-cols-[1fr_auto] border-b-2 border-ink bg-paper">
          <div className="border-r-2 border-ink p-4 sm:p-6">
            <div className="b-mono">{section}</div>
            <motion.div key={caption.title} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mt-2">
              <div className="b-display text-[clamp(1.6rem,4.2vw,3.6rem)] leading-[0.92]">{caption.title}</div>
              <div className="mt-2 max-w-xl text-sm sm:text-base">{caption.body}</div>
            </motion.div>
          </div>
          <div className="flex min-w-[8.5rem] flex-col justify-between p-4 sm:min-w-[14rem] sm:p-6">
            <div className="b-mono">Burnout score · {weeks[Math.min(done, weeks.length - 1)]}</div>
            <motion.div className="b-display mt-3 text-[clamp(3.5rem,9vw,8rem)] leading-[0.85]" style={{ color: crossed ? 'var(--hot)' : 'var(--ink)' }}>
              {scoreText}
            </motion.div>
          </div>
        </div>

        {/* burnout line */}
        <div className="absolute inset-x-0 z-10" style={{ top: lineY }}>
          <div className={`hazard h-3 ${crossed ? 'hazard-live' : ''}`} />
          <div className="absolute right-3 top-4 bg-ink px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-paper sm:right-6">
            {crossed ? '■ Burnout line crossed' : 'Burnout line · 50'}
          </div>
        </div>

        {/* dock */}
        <div className="absolute z-0 border-2 border-ink bg-concrete" style={{ left: geo.stackLeft - 24, width: geo.cW + 48, top: geo.baseY, height: geo.groundY - geo.baseY }}>
          <div className="hazard h-2" />
          <div className="b-mono p-2">Dock 07</div>
        </div>

        {/* crane cable */}
        <motion.div className="absolute top-0 z-20 w-[3px] bg-ink" style={{ left: geo.stackLeft + geo.cW / 2 - 1.5, height: cable, opacity: cableOpacity }}>
          <div className="absolute -bottom-3 left-1/2 h-4 w-8 -translate-x-1/2 border-2 border-ink bg-hot" />
        </motion.div>

        {/* containers */}
        {boxes.map((b, k) => (
          <ContainerSprite key={b.label} box={b} k={k} geo={geo} p={p} pos={boxPos} strained={strained} />
        ))}

        {/* truck */}
        <motion.div className="absolute z-20" style={{ x: tx, top: geo.groundY - geo.truckH, width: geo.truckW, height: geo.truckH }}>
          <TruckArt wheelSpin={spin} />
        </motion.div>

        {/* road */}
        <div className="absolute inset-x-0 bottom-0 z-10 border-t-[6px] border-ink bg-ink" style={{ top: geo.groundY }}>
          <motion.div className="road-dashes mt-6 h-1.5" style={{ backgroundPosition: roadShift }} />
        </div>
      </div>
    </section>
  )
}

function ContainerSprite({ box, k, geo, p, pos, strained }: {
  box: Box
  k: number
  geo: Geo
  p: MotionValue<number>
  pos: (k: number, v: number) => { x: number; y: number; slotted: boolean }
  strained: boolean
}) {
  const x = useTransform(p, (v) => pos(k, v).x)
  const y = useTransform(p, (v) => pos(k, v).y)
  const z = useTransform(p, (v) => (pos(k, v).slotted ? 15 : 25))
  return (
    <motion.div
      className={`absolute left-0 top-0 ${strained ? 'strain' : ''}`}
      style={{ x, y, zIndex: z, width: geo.cW, height: geo.cH, animationDelay: `${k * 0.07}s` }}
    >
      <ContainerArt color={box.color} />
      <div className="absolute inset-0 flex items-center justify-between gap-2 px-[7%]" style={stencilStyle(box.color)}>
        <span className="b-display leading-[0.9]" style={{ fontSize: geo.cH * 0.4 }}>{box.label}</span>
        <span className="flex flex-col items-end whitespace-nowrap font-mono uppercase tracking-wider" style={{ fontSize: Math.max(8, geo.cH * 0.085) }}>
          <span>{box.week}</span><span>30,480 kg</span>
        </span>
      </div>
    </motion.div>
  )
}
