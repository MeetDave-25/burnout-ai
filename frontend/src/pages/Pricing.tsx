import { Link } from 'react-router-dom'
import { PageHead } from '../components/ui'

/** Plans. Prices are placeholders until billing is wired up. */

const PLANS = [
  {
    name: 'Personal',
    price: 'Free',
    per: 'forever',
    tone: 'bg-surface',
    cta: ['/signup', 'Start free'],
    points: ['Weekly 3-minute check-in', 'Validated burnout score (CBI)', 'Every point explained', '4-week forecast & early warning', 'Cool-down lab: what-if levers'],
  },
  {
    name: 'Team',
    price: '$4',
    per: 'per person / month',
    tone: 'bg-hot text-[#0b0b0b]',
    cta: ['/signup?next=/start', 'Start a team'],
    points: ['Everything in Personal, for everyone', 'Thermal map of every team', 'What changed & what’s driving it', 'Rising & early-warning counts', 'Invite links, admins, consent built in', 'Groups under 5 always hidden'],
    badge: 'Most popular',
  },
  {
    name: 'Campus',
    price: 'Custom',
    per: 'per institution',
    tone: 'bg-ink text-bg',
    cta: ['/signup?next=/start', 'Set up a school'],
    points: ['Student-worded check-ins', 'Class & cohort heat maps', 'Exam-season forecasting', 'Counselling-team admin seats', 'Data-protection agreement'],
  },
]

const FAQ = [
  ['Can my employer or school see my score?', 'No. They see team or class aggregates only, and only when at least 5 people have answered. Your individual score, answers and history are never shown to them.'],
  ['Is this a medical diagnosis?', 'No. BurnoutAI is a risk signal based on the Copenhagen Burnout Inventory and your work patterns. If you’re struggling, please talk to a professional.'],
  ['How accurate is it?', 'The headline score comes from a validated questionnaire. The “why” comes from a model that is still being validated on real-world outcomes; we publish its error (about ±12 points) on every reading.'],
  ['What happens if I leave?', 'Your organisation stops seeing anything from you immediately. Your personal history stays in your account.'],
]

export default function Pricing() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
      <PageHead eyebrow="Pricing" title={<>Cheaper than<br /><span className="text-hot">one resignation.</span></>}>
        Replacing one burnt-out employee costs months of salary. Seeing it five weeks early costs a coffee a month.
      </PageHead>

      <div className="mt-10 grid md:grid-cols-3">
        {PLANS.map((p, i) => (
          <div key={p.name} className={`relative flex flex-col border-2 border-line p-6 ${p.tone} ${i ? 'max-md:-mt-[2px] md:-ml-[2px]' : ''}`}>
            {p.badge && <span className="b-mono absolute -top-[2px] right-6 -translate-y-full border-2 border-b-0 border-line bg-ink px-3 py-1 text-bg">{p.badge}</span>}
            <div className="b-mono opacity-70">{p.name}</div>
            <div className="b-display mt-6 text-7xl leading-none">{p.price}</div>
            <div className="b-mono mt-2 opacity-70">{p.per}</div>
            <ul className="mt-8 flex-1 space-y-2.5 text-sm">
              {p.points.map((pt) => <li key={pt} className="flex gap-2"><span aria-hidden>■</span>{pt}</li>)}
            </ul>
            <Link to={p.cta[0]} className={`btn mt-8 w-full ${p.name === 'Team' ? 'btn-ink' : p.name === 'Campus' ? 'btn-hot' : 'btn-ink'}`}>{p.cta[1]} →</Link>
          </div>
        ))}
      </div>

      <section id="faq" className="mt-16">
        <h2 className="b-display text-5xl">Questions</h2>
        <div className="mt-6 border-t-2 border-line">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group border-b-2 border-line">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-lg font-semibold">
                {q}<span className="b-display text-3xl transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="max-w-3xl pb-5 text-ink-2">{a}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  )
}
