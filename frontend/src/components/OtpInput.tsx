import { useRef, type ClipboardEvent, type KeyboardEvent } from 'react'

/** Six boxes for a 6-digit code: auto-advance, backspace to go back, paste the whole code, OS one-time-code autofill. */
export function OtpInput({ value, onChange, onComplete, disabled }: {
  value: string
  onChange: (v: string) => void
  onComplete?: (v: string) => void
  disabled?: boolean
}) {
  const refs = useRef<(HTMLInputElement | null)[]>([])
  const digits = Array.from({ length: 6 }, (_, i) => value[i] ?? '')

  const set = (next: string) => {
    const clean = next.replace(/\D/g, '').slice(0, 6)
    onChange(clean)
    if (clean.length === 6) onComplete?.(clean)
    refs.current[Math.min(clean.length, 5)]?.focus()
  }

  const onKey = (i: number) => (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) {
      e.preventDefault()
      set(value.slice(0, i - 1))
    } else if (e.key === 'ArrowLeft' && i > 0) refs.current[i - 1]?.focus()
    else if (e.key === 'ArrowRight' && i < 5) refs.current[i + 1]?.focus()
  }

  const onPaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault()
    set(e.clipboardData.getData('text'))
  }

  return (
    <div className="grid grid-cols-6" role="group" aria-label="6-digit code">
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el }}
          value={d}
          disabled={disabled}
          inputMode="numeric"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          aria-label={`Digit ${i + 1}`}
          maxLength={6}
          onPaste={onPaste}
          onKeyDown={onKey(i)}
          onChange={(e) => {
            const typed = e.target.value.replace(/\D/g, '')
            if (!typed) return set(value.slice(0, i) + value.slice(i + 1))
            set((value.slice(0, i) + typed).slice(0, 6))
          }}
          onFocus={(e) => e.target.select()}
          className={`b-display -ml-[2px] h-20 w-full border-2 border-line bg-surface text-center text-5xl outline-none first:ml-0 focus:z-10 focus:bg-hot focus:text-[#0b0b0b] sm:h-24 sm:text-6xl ${d ? 'bg-ink text-bg' : ''}`}
        />
      ))}
    </div>
  )
}
