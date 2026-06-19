import { ConcertList } from './ConcertList.jsx'

// Recommendation list section
export function ConcertSection({
  concerts,
  error,
  highlightedConcertId,
  loading,
  onConcertSelect,
  selectedConcertId,
  showTasteMatch = false,
  title,
  tone,
}) {
  return (
    <section className="concert-section">
      <div className="section-heading">
        <h2>{title}</h2>
        {!loading && !error && <span>{concerts.length}</span>}
      </div>

      {loading && <p className="loading-state">Loading concerts...</p>}
      {error && <p className="error-state">{error}</p>}
      {!loading && !error && (
        <ConcertList
          concerts={concerts}
          highlightedConcertId={highlightedConcertId}
          onConcertSelect={onConcertSelect}
          selectedConcertId={selectedConcertId}
          showTasteMatch={showTasteMatch}
          tone={tone}
        />
      )}
    </section>
  )
}
