import { useCallback, useEffect, useRef, useState } from 'react'
import { Camera, Check, ChevronLeft, Copy, Filter, LogOut, Pencil, Settings, Star, Trash2, UserMinus, X } from 'lucide-react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  deleteCircle,
  getCircleMembers,
  getMyCircles,
  leaveCircle,
  removeCircleMember,
  uploadCircleImage,
  updateCircleName,
} from '../api/circles.js'
import { getCircleForYouConcerts, getCircleSomethingNewConcerts } from '../api/concerts.js'
import { CategorySwitch } from '../components/CategorySwitch.jsx'
import { CircleTasteView } from '../components/CircleTasteView.jsx'
import { ConcertRecommendationsView } from '../components/ConcertRecommendationsView.jsx'
import { MAX_MEMBERS_PER_CIRCLE } from '../config/appConfig.js'
import { AppLayout } from '../layout/AppLayout.jsx'

const VIEW_OPTIONS = [
  { value: 'concerts', label: 'Concerts' },
  { value: 'taste', label: 'Taste' },
]

export function CircleDetailPage() {
  const { circleId } = useParams()
  // the view lives in the URL so a refresh or back button keeps it
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get('view') === 'taste' ? 'taste' : 'concerts'
  const navigate = useNavigate()
  const [circle, setCircle] = useState(null)
  const [circleName, setCircleName] = useState('')
  const [circleNameDraft, setCircleNameDraft] = useState('')
  const [members, setMembers] = useState([])
  const [forYouConcerts, setForYouConcerts] = useState([])
  const [somethingNewConcerts, setSomethingNewConcerts] = useState([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [editingName, setEditingName] = useState(false)
  const [loading, setLoading] = useState(true)
  const [savingAction, setSavingAction] = useState(false)
  const [inviteCopied, setInviteCopied] = useState(false)
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const settingsRef = useRef(null)

  const currentMember = members.find((member) => member.is_current_user)
  const isAdmin = currentMember?.role === 'creator'

  // Circle page data loading
  const loadCircleData = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const [circles, circleMembers] = await Promise.all([
        getMyCircles(),
        getCircleMembers(circleId),
      ])

      const activeCircle = circles.find((item) => String(item.id) === String(circleId))
      setCircle(activeCircle || null)
      setCircleName(activeCircle?.name || `Circle ${circleId}`)
      setCircleNameDraft(activeCircle?.name || `Circle ${circleId}`)
      setMembers(circleMembers)

      const [forYou, somethingNew] = await Promise.all([
        getCircleForYouConcerts(circleId, { artistLimit: 40 }),
        getCircleSomethingNewConcerts(circleId, { artistLimit: 40 }),
      ])

      setForYouConcerts(forYou)
      setSomethingNewConcerts(somethingNew)
    } catch (requestError) {
      if (requestError.status === 409) {
        setError('Waiting for at least one more person to join this circle.')
      } else {
        setError(requestError.message || 'Could not load circle concerts')
      }
    } finally {
      setLoading(false)
    }
  }, [circleId])

  useEffect(() => {
    loadCircleData()
  }, [loadCircleData])

  // Invite code action
  const handleCopyInviteCode = async () => {
    if (!circle?.invite_code) {
      return
    }

    await navigator.clipboard?.writeText(circle.invite_code)
    setInviteCopied(true)
    window.setTimeout(() => setInviteCopied(false), 900)
  }

  // Circle image settings, uploads right after a file is picked
  const handleUploadCircleImage = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''

    if (!file) {
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setActionMessage('Image too large (max 5 MB)')
      return
    }

    setSavingAction(true)
    setActionMessage('')

    try {
      const updatedCircle = await uploadCircleImage(circleId, file)
      setCircle(updatedCircle)
      setActionMessage('Circle image updated')
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not update circle image')
    } finally {
      setSavingAction(false)
    }
  }

  // Circle name settings
  const handleUpdateCircleName = async (event) => {
    event.preventDefault()

    if (!circleNameDraft.trim()) {
      return
    }

    setSavingAction(true)
    setActionMessage('')

    try {
      const updatedCircle = await updateCircleName(circleId, circleNameDraft.trim())
      setCircle(updatedCircle)
      setCircleName(updatedCircle.name)
      setCircleNameDraft(updatedCircle.name)
      setEditingName(false)
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not update circle name')
    } finally {
      setSavingAction(false)
    }
  }

  // Each edit starts from the saved name, so a closed or cancelled edit leaves nothing behind
  const startNameEdit = () => {
    setCircleNameDraft(circleName)
    setEditingName(true)
  }

  const cancelNameEdit = () => setEditingName(false)

  // Circle membership actions
  const handleLeaveCircle = async () => {
    if (!window.confirm('Are you sure you want to leave this circle?')) {
      return
    }

    setSavingAction(true)
    try {
      await leaveCircle(circleId)
      navigate('/circles', { replace: true })
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not leave circle')
      setSavingAction(false)
    }
  }

  // Circle admin member actions
  const handleRemoveMember = async (member) => {
    const name = member.is_current_user ? 'you' : member.display_name
    if (!window.confirm(`Are you sure you want to remove ${name} from this circle?`)) {
      return
    }

    setSavingAction(true)
    setActionMessage('')

    try {
      await removeCircleMember(circleId, member.id)
      await loadCircleData()
      setActionMessage('Member removed')
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not remove member')
    } finally {
      setSavingAction(false)
    }
  }

  // Circle admin danger action
  const handleDeleteCircle = async () => {
    if (!window.confirm('Are you sure you want to delete this circle? This cannot be undone.')) {
      return
    }

    setSavingAction(true)
    try {
      await deleteCircle(circleId)
      navigate('/circles', { replace: true })
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not delete circle')
      setSavingAction(false)
    }
  }

  // Closing the settings popover also drops an unfinished name edit
  const closeSettings = () => {
    setSettingsOpen(false)
    setEditingName(false)
  }

  const toggleSettings = () => (settingsOpen ? closeSettings() : setSettingsOpen(true))

  // Settings popover closes on outside click and Escape
  useEffect(() => {
    if (!settingsOpen) {
      return undefined
    }

    const handlePointerDown = (event) => {
      if (!settingsRef.current?.contains(event.target)) {
        setSettingsOpen(false)
        setEditingName(false)
      }
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setSettingsOpen(false)
        setEditingName(false)
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [settingsOpen])

  // Circle settings popover content
  const settingsContent = (
    <div className="circle-settings">
      <div className="circle-settings-profile">
        <label
          className={`circle-settings-image ${savingAction ? 'circle-settings-image-busy' : ''}`}
          title="Change circle image"
        >
          {circle?.image_url ? <img src={circle.image_url} alt="" /> : <Camera size={26} aria-hidden="true" />}
          <span className="circle-settings-image-overlay" aria-hidden="true">
            <Camera size={20} />
          </span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            aria-label="Change circle image"
            disabled={savingAction}
            onChange={handleUploadCircleImage}
          />
        </label>

        {editingName ? (
          <form className="circle-settings-name-form" onSubmit={handleUpdateCircleName}>
            <input
              aria-label="Circle name"
              autoFocus
              type="text"
              value={circleNameDraft}
              onChange={(event) => setCircleNameDraft(event.target.value)}
              onKeyDown={(event) => {
                // Escape cancels the edit without closing the popover
                if (event.key === 'Escape') {
                  event.stopPropagation()
                  cancelNameEdit()
                }
              }}
            />
            <button type="submit" aria-label="Save name" disabled={savingAction || !circleNameDraft.trim()}>
              <Check size={16} />
            </button>
            <button type="button" aria-label="Cancel" onClick={cancelNameEdit}>
              <X size={16} />
            </button>
          </form>
        ) : (
          <div className="circle-settings-name">
            <h2>{circleName}</h2>
            {isAdmin && (
              <button type="button" aria-label="Rename circle" onClick={startNameEdit}>
                <Pencil size={14} />
              </button>
            )}
          </div>
        )}

        {actionMessage && <p className="circle-action-message">{actionMessage}</p>}
      </div>

      <section className="circle-settings-section">
        <h3>Invite code</h3>
        <div className="circle-invite-pill">
          <strong>{circle?.invite_code || '...'}</strong>
          <button type="button" onClick={handleCopyInviteCode} disabled={!circle?.invite_code}>
            {inviteCopied ? <Check size={14} /> : <Copy size={14} />}
            {inviteCopied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </section>

      <section className="circle-settings-section">
        <h3>
          Members <span>{members.length}/{MAX_MEMBERS_PER_CIRCLE}</span>
        </h3>
        <ul className="circle-settings-members">
          {members.map((member) => (
            <li key={member.id}>
              <span className="circle-avatar">
                {member.avatar_url ? (
                  <img src={member.avatar_url} alt="" />
                ) : (
                  (member.display_name || '?').trim().charAt(0).toUpperCase()
                )}
              </span>
              <span className="circle-settings-member-name">
                {member.is_current_user ? 'you' : member.display_name}
              </span>
              {member.role === 'creator' && (
                <span className="circle-admin-badge">
                  <Star fill="currentColor" size={11} aria-hidden="true" />
                  admin
                </span>
              )}
              {isAdmin && !member.is_current_user && (
                <button
                  className="circle-member-remove"
                  type="button"
                  onClick={() => handleRemoveMember(member)}
                  disabled={savingAction}
                  aria-label={`Remove ${member.display_name}`}
                  title="Remove from circle"
                >
                  <UserMinus size={15} />
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <div className="circle-settings-footer">
        <button type="button" onClick={handleLeaveCircle} disabled={savingAction}>
          <LogOut size={15} />
          Leave circle
        </button>
        {isAdmin && (
          <button className="circle-settings-delete" type="button" onClick={handleDeleteCircle} disabled={savingAction}>
            <Trash2 size={15} />
            Delete circle
          </button>
        )}
      </div>
    </div>
  )

  // Circle name, member avatars and settings popover in the top bar
  // they share one anchor so the popover spans from the circle image to the gear
  const headerTitle = (
    <span className="circle-title">
      <span className={`circle-title-image ${circle?.image_url ? 'circle-title-image-filled' : ''}`} aria-hidden="true">
        {circle?.image_url ? (
          <img src={circle.image_url} alt="" />
        ) : (
          <>
            <span />
            <span />
          </>
        )}
      </span>
      <span className="circle-title-name">{circleName || 'Circle'}</span>
    </span>
  )

  const headerAside = (
    <div className="circle-header">
      <Link className="circle-back-button" to="/circles" aria-label="Back to circles" title="Back to circles">
        <ChevronLeft size={20} />
      </Link>
      <div className="circle-header-anchor" ref={settingsRef}>
        <h1 className="circle-header-title">{headerTitle}</h1>
        <button
          className="circle-avatar-stack"
          type="button"
          onClick={toggleSettings}
          aria-expanded={settingsOpen}
          aria-label={`Circle settings, ${members.length} of ${MAX_MEMBERS_PER_CIRCLE} members`}
        >
          <span className="circle-avatar-stack-faces">
            {members.map((member) => (
              <span className="circle-avatar" key={member.id} title={member.is_current_user ? 'you' : member.display_name}>
                {member.avatar_url ? (
                  <img src={member.avatar_url} alt="" />
                ) : (
                  (member.display_name || '?').trim().charAt(0).toUpperCase()
                )}
              </span>
            ))}
          </span>
          <span className="circle-avatar-stack-count">
            {members.length}/{MAX_MEMBERS_PER_CIRCLE}
          </span>
          <Settings className="circle-avatar-stack-settings" size={16} aria-hidden="true" />
        </button>

        {settingsOpen && (
          <div className="circle-settings-popover" role="dialog" aria-label="Circle settings">
            <button
              className="circle-settings-close"
              type="button"
              onClick={closeSettings}
              aria-label="Close settings"
            >
              <X size={18} />
            </button>

            {settingsContent}
          </div>
        )}
      </div>
      <div className="header-view-switch header-view-switch-circle">
        <CategorySwitch
          label="Circle view"
          onChange={(value) => setSearchParams(value === 'taste' ? { view: 'taste' } : {})}
          options={VIEW_OPTIONS}
          value={view}
        />
      </div>
    </div>
  )

  // Circle recommendations screen
  return (
    <AppLayout headerAside={headerAside} mainClassName={view === 'taste' ? 'taste-main' : 'map-main'}>
      {view === 'taste' ? (
        <CircleTasteView circleId={circleId} key={circleId} />
      ) : (
        <ConcertRecommendationsView
          mapWater="plum"
          error={error}
          filtersOpen={filtersOpen}
          listAction={
            <button
              className="filter-button"
              type="button"
              onClick={() => setFiltersOpen((current) => !current)}
              aria-expanded={filtersOpen}
              aria-label="Date filter"
            >
              <Filter size={18} />
            </button>
          }
          forYouConcerts={forYouConcerts}
          loading={loading}
          showForYouTasteMatch
          somethingNewConcerts={somethingNewConcerts}
        />
      )}
    </AppLayout>
  )
}
