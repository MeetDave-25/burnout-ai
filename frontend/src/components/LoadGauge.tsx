import { AnimatePresence, motion } from 'motion/react'
import { ContainerArt, type ContainerColor } from '../landing/assets'

/**
 * Burnout as load: one shipping container per 20 points (rounded), stacked on a dock, with the
 * hazard-striped burnout line at 50 (2.5 containers): a score under 50 never crosses it, 50+ always does.
 * Containers drop in / lift off as the score moves.
 */

const SLOTS = 5
const COLORS: ContainerColor[] = ['concrete', 'white', 'black', 'orange', 'orange']

export function LoadGauge({ score, width = 220, label = true }: { score: number; width?: number; label?: boolean }) {
  const ch = width / 2.51
  const filled = Math.max(0, Math.min(SLOTS, Math.round(score / 20)))
  const over = score >= 50
  return (
    <div className="relative select-none" style={{ width, height: SLOTS * ch + 18 }} aria-hidden>
      <AnimatePresence initial={false}>
        {Array.from({ length: filled }, (_, i) => (
          <motion.div
            key={i}
            className="absolute left-0"
            style={{ width, height: ch, bottom: 14 + i * ch }}
            initial={{ y: -ch * 1.4, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -ch * 1.2, opacity: 0, transition: { duration: 0.25 } }}
            transition={{ type: 'spring', stiffness: 420, damping: 24 }}
          >
            <ContainerArt color={COLORS[i]} />
          </motion.div>
        ))}
      </AnimatePresence>
      <div className="absolute inset-x-[-8%] z-10" style={{ bottom: 14 + 2.5 * ch }}>
        <div className={`hazard h-2 ${over ? 'hazard-live' : ''}`} />
        {label && <span className="b-mono absolute -top-[22px] left-0 bg-ink px-1.5 py-0.5 text-[10px] text-bg">Burnout line · 50</span>}
      </div>
      <div className="absolute inset-x-[-6%] bottom-0 h-[14px] border-2 border-line bg-concrete" />
    </div>
  )
}
