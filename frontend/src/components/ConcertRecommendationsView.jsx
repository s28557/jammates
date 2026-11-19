import { useEffect, useRef, useMemo, useState } from 'react'
import { ConcertMap } from './ConcertMap.jsx'
import { ConcertPanel } from './ConcertPanel.jsx'
import { DateRangeFilter } from './DateRangeFilter.jsx'

// Date filter helpers
function getConcertDate(concert) {
  const rawDate = concert.local_date || concert.date

  if (!rawDate) {
    return null
  }

  if (concert.local_date) {
    const [year, month, day] = concert.local_date.split('-').map(Number)
    const localDate = new Date(year, month - 1, day)
    return Number.isNaN(localDate.getTime()) ? null : localDate
  }

  // compare by day, so a concert late on the last day stays in range
  const date = new Date(rawDate)
  date.setHours(0, 0, 0, 0)
  return Number.isNaN(date.getTime()) ? null : date
}

function getTodayStart() {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return today
}

// Upcoming concerts only, optionally inside the chosen date range
function isUpcoming(concert, today) {
  const concertDate = getConcertDate(concert)
  return Boolean(concertDate) && concertDate >= today
}

function isInDateRange(concert, dateRange) {
  if (!dateRange) {
    return true
  }

  const concertDate = getConcertDate(concert)
  return concertDate >= dateRange.start && concertDate <= dateRange.end
}

// Merged list ordering, nearest concerts first
function sortByDate(concerts) {
  return [...concerts].sort((first, second) => {
    const firstDate = getConcertDate(first)
    const secondDate = getConcertDate(second)

    if (!firstDate || !secondDate) {
      return firstDate ? -1 : secondDate ? 1 : 0
    }

    return firstDate - secondDate
  })
}

export function ConcertRecommendationsView({
  error,
  loading,
  filtersOpen,
  forYouConcerts,
  // defaults read error and loading, so those two must come first
  forYouError = error,
  forYouLoading = loading,
  listAction,
  showForYouTasteMatch = false,
  somethingNewConcerts,
  somethingNewError = error,
  somethingNewLoading = loading,
  mapWater = 'teal',
}) {
  const [dateRange, setDateRange] = useState(null)
  const [category, setCategory] = useState('all')
  const [selectedConcertId, setSelectedConcertId] = useState(null)
  const [highlightedConcertId, setHighlightedConcertId] = useState(null)
  const highlightTimerRef = useRef(null)

  // Highlight cleanup
  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        window.clearTimeout(highlightTimerRef.current)
      }
    }
  }, [])

  // Upcoming concerts from both lists, tagged with their category
  const today = useMemo(() => getTodayStart(), [])
  const upcomingConcerts = useMemo(
    () =>
      [
        ...forYouConcerts.map((concert) => ({ ...concert, category: 'forYou' })),
        ...somethingNewConcerts.map((concert) => ({ ...concert, category: 'somethingNew' })),
      ].filter((concert) => isUpcoming(concert, today)),
    [forYouConcerts, somethingNewConcerts, today],
  )
  const dateFilteredConcerts = useMemo(
    () => upcomingConcerts.filter((concert) => isInDateRange(concert, dateRange)),
    [dateRange, upcomingConcerts],
  )

  // Category switch drives both the list and the map pins
  const visibleConcerts = useMemo(
    () =>
      category === 'all'
        ? sortByDate(dateFilteredConcerts)
        : dateFilteredConcerts.filter((concert) => concert.category === category),
    [category, dateFilteredConcerts],
  )

  // Date slider spans today to the furthest concert, histogram follows the category
  const dateDomainEnd = useMemo(() => {
    const lastDate = upcomingConcerts.reduce((latest, concert) => {
      const concertDate = getConcertDate(concert)
      return concertDate > latest ? concertDate : latest
    }, today)
    const minimumEnd = new Date(today)
    minimumEnd.setDate(minimumEnd.getDate() + 30)
    return lastDate > minimumEnd ? lastDate : minimumEnd
  }, [today, upcomingConcerts])
  const histogramDates = useMemo(
    () =>
      upcomingConcerts
        .filter((concert) => category === 'all' || concert.category === category)
        .map(getConcertDate),
    [category, upcomingConcerts],
  )

  const countByCategory = (value) =>
    dateFilteredConcerts.filter((concert) => concert.category === value).length
  const listLoading = {
    all: forYouLoading || somethingNewLoading,
    forYou: forYouLoading,
    somethingNew: somethingNewLoading,
  }[category]
  const listErrors = [
    ...new Set(
      [category !== 'somethingNew' && forYouError, category !== 'forYou' && somethingNewError].filter(Boolean),
    ),
  ]
  const categoryOptions = [
    {
      value: 'all',
      label: 'All',
      count:
        forYouLoading || somethingNewLoading || forYouError || somethingNewError
          ? undefined
          : dateFilteredConcerts.length,
    },
    {
      value: 'forYou',
      label: 'For You',
      count: forYouLoading || forYouError ? undefined : countByCategory('forYou'),
    },
    {
      value: 'somethingNew',
      label: 'Something New',
      count: somethingNewLoading || somethingNewError ? undefined : countByCategory('somethingNew'),
    },
  ]

  // Concert selection syncs map and list
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

  // Recommendations map, list and filters
  return (
    <div className="recommendations-map-layout">
      <div className="recommendations-map-column">
        <ConcertMap
          activeConcertId={highlightedConcertId}
          concerts={visibleConcerts}
          loading={listLoading}
          onConcertSelect={handleConcertSelect}
          selectedConcertId={selectedConcertId}
          water={mapWater}
        />
      </div>

      <aside className="recommendations-sidebar">
        <ConcertPanel
          category={category}
          categoryOptions={categoryOptions}
          concerts={visibleConcerts}
          errors={listErrors}
          filters={
            <DateRangeFilter
              dates={histogramDates}
              domainEnd={dateDomainEnd}
              domainStart={today}
              matchCount={visibleConcerts.length}
              onChange={setDateRange}
              value={dateRange}
            />
          }
          filtersActive={Boolean(dateRange)}
          filtersOpen={filtersOpen}
          headerAction={listAction}
          highlightedConcertId={highlightedConcertId}
          loading={listLoading}
          onCategoryChange={setCategory}
          onConcertSelect={handleConcertSelect}
          selectedConcertId={selectedConcertId}
          showTasteMatch={showForYouTasteMatch}
        />
      </aside>
    </div>
  )
}
