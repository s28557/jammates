import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { AUTH_EXPIRED_EVENT } from '../api/apiClient.js'

export function ProtectedRoute({ children }) {
  const location = useLocation()
  const [token, setToken] = useState(() => localStorage.getItem('jammates_token'))

  useEffect(() => {
    const handleAuthExpired = () => {
      setToken(null)
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired)

    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired)
    }
  }, [])

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}
