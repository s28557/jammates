import { Link } from 'react-router-dom'
import { AppLayout } from '../layout/AppLayout.jsx'

export function HomePage() {
  // Homepage mode selector
  return (
    <AppLayout mainClassName="home-main">
      <section className="mode-grid">
        <Link className="mode-tile mode-tile-you" to="/you">
          You
        </Link>
        <Link className="mode-tile mode-tile-circles" to="/circles">
          <svg aria-label="Circles" className="circles-arc-svg" viewBox="0 0 600 420" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <path id="circles-arc-path" d="M 20,375 A 320,320 0 0,1 580,375" />
            </defs>
            <text className="circles-arc-text">
              <textPath href="#circles-arc-path" startOffset="50%" textAnchor="middle">
                CIRCLES
              </textPath>
            </text>
          </svg>
        </Link>
      </section>
    </AppLayout>
  )
}
