import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'

/**
 * Cinematic opener for the landing page: MEET G. DAVE sharpens letter by letter, "presents",
 * the MD monogram draws itself, then a hazard-edged shutter lifts to reveal the site.
 * Plays once per browser session; skippable; skipped entirely for reduced-motion users.
 */

export const PORTFOLIO = 'https://www.meetdave.tech/'
const KEY = 'bai-intro-seen'
const NAME = 'MEET G. DAVE'
const DURATION = 4200 // ms until the shutter lifts

function alreadySeen(): boolean {
  try {
    return sessionStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

function markSeen() {
  try {
    sessionStorage.setItem(KEY, '1')
  } catch {
    /* storage blocked: the intro simply plays again next time */
  }
}

export function useIntro() {
  const reduce = useReducedMotion()
  const [playing, setPlaying] = useState(() => !alreadySeen())
  useEffect(() => {
    if (reduce) setPlaying(false)
  }, [reduce])
  useEffect(() => {
    if (!playing) return
    document.documentElement.style.overflow = 'hidden'
    const id = setTimeout(() => setPlaying(false), DURATION)
    return () => {
      clearTimeout(id)
      document.documentElement.style.overflow = ''
    }
  }, [playing])
  useEffect(() => {
    if (!playing) markSeen()
  }, [playing])
  return { playing, skip: () => setPlaying(false) }
}

const ease = [0.16, 1, 0.3, 1] as const

export function IntroReveal({ playing, onSkip }: { playing: boolean; onSkip: () => void }) {
  return (
    <AnimatePresence>
      {playing && (
        <motion.div
          key="intro"
          role="dialog"
          aria-label="Intro: Meet G. Dave presents BurnoutAI"
          onClick={onSkip}
          className="fixed inset-0 z-[200] cursor-pointer overflow-hidden bg-[#0b0b0b] text-[#ece9e2]"
          initial={{ y: 0 }}
          exit={{ y: '-100%', transition: { duration: 0.75, ease: [0.76, 0, 0.24, 1] } }}
        >
          <div className="brutal-grid-dark absolute inset-0" />
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-[70vmin] w-[70vmin] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(255,74,0,0.10),transparent_70%)]" />

          {/* Step 1–2: the name, then "presents" */}
          <motion.div
            className="absolute inset-0 flex flex-col items-center justify-center px-4"
            animate={{ opacity: [1, 1, 0], scale: [1, 1, 0.96], filter: ['blur(0px)', 'blur(0px)', 'blur(6px)'] }}
            transition={{ duration: 2.5, times: [0, 0.86, 1], ease: 'easeInOut' }}
          >
            <div className="b-display flex text-[clamp(2.6rem,9vw,7.5rem)] leading-none tracking-[0.18em]" aria-hidden>
              {NAME.split('').map((ch, i) => (
                <motion.span
                  key={i}
                  className="inline-block"
                  style={{ width: ch === ' ' ? '0.35em' : undefined }}
                  initial={{ opacity: 0, scale: 1.18, filter: 'blur(14px)' }}
                  animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
                  transition={{ duration: 0.9, delay: 0.15 + i * 0.075, ease }}
                >
                  {ch === ' ' ? ' ' : ch}
                </motion.span>
              ))}
            </div>
            <motion.div
              className="mt-5 h-[3px] w-[min(70vw,560px)] origin-left bg-[#ff4a00]"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.7, delay: 1.2, ease }}
            />
            <motion.div
              className="b-mono mt-4 text-sm tracking-[0.5em] text-[#ece9e2]"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 1.45 }}
            >
              presents
            </motion.div>
          </motion.div>

          {/* Step 3: the MD monogram draws itself */}
          <motion.div
            className="absolute inset-0 flex flex-col items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 2.35, duration: 0.3 }}
          >
            <svg viewBox="0 0 220 150" className="w-[min(60vw,300px)] overflow-visible drop-shadow-[0_0_18px_rgba(255,74,0,0.25)]" aria-hidden>
              <motion.path d="M 25 110 L 25 30 L 65 70 L 105 30 L 105 110" fill="none" stroke="#ece9e2" strokeWidth="7"
                strokeLinecap="square" strokeLinejoin="miter"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 2.4, duration: 0.6, ease: 'easeInOut' }} />
              <motion.path d="M 135 110 L 135 30 C 185 30, 195 50, 195 70 C 195 90, 185 110, 135 110 Z" fill="none" stroke="#ece9e2"
                strokeWidth="7" strokeLinecap="square" strokeLinejoin="miter"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 2.85, duration: 0.6, ease: 'easeInOut' }} />
              <motion.path d="M 10 138 L 210 138" fill="none" stroke="#ff4a00" strokeWidth="6"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 3.3, duration: 0.45, ease }} />
            </svg>
            <motion.div className="b-display mt-6 text-3xl tracking-[0.08em]"
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 3.45, duration: 0.4 }}>
              Burnout<span className="text-[#ff4a00]">AI</span>
            </motion.div>
          </motion.div>

          <button
            onClick={(e) => { e.stopPropagation(); onSkip() }}
            className="b-mono absolute bottom-6 right-6 border-2 border-[#ece9e2]/40 px-3 py-2 text-[#ece9e2]/80 hover:border-[#ff4a00] hover:text-[#ff4a00]"
          >
            Skip intro →
          </button>

          {/* the shutter's leading edge */}
          <div className="hazard absolute inset-x-0 bottom-0 h-4" />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
