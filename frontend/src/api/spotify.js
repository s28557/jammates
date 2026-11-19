import { apiRequest } from './apiClient.js'

// top artists, tracks, albums and genres for one time range
export function getMyTaste(timeRange = 'medium_term') {
  return apiRequest(`/spotify/me/taste?time_range=${encodeURIComponent(timeRange)}`)
}
