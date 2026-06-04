import { ConcertList } from './ConcertList.jsx'

export function ConcertSection({ concerts, error, loading, title, tone }) {
  return (
    <section className="concert-section">
      <div className="section-heading">
        <h2>{title}</h2>
        {!loading && !error && <span>{concerts.length}</span>}
      </div>

      {loading && <p className="loading-state">Loading concerts...</p>}
      {error && <p className="error-state">{error}</p>}
      {!loading && !error && <ConcertList concerts={concerts} tone={tone} />}
    </section>
  )
}
