import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PageHead } from '../components/ui'
import { SITE } from '../lib/site'

function Contact() {
  return SITE.contactEmail
    ? <a href={`mailto:${SITE.contactEmail}`} className="border-b-2 border-line font-semibold">{SITE.contactEmail}</a>
    : <span className="font-semibold">the support address on our website</span>
}

function Doc({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) {
  return (
    <div className="mx-auto max-w-4xl px-4 pb-20 sm:px-6">
      <PageHead eyebrow={eyebrow} title={title}>Last updated {SITE.updated}.</PageHead>
      <article className="legal mt-8 space-y-8 text-[15px] leading-relaxed">{children}</article>
    </div>
  )
}

function H({ n, children }: { n: string; children: ReactNode }) {
  return <h2 className="b-display flex gap-4 border-t-2 border-line pt-6 text-3xl"><span className="text-heat">{n}</span>{children}</h2>
}

export function Privacy() {
  return (
    <Doc eyebrow="Legal" title="Privacy policy">
      <section className="border-2 border-line bg-hot p-5 text-[#0b0b0b]">
        <b>The short version.</b> Your check-ins are yours. If you join an organisation, it sees team averages only,
        never your answers, and only for groups of 5 or more. You can download or delete everything at any time.
      </section>

      <section><H n="01">Who we are</H>
        <p className="mt-3">{SITE.company} (“we”) runs BurnoutAI and is responsible for your personal data. Contact us at <Contact />.</p>
      </section>

      <section><H n="02">What we collect</H>
        <ul className="mt-3 list-none space-y-2">
          <li>■ <b>Account:</b> name, email, password (stored only as a salted scrypt hash), timezone.</li>
          <li>■ <b>Check-ins:</b> your answers (sleep, hours, late evenings, workload, ability to switch off, support), the weekly burnout questions, and the scores we calculate from them.</li>
          <li>■ <b>Organisation details</b>, if you join one: which organisation, your role, your team or class, and when you started sharing.</li>
          <li>■ <b>Security records:</b> sign-in attempts and one-time codes (stored hashed) to protect your account.</li>
        </ul>
        <p className="mt-3">We don’t use advertising trackers and we don’t sell data.</p>
      </section>

      <section><H n="03">Why we use it</H>
        <p className="mt-3">To give you your burnout reading, explanation, trend and early warnings; to send the emails you need (codes, invitations, reminders you can turn off); to keep accounts secure; and, in de-identified form, to improve the accuracy of our model. Check-in data is sensitive information about your wellbeing; we process it on the basis of your consent, which you can withdraw at any time.</p>
      </section>

      <section><H n="04">What organisations can see</H>
        <ul className="mt-3 list-none space-y-2">
          <li>■ Only team- or class-level averages, trends and the main factors behind them.</li>
          <li>■ Only for groups where at least 5 people have answered. Smaller groups are locked.</li>
          <li>■ Only check-ins made after you joined and while you’re sharing. Stopping or leaving takes effect immediately.</li>
          <li>■ Never your individual score, answers, forecast or history. Using BurnoutAI for performance evaluation is prohibited by our Terms.</li>
        </ul>
      </section>

      <section><H n="05">Who processes it for us</H>
        <p className="mt-3">Our hosting and database provider, and our email delivery provider (to send codes, invitations and reminders). They act only on our instructions under data-processing agreements.</p>
      </section>

      <section><H n="06">How long we keep it</H>
        <p className="mt-3">Until you delete your account. Deleting your account permanently erases your account and every check-in. Security records are kept for up to 2 days; one-time codes expire after 10 minutes.</p>
      </section>

      <section><H n="07">Your rights</H>
        <p className="mt-3">You can access and download your data, correct it, stop sharing with an organisation, withdraw consent, and delete your account, all from <Link to="/account" className="border-b-2 border-line font-semibold">Account &amp; privacy</Link>. You may also contact us at <Contact /> or complain to your data-protection authority.</p>
      </section>

      <section><H n="08">Security</H>
        <p className="mt-3">Passwords are hashed with scrypt; sessions use secure, http-only cookies; sign-ins and codes are rate-limited; data is encrypted in transit (HTTPS).</p>
      </section>

      <section><H n="09">Not medical advice</H>
        <p className="mt-3">BurnoutAI is a risk signal, not a diagnosis. If you are struggling, please speak to a doctor, counsellor or someone you trust. In an emergency, contact your local emergency services.</p>
      </section>

      <section><H n="10">Age and changes</H>
        <p className="mt-3">BurnoutAI is for people aged 16 and over. If we change this policy materially, we’ll tell you by email or in the app before the change applies.</p>
      </section>
    </Doc>
  )
}

export function Terms() {
  return (
    <Doc eyebrow="Legal" title="Terms of service">
      <section><H n="01">The service</H>
        <p className="mt-3">BurnoutAI provides daily check-ins, burnout readings, explanations and trends for individuals, and aggregate team insights for organisations. These terms are an agreement between you and {SITE.company}.</p>
      </section>
      <section><H n="02">Not a medical service</H>
        <p className="mt-3">Readings are statistical risk signals based on a validated questionnaire and a predictive model with known error (shown on every reading). They are not a diagnosis or treatment. Seek professional help if you are struggling.</p>
      </section>
      <section><H n="03">Your account</H>
        <p className="mt-3">Keep your password safe and your email address current. You must be 16 or older. You’re responsible for activity on your account; tell us at <Contact /> if you think it has been compromised.</p>
      </section>
      <section><H n="04">Organisations</H>
        <ul className="mt-3 list-none space-y-2">
          <li>■ Organisations must invite people only with their knowledge, and must never pressure anyone to join or to share.</li>
          <li>■ <b>Insights must never be used</b> for hiring, firing, promotion, pay, discipline, grading or any performance evaluation, or to try to identify an individual.</li>
          <li>■ Admins are responsible for who they invite and grant admin access to.</li>
        </ul>
      </section>
      <section><H n="05">Acceptable use</H>
        <p className="mt-3">Don’t misuse the service: no attempts to access others’ data, to bypass privacy thresholds or rate limits, to reverse-engineer the service, or to send unsolicited invitations.</p>
      </section>
      <section><H n="06">Plans and fees</H>
        <p className="mt-3">Personal use is free. Paid organisation plans are billed as described on the <Link to="/pricing" className="border-b-2 border-line font-semibold">pricing page</Link> or in your order form.</p>
      </section>
      <section><H n="07">Ending the service</H>
        <p className="mt-3">You can delete your account at any time from Account &amp; privacy. We may suspend accounts that breach these terms.</p>
      </section>
      <section><H n="08">Liability</H>
        <p className="mt-3">The service is provided “as is”. To the extent the law allows, we aren’t liable for decisions made on the basis of readings or insights. Nothing in these terms limits liability that cannot be limited by law.</p>
      </section>
      <section><H n="09">Law</H>
        <p className="mt-3">These terms are governed by the laws of {SITE.jurisdiction}. Questions: <Contact />.</p>
      </section>
    </Doc>
  )
}

export function NotFound() {
  return (
    <div className="mx-auto grid min-h-[calc(100svh-var(--nav-h))] max-w-5xl content-center px-4 py-16 sm:px-6">
      <div className="b-mono text-ink-3">Error 404</div>
      <h1 className="b-display mt-3 text-[clamp(5rem,18vw,14rem)] leading-[0.8]">Nothing<br /><span className="text-hot">here.</span></h1>
      <p className="mt-6 max-w-md text-ink-2">This page doesn’t exist, or it moved. No load to carry here.</p>
      <div className="mt-8 flex flex-wrap gap-3"><Link to="/" className="btn btn-hot">Go home →</Link><Link to="/me" className="btn">My pulse</Link></div>
    </div>
  )
}
