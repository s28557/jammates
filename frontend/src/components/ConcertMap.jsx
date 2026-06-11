import L from 'leaflet'
import { Marker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import { useEffect, useMemo, useRef } from 'react'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER = [48.5, 12]
const DEFAULT_ZOOM = 4

function hasCoordinates(concert) {
  return Number.isFinite(Number(concert.lat)) && Number.isFinite(Number(concert.lng))
}

function getMarkerColor(category) {
  return category === 'somethingNew' ? '#9b3378' : '#293447'
}

function getPinLabel(concert) {
  return (concert.artist || concert.name || '?').trim().charAt(0).toUpperCase()
}

function createConcertIcon(concert) {
  const markerColor = getMarkerColor(concert.category)
  const imageStyle = concert.image_url
    ? `style="background-image: url('${concert.image_url.replaceAll("'", "%27")}')"`
    : ''
  const imageContent = concert.image_url ? '' : `<span>${getPinLabel(concert)}</span>`

  return L.divIcon({
    className: 'concert-div-icon',
    html: `
      <div class="artist-map-pin-wrapper" style="--pin-color: ${markerColor}">
        <div class="artist-map-pin">
          <div class="artist-map-pin-media ${concert.image_url ? 'has-image' : ''}" ${imageStyle}>
            ${imageContent}
          </div>
        </div>
      </div>
    `,
    iconAnchor: [26, 58],
    iconSize: [52, 62],
    popupAnchor: [0, -66],
  })
}

function formatDate(concert) {
  const date = concert.local_date || concert.date

  if (!date) {
    return 'Date TBA'
  }

  return new Intl.DateTimeFormat('en', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(date))
}

function MapBounds({ concerts }) {
  const map = useMap()
  const boundsKey = useMemo(
    () => concerts.map((concert) => `${concert.id}:${concert.lat}:${concert.lng}`).join('|'),
    [concerts],
  )

  useEffect(() => {
    if (concerts.length > 1) {
      const bounds = concerts.map((concert) => [Number(concert.lat), Number(concert.lng)])
      map.fitBounds(bounds, { padding: [34, 34], maxZoom: 8 })
      return
    }

    if (concerts.length === 1) {
      map.setView([Number(concerts[0].lat), Number(concerts[0].lng)], 8)
    }
  }, [boundsKey, map])

  return null
}

function MapFocus({ concert }) {
  const map = useMap()

  useEffect(() => {
    if (!concert || !hasCoordinates(concert)) {
      return
    }

    map.flyTo([Number(concert.lat), Number(concert.lng)], Math.max(map.getZoom(), 9), {
      duration: 0.7,
    })
  }, [concert, map])

  return null
}

function ConcertMarker({ concert, isActive, onConcertSelect }) {
  const markerRef = useRef(null)
  const icon = useMemo(() => createConcertIcon(concert), [concert])

  useEffect(() => {
    const markerElement = markerRef.current?.getElement()
    const pinElement = markerElement?.querySelector('.artist-map-pin-wrapper')

    if (!pinElement) {
      return
    }

    pinElement.classList.toggle('artist-map-pin-wrapper-active', isActive)
  }, [isActive])

  return (
    <Marker
      eventHandlers={{
        click: () => onConcertSelect?.(concert),
      }}
      icon={icon}
      ref={markerRef}
      position={[Number(concert.lat), Number(concert.lng)]}
    >
      <Popup>
        <div className="map-popup">
          <strong>{concert.artist || concert.name}</strong>
          <span>{concert.name}</span>
          <span>{concert.venue || 'Venue TBA'}</span>
          <span>
            {formatDate(concert)} · {[concert.city, concert.country].filter(Boolean).join(', ')}
          </span>
        </div>
      </Popup>
    </Marker>
  )
}

export function ConcertMap({ activeConcertId, concerts, onConcertSelect, selectedConcertId }) {
  const mappableConcerts = concerts.filter(hasCoordinates)
  const selectedConcert = mappableConcerts.find((concert) => concert.id === selectedConcertId)

  return (
    <div className="concert-map-shell">
      <MapContainer
        center={DEFAULT_CENTER}
        className="concert-map"
        scrollWheelZoom
        zoom={DEFAULT_ZOOM}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapBounds concerts={mappableConcerts} />
        <MapFocus concert={selectedConcert} />

        {mappableConcerts.map((concert) => (
          <ConcertMarker
            concert={concert}
            isActive={concert.id === activeConcertId}
            key={`${concert.category}-${concert.id}`}
            onConcertSelect={onConcertSelect}
          />
        ))}
      </MapContainer>

      {!mappableConcerts.length && (
        <div className="map-empty-state">
          No concerts with map coordinates yet.
        </div>
      )}
    </div>
  )
}
