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

export function ConcertList({ concerts, tone }) {
  if (!concerts.length) {
    return <p className="empty-state">No concerts found yet.</p>
  }

  return (
    <div className="concert-list">
      {concerts.map((concert) => (
        <a
          className={`concert-card concert-card-${tone}`}
          href={concert.url}
          key={concert.id}
          rel="noreferrer"
          target="_blank"
        >
          <div className="concert-image">
            {concert.image_url ? <img src={concert.image_url} alt="" /> : <span>{concert.artist?.[0] || '?'}</span>}
          </div>
          <div className="concert-details">
            <h3>{concert.artist || concert.name}</h3>
            <p>{concert.name}</p>
            <p>{concert.venue || 'Venue TBA'}</p>
            <p>
              {formatDate(concert)} · {getLocation(concert)}
            </p>
          </div>
        </a>
      ))}
    </div>
  )
}
