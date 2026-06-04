import { useEffect, useState } from 'react'
import { getForYouConcerts, getSomethingNewConcerts } from '../api/concerts.js'
import { ConcertSection } from '../components/ConcertSection.jsx'
import { AppLayout } from '../layout/AppLayout.jsx'

export function YouPage() {
  const [forYouConcerts, setForYouConcerts] = useState([])
  const [somethingNewConcerts, setSomethingNewConcerts] = useState([])
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
    <AppLayout title="You">
      <div className="concert-grid">
        <ConcertSection
          concerts={forYouConcerts}
          error={error}
          loading={loading}
          title="For You"
          tone="green"
        />
        <ConcertSection
          concerts={somethingNewConcerts}
          error={error}
          loading={loading}
          title="Something New"
          tone="purple"
        />
      </div>
    </AppLayout>
  )
}
