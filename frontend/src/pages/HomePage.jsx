import { Link } from 'react-router-dom'
import { AppLayout } from '../layout/AppLayout.jsx'

export function HomePage() {
  // Homepage mode selector
  return (
    <AppLayout mainClassName="home-main">
      <section className="mode-grid">
        <Link className="mode-tile mode-tile-you" to="/you">
          <span className="mode-tile-word">You</span>
          <p className="mode-tile-caption">Concerts matched to your Spotify taste, plus new artists worth discovering.</p>
        </Link>
        <Link className="mode-tile mode-tile-circles" to="/circles">
          <svg aria-label="Circles" className="circles-arc-svg" viewBox="0 120 600 178" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <path id="circles-arc-path" d="M 20,375 A 320,320 0 0,1 580,375" />
            </defs>
            <text className="circles-arc-text circles-arc-shadow" transform="translate(7 7)" aria-hidden="true">
              <textPath href="#circles-arc-path" startOffset="50%" textAnchor="middle">
                CIRCLES
              </textPath>
            </text>
            <text className="circles-arc-text">
              <textPath href="#circles-arc-path" startOffset="50%" textAnchor="middle">
                CIRCLES
              </textPath>
            </text>
          </svg>
          <p className="mode-tile-caption">Team up with friends and find concerts you&apos;ll all love.</p>
        </Link>
      </section>
    </AppLayout>
  )
}
