// Mirrors backend/security.py password_problems(); the server stays the source of truth.
export function passwordChecks(password: string, username: string) {
  return [
    { label: 'At least 10 characters', ok: password.length >= 10 },
    { label: 'A letter and a number', ok: /[A-Za-z]/.test(password) && /\d/.test(password) },
    { label: 'Doesn’t contain your username', ok: !username || !password.toLowerCase().includes(username.toLowerCase()) },
  ]
}

export function PasswordRules({ password, username }: { password: string; username: string }) {
  return (
    <ul className="m-0 mt-2 list-none space-y-1 p-0 text-sm" aria-label="Password requirements">
      {passwordChecks(password, username).map((c) => (
        <li key={c.label} className={c.ok ? 'text-pass' : 'text-ink-soft'}>
          <span aria-hidden className="mr-2 inline-block w-3">{c.ok ? '✓' : '○'}</span>
          {c.label}
          <span className="sr-only">{c.ok ? ' (met)' : ' (not met yet)'}</span>
        </li>
      ))}
    </ul>
  )
}

export const passwordOk = (password: string, username: string) => passwordChecks(password, username).every((c) => c.ok)
