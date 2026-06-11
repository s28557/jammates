import { useEffect, useRef, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { ConcertMap } from './ConcertMap.jsx'
import { ConcertSection } from './ConcertSection.jsx'

const CONTINENT_COUNTRY_CODES = {
  europe: [
    'PL',
    'DE',
    'GB',
    'FR',
    'NL',
    'ES',
    'IT',
    'SE',
    'NO',
    'DK',
    'BE',
    'AT',
    'CH',
    'CZ',
    'PT',
    'IE',
    'FI',
    'GR',
    'HU',
    'RO',
    'HR',
    'SK',
    'SI',
    'BG',
    'RS',
    'UA',
    'TR',
    'IS',
    'LU',
    'LT',
    'LV',
    'EE',
  ],
  northAmerica: ['US', 'CA', 'MX'],
}

const DATE_FILTERS = {
  all: null,
  next30: 30,
  next90: 90,
  next180: 180,
}

function normalizeCountry(country) {
  return (country || '').trim().toUpperCase()
}

function matchesContinent(concert, continents) {
  if (!continents.length) {
    return false
  }

  const country = normalizeCountry(concert.country)
  return continents.some((continent) => CONTINENT_COUNTRY_CODES[continent]?.includes(country))
}

function getConcertDate(concert) {
  const rawDate = concert.local_date || concert.date

  if (!rawDate) {
    return null
  }

  const date = new Date(rawDate)
  return Number.isNaN(date.getTime()) ? null : date
}

function matchesDateRange(concert, dateRange) {
  const days = DATE_FILTERS[dateRange]

  if (!days) {
    return true
  }

  const concertDate = getConcertDate(concert)

  if (!concertDate) {
    return false
  }

  const now = new Date()
  const end = new Date()
  end.setDate(now.getDate() + days)

  return concertDate >= now && concertDate <= end
}

function filterConcerts(concerts, filters) {
  return concerts.filter(
    (concert) =>
      matchesContinent(concert, filters.continents) &&
      matchesDateRange(concert, filters.dateRange),
  )
}

export function ConcertRecommendationsView({
  error,
  filtersOpen,
  forYouConcerts,
  forYouTitle,
  loading,
  mapHeader,
  onCloseFilters,
  onCloseSettings,
  settingsContent,
  settingsOpen = false,
  showForYouTasteMatch = false,
  somethingNewConcerts,
  somethingNewTitle,
}) {
  const [filters, setFilters] = useState({
    continents: ['europe', 'northAmerica'],
    dateRange: 'all',
  })
  const [selectedConcertId, setSelectedConcertId] = useState(null)
  const [highlightedConcertId, setHighlightedConcertId] = useState(null)
  const highlightTimerRef = useRef(null)

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        window.clearTimeout(highlightTimerRef.current)
      }
    }
  }, [])

  const filteredForYouConcerts = useMemo(
    () => filterConcerts(forYouConcerts, filters),
    [filters, forYouConcerts],
  )
  const filteredSomethingNewConcerts = useMemo(
    () => filterConcerts(somethingNewConcerts, filters),
    [filters, somethingNewConcerts],
  )

  const mappedConcerts = useMemo(
    () => [
      ...filteredForYouConcerts.map((concert) => ({ ...concert, category: 'forYou' })),
      ...filteredSomethingNewConcerts.map((concert) => ({ ...concert, category: 'somethingNew' })),
    ],
    [filteredForYouConcerts, filteredSomethingNewConcerts],
  )

  const toggleContinent = (continent) => {
    setFilters((current) => {
      const active = current.continents.includes(continent)
      const continents = active
        ? current.continents.filter((item) => item !== continent)
        : [...current.continents, continent]

      return {
        ...current,
        continents,
      }
    })
  }

  const resetFilters = () => {
    setFilters({
      continents: ['europe', 'northAmerica'],
      dateRange: 'all',
    })
  }

  const handleConcertSelect = (concert) => {
    setSelectedConcertId(concert.id)
    setHighlightedConcertId(concert.id)

    if (highlightTimerRef.current) {
      window.clearTimeout(highlightTimerRef.current)
    }

    highlightTimerRef.current = window.setTimeout(() => {
      setHighlightedConcertId(null)
    }, 2000)
  }

  return (
    <div className="recommendations-map-layout">
      <div className={`recommendations-map-column ${mapHeader ? 'recommendations-map-column-with-header' : ''}`}>
        {mapHeader && <div className="recommendations-map-header">{mapHeader}</div>}
        <ConcertMap
          activeConcertId={highlightedConcertId}
          concerts={mappedConcerts}
          onConcertSelect={handleConcertSelect}
          selectedConcertId={selectedConcertId}
        />
      </div>

      <aside className="recommendations-sidebar">
        <ConcertSection
          concerts={filteredForYouConcerts}
          error={error}
          highlightedConcertId={highlightedConcertId}
          loading={loading}
          onConcertSelect={handleConcertSelect}
          selectedConcertId={selectedConcertId}
          showTasteMatch={showForYouTasteMatch}
          title={forYouTitle}
          tone="green"
        />
        <ConcertSection
          concerts={filteredSomethingNewConcerts}
          error={error}
          highlightedConcertId={highlightedConcertId}
          loading={loading}
          onConcertSelect={handleConcertSelect}
          selectedConcertId={selectedConcertId}
          title={somethingNewTitle}
          tone="purple"
        />

        {filtersOpen && (
          <div className="filters-panel">
            <div className="filters-panel-header">
              <h2>Filters</h2>
              <button type="button" onClick={onCloseFilters} aria-label="Close filters">
                <X size={18} />
              </button>
            </div>

            <section className="filter-group">
              <h3>Locations</h3>
              <label>
                <input
                  checked={filters.continents.includes('europe')}
                  type="checkbox"
                  onChange={() => toggleContinent('europe')}
                />
                Europe
              </label>
              <label>
                <input
                  checked={filters.continents.includes('northAmerica')}
                  type="checkbox"
                  onChange={() => toggleContinent('northAmerica')}
                />
                North America
              </label>
            </section>

            <section className="filter-group">
              <h3>Dates</h3>
              <label>
                <input
                  checked={filters.dateRange === 'all'}
                  name="dateRange"
                  type="radio"
                  onChange={() => setFilters((current) => ({ ...current, dateRange: 'all' }))}
                />
                All dates
              </label>
              <label>
                <input
                  checked={filters.dateRange === 'next30'}
                  name="dateRange"
                  type="radio"
                  onChange={() => setFilters((current) => ({ ...current, dateRange: 'next30' }))}
                />
                Next 30 days
              </label>
              <label>
                <input
                  checked={filters.dateRange === 'next90'}
                  name="dateRange"
                  type="radio"
                  onChange={() => setFilters((current) => ({ ...current, dateRange: 'next90' }))}
                />
                Next 90 days
              </label>
              <label>
                <input
                  checked={filters.dateRange === 'next180'}
                  name="dateRange"
                  type="radio"
                  onChange={() => setFilters((current) => ({ ...current, dateRange: 'next180' }))}
                />
                Next 6 months
              </label>
            </section>

            <button className="secondary-button" type="button" onClick={resetFilters}>
              Reset filters
            </button>
          </div>
        )}

        {settingsOpen && (
          <div className="filters-panel settings-panel">
            <div className="filters-panel-header">
              <h2>Circle settings</h2>
              <button type="button" onClick={onCloseSettings} aria-label="Close settings">
                <X size={18} />
              </button>
            </div>

            {settingsContent}
          </div>
        )}
      </aside>
    </div>
  )
}
