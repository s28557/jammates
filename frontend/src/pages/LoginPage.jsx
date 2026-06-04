import { API_BASE_URL } from '../api/apiClient.js'

export function LoginPage() {
  const loginUrl = `${API_BASE_URL}/auth/spotify/login`

  return (
    <div className="auth-screen">
      <div className="auth-panel">
        <p className="eyebrow">JamMates</p>
        <h1>Find concerts through your music taste.</h1>
        <form action={loginUrl} method="get">
          <button className="primary-button" type="submit">
            Continue with Spotify
          </button>
        </form>
      </div>
    </div>
  )
}
