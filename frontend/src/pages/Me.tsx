import { Link, useLocation } from 'react-router-dom'
import { LoadGauge } from '../components/LoadGauge'
import { Reading } from '../components/Reading'
import { ErrorNote, Spinner } from '../components/ui'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAsync } from '../lib/hooks'

/** My pulse: today's status on top, then the latest reading. */
export default function Me() {
  const { me } = useAuth()
  const fresh = (useLocation().state as { fresh?: boolean } | null)?.fresh
  const hasData = (me?.check_ins ?? 0) > 0
  const data = useAsync(
    () => (hasData ? Promise.all([api.myLatest(), api.myForecast(), api.myHistory()]) : Promise.resolve(null)),
    [me?.check_ins],
  )

  const today = me!.today
  const bar = (
    <div className={`flex flex-wrap items-center gap-4 border-2 border-line p-4 sm:p-5 ${today.done ? 'bg-surface' : 'bg-hot text-[#0b0b0b]'}`}>
      <div className="mr-auto">
        <div className="b-mono opacity-70">{new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}</div>
        <div className="b-display mt-1 text-3xl leading-none">
          {fresh ? 'Saved. See you tomorrow.' : today.done ? 'Done for today ✓' : today.weekly_due ? 'Today’s check-in · weekly' : 'Today’s check-in'}
        </div>
      </div>
      {!today.done && (
        <Link to="/check-in" className="btn btn-ink text-sm">
          {today.weekly_due ? 'Start · 2 min →' : 'Start · 1 min →'}
        </Link>
      )}
    </div>
  )

  if (!hasData) {
    return (
      <div className="mx-auto max-w-6xl space-y-8 px-4 pb-20 pt-8 sm:px-6">
        {bar}
        <div className="grid items-end gap-10 border-2 border-line bg-surface p-8 md:grid-cols-[auto_1fr]">
          <LoadGauge score={0} width={180} />
          <div>
            <h1 className="b-display text-[clamp(3rem,7vw,5.5rem)] leading-[0.86]">Hi {me!.user.name.split(' ')[0]}.<br />Your stack is <span className="text-hot">empty.</span></h1>
            <p className="mt-4 max-w-lg text-ink-2">Take one quick check-in a day. After three, you’ll see your trend and get early warnings.</p>
          </div>
        </div>
      </div>
    )
  }
  if (data.error) return <div className="px-4 py-20"><ErrorNote message={data.error} onRetry={data.reload} /></div>
  if (!data.data) return <div className="grid place-items-center py-40"><Spinner label="Loading your pulse" /></div>
  const [latest, forecast, history] = data.data
  return (
    <div className="pt-8">
      <Reading prediction={latest.prediction} drivers={latest.drivers} forecast={forecast} history={history} top={bar} />
    </div>
  )
}
