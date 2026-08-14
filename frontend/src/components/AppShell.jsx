import { Link } from 'react-router-dom'
import { homeForRole } from './RequireRole.jsx'
import { useAuth } from '../lib/auth.jsx'

const ROLE_LABELS = { admin: 'Admin', auditor: 'Auditor', voter: 'Voter' }

export default function AppShell({ children }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-svh bg-sheet">
      <header className="flex items-center justify-between bg-maroon px-4 py-3 text-sheet sm:px-8">
        <Link to={user ? homeForRole(user.role) : '/login'} className="font-display text-lg uppercase tracking-wide">
          UniVote
        </Link>
        <div className="flex items-center gap-4 font-body text-sm">
          {user && (
            <span className="hidden text-sheet/80 sm:inline">
              {user.fullName} · {ROLE_LABELS[user.role] ?? user.role}
            </span>
          )}
          <button
            type="button"
            onClick={logout}
            className="rounded border border-sheet/40 px-3 py-1 text-sm transition-colors hover:bg-maroonDark"
          >
            Log out
          </button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  )
}
