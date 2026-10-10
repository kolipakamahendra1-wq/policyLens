import { useEffect, useState, type FormEvent } from 'react'
import { NavLink, Navigate, useNavigate, useParams } from 'react-router-dom'
import { api, type Profile } from '../api'
import { useAuth } from '../auth'
import { PasswordRules, passwordOk } from '../PasswordRules'
import { Button, ErrorNote, Field, Loading, PageTitle, fmtDate, inputClass } from '../ui'

const SECTIONS = [
  { id: 'profile', label: 'Profile' },
  { id: 'password', label: 'Password' },
  { id: 'sessions', label: 'Sessions & account' },
]

function Saved({ text }: { text: string }) {
  return text ? <p role="status" className="m-0 rounded-md bg-pass/10 px-3 py-2 text-sm text-pass">{text}</p> : null
}

function Card({ title, lead, children }: { title: string; lead?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg bg-paper p-6 ring-1 ring-rule">
      <h2 className="m-0 text-lg font-semibold">{title}</h2>
      {lead && <p className="mt-1 mb-0 text-sm text-ink-soft">{lead}</p>}
      <div className="mt-5">{children}</div>
    </section>
  )
}

function ProfileSection({ me, onSaved }: { me: Profile; onSaved: (p: Profile) => void }) {
  const [name, setName] = useState(me.display_name)
  const [email, setEmail] = useState(me.email ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [saved, setSaved] = useState('')
  const dirty = name !== me.display_name || email !== (me.email ?? '')

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null); setSaved('')
    try { onSaved(await api.updateMe({ display_name: name, email })); setSaved('Profile saved.') }
    catch (err) { setError(err) } finally { setBusy(false) }
  }

  return (
    <Card title="Profile" lead="How you appear to reviewers and in audit packages.">
      <form onSubmit={submit} className="max-w-md space-y-5">
        <Field label="Full name">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={128} />
        </Field>
        <Field label="Email" hint="Used to identify you; PolicyLens doesn’t send email.">
          <input className={inputClass} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        </Field>
        <Field label="Username" hint="Usernames can’t be changed because audit logs refer to them.">
          <input className={`${inputClass} bg-vellum text-ink-soft`} value={me.username} readOnly />
        </Field>
        <ErrorNote error={error} />
        <Saved text={saved} />
        <Button type="submit" busy={busy} disabled={!dirty}>Save profile</Button>
      </form>
    </Card>
  )
}

function PasswordSection({ me }: { me: Profile }) {
  const { adopt } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [saved, setSaved] = useState('')

  if (me.is_demo) {
    return (
      <Card title="Password">
        <p className="m-0 text-ink-soft">
          <span className="font-semibold text-ink">{me.username}</span> is a shared demo account, so its password can’t be changed.
          Create your own account to manage a password.
        </p>
      </Card>
    )
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (next !== confirm) return setError(new Error('The new passwords don’t match.'))
    setBusy(true); setError(null); setSaved('')
    try {
      adopt(await api.changePassword(current, next))
      setCurrent(''); setNext(''); setConfirm('')
      setSaved('Password changed. Other devices have been signed out.')
    } catch (err) { setError(err) } finally { setBusy(false) }
  }

  return (
    <Card title="Change password" lead="Changing your password signs you out everywhere else.">
      <form onSubmit={submit} className="max-w-md space-y-5">
        <Field label="Current password">
          <input className={inputClass} type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
        </Field>
        <Field label="New password">
          <input className={inputClass} type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required />
          <PasswordRules password={next} username={me.username} />
        </Field>
        <Field label="Confirm new password">
          <input className={inputClass} type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
          {confirm && confirm !== next && <span className="mt-1 block text-sm text-fail">Passwords don’t match yet.</span>}
        </Field>
        <ErrorNote error={error} />
        <Saved text={saved} />
        <Button type="submit" busy={busy} disabled={!current || !passwordOk(next, me.username) || next !== confirm}>Change password</Button>
      </form>
    </Card>
  )
}

function SessionsSection({ me }: { me: Profile }) {
  const { adopt, signOut } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [saved, setSaved] = useState('')

  async function everywhere() {
    setBusy(true); setError(null); setSaved('')
    try { adopt(await api.signOutEverywhere()); setSaved('Signed out on every other device. This one stays signed in.') }
    catch (err) { setError(err) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      <Card title="Account">
        <dl className="m-0 grid max-w-md grid-cols-[9rem_1fr] gap-y-3 text-sm">
          <dt className="text-ink-soft">Role</dt>
          <dd className="m-0 capitalize">{me.role}{me.role === 'engineer' && <span className="block text-ink-soft normal-case">Ask an administrator if you need to approve reviews.</span>}</dd>
          <dt className="text-ink-soft">Member since</dt><dd className="m-0">{fmtDate(me.created_at)}</dd>
          <dt className="text-ink-soft">Last sign-in</dt><dd className="m-0">{me.last_login_at ? fmtDate(me.last_login_at) : '—'}</dd>
          <dt className="text-ink-soft">Account type</dt><dd className="m-0">{me.is_demo ? 'Shared demo account' : 'Personal account'}</dd>
        </dl>
      </Card>
      <Card title="Sessions" lead="Sign out on other browsers and devices, for example after using a shared computer.">
        <div className="space-y-4">
          <ErrorNote error={error} />
          <Saved text={saved} />
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" busy={busy} onClick={everywhere}>Sign out other sessions</Button>
            <Button variant="ghost" onClick={() => { signOut(); navigate('/login') }}>Sign out of this device</Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default function Settings() {
  const { section = 'profile' } = useParams()
  const [me, setMe] = useState<Profile | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => { api.me().then(setMe, setError) }, [])

  if (!SECTIONS.some((s) => s.id === section)) return <Navigate to="/settings/profile" replace />
  return (
    <>
      <PageTitle title="Account settings" lead="Manage your profile, password and signed-in sessions." />
      <div className="grid gap-8 md:grid-cols-[12rem_1fr]">
        <nav aria-label="Settings" className="flex gap-1 overflow-x-auto md:flex-col">
          {SECTIONS.map((s) => (
            <NavLink key={s.id} to={`/settings/${s.id}`}
              className={({ isActive }) => `whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium ${isActive ? 'bg-paper text-ink ring-1 ring-rule' : 'text-ink-soft hover:text-ink'}`}>
              {s.label}
            </NavLink>
          ))}
        </nav>
        <div>
          <ErrorNote error={error} />
          {!me && !error && <Loading />}
          {me && section === 'profile' && <ProfileSection me={me} onSaved={setMe} />}
          {me && section === 'password' && <PasswordSection me={me} />}
          {me && section === 'sessions' && <SessionsSection me={me} />}
        </div>
      </div>
    </>
  )
}
