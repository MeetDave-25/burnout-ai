// Score → colour. A semantic heat ramp (cool sage → amber → ember), always shown with a scale legend.

type RGB = [number, number, number]

const STOPS_LIGHT: [number, RGB][] = [
  [0, [214, 232, 222]],
  [35, [236, 220, 190]],
  [50, [243, 182, 120]],
  [65, [234, 128, 72]],
  [80, [205, 76, 33]],
  [100, [150, 38, 14]],
]
const STOPS_DARK: [number, RGB][] = [
  [0, [38, 58, 52]],
  [35, [86, 70, 48]],
  [50, [150, 92, 46]],
  [65, [214, 104, 52]],
  [80, [242, 120, 62]],
  [100, [255, 170, 110]],
]

function lerp(stops: [number, RGB][], score: number): RGB {
  const s = Math.max(0, Math.min(100, score))
  for (let i = 1; i < stops.length; i++) {
    const [b, cb] = stops[i]
    const [a, ca] = stops[i - 1]
    if (s <= b) {
      const t = (s - a) / (b - a)
      return ca.map((c, k) => Math.round(c + (cb[k] - c) * t)) as RGB
    }
  }
  return stops[stops.length - 1][1]
}

export function heatColor(score: number, dark: boolean): string {
  const [r, g, b] = lerp(dark ? STOPS_DARK : STOPS_LIGHT, score)
  return `rgb(${r} ${g} ${b})`
}

/** Ink colour that stays readable on top of heatColor(score). */
export function inkOn(score: number, dark: boolean): string {
  const [r, g, b] = lerp(dark ? STOPS_DARK : STOPS_LIGHT, score)
  const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
  return lum > 0.55 ? '#1c1916' : '#fff8f0'
}

const ORB_CORE: [number, RGB][] = [[0, [230, 247, 238]], [45, [255, 240, 200]], [100, [255, 222, 160]]]
const ORB_MID: [number, RGB][] = [[0, [95, 184, 160]], [30, [150, 196, 150]], [45, [232, 184, 106]], [65, [242, 132, 66]], [100, [224, 69, 26]]]
const ORB_RIM: [number, RGB][] = [[0, [30, 96, 84]], [35, [96, 110, 60]], [50, [160, 102, 42]], [100, [130, 26, 8]]]

/** Orb palette: core highlight, mid, and rim for a given score (0..100), routed cool → amber → ember. */
export function orbColors(score: number): { core: string; mid: string; rim: string } {
  const c = (stops: [number, RGB][]) => `rgb(${lerp(stops, score).join(' ')})`
  return { core: c(ORB_CORE), mid: c(ORB_MID), rim: c(ORB_RIM) }
}

export const LEVELS = [
  { level: 0, label: 'Low', min: 0, token: 'var(--good)', icon: '●' },
  { level: 1, label: 'Moderate', min: 50, token: 'var(--warning)', icon: '▲' },
  { level: 2, label: 'High', min: 75, token: 'var(--critical)', icon: '◆' },
] as const
