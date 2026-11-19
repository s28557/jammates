import {
  AttributionControl,
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  Popup,
  setWorkerUrl,
} from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useMemo, useRef, useState } from 'react'
import 'maplibre-gl/dist/maplibre-gl.css'

// MapLibre looks for its worker next to its own module file, which no longer
// exists once Vite bundles it, so point it at the emitted worker file instead
setWorkerUrl(maplibreWorkerUrl)

// MapLibre zoom levels are one lower than Leaflet's for the same scale
const DEFAULT_CENTER = [12, 48.5]
const DEFAULT_ZOOM = 3
const FIT_MAX_ZOOM = 7
const FOCUS_MIN_ZOOM = 8

const LAND_COLOR = '#f6f1e7'
const VECTOR_STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'

// Plain OSM raster tiles, used if the vector style can't be loaded
const RASTER_FALLBACK_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}

const LOADING_STYLE = {
  version: 8,
  sources: {},
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': LAND_COLOR } }],
}

// App palette for the OpenFreeMap Positron layers
function getVectorPaint(waterColor) {
  return {
    background: { 'background-color': LAND_COLOR },
    building: { 'fill-color': '#ebe4d8', 'fill-outline-color': '#dfd7c8' },
    landcover_wood: { 'fill-color': '#e6dfd1' },
    landuse_residential: { 'fill-color': '#efe9de' },
    park: { 'fill-color': '#ebe6d9' },
    road_area_pier: { 'fill-color': LAND_COLOR },
    road_pier: { 'line-color': LAND_COLOR },
    water: { 'fill-color': waterColor },
    water_name_line_label: { 'text-color': '#eeeae3', 'text-halo-color': waterColor },
    water_name_point_label: { 'text-color': '#eeeae3', 'text-halo-color': waterColor },
    waterway: { 'line-color': waterColor },
    waterway_line_label: { 'text-color': waterColor, 'text-halo-color': 'rgba(246, 241, 231, 0.8)' },
  }
}

function applyAppPalette(style, waterColor) {
  const paint = getVectorPaint(waterColor)

  return {
    ...style,
    layers: style.layers.map((layer) =>
      paint[layer.id] ? { ...layer, paint: { ...layer.paint, ...paint[layer.id] } } : layer,
    ),
  }
}

// Water uses a palette token from index.css, e.g. "teal" -> --color-teal
function getCssColor(token) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--color-${token}`).trim()
}

// Map data helpers
// Missing coordinates (null) and Ticketmaster's 0,0 placeholder would land on "Null Island"
function hasCoordinates(concert) {
  if (concert.lat == null || concert.lng == null || concert.lat === '' || concert.lng === '') {
    return false
  }

  const lat = Number(concert.lat)
  const lng = Number(concert.lng)
  return Number.isFinite(lat) && Number.isFinite(lng) && !(lat === 0 && lng === 0)
}

function getLngLat(concert) {
  return [Number(concert.lng), Number(concert.lat)]
}

function getMarkerColor(category) {
  return category === 'somethingNew' ? 'var(--color-brand)' : 'var(--color-teal)'
}

function getPinLabel(concert) {
  return (concert.artist || concert.name || '?').trim().charAt(0).toUpperCase()
}

function getMarkerKey(concert) {
  return `${concert.category}-${concert.id}`
}

// Popup date formatting
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

function createElement(tagName, className, text) {
  const element = document.createElement(tagName)

  if (className) {
    element.className = className
  }
  if (text !== undefined) {
    element.textContent = text
  }

  return element
}

// Custom map marker element
function createMarkerElement(concert) {
  const root = createElement('div', 'concert-marker')
  const wrapper = createElement('div', 'artist-map-pin-wrapper')
  const pin = createElement('div', 'artist-map-pin')
  const media = createElement('div', 'artist-map-pin-media')

  wrapper.style.setProperty('--pin-color', getMarkerColor(concert.category))

  if (concert.image_url) {
    media.classList.add('has-image')
    media.style.backgroundImage = `url("${concert.image_url.replaceAll('"', '%22')}")`
  } else {
    media.append(createElement('span', '', getPinLabel(concert)))
  }

  pin.append(media)
  wrapper.append(pin)
  root.append(wrapper)

  return root
}

function createPopupContent(concert) {
  const content = createElement('div', 'map-popup')

  content.append(
    createElement('strong', '', concert.artist || concert.name),
    createElement('span', '', concert.name),
    createElement('span', '', concert.venue || 'Venue TBA'),
    createElement(
      'span',
      '',
      `${formatDate(concert)} · ${[concert.city, concert.country].filter(Boolean).join(', ')}`,
    ),
  )

  return content
}

