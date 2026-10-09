import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type AuditEntry } from '../api'
import { ErrorNote, Loading, PageTitle, fmtDate } from '../ui'

const LABEL: Record<string, string> = {
  'auth.login': 'signed in', 'policy.ingest': 'uploaded a policy', 'review.submit': 'submitted a review',
  'evidence.add': 'attached evidence', 'evidence.download': 'downloaded evidence', 'review.evaluate': 'ran an evaluation',
  'review.approve': 'approved a review', 'review.reject': 'rejected a review', 'review.return': 'sent a review back',
  'audit.package': 'opened an audit package',
}

function Target({ target }: { target: string }) {
  const [kind, id] = target.split(':')
  if (kind === 'review') return <Link to={`/reviews/${id}`} className="text-pen hover:underline">review #{id}</Link>
  if (kind === 'policy') return <Link to={`/policies/${id}`} className="text-pen hover:underline">policy #{id}</Link>
  return <span className="text-ink-soft">{target}</span>
}

export default function Activity() {
  const [rows, setRows] = useState<AuditEntry[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => { api.activity().then(setRows, setError) }, [])
  return (
    <>
      <PageTitle title="Activity" lead="Every sign-in, upload, evaluation and decision, newest first." />
      <ErrorNote error={error} />
      {!rows && !error && <Loading />}
      {rows && (
        <ol className="m-0 list-none divide-y divide-rule rounded-lg bg-paper p-0 ring-1 ring-rule">
          {rows.map((a) => (
            <li key={a.id} className="flex flex-wrap justify-between gap-2 px-4 py-3 text-sm">
              <span><span className="font-semibold">{a.actor}</span> {LABEL[a.action] ?? a.action} <Target target={a.target} /></span>
              <time className="text-ink-soft" dateTime={a.ts}>{fmtDate(a.ts)}</time>
            </li>
          ))}
        </ol>
      )}
    </>
  )
}
