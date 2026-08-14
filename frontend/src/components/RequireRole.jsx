import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth.jsx'
import AppShell from './AppShell.jsx'

export function homeForRole(role) {
  if (role === 'voter') return '/vote'
  if (role === 'admin') return '/admin'
  if (role === 'auditor') return '/audit'
  return '/login'
}

/**
 * @param {{ roles?: string[], children: React.ReactNode }} props
 */
export default function RequireRole({ roles, children }) {
  const { user, isReady } = useAuth()
  const location = useLocation()

  if (!isReady) return null

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (user.mustChangePassword && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={homeForRole(user.role)} replace />
  }

  return <AppShell>{children}</AppShell>
}