// Concert map container
export function ConcertMap({
  activeConcertId,
  concerts,
  loading = false,
  onConcertSelect,
  selectedConcertId,
  water = 'teal',
}) {
  const containerRef = useRef(null)
  const markersRef = useRef(new Map())
  const hasFittedRef = useRef(false)
  const onConcertSelectRef = useRef(onConcertSelect)
  const [map, setMap] = useState(null)
  const [mapError, setMapError] = useState('')

  const mappableConcerts = useMemo(() => concerts.filter(hasCoordinates), [concerts])
  const concertsKey = useMemo(
    () => mappableConcerts.map((concert) => `${getMarkerKey(concert)}:${concert.lat}:${concert.lng}`).join('|'),
    [mappableConcerts],
  )
  const selectedConcert = mappableConcerts.find((concert) => concert.id === selectedConcertId)

  useEffect(() => {
    onConcertSelectRef.current = onConcertSelect
  }, [onConcertSelect])

  // Map setup
  useEffect(() => {
    let cancelled = false
    let instance

    try {
      instance = new MapLibreMap({
        attributionControl: false,
        center: DEFAULT_CENTER,
        container: containerRef.current,
        dragRotate: false,
        maxPitch: 0,
        pitchWithRotate: false,
        style: LOADING_STYLE,
        touchPitch: false,
        zoom: DEFAULT_ZOOM,
      })
    } catch {
      queueMicrotask(() => setMapError('The map needs WebGL, which this browser does not support.'))
      return undefined
    }

    instance.touchZoomRotate.disableRotation()
    instance.keyboard.disableRotation()
    instance.addControl(new NavigationControl({ showCompass: false }), 'top-left')
    // Attribution text comes from the style sources (OpenFreeMap or the OSM fallback)
    instance.addControl(new AttributionControl({ compact: false }), 'bottom-right')
    instance.once('load', () => {
      if (!cancelled) {
        setMap(instance)
      }
    })

    fetch(VECTOR_STYLE_URL)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Map style request failed: ${response.status}`)
        }
        return response.json()
      })
      .then((style) => {
        if (!cancelled) {
          instance.setStyle(applyAppPalette(style, getCssColor(water)))
        }
      })
      .catch(() => {
        if (!cancelled) {
          instance.setStyle(RASTER_FALLBACK_STYLE)
        }
      })

    return () => {
      cancelled = true
      instance.remove()
      setMap(null)
    }
  }, [water])

  // Concert markers
  useEffect(() => {
    if (!map) {
      return undefined
    }

    const markers = markersRef.current

    mappableConcerts.forEach((concert) => {
      const element = createMarkerElement(concert)
      const popup = new Popup({ closeButton: true, maxWidth: '260px', offset: 60 }).setDOMContent(
        createPopupContent(concert),
      )
      const marker = new Marker({ anchor: 'bottom', element, offset: [0, 4] })
        .setLngLat(getLngLat(concert))
        .setPopup(popup)
        .addTo(map)

      element.addEventListener('click', () => onConcertSelectRef.current?.(concert))
      markers.set(getMarkerKey(concert), { concert, element, marker })
    })

    return () => {
      markers.forEach(({ marker }) => marker.remove())
      markers.clear()
    }
    // concertsKey tracks the concerts that matter for markers
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [concertsKey, map])

  // Highlighted marker
  useEffect(() => {
    markersRef.current.forEach(({ concert, element }) => {
      element
        .querySelector('.artist-map-pin-wrapper')
        ?.classList.toggle('artist-map-pin-wrapper-active', concert.id === activeConcertId)
      element.classList.toggle('concert-marker-active', concert.id === activeConcertId)
    })
  }, [activeConcertId, concertsKey, map])

  // Map bounds
  useEffect(() => {
    if (!map || !mappableConcerts.length) {
      return
    }

    // Jump on the first fit, glide when the shown concerts change later
    const animate = hasFittedRef.current
    hasFittedRef.current = true

    if (mappableConcerts.length === 1) {
      map.easeTo({ center: getLngLat(mappableConcerts[0]), duration: animate ? 600 : 0, zoom: FIT_MAX_ZOOM })
      return
    }

    const bounds = new LngLatBounds()
    mappableConcerts.forEach((concert) => bounds.extend(getLngLat(concert)))
    map.fitBounds(bounds, { duration: animate ? 600 : 0, maxZoom: FIT_MAX_ZOOM, padding: 34 })
    // concertsKey tracks the concerts that matter for bounds
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [concertsKey, map])

  // Selected marker focus
  useEffect(() => {
    if (!map || !selectedConcert) {
      return
    }

    map.flyTo({
      center: getLngLat(selectedConcert),
      duration: 700,
      zoom: Math.max(map.getZoom(), FOCUS_MIN_ZOOM),
    })
  }, [map, selectedConcert])

  return (
    <div className="concert-map-shell">
      <div className="concert-map" ref={containerRef} />

      {(mapError || (!loading && !mappableConcerts.length)) && (
        <div className="map-empty-state">
          {mapError || 'No concerts with map coordinates yet.'}
        </div>
      )}
    </div>
  )
}
