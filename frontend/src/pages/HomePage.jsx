import { Link } from 'react-router-dom'
import { AppLayout } from '../layout/AppLayout.jsx'

export function HomePage() {
  return (
    <AppLayout mainClassName="home-main">
      <section className="mode-grid">
        <Link className="mode-tile mode-tile-you" to="/you">
          You
        </Link>
        <Link className="mode-tile mode-tile-circles" to="/circles">
          Circles
        </Link>
      </section>
    </AppLayout>
  )
}
