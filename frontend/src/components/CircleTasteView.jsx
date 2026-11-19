import { useEffect, useState } from 'react'
import { getCircleTaste } from '../api/circles.js'
import { TASTE_TIME_RANGES } from '../config/appConfig.js'
import { CategorySwitch } from './CategorySwitch.jsx'

const RING_RADIUS = 56
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS

function getInitial(name) {
  return (name || '?').trim().charAt(0).toUpperCase()
}

function getMemberName(member) {
  return member.is_current_user ? 'you' : member.display_name
}

function MemberAvatar({ member, className = 'taste-member-avatar' }) {
  return (
    <span className={className} title={getMemberName(member)}>
      {member.avatar_url ? <img src={member.avatar_url} alt="" /> : getInitial(member.display_name)}
    </span>
  )
}

// Small overlapping avatars of the members who like something
function LikedBy({ memberIds, membersById, total }) {
  const count = memberIds.length

  return (
    <span className="taste-liked-by">
      <span className="taste-liked-by-faces">
        {memberIds.map((id) => membersById[id] && <MemberAvatar key={id} member={membersById[id]} />)}
      </span>
      <span>{count === total ? 'all' : `${count} of ${total}`}</span>
    </span>
  )
}

function SectionHeading({ children, note }) {
  return (
    <div className="taste-section-heading">
      <h3>{children}</h3>
      {note && <span>{note}</span>}
    </div>
  )
}

// Circular match score, a dash when there is nobody to compare
function MatchRing({ value }) {
  const hasValue = value !== null && value !== undefined

  return (
    <div
      className="circle-match-ring"
      role="img"
      aria-label={hasValue ? `Taste match ${value}%` : 'Not enough data for a taste match'}
    >
      <svg viewBox="0 0 132 132" aria-hidden="true">
        <circle className="circle-match-ring-track" cx="66" cy="66" r={RING_RADIUS} />
        <circle
          className="circle-match-ring-value"
          cx="66"
          cy="66"
          r={RING_RADIUS}
          strokeDasharray={RING_CIRCUMFERENCE}
          strokeDashoffset={RING_CIRCUMFERENCE * (1 - (hasValue ? value : 0) / 100)}
        />
      </svg>
      <strong>
        {hasValue ? value : '–'}
        {hasValue && <span>%</span>}
      </strong>
    </div>
  )
}

function CircleTasteSkeleton() {
  return (
    <div className="taste-grid" aria-hidden="true">
      <div className="taste-card taste-wide taste-skeleton taste-skeleton-strip" />
      <div className="taste-card taste-wide taste-skeleton taste-skeleton-strip" />
      <div className="taste-card taste-skeleton" />
      <div className="taste-card taste-skeleton" />
    </div>
  )
}

