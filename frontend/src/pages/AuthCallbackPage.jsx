import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const [error, setError] = useState('')

  // Spotify auth callback handling
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    const spotifyError = params.get('error')

    if (token) {
      localStorage.setItem('jammates_token', token)
      navigate('/home', { replace: true })
      return
    }

    if (spotifyError) {
      setError(`Spotify returned an error: ${spotifyError}`)
      return
    }

    setError(`No token found in callback URL: ${window.location.href}`)
  }, [navigate])

  // Auth callback status screen
  return (
    <div className="auth-screen">
      <div className="auth-panel">
        <p className="eyebrow">JamMates</p>
        <h1>{error ? 'Login callback failed.' : 'Connecting...'}</h1>
        {error && <p className="auth-error">{error}</p>}
      </div>
    </div>
  )
}
