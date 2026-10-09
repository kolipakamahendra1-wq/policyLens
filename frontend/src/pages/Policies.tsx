import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, EVIDENCE_TYPES, type PolicyDetail, type PolicySummary } from '../api'
import { useAuth } from '../auth'
import { Button, ErrorNote, Loading, PageTitle, PolicyQuote, RiskTag } from '../ui'

export function Policies() {
  const { session } = useAuth()
  const [rows, setRows] = useState<PolicySummary[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const canUpload = session?.role !== 'engineer'

  const load = () => api.policies().then(setRows, setError)
  useEffect(() => { load() }, [])

  async function upload(file: File) {
    setBusy(true); setError(null); setNotice('')
    try {
      const p = await api.uploadPolicy(file)
      setNotice(`Added “${p.title}”: ${p.sections} sections, ${p.requirements} requirements.`)
      await load()
    } catch (e) { setError(e) } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <>
      <PageTitle title="Policy library" lead="Every review is matched against these documents. Each section keeps its own citation.">
        {canUpload && (
          <>
            <input ref={fileRef} type="file" accept=".md,.markdown,.txt,.pdf,.html,.htm,.docx" className="sr-only" id="policy-file"
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            <Button busy={busy} onClick={() => fileRef.current?.click()}>Upload policy</Button>
          </>
        )}
      </PageTitle>
      {canUpload && <p className="-mt-4 mb-6 text-sm text-ink-soft">PDF, Markdown, HTML or DOCX. Uploading a policy with the same ID replaces it.</p>}
      {notice && <p role="status" className="mb-4 rounded-md bg-pass/10 px-3 py-2 text-sm text-pass">{notice}</p>}
      <ErrorNote error={error} />
      {!rows && !error && <Loading />}
      {rows && (
        <ul className="m-0 grid list-none gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((p) => (
            <li key={p.id}>
              <Link to={`/policies/${p.id}`} className="block h-full rounded-lg border border-rule bg-paper p-5 text-ink hover:border-pen">
                <span className="font-serif text-sm text-pen">{p.policy_key}</span>
                <span className="mt-1 block text-lg font-semibold">{p.title}</span>
                <span className="mt-3 block text-sm text-ink-soft">{p.sections} sections, {p.requirements} requirements</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export function PolicyView() {
  const id = Number(useParams().id)
  const [p, setP] = useState<PolicyDetail | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => { api.policy(id).then(setP, setError) }, [id])
  if (error) return <ErrorNote error={error} />
  if (!p) return <Loading />
  return (
    <article className="max-w-4xl">
      <p className="m-0 text-sm text-ink-soft"><Link to="/policies" className="text-pen hover:underline">Policy library</Link> / {p.policy_key}</p>
      <h1 className="mt-2 mb-10 text-3xl font-semibold tracking-tight">{p.title}</h1>
      <div className="space-y-10">
        {p.sections.map((s) => (
          <section key={s.citation}>
            <h2 className="m-0 mb-3 text-lg font-semibold">{s.heading}</h2>
            <PolicyQuote citation={s.citation}>{s.text}</PolicyQuote>
            {s.requirements.length > 0 && (
              <ul className="m-0 mt-4 list-none space-y-2 p-0 pl-[6.25rem] sm:pl-[7.75rem]">
                {s.requirements.map((r) => (
                  <li key={r.code} className="rounded-md bg-paper px-3 py-2 text-sm ring-1 ring-rule">
                    <span className="font-semibold">{r.code}</span> <RiskTag risk={r.risk} />
                    <span className="block text-ink-soft">Checked with: {r.evidence_types.map((t) => EVIDENCE_TYPES[t] ?? t).join(', ') || 'reviewer judgement'}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </article>
  )
}
