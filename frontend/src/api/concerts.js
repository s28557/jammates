import { apiRequest } from './apiClient.js'

function buildConcertQuery({ countryCode, artistLimit } = {}) {
  const params = new URLSearchParams()

  if (countryCode) {
    params.set('country_code', countryCode)
  }

  if (artistLimit) {
    params.set('artist_limit', String(artistLimit))
  }

  const query = params.toString()
  return query ? `?${query}` : ''
}

export function getForYouConcerts(options) {
  return apiRequest(`/concerts/me/for-you${buildConcertQuery(options)}`)
}

export function getSomethingNewConcerts(options) {
  return apiRequest(`/concerts/me/something-new${buildConcertQuery(options)}`)
}

export function getCircleForYouConcerts(circleId, options) {
  return apiRequest(`/concerts/circle/${circleId}/for-you${buildConcertQuery(options)}`)
}

export function getCircleSomethingNewConcerts(circleId, options) {
  return apiRequest(`/concerts/circle/${circleId}/something-new${buildConcertQuery(options)}`)
}
