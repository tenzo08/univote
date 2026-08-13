import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import RequireRole from './RequireRole'

const mockUseAuth = vi.fn()
vi.mock('../lib/auth.jsx', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderGuarded({ path = '/protected', roles } = {}) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<div>Login screen</div>} />
        <Route path="/vote" element={<div>Voter home</div>} />
        <Route path="/admin" element={<div>Admin home</div>} />
        <Route path="/audit" element={<div>Auditor home</div>} />
        <Route
          path="/change-password"
          element={
            <RequireRole>
              <div>Change password screen</div>
            </RequireRole>
          }
        />
        <Route
          path="/protected"
          element={
            <RequireRole roles={roles}>
              <div>Protected content</div>
            </RequireRole>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireRole', () => {
  it('redirects to /login when there is no authenticated user', () => {
    mockUseAuth.mockReturnValue({ user: null, isReady: true })
    renderGuarded()
    expect(screen.getByText('Login screen')).toBeInTheDocument()
  })

  it('redirects to /change-password when must_change_password is true', () => {
    mockUseAuth.mockReturnValue({
      user: { role: 'voter', mustChangePassword: true },
      isReady: true,
    })
    renderGuarded()
    expect(screen.getByText('Change password screen')).toBeInTheDocument()
  })

  it('does not redirect away from /change-password itself, avoiding a loop', () => {
    mockUseAuth.mockReturnValue({
      user: { role: 'voter', mustChangePassword: true },
      isReady: true,
    })
    renderGuarded({ path: '/change-password' })
    expect(screen.getByText('Change password screen')).toBeInTheDocument()
  })

  it("redirects to the user's own home when their role is not allowed", () => {
    mockUseAuth.mockReturnValue({
      user: { role: 'voter', mustChangePassword: false },
      isReady: true,
    })
    renderGuarded({ roles: ['admin'] })
    expect(screen.getByText('Voter home')).toBeInTheDocument()
  })

  it('renders the protected content when role and password state are both fine', () => {
    mockUseAuth.mockReturnValue({
      user: { role: 'admin', mustChangePassword: false },
      isReady: true,
    })
    renderGuarded({ roles: ['admin'] })
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('renders nothing while the auth state is not ready yet', () => {
    mockUseAuth.mockReturnValue({ user: null, isReady: false })
    const { container } = renderGuarded()
    expect(container).toBeEmptyDOMElement()
  })
})
