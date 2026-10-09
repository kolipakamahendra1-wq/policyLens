import { useRef, useState } from 'react'
import { EVIDENCE_TYPES } from './api'
import { Button, inputClass } from './ui'

export interface PendingEvidence { file: File; type: string; note: string }

/** Pick a file, optionally say what it is, and queue it. */
export function EvidenceInput({ onAdd, busy, actionLabel = 'Add evidence' }:
  { onAdd: (e: PendingEvidence) => void | Promise<void>; busy?: boolean; actionLabel?: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [type, setType] = useState('')
  const [note, setNote] = useState('')
  const ref = useRef<HTMLInputElement>(null)
  const isImage = file?.type.startsWith('image/')

  async function add() {
    if (!file) return
    await onAdd({ file, type, note })
    setFile(null); setType(''); setNote('')
    if (ref.current) ref.current.value = ''
  }

  return (
    <div className="grid gap-3 rounded-md border border-dashed border-rule bg-vellum/50 p-4 sm:grid-cols-[1fr_14rem]">
      <input
        ref={ref}
        type="file"
        aria-label="Evidence file"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm file:mr-3 file:rounded-md file:border file:border-rule file:bg-paper file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-ink"
      />
      <select aria-label="Evidence type" value={type} onChange={(e) => setType(e.target.value)} className={inputClass}>
        <option value="">Detect type automatically</option>
        {Object.entries(EVIDENCE_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <input
        aria-label="Note about this evidence"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className={`${inputClass} sm:col-span-2`}
        placeholder={isImage ? 'Describe what the screenshot shows (images are not read automatically)' : 'Optional note, e.g. “prod IAM policy for the customers API”'}
      />
      <div className="sm:col-span-2">
        <Button type="button" variant="secondary" onClick={add} disabled={!file} busy={busy}>{actionLabel}</Button>
      </div>
    </div>
  )
}
