import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut, User } from 'lucide-react'
import { getCurrentUser } from '../api/users.js'

export function AppLayout({
  children,
  headerActions,
  headerAside,
  headerTitle,
  mainClassName = '',
  title,
  titleAction,
}) {
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

  // Logout action
  const handleLogout = () => {
    localStorage.removeItem('jammates_token')
    navigate('/login', { replace: true })
  }

  // App layout shell and page content
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/home">
          <span className="brand-jam">Jam</span><span className="brand-dot">×</span><span className="brand-mates">Mates</span>
        </Link>
        {headerTitle && <h1 className="header-title">{headerTitle}</h1>}
        {headerAside}
        {headerActions && <div className="header-actions">{headerActions}</div>}

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
        {title && (
          <div className="page-title-row">
            <h1 className="page-title">{title}</h1>
            {titleAction}
          </div>
        )}
        {children}
      </main>
    </div>
  )
}
