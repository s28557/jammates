import { apiRequest } from './apiClient.js'

export function getMyCircles() {
  return apiRequest('/circles/my')
}

export function createCircle(name) {
  const params = new URLSearchParams({ name })
  return apiRequest(`/circles?${params.toString()}`, {
    method: 'POST',
  })
}

export function joinCircle(inviteCode) {
  const params = new URLSearchParams({ invite_code: inviteCode })
  return apiRequest(`/circles/join?${params.toString()}`, {
    method: 'POST',
  })
}
