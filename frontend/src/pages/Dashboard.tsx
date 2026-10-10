import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Dashboard as Data, type DashboardReview, type Status } from '../api'
import { ErrorNote, Loading, ResultBadge, STATUS, Stamp, fmtDate } from '../ui'
import { STATE_LABEL } from './Reviews'

const ACTION_LABEL: Record<string, string> = {
  'auth.login': 'Signed in', 'account.register': 'Created your account', 'account.profile': 'Updated your profile',
  'account.password': 'Changed your password', 'account.sign_out_all': 'Signed out other sessions',
  'review.submit': 'Submitted a review', 'evidence.add': 'Attached evidence', 'review.evaluate': 'Ran an evaluation',
  'review.approve': 'Approved a review', 'review.reject': 'Rejected a review', 'review.return': 'Sent a review back',
  'audit.package': 'Opened an audit package', 'policy.ingest': 'Uploaded a policy', 'evidence.download': 'Downloaded evidence',
  'admin.user_update': 'Updated a user', 'admin.password_reset': 'Reset a user’s password',
}

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

function Tile({ label, value, to, tone }: { label: string; value: number; to?: string; tone?: string }) {
  const body = (
    <>
      <span className={`block text-3xl font-semibold tabular-nums ${tone ?? ''}`}>{value}</span>
      <span className="mt-1 block text-sm text-ink-soft">{label}</span>
    </>
  )
  const cls = 'block rounded-lg bg-paper p-5 ring-1 ring-rule'
  return to ? <Link to={to} className={`${cls} text-ink hover:ring-pen`}>{body}</Link> : <div className={cls}>{body}</div>
}

function ReviewList({ rows, empty }: { rows: DashboardReview[]; empty: string }) {
  if (!rows.length) return <p className="m-0 py-6 text-center text-sm text-ink-soft">{empty}</p>
  return (
    <ul className="m-0 list-none divide-y divide-rule p-0">
      {rows.map((r) => (
        <li key={r.id} className="flex items-center justify-between gap-4 py-3">
          <div className="min-w-0">
            <Link to={`/reviews/${r.id}`} className="block truncate font-semibold text-ink hover:text-pen">{r.title}</Link>
            <span className="text-xs text-ink-soft">#{r.id} by {r.submitted_by}, {STATE_LABEL[r.status] ?? r.status}</span>
          </div>
          <div className="shrink-0 text-right">
            <ResultBadge result={r.result} />
            {r.findings > 0 && <span className="block text-xs text-ink-soft">{r.open} of {r.findings} open</span>}
          </div>
        </li>
      ))}
    </ul>
  )
}

function Panel({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-lg bg-paper p-5 ring-1 ring-rule sm:p-6">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="m-0 text-lg font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export default function Dashboard() {
  const [d, setD] = useState<Data | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => { api.dashboard().then(setD, setError) }, [])
  if (error) return <ErrorNote error={error} />
  if (!d) return <Loading />

  const reviewer = d.me.role !== 'engineer'
  const totalFindings = Object.values(d.finding_statuses).reduce((a, b) => a + b, 0)
  const order: Status[] = ['FAIL', 'NEEDS_HUMAN_REVIEW', 'UNKNOWN', 'PASS']

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="m-0 text-3xl font-semibold tracking-tight">{greeting()}, {d.me.display_name.split(' ')[0]}</h1>
          <p className="mt-1 mb-0 text-ink-soft">
            {reviewer
              ? d.counts.awaiting_decision ? `${d.counts.awaiting_decision} review${d.counts.awaiting_decision > 1 ? 's are' : ' is'} waiting for a decision.` : 'Nothing is waiting for your decision.'
              : d.counts.returned_to_me ? `${d.counts.returned_to_me} review${d.counts.returned_to_me > 1 ? 's were' : ' was'} sent back to you for more evidence.` : 'Here’s where your change requests stand.'}
          </p>
        </div>
        {d.me.role !== 'reviewer' && (
          <Link to="/reviews/new" className="rounded-md bg-pen px-4 py-2 text-sm font-semibold text-white hover:bg-pen-dark">Start a review</Link>
        )}
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {reviewer
          ? <Tile label="Awaiting your decision" value={d.counts.awaiting_decision} to="/reviews" tone={d.counts.awaiting_decision ? 'text-human' : ''} />
          : <Tile label="Sent back to you" value={d.counts.returned_to_me} to="/reviews" tone={d.counts.returned_to_me ? 'text-unknown' : ''} />}
        <Tile label="Your open reviews" value={d.counts.my_open} to="/reviews" />
        <Tile label={reviewer ? 'Approved (all)' : 'Approved'} value={d.counts.approved} tone="text-pass" />
        <Tile label="Policies in the library" value={d.counts.policies} to="/policies" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          {reviewer ? (
            <Panel title="Waiting for your decision" action={<Link to="/reviews" className="text-sm text-pen hover:underline">All reviews</Link>}>
              <ReviewList rows={d.decision_queue} empty="No evaluated reviews from other people right now." />
            </Panel>
          ) : (
            <Panel title="Needs your action" action={<Link to="/reviews" className="text-sm text-pen hover:underline">All reviews</Link>}>
              <ReviewList rows={d.needs_my_action} empty="Nothing to do. Reviews you submit or get back show up here." />
            </Panel>
          )}
          {d.me.role !== 'reviewer' && (
            <Panel title="Your recent reviews">
              <ReviewList rows={d.my_recent} empty="You haven’t submitted a change yet." />
            </Panel>
          )}
        </div>

        <div className="space-y-6">
          <Panel title={reviewer ? 'Findings across all reviews' : 'Findings on your reviews'}>
            {totalFindings === 0 ? (
              <p className="m-0 py-6 text-center text-sm text-ink-soft">No evaluated findings yet.</p>
            ) : (
              <ul className="m-0 mt-3 list-none space-y-3 p-0">
                {order.map((s) => {
                  const n = d.finding_statuses[s] ?? 0
                  return (
                    <li key={s}>
                      <div className="flex items-center justify-between text-sm">
                        <Stamp status={s} size="sm" />
                        <span className="tabular-nums text-ink-soft">{n}</span>
                      </div>
                      <div className="mt-1.5 h-1.5 rounded-full bg-vellum" aria-hidden>
                        <div className="h-1.5 rounded-full" style={{ width: `${(n / totalFindings) * 100}%`, background: STATUS[s].color }} />
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </Panel>
          <Panel title="Your recent activity">
            {d.recent_activity.length === 0 ? (
              <p className="m-0 py-6 text-center text-sm text-ink-soft">No activity yet.</p>
            ) : (
              <ol className="m-0 list-none space-y-2 p-0 text-sm">
                {d.recent_activity.map((a, i) => (
                  <li key={i} className="flex justify-between gap-3">
                    <span>{ACTION_LABEL[a.action] ?? a.action}</span>
                    <time className="shrink-0 text-ink-soft" dateTime={a.ts}>{fmtDate(a.ts)}</time>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        </div>
      </div>
    </div>
  )
}
