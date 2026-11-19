import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { createCircle, getMyCircles, joinCircle } from '../api/circles.js'
import { MAX_CIRCLES_PER_USER } from '../config/appConfig.js'
import { AppLayout } from '../layout/AppLayout.jsx'

export function CirclesPage() {
  const [circles, setCircles] = useState([])
  const [circleName, setCircleName] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [actionsOpen, setActionsOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Circles page data loading
  async function loadCircles() {
    setLoading(true)
    setError('')

    try {
      const data = await getMyCircles()
      setCircles(data)
    } catch (requestError) {
      setError(requestError.message || 'Could not load circles')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCircles()
  }, [])

  // Create circle form
  const handleCreateCircle = async (event) => {
    event.preventDefault()

    if (!circleName.trim()) {
      return
    }

    setSaving(true)
    setError('')

    try {
      await createCircle(circleName.trim())
      setCircleName('')
      setActionsOpen(false)
      await loadCircles()
    } catch (requestError) {
      setError(requestError.message || 'Could not create circle')
    } finally {
      setSaving(false)
    }
  }

  // Join circle form
  const handleJoinCircle = async (event) => {
    event.preventDefault()

    if (!inviteCode.trim()) {
      return
    }

    setSaving(true)
    setError('')

    try {
      await joinCircle(inviteCode.trim())
      setInviteCode('')
      setActionsOpen(false)
      await loadCircles()
    } catch (requestError) {
      setError(requestError.message || 'Could not join circle')
    } finally {
      setSaving(false)
    }
  }

  // Circles grid and create/join modal
  return (
    <AppLayout headerTitle={<span className="header-title-circles">Circles</span>} mainClassName="circles-main">
      <section className="circles-page">
        {loading && <p className="loading-state">Loading circles...</p>}
        {error && <p className="error-state">{error}</p>}

        {!loading && (
          <div className="circle-grid">
            {circles.slice(0, MAX_CIRCLES_PER_USER).map((circle) => (
              <Link className="circle-card" key={circle.id} to={`/circles/${circle.id}`}>
                <div className={`circle-art ${circle.image_url ? 'circle-art-image' : ''}`} aria-hidden="true">
                  {circle.image_url ? (
                    <img src={circle.image_url} alt="" />
                  ) : (
                    <>
                      <span />
                      <span />
                    </>
                  )}
                </div>
                <h3>{circle.name}</h3>
              </Link>
            ))}

            {circles.length < MAX_CIRCLES_PER_USER && (
              <button className="circle-card circle-card-add" type="button" onClick={() => setActionsOpen(true)}>
                <div className="circle-add-box" aria-hidden="true">
                  +
                </div>
                <h3>Create / Join</h3>
              </button>
            )}
          </div>
        )}

        {actionsOpen && (
          <div className="circle-actions-modal" role="dialog" aria-modal="true" aria-label="Create or join circle">
            <div className="circle-actions-panel">
              <button className="modal-close" type="button" onClick={() => setActionsOpen(false)} aria-label="Close">
                x
              </button>

              <form className="circle-form" onSubmit={handleCreateCircle}>
                <h2>Create circle</h2>
                <input
                  type="text"
                  placeholder="Circle name"
                  value={circleName}
                  onChange={(event) => setCircleName(event.target.value)}
                />
                <button className="secondary-button" type="submit" disabled={saving || !circleName.trim()}>
                  Create
                </button>
              </form>

              <form className="circle-form" onSubmit={handleJoinCircle}>
                <h2>Join circle</h2>
                <input
                  type="text"
                  placeholder="Invite code"
                  value={inviteCode}
                  onChange={(event) => setInviteCode(event.target.value)}
                />
                <button className="secondary-button" type="submit" disabled={saving || !inviteCode.trim()}>
                  Join
                </button>
              </form>
            </div>
          </div>
        )}
      </section>
    </AppLayout>
  )
}
