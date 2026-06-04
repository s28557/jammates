import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getCircleForYouConcerts, getCircleSomethingNewConcerts } from '../api/concerts.js'
import { ConcertSection } from '../components/ConcertSection.jsx'
import { AppLayout } from '../layout/AppLayout.jsx'

export function CircleDetailPage() {
  const { circleId } = useParams()
  const [forYouConcerts, setForYouConcerts] = useState([])
  const [somethingNewConcerts, setSomethingNewConcerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadCircleConcerts() {
      setLoading(true)
      setError('')

      try {
        const [forYou, somethingNew] = await Promise.all([
          getCircleForYouConcerts(circleId, { artistLimit: 40 }),
          getCircleSomethingNewConcerts(circleId, { artistLimit: 40 }),
        ])

        if (!ignore) {
          setForYouConcerts(forYou)
          setSomethingNewConcerts(somethingNew)
        }
      } catch (requestError) {
        if (!ignore) {
          if (requestError.status === 409) {
            setError('Waiting for at least one more person to join this circle.')
          } else {
            setError(requestError.message || 'Could not load circle concerts')
          }
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    loadCircleConcerts()

    return () => {
      ignore = true
    }
  }, [circleId])

  return (
    <AppLayout title={`Circle ${circleId}`}>
      <div className="concert-grid">
        <ConcertSection
          concerts={forYouConcerts}
          error={error}
          loading={loading}
          title="Circle For You"
          tone="green"
        />
        <ConcertSection
          concerts={somethingNewConcerts}
          error={error}
          loading={loading}
          title="Circle Something New"
          tone="purple"
        />
      </div>
    </AppLayout>
  )
}
