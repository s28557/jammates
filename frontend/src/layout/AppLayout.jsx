import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut, Menu, Search, User } from 'lucide-react'
import { getCurrentUser } from '../api/users.js'

export function AppLayout({ children, mainClassName = '', title }) {
  const navigate = useNavigate()
  const [currentUser, setCurrentUser] = useState(null)
  const [userError, setUserError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadCurrentUser() {
      try {
        const user = await getCurrentUser()
        if (!ignore) {
          setCurrentUser(user)
          setUserError('')
        }
      } catch (error) {
        if (!ignore) {
          setUserError('Could not load profile')
        }
      }
    }

    loadCurrentUser()

    return () => {
      ignore = true
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('jammates_token')
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/home">
          JamMates
        </Link>

        <label className="search-box">
          <Search size={16} aria-hidden="true" />
          <input type="search" placeholder="Search" />
        </label>

        <button className="icon-button" type="button" aria-label="Menu">
          <Menu size={20} />
        </button>
        <div className="profile-chip" title={userError || currentUser?.email || 'Profile'}>
          {currentUser?.avatar_url ? (
            <img src={currentUser.avatar_url} alt="" />
          ) : (
            <User size={18} aria-hidden="true" />
          )}
          <span>{currentUser?.display_name || userError || 'Profile'}</span>
        </div>
        <button className="icon-button" type="button" aria-label="Logout" onClick={handleLogout}>
          <LogOut size={20} />
        </button>
      </header>

      <main className={`app-main ${mainClassName}`.trim()}>
        {title && <h1 className="page-title">{title}</h1>}
        {children}
      </main>
    </div>
  )
}
