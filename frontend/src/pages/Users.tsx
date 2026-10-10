import { useEffect, useState } from 'react'
import { api, type Profile, type Role } from '../api'
import { useAuth } from '../auth'
import { ErrorNote, Loading, PageTitle, fmtDate, inputClass } from '../ui'

export default function Users() {
  const { session } = useAuth()
  const [rows, setRows] = useState<Profile[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState<number | null>(null)

  useEffect(() => { api.users().then(setRows, setError) }, [])

  async function run(id: number, fn: () => Promise<string | Profile>) {
    setBusy(id); setError(null); setNotice('')
    try {
      const r = await fn()
      if (typeof r === 'string') setNotice(r)
      else setRows((rs) => rs!.map((u) => (u.id === r.id ? r : u)))
    } catch (e) { setError(e) } finally { setBusy(null) }
  }

  return (
    <>
      <PageTitle title="Users" lead="Roles decide what people can do: engineers submit changes, reviewers decide, admins also manage policies and users." />
      <ErrorNote error={error} />
      {notice && <p role="status" className="mb-4 rounded-md bg-unknown/10 px-3 py-2 text-sm">{notice}</p>}
      {!rows && !error && <Loading />}
      {rows && (
        <div className="overflow-x-auto rounded-lg bg-paper ring-1 ring-rule">
          <table className="w-full min-w-[760px] border-collapse text-left text-sm">
            <thead className="border-b border-rule text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Last sign-in</th>
                <th className="px-4 py-3 font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => {
                const locked = u.is_demo || u.username === session?.username
                return (
                  <tr key={u.id} className="border-b border-rule last:border-0">
                    <td className="px-4 py-3">
                      <span className="font-semibold">{u.display_name}</span>
                      <span className="block text-xs text-ink-soft">{u.username}{u.email ? `, ${u.email}` : ''}{u.is_demo ? ', demo' : ''}</span>
                    </td>
                    <td className="px-4 py-3">
                      <select aria-label={`Role for ${u.username}`} className={`${inputClass} w-36 py-1 disabled:cursor-not-allowed disabled:bg-vellum disabled:text-ink-soft`} value={u.role} disabled={locked || busy === u.id}
                        onChange={(e) => run(u.id, () => api.updateUser(u.id, { role: e.target.value as Role }))}>
                        <option value="engineer">Engineer</option>
                        <option value="reviewer">Reviewer</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={u.is_active ? 'text-pass' : 'text-fail'}>{u.is_active ? 'Active' : 'Deactivated'}</span>
                    </td>
                    <td className="px-4 py-3 text-ink-soft">{u.last_login_at ? fmtDate(u.last_login_at) : 'Never'}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {!locked && (
                        <>
                          <button className="mr-3 text-pen hover:underline disabled:opacity-50" disabled={busy === u.id}
                            onClick={() => run(u.id, async () => {
                              const r = await api.resetPassword(u.id)
                              return `Temporary password for ${r.username}: ${r.temporary_password} (shown once; share it privately and ask them to change it).`
                            })}>Reset password</button>
                          <button className={`hover:underline disabled:opacity-50 ${u.is_active ? 'text-fail' : 'text-pass'}`} disabled={busy === u.id}
                            onClick={() => run(u.id, () => api.updateUser(u.id, { is_active: !u.is_active }))}>
                            {u.is_active ? 'Deactivate' : 'Reactivate'}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-sm text-ink-soft">Demo accounts and your own account can’t be changed here.</p>
    </>
  )
}
