import { Navigate, Route, Routes } from 'react-router-dom'
import RequireRole, { homeForRole } from './components/RequireRole.jsx'
import { useAuth } from './lib/auth.jsx'
import ChangePassword from './pages/ChangePassword.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/admin/Dashboard.jsx'
import ElectionSetup from './pages/admin/ElectionSetup.jsx'
import Roster from './pages/admin/Roster.jsx'
import AuditDetail from './pages/auditor/AuditDetail.jsx'
import ElectionPicker from './pages/auditor/ElectionPicker.jsx'
import Ballot from './pages/voter/Ballot.jsx'
import Receipt from './pages/voter/Receipt.jsx'

function RoleHomeRedirect() {
  const { user, isReady } = useAuth()
  if (!isReady) return null
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={homeForRole(user.role)} replace />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/change-password"
        element={
          <RequireRole>
            <ChangePassword />
          </RequireRole>
        }
      />
      <Route
        path="/vote"
        element={
          <RequireRole roles={['voter']}>
            <Ballot />
          </RequireRole>
        }
      />
      <Route
        path="/vote/receipt"
        element={
          <RequireRole roles={['voter']}>
            <Receipt />
          </RequireRole>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireRole roles={['admin']}>
            <Dashboard />
          </RequireRole>
        }
      />
      <Route
        path="/admin/elections/:id"
        element={
          <RequireRole roles={['admin']}>
            <ElectionSetup />
          </RequireRole>
        }
      />
      <Route
        path="/admin/elections/:id/roster"
        element={
          <RequireRole roles={['admin']}>
            <Roster />
          </RequireRole>
        }
      />
      <Route
        path="/audit"
        element={
          <RequireRole roles={['auditor', 'admin']}>
            <ElectionPicker />
          </RequireRole>
        }
      />
      <Route
        path="/audit/:id"
        element={
          <RequireRole roles={['auditor', 'admin']}>
            <AuditDetail />
          </RequireRole>
        }
      />
      <Route path="/" element={<RoleHomeRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
