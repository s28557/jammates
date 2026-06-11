import { useCallback, useEffect, useState } from 'react'
import { Copy, Filter, LogOut, Settings, Star, Trash2, Upload, UserMinus } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
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
import { ConcertRecommendationsView } from '../components/ConcertRecommendationsView.jsx'
import { MAX_MEMBERS_PER_CIRCLE } from '../config/appConfig.js'
import { AppLayout } from '../layout/AppLayout.jsx'

export function CircleDetailPage() {
  const { circleId } = useParams()
  const navigate = useNavigate()
  const [circle, setCircle] = useState(null)
  const [circleName, setCircleName] = useState('')
  const [circleNameDraft, setCircleNameDraft] = useState('')
  const [members, setMembers] = useState([])
  const [forYouConcerts, setForYouConcerts] = useState([])
  const [somethingNewConcerts, setSomethingNewConcerts] = useState([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [selectedImageFile, setSelectedImageFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [savingAction, setSavingAction] = useState(false)
  const [inviteCopied, setInviteCopied] = useState(false)
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')

  const currentMember = members.find((member) => member.is_current_user)
  const isAdmin = currentMember?.role === 'creator'

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

  const handleCopyInviteCode = async () => {
    if (!circle?.invite_code) {
      return
    }

    await navigator.clipboard?.writeText(circle.invite_code)
    setInviteCopied(true)
    window.setTimeout(() => setInviteCopied(false), 900)
  }

  const handleUploadCircleImage = async (event) => {
    event.preventDefault()

    if (!selectedImageFile) {
      return
    }

    setSavingAction(true)
    setActionMessage('')

    try {
      const updatedCircle = await uploadCircleImage(circleId, selectedImageFile)
      setCircle(updatedCircle)
      setSelectedImageFile(null)
      setActionMessage('Circle image updated')
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not update circle image')
    } finally {
      setSavingAction(false)
    }
  }

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
      setActionMessage('Circle name updated')
    } catch (requestError) {
      setActionMessage(requestError.message || 'Could not update circle name')
    } finally {
      setSavingAction(false)
    }
  }

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

  const toggleSettings = () => {
    setSettingsOpen((current) => {
      const next = !current
      if (next) {
        setFiltersOpen(false)
      }
      return next
    })
  }

  const toggleFilters = () => {
    setFiltersOpen((current) => {
      const next = !current
      if (next) {
        setSettingsOpen(false)
      }
      return next
    })
  }

  const settingsContent = (
    <div className="circle-settings-content">
      <div className="circle-invite-row">
        <span>Invite code</span>
        <strong>{circle?.invite_code || '...'}</strong>
        <button
          className={inviteCopied ? 'copy-button-copied' : ''}
          type="button"
          onClick={handleCopyInviteCode}
          disabled={!circle?.invite_code}
        >
          <Copy size={14} />
        </button>
      </div>

      <form className="circle-upload-form" onSubmit={handleUploadCircleImage}>
        <div className="circle-upload-field">
          <span>Circle image</span>
          <div className="circle-file-control">
            <input
              id="circle-image-upload"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              onChange={(event) => setSelectedImageFile(event.target.files?.[0] || null)}
            />
            <label htmlFor="circle-image-upload">Choose file</label>
            <em>{selectedImageFile?.name || 'No file selected'}</em>
          </div>
        </div>
        <button type="submit" disabled={savingAction || !selectedImageFile}>
          <Upload size={14} />
          Upload image
        </button>
      </form>

      {isAdmin && (
        <form className="circle-name-form" onSubmit={handleUpdateCircleName}>
          <label>
            <span>Circle name</span>
            <input
              type="text"
              value={circleNameDraft}
              onChange={(event) => setCircleNameDraft(event.target.value)}
            />
          </label>
          <button type="submit" disabled={savingAction || !circleNameDraft.trim()}>
            Save name
          </button>
        </form>
      )}

      <section className="settings-members-section">
        <h3>Members</h3>
        <div className="settings-members-list">
          {members.map((member) => (
            <div className="settings-member-row" key={member.id}>
              <span>{member.is_current_user ? 'you' : member.display_name}</span>
              {member.role === 'creator' && (
                <Star aria-label="Circle admin" className="circle-admin-icon" fill="currentColor" size={13} />
              )}
              {isAdmin && !member.is_current_user && (
                <button type="button" onClick={() => handleRemoveMember(member)} disabled={savingAction}>
                  <UserMinus size={13} />
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <div className="circle-danger-actions">
        <button type="button" onClick={handleLeaveCircle} disabled={savingAction}>
          <LogOut size={14} />
          Leave circle
        </button>
        {isAdmin && (
          <button type="button" onClick={handleDeleteCircle} disabled={savingAction}>
            <Trash2 size={14} />
            Delete circle
          </button>
        )}
      </div>

      {actionMessage && <p className="circle-action-message">{actionMessage}</p>}
    </div>
  )

  const membersPanel = (
    <section className="circle-members-panel" aria-label="Circle members">
      <div className="circle-members-summary">
        <span>Members</span>
        <strong>
          {members.length}/{MAX_MEMBERS_PER_CIRCLE}
        </strong>
      </div>
      <div className="circle-members-list">
        {members.map((member) => (
          <div className="circle-member-chip" key={member.id} title={member.display_name}>
            {member.avatar_url ? (
              <img src={member.avatar_url} alt="" />
            ) : (
              <span>{(member.display_name || '?').trim().charAt(0).toUpperCase()}</span>
            )}
            <strong>{member.is_current_user ? 'you' : member.display_name}</strong>
            {member.role === 'creator' && (
              <Star aria-label="Circle admin" className="circle-admin-icon" fill="currentColor" size={13} />
            )}
          </div>
        ))}
      </div>
    </section>
  )

  return (
    <AppLayout
      title={
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
          {circleName || 'Circle'}
        </span>
      }
      titleAction={
        <div className="page-title-actions">
          <button
            className="filter-button"
            type="button"
            onClick={toggleSettings}
            aria-label="Open circle settings"
          >
            <Settings size={18} />
          </button>
          <button
            className="filter-button"
            type="button"
            onClick={toggleFilters}
            aria-label="Open filters"
          >
            <Filter size={18} />
          </button>
        </div>
      }
    >
      <ConcertRecommendationsView
        error={error}
        filtersOpen={filtersOpen}
        forYouConcerts={forYouConcerts}
        forYouTitle="Circle For You"
        loading={loading}
        mapHeader={membersPanel}
        onCloseFilters={() => setFiltersOpen(false)}
        onCloseSettings={() => setSettingsOpen(false)}
        settingsContent={settingsContent}
        settingsOpen={settingsOpen}
        showForYouTasteMatch
        somethingNewConcerts={somethingNewConcerts}
        somethingNewTitle="Circle Something New"
      />
    </AppLayout>
  )
}
