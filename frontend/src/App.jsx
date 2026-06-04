import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './auth/ProtectedRoute.jsx'
import { AuthCallbackPage } from './pages/AuthCallbackPage.jsx'
import { CircleDetailPage } from './pages/CircleDetailPage.jsx'
import { CirclesPage } from './pages/CirclesPage.jsx'
import { HomePage } from './pages/HomePage.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { YouPage } from './pages/YouPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/home" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route
        path="/home"
        element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/you"
        element={
          <ProtectedRoute>
            <YouPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/circles"
        element={
          <ProtectedRoute>
            <CirclesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/circles/:circleId"
        element={
          <ProtectedRoute>
            <CircleDetailPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
