import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

export const ThemeContext = createContext<'light' | 'dark'>('light')
export const useIsDark = () => useContext(ThemeContext) === 'dark'

/** Fetch on mount / when deps change. Keeps the previous data while refetching (no flash). */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let alive = true
    setLoading(true)
    fn()
      .then((d) => alive && (setData(d), setError(null)))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}

export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return v
}

type Theme = 'light' | 'dark' | 'system'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (localStorage.getItem('theme') as Theme) || 'system'
    } catch {
      return 'system'
    }
  })
  const [resolved, setResolved] = useState<'light' | 'dark'>(() =>
    theme === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme,
  )

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const apply = () => {
      const r = theme === 'system' ? (mq.matches ? 'dark' : 'light') : theme
      const root = document.documentElement
      if (theme === 'system') delete root.dataset.theme
      else root.dataset.theme = theme
      root.dataset.resolvedTheme = r
      setResolved(r)
    }
    apply()
    mq.addEventListener('change', apply)
    try {
      localStorage.setItem('theme', theme)
    } catch {
      /* storage unavailable — theme still applies for this session */
    }
    return () => mq.removeEventListener('change', apply)
  }, [theme])

  return { theme, resolved, setTheme }
}

/** Member id for the personal dashboard (demo stand-in for login). */
export function useMemberId() {
  const read = () => {
    try {
      const v = localStorage.getItem('memberId')
      return v ? Number(v) : null
    } catch {
      return null
    }
  }
  const [id, setId] = useState<number | null>(read)
  const set = useCallback((v: number | null) => {
    try {
      if (v == null) localStorage.removeItem('memberId')
      else localStorage.setItem('memberId', String(v))
    } catch {
      /* ignore */
    }
    setId(v)
  }, [])
  return [id, set] as const
}

/** Element width via ResizeObserver, for responsive SVG charts. */
export function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}
