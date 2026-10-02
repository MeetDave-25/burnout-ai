import { motion, type MotionValue } from 'motion/react'
import { useEffect, useState, type CSSProperties } from 'react'

/**
 * Landing-story imagery. Drop real PNGs into /public/story/ with these names and they replace the
 * built-in stand-ins automatically (see public/story/README.md). No code changes needed.
 */
export const ASSET_FILES = {
  truck: 'truck',
  containerOrange: 'container-orange',
  containerBlack: 'container-black',
  containerConcrete: 'container-concrete',
  containerWhite: 'container-white',
  zipperPull: 'zipper-pull',
} as const

export type AssetName = keyof typeof ASSET_FILES

/**
 * Geometry of the truck art, as fractions, so containers sit on the deck whatever image is used.
 * Re-measure these if the real truck.png is swapped in.
 */
export const ART = {
  truckAspect: 3.194, // width / height (measured from public/story/truck.webp)
  bedLeft: 0.029, // deck starts here (fraction of truck width)
  bedWidth: 0.742, // deck length, up to the exhaust stack (fraction of truck width)
  bedHeight: 0.378, // deck surface height above the ground (fraction of truck height)
  containerAspect: 2.51,
}

const cache = new Map<AssetName, string | null>()

/** URL of a real asset in /public/story (.webp, then .png), or null to use the stand-in. */
export function useAsset(name: AssetName): string | null {
  const [src, setSrc] = useState<string | null>(() => cache.get(name) ?? null)
  useEffect(() => {
    if (cache.has(name)) return setSrc(cache.get(name) ?? null)
    const tryLoad = (exts: string[]) => {
      if (!exts.length) return cache.set(name, null), setSrc(null)
      const url = `/story/${ASSET_FILES[name]}.${exts[0]}`
      const img = new Image()
      img.onload = () => (cache.set(name, url), setSrc(url))
      img.onerror = () => tryLoad(exts.slice(1))
      img.src = url
    }
    tryLoad(['webp', 'png'])
  }, [name])
  return src
}

// ── Stand-in art ───────────────────────────────────────────────────

export function TruckArt({ wheelSpin }: { wheelSpin?: MotionValue<number> }) {
  const src = useAsset('truck')
  if (src) return <img src={src} alt="" className="h-full w-full object-contain object-bottom" draggable={false} />
  const wheel = (cx: number, r: number) => (
    <motion.g key={cx} style={{ rotate: wheelSpin, transformBox: 'fill-box', transformOrigin: 'center' }}>
      <circle cx={cx} cy={176} r={r} fill="#0b0b0b" />
      <circle cx={cx} cy={176} r={r * 0.55} fill="#6d6a64" />
      <rect x={cx - 2} y={176 - r * 0.5} width={4} height={r} fill="#0b0b0b" />
      <circle cx={cx} cy={176} r={r * 0.15} fill="#0b0b0b" />
    </motion.g>
  )
  return (
    <svg viewBox="0 0 640 200" className="h-full w-full" aria-hidden>
      {/* trailer deck + chassis */}
      <rect x="6" y="120" width="420" height="14" fill="#1a1a1a" />
      <rect x="6" y="134" width="420" height="6" fill="#ff4a00" />
      <rect x="30" y="140" width="380" height="10" fill="#0b0b0b" />
      <rect x="380" y="140" width="80" height="12" fill="#0b0b0b" />
      {/* cab */}
      <path d="M452 150 V52 Q452 38 466 38 H560 Q578 38 584 56 L600 96 H632 V150 Z" fill="#0b0b0b" />
      <path d="M470 54 H548 Q560 54 564 66 L574 92 H470 Z" fill="#cfd4d6" />
      <rect x="470" y="100" width="104" height="5" fill="#ff4a00" />
      <rect x="440" y="22" width="8" height="100" fill="#0b0b0b" />
      <rect x="612" y="108" width="20" height="10" fill="#e8e3d8" />
      {wheel(66, 24)}
      {wheel(122, 24)}
      {wheel(492, 26)}
      {wheel(592, 26)}
    </svg>
  )
}

const CONTAINER_FILL = {
  orange: { body: '#ff4a00', rib: '#d63d00', text: '#0b0b0b' },
  black: { body: '#161616', rib: '#000000', text: '#ece9e2' },
  concrete: { body: '#b9b4aa', rib: '#9d988e', text: '#0b0b0b' },
  white: { body: '#ece9e2', rib: '#cfcac0', text: '#0b0b0b' },
} as const
export type ContainerColor = keyof typeof CONTAINER_FILL

export const containerText = (c: ContainerColor) => CONTAINER_FILL[c].text

/** Label styled like paint stencilled onto corrugated steel: it picks up the panel texture. */
export function stencilStyle(c: ContainerColor): CSSProperties {
  const dark = c === 'black'
  return { color: CONTAINER_FILL[c].text, mixBlendMode: dark ? 'screen' : 'multiply', opacity: dark ? 0.86 : 0.9 }
}

export function ContainerArt({ color }: { color: ContainerColor }) {
  const name = (`container${color[0].toUpperCase()}${color.slice(1)}`) as AssetName
  const src = useAsset(name)
  if (src) return <img src={src} alt="" className="h-full w-full object-fill" draggable={false} />
  const f = CONTAINER_FILL[color]
  return (
    <svg viewBox="0 0 600 245" preserveAspectRatio="none" className="h-full w-full" aria-hidden>
      <rect width="600" height="245" fill={f.body} />
      {Array.from({ length: 44 }, (_, i) => (
        <rect key={i} x={14 + i * 12.4} y="16" width="5" height="213" fill={f.rib} opacity="0.55" />
      ))}
      <rect width="600" height="16" fill={f.rib} />
      <rect y="229" width="600" height="16" fill={f.rib} />
      {[0, 576].map((x) => [0, 221].map((y) => <rect key={`${x}-${y}`} x={x} y={y} width="24" height="24" fill="#0b0b0b" />))}
      {[520, 548].map((x) => <rect key={x} x={x} y="24" width="4" height="197" fill="#0b0b0b" opacity="0.7" />)}
    </svg>
  )
}

export function ZipPullArt() {
  const src = useAsset('zipperPull')
  if (src) return <img src={src} alt="" className="h-full w-full object-contain" draggable={false} />
  return (
    <svg viewBox="0 0 60 150" className="h-full w-full drop-shadow-[0_6px_10px_rgba(0,0,0,.5)]" aria-hidden>
      <defs>
        <linearGradient id="zpm" x1="0" x2="1">
          <stop offset="0" stopColor="#8a857c" />
          <stop offset=".45" stopColor="#f2efe8" />
          <stop offset=".6" stopColor="#c9c3b8" />
          <stop offset="1" stopColor="#6e6a63" />
        </linearGradient>
      </defs>
      <path d="M10 0 H50 L46 44 Q30 52 14 44 Z" fill="url(#zpm)" stroke="#0b0b0b" strokeWidth="2" />
      <rect x="24" y="40" width="12" height="14" fill="url(#zpm)" stroke="#0b0b0b" strokeWidth="2" />
      <rect x="14" y="52" width="32" height="94" rx="4" fill="url(#zpm)" stroke="#0b0b0b" strokeWidth="2" />
      <rect x="23" y="110" width="14" height="26" rx="7" fill="#0b0b0b" />
    </svg>
  )
}
