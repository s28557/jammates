import { useEffect, useState } from 'react'
import { Filter } from 'lucide-react'
import { getForYouConcerts, getSomethingNewConcerts } from '../api/concerts.js'
import { ConcertRecommendationsView } from '../components/ConcertRecommendationsView.jsx'
import { AppLayout } from '../layout/AppLayout.jsx'

export function YouPage() {
  const [forYouConcerts, setForYouConcerts] = useState([])
  const [somethingNewConcerts, setSomethingNewConcerts] = useState([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadConcerts() {
      setLoading(true)
      setError('')

      try {
        const [forYou, somethingNew] = await Promise.all([
          getForYouConcerts({ artistLimit: 40 }),
          getSomethingNewConcerts({ artistLimit: 40 }),
        ])

        if (!ignore) {
          setForYouConcerts(forYou)
          setSomethingNewConcerts(somethingNew)
        }
      } catch (requestError) {
        if (!ignore) {
          setError(requestError.message || 'Could not load concerts')
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    loadConcerts()

    return () => {
      ignore = true
    }
  }, [])

  return (
    <AppLayout
      title="You"
      titleAction={
        <button
          className="filter-button"
          type="button"
          onClick={() => setFiltersOpen((current) => !current)}
          aria-label="Open filters"
        >
          <Filter size={18} />
        </button>
      }
    >
      <ConcertRecommendationsView
        error={error}
        filtersOpen={filtersOpen}
        forYouConcerts={forYouConcerts}
        forYouTitle="For You"
        loading={loading}
        onCloseFilters={() => setFiltersOpen(false)}
        somethingNewConcerts={somethingNewConcerts}
        somethingNewTitle="Something New"
      />
    </AppLayout>
  )
}
