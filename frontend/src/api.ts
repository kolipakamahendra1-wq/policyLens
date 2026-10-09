export type Status = 'PASS' | 'FAIL' | 'UNKNOWN' | 'NEEDS_HUMAN_REVIEW'
export type Role = 'engineer' | 'reviewer' | 'admin'

export interface Session { token: string; username: string; role: Role }

export interface PolicySummary {
  id: number; policy_key: string; title: string; domain: string; filename: string
  sections: number; requirements: number; created_at: string
}
export interface PolicyDetail {
  id: number; policy_key: string; title: string; domain: string
  sections: { citation: string; heading: string; text: string
    requirements: { code: string; text: string; risk: string; evidence_types: string[] }[] }[]
}
export interface ReviewSummary {
  id: number; title: string; submitted_by: string; status: string; result: string | null
  evidence: number; findings: number; open: number; created_at: string
}
export interface Finding {
  id: number; requirement: string; requirement_text: string; risk: 'high' | 'medium' | 'low'
  citation: string; policy: string; section_heading: string; policy_text: string; status: Status
  interpretation: string; evidence_ids: number[]; confidence: number; source: string; notes: string[]
  evidence_types: string[]
}
export interface EvidenceItem {
  id: number; filename: string; evidence_type: string; sha256: string; content_type: string
  excerpt: string; created_at: string
}
export interface Review {
  id: number; title: string; description: string; submitted_by: string; status: string
  result: string | null; claims: { text: string; types: string[] }[]; summary: string | null
  evidence_requested: string[]; created_at: string; evidence: EvidenceItem[]; findings: Finding[]
  decisions: { reviewer: string; action: string; comment: string; created_at: string }[]
}
export interface Control {
  id: number; code: string; text: string; risk: string; evidence_types: string[]; citation: string
  heading: string; policy_title: string; policy_text: string; retrieval_score: number
}
export interface AuditEntry { id: number; actor: string; action: string; target: string; detail: Record<string, unknown>; ts: string }
export interface AuditPackage {
  review_id: number; title: string; generated_at: string; disclaimer: string
  executive_summary: { request: string; submitted_by: string; result: string; status: string; summary: string
    final_decision: { reviewer: string; action: string; comment: string; at: string } | null }
  control_matrix: { requirement: string; citation: string; policy: string; policy_text: string; risk: string
    status: Status; interpretation: string; evidence: string[]; decided_by: string; guardrail_notes: string[] }[]
  evidence_references: { id: string; filename: string; type: string; sha256: string; uploaded_at: string }[]
  open_questions: string[]; evidence_requested: string[]
  risk_register: { requirement: string; citation: string; risk: string; status: Status; issue: string }[]
  reviewer_checklist: { item: string; done: boolean }[]
  decision_history: { reviewer: string; action: string; comment: string; at: string }[]
}

const KEY = 'policylens.session'

export function loadSession(): Session | null {
  try { return JSON.parse(localStorage.getItem(KEY) || 'null') } catch { return null }
}
export function saveSession(s: Session | null) {
  try { s ? localStorage.setItem(KEY, JSON.stringify(s)) : localStorage.removeItem(KEY) } catch { /* storage unavailable */ }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function request<T>(path: string, init: RequestInit = {}, raw = false): Promise<T> {
  const s = loadSession()
  const headers = new Headers(init.headers)
  if (s) headers.set('Authorization', `Bearer ${s.token}`)
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams))
    headers.set('Content-Type', 'application/json')
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (res.status === 401 && path !== '/token') {
    saveSession(null)
    window.location.assign('/login?expired=1')
  }
  if (!res.ok) {
    let msg = res.statusText
    try {
      const body = await res.json()
      msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* not json */ }
    throw new ApiError(res.status, msg)
  }
  return (raw ? res.text() : res.json()) as Promise<T>
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; username: string; role: Role }>('/token', {
      method: 'POST', body: new URLSearchParams({ username, password }),
    }),
  policies: () => request<PolicySummary[]>('/policies'),
  policy: (id: number) => request<PolicyDetail>(`/policies/${id}`),
  uploadPolicy: (file: File) => {
    const f = new FormData(); f.append('file', file)
    return request<{ title: string; sections: number; requirements: number }>('/policies', { method: 'POST', body: f })
  },
  reviews: () => request<ReviewSummary[]>('/reviews'),
  review: (id: number) => request<Review>(`/reviews/${id}`),
  createReview: (title: string, description: string) =>
    request<Review>('/reviews', { method: 'POST', body: JSON.stringify({ title, description }) }),
  addEvidence: (reviewId: number, file: File, evidenceType: string, note: string) => {
    const f = new FormData()
    f.append('review_id', String(reviewId)); f.append('file', file)
    f.append('evidence_type', evidenceType); f.append('note', note)
    return request<{ filename: string; detected_types: string[] }>('/evidence', { method: 'POST', body: f })
  },
  controls: (reviewId: number) => request<Control[]>(`/controls?review_id=${reviewId}`),
  evaluate: (reviewId: number) =>
    request<Review>('/evaluate', { method: 'POST', body: JSON.stringify({ review_id: reviewId }) }),
  decide: (reviewId: number, action: 'approve' | 'reject' | 'return', comment: string) =>
    request<Review>('/approve', { method: 'POST', body: JSON.stringify({ review_id: reviewId, action, comment }) }),
  audit: (reviewId: number) => request<AuditPackage>(`/audit/${reviewId}`),
  auditMarkdown: (reviewId: number) => request<string>(`/audit/${reviewId}?format=md`, {}, true),
  activity: () => request<AuditEntry[]>('/audit-log'),
}

export async function downloadEvidence(id: number, filename: string) {
  const s = loadSession()
  const res = await fetch(`/api/evidence/${id}/download`, { headers: s ? { Authorization: `Bearer ${s.token}` } : {} })
  if (!res.ok) throw new ApiError(res.status, 'Download failed')
  saveBlob(await res.blob(), filename)
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}

export const EVIDENCE_TYPES: Record<string, string> = {
  iam: 'IAM configuration',
  retention: 'Retention configuration',
  encryption: 'Encryption configuration',
  logging: 'Logging configuration',
  data_classification: 'Data classification record',
  deployment: 'Deployment / rollback plan',
  api_spec: 'API specification',
  change_management: 'Change ticket / approval',
  privacy: 'Privacy impact assessment',
}
