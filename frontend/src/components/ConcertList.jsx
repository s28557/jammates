import { useEffect, useRef } from 'react'
import { ExternalLink } from 'lucide-react'

function formatDate(concert) {
  const date = concert.local_date || concert.date

  if (!date) {
    return 'Date TBA'
  }

  return new Intl.DateTimeFormat('en', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(date))
}

function getLocation(concert) {
  return [concert.city, concert.country].filter(Boolean).join(', ') || 'Location TBA'
}

function formatTasteMatch(tasteMatch) {
  const names = tasteMatch?.liked_by_display_names || []

  if (!names.length) {
    return ''
  }

  if (tasteMatch.liked_by_all) {
    return 'Liked by everyone'
  }

  return `Liked by ${names.join(', ')}`
}

export function ConcertList({
  concerts,
  highlightedConcertId,
  onConcertSelect,
  selectedConcertId,
  showTasteMatch = false,
  tone,
}) {
  const concertRefs = useRef(new Map())

  useEffect(() => {
    if (!selectedConcertId) {
      return
    }

    const selectedElement = concertRefs.current.get(selectedConcertId)

    if (selectedElement) {
      selectedElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }
  }, [selectedConcertId])

  if (!concerts.length) {
    return <p className="empty-state">No concerts found yet.</p>
  }

  return (
    <div className="concert-list">
      {concerts.map((concert) => {
        const tasteMatchLabel = showTasteMatch ? formatTasteMatch(concert.taste_match) : ''

        return (
          <article
            className={`concert-card concert-card-${tone} ${
              highlightedConcertId === concert.id ? 'concert-card-highlight' : ''
            }`}
            key={concert.id}
            onClick={() => onConcertSelect?.(concert)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onConcertSelect?.(concert)
              }
            }}
            ref={(element) => {
              if (element) {
                concertRefs.current.set(concert.id, element)
              } else {
                concertRefs.current.delete(concert.id)
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="concert-image">
              {concert.image_url ? (
                <img src={concert.image_url} alt="" />
              ) : (
                <span>{concert.artist?.[0] || '?'}</span>
              )}
            </div>
            <div className="concert-details">
              <h3>{concert.artist || concert.name}</h3>
              <p>{concert.name}</p>
              <p>{concert.venue || 'Venue TBA'}</p>
              <p>
                {formatDate(concert)} · {getLocation(concert)}
              </p>
              {tasteMatchLabel && <p className="concert-taste-match">{tasteMatchLabel}</p>}
            </div>
            {concert.url && (
              <a
                aria-label={`Open ${concert.name} on Ticketmaster`}
                className="concert-external-link"
                href={concert.url}
                onClick={(event) => event.stopPropagation()}
                rel="noreferrer"
                target="_blank"
              >
                <ExternalLink size={16} />
              </a>
            )}
          </article>
        )
      })}
    </div>
  )
}
