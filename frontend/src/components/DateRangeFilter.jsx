const DAY_MS = 24 * 60 * 60 * 1000
const MAX_BARS = 36

// Day helpers on local midnight dates
function addDays(date, days) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function addMonths(date, months) {
  const next = new Date(date)
  next.setMonth(next.getMonth() + months)
  return next
}

function getDayIndex(date, start) {
  return Math.round((date - start) / DAY_MS)
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function formatDay(date) {
  const sameYear = date.getFullYear() === new Date().getFullYear()

  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' }),
  }).format(date)
}

// Dual-handle date range slider with a weekly concert histogram
export function DateRangeFilter({ dates, domainEnd, domainStart, matchCount, onChange, value }) {
  const totalDays = Math.max(1, getDayIndex(domainEnd, domainStart))
  const startIndex = value ? clamp(getDayIndex(value.start, domainStart), 0, totalDays) : 0
  const endIndex = value ? clamp(getDayIndex(value.end, domainStart), startIndex, totalDays) : totalDays

  // Concerts per bucket, roughly one bar per week
  const barCount = clamp(Math.ceil((totalDays + 1) / 7), 1, MAX_BARS)
  const daysPerBar = (totalDays + 1) / barCount
  const bars = Array.from({ length: barCount }, () => 0)
  dates.forEach((date) => {
    const index = getDayIndex(date, domainStart)
    if (index >= 0 && index <= totalDays) {
      bars[Math.min(barCount - 1, Math.floor(index / daysPerBar))] += 1
    }
  })
  const tallestBar = Math.max(1, ...bars)

  const setRange = (nextStart, nextEnd) => {
    const start = clamp(nextStart, 0, totalDays)
    const end = clamp(nextEnd, start, totalDays)

    onChange(
      start === 0 && end === totalDays
        ? null
        : { start: addDays(domainStart, start), end: addDays(domainStart, end) },
    )
  }

  const today = domainStart
  const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0)
  const shortcuts = [
    { label: 'This month', start: 0, end: getDayIndex(endOfMonth, domainStart) },
    { label: 'Next 3 months', start: 0, end: getDayIndex(addMonths(today, 3), domainStart) },
    { label: 'Any time', start: 0, end: totalDays },
  ]

  // Handles travel inside the track minus their 18px width
  const startOffset = `calc(9px + (100% - 18px) * ${startIndex / totalDays})`
  const endOffset = `calc(9px + (100% - 18px) * ${1 - endIndex / totalDays})`

  return (
    <div className="date-filter">
      <div className="date-filter-summary">
        <strong>
          {formatDay(addDays(domainStart, startIndex))} – {formatDay(addDays(domainStart, endIndex))}
        </strong>
        <span>
          {matchCount} {matchCount === 1 ? 'concert' : 'concerts'}
        </span>
      </div>

      <div aria-hidden="true" className="date-filter-histogram">
        {bars.map((count, index) => {
          const barStart = index * daysPerBar
          const barEnd = (index + 1) * daysPerBar - 1
          const inRange = barEnd >= startIndex && barStart <= endIndex

          return (
            <span
              className={inRange ? 'date-filter-bar-in-range' : ''}
              key={index}
              style={{ height: count ? `${Math.max(10, (count / tallestBar) * 100)}%` : '2px' }}
            />
          )
        })}
      </div>

      <div className="date-filter-slider">
        <span className="date-filter-fill" style={{ left: startOffset, right: endOffset }} />
        <input
          aria-label="Start date"
          aria-valuetext={formatDay(addDays(domainStart, startIndex))}
          // keep the start handle reachable when both handles sit at the far end
          className={startIndex > totalDays / 2 ? 'date-filter-handle-top' : ''}
          max={totalDays}
          min={0}
          onChange={(event) => setRange(Math.min(Number(event.target.value), endIndex), endIndex)}
          step={1}
          type="range"
          value={startIndex}
        />
        <input
          aria-label="End date"
          aria-valuetext={formatDay(addDays(domainStart, endIndex))}
          max={totalDays}
          min={0}
          onChange={(event) => setRange(startIndex, Math.max(Number(event.target.value), startIndex))}
          step={1}
          type="range"
          value={endIndex}
        />
      </div>

      <div className="date-filter-shortcuts">
        {shortcuts.map((shortcut) => {
          const end = clamp(shortcut.end, 0, totalDays)
          const active = startIndex === shortcut.start && endIndex === end

          return (
            <button
              aria-pressed={active}
              key={shortcut.label}
              onClick={() => setRange(shortcut.start, end)}
              type="button"
            >
              {shortcut.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
