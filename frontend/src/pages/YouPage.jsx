import { useEffect, useState } from 'react'
import { Filter } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { getForYouConcerts, getSomethingNewConcerts } from '../api/concerts.js'
import { CategorySwitch } from '../components/CategorySwitch.jsx'
import { ConcertRecommendationsView } from '../components/ConcertRecommendationsView.jsx'
import { TasteView } from '../components/TasteView.jsx'
import { AppLayout } from '../layout/AppLayout.jsx'

const VIEW_OPTIONS = [
  { value: 'concerts', label: 'Concerts' },
  { value: 'taste', label: 'Taste' },
]

export function YouPage() {
  // the view lives in the URL so a refresh or back button keeps it
  const [searchParams, setSearchParams] = useSearchParams()
  const view = searchParams.get('view') === 'taste' ? 'taste' : 'concerts'
  const [forYouConcerts, setForYouConcerts] = useState([])
  const [somethingNewConcerts, setSomethingNewConcerts] = useState([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [forYouLoading, setForYouLoading] = useState(true)
  const [somethingNewLoading, setSomethingNewLoading] = useState(true)
  const [forYouError, setForYouError] = useState('')
  const [somethingNewError, setSomethingNewError] = useState('')

  // You page concert recommendations, each list shown as soon as it arrives
  useEffect(() => {
    let ignore = false

    function loadList(request, setConcerts, setListLoading, setListError) {
      request({ artistLimit: 40 })
        .then((concerts) => {
          if (!ignore) {
            setConcerts(concerts)
          }
        })
        .catch((requestError) => {
          if (!ignore) {
            setListError(requestError.message || 'Could not load concerts')
          }
        })
        .finally(() => {
          if (!ignore) {
            setListLoading(false)
          }
        })
    }

    loadList(getForYouConcerts, setForYouConcerts, setForYouLoading, setForYouError)
    loadList(getSomethingNewConcerts, setSomethingNewConcerts, setSomethingNewLoading, setSomethingNewError)

    return () => {
      ignore = true
    }
  }, [])

  // You recommendations screen
  return (
    <AppLayout
      headerAside={
        <div className="header-view-switch">
          <CategorySwitch
            label="You view"
            onChange={(value) => setSearchParams(value === 'taste' ? { view: 'taste' } : {})}
            options={VIEW_OPTIONS}
            value={view}
          />
        </div>
      }
      headerTitle="You"
      mainClassName={view === 'taste' ? 'taste-main' : 'map-main'}
    >
      {view === 'taste' ? (
        <TasteView />
      ) : (
        <ConcertRecommendationsView
          filtersOpen={filtersOpen}
          listAction={
            <button
              className="filter-button"
              type="button"
              onClick={() => setFiltersOpen((current) => !current)}
              aria-expanded={filtersOpen}
              aria-label="Date filter"
            >
              <Filter size={18} />
            </button>
          }
          forYouConcerts={forYouConcerts}
          forYouError={forYouError}
          forYouLoading={forYouLoading}
          somethingNewConcerts={somethingNewConcerts}
          somethingNewError={somethingNewError}
          somethingNewLoading={somethingNewLoading}
          mapWater="teal"
        />
      )}
    </AppLayout>
  )
}
