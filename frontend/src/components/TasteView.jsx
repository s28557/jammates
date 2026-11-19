import { useEffect, useRef, useState } from 'react'
import { getMyTaste } from '../api/spotify.js'
import { TASTE_TIME_RANGES as TIME_RANGES } from '../config/appConfig.js'
import { CategorySwitch } from './CategorySwitch.jsx'


// collapsed artists grid shows this many full rows, however many columns fit
const ARTIST_ROWS = 2
const ALBUMS_COUNT = 9

function getInitial(name) {
  return (name || '?').trim().charAt(0).toUpperCase()
}

// Round artist photo with a letter fallback
function ArtistPhoto({ artist, className }) {
  return (
    <span className={className}>
      {artist.image_url ? <img src={artist.image_url} alt="" /> : getInitial(artist.name)}
    </span>
  )
}

function SectionHeading({ action, children, note }) {
  return (
    <div className="taste-section-heading">
      <h3>{children}</h3>
      {action || (note && <span>{note}</span>)}
    </div>
  )
}

// Placeholder blocks while Spotify data loads
function TasteSkeleton() {
  return (
    <div className="taste-grid" aria-hidden="true">
      <div className="taste-card taste-hero taste-skeleton" />
      <div className="taste-card taste-skeleton" />
      <div className="taste-card taste-wide taste-skeleton taste-skeleton-strip" />
      <div className="taste-card taste-skeleton taste-skeleton-tall" />
      <div className="taste-card taste-skeleton taste-skeleton-tall" />
    </div>
  )
}

// Your Spotify taste: top artists, tracks, albums and genres for a chosen time range
export function TasteView() {
  const [timeRange, setTimeRange] = useState('medium_term')
  const [profiles, setProfiles] = useState({})
  const [errors, setErrors] = useState({})
  const [showAllArtists, setShowAllArtists] = useState(false)
  const [artistColumns, setArtistColumns] = useState(6)
  const artistsGridRef = useRef(null)

  const profile = profiles[timeRange]
  const error = errors[timeRange]
  const rangeDescription = TIME_RANGES.find((range) => range.value === timeRange).description

  // Each time range loads once, switching back reuses it
  useEffect(() => {
    if (profiles[timeRange]) {
      return undefined
    }

    let ignore = false

    getMyTaste(timeRange)
      .then((data) => {
        if (!ignore) {
          setProfiles((current) => ({ ...current, [timeRange]: data }))
          setErrors((current) => ({ ...current, [timeRange]: '' }))
        }
      })
      .catch((requestError) => {
        if (!ignore) {
          setErrors((current) => ({ ...current, [timeRange]: requestError.message || 'Could not load your taste' }))
        }
      })

    return () => {
      ignore = true
    }
  }, [profiles, timeRange])

  const hasData = Boolean(profile && (profile.artists.length || profile.tracks.length))

  // Count the columns the auto-fill grid resolved to, so the collapsed grid ends on full rows
  useEffect(() => {
    const grid = artistsGridRef.current
    if (!grid) {
      return undefined
    }

    const observer = new ResizeObserver(() => {
      const columns = getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length
      setArtistColumns(Math.max(1, columns))
    })
    observer.observe(grid)

    return () => observer.disconnect()
  }, [hasData])

  const handleTimeRangeChange = (value) => {
    setTimeRange(value)
    setShowAllArtists(false)
  }

  const artists = profile?.artists || []
  const topArtist = artists[0]
  const collapsedArtistCount = artistColumns * ARTIST_ROWS
  const stripArtists = showAllArtists ? artists : artists.slice(0, collapsedArtistCount)

  return (
    <div className="taste-view">
      <div className="taste-header">
        <div>
          <h2>Your taste</h2>
          <p>From your Spotify listening over {rangeDescription}</p>
        </div>
        <CategorySwitch
          label="Time range"
          onChange={handleTimeRangeChange}
          options={TIME_RANGES}
          value={timeRange}
        />
      </div>

      {error && <p className="error-state">{error}</p>}
      {!profile && !error && <TasteSkeleton />}

      {profile && !hasData && (
        <p className="taste-empty">Not enough listening on Spotify for this period yet. Try a longer time range.</p>
      )}

      {hasData && (
        <div className="taste-grid">
          {topArtist ? (
            <section className="taste-card taste-hero" aria-label="Top artist">
              {topArtist.image_url && <img className="taste-hero-image" src={topArtist.image_url} alt="" />}
              <div className="taste-hero-content">
                <span className="taste-hero-label">Your #1 artist</span>
                <h3>{topArtist.name}</h3>
                {topArtist.genres.length > 0 && (
                  <div className="taste-hero-genres">
                    {topArtist.genres.slice(0, 3).map((genre) => (
                      <span key={genre}>{genre}</span>
                    ))}
                  </div>
                )}
              </div>
            </section>
          ) : (
            <section className="taste-card taste-hero taste-hero-empty" />
          )}

          <section className="taste-card">
            <SectionHeading>Top genres</SectionHeading>
            {profile.genres.length ? (
              <ol className="taste-genres">
                {profile.genres.map((genre, index) => (
                  <li key={genre.name}>
                    <span className="taste-genre-name">{genre.name}</span>
                    <span className="taste-genre-bar">
                      <span
                        className={index === 0 ? 'taste-genre-fill taste-genre-fill-top' : 'taste-genre-fill'}
                        style={{ width: `${Math.max(6, genre.score * 100)}%` }}
                      />
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="taste-muted">Spotify doesn&apos;t list genres for your top artists in this period.</p>
            )}
          </section>

          {artists.length > 0 && (
            <section className="taste-card taste-wide">
              <SectionHeading
                action={
                  artists.length > collapsedArtistCount && (
                    <button
                      className="taste-more-button"
                      type="button"
                      onClick={() => setShowAllArtists((current) => !current)}
                    >
                      {showAllArtists ? 'Show less' : `Show all ${artists.length}`}
                    </button>
                  )
                }
              >
                Top artists
              </SectionHeading>
              <ol className="taste-artists" ref={artistsGridRef}>
                {stripArtists.map((artist, index) => (
                  <li key={artist.id} title={artist.name}>
                    <span className="taste-artist-photo-wrap">
                      <ArtistPhoto artist={artist} className="taste-artist-photo" />
                      <span className="taste-rank-badge">{index + 1}</span>
                    </span>
                    <span className="taste-artist-name">{artist.name}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="taste-card taste-tracks-card">
            <SectionHeading note={`${profile.tracks.length} tracks`}>Top tracks</SectionHeading>
            {/* the list scrolls inside a card sized by the albums card next to it */}
            <div className="taste-tracks-viewport">
              <ol className="taste-tracks">
                {profile.tracks.map((track, index) => (
                  <li key={track.id}>
                    <span className="taste-track-rank">{index + 1}</span>
                    <span className="taste-track-cover">
                      {track.image_url ? <img src={track.image_url} alt="" /> : getInitial(track.name)}
                    </span>
                    <span className="taste-track-text">
                      <strong>{track.name}</strong>
                      <span>{track.artist}</span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          </section>

          <section className="taste-card">
            <SectionHeading note="from your top tracks">Top albums</SectionHeading>
            <ol className="taste-albums">
              {profile.albums.slice(0, ALBUMS_COUNT).map((album) => (
                <li key={album.id}>
                  <span className="taste-album-cover">
                    {album.image_url ? <img src={album.image_url} alt="" /> : getInitial(album.name)}
                    {album.track_count > 1 && <span className="taste-album-count">{album.track_count} tracks</span>}
                  </span>
                  <strong>{album.name}</strong>
                  <span>{album.artist}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </div>
  )
}
