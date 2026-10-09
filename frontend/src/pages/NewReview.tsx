import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, EVIDENCE_TYPES } from '../api'
import { EvidenceInput, type PendingEvidence } from '../EvidenceInput'
import { Button, ErrorNote, Field, PageTitle, inputClass } from '../ui'

export default function NewReview() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [queue, setQueue] = useState<PendingEvidence[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const review = await api.createReview(title, description)
      for (const ev of queue) await api.addEvidence(review.id, ev.file, ev.type, ev.note)
      navigate(`/reviews/${review.id}`)
    } catch (err) {
      setError(err)
      setBusy(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <PageTitle title="Start a review" lead="Describe the change in plain language and attach any evidence you already have. You can add more later." />
      <form onSubmit={submit} className="space-y-7">
        <Field label="Title">
          <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Customer profile API" required minLength={3} />
        </Field>
        <Field label="What is changing?" hint="Mention the data involved, where it is stored, who can access it and how it ships.">
          <textarea
            className={`${inputClass} min-h-36 font-serif text-[1.05rem] leading-relaxed`}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="We are deploying a new API that stores customer information…"
            required
            minLength={10}
          />
        </Field>
        <div>
          <p className="m-0 text-sm font-semibold">Evidence</p>
          <p className="mt-0.5 mb-3 text-sm text-ink-soft">Configuration files, API specifications, architecture documents or screenshots.</p>
          {queue.length > 0 && (
            <ul className="m-0 mb-3 list-none space-y-2 p-0">
              {queue.map((q, i) => (
                <li key={i} className="flex items-center justify-between gap-3 rounded-md border border-rule bg-paper px-3 py-2 text-sm">
                  <span><span className="font-semibold">{q.file.name}</span>
                    <span className="text-ink-soft">{q.type ? `, ${EVIDENCE_TYPES[q.type]}` : ', type detected on upload'}</span></span>
                  <button type="button" className="text-pen hover:underline" onClick={() => setQueue(queue.filter((_, j) => j !== i))}>Remove</button>
                </li>
              ))}
            </ul>
          )}
          <EvidenceInput actionLabel="Attach file" onAdd={(e) => setQueue([...queue, e])} />
        </div>
        <ErrorNote error={error} />
        <div className="flex gap-3">
          <Button type="submit" busy={busy}>Submit change request</Button>
          <Button type="button" variant="ghost" onClick={() => navigate('/reviews')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