// Circle taste blend: how members' Spotify taste overlaps and what each one brings
export function CircleTasteView({ circleId }) {
  const [timeRange, setTimeRange] = useState('medium_term')
  const [blends, setBlends] = useState({})
  const [errors, setErrors] = useState({})

  const blend = blends[timeRange]
  const error = errors[timeRange]
  const rangeDescription = TASTE_TIME_RANGES.find((range) => range.value === timeRange).description

  // Each time range loads once, switching back reuses it
  useEffect(() => {
    if (blends[timeRange]) {
      return undefined
    }

    let ignore = false

    getCircleTaste(circleId, timeRange)
      .then((data) => {
        if (!ignore) {
          setBlends((current) => ({ ...current, [timeRange]: data }))
          setErrors((current) => ({ ...current, [timeRange]: '' }))
        }
      })
      .catch((requestError) => {
        if (!ignore) {
          const message =
            requestError.status === 409
              ? 'Waiting for at least one more person to join this circle.'
              : requestError.message || 'Could not load circle taste'
          setErrors((current) => ({ ...current, [timeRange]: message }))
        }
      })

    return () => {
      ignore = true
    }
  }, [blends, circleId, timeRange])

  const members = blend?.members || []
  const membersById = Object.fromEntries(members.map((member) => [member.id, member]))
  const sharedArtistCount = blend?.shared_artists.length || 0

  return (
    <div className="taste-view taste-view-circle">
      <div className="taste-header">
        <div>
          <h2>Circle taste</h2>
          <p>How your Spotify listening overlaps over {rangeDescription}</p>
        </div>
        <CategorySwitch label="Time range" onChange={setTimeRange} options={TASTE_TIME_RANGES} value={timeRange} />
      </div>

      {error && <p className="error-state">{error}</p>}
      {!blend && !error && <CircleTasteSkeleton />}

      {blend && (
        <div className="taste-grid">
          <section className="taste-card taste-wide circle-blend-hero" aria-label="Taste match">
            <MatchRing value={blend.match} />
            <div className="circle-blend-summary">
              <span className="taste-hero-label">Your taste match</span>
              <div className="circle-blend-members">
                {members.map((member) => (
                  <span
                    className={`circle-blend-member ${member.has_data ? '' : 'circle-blend-member-missing'}`}
                    key={member.id}
                  >
                    <MemberAvatar member={member} className="taste-member-avatar taste-member-avatar-large" />
                    {getMemberName(member)}
                    {!member.has_data && <em>no data</em>}
                  </span>
                ))}
              </div>

              {/* members without data are marked by their "no data" badge and simply have no pairs */}
              {blend.match === null && (
                <p className="taste-muted">Not enough listening over {rangeDescription} to compare. Try a longer time range.</p>
              )}

              {blend.pairs.length > 0 && (
                <div className="circle-blend-pairs">
                  {blend.pairs.map((pair) => {
                    const [first, second] = pair.members.map((id) => membersById[id])
                    return (
                      <span className="circle-blend-pair" key={pair.members.join('-')}>
                        <span className="taste-liked-by-faces">
                          <MemberAvatar member={first} />
                          <MemberAvatar member={second} />
                        </span>
                        {getMemberName(first)} &amp; {getMemberName(second)}
                        <strong>{pair.match}%</strong>
                      </span>
                    )
                  })}
                </div>
              )}
            </div>
          </section>

          <section className="taste-card taste-wide">
            <SectionHeading
              note={sharedArtistCount ? `${sharedArtistCount} ${sharedArtistCount === 1 ? 'artist' : 'artists'}` : null}
            >
              What you share
            </SectionHeading>
            {blend.shared_artists.length ? (
              <ol className="taste-artists">
                {blend.shared_artists.map((artist) => (
                  <li key={artist.id} title={artist.name}>
                    <span className="taste-artist-photo">
                      {artist.image_url ? <img src={artist.image_url} alt="" /> : getInitial(artist.name)}
                    </span>
                    <span className="taste-artist-name">{artist.name}</span>
                    <LikedBy memberIds={artist.liked_by} membersById={membersById} total={members.length} />
                  </li>
                ))}
              </ol>
            ) : (
              <p className="taste-muted">No artists in common for this period yet. Try a longer time range.</p>
            )}
          </section>

          <section className="taste-card">
            <SectionHeading>Shared genres</SectionHeading>
            {blend.shared_genres.length ? (
              <ol className="circle-shared-genres">
                {blend.shared_genres.map((genre) => (
                  <li key={genre.name}>
                    <span className="taste-genre-name">{genre.name}</span>
                    <LikedBy memberIds={genre.liked_by} membersById={membersById} total={members.length} />
                  </li>
                ))}
              </ol>
            ) : (
              <p className="taste-muted">No genres in common for this period.</p>
            )}
          </section>

          <section className="taste-card">
            <SectionHeading>Tracks you share</SectionHeading>
            {blend.shared_tracks.length ? (
              <ol className="taste-tracks circle-shared-tracks">
                {blend.shared_tracks.map((track) => (
                  <li key={track.id}>
                    <span className="taste-track-cover">
                      {track.image_url ? <img src={track.image_url} alt="" /> : getInitial(track.name)}
                    </span>
                    <span className="taste-track-text">
                      <strong>{track.name}</strong>
                      <span>{track.artist}</span>
                    </span>
                    <LikedBy memberIds={track.liked_by} membersById={membersById} total={members.length} />
                  </li>
                ))}
              </ol>
            ) : (
              <p className="taste-muted">None of your top tracks overlap in this period.</p>
            )}
          </section>

          <section className="taste-card taste-wide">
            <SectionHeading note="artists only they have in their top">Everyone brings</SectionHeading>
            <div className="circle-brings">
              {members.map((member) => (
                <div className="circle-brings-member" key={member.id}>
                  <div className="circle-brings-header">
                    <MemberAvatar member={member} className="taste-member-avatar taste-member-avatar-large" />
                    <strong>{getMemberName(member)}</strong>
                  </div>
                  {member.unique_artists.length ? (
                    <ol>
                      {member.unique_artists.map((artist) => (
                        <li key={artist.id}>
                          <span className="circle-brings-photo">
                            {artist.image_url ? <img src={artist.image_url} alt="" /> : getInitial(artist.name)}
                          </span>
                          <span>{artist.name}</span>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="taste-muted">
                      {member.has_data ? 'Everything they love, someone else does too.' : 'No Spotify data for this period.'}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
