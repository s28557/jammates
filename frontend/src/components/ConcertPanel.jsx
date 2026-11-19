import { CategorySwitch } from './CategorySwitch.jsx'
import { ConcertList } from './ConcertList.jsx'

// Single recommendations list with the All / For You / Something New switch
export function ConcertPanel({
  category,
  categoryOptions,
  concerts,
  errors,
  filters,
  filtersActive = false,
  filtersOpen = false,
  headerAction,
  highlightedConcertId,
  loading,
  onCategoryChange,
  onConcertSelect,
  selectedConcertId,
  showTasteMatch = false,
}) {
  const waitingForFirstResults = loading && !concerts.length

  return (
    <section className={`concert-section concert-panel concert-panel-${category}`}>
      <div className={`concert-panel-header ${filtersActive ? 'concert-panel-header-filtered' : ''}`}>
        <CategorySwitch
          label="Concert recommendations"
          onChange={onCategoryChange}
          options={categoryOptions}
          value={category}
        />
        {headerAction}
      </div>

      <div className={`concert-panel-filters ${filtersOpen ? 'concert-panel-filters-open' : ''}`} inert={!filtersOpen}>
        <div className="concert-panel-filters-inner">{filters}</div>
      </div>

      <div className="concert-panel-body">
        {waitingForFirstResults && <p className="loading-state">Loading concerts...</p>}
        {errors.map((error) => (
          <p className="error-state" key={error}>
            {error}
          </p>
        ))}
        {!waitingForFirstResults && !(errors.length && !concerts.length) && (
          <ConcertList
            concerts={concerts}
            highlightedConcertId={highlightedConcertId}
            onConcertSelect={onConcertSelect}
            selectedConcertId={selectedConcertId}
            showTasteMatch={showTasteMatch}
          />
        )}
        {loading && concerts.length > 0 && <p className="loading-state loading-more">Loading more concerts...</p>}
      </div>
    </section>
  )
}
