import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { isAdmin, useAuth } from '../lib/auth'
import { useTheme } from '../lib/hooks'
import { SITE } from '../lib/site'
import { PORTFOLIO } from './IntroReveal'

/** Site-wide brutalist navigation + footer. */

export function Nav({ theme }: { theme: ReturnType<typeof useTheme> }) {
  const { me, ready, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const menu = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = (e: MouseEvent) => !menu.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const verified = !!me?.user.email_verified
  const links = me && !verified
    ? []
    : me
    ? [
        { to: '/me', label: 'My pulse' },
        ...(!me.today.done ? [{ to: '/check-in', label: 'Check in', hot: true }] : []),
        ...(isAdmin(me) ? [{ to: `/org/${me.membership!.org_id}`, label: 'Team' }] : []),
      ]
    : [{ to: '/pricing', label: 'Pricing' }]

  const cell = 'flex items-center border-l-2 border-line px-3 font-mono text-[11px] uppercase tracking-[0.14em] transition-colors sm:px-5'

  return (
    <header className="sticky top-0 z-50 grid h-[var(--nav-h)] grid-cols-[auto_1fr_auto] border-b-2 border-line bg-bg">
      <Link to={me ? '/me' : '/'} className="flex items-center gap-2 px-4 sm:px-6" aria-label="BurnoutAI home">
        <span className="h-3.5 w-3.5 bg-hot" />
        <span className="b-display text-xl tracking-wide">BurnoutAI</span>
      </Link>
      <div className="b-mono hidden items-center border-l-2 border-line px-6 text-ink-3 lg:flex">Early-warning system for humans</div>
      <nav className="flex">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              `${cell} ${isActive ? 'bg-ink text-bg' : 'hot' in l && l.hot ? 'bg-hot text-[#0b0b0b] hover:bg-ink hover:text-bg' : 'hover:bg-ink hover:text-bg'} `
            }
          >
            {l.label}
          </NavLink>
        ))}
        <button
          onClick={() => theme.setTheme(theme.resolved === 'dark' ? 'light' : 'dark')}
          aria-label={`Switch to ${theme.resolved === 'dark' ? 'light' : 'dark'} mode`}
          className={`${cell} max-sm:hidden hover:bg-ink hover:text-bg`}
        >
          {theme.resolved === 'dark' ? '☀' : '☾'}
        </button>
        {ready && !me && (
          <>
            <NavLink to="/login" className={`${cell} hover:bg-ink hover:text-bg`}>Log in</NavLink>
            <NavLink to="/signup" className={`${cell} bg-hot text-[#0b0b0b] hover:bg-ink hover:text-bg`}>Start free</NavLink>
          </>
        )}
        {me && (
          <div ref={menu} className="relative flex">
            <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className={`${cell} gap-2 hover:bg-ink hover:text-bg`}>
              <span className="grid h-6 w-6 place-items-center bg-ink text-[11px] text-bg">{me.user.name.slice(0, 1).toUpperCase()}</span>
              <span className="max-md:hidden">{me.user.name.split(' ')[0]}</span>
            </button>
            {open && (
              <div className="absolute right-0 top-full z-50 w-64 border-2 border-line bg-surface shadow-hard" onClick={() => setOpen(false)}>
                <div className="border-b-2 border-line px-4 py-3">
                  <div className="text-sm font-semibold">{me.user.name}</div>
                  <div className="truncate text-xs text-ink-3">{me.user.email}</div>
                  {me.membership && <div className="b-mono mt-2 text-ink-2">{me.membership.role} · {me.membership.org_name}</div>}
                </div>
                {(verified ? [
                  ['/account', 'Account & privacy'],
                  ...(isAdmin(me) ? [[`/org/${me.membership!.org_id}/settings`, 'Invite people']] : []),
                  ...(!me.membership ? [['/start', 'Add your team or school']] : []),
                ] : []).map(([to, label]) => (
                  <Link key={to} to={to} className="block border-b-2 border-line px-4 py-3 text-sm hover:bg-ink hover:text-bg">{label}</Link>
                ))}
                <button
                  onClick={async () => { await logout(); navigate('/') }}
                  className="block w-full px-4 py-3 text-left text-sm hover:bg-ink hover:text-bg"
                >
                  Log out
                </button>
              </div>
            )}
          </div>
        )}
      </nav>
    </header>
  )
}

export function Footer() {
  const { me } = useAuth()
  const groups: [string, string[][]][] = me
    ? [
        ['You', [['/me', 'My pulse'], ['/account', 'Account & privacy']]],
        ['Teams', [[me.membership ? '/account' : '/start', me.membership ? 'Your organisation' : 'Add your team or school']]],
        ['Help', [['/pricing#faq', 'FAQ'], ['/privacy', 'Privacy policy'], ['/terms', 'Terms']]],
      ]
    : [
        ['Product', [['/pricing', 'Pricing'], ['/pricing#faq', 'FAQ']]],
        ['Account', [['/signup', 'Create account'], ['/login', 'Log in']]],
        ['Legal', [['/privacy', 'Privacy policy'], ['/terms', 'Terms']]],
      ]
  return (
    <footer className="border-t-2 border-line">
      <div className="grid sm:grid-cols-4">
        {groups.map(([title, items]) => (
          <div key={title} className="border-b-2 border-line p-6 sm:border-b-0 sm:border-r-2">
            <div className="b-mono text-ink-3">{title}</div>
            <ul className="mt-3 space-y-1.5">
              {items.map(([to, label]) => (
                <li key={to}><Link to={to} className="text-sm hover:underline">{label}</Link></li>
              ))}
            </ul>
          </div>
        ))}
        <div className="flex flex-col justify-between bg-hot p-6 text-[#0b0b0b]">
          <div className="b-display text-3xl leading-none">See it coming.</div>
          <div className="b-mono mt-6">Risk assessment, not diagnosis.</div>
        </div>
      </div>
      <div className="grid border-t-2 border-line md:grid-cols-[1fr_auto_1fr]">
        <span className="b-mono flex items-center px-6 py-4 text-ink-3">© {new Date().getFullYear()} {SITE.company}</span>
        <MadeBy className="border-line max-md:border-y-2 md:border-x-2" />
        <span className="b-mono flex items-center px-6 py-4 text-ink-3 md:justify-end">If you’re struggling, talk to someone today.</span>
      </div>
    </footer>
  )
}

/** "Made by Meet G. Dave" credit, linking to the portfolio. Shown on every page. */
export function MadeBy({ className = '', compact = false }: { className?: string; compact?: boolean }) {
  return (
    <a
      href={PORTFOLIO}
      target="_blank"
      rel="noopener"
      className={`group flex items-center justify-center gap-2 px-6 font-mono text-[11px] uppercase tracking-[0.16em] transition-colors hover:bg-hot hover:text-[#0b0b0b] ${compact ? 'py-2' : 'py-4'} ${className}`}
    >
      <span className="text-ink-3 group-hover:text-[#0b0b0b]">Made by</span>
      <span className="b-display text-base normal-case tracking-[0.06em] text-ink group-hover:text-[#0b0b0b]">Meet G. Dave</span>
      <span aria-hidden className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5">↗</span>
      <span className="sr-only">(opens portfolio in a new tab)</span>
    </a>
  )
}
